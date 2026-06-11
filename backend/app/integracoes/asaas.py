"""Asaas — cobrança (Pix/boleto/cartão) com confirmação via webhook."""
import httpx
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento


def _headers():
    return {"access_token": get_settings().asaas_api_key}


def criar_cobranca(caso_id: str, valor: float, descricao: str) -> dict:
    """Cria cliente (se preciso) e cobrança no Asaas; envia link ao cliente."""
    s = get_settings()
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
    cli = caso["clientes"]

    with httpx.Client(base_url=s.asaas_base_url, headers=_headers(), timeout=30) as http:
        # cliente Asaas
        r = http.get("/customers", params={"cpfCnpj": cli.get("cpf_cnpj") or ""})
        achados = r.json().get("data", [])
        if achados:
            customer_id = achados[0]["id"]
        else:
            r = http.post("/customers", json={
                "name": cli["nome"], "cpfCnpj": cli.get("cpf_cnpj"),
                "email": cli.get("email"), "mobilePhone": cli.get("whatsapp"),
            })
            r.raise_for_status()
            customer_id = r.json()["id"]

        # cobrança (UNDEFINED = cliente escolhe Pix/boleto/cartão no link)
        r = http.post("/payments", json={
            "customer": customer_id, "billingType": "UNDEFINED",
            "value": valor, "description": descricao,
            "externalReference": caso_id,
        })
        r.raise_for_status()
        cobranca = r.json()

    db.table("casos").update({"cobranca_asaas_id": cobranca["id"]}).eq("id", caso_id).execute()
    registrar_evento(caso_id, "COBRANCA_CRIADA",
                     {"asaas_id": cobranca["id"], "valor": valor,
                      "link": cobranca.get("invoiceUrl")})
    return {"link_pagamento": cobranca.get("invoiceUrl"), "asaas_id": cobranca["id"]}


def processar_webhook(payload: dict) -> dict:
    """Webhook Asaas: pagamento confirmado → caso avança para COLETA_DOCS."""
    from ..agentes.orquestrador import mudar_estado
    evento = payload.get("event", "")
    pagamento = payload.get("payment", {}) or {}
    caso_id = pagamento.get("externalReference")

    registrar_evento(caso_id, "WEBHOOK_ASAAS", {"event": evento, "id": pagamento.get("id")})

    if evento in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED") and caso_id:
        from datetime import datetime, timezone
        get_db().table("casos").update(
            {"pagamento_confirmado_em": datetime.now(timezone.utc).isoformat()}
        ).eq("id", caso_id).execute()
        mudar_estado(caso_id, "COLETA_DOCS", motivo="Pagamento confirmado (Asaas)")

        # avisa o cliente e já pede o primeiro documento
        from .whatsapp import enviar_para_cliente
        try:
            enviar_para_cliente(caso_id,
                "Pagamento confirmado, obrigado! 🎉 Agora vamos reunir os documentos "
                "do seu caso. Já te explico o primeiro que preciso.")
        except Exception:
            pass
        return {"ok": True, "avancou": "COLETA_DOCS"}
    return {"ok": True, "ignorado": evento}
