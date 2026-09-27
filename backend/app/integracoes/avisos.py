"""
CENTRAL DE AVISOS AO CLIENTE — e-mail + WhatsApp, com ciência.

Toda movimentação que o cliente precisa saber (pedido de documento,
audiência, andamento do processo, prazo, pagamento) passa por aqui:

    notificar(caso_id, tipo, titulo, mensagem)

O que ela faz, nesta ordem:
  1. grava o aviso no banco (tabela `avisos`) — é o registro que sustenta
     a prova de comunicação;
  2. escolhe DE QUAL número do escritório falar, pelo DDD do cliente:
        DDD 69  -> número de Rondônia
        DDD 48  -> número de Santa Catarina
        outro / sem telefone -> sempre o 48 (padrão do escritório);
  3. envia por WhatsApp e por e-mail, cada canal de forma independente
     (falha em um não impede o outro);
  4. o cliente dá CIÊNCIA no painel; enquanto não der, o job de lembrete
     reenvia o aviso a cada 24 h, até o limite configurado.

Nenhuma falha de envio derruba a operação: o aviso fica gravado e o
erro é registrado para o escritório ver no CRM.
"""
from __future__ import annotations

import smtplib
import ssl
from datetime import datetime, timedelta, timezone as _tz
from email.message import EmailMessage

import httpx

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

GRAPH = "https://graph.facebook.com/v21.0"


# ── Roteamento pelo DDD ──────────────────────────────────────────
def so_digitos(v: str | None) -> str:
    return "".join(c for c in (v or "") if c.isdigit())


def ddd_do_cliente(whatsapp: str | None) -> str | None:
    """Extrai o DDD de um número brasileiro em qualquer formato usual
    (5569993225383, 69993225383, (69) 99322-5383...)."""
    n = so_digitos(whatsapp)
    if not n:
        return None
    if n.startswith("55") and len(n) >= 12:
        n = n[2:]
    return n[:2] if len(n) >= 10 else None


def escolher_origem(whatsapp_cliente: str | None) -> tuple[str, str]:
    """Devolve (phone_id do escritório, rótulo do DDD de origem).

    Regra do escritório: 69 fala com 69, 48 fala com 48, o resto fala
    com o 48. Se o número do DDD escolhido não estiver configurado,
    cai no que existir — melhor enviar por um número do que não enviar.
    """
    s = get_settings()
    ddd = ddd_do_cliente(whatsapp_cliente)
    alvo = ddd if ddd in ("69", "48") else s.whatsapp_ddd_padrao

    mapa = {"69": s.whatsapp_phone_id_69, "48": s.whatsapp_phone_id_48}
    phone_id = mapa.get(alvo) or ""

    if not phone_id:                      # o número preferido não está ligado
        outro = "48" if alvo == "69" else "69"
        if mapa.get(outro):
            return mapa[outro], outro
        return s.whatsapp_phone_id, alvo  # configuração antiga, número único
    return phone_id, alvo


def numero_publico(ddd: str) -> str:
    s = get_settings()
    return s.whatsapp_numero_69 if ddd == "69" else (s.whatsapp_numero_48 or s.whatsapp_numero_69)


# ── Canais ───────────────────────────────────────────────────────
def enviar_whatsapp(destino: str, texto: str, phone_id: str) -> None:
    s = get_settings()
    if not (s.whatsapp_token and phone_id and destino):
        raise RuntimeError("WhatsApp não configurado")
    r = httpx.post(
        f"{GRAPH}/{phone_id}/messages",
        headers={"Authorization": f"Bearer {s.whatsapp_token}"},
        json={"messaging_product": "whatsapp", "to": so_digitos(destino),
              "type": "text", "text": {"body": texto[:4000]}},
        timeout=30,
    )
    r.raise_for_status()


