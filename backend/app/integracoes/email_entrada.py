"""
CAIXA DE ENTRADA — recebe a via assinada que o cliente devolve por e-mail.

O cliente tem dois caminhos para devolver o documento assinado, e os dois
terminam no mesmo lugar (a pasta do caso):

  1. pelo painel da plataforma (botão "Enviar assinado");
  2. **respondendo o próprio e-mail** que recebeu, com o arquivo em anexo.

Este módulo cuida do caminho 2. De tempos em tempos ele abre a caixa do
escritório por IMAP, procura respostas que tragam a REFERÊNCIA do documento
(`FSCDOC-xxxxxxxx`, que vai no assunto), confere se o remetente é mesmo o
cliente daquele caso e guarda os anexos.

Segurança: anexo vindo de endereço diferente do cadastrado NÃO é arquivado
automaticamente — o caso é sinalizado para conferência humana. É o mesmo
cuidado que se tem ao receber uma procuração por e-mail: confirmar quem
mandou antes de juntar aos autos.
"""
from __future__ import annotations

import email
import imaplib
import re
import uuid
from datetime import datetime, timezone as _tz
from email.header import decode_header, make_header

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

# tipos de arquivo que aceitamos como via assinada
EXTENSOES_OK = (".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".heic")
PADRAO_REF = re.compile(r"FSCDOC-([0-9a-f]{8})", re.I)


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
    saida = []
    for p in msg.walk():
        nome = _texto(p.get_filename())
        if not nome:
            continue
        if not nome.lower().endswith(EXTENSOES_OK):
            continue
        try:
            dados = p.get_payload(decode=True)
        except Exception:
            continue
        if dados:
            saida.append((nome, dados, p.get_content_type()))
    return saida


# ── Arquivamento ────────────────────────────────────────────────
def _guardar(doc: dict, nome: str, dados: bytes, mime: str, remetente: str,
             conferido: bool, marcar_assinado: bool = True) -> None:
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

    if conferido and marcar_assinado:
        agora = datetime.now(_tz.utc).isoformat()
        db.table("documentos_assinatura").update({
            "status": "ASSINADO", "assinado_em": agora,
            "assinado_url": path, "atualizado_em": agora,
        }).eq("id", doc["id"]).execute()


def _avisar_chat(doc: dict, conferido: bool, remetente: str, arquivos: list[str],
                 parcial: bool = False, faltam: int = 0) -> None:
    db = get_db()
    lista = ", ".join(arquivos)
    try:
        db.table("mensagens").insert({
            "caso_id": doc["caso_id"], "canal": "PORTAL", "autor": "CLIENTE",
            "conteudo": f"✍ Enviei por e-mail o {doc['titulo']} assinado ({lista}).",
        }).execute()
        if conferido and not parcial:
            db.table("mensagens").insert({
                "caso_id": doc["caso_id"], "canal": "PORTAL", "autor": "AGENTE",
                "conteudo": "Recebemos os seus documentos assinados por e-mail. "
                            "Muito obrigado! Já estão arquivados no seu processo.",
            }).execute()
        elif parcial:
            db.table("mensagens").insert({
                "caso_id": doc["caso_id"], "canal": "PORTAL", "autor": "AGENTE",
                "conteudo": f"Recebemos {len(arquivos)} documento(s) assinado(s) por "
                            f"e-mail — obrigado! Ainda {'falta' if faltam == 1 else 'faltam'} "
                            f"{faltam} para concluirmos esta etapa.",
            }).execute()
        else:
            db.table("mensagens").insert({
                "caso_id": doc["caso_id"], "canal": "CRM", "autor": "HUMANO",
                "conteudo": f"⚠ Chegou um arquivo por e-mail de {remetente}, que NÃO é o "
                            f"endereço cadastrado do cliente. O arquivo foi guardado em "
                            f"'assinados_a_conferir' e o documento segue como pendente "
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
def ler_respostas(limite: int = 30) -> dict:
    """Varre a caixa do escritório e arquiva as vias assinadas que chegaram
    por e-mail. Roda sozinha a cada 10 minutos."""
    s = get_settings()
    if not (s.smtp_usuario and s.smtp_senha):
        return {"ok": False, "motivo": "e-mail não configurado"}

    db = get_db()
    resultado = {"lidas": 0, "arquivadas": 0, "a_conferir": 0,
                 "sem_referencia": 0, "erros": []}
    try:
        M = imaplib.IMAP4_SSL(s.imap_host, s.imap_porta, timeout=40)
        M.login(s.smtp_usuario, s.smtp_senha)
        M.select(s.imap_pasta)
    except Exception as e:
        return {"ok": False, "motivo": f"não foi possível abrir a caixa: {e}"}

    try:
        tipo, dados = M.search(None, "UNSEEN")
        ids = (dados[0].split() if dados and dados[0] else [])[-limite:]
        for num in ids:
            try:
                _, bruto = M.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(bruto[0][1])
                resultado["lidas"] += 1

                alvo = f"{_texto(msg.get('Subject'))}\n{_corpo_texto(msg)}"
                m = PADRAO_REF.search(alvo)
                if not m:
                    resultado["sem_referencia"] += 1
                    continue          # não é resposta nossa: deixa na caixa

                token = m.group(1).lower()
                try:
                    docs = db.table("documentos_assinatura").select("*") \
                             .eq("email_token", token).execute().data or []
                except Exception:
                    docs = []
                pendentes = [d for d in docs if d["status"] != "ASSINADO"]
                if not docs:
                    resultado["sem_referencia"] += 1
                    continue
                doc = pendentes[0] if pendentes else docs[0]

                anexos = _anexos(msg)
                if not anexos:
                    continue          # resposta sem arquivo: ignora, segue pendente

                caso = db.table("casos").select("clientes(email)") \
                         .eq("id", doc["caso_id"]).single().execute().data
                email_cli = ((caso.get("clientes") or {}).get("email") or "").lower()
                de = _remetente(msg)
                conferido = bool(email_cli) and de == email_cli

                # os arquivos entram uma vez na pasta do caso
                nomes = []
                for nome, conteudo, mime in anexos:
                    _guardar(doc, nome, conteudo, mime, de, conferido,
                             marcar_assinado=False)
                    nomes.append(nome)

                # quando o envio foi em lote, só damos por assinado se vierem
                # pelo menos tantos arquivos quanto documentos pendentes
                completo = conferido and len(anexos) >= len(pendentes)
                if completo:
                    agora = datetime.now(_tz.utc).isoformat()
                    for d in pendentes:
                        db.table("documentos_assinatura").update({
                            "status": "ASSINADO", "assinado_em": agora,
                            "atualizado_em": agora,
                        }).eq("id", d["id"]).execute()

                _avisar_chat(doc, conferido, de, nomes,
                             parcial=(conferido and not completo),
                             faltam=max(len(pendentes) - len(anexos), 0))
                if completo:
                    _liberar_producao(doc["caso_id"])
                    resultado["arquivadas"] += 1
                else:
                    resultado["a_conferir"] += 1

                registrar_evento(doc["caso_id"], "ASSINADO_RECEBIDO_EMAIL",
                                 {"documento_id": doc["id"], "de": de,
                                  "conferido": conferido, "completo": completo,
                                  "pendentes": len(pendentes), "arquivos": nomes})
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
