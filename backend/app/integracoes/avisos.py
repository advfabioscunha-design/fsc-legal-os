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
                 anexos: list[tuple[str, bytes, str]] | None = None,
                 responder_a: str | None = None) -> str:
    """Envia o e-mail e devolve o Message-ID.

    `anexos`: lista de (nome, conteúdo, mime) — é por aí que o documento
      para assinatura viaja junto da mensagem.
    `responder_a`: Message-ID do primeiro e-mail do caso. Com ele, tudo
      fica na MESMA conversa na caixa do cliente: o histórico do
      atendimento inteiro em um fio só.
    """
    from email.utils import make_msgid
    s = get_settings()
    if not (s.smtp_usuario and s.smtp_senha and destino):
        raise RuntimeError("E-mail não configurado")
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = f"{s.smtp_remetente} <{s.smtp_usuario}>"
    msg["To"] = destino
    msg["Reply-To"] = s.email_escritorio
    meu_id = make_msgid(domain="fscadvocaciadigital.com.br")
    msg["Message-ID"] = meu_id
    # `responder_a` pode trazer mais de um id (o âncora do caso e o último
    # e-mail enviado). O In-Reply-To aponta para o mais recente; o References
    # leva todos, e é ele que mantém tudo numa conversa só no Gmail.
    fios = [x for x in (responder_a or "").split() if x.startswith("<")]
    if fios:
        msg["In-Reply-To"] = fios[-1]
        msg["References"] = " ".join(fios)
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
    return meu_id


def ancora_do_caso(caso_id: str) -> str:
    """Identificador FIXO do atendimento, derivado do próprio id do caso.

    Serve de âncora da conversa: como ele nunca muda, todo e-mail do caso
    carrega o mesmo References e o Gmail agrupa tudo num fio só — inclusive
    nos atendimentos que já existiam antes de guardarmos o Message-ID do
    primeiro e-mail. Sem isso, cada aviso abria uma conversa nova."""
    return f"<atendimento-{caso_id}@fscadvocaciadigital.com.br>"


def fio_do_caso(caso_id: str) -> str:
    """Cadeia de References deste atendimento: a âncora fixa e, quando já
    houver, o Message-ID do primeiro e-mail realmente enviado."""
    ancora = ancora_do_caso(caso_id)
    try:
        c = get_db().table("casos").select("email_thread_id").eq("id", caso_id) \
              .maybe_single().execute().data
        primeiro = (c or {}).get("email_thread_id")
    except Exception:
        primeiro = None
    if primeiro and primeiro != ancora:
        return f"{ancora} {primeiro}"
    return ancora


def guardar_fio(caso_id: str, message_id: str) -> None:
    try:
        get_db().table("casos").update({"email_thread_id": message_id}) \
          .eq("id", caso_id).execute()
    except Exception:
        pass


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
        "id,numero_atendimento,titulo,email_thread_id,clientes(nome,email,whatsapp)"
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
        fio = fio_do_caso(caso_id)
        # ASSUNTO FIXO do atendimento: o que muda a cada aviso fica no corpo.
        # Assunto estável + References estável = uma conversa só, do primeiro
        # contato à prestação de contas.
        assunto_caso = (caso.get("titulo") or "Atendimento").strip()
        novo_id = enviar_email(
            cli.get("email") or "",
            f"[{num_atend}] {assunto_caso} — FC Advocacia{assunto_extra}",
            corpo_txt, corpo_html, anexos=anexos, responder_a=fio,
        )
        if novo_id and not (caso or {}).get("email_thread_id"):
            guardar_fio(caso_id, novo_id)   # este vira o fio do atendimento
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


