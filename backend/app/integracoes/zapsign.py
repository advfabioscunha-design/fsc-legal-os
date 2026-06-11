"""ZapSign — contrato de honorários com assinatura digital + webhook."""
import httpx
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

MODELO_CONTRATO = """CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS

CONTRATADO: {advogado}, {oab}, FSC ADVOCACIA
            (e-mail: {email_escritorio}).
CONTRATANTE: {nome}, CPF {cpf}, e-mail {email}.

1. DO OBJETO: prestação de serviços advocatícios na demanda de natureza
{grupo}, conforme tese {tese_id} — {tese_titulo}.

2. DOS HONORÁRIOS: {honorarios}.

3. O CONTRATANTE declara ciência de que resultados judiciais não são
garantidos, obrigando-se o CONTRATADO aos melhores esforços técnicos.
"""


def enviar_contrato(caso_id: str) -> dict:
    """Gera o contrato a partir do caso/tese e envia via ZapSign."""
    s = get_settings()
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
    cli = caso["clientes"]
    tese = {}
    if caso.get("tese_id"):
        tese = db.table("teses").select("titulo").eq("id", caso["tese_id"]) \
                 .maybe_single().execute().data or {}

    corpo = MODELO_CONTRATO.format(
        advogado=s.advogado, oab=s.oab,
        email_escritorio=s.email_escritorio,
        nome=cli["nome"], cpf=cli.get("cpf_cnpj") or "[A PREENCHER]",
        email=cli.get("email") or "", grupo=caso.get("grupo") or "",
        tese_id=caso.get("tese_id") or "", tese_titulo=tese.get("titulo", ""),
        honorarios=caso.get("honorarios_valor") or "[CONFORME PROPOSTA ACEITA]",
    )

    with httpx.Client(base_url=s.zapsign_base_url, timeout=30,
                      headers={"Authorization": f"Bearer {s.zapsign_api_token}"}) as http:
        r = http.post("/docs/", json={
            "name": f"Contrato Honorários - {cli['nome']}",
            "raw_text": corpo,
            "external_id": caso_id,
            "signers": [{
                "name": cli["nome"], "email": cli.get("email"),
                "phone_number": cli.get("whatsapp"),
                "auth_mode": "assinaturaTela",
                "send_automatic_email": True, "send_automatic_whatsapp": True,
            }],
        })
        r.raise_for_status()
        doc = r.json()

    db.table("casos").update({"contrato_zapsign_id": doc.get("token")}).eq("id", caso_id).execute()
    registrar_evento(caso_id, "CONTRATO_ENVIADO", {"zapsign_token": doc.get("token")})
    return {"zapsign_token": doc.get("token"),
            "link_assinatura": (doc.get("signers") or [{}])[0].get("sign_url")}


def processar_webhook(payload: dict) -> dict:
    """Webhook ZapSign: contrato assinado → cria cobrança Asaas e avança."""
    from ..agentes.orquestrador import mudar_estado
    from .asaas import criar_cobranca

    caso_id = payload.get("external_id")
    status = payload.get("status", "")
    registrar_evento(caso_id, "WEBHOOK_ZAPSIGN", {"status": status})

    if status == "signed" and caso_id:
        from datetime import datetime, timezone
        db = get_db()
        db.table("casos").update(
            {"contrato_assinado_em": datetime.now(timezone.utc).isoformat()}
        ).eq("id", caso_id).execute()
        caso = mudar_estado(caso_id, "PAGAMENTO", motivo="Contrato assinado (ZapSign)")

        # honorários de entrada: gera cobrança automaticamente
        valor = _valor_entrada(caso)
        link = None
        if valor:
            link = criar_cobranca(caso_id, valor,
                                  "Honorários advocatícios - FSC ADVOCACIA")["link_pagamento"]
        from .whatsapp import enviar_para_cliente
        try:
            msg = "Contrato assinado com sucesso! ✅"
            if link:
                msg += f"\nAqui está o link para o pagamento: {link}"
            enviar_para_cliente(caso_id, msg)
        except Exception:
            pass
        return {"ok": True, "avancou": "PAGAMENTO", "cobranca": link}
    return {"ok": True, "ignorado": status}


def _valor_entrada(caso: dict) -> float | None:
    """Extrai valor numérico de entrada do campo honorarios_valor, se houver."""
    import re
    bruto = str(caso.get("honorarios_valor") or "")
    m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+(?:\.\d{2})?)", bruto)
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None
