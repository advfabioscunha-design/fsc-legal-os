"""
CAIXA DE ENTRADA — recebe a via assinada que o cliente devolve por e-mail.

O cliente tem dois caminhos para devolver o documento assinado, e os dois
terminam no mesmo lugar (a pasta do caso):

  1. pelo painel da plataforma (botão "Enviar assinado");
  2. **respondendo o próprio e-mail** que recebeu, com o arquivo em anexo.

Este módulo cuida do caminho 2. De tempos em tempos ele abre a caixa do
escritório por IMAP e tenta reconhecer a que caso cada resposta pertence.

RECONHECIMENTO EM TRÊS CAMADAS (da mais forte para a mais tolerante) —
porque na prática o cliente nem sempre responde o e-mail original: às
vezes ele encaminha, às vezes escreve um e-mail novo, às vezes o celular
corta o assunto.

  1. REFERÊNCIA  `FSCDOC-xxxxxxxx`  — vai no assunto do e-mail que enviamos.
  2. NÚMERO DE ATENDIMENTO `FSC-2026-0015` — também vai no assunto e
     sobrevive ao "Re:", ao encaminhamento e à citação no corpo.
  3. REMETENTE — se o e-mail veio de um endereço cadastrado de cliente e
     esse cliente tem documentos aguardando assinatura, o anexo é dele.

Segurança: anexo vindo de endereço que não é o do cliente daquele caso NÃO
é arquivado como assinado — vai para conferência humana. É o mesmo cuidado
de sempre conferir quem mandou antes de juntar aos autos. E-mail saído da
própria caixa do escritório é ignorado.

Idempotência: cada mensagem processada fica registrada pelo Message-ID, de
modo que a rotina pode varrer também mensagens já lidas sem duplicar nada.
"""
from __future__ import annotations

import email
import imaplib
import re
import uuid
from datetime import datetime, timedelta, timezone as _tz
from email.header import decode_header, make_header

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

