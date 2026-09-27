"""ZapSign — assinatura digital dos documentos do escritório + webhook.

Dois caminhos entram aqui:

  1) `enviar_documento(documento_id)` — o .docx gerado pelo agente redator
     (contrato, procuração, declaração) já aprovado pelo advogado. É o
     caminho principal: o arquivo sobe para o ZapSign em base64, o cliente
     recebe o link por e-mail e por WhatsApp, e o link também aparece no
     painel dele dentro da plataforma.

  2) `enviar_contrato(caso_id)` — caminho legado, gera um contrato simples
     em texto. Mantido para compatibilidade.
"""
import base64
import httpx
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

MODELO_CONTRATO = """CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS

CONTRATADO: {advogado}, {oab}, FC ADVOCACIA
            (e-mail: {email_escritorio}).
CONTRATANTE: {nome}, CPF {cpf}, e-mail {email}.

1. DO OBJETO: prestação de serviços advocatícios na demanda de natureza
{grupo}, conforme tese {tese_id} — {tese_titulo}.

2. DOS HONORÁRIOS: {honorarios}.

3. O CONTRATANTE declara ciência de que resultados judiciais não são
garantidos, obrigando-se o CONTRATADO aos melhores esforços técnicos.
"""


def _telefone(cli: dict) -> tuple[str, str]:
    """Separa DDI e número, no formato que o ZapSign espera."""
    n = "".join(c for c in (cli.get("whatsapp") or "") if c.isdigit())
    if n.startswith("55") and len(n) > 11:
        return "55", n[2:]
    return "55", n