def enviar_email(destino: str, assunto: str, corpo_texto: str, corpo_html: str,
                 anexos: list[tuple[str, bytes, str]] | None = None) -> None:
    """Envia o e-mail. `anexos` é uma lista de (nome, conteúdo, mime) — é por
    aí que o documento para assinatura vai junto da mensagem."""
    s = get_settings()
    if not (s.smtp_usuario and s.smtp_senha and destino):
        raise RuntimeError("E-mail não configurado")
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = f"{s.smtp_remetente} <{s.smtp_usuario}>"
    msg["To"] = destino
    msg["Reply-To"] = s.email_escritorio
    msg.set_content(corpo_texto)
    msg.add_alternative(corpo_html, subtype="html")

    for nome, dados, mime in (anexos or []):
        tipo, _, sub = (mime or "application/octet-stream").partition("/")
        msg.add_attachment(dados, maintype=tipo or "application",
                           subtype=sub or "octet-stream", filename=nome)

    ctx = ssl.create_default_context()
    if s.smtp_porta == 465:
        with smtplib.SMTP_SSL(s.smtp_host, s.smtp_porta, context=ctx, timeout=30) as srv:
            srv.login(s.smtp_usuario, s.smtp_senha)
            srv.send_message(msg)
    else:
        with smtplib.SMTP(s.smtp_host, s.smtp_porta, timeout=30) as srv:
            srv.starttls(context=ctx)
            srv.login(s.smtp_usuario, s.smtp_senha)
            srv.send_message(msg)


# ── Textos ───────────────────────────────────────────────────────
def _link_caso(caso_id: str) -> str:
    return f"{get_settings().app_url}/cliente?caso={caso_id}"


def _texto_whatsapp(nome: str, num_atend: str, titulo: str,
                    mensagem: str, link: str, ddd_origem: str) -> str:
    s = get_settings()
    primeiro = (nome or "").split(" ")[0]
    return (
        f"Olá{', ' + primeiro if primeiro else ''}! Aqui é do escritório "
        f"{s.advogado} ({s.oab}).\n\n"
        f"*{titulo}*\n"
        f"Atendimento nº {num_atend}\n\n"
        f"{mensagem}\n\n"
        f"Para ver os detalhes e confirmar que recebeu, acesse:\n{link}\n\n"
        f"Assim que abrir, é só tocar em *“Li e estou ciente”* — isso nos "
        f"confirma que a informação chegou até você.\n\n"
        f"Estamos à disposição neste mesmo número."
    )


def _html_email(nome: str, num_atend: str, titulo: str, mensagem: str,
                link: str, whats: str) -> tuple[str, str]:
    s = get_settings()
    primeiro = (nome or "").split(" ")[0]
    texto = (
        f"Olá{', ' + primeiro if primeiro else ''}!\n\n"
        f"{titulo}\nAtendimento nº {num_atend}\n\n{mensagem}\n\n"
        f"Acesse para ver os detalhes e dar ciência: {link}\n\n"
        f"{s.advogado} — {s.oab}\nWhatsApp: {whats}"
    )
    html = f"""<!doctype html><html><body style="margin:0;background:#F4F5F7;
 font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#2B2B2B">
 <div style="max-width:560px;margin:0 auto;padding:24px">
  <div style="background:#0F2A44;border-radius:12px 12px 0 0;padding:20px 24px">
    <span style="color:#fff;font-size:20px;font-weight:700">FC</span>
    <span style="color:#C9A84C;font-size:11px;letter-spacing:3px;
      text-transform:uppercase;margin-left:8px">Advocacia</span>
  </div>
  <div style="background:#fff;border-radius:0 0 12px 12px;padding:28px 24px">
    <p style="margin:0 0 18px;font-size:15px">Olá{', ' + primeiro if primeiro else ''},</p>
    <h1 style="margin:0 0 6px;font-size:19px;color:#0F2A44">{titulo}</h1>
    <p style="margin:0 0 20px;font-size:12px;color:#7A7A7A">
      Atendimento nº <strong style="color:#0F2A44">{num_atend}</strong></p>
    <p style="margin:0 0 24px;font-size:15px;line-height:1.6;white-space:pre-line">{mensagem}</p>
    <a href="{link}" style="display:inline-block;background:#C9A84C;color:#0F2A44;
      text-decoration:none;font-weight:700;font-size:15px;padding:13px 26px;
      border-radius:10px">Ver e confirmar recebimento</a>
    <p style="margin:22px 0 0;font-size:13px;color:#6B6B6B;line-height:1.6">
      Ao abrir, toque em <strong>“Li e estou ciente”</strong>. É assim que
      registramos que a informação chegou até você.</p>
    <hr style="border:0;border-top:1px solid #ECECEC;margin:26px 0">
    <p style="margin:0;font-size:12px;color:#8A8A8A;line-height:1.7">
      {s.advogado} — {s.oab}<br>WhatsApp: {whats}<br>
      Você recebeu este aviso porque tem um atendimento em andamento no escritório.
    </p>
  </div>
 </div></body></html>"""
    return texto, html