# tipos de arquivo que aceitamos como via assinada
EXTENSOES_OK = (".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".heic")
PADRAO_REF = re.compile(r"FSCDOC-([0-9a-f]{8})", re.I)
PADRAO_ATENDIMENTO = re.compile(r"FSC-\d{4}-\d{3,6}", re.I)
# anexos que são enchimento do próprio e-mail, não documento do cliente
LIXO = re.compile(r"^(icon|logo|image\d*|imagem\d*|assinatura|signature)\.", re.I)
TAMANHO_MINIMO = 3 * 1024      # abaixo disso é ícone, não documento


def novo_token() -> str:
    return uuid.uuid4().hex[:8]


def referencia(token: str) -> str:
    return f"FSCDOC-{token}"


def _texto(cabecalho) -> str:
    try:
        return str(make_header(decode_header(cabecalho or "")))
    except Exception:
        return str(cabecalho or "")


def _remetente(msg) -> str:
    bruto = _texto(msg.get("From"))
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", bruto)
    return (m.group(0) if m else bruto).strip().lower()


def _corpo_texto(msg) -> str:
    partes = []
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and not p.get_filename():
                try:
                    partes.append(p.get_payload(decode=True).decode(
                        p.get_content_charset() or "utf-8", "ignore"))
                except Exception:
                    pass
    else:
        try:
            partes.append(msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", "ignore"))
        except Exception:
            pass
    return "\n".join(partes)


def _anexos(msg) -> list[tuple[str, bytes, str]]:
    """Só o que é documento de verdade: descarta imagem embutida na
    assinatura do e-mail, ícone e arquivo minúsculo."""
    saida = []
    for p in msg.walk():
        nome = _texto(p.get_filename())
        if not nome or not nome.lower().endswith(EXTENSOES_OK):
            continue
        if LIXO.match(nome.rsplit("/", 1)[-1]):
            continue
        # imagem embutida no corpo (Content-ID) não é anexo do cliente
        if p.get("Content-ID") and "attachment" not in \
                (p.get("Content-Disposition") or "").lower():
            continue
        try:
            dados = p.get_payload(decode=True)
        except Exception:
            continue
        if dados and len(dados) >= TAMANHO_MINIMO:
            saida.append((nome, dados, p.get_content_type()))
    return saida


# ── Memória das mensagens já processadas ────────────────────────
def _ja_processado(message_id: str) -> bool:
    if not message_id:
        return False
    db = get_db()
    try:
        r = db.table("emails_lidos").select("message_id") \
              .eq("message_id", message_id).limit(1).execute().data
        return bool(r)
    except Exception:
        return False


def _marcar_processado(message_id: str, caso_id: str | None, resumo: str) -> None:
    if not message_id:
        return
    try:
        get_db().table("emails_lidos").insert({
            "message_id": message_id[:400], "caso_id": caso_id, "resumo": resumo[:300],
        }).execute()
    except Exception:
        pass


# ── Camadas de reconhecimento ───────────────────────────────────
def _por_referencia(alvo: str) -> list[dict]:
    m = PADRAO_REF.search(alvo)
    if not m:
        return []
    try:
        return get_db().table("documentos_assinatura").select("*") \
                 .eq("email_token", m.group(1).lower()).execute().data or []
    except Exception:
        return []


def _por_numero_atendimento(alvo: str) -> list[dict]:
    m = PADRAO_ATENDIMENTO.search(alvo)
    if not m:
        return []
    db = get_db()
    try:
        caso = db.table("casos").select("id") \
                 .eq("numero_atendimento", m.group(0).upper()) \
                 .limit(1).execute().data
        if not caso:
            return []
        return db.table("documentos_assinatura").select("*") \
                 .eq("caso_id", caso[0]["id"]).execute().data or []
    except Exception:
        return []


def _por_remetente(de: str) -> list[dict]:
    """Último recurso: e-mail de cliente cadastrado que tem documento
    aguardando assinatura. Só vale quando houver exatamente um caso
    pendente — havendo dois, mandamos conferir em vez de adivinhar."""
    db = get_db()
    try:
        cli = db.table("clientes").select("id").ilike("email", de).execute().data or []
        if not cli:
            return []
        ids = [c["id"] for c in cli]
        casos = db.table("casos").select("id").in_("cliente_id", ids).execute().data or []
        if not casos:
            return []
        docs = db.table("documentos_assinatura").select("*") \
                 .in_("caso_id", [c["id"] for c in casos]) \
                 .eq("status", "ENVIADO").execute().data or []
        if len({d["caso_id"] for d in docs}) != 1:
            return []
        return docs
    except Exception:
        return []


def _identificar(msg, alvo: str, de: str) -> tuple[list[dict], str]:
    for achar, como in ((lambda: _por_referencia(alvo), "referência"),
                        (lambda: _por_numero_atendimento(alvo), "nº de atendimento"),
                        (lambda: _por_remetente(de), "remetente cadastrado")):
        docs = achar()
        if docs:
            return docs, como
    return [], ""


# ── Arquivamento ────────────────────────────────────────────────
def _guardar(doc: dict, nome: str, dados: bytes, mime: str, remetente: str,
             conferido: bool) -> str:
    s = get_settings()
    db = get_db()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", nome.rsplit("/", 1)[-1]) or "assinado"
    pasta = "assinados" if conferido else "assinados_a_conferir"
    path = f"{doc['caso_id']}/{pasta}/{uuid.uuid4().hex}_{safe}"
    db.storage.from_(s.bucket_documentos).upload(
        path, dados, {"content-type": mime or "application/octet-stream",
                      "upsert": "true"},
    )
    obs = (f"{doc['titulo']} (assinado, recebido por e-mail)" if conferido
           else f"{doc['titulo']} (recebido por e-mail de {remetente} — CONFERIR REMETENTE)")
    linha = {"caso_id": doc["caso_id"], "tipo": f"ASSINADO_{doc['tipo']}",
             "storage_path": path, "status": "RECEBIDO", "observacao": obs}
    try:
        linha["enviado_por"] = "CLIENTE"
        db.table("documentos").insert(linha).execute()
    except Exception:
        linha.pop("enviado_por", None)
        db.table("documentos").insert(linha).execute()
    return path


def _marcar_assinados(pendentes: list[dict], caminhos: list[str]) -> None:
    db = get_db()
    agora = datetime.now(_tz.utc).isoformat()
    for i, d in enumerate(pendentes):
        db.table("documentos_assinatura").update({
            "status": "ASSINADO", "assinado_em": agora, "atualizado_em": agora,
            "assinado_url": caminhos[i] if i < len(caminhos) else caminhos[0],
        }).eq("id", d["id"]).execute()


def _avisar_chat(caso_id: str, titulos: list[str], conferido: bool, remetente: str,
                 arquivos: list[str], completo: bool, faltam: int) -> None:
    db = get_db()
    lista = ", ".join(arquivos)
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "PORTAL", "autor": "CLIENTE",
            "conteudo": f"✍ Enviei por e-mail os documentos assinados ({lista}).",
        }).execute()
        if conferido and completo:
            db.table("mensagens").insert({
                "caso_id": caso_id, "canal": "PORTAL", "autor": "AGENTE",
                "conteudo": "Recebemos os seus documentos assinados por e-mail. "
                            "Muito obrigado! Já estão arquivados no seu processo.",
            }).execute()
        elif conferido:
            db.table("mensagens").insert({
                "caso_id": caso_id, "canal": "PORTAL", "autor": "AGENTE",
                "conteudo": f"Recebemos {len(arquivos)} documento(s) assinado(s) por "
                            f"e-mail — obrigado! Ainda {'falta' if faltam == 1 else 'faltam'} "
                            f"{faltam} para concluirmos esta etapa.",
            }).execute()
        else:
            db.table("mensagens").insert({
                "caso_id": caso_id, "canal": "CRM", "autor": "HUMANO",
                "conteudo": f"⚠ Chegou um arquivo por e-mail de {remetente}, que NÃO é o "
                            f"endereço cadastrado do cliente. O arquivo foi guardado em "
                            f"'assinados_a_conferir' e o documento segue pendente "
                            f"até a conferência.",
            }).execute()
    except Exception:
        pass


