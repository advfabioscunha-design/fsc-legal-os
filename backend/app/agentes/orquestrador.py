"""
ORQUESTRADOR DA JORNADA — máquina de estados do caso.

Regra de ouro: NENHUM estado avança sem evento confirmado.
O Agente Especialista conduz a conversa; o orquestrador garante
que contrato assinado e pagamento confirmado precedem a coleta
de provas, e que dificuldades escalonam para humano.
"""
from datetime import datetime, timezone
from ..core.db import get_db, registrar_evento

# Transições permitidas (anti-bug: o agente não pode pular etapas)
TRANSICOES = {
    "LEAD":            ["QUALIFICACAO", "ESCALADO_HUMANO", "CANCELADO"],
    "QUALIFICACAO":    ["PROPOSTA", "INVIAVEL", "ESCALADO_HUMANO"],
    "PROPOSTA":        ["CONTRATO", "ESCALADO_HUMANO", "CANCELADO"],
    "CONTRATO":        ["PAGAMENTO", "ESCALADO_HUMANO", "CANCELADO"],   # via webhook ZapSign
    "PAGAMENTO":       ["COLETA_DOCS", "ESCALADO_HUMANO", "CANCELADO"], # via webhook Asaas
    "COLETA_DOCS":     ["COLETA_PROVAS", "ESCALADO_HUMANO"],
    "COLETA_PROVAS":   ["ANALISE", "ESCALADO_HUMANO"],
    "ANALISE":         ["PETICAO", "INVIAVEL", "ESCALADO_HUMANO"],
    "PETICAO":         ["REVISAO"],
    "REVISAO":         ["APROVADO", "PETICAO"],          # advogado pode devolver p/ reescrita
    "APROVADO":        ["PROTOCOLO_RPA"],
    "PROTOCOLO_RPA":   ["PROTOCOLADO", "ESCALADO_HUMANO"],
    "PROTOCOLADO":     ["CONCLUIDO"],
    "ESCALADO_HUMANO": ["QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO",
                        "COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "AGENDADO", "CANCELADO"],
    "AGENDADO":        ["QUALIFICACAO", "COLETA_DOCS", "CANCELADO"],
}


class TransicaoInvalida(Exception):
    pass


def mudar_estado(caso_id: str, novo_estado: str, motivo: str = "") -> dict:
    db = get_db()
    caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    atual = caso["estado"]

    if novo_estado not in TRANSICOES.get(atual, []):
        raise TransicaoInvalida(f"{atual} → {novo_estado} não permitido")

    db.table("casos").update({
        "estado": novo_estado,
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", caso_id).execute()

    registrar_evento(caso_id, "ESTADO_MUDOU",
                     {"de": atual, "para": novo_estado, "motivo": motivo})
    return {**caso, "estado": novo_estado}


def escalar_para_humano(caso_id: str, motivo: str, detalhe: str = "",
                        oferecer_agenda: bool = True) -> dict:
    """Agente detectou dificuldade/demora → humano assume.
    Notifica o advogado e (opcional) oferece link de agendamento ao cliente."""
    from ..integracoes.whatsapp import notificar_humano
    from ..core.config import get_settings

    db = get_db()
    db.table("escalacoes").insert({
        "caso_id": caso_id, "motivo": motivo, "detalhe": detalhe
    }).execute()

    caso = mudar_estado(caso_id, "ESCALADO_HUMANO", motivo=f"{motivo}: {detalhe}")

    # Busca o link de agenda do especialista do grupo
    s = get_settings()
    link = s.link_agenda_padrao
    if caso.get("grupo"):
        esp = db.table("agentes_especialistas").select("link_agenda,advogado_humano") \
                .eq("grupo", caso["grupo"]).maybe_single().execute().data
        if esp and esp.get("link_agenda"):
            link = esp["link_agenda"]

    try:
        notificar_humano(
            f"⚠️ ESCALAÇÃO — caso {caso_id[:8]} ({caso.get('grupo','?')})\n"
            f"Motivo: {motivo}\nDetalhe: {detalhe[:300]}"
        )
    except Exception:
        pass  # notificação nunca pode travar a esteira

    return {"caso": caso, "link_agenda": link if oferecer_agenda else None}