# ══════════════════════════════════════════════════════════════════
#  PRESTAÇÃO DE CONTAS — o último e-mail do fio, que encerra o caso
# ══════════════════════════════════════════════════════════════════
ROTULO_EVENTO = {
    "TRIAGEM": "Atendimento iniciado",
    "ESTADO_MUDOU": "Andamento",
    "SOLICITACAO_CLIENTE": "Documento solicitado",
    "DOCUMENTOS_RECEBIDOS_DO_CLIENTE": "Documentos recebidos",
    "DOCUMENTO_GERADO": "Documento elaborado",
    "DOCUMENTO_ENVIADO_CLIENTE": "Documento enviado para assinatura",
    "DOCUMENTO_ASSINADO_RECEBIDO": "Documento assinado recebido",
    "ASSINADO_RECEBIDO_EMAIL": "Documento assinado recebido por e-mail",
    "AVISO_ENVIADO": "Comunicação enviada",
    "CIENCIA_CLIENTE": "Cliente confirmou o recebimento",
    "PROCESSO_INICIADO_ESTEIRA": "Processo iniciado",
    "CONTRATO_ENVIADO": "Contrato enviado",
    "CASO_ESCRITORIO_CRIADO": "Caso cadastrado",
    "CLIENTE_RETORNOU": "Cliente respondeu",
    "CONTATO_ATUALIZADO": "Contato atualizado",
}


def montar_historico(caso_id: str) -> list[dict]:
    """Linha do tempo do atendimento, do primeiro contato ao encerramento."""
    db = get_db()
    linha: list[dict] = []
    try:
        for e in (db.table("eventos").select("tipo,payload,criado_em")
                    .eq("caso_id", caso_id).order("criado_em").execute().data or []):
            rot = ROTULO_EVENTO.get(e["tipo"])
            if not rot:
                continue
            det = ""
            p = e.get("payload") or {}
            if e["tipo"] == "ESTADO_MUDOU":
                det = f"{p.get('de', '')} → {p.get('para', '')}".strip(" →")
            elif e["tipo"] == "SOLICITACAO_CLIENTE":
                det = p.get("texto", "")
            elif e["tipo"] in ("DOCUMENTO_GERADO", "DOCUMENTO_ENVIADO_CLIENTE",
                               "DOCUMENTO_ASSINADO_RECEBIDO"):
                det = p.get("tipo", "")
            elif e["tipo"] == "AVISO_ENVIADO":
                det = p.get("titulo", "")
            elif e["tipo"] in ("DOCUMENTOS_RECEBIDOS_DO_CLIENTE",
                               "ASSINADO_RECEBIDO_EMAIL"):
                det = ", ".join(p.get("arquivos", []) or [])
            linha.append({"quando": e["criado_em"], "o_que": rot, "detalhe": det})
    except Exception:
        pass
    return linha


