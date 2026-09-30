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

        # O CLIENTE SABE PELOS TRÊS CANAIS, NÃO POR UM
        #
        # Isto avisava só pelo WhatsApp. Quem pagou por outro caminho,
        # ou não tem WhatsApp cadastrado, não recebia nada: pagava e
        # ficava no escuro, justamente no momento em que mais precisa
        # de confirmação. A central de avisos já sabe o e-mail, o
        # número, o fio do assunto e o número do atendimento, e
        # registra a ciência.
        texto = ("Pagamento confirmado, obrigado pela confiança. "
                 "A partir de agora o seu caso está em andamento e você "
                 "acompanha cada passo pela plataforma. O próximo passo é "
                 "reunir os documentos, e já vamos te dizer qual é o "
                 "primeiro de que precisamos.")
        try:
            from . import avisos
            avisos.notificar(caso_id, "PAGAMENTO", "Pagamento confirmado", texto)
        except Exception as e:
            print(f"[asaas] aviso de pagamento não saiu: {e}")

        # E aparece também na conversa, que é onde o cliente volta para
        # olhar depois. Aviso que só existe no e-mail some na caixa de
        # entrada de quem recebe cinquenta por dia.
        try:
            get_db().table("mensagens").insert({
                "caso_id": caso_id, "canal": "PORTAL", "autor": "AGENTE",
                "conteudo": texto,
            }).execute()
        except Exception as e:
            print(f"[asaas] confirmação não registrada na conversa: {e}")

        return {"ok": True, "avancou": "COLETA_DOCS"}
    return {"ok": True, "ignorado": evento}
