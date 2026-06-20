"""
Escavador — monitoramento de processos e recebimento de intimações.

Sincroniza com os dados que já vêm do CNJ (casos.numero_processo):
- criar_monitoramento(): registra um processo/OAB para o Escavador vigiar.
- processar_webhook(): recebe os callbacks do Escavador, normaliza e grava em
  'intimacoes' de forma IDEMPOTENTE (evento_id único) — insert rápido, sem IA
  no caminho da requisição (regra do webhook: responder rápido).

OBS: os caminhos/campos exatos da API podem variar conforme o plano/versão do
Escavador. O cliente abaixo é tolerante e fácil de ajustar (base_url + token via
.env). A normalização do webhook aceita vários formatos de payload.
"""
import httpx
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento


def _headers() -> dict:
    s = get_settings()
    return {
        "Authorization": f"Bearer {s.escavador_api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def criar_monitoramento(numero_processo: str | None = None, oab: str | None = None,
                        tribunal: str | None = None, caso_id: str | None = None) -> dict:
    """Cadastra um monitoramento no Escavador e guarda localmente."""
    s = get_settings()
    db = get_db()

    if numero_processo:
        payload = {"tipo": "processo", "valor": numero_processo}
    elif oab:
        payload = {"tipo": "oab", "valor": oab, "tribunal": tribunal}
    else:
        raise ValueError("Informe numero_processo ou oab para monitorar.")

    escavador_id = None
    erro = None
    if s.escavador_api_token:
        try:
            with httpx.Client(base_url=s.escavador_base_url, headers=_headers(), timeout=30) as http:
                r = http.post("/api/v2/monitoramentos", json=payload)
                if r.status_code < 300:
                    data = r.json()
                    escavador_id = str(data.get("id") or data.get("monitoramento_id") or "")
                else:
                    erro = f"{r.status_code}: {r.text[:200]}"
        except Exception as e:
            erro = str(e)

    row = db.table("monitoramentos").insert({
        "caso_id": caso_id, "numero_processo": numero_processo,
        "oab": oab, "tribunal": tribunal, "escavador_id": escavador_id,
    }).execute().data[0]
    registrar_evento(caso_id, "MONITORAMENTO_CRIADO",
                     {"numero": numero_processo, "oab": oab, "escavador_id": escavador_id, "erro": erro})
    return {**row, "escavador_ok": escavador_id is not None, "erro": erro}


def _eventos_do_payload(payload: dict) -> list:
    for chave in ("movimentacoes", "movimentos", "intimacoes", "data", "items"):
        v = payload.get(chave)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
    return [payload]


def _g(ev: dict, *chaves):
    for k in chaves:
        if ev.get(k):
            return ev.get(k)
    return None


def processar_webhook(payload: dict) -> dict:
    """Normaliza o callback do Escavador e grava em 'intimacoes' (idempotente)."""
    db = get_db()
    novas = 0
    for ev in _eventos_do_payload(payload):
        if not isinstance(ev, dict):
            continue
        evento_id = str(_g(ev, "id", "evento_id", "movimentacao_id") or "") or None
        numero = _g(ev, "numero_processo", "numero_unico", "processo") or payload.get("numero_processo")
        tribunal = _g(ev, "tribunal", "sigla_tribunal") or payload.get("tribunal")
        conteudo = _g(ev, "conteudo", "texto", "descricao", "resumo") or ""
        data_mov = _g(ev, "data", "data_movimento", "data_publicacao", "created_at")

        if evento_id:
            existe = db.table("intimacoes").select("id").eq("evento_id", evento_id).limit(1).execute().data
            if existe:
                continue

        caso_id = None
        if numero:
            c = db.table("casos").select("id").eq("numero_processo", numero).limit(1).execute().data
            if c:
                caso_id = c[0]["id"]

        db.table("intimacoes").insert({
            "caso_id": caso_id, "evento_id": evento_id, "tribunal": tribunal,
            "numero_processo": numero, "conteudo": conteudo,
            "status": "A_RESOLVER", "data_movimento": data_mov, "payload": ev,
        }).execute()
        novas += 1

    registrar_evento(None, "WEBHOOK_ESCAVADOR", {"novas": novas})
    return {"ok": True, "novas": novas}