# ── Função principal ─────────────────────────────────────────────
def notificar(caso_id: str, tipo: str, titulo: str, mensagem: str,
              solicitacao_id: str | None = None,
              anexos: list[tuple[str, bytes, str]] | None = None,
              assunto_extra: str = "") -> dict:
    """Registra e dispara um aviso ao cliente por e-mail e WhatsApp.
    `anexos` vai junto do e-mail (ex.: o PDF para assinatura)."""
    db = get_db()
    caso = db.table("casos").select(
        "id,numero_atendimento,titulo,clientes(nome,email,whatsapp)"
    ).eq("id", caso_id).single().execute().data
    cli = caso.get("clientes") or {}
    num_atend = caso.get("numero_atendimento") or "—"

    phone_id, ddd_origem = escolher_origem(cli.get("whatsapp"))
    link = _link_caso(caso_id)

    linha = {
        "caso_id": caso_id, "tipo": tipo, "titulo": titulo,
        "mensagem": mensagem, "numero_origem": ddd_origem,
    }
    if solicitacao_id:
        linha["solicitacao_id"] = solicitacao_id
    aviso = db.table("avisos").insert(linha).execute().data[0]

    erros: list[str] = []

    # WhatsApp
    ok_whats = False
    try:
        enviar_whatsapp(
            cli.get("whatsapp") or "",
            _texto_whatsapp(cli.get("nome") or "", num_atend, titulo,
                            mensagem, link, ddd_origem),
            phone_id,
        )
        ok_whats = True
    except Exception as e:
        erros.append(f"whatsapp: {e}")

    # E-mail
    ok_mail = False
    try:
        corpo_txt, corpo_html = _html_email(
            cli.get("nome") or "", num_atend, titulo, mensagem,
            link, numero_publico(ddd_origem),
        )
        enviar_email(cli.get("email") or "",
                     f"[{num_atend}] {titulo} — FC Advocacia{assunto_extra}",
                     corpo_txt, corpo_html, anexos=anexos)
        ok_mail = True
    except Exception as e:
        erros.append(f"email: {e}")

    db.table("avisos").update({
        "enviado_whatsapp": ok_whats, "enviado_email": ok_mail,
        "erro_envio": "; ".join(erros)[:500] or None,
    }).eq("id", aviso["id"]).execute()

    registrar_evento(caso_id, "AVISO_ENVIADO", {
        "aviso_id": aviso["id"], "tipo": tipo, "titulo": titulo,
        "whatsapp": ok_whats, "email": ok_mail, "origem_ddd": ddd_origem,
    })
    return {"aviso_id": aviso["id"], "enviado_whatsapp": ok_whats,
            "enviado_email": ok_mail, "origem_ddd": ddd_origem,
            "erros": erros}