def _br_data(iso) -> str:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _reais(v) -> str:
    try:
        return ("R$ " + f"{float(v):,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _destino_do_repasse(cli: dict) -> str:
    """A conta para onde o valor foi, escrita na prestação de contas.

    É o único documento em que o dado bancário do cliente aparece. Não
    vai para contrato, procuração ou petição: peça processual é pública,
    e conta bancária em processo público é problema de quem a informou.

    Sem a declaração de titularidade, não escreve nada. Transferir
    alvará para conta de terceiro é o caminho mais curto para uma
    acusação de apropriação, e o silêncio aqui obriga o escritório a
    confirmar com a pessoa, como fazia antes."""
    if not cli.get("titular_confirmado"):
        return ""

    partes = []
    if cli.get("pix_chave"):
        rotulo = {"CPF": "CPF", "CNPJ": "CNPJ", "EMAIL": "e-mail",
                  "TELEFONE": "telefone", "ALEATORIA": "chave aleatória"}.get(
            (cli.get("pix_tipo") or "").upper(), "chave")
        partes.append(f"PIX ({rotulo}): {cli['pix_chave']}")
    if cli.get("conta"):
        banco = cli.get("banco_nome") or cli.get("banco_codigo") or "banco"
        tipo = (cli.get("conta_tipo") or "").lower()
        partes.append(
            f"{banco}, agência {cli.get('agencia') or '—'}, conta "
            f"{cli['conta']}" + (f" ({tipo})" if tipo else ""))
    if not partes:
        return ""

    quando = cli.get("dados_bancarios_em")
    data = f" Dados informados por você em {_br_data(quando)}." if quando else ""
    return ("\n\nDESTINO DO REPASSE\n"
            + "\n".join(partes)
            + f"\nTitular: {cli.get('nome') or 'o próprio cliente'}." + data)


def prestacao_de_contas(caso_id: str, valores: dict) -> dict:
    """Envia a prestação de contas: linha do tempo completa do atendimento
    + demonstrativo financeiro. É o último e-mail do fio e encerra o caso."""
    s = get_settings()
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id) \
             .single().execute().data
    cli = caso.get("clientes") or {}
    num = caso.get("numero_atendimento") or "—"
    historico = montar_historico(caso_id)

    recebido = float(valores.get("valor_recebido") or 0)
    hc = float(valores.get("honorarios_contratuais") or 0)
    hs = float(valores.get("honorarios_sucumbenciais") or 0)
    desp = float(valores.get("despesas") or 0)
    repasse = valores.get("repasse_cliente")
    repasse = float(repasse) if repasse not in (None, "") else max(recebido - hc - desp, 0)

    registro = db.table("prestacoes_contas").insert({
        "caso_id": caso_id, "valor_recebido": recebido,
        "honorarios_contratuais": hc, "honorarios_sucumbenciais": hs,
        "despesas": desp, "repasse_cliente": repasse,
        "forma_repasse": valores.get("forma_repasse"),
        "observacoes": valores.get("observacoes"),
        "resultado": valores.get("resultado"),
        "historico": historico,
    }).execute().data[0]

    # ── corpo em texto (WhatsApp e fallback) ──
    linhas_hist = "\n".join(
        f"• {_br_data(h['quando'])} — {h['o_que']}" + (f": {h['detalhe']}" if h["detalhe"] else "")
        for h in historico
    ) or "• (sem registros)"
    financeiro_txt = (
        f"Valor recebido no processo: {_reais(recebido)}\n"
        f"Honorários contratuais: {_reais(hc)}\n"
        + (f"Honorários sucumbenciais (do escritório): {_reais(hs)}\n" if hs else "")
        + (f"Despesas processuais: {_reais(desp)}\n" if desp else "")
        + f"VALOR REPASSADO A VOCÊ: {_reais(repasse)}"
        + (f"\nForma do repasse: {valores.get('forma_repasse')}" if valores.get("forma_repasse") else "")
        + _destino_do_repasse(cli)
    )
    mensagem = (
        f"Chegamos ao fim do seu atendimento nº {num}.\n\n"
        + (f"RESULTADO\n{valores.get('resultado')}\n\n" if valores.get("resultado") else "")
        + f"DEMONSTRATIVO FINANCEIRO\n{financeiro_txt}\n\n"
        f"HISTÓRICO DO ATENDIMENTO\n{linhas_hist}\n\n"
        + (f"{valores.get('observacoes')}\n\n" if valores.get("observacoes") else "")
        + "Este e-mail encerra formalmente o atendimento e segue no mesmo fio de "
        "conversa, com tudo o que foi tratado desde o primeiro contato.\n\n"
        "Foi uma honra cuidar do seu caso. Qualquer dúvida sobre estes valores, "
        "é só responder esta mensagem."
    )

    # ── HTML com tabelas ──
    tabela_fin = "".join(
        f'<tr><td style="padding:6px 0;color:#4A4A4A">{rot}</td>'
        f'<td style="padding:6px 0;text-align:right;color:#2B2B2B">{_reais(val)}</td></tr>'
        for rot, val in [("Valor recebido no processo", recebido),
                         ("Honorários contratuais", hc)]
        + ([("Honorários sucumbenciais (do escritório)", hs)] if hs else [])
        + ([("Despesas processuais", desp)] if desp else [])
    )
    tabela_hist = "".join(
        f'<tr><td style="padding:5px 10px 5px 0;color:#8A8A8A;white-space:nowrap;'
        f'vertical-align:top">{_br_data(h["quando"])}</td>'
        f'<td style="padding:5px 0;color:#2B2B2B"><strong>{h["o_que"]}</strong>'
        + (f'<br><span style="color:#6B6B6B">{h["detalhe"]}</span>' if h["detalhe"] else "")
        + "</td></tr>"
        for h in historico
    ) or '<tr><td style="color:#8A8A8A">Sem registros.</td></tr>'

    html = f"""<!doctype html><html><body style="margin:0;background:#F4F5F7;
 font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#2B2B2B">
 <div style="max-width:600px;margin:0 auto;padding:24px">
  <div style="background:#0F2A44;border-radius:12px 12px 0 0;padding:20px 24px">
    <span style="color:#fff;font-size:20px;font-weight:700">FC</span>
    <span style="color:#C9A84C;font-size:11px;letter-spacing:3px;
      text-transform:uppercase;margin-left:8px">Advocacia</span>
  </div>
  <div style="background:#fff;border-radius:0 0 12px 12px;padding:28px 24px">
    <h1 style="margin:0 0 4px;font-size:20px;color:#0F2A44">Prestação de contas</h1>
    <p style="margin:0 0 22px;font-size:12px;color:#7A7A7A">
      Atendimento nº <strong style="color:#0F2A44">{num}</strong>
      &nbsp;·&nbsp; {cli.get('nome', '')}</p>

    {f'<h2 style="margin:0 0 6px;font-size:15px;color:#0F2A44">Resultado</h2><p style="margin:0 0 22px;font-size:14px;line-height:1.6;white-space:pre-line">{valores.get("resultado")}</p>' if valores.get("resultado") else ""}

    <h2 style="margin:0 0 8px;font-size:15px;color:#0F2A44">Demonstrativo financeiro</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px">{tabela_fin}
      <tr><td colspan="2" style="border-top:1px solid #ECECEC;padding-top:10px"></td></tr>
      <tr><td style="padding:4px 0;font-weight:700;color:#0F2A44">Valor repassado a você</td>
          <td style="padding:4px 0;text-align:right;font-weight:700;font-size:16px;
              color:#1D7A4C">{_reais(repasse)}</td></tr>
    </table>
    {f'<p style="margin:10px 0 0;font-size:13px;color:#6B6B6B">Forma do repasse: {valores.get("forma_repasse")}</p>' if valores.get("forma_repasse") else ""}

    <h2 style="margin:28px 0 8px;font-size:15px;color:#0F2A44">Histórico do atendimento</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px">{tabela_hist}</table>

    {f'<p style="margin:24px 0 0;font-size:14px;line-height:1.6;white-space:pre-line">{valores.get("observacoes")}</p>' if valores.get("observacoes") else ""}

    <p style="margin:24px 0 0;font-size:13px;color:#6B6B6B;line-height:1.6">
      Este e-mail encerra formalmente o atendimento e segue no mesmo fio de conversa,
      com tudo o que foi tratado desde o primeiro contato. Qualquer dúvida sobre estes
      valores, é só responder esta mensagem.</p>
    <hr style="border:0;border-top:1px solid #ECECEC;margin:26px 0">
    <p style="margin:0;font-size:12px;color:#8A8A8A;line-height:1.7">
      {s.advogado} — {s.oab}</p>
  </div>
 </div></body></html>"""

    ok_mail, erro = False, None
    try:
        fio = fio_do_caso(caso_id)
        novo_id = enviar_email(
            cli.get("email") or "",
            f"[{num}] Prestação de contas — FC Advocacia",
            mensagem, html, responder_a=fio,
        )
        if not fio and novo_id:
            guardar_fio(caso_id, novo_id)
        ok_mail = True
    except Exception as e:
        erro = str(e)

    ok_whats = False
    try:
        phone_id, ddd = escolher_origem(cli.get("whatsapp"))
        enviar_whatsapp(cli.get("whatsapp") or "",
                        _texto_whatsapp(cli.get("nome") or "", num,
                                        "Prestação de contas", mensagem,
                                        f"{s.app_url}/cliente", ddd), phone_id)
        ok_whats = True
    except Exception:
        pass

    agora = datetime.now(_tz.utc).isoformat()
    db.table("prestacoes_contas").update({"enviada_em": agora}) \
      .eq("id", registro["id"]).execute()
    try:
        db.table("casos").update({"estado": "CONCLUIDO", "atualizado_em": agora}) \
          .eq("id", caso_id).execute()
    except Exception:
        pass
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "PORTAL", "autor": "HUMANO",
            "conteudo": f"📑 Prestação de contas do atendimento {num}.\n\n{mensagem}",
        }).execute()
    except Exception:
        pass

    registrar_evento(caso_id, "PRESTACAO_DE_CONTAS",
                     {"prestacao_id": registro["id"], "repasse": repasse,
                      "email": ok_mail, "whatsapp": ok_whats})
    return {"ok": True, "prestacao_id": registro["id"], "repasse_cliente": repasse,
            "enviado_email": ok_mail, "enviado_whatsapp": ok_whats,
            "itens_historico": len(historico),
            **({"erro_email": erro} if erro else {})}


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
