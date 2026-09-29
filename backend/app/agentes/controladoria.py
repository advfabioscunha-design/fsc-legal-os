"""
Controladoria de prazos — a rodada diária que mantém o acervo honesto.

O que ela faz, na ordem:

 1. VARRE O DJEN pela OAB do escritório (últimos dias) e grava as
    publicações novas dos processos que já estão na plataforma. Processo
    desconhecido NÃO é cadastrado sozinho: fica na prévia da tela do
    judicial para o advogado conferir e importar.

    ATENÇÃO — hoje esta etapa falha aqui: o Comunica CNJ responde 403
    para este servidor, que está nos Estados Unidos. Quem consegue
    consultar é o navegador do escritório, no Brasil, e é de lá que a
    varredura sai (tela de Intimações → "Atualizar pelo Diário", que
    chama `importador.sincronizar_conhecidos`). A etapa continua aqui
    porque passa a funcionar sozinha no dia em que houver um ponto de
    saída no Brasil; enquanto não houver, ela apenas registra o erro e
    as outras etapas seguem.
 2. RECALCULA a data de trabalho de todo prazo aberto: prazo fatal menos
    dois dias úteis. Se o prazo fatal mudou, a agenda muda com ele.
 3. VIRA A FASE quando o fato aparece: processo protocolado vai para
    JUDICIAL; certidão de trânsito em julgado, cumprimento de sentença,
    alvará ou RPV levam para RECEBIMENTO.
 4. MANDA OS CONVITES de agenda: para o escritório, todo prazo; para o
    cliente, apenas o que depende dele (audiência, perícia, documento,
    comparecimento), sempre dois dias antes do prazo real.
 5. ORDENA A FILA pelo que vence primeiro e marca o que já venceu.

Limite que não se resolve com código: o prazo em dias vem de estimativa
por tipo de ato (ver `core.datas` e `agentes.importador`). Prazo estimado
entra na fila com marca de conferência. A controladoria organiza e cobra;
quem confirma o prazo é o advogado.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from ..core.config import get_settings
from ..core.datas import antecipar_uteis, dias_ate
from ..core.db import get_db, registrar_evento
from ..integracoes import comunica_cnj
from . import importador

# Atos que são obrigação do cliente — só estes vão para a agenda dele.
_RE_DO_CLIENTE = re.compile(
    r"audi[êe]ncia|per[íi]cia|compareci|deposi[çc][ãa]o|"
    r"interrogat[óo]rio|concilia[çc][ãa]o|media[çc][ãa]o|"
    r"apresenta[çc][ãa]o\s+de\s+documento", re.I)

DIAS_DE_VARREDURA = 7


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def depende_do_cliente(texto: str | None, tipo: str | None = None) -> bool:
    alvo = f"{tipo or ''} {texto or ''}"
    return bool(_RE_DO_CLIENTE.search(alvo))


# ── 1. Varredura das publicações novas ──────────────────────────
def varrer_publicacoes(dias: int = DIAS_DE_VARREDURA) -> dict:
    db = get_db()
    try:
        previa = importador.previa_por_oab(dias=dias)
    except Exception as e:                      # fonte fora do ar não derruba a rodada
        return {"erro": str(e), "processos": 0, "intimacoes": 0}

    conhecidos = [p for p in previa["itens"] if p["ja_na_plataforma"]]
    novas, prazos = 0, 0
    for p in conhecidos:
        for com in p["comunicacoes"]:
            nova = importador._gravar_intimacao(p["caso_id"], com)
            if not nova:
                continue
            novas += 1
            if nova.get("prazo_em"):
                titulo = f"{nova.get('tipo') or 'Intimação'} — {p['numero_processo']}"
                importador._gravar_prazo(p["caso_id"], nova, titulo)
                # quem manda no campo é o conteúdo do ato, não o padrão
                db.table("prazos").update({
                    "depende_do_cliente": depende_do_cliente(
                        nova.get("conteudo"), nova.get("tipo")),
                }).eq("intimacao_id", nova["id"]).execute()
                prazos += 1

    return {"processos": len(conhecidos), "intimacoes": novas, "prazos": prazos,
            "novos_para_conferir": previa["novos"]}


# ── 2. Recálculo das datas de trabalho ──────────────────────────
def recalcular_datas() -> int:
    db = get_db()
    ajustados = 0
    abertos = db.table("prazos").select("id,data,prazo_fatal,status") \
        .eq("status", "ABERTO").limit(2000).execute().data
    for p in abertos:
        if not p.get("prazo_fatal"):
            continue
        alvo = antecipar_uteis(date.fromisoformat(p["prazo_fatal"][:10]), 2).isoformat()
        if (p.get("data") or "")[:10] != alvo:
            db.table("prazos").update({"data": alvo, "atualizado_em": _agora()}) \
                .eq("id", p["id"]).execute()
            ajustados += 1
    return ajustados


# ── 3. Viradas de fase ──────────────────────────────────────────
def avancar_fases() -> dict:
    """Protocolado → Judicial; trânsito/cumprimento → Recebimento."""
    db = get_db()
    para_judicial, para_recebimento = 0, 0

    # Protocolado com número de processo: já está em juízo.
    for c in db.table("casos").select("id,numero_processo,protocolado_em") \
            .eq("estado", "PROTOCOLADO").eq("situacao", "ATIVO").limit(500).execute().data:
        if not c.get("numero_processo"):
            continue                              # sem número não há como acompanhar
        db.table("casos").update({
            "estado": "JUDICIAL", "judicial_em": _agora(),
            "protocolado_em": c.get("protocolado_em") or _agora(),
            "atualizado_em": _agora(),
        }).eq("id", c["id"]).execute()
        registrar_evento(c["id"], "FASE_JUDICIAL",
                         {"motivo": "protocolo com número de processo"})
        para_judicial += 1

    # Trânsito em julgado ou início de cumprimento: fase de recebimento.
    judiciais = db.table("casos").select("id,numero_processo") \
        .eq("estado", "JUDICIAL").eq("situacao", "ATIVO").limit(500).execute().data
    for c in judiciais:
        intims = db.table("intimacoes").select("conteudo,tipo,data_movimento") \
            .eq("caso_id", c["id"]).order("data_movimento", desc=True) \
            .limit(20).execute().data
        texto = "\n".join((i.get("conteudo") or "") + " " + (i.get("tipo") or "")
                          for i in intims)
        transitou = importador.transitou(texto)
        if not (transitou or importador.em_recebimento(texto)):
            continue
        db.table("casos").update({
            "estado": "RECEBIMENTO", "recebimento_em": _agora(),
            "transito_em": _agora() if transitou else None,
            "atualizado_em": _agora(),
        }).eq("id", c["id"]).execute()
        registrar_evento(c["id"], "FASE_RECEBIMENTO", {
            "motivo": "certidão de trânsito em julgado" if transitou
                      else "cumprimento de sentença / alvará",
        })
        para_recebimento += 1

    return {"para_judicial": para_judicial, "para_recebimento": para_recebimento}


def mover_fase(caso_id: str, destino: str, motivo: str = "") -> dict:
    """Mudança de fase pela mão do advogado (botões das telas)."""
    if destino not in ("JUDICIAL", "RECEBIMENTO", "PROTOCOLADO"):
        raise ValueError("Destino inválido.")
    db = get_db()
    # `.single()` levanta exceção quando não acha nada, e o que chegava
    # na tela era um "Internal Server Error" sem explicação. Um id que
    # não existe é erro de quem chamou, não falha do servidor.
    achados = db.table("casos").select("id,estado,numero_processo") \
        .eq("id", caso_id).limit(1).execute().data
    if not achados:
        raise ValueError("Caso não encontrado.")
    caso = achados[0]
    if destino in ("JUDICIAL", "RECEBIMENTO") and not caso.get("numero_processo"):
        raise ValueError("Informe o número do processo antes de mover a fase — "
                         "sem ele não há como acompanhar as publicações.")
    # A máquina de estados continua mandando: mover à mão não é motivo
    # para um caso pular da proposta direto para o recebimento.
    from .orquestrador import TRANSICOES
    atual = caso.get("estado")
    if destino not in TRANSICOES.get(atual, []):
        raise ValueError(f"Não dá para ir de {atual} para {destino}. "
                         f"Deste ponto o caso só pode seguir para: "
                         f"{', '.join(TRANSICOES.get(atual, [])) or 'nenhum estado'}.")
    campos = {"estado": destino, "atualizado_em": _agora()}
    campos["judicial_em" if destino == "JUDICIAL" else "recebimento_em"] = _agora()
    db.table("casos").update(campos).eq("id", caso_id).execute()
    registrar_evento(caso_id, f"FASE_{destino}",
                     {"de": caso.get("estado"), "manual": True, "motivo": motivo})
    return {"ok": True, "de": caso.get("estado"), "para": destino}


# ── 4. Convites de agenda ───────────────────────────────────────
def enviar_convites(limite: int = 60) -> dict:
    from ..integracoes import agenda_ics
    s = get_settings()
    db = get_db()
    enviados_escritorio, enviados_cliente, falhas = 0, 0, []

    prazos = db.table("prazos").select(
        "id,titulo,descricao,data,prazo_fatal,tipo,depende_do_cliente,"
        "convite_escritorio_em,convite_cliente_em,caso_id,"
        "casos(numero_processo,numero_atendimento,cliente_id,clientes(nome,email))"
    ).eq("status", "ABERTO").order("data").limit(limite).execute().data

    for p in prazos:
        if not p.get("data"):
            continue
        dia = date.fromisoformat(p["data"][:10])
        caso = p.get("casos") or {}
        cliente = caso.get("clientes") or {}
        fatal = (p.get("prazo_fatal") or "")[:10]
        fatal_br = ("/".join(reversed(fatal.split("-"))) if fatal else "a confirmar")
        base = (f"Processo: {caso.get('numero_processo') or '—'}\n"
                f"Atendimento: {caso.get('numero_atendimento') or '—'}\n"
                f"Prazo fatal: {fatal_br}\n"
                f"Data no calendário: dois dias antes do prazo fatal.\n\n"
                f"{(p.get('descricao') or '')[:600]}")

        if not p.get("convite_escritorio_em") and s.email_escritorio:
            try:
                agenda_ics.enviar(
                    s.email_escritorio, p["titulo"], base, dia,
                    uid=f"prazo-{p['id']}",
                    html_extra="<p style='font-family:Arial;font-size:12px;color:#a00'>"
                               "Prazo estimado pelo tipo de ato — confira a contagem "
                               "no processo antes de trabalhar a peça.</p>")
                db.table("prazos").update({"convite_escritorio_em": _agora()}) \
                    .eq("id", p["id"]).execute()
                enviados_escritorio += 1
            except Exception as e:
                falhas.append({"prazo": p["id"], "onde": "escritorio", "erro": str(e)})

        if (p.get("depende_do_cliente") and not p.get("convite_cliente_em")
                and cliente.get("email")):
            texto = (f"{(p.get('descricao') or '')[:400]}\n\n"
                     f"Processo: {caso.get('numero_processo') or '—'}\n"
                     f"Qualquer dúvida, fale com o escritório pelo painel do cliente.")
            try:
                agenda_ics.enviar(cliente["email"],
                                  f"{p['titulo']} — {cliente.get('nome') or ''}".strip(),
                                  texto, dia, uid=f"prazo-cli-{p['id']}")
                db.table("prazos").update({"convite_cliente_em": _agora()}) \
                    .eq("id", p["id"]).execute()
                enviados_cliente += 1
            except Exception as e:
                falhas.append({"prazo": p["id"], "onde": "cliente", "erro": str(e)})

    return {"escritorio": enviados_escritorio, "cliente": enviados_cliente,
            "falhas": falhas}


# ── 5. Audiências e perícias viram compromisso ──────────────────
# Prazo e compromisso não são a mesma coisa, e tratar os dois como
# prazo foi o que deixou audiência de fora da agenda até aqui: prazo
# tem data-limite e se trabalha ANTES; audiência tem hora marcada e se
# comparece NAQUELE dia. Por isso o compromisso não recua dois dias —
# o alarme é que vem antes.
_RE_AUDIENCIA = re.compile(
    r"audi[êe]ncia\s+(?:de\s+\w+\s+)?(?:designada|agendada|marcada|redesignada|"
    r"no\s+dia|para\s+o\s+dia)|designo\s+(?:a\s+)?audi[êe]ncia", re.I)
_RE_PERICIA = re.compile(
    r"per[íi]cia\s+(?:m[ée]dica|t[ée]cnica|cont[áa]bil\s+)?"
    r"(?:designada|agendada|marcada|no\s+dia|para\s+o\s+dia)|"
    r"comparecer\s+[àa]\s+per[íi]cia", re.I)
_RE_DATA_HORA = re.compile(
    r"\b(\d{2})[/.\-](\d{2})[/.\-](\d{4})\b(?:[^\n]{0,40}?(\d{1,2})\s*(?:h|:)\s*(\d{2})?)?")


def _quando_e_onde(texto: str, marco: re.Pattern) -> tuple[date, str] | None:
    """Data e hora do compromisso, quando o texto traz."""
    m = marco.search(texto or "")
    if not m:
        return None
    trecho = texto[m.start(): m.start() + 300]
    achou = _RE_DATA_HORA.search(trecho)
    if not achou:
        return None
    d, mes, ano, h, mi = achou.groups()
    try:
        quando = date(int(ano), int(mes), int(d))
    except ValueError:
        return None
    hora = f"{int(h):02d}h{mi or '00'}" if h else ""
    return quando, hora


def agendar_eventos(dias_para_tras: int = 120) -> dict:
    """Lê as publicações e põe audiência e perícia na agenda.

    Só compromisso FUTURO entra: audiência que já aconteceu é história,
    e o que a agenda precisa mostrar é o que ainda vai acontecer.

    Estes são os compromissos que o cliente precisa saber — ele é quem
    comparece. Por isso nascem com `depende_do_cliente`, que é o que
    manda o convite para a agenda dele."""
    db = get_db()
    hoje = date.today()
    desde = (hoje - timedelta(days=dias_para_tras)).isoformat()

    intims = db.table("intimacoes").select(
        "id,caso_id,conteudo,tipo,numero_processo,data_movimento"
    ).gte("data_movimento", desde).order("data_movimento", desc=True) \
        .limit(800).execute().data

    criados, ja_tinha, passados = 0, 0, 0
    for i in intims:
        texto = i.get("conteudo") or ""
        for rotulo, marco in (("AUDIENCIA", _RE_AUDIENCIA), ("PERICIA", _RE_PERICIA)):
            achado = _quando_e_onde(texto, marco)
            if not achado:
                continue
            quando, hora = achado
            if quando < hoje:
                passados += 1
                continue

            titulo = (f"{rotulo.capitalize()}"
                      f"{' às ' + hora if hora else ''} — "
                      f"{i.get('numero_processo') or ''}").strip()
            # A chave é a intimação: a mesma publicação não gera dois
            # compromissos, e uma redesignação nova cria o seu.
            existe = db.table("prazos").select("id") \
                .eq("intimacao_id", i["id"]).limit(1).execute().data
            if existe:
                ja_tinha += 1
                continue
            db.table("prazos").insert({
                "caso_id": i["caso_id"], "intimacao_id": i["id"],
                "titulo": titulo[:140],
                "descricao": texto[:1000],
                "data": quando.isoformat(),        # compromisso não recua
                "prazo_fatal": quando.isoformat(),
                "tipo": rotulo, "origem": "CONTROLADORIA",
                "depende_do_cliente": True,
                "status": "ABERTO",
                "atualizado_em": _agora(),
            }).execute()
            criados += 1
            registrar_evento(i["caso_id"], "COMPROMISSO_AGENDADO",
                             {"tipo": rotulo, "quando": quando.isoformat(),
                              "hora": hora})
            break        # uma publicação gera um compromisso, não dois

    return {"criados": criados, "ja_agendados": ja_tinha,
            "ja_aconteceram": passados}


# ── 6. A semana pela frente ─────────────────────────────────────
def agenda_da_semana(dias: int = 7) -> dict:
    """O que vem nos próximos dias, dia a dia.

    A fila ordenada por urgência responde "o que é mais urgente"; esta
    responde "como está a minha semana", que é outra pergunta e a que
    se faz na segunda-feira de manhã."""
    hoje = date.today()
    limite = hoje + timedelta(days=dias)
    por_dia: dict[str, list] = {}

    for p in fila(dias=dias + 2, limite=300):
        d = p.get("data_trabalho")
        if not d or date.fromisoformat(d) > limite:
            continue
        por_dia.setdefault(d, []).append({
            "id": p["id"], "titulo": p["descricao"], "tipo": p.get("tipo"),
            "cliente": p.get("cliente"), "processo": p.get("numero_processo"),
            "prazo_fatal": p.get("prazo_fatal"),
            "depende_do_cliente": p.get("depende_do_cliente"),
            "atrasado": p["dias_restantes"] < 0,
        })

    dias_lista = []
    for i in range(dias + 1):
        d = (hoje + timedelta(days=i)).isoformat()
        itens = sorted(por_dia.get(d, []), key=lambda x: x["titulo"] or "")
        dias_lista.append({"data": d, "itens": itens, "total": len(itens)})
    atrasados = [x for lista in por_dia.values() for x in lista if x["atrasado"]]
    return {"de": hoje.isoformat(), "ate": limite.isoformat(),
            "dias": dias_lista, "atrasados": atrasados,
            "total": sum(d["total"] for d in dias_lista)}


# ── 7. O que está fora dos conformes ────────────────────────────
def auditoria() -> dict:
    """Lista o que impede o acompanhamento de funcionar.

    Não é relatório de produtividade: é a lista do que está quebrado e
    precisa da mão de alguém. Cada achado diz o caso e o que fazer."""
    db = get_db()
    hoje = date.today()
    achados: list[dict] = []

    casos = db.table("casos").select(
        "id,numero_processo,estado,fase_judicial,fase_judicial_em,"
        "titulo,cliente_id,clientes(nome,email)"
    ).eq("situacao", "ATIVO").in_(
        "estado", ["JUDICIAL", "PROTOCOLADO", "TRANSITO_JULGADO", "RECEBIMENTO"]
    ).limit(600).execute().data

    for c in casos:
        nome = (c.get("clientes") or {}).get("nome") or "—"
        rot = f"{nome} · {c.get('numero_processo') or 'sem número'}"
        if not c.get("numero_processo"):
            achados.append({"caso_id": c["id"], "caso": rot, "gravidade": "ALTA",
                            "o_que": "processo judicial sem número",
                            "fazer": "cadastrar o número para o Diário poder acompanhar"})
        if not (c.get("clientes") or {}).get("nome") or nome == "A identificar":
            achados.append({"caso_id": c["id"], "caso": rot, "gravidade": "MEDIA",
                            "o_que": "cliente não identificado",
                            "fazer": "abrir o caso e informar de quem é o processo"})
        if not (c.get("clientes") or {}).get("email"):
            achados.append({"caso_id": c["id"], "caso": rot, "gravidade": "BAIXA",
                            "o_que": "cliente sem e-mail",
                            "fazer": "sem e-mail não há convite de agenda nem aviso"})
        if c.get("estado") == "JUDICIAL" and not c.get("fase_judicial"):
            achados.append({"caso_id": c["id"], "caso": rot, "gravidade": "MEDIA",
                            "o_que": "sem coluna no judicializado",
                            "fazer": "usar Reavaliar colunas, ou escolher a coluna à mão"})

    # Publicação com prazo que ninguém resolveu e o prazo já passou
    vencidas = db.table("intimacoes").select(
        "id,caso_id,numero_processo,prazo_em,tipo"
    ).eq("status", "A_RESOLVER").lt("prazo_em", hoje.isoformat()) \
        .order("prazo_em", desc=True).limit(50).execute().data
    for i in vencidas:
        achados.append({
            "caso_id": i.get("caso_id"),
            "caso": i.get("numero_processo") or "—", "gravidade": "ALTA",
            "o_que": f"intimação de {i.get('tipo') or 'ato'} com prazo vencido "
                     f"em {i.get('prazo_em')} ainda marcada como a resolver",
            "fazer": "conferir no processo e dar baixa, ou registrar o que foi feito",
        })

    # Prazo aberto sem data: não entra em fila nenhuma e some da vista
    sem_data = db.table("prazos").select("id,caso_id,titulo") \
        .eq("status", "ABERTO").is_("prazo_fatal", "null").limit(50).execute().data
    for p in sem_data:
        achados.append({"caso_id": p.get("caso_id"), "caso": p.get("titulo") or "—",
                        "gravidade": "MEDIA", "o_que": "prazo aberto sem data fatal",
                        "fazer": "informar a data ou dar baixa no prazo"})

    ordem = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
    achados.sort(key=lambda a: ordem.get(a["gravidade"], 9))
    return {
        "total": len(achados),
        "por_gravidade": {g: sum(1 for a in achados if a["gravidade"] == g)
                          for g in ("ALTA", "MEDIA", "BAIXA")},
        "achados": achados[:120],
        "casos_conferidos": len(casos),
    }


# ── A fila do dia ───────────────────────────────────────────────
def fila(dias: int = 30, limite: int = 200) -> list[dict]:
    """Prazos abertos ordenados pelo que vence primeiro. Vencido vem
    antes de tudo — é o que precisa de decisão hoje."""
    db = get_db()
    rows = db.table("prazos").select(
        "id,titulo,data,prazo_fatal,tipo,status,depende_do_cliente,caso_id,"
        "casos(numero_processo,numero_atendimento,estado,clientes(nome))"
    ).eq("status", "ABERTO").order("data").limit(1000).execute().data

    saida = []
    for p in rows:
        restantes = dias_ate(p.get("data"))
        if restantes is None or restantes > dias:
            continue
        caso = p.get("casos") or {}
        saida.append({
            "id": p["id"], "caso_id": p.get("caso_id"),
            "descricao": p.get("titulo"), "tipo": p.get("tipo"),
            "data_trabalho": (p.get("data") or "")[:10],
            "prazo_fatal": (p.get("prazo_fatal") or "")[:10] or None,
            "dias_restantes": restantes,
            "dias_ate_o_fatal": dias_ate(p.get("prazo_fatal")),
            "depende_do_cliente": p.get("depende_do_cliente"),
            "numero_processo": caso.get("numero_processo"),
            "numero_atendimento": caso.get("numero_atendimento"),
            "fase": caso.get("estado"),
            "cliente": (caso.get("clientes") or {}).get("nome"),
        })
    saida.sort(key=lambda x: (x["dias_restantes"], x["prazo_fatal"] or "9999"))
    return saida[:limite]


def marcar_vencidos() -> int:
    """Prazo de trabalho que passou do fatal sem baixa fica sinalizado —
    sem apagar nada, para a conversa sobre o que aconteceu ser possível."""
    db = get_db()
    hoje = date.today().isoformat()
    abertos = db.table("prazos").select("id,prazo_fatal,caso_id") \
        .eq("status", "ABERTO").lt("prazo_fatal", hoje).limit(500).execute().data
    for p in abertos:
        registrar_evento(p.get("caso_id"), "PRAZO_VENCIDO_EM_ABERTO",
                         {"prazo_id": p["id"], "prazo_fatal": p["prazo_fatal"]})
    return len(abertos)


# ── Rodada diária ───────────────────────────────────────────────
def rodar() -> dict:
    resultado = {"em": _agora()}
    from . import fase_judicial
    # A ordem não é arbitrária: primeiro chegam as publicações novas,
    # depois os prazos que nasceram delas são ajustados, as fases
    # avançam, as colunas são relidas, os compromissos entram na agenda
    # e só então saem os convites — convidar antes de saber a data é
    # mandar o cliente para o dia errado.
    for nome, funcao in (("publicacoes", varrer_publicacoes),
                         ("datas_ajustadas", recalcular_datas),
                         ("fases", avancar_fases),
                         ("colunas_do_judicial", fase_judicial.recalcular_todos),
                         ("compromissos", agendar_eventos),
                         ("convites", enviar_convites),
                         ("vencidos_em_aberto", marcar_vencidos),
                         ("auditoria", auditoria)):
        try:
            resultado[nome] = funcao()
        except Exception as e:
            # uma etapa quebrada não pode impedir as outras de rodar
            resultado[nome] = {"erro": str(e)}
    resultado["fila"] = len(fila())
    try:
        resultado["semana"] = agenda_da_semana()
    except Exception as e:
        resultado["semana"] = {"erro": str(e)}

    # O relatório fica guardado como evento: dá para olhar depois o que
    # a rodada de terça-feira encontrou, sem depender de ninguém ter
    # estado com a tela aberta.
    resumo = {k: v for k, v in resultado.items() if k not in ("em", "semana")}
    if isinstance(resumo.get("auditoria"), dict):
        resumo["auditoria"] = {kk: vv for kk, vv in resumo["auditoria"].items()
                               if kk != "achados"}
    registrar_evento(None, "CONTROLADORIA_RODOU", resumo)
    return resultado