# ── Lembretes de quem não deu ciência ────────────────────────────
def reenviar_pendentes() -> dict:
    """Reenvia os avisos sem ciência após o prazo. Roda de hora em hora."""
    s = get_settings()
    db = get_db()
    limite = datetime.now(_tz.utc) - timedelta(hours=s.aviso_lembrete_horas)

    try:
        pendentes = db.table("avisos").select("*") \
            .is_("ciencia_em", "null") \
            .lt("lembretes", s.aviso_lembretes_max) \
            .order("criado_em").limit(200).execute().data
    except Exception:
        pendentes = []

    reenviados, ignorados = 0, 0
    for a in pendentes or []:
        if a.get("lembretes", 0) >= s.aviso_lembretes_max:
            ignorados += 1
            continue
        marco = a.get("ultimo_lembrete") or a.get("criado_em")
        try:
            quando = datetime.fromisoformat(str(marco).replace("Z", "+00:00"))
        except Exception:
            continue
        if quando > limite:
            continue

        try:
            caso = db.table("casos").select(
                "id,numero_atendimento,clientes(nome,email,whatsapp)"
            ).eq("id", a["caso_id"]).single().execute().data
        except Exception:
            continue
        cli = caso.get("clientes") or {}
        phone_id, ddd = escolher_origem(cli.get("whatsapp"))
        link = _link_caso(a["caso_id"])
        num = caso.get("numero_atendimento") or "—"
        titulo = f"Lembrete: {a['titulo']}"

        try:
            enviar_whatsapp(cli.get("whatsapp") or "",
                            _texto_whatsapp(cli.get("nome") or "", num, titulo,
                                            a["mensagem"], link, ddd), phone_id)
        except Exception:
            pass
        try:
            txt, html = _html_email(cli.get("nome") or "", num, titulo,
                                    a["mensagem"], link, numero_publico(ddd))
            enviar_email(cli.get("email") or "",
                         f"[{num}] {titulo} — FC Advocacia", txt, html)
        except Exception:
            pass

        db.table("avisos").update({
            "lembretes": a.get("lembretes", 0) + 1,
            "ultimo_lembrete": datetime.now(_tz.utc).isoformat(),
        }).eq("id", a["id"]).execute()
        reenviados += 1

    return {"reenviados": reenviados, "sem_reenvio": ignorados}


# ── Troca de contato: passa a falar no endereço novo ─────────────
ROTULO_CONTATO = {"email": "e-mail", "whatsapp": "WhatsApp"}


def avisar_troca_de_contato(cliente_id: str, antes: dict, depois: dict,
                            quem: str = "ESCRITORIO") -> dict:
    """Quando o e-mail ou o WhatsApp do cliente muda, a plataforma passa a
    falar no endereço novo imediatamente — e confirma isso nos dois lados:

      · no endereço NOVO: confirmação de que os avisos vêm para cá;
      · no endereço ANTIGO: comunicado de segurança, para o cliente
        perceber na hora se a troca não partiu dele.

    Em seguida, tudo o que ainda estava pendente de ciência é reenviado
    para o contato novo — nada se perde na troca.
    """
    db = get_db()
    cli = db.table("clientes").select("*").eq("id", cliente_id).single().execute().data
    mudou = [c for c in ("email", "whatsapp")
             if (antes.get(c) or "") != (depois.get(c) or "") and depois.get(c)]
    if not mudou:
        return {"ok": True, "sem_mudanca": True}

    nome = (cli.get("nome") or "").split(" ")[0]
    lista = " e ".join(ROTULO_CONTATO[c] for c in mudou)
    por_quem = ("Você atualizou" if quem == "CLIENTE"
                else "Atualizamos, a seu pedido,")

    # 1) confirmação no endereço NOVO
    corpo_novo = (
        f"{por_quem} o seu {lista} de contato.\n\n"
        f"A partir de agora, todo aviso sobre o seu processo — pedido de "
        f"documento, audiência, prazo e movimentação — chega neste endereço.\n\n"
        + "\n".join(f"Novo {ROTULO_CONTATO[c]}: {depois.get(c)}" for c in mudou)
    )
    phone_id, ddd = escolher_origem(depois.get("whatsapp") or cli.get("whatsapp"))
    link = f"{get_settings().app_url}/cliente"
    enviados = {"novo_email": False, "novo_whatsapp": False, "antigo_email": False}

    if "email" in mudou or depois.get("email"):
        try:
            txt, html = _html_email(nome, "—", "Contato atualizado",
                                    corpo_novo, link, numero_publico(ddd))
            enviar_email(depois.get("email") or cli.get("email"),
                         "Contato atualizado — FC Advocacia", txt, html)
            enviados["novo_email"] = True
        except Exception:
            pass
    if depois.get("whatsapp"):
        try:
            enviar_whatsapp(depois["whatsapp"],
                            _texto_whatsapp(nome, "—", "Contato atualizado",
                                            corpo_novo, link, ddd), phone_id)
            enviados["novo_whatsapp"] = True
        except Exception:
            pass

    # 2) comunicado de segurança no endereço ANTIGO
    if "email" in mudou and antes.get("email"):
        aviso_seguranca = (
            f"O {lista} de contato da sua conta na plataforma da FC Advocacia "
            f"acaba de ser alterado.\n\n"
            f"Se foi você (ou se pediu isso ao escritório), não precisa fazer "
            f"nada — os próximos avisos já vão para o endereço novo.\n\n"
            f"**Se não foi você, fale conosco imediatamente.** Este é o último "
            f"aviso que enviamos para este endereço."
        )
        try:
            txt, html = _html_email(nome, "—", "Alteração de contato na sua conta",
                                    aviso_seguranca, link, numero_publico(ddd))
            enviar_email(antes["email"],
                         "Alteração de contato na sua conta — FC Advocacia", txt, html)
            enviados["antigo_email"] = True
        except Exception:
            pass

    # 3) o que estava pendente vai de novo, agora para o endereço certo
    reenviados = reenviar_pendentes_do_cliente(cliente_id)

    try:
        casos = db.table("casos").select("id").eq("cliente_id", cliente_id) \
                  .limit(1).execute().data
        if casos:
            registrar_evento(casos[0]["id"], "CONTATO_ATUALIZADO",
                             {"campos": mudou, "por": quem, "envios": enviados,
                              "avisos_reenviados": reenviados})
    except Exception:
        pass
    return {"ok": True, "campos": mudou, "envios": enviados,
            "avisos_reenviados": reenviados}


