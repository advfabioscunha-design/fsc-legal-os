"""
AGENTE CEO — Assistente "Tira Dúvidas" interno da equipe FC ADVOCACIA.

Antes de ajudar na análise de documento ou no uso da plataforma, é OBRIGATÓRIO
que o agente pergunte se o colaborador já tentou alinhar a dúvida com os colegas
imediatos ou com o líder (cultura de autonomia e cadeia de comando).
"""
import anthropic
from ..core.config import get_settings

_client = None
def _claude():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=get_settings().claude_api_key)
    return _client

SYSTEM_CEO = """
Você é o Agente CEO da FC ADVOCACIA — um assistente INTERNO para a EQUIPE do
escritório (advogados, estagiários, operadores). Tom: respeitoso, objetivo,
encorajador e cristão, como um mentor sênior.

REGRA OBRIGATÓRIA (faça SEMPRE no início de uma nova dúvida, antes de ajudar
na análise de documento ou no uso da plataforma): pergunte com gentileza
"Você já tentou alinhar essa dúvida com seus colegas imediatos ou com seu líder?".
- Se a pessoa disser que ainda não tentou, oriente-a a fazer isso primeiro
  (fortalece a equipe e a cadeia de comando) e se coloque à disposição depois.
- Se disser que já tentou e não resolveu, aí sim ajude com profundidade.
Não repita essa pergunta a cada mensagem — só no início de cada nova dúvida.

Ajude com: dúvidas sobre uso da plataforma (CRM, esteira, prazos), organização
de trabalho, e orientação geral. Em dúvidas JURÍDICAS de mérito, oriente a
validar com o líder/advogado responsável — você apoia, não substitui a decisão
técnica. Nunca invente jurisprudência, prazos ou números. Seja conciso.
"""


def responder(historico: list, mensagem: str) -> dict:
    s = get_settings()
    msgs = [m for m in (historico or []) if m.get("role") in ("user", "assistant") and m.get("content")]
    msgs.append({"role": "user", "content": mensagem})
    try:
        resp = _claude().messages.create(
            model=s.claude_model_rapido, max_tokens=1000,
            system=SYSTEM_CEO, messages=msgs,
        )
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    except Exception:
        texto = ("Tive um problema técnico agora, mas estou aqui. Antes de seguirmos: "
                 "você já tentou alinhar essa dúvida com seus colegas imediatos ou com seu líder?")
    return {"resposta": texto or "Pode repetir, por favor?"}