def enviar_documento(documento_id: str) -> dict:
    """Envia para assinatura um documento já gerado e APROVADO.

    O cliente recebe por e-mail e WhatsApp (pelo próprio ZapSign) e o link
    fica disponível no painel dele, dentro da plataforma.
    """
    from datetime import datetime, timezone
    s = get_settings()
    db = get_db()

    d = db.table("documentos_assinatura").select("*").eq("id", documento_id) \
          .single().execute().data
    if d["status"] not in ("APROVADO", "ENVIADO"):
        raise RuntimeError("O documento precisa ser aprovado pelo advogado antes "
                           "de ir para assinatura.")
    caso = db.table("casos").select("numero_atendimento, clientes(*)") \
             .eq("id", d["caso_id"]).single().execute().data
    cli = caso.get("clientes") or {}
    if not s.zapsign_api_token:
        raise RuntimeError("ZapSign não configurado (ZAPSIGN_API_TOKEN vazio).")

    arquivo = db.storage.from_(s.bucket_documentos).download(d["storage_path"])
    ddi, fone = _telefone(cli)

    corpo = {
        "name": f"{d['titulo']} ({caso.get('numero_atendimento') or ''})".strip(),
        "base64_docx": base64.b64encode(arquivo).decode(),
        "external_id": documento_id,
        "lang": "pt-br",
        "folder_path": f"/FSC/{caso.get('numero_atendimento') or 'casos'}",
        "signers": [{
            "name": cli.get("nome") or "Cliente",
            "email": cli.get("email") or None,
            "phone_country": ddi if fone else None,
            "phone_number": fone or None,
            "auth_mode": "assinaturaTela",
            "send_automatic_email": bool(cli.get("email")),
            "send_automatic_whatsapp": bool(fone),
        }],
    }

    with httpx.Client(base_url=s.zapsign_base_url, timeout=60,
                      headers={"Authorization": f"Bearer {s.zapsign_api_token}"}) as http:
        r = http.post("/docs/", json=corpo)
        if r.status_code >= 400:
            raise RuntimeError(f"ZapSign recusou o envio ({r.status_code}): {r.text[:300]}")
        doc = r.json()

    link = (doc.get("signers") or [{}])[0].get("sign_url")
    db.table("documentos_assinatura").update({
        "status": "ENVIADO", "zapsign_token": doc.get("token"),
        "link_assinatura": link,
        "enviado_em": datetime.now(timezone.utc).isoformat(),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", documento_id).execute()

    # o contrato de honorários também marca a fase do caso
    if d["tipo"] == "CONTRATO":
        db.table("casos").update({"contrato_zapsign_id": doc.get("token")}) \
          .eq("id", d["caso_id"]).execute()

    # aviso na plataforma (e-mail + WhatsApp do escritório) com o link
    try:
        from . import avisos
        avisos.notificar(
            d["caso_id"], "CONTRATO",
            f"{d['titulo']} pronto para assinatura",
            "Preparamos o seu documento e ele já está disponível para assinatura "
            "digital. É rápido: abra o link, confira o conteúdo e assine na tela "
            "do seu próprio celular ou computador.\n\n"
            f"Link para assinar: {link}",
        )
    except Exception:
        pass

    # registra na conversa, para o cliente achar pelo chat também
    try:
        db.table("mensagens").insert({
            "caso_id": d["caso_id"], "canal": "PORTAL", "autor": "HUMANO",
            "conteudo": f"📄 {d['titulo']} disponível para assinatura digital.\n{link}",
        }).execute()
    except Exception:
        pass

    registrar_evento(d["caso_id"], "DOCUMENTO_ENVIADO_ASSINATURA",
                     {"documento_id": documento_id, "tipo": d["tipo"],
                      "zapsign_token": doc.get("token")})
    return {"ok": True, "link_assinatura": link, "zapsign_token": doc.get("token")}


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


def _webhook_documento(documento_id: str, payload: dict) -> dict | None:
    """Trata o webhook quando o external_id é um documento gerado pelo agente.
    Devolve None se o id não for de um documento (aí o fluxo legado assume)."""
    from datetime import datetime, timezone
    db = get_db()
    try:
        d = db.table("documentos_assinatura").select("*").eq("id", documento_id) \
              .maybe_single().execute().data
    except Exception:
        d = None
    if not d:
        return None

    url_assinado = payload.get("signed_file") or payload.get("original_file")
    db.table("documentos_assinatura").update({
        "status": "ASSINADO",
        "assinado_em": datetime.now(timezone.utc).isoformat(),
        "assinado_url": url_assinado,
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", documento_id).execute()

    # o PDF assinado entra na pasta do caso, junto dos demais documentos
    if url_assinado:
        try:
            db.table("documentos").insert({
                "caso_id": d["caso_id"], "tipo": f"ASSINADO_{d['tipo']}",
                "storage_path": url_assinado,
                "observacao": f"{d['titulo']} (assinado digitalmente)",
                "status": "VALIDADO", "enviado_por": "CLIENTE",
            }).execute()
        except Exception:
            pass

    try:
        db.table("mensagens").insert({
            "caso_id": d["caso_id"], "canal": "PORTAL", "autor": "AGENTE",
            "conteudo": f"✅ Recebemos a sua assinatura em {d['titulo']}. "
                        f"Muito obrigado! O documento já está arquivado no seu processo.",
        }).execute()
    except Exception:
        pass

    registrar_evento(d["caso_id"], "DOCUMENTO_ASSINADO",
                     {"documento_id": documento_id, "tipo": d["tipo"]})

    # contrato assinado mantém o fluxo antigo: avança a fase e cobra
    if d["tipo"] == "CONTRATO":
        return _pos_contrato_assinado(d["caso_id"])
    return {"ok": True, "documento": d["tipo"], "assinado": True}


def _pos_contrato_assinado(caso_id: str) -> dict:
    from datetime import datetime, timezone
    from ..agentes.orquestrador import mudar_estado
    from .asaas import criar_cobranca
    db = get_db()
    db.table("casos").update(
        {"contrato_assinado_em": datetime.now(timezone.utc).isoformat()}
    ).eq("id", caso_id).execute()
    try:
        caso = mudar_estado(caso_id, "PAGAMENTO", motivo="Contrato assinado (ZapSign)")
    except Exception:
        caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    valor = _valor_entrada(caso)
    link = None
    if valor:
        try:
            link = criar_cobranca(caso_id, valor,
                                  "Honorários advocatícios - FC ADVOCACIA")["link_pagamento"]
        except Exception:
            link = None
    if link:
        try:
            from . import avisos
            avisos.notificar(caso_id, "PAGAMENTO", "Contrato assinado — pagamento liberado",
                             f"Seu contrato foi assinado com sucesso. "
                             f"Aqui está o link para o pagamento:\n{link}")
        except Exception:
            pass
    return {"ok": True, "avancou": "PAGAMENTO", "cobranca": link}


def processar_webhook(payload: dict) -> dict:
    """Webhook ZapSign: documento assinado → arquiva, avisa o cliente e,
    no caso do contrato, avança a esteira e gera a cobrança."""
    from ..agentes.orquestrador import mudar_estado
    from .asaas import criar_cobranca

    caso_id = payload.get("external_id")
    status = payload.get("status", "")
    registrar_evento(None, "WEBHOOK_ZAPSIGN", {"status": status, "external_id": caso_id})

    if status == "signed" and caso_id:
        tratado = _webhook_documento(caso_id, payload)
        if tratado is not None:
            return tratado

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
                                  "Honorários advocatícios - FC ADVOCACIA")["link_pagamento"]
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