def reenviar_pendentes_do_cliente(cliente_id: str) -> int:
    """Reenvia, para o contato ATUAL, os avisos deste cliente que ainda não
    receberam ciência. Usado depois de uma troca de e-mail ou WhatsApp."""
    db = get_db()
    try:
        casos = db.table("casos").select("id").eq("cliente_id", cliente_id) \
                  .execute().data or []
        ids = [c["id"] for c in casos]
        if not ids:
            return 0
        pend = db.table("avisos").select("*").in_("caso_id", ids) \
                 .is_("ciencia_em", "null").order("criado_em").execute().data or []
    except Exception:
        return 0

    n = 0
    for a in pend:
        try:
            caso = db.table("casos").select(
                "numero_atendimento, clientes(nome,email,whatsapp)"
            ).eq("id", a["caso_id"]).single().execute().data
            cli = caso.get("clientes") or {}
            phone_id, ddd = escolher_origem(cli.get("whatsapp"))
            link = _link_caso(a["caso_id"])
            num = caso.get("numero_atendimento") or "—"
            try:
                enviar_whatsapp(cli.get("whatsapp") or "",
                                _texto_whatsapp(cli.get("nome") or "", num, a["titulo"],
                                                a["mensagem"], link, ddd), phone_id)
            except Exception:
                pass
            try:
                txt, html = _html_email(cli.get("nome") or "", num, a["titulo"],
                                        a["mensagem"], link, numero_publico(ddd))
                enviar_email(cli.get("email") or "",
                             f"[{num}] {a['titulo']} — FC Advocacia", txt, html)
            except Exception:
                pass
            db.table("avisos").update({
                "ultimo_lembrete": datetime.now(_tz.utc).isoformat(),
            }).eq("id", a["id"]).execute()
            n += 1
        except Exception:
            continue
    return n


def dar_ciencia(aviso_id: str, canal: str = "PAINEL") -> dict:
    db = get_db()
    agora = datetime.now(_tz.utc).isoformat()
    db.table("avisos").update({"ciencia_em": agora, "ciencia_canal": canal}) \
      .eq("id", aviso_id).is_("ciencia_em", "null").execute()
    a = db.table("avisos").select("caso_id,titulo,ciencia_em") \
          .eq("id", aviso_id).single().execute().data
    registrar_evento(a["caso_id"], "CIENCIA_CLIENTE",
                     {"aviso_id": aviso_id, "canal": canal, "titulo": a["titulo"]})
    return {"ok": True, "ciencia_em": a.get("ciencia_em")}