def _liberar_producao(caso_id: str) -> None:
    db = get_db()
    try:
        pend = db.table("documentos_assinatura").select("id") \
                 .eq("caso_id", caso_id).eq("status", "ENVIADO").execute().data or []
        if not pend:
            db.table("casos").update({
                "aguardando_cliente": False, "aguardando_desc": None,
                "atualizado_em": datetime.now(_tz.utc).isoformat(),
            }).eq("id", caso_id).execute()
    except Exception:
        pass


# ── Rotina principal ────────────────────────────────────────────
def ler_respostas(limite: int = 60, dias: int = 21) -> dict:
    """Varre a caixa do escritório e arquiva as vias assinadas que chegaram
    por e-mail. Roda sozinha a cada 10 minutos.

    Varre TODAS as mensagens recentes (não só as não lidas), porque o
    advogado costuma abrir o e-mail antes da rotina rodar. O controle de
    repetição é feito pelo Message-ID, não pelo flag de lido."""
    s = get_settings()
    if not (s.smtp_usuario and s.smtp_senha):
        return {"ok": False, "motivo": "e-mail não configurado"}

    db = get_db()
    resultado = {"lidas": 0, "arquivadas": 0, "a_conferir": 0,
                 "sem_referencia": 0, "ignoradas": 0, "erros": []}
    try:
        M = imaplib.IMAP4_SSL(s.imap_host, s.imap_porta, timeout=40)
        M.login(s.smtp_usuario, s.smtp_senha)
        M.select(s.imap_pasta)
    except Exception as e:
        return {"ok": False, "motivo": f"não foi possível abrir a caixa: {e}"}

    try:
        desde = (datetime.now(_tz.utc) - timedelta(days=dias)).strftime("%d-%b-%Y")
        tipo, dados = M.search(None, f'(SINCE {desde})')
        ids = (dados[0].split() if dados and dados[0] else [])[-limite:]
        for num in ids:
            try:
                _, bruto = M.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(bruto[0][1])
                mid = (msg.get("Message-ID") or "").strip()
                if _ja_processado(mid):
                    continue
                resultado["lidas"] += 1

                de = _remetente(msg)
                # nunca processa o que a própria plataforma mandou
                if de == (s.smtp_usuario or "").lower():
                    resultado["ignoradas"] += 1
                    continue

                anexos = _anexos(msg)
                if not anexos:
                    continue          # sem arquivo não há o que arquivar

                alvo = f"{_texto(msg.get('Subject'))}\n{_corpo_texto(msg)}"
                docs, como = _identificar(msg, alvo, de)
                if not docs:
                    resultado["sem_referencia"] += 1
                    continue

                pendentes = [d for d in docs if d["status"] != "ASSINADO"] or docs
                caso_id = pendentes[0]["caso_id"]

                caso = db.table("casos").select("clientes(email)") \
                         .eq("id", caso_id).single().execute().data
                email_cli = ((caso.get("clientes") or {}).get("email") or "").lower()
                conferido = bool(email_cli) and de == email_cli

                caminhos, nomes = [], []
                for nome, conteudo, mime in anexos:
                    caminhos.append(_guardar(pendentes[0], nome, conteudo, mime,
                                             de, conferido))
                    nomes.append(nome)

                completo = conferido and len(anexos) >= len(pendentes)
                if completo:
                    _marcar_assinados(pendentes, caminhos)
                    _liberar_producao(caso_id)
                    resultado["arquivadas"] += 1
                else:
                    resultado["a_conferir"] += 1

                _avisar_chat(caso_id, [d["titulo"] for d in pendentes], conferido,
                             de, nomes, completo,
                             max(len(pendentes) - len(anexos), 0))

                registrar_evento(caso_id, "ASSINADO_RECEBIDO_EMAIL",
                                 {"de": de, "reconhecido_por": como,
                                  "conferido": conferido, "completo": completo,
                                  "pendentes": len(pendentes), "arquivos": nomes})
                _marcar_processado(mid, caso_id,
                                   f"{como}: {len(nomes)} anexo(s) de {de}")
                M.store(num, "+FLAGS", "\\Seen")
            except Exception as e:
                resultado["erros"].append(str(e)[:200])
    finally:
        try:
            M.close()
            M.logout()
        except Exception:
            pass

    return {"ok": True, **resultado}
