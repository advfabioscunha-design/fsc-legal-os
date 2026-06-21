"""
MÓDULO 1 — Fundação omnichannel do WhatsApp.
Responsabilidades (somente estas):
  1) Verificar o webhook do Meta (GET) e receber mensagens (POST).
  2) Gerenciar a sessão/contexto no Supabase (cliente + histórico).
  3) Espelhar uma resposta (send_whatsapp_message) de volta ao cliente.

NÃO faz CRM, petição nem pagamento. A resposta é uma IA básica (ou simulada).
"""
import httpx
import anthropic
from ..core.config import get_settings
from ..core.db import get_db

GRAPH = "https://graph.facebook.com/v21.0"

_cli = None
def _claude():
    global _cli
    if _cli is None:
        _cli = anthropic.Anthropic(api_key=get_settings().claude_api_key)
    return _cli


# ── 1. Verificação do token (GET do Meta) ────────────────────────
def verificar_webhook(mode: str | None, token: str | None, challenge: str | None):
    """Retorna o challenge se o token bater; senão None (rota responde 403)."""
    s = get_settings()
    if mode == "subscribe" and token and token == s.whatsapp_verify_token:
        return challenge
    return None


# ── 1. Extração da mensagem (POST do Meta) ───────────────────────
def extrair_mensagem(payload: dict):
    """Devolve (numero, texto, nome) ou (None, None, None) se não houver texto."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        numero = msg.get("from")
        texto = (msg.get("text") or {}).get("body", "")
        nome = ""
        try:
            nome = value["contacts"][0]["profile"]["name"]
        except (KeyError, IndexError, TypeError):
            nome = ""
        return numero, texto, nome
    except (KeyError, IndexError, TypeError):
        return None, None, None


# ── 2. Gerenciador de contexto (Supabase) ────────────────────────
def gerenciar_contexto(numero: str, nome: str = ""):
    """Lookup do cliente por número. Cria se novo. Devolve (cliente, historico)."""
    db = get_db()
    cliente = None
    try:
        cliente = db.table("clientes").select("id,nome,whatsapp") \
            .eq("whatsapp", numero).maybe_single().execute().data
    except Exception:
        cliente = None

    if not cliente:
        try:
            cliente = db.table("clientes").insert({
                "nome": nome or f"WhatsApp {numero[-4:]}",
                "whatsapp": numero, "origem": "WHATSAPP",
            }).execute().data[0]
        except Exception as e:
            cliente = {"id": None, "erro_criacao": str(e)}

    historico = []
    try:
        msgs = db.table("wa_mensagens").select("autor,conteudo") \
            .eq("numero", numero).order("criado_em").limit(20).execute().data
        historico = [
            {"role": "user" if m["autor"] == "CLIENTE" else "assistant", "content": m["conteudo"]}
            for m in msgs
        ]
    except Exception:
        historico = []

    return cliente, historico


def registrar_mensagem(numero: str, autor: str, conteudo: str):
    """Grava uma linha no log da conversa (não derruba o fluxo se falhar)."""
    try:
        get_db().table("wa_mensagens").insert(
            {"numero": numero, "autor": autor, "conteudo": conteudo}
        ).execute()
    except Exception:
        pass


# ── IA básica (resposta) — placeholder do Módulo 1 ───────────────
SYSTEM_BASICO = (
    "Você é o atendente virtual da FC Advocacia no WhatsApp. Responda de forma "
    "educada, acolhedora e breve. (Módulo de fundação — apenas conversa básica.)"
)

def gerar_resposta(historico: list, texto: str) -> str:
    s = get_settings()
    if not s.claude_api_key:
        return f'Recebi sua mensagem: "{texto}". (resposta simulada — IA ainda não configurada)'
    try:
        msgs = list(historico or []) + [{"role": "user", "content": texto}]
        resp = _claude().messages.create(
            model=s.claude_model_rapido, max_tokens=600,
            system=SYSTEM_BASICO, messages=msgs,
        )
        out = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        return out or "Pode repetir, por favor?"
    except Exception:
        return "Recebi sua mensagem! Já te respondo. 🙏"


# ── 3. Espelhamento simples (envio via API do Meta) ──────────────
def send_whatsapp_message(numero: str, texto: str) -> dict:
    s = get_settings()
    if not (s.whatsapp_token and s.whatsapp_phone_id):
        return {"ok": False, "erro": "WhatsApp não configurado (WHATSAPP_TOKEN/WHATSAPP_PHONE_ID)"}
    try:
        r = httpx.post(
            f"{GRAPH}/{s.whatsapp_phone_id}/messages",
            headers={"Authorization": f"Bearer {s.whatsapp_token}"},
            json={"messaging_product": "whatsapp", "to": numero,
                  "type": "text", "text": {"body": texto[:4000]}},
            timeout=30,
        )
        r.raise_for_status()
        return {"ok": True, "resp": r.json()}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ── Orquestração do POST ─────────────────────────────────────────
def processar_mensagem(payload: dict) -> dict:
    numero, texto, nome = extrair_mensagem(payload)
    if not numero or not texto:
        return {"ok": True, "ignorado": "sem mensagem de texto"}
    try:
        cliente, historico = gerenciar_contexto(numero, nome)
        registrar_mensagem(numero, "CLIENTE", texto)
        resposta = gerar_resposta(historico, texto)
        registrar_mensagem(numero, "AGENTE", resposta)
        envio = send_whatsapp_message(numero, resposta)
        return {"ok": True, "numero": numero, "cliente_id": (cliente or {}).get("id"),
                "enviado": envio.get("ok"), "erro_envio": envio.get("erro")}
    except Exception as e:
        return {"ok": False, "erro": str(e)}
