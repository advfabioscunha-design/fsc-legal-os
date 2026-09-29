"""
Pendências — o que alguém anotou que precisa ser feito.

A diferença para tudo o mais que a plataforma já controla: prazo nasce
de uma intimação, tarefa nasce do plano do agente. Pendência nasce da
cabeça de quem está cuidando do caso — "ligar para a perita", "juntar o
comprovante que o cliente mandou no WhatsApp", "conferir se o alvará
saiu". Coisas que não vêm de publicação nenhuma e que, sem um lugar,
ficam no papel da mesa.

O nome do módulo é `anotacoes` e não `pendencias` porque já existe um
`agentes/pendencias.py` — a régua de cobrança do cliente que não mandou
documento. Dois arquivos com o mesmo nome em domínios diferentes é
confusão garantida daqui a seis meses.

Como entra na rotina: toda pendência com data entra no levantamento do
agente de tarefas junto com os prazos, e por isso aparece no plano do
dia e da semana. Resolvida, vira registro no histórico do caso — o que
foi feito fica no card do cliente, não só na cabeça de quem fez.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from ..core.db import get_db, registrar_evento


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar(texto: str, data_resolver: str | None = None,
          caso_id: str | None = None, cliente_id: str | None = None,
          numero_processo: str | None = None, prioridade: str = "MEDIA",
          responsavel_id: str | None = None, quem: str = "") -> dict:
    if not (texto or "").strip():
        raise ValueError("Escreva o que precisa ser feito.")
    if prioridade not in ("ALTA", "MEDIA", "BAIXA"):
        prioridade = "MEDIA"
    db = get_db()

    # Anotação sem caso é legítima (um lembrete do escritório), mas
    # quando há caso a ligação é o que faz a pendência aparecer no card
    # do cliente depois.
    if caso_id and not cliente_id:
        achado = db.table("casos").select("cliente_id,numero_processo") \
            .eq("id", caso_id).limit(1).execute().data
        if achado:
            cliente_id = achado[0].get("cliente_id")
            numero_processo = numero_processo or achado[0].get("numero_processo")

    row = db.table("anotacoes").insert({
        "texto": texto.strip(), "data_resolver": data_resolver,
        "caso_id": caso_id, "cliente_id": cliente_id,
        "numero_processo": numero_processo, "prioridade": prioridade,
        "responsavel_id": responsavel_id, "status": "ABERTA",
        "criado_por": quem or None,
        "historico": [{"em": _agora(), "quem": quem, "acao": "CRIADA"}],
    }).execute().data[0]

    if caso_id:
        registrar_evento(caso_id, "PENDENCIA_ANOTADA", {
            "anotacao": row["id"], "texto": texto.strip()[:300],
            "para": data_resolver, "por": quem,
        })
    return row


def listar(status: str = "ABERTA", caso_id: str | None = None,
           responsavel_id: str | None = None, ate: str | None = None) -> list[dict]:
    q = get_db().table("anotacoes").select(
        "*, casos(numero_processo,estado,clientes(nome)), membros_equipe(nome)")
    if status and status != "TODAS":
        q = q.eq("status", status)
    if caso_id:
        q = q.eq("caso_id", caso_id)
    if responsavel_id:
        q = q.eq("responsavel_id", responsavel_id)
    if ate:
        q = q.lte("data_resolver", ate)
    linhas = q.order("data_resolver", desc=False).limit(400).execute().data
    peso = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
    # Sem data vai para o fim: é lembrete, não compromisso.
    linhas.sort(key=lambda a: (a.get("data_resolver") or "9999-12-31",
                               peso.get(a.get("prioridade"), 9)))
    return linhas


def resolver(anotacao_id: str, resultado: str = "", quem: str = "") -> dict:
    """Resolver registra O QUE FOI FEITO no histórico do caso.

    O campo `resultado` não é enfeite: "liguei para a perita" e "perita
    confirmou a data para o dia 12" são coisas diferentes para quem
    abrir o caso daqui a três meses."""
    db = get_db()
    achado = db.table("anotacoes").select("*").eq("id", anotacao_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pendência não encontrada.")
    a = achado[0]
    hist = (a.get("historico") or [])
    hist.append({"em": _agora(), "quem": quem, "acao": "RESOLVIDA",
                 "resultado": resultado})
    db.table("anotacoes").update({
        "status": "RESOLVIDA", "resolvido_em": _agora(),
        "resultado": resultado or None, "historico": hist,
    }).eq("id", anotacao_id).execute()

    if a.get("caso_id"):
        registrar_evento(a["caso_id"], "PENDENCIA_RESOLVIDA", {
            "anotacao": anotacao_id, "texto": (a.get("texto") or "")[:300],
            "resultado": resultado[:500], "por": quem,
        })
    return {"ok": True}


def reagendar(anotacao_id: str, nova_data: str, motivo: str = "",
              quem: str = "") -> dict:
    db = get_db()
    achado = db.table("anotacoes").select("data_resolver,historico,caso_id") \
        .eq("id", anotacao_id).limit(1).execute().data
    if not achado:
        raise ValueError("Pendência não encontrada.")
    hist = (achado[0].get("historico") or [])
    hist.append({"em": _agora(), "quem": quem, "acao": "REAGENDADA",
                 "de": achado[0].get("data_resolver"), "para": nova_data,
                 "motivo": motivo})
    db.table("anotacoes").update({
        "data_resolver": nova_data, "historico": hist,
        "adiamentos": len([h for h in hist if h.get("acao") == "REAGENDADA"]),
    }).eq("id", anotacao_id).execute()
    if achado[0].get("caso_id"):
        registrar_evento(achado[0]["caso_id"], "PENDENCIA_REAGENDADA",
                         {"anotacao": anotacao_id, "para": nova_data,
                          "motivo": motivo})
    return {"ok": True, "data_resolver": nova_data}


def cancelar(anotacao_id: str, motivo: str = "", quem: str = "") -> dict:
    """Cancelar não apaga: a anotação some da fila e fica no histórico.
    Saber que alguém decidiu não fazer aquilo, e quando, vale tanto
    quanto saber que fez."""
    db = get_db()
    achado = db.table("anotacoes").select("historico,caso_id,texto") \
        .eq("id", anotacao_id).limit(1).execute().data
    if not achado:
        raise ValueError("Pendência não encontrada.")
    hist = (achado[0].get("historico") or [])
    hist.append({"em": _agora(), "quem": quem, "acao": "CANCELADA",
                 "motivo": motivo})
    db.table("anotacoes").update({
        "status": "CANCELADA", "historico": hist, "resultado": motivo or None,
    }).eq("id", anotacao_id).execute()
    if achado[0].get("caso_id"):
        registrar_evento(achado[0]["caso_id"], "PENDENCIA_CANCELADA",
                         {"anotacao": anotacao_id, "motivo": motivo})
    return {"ok": True}


def para_o_plano() -> list[dict]:
    """O que o agente de tarefas leva para a agenda.

    Só pendência COM data entra: sem data, é lembrete — aparece na tela
    de Pendências, não ocupa espaço no plano do dia de ninguém."""
    hoje = date.today().isoformat()
    saida = []
    for a in listar("ABERTA"):
        if not a.get("data_resolver"):
            continue
        caso = a.get("casos") or {}
        saida.append({
            "origem": "ANOTACAO", "anotacao_id": a["id"],
            "caso_id": a.get("caso_id"),
            "titulo": (a.get("texto") or "")[:150],
            "descricao": a.get("texto"),
            "data": a["data_resolver"][:10],
            "prazo_fatal": None,
            "prioridade": a.get("prioridade") or "MEDIA",
            "motivo": ("anotado como pendência"
                       + (" — data já passou" if a["data_resolver"][:10] < hoje else "")),
            "responsavel_id": a.get("responsavel_id"),
            "cliente": (caso.get("clientes") or {}).get("nome"),
            "processo": a.get("numero_processo") or caso.get("numero_processo"),
        })
    return saida
