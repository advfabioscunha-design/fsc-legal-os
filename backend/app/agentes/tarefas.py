"""
O plano de trabalho — o que fazer hoje, e o que vem na semana.

De onde saem as tarefas:

  PRAZOS       cada prazo em aberto vira uma tarefa no dia de trabalho
               (prazo fatal menos dois dias úteis)
  PUBLICAÇÕES  intimação que chegou e ninguém resolveu
  TRIAGEM      caso parado esperando alguém do escritório agir
  CONTRATOS    pedido do balcão parado numa fase que é do escritório

PRIORIDADE — o que vai para o topo
----------------------------------
Não é "o que vence primeiro", só. Um recurso com dez dias pode ser mais
urgente que um despacho com três: perder o prazo recursal encerra o
caso, enquanto um despacho comum se resolve depois com uma petição.

A ordem que este agente usa:

  1. Peça que, perdida, encerra o caso — apelação, réplica,
     contrarrazões, embargos, recurso especial. São as que levam o
     processo ao julgamento, e é onde o escritório ganha ou perde.
  2. Prazo fatal chegando, com peso crescente conforme encurta.
  3. Audiência e perícia marcadas — data que não se remarca sozinha.
  4. O resto, por data.

Uma tarefa nunca é criada duas vezes para o mesmo prazo: a chave é o
prazo de origem. Isso importa porque o plano roda toda semana e
diariamente — sem a chave, a lista dobraria a cada rodada.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from ..core.datas import antecipar_uteis, dias_ate, util
from ..core.db import get_db, registrar_evento

# Atos cuja perda encerra o caso. O peso alto não é exagero: é o que
# faz a réplica de sexta aparecer antes do despacho de quarta.
_RE_DECISIVO = re.compile(
    r"apela[çc][ãa]o|r[ée]plica|contrarraz[õo]es|contra-?raz[õo]es|"
    r"embargos\s+(?:de\s+declara[çc][ãa]o|infringentes|[àa]\s+execu[çc][ãa]o)|"
    r"recurso\s+(?:especial|extraordin[áa]rio|ordin[áa]rio|inominado|"
    r"de\s+revista|adesivo)|agravo\s+(?:de\s+instrumento|interno|em\s+recurso)|"
    r"impugna[çc][ãa]o\s+ao\s+cumprimento|contesta[çc][ãa]o", re.I)

_RE_AUDIENCIA_PERICIA = re.compile(r"audi[êe]ncia|per[íi]cia", re.I)

PESO = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def classificar(titulo: str, descricao: str | None,
                dias_restantes: int | None, tipo: str | None = None) -> tuple[str, str]:
    """(prioridade, motivo)."""
    alvo = f"{titulo or ''} {tipo or ''} {(descricao or '')[:600]}"

    if _RE_DECISIVO.search(alvo):
        return "ALTA", "peça que leva o caso a julgamento — perdê-la encerra a discussão"
    if dias_restantes is not None and dias_restantes <= 2:
        return "ALTA", ("vence hoje" if dias_restantes == 0
                        else "vencido" if dias_restantes < 0
                        else f"vence em {dias_restantes} dia(s)")
    if _RE_AUDIENCIA_PERICIA.search(alvo):
        return "ALTA", "data marcada, não se remarca sozinha"
    if dias_restantes is not None and dias_restantes <= 7:
        return "MEDIA", f"vence em {dias_restantes} dias"
    return "BAIXA", "sem urgência imediata"


def _segunda_da_semana(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _proximo_dia_util(d: date) -> date:
    while not util(d):
        d += timedelta(days=1)
    return d


# ── Levantamento do que está pendente ───────────────────────────
def levantar() -> list[dict]:
    """Tudo que exige ação do escritório, sem duplicar o que já virou
    tarefa."""
    db = get_db()
    hoje = date.today()
    pendentes: list[dict] = []

    # O que JÁ VIROU TAREFA — em qualquer status, não só as vivas.
    #
    # A primeira versão disto só olhava ABERTA e REAGENDADA, e tinha um
    # furo grande: concluída a tarefa, ela saía da lista e a origem
    # voltava a gerar outra igual no dia seguinte. O escritório fazia o
    # trabalho, marcava como feito, e no dia seguinte a mesma tarefa
    # estava lá de novo — não há jeito mais rápido de fazer alguém
    # parar de confiar na lista.
    #
    # Tarefa CANCELADA também conta: cancelar é dizer "isto não era para
    # ser feito". Ressuscitá-la sozinha desfaria a decisão de quem
    # cancelou.
    vivas = db.table("tarefas").select(
        "prazo_id,intimacao_id,anotacao_id,pedido_id,caso_id,origem"
    ).limit(5000).execute().data

    ja_tem      = {t["prazo_id"] for t in vivas if t.get("prazo_id")}
    ja_intim    = {t["intimacao_id"] for t in vivas if t.get("intimacao_id")}
    ja_anotacao = {t["anotacao_id"] for t in vivas if t.get("anotacao_id")}
    ja_pedido   = {t["pedido_id"] for t in vivas if t.get("pedido_id")}
    # Triagem não tem id próprio: a chave é o caso nessa origem.
    ja_triagem  = {t["caso_id"] for t in vivas
                   if t.get("origem") == "TRIAGEM" and t.get("caso_id")}

    # 1) Prazos em aberto
    prazos = db.table("prazos").select(
        "id,titulo,descricao,data,prazo_fatal,tipo,caso_id,responsavel_id,"
        "depende_do_cliente,casos(numero_processo,clientes(nome))"
    ).eq("status", "ABERTO").order("prazo_fatal").limit(500).execute().data
    for p in prazos:
        if p["id"] in ja_tem:
            continue
        restantes = dias_ate(p.get("data"))
        prio, motivo = classificar(p.get("titulo"), p.get("descricao"),
                                   restantes, p.get("tipo"))
        caso = p.get("casos") or {}
        pendentes.append({
            "origem": "PRAZO", "prazo_id": p["id"], "caso_id": p.get("caso_id"),
            "titulo": p.get("titulo") or "Prazo",
            "descricao": (p.get("descricao") or "")[:800],
            "data": (p.get("data") or hoje.isoformat())[:10],
            "prazo_fatal": (p.get("prazo_fatal") or "")[:10] or None,
            "prioridade": prio, "motivo": motivo,
            "responsavel_id": p.get("responsavel_id"),
            "cliente": (caso.get("clientes") or {}).get("nome"),
            "processo": caso.get("numero_processo"),
        })

    # 2) Publicações que ninguém resolveu
    intims = db.table("intimacoes").select(
        "id,caso_id,conteudo,tipo,numero_processo,data_movimento,prazo_em"
    ).eq("status", "A_RESOLVER").order("data_movimento", desc=True) \
        .limit(120).execute().data
    for i in intims:
        if i["id"] in ja_intim:
            continue
        restantes = dias_ate(i.get("prazo_em"))
        prio, motivo = classificar(i.get("tipo") or "Publicação",
                                   i.get("conteudo"), restantes, i.get("tipo"))
        pendentes.append({
            "origem": "PUBLICACAO", "intimacao_id": i["id"],
            "caso_id": i.get("caso_id"),
            "titulo": f"Analisar {i.get('tipo') or 'publicação'} — "
                      f"{i.get('numero_processo') or ''}".strip(),
            "descricao": (i.get("conteudo") or "")[:800],
            "data": (i.get("prazo_em") or hoje.isoformat())[:10],
            "prazo_fatal": (i.get("prazo_em") or "")[:10] or None,
            "prioridade": prio, "motivo": motivo,
            "processo": i.get("numero_processo"),
        })

    # 3) Casos parados na triagem esperando o escritório
    parados = db.table("casos").select(
        "id,estado,titulo,atualizado_em,numero_processo,clientes(nome)"
    ).eq("situacao", "ATIVO").eq("aguardando_cliente", False).in_(
        "estado", ["PRONTO_PARA_ANALISE", "ANALISE", "PETICAO", "REVISAO",
                   "COLETA_PROVAS"]
    ).limit(200).execute().data
    for c in parados:
        if c["id"] in ja_triagem:
            continue
        parado_desde = (c.get("atualizado_em") or "")[:10]
        dias_parado = -(dias_ate(parado_desde) or 0)
        if dias_parado < 3:
            continue                      # ainda é trabalho em curso
        pendentes.append({
            "origem": "TRIAGEM", "caso_id": c["id"],
            "titulo": f"{c.get('estado')} parado há {dias_parado} dias",
            "descricao": c.get("titulo") or "",
            "data": hoje.isoformat(), "prazo_fatal": None,
            "prioridade": "MEDIA" if dias_parado < 10 else "ALTA",
            "motivo": f"sem movimento há {dias_parado} dias",
            "cliente": (c.get("clientes") or {}).get("nome"),
            "processo": c.get("numero_processo"),
        })

    # 4) Pendências anotadas à mão, com data marcada
    try:
        from . import anotacoes
        pendentes.extend(a for a in anotacoes.para_o_plano()
                         if a.get("anotacao_id") not in ja_anotacao)
    except Exception as e:
        print(f"[tarefas] anotações não levantadas: {e}")

    # 5) Pedidos de contrato parados numa fase do escritório
    try:
        do_escritorio = ["PAGAMENTO", "REDACAO", "REVISAO_IA", "AJUSTE",
                         "REVISAO_ADV"]
        pedidos = db.table("pedidos_contrato").select(
            "id,numero,tipo,fase,atualizado_em,clientes(nome)"
        ).in_("fase", do_escritorio).limit(100).execute().data
        for p in pedidos:
            if p["id"] in ja_pedido:
                continue
            dias_parado = -(dias_ate((p.get("atualizado_em") or "")[:10]) or 0)
            pendentes.append({
                "origem": "CONTRATO", "pedido_id": p["id"],
                "titulo": f"{p.get('numero')} — {p.get('fase')}",
                "descricao": p.get("tipo") or "",
                "data": hoje.isoformat(), "prazo_fatal": None,
                "prioridade": "ALTA" if dias_parado >= 2 else "MEDIA",
                "motivo": f"pedido do balcão parado há {dias_parado} dia(s)",
                "cliente": (p.get("clientes") or {}).get("nome"),
            })
    except Exception:
        pass                              # balcão ainda pode não existir

    pendentes.sort(key=lambda t: (PESO.get(t["prioridade"], 9),
                                  t.get("prazo_fatal") or "9999",
                                  t.get("data") or "9999"))
    return pendentes


# ── Montagem do plano ───────────────────────────────────────────
def planejar(de: date, ate: date, limpar_abertas: bool = False) -> dict:
    """Cria as tarefas do período. Só cria; nunca apaga o que alguém já
    marcou como feito."""
    db = get_db()
    criadas, fora_do_periodo = 0, 0
    recusadas: list[str] = []

    for p in levantar():
        try:
            quando = date.fromisoformat(p["data"])
        except ValueError:
            quando = de
        # Tarefa cujo dia já passou vem para o próximo dia útil: lista
        # com data velha some do calendário e vira dívida invisível.
        if quando < date.today():
            quando = _proximo_dia_util(date.today())
        if not (de <= quando <= ate):
            fora_do_periodo += 1
            continue

        # Uma tarefa que o banco recusa (índice único, caso apagado) não
        # pode derrubar o plano inteiro: o resto do dia continua valendo.
        try:
            db.table("tarefas").insert({
                "titulo": p["titulo"][:200],
                "descricao": p.get("descricao"),
                "origem": p["origem"],
                "prazo_id": p.get("prazo_id"),
                "intimacao_id": p.get("intimacao_id"),
                "anotacao_id": p.get("anotacao_id"),
                "caso_id": p.get("caso_id"),
                "pedido_id": p.get("pedido_id"),
                "data": quando.isoformat(),
                "prazo_fatal": p.get("prazo_fatal"),
                "prioridade": p["prioridade"],
                "motivo": p.get("motivo"),
                "responsavel_id": p.get("responsavel_id"),
                "status": "ABERTA",
                "criado_por": "AGENTE",
            }).execute()
            criadas += 1
        except Exception as e:
            recusadas.append(f"{p.get('titulo', '')[:60]}: {e}")

    if recusadas:
        print(f"[tarefas] {len(recusadas)} recusadas: {recusadas[:5]}")
    return {"criadas": criadas, "fora_do_periodo": fora_do_periodo,
            "recusadas": len(recusadas),
            "de": de.isoformat(), "ate": ate.isoformat()}


def puxar_atrasadas(para: date | None = None) -> dict:
    """Traz para hoje as tarefas abertas que ficaram no passado.

    Aqui estava a dívida invisível de verdade.

    `planejar` só cria tarefas NOVAS — nunca toca nas que já existem. Uma
    tarefa criada na sexta para um prazo de quinta fica marcada na sexta
    para sempre. Quando alguém abre a lista de hoje, ela não está lá: o
    que ficou para trás não aparece em dia nenhum, e o prazo vencido
    some da tela justamente quando mais precisava ser visto.

    Puxar para hoje é o comportamento certo. O que está atrasado é para
    agora, não para o próximo dia útil: empurrar para amanhã seria
    repetir o erro que criou o atraso.

    Cada puxada fica no histórico da tarefa — três puxadas seguidas
    dizem algo que a lista sozinha não diz.
    """
    db = get_db()
    hoje = para or date.today()
    atrasadas = db.table("tarefas").select("id,data,titulo,historico,prazo_fatal") \
        .in_("status", ["ABERTA", "REAGENDADA"]) \
        .lt("data", hoje.isoformat()).limit(1000).execute().data or []

    movidas, falhas = 0, 0
    for t in atrasadas:
        h = list(t.get("historico") or [])
        h.append({"em": datetime.utcnow().isoformat(), "o_que": "PUXADA_PARA_HOJE",
                  "quem": "agente", "de": t.get("data"), "para": hoje.isoformat()})
        try:
            db.table("tarefas").update({
                "data": hoje.isoformat(), "historico": h[-60:],
            }).eq("id", t["id"]).execute()
            movidas += 1
        except Exception as e:
            falhas += 1
            print(f"[tarefas] não puxou {t.get('titulo', '')[:40]}: {e}")

    return {"puxadas": movidas, "falhas": falhas, "para": hoje.isoformat()}


def plano_do_dia(dia: date | None = None) -> dict:
    """Roda de manhã: garante que o que vence hoje está na lista.

    Puxa o atrasado ANTES de criar o novo. Na outra ordem, a tarefa
    recém-criada para um prazo vencido entraria hoje e a antiga
    continuaria escondida no passado — duas linhas para a mesma coisa."""
    hoje = dia or date.today()
    atrasadas = puxar_atrasadas(hoje)
    r = planejar(hoje, hoje)
    r["atrasadas_puxadas"] = atrasadas["puxadas"]
    registrar_evento(None, "PLANO_DIARIO", r)
    return r


def plano_da_semana(semana_de: date | None = None) -> dict:
    """Roda na sexta às 18h para a semana seguinte.

    Sexta à tarde é o momento certo: o que chegou na semana já está
    dentro, e a equipe começa a segunda com a lista pronta em vez de
    gastar a manhã montando-a."""
    base = semana_de or (date.today() + timedelta(days=3))
    segunda = _segunda_da_semana(base)
    sexta = segunda + timedelta(days=4)
    r = planejar(segunda, sexta)
    r["semana"] = f"{segunda:%d/%m} a {sexta:%d/%m}"
    registrar_evento(None, "PLANO_SEMANAL", r)
    return r


def replanejar_apos_publicacoes() -> dict:
    """Chamado depois de cada varredura do Diário.

    Publicação nova muda a semana: um prazo que nasce na terça pode ter
    de ser trabalhado na quarta. Em vez de esperar a sexta, o plano se
    ajusta na hora — é o que evita a lista envelhecer no meio da semana."""
    hoje = date.today()
    fim = _segunda_da_semana(hoje) + timedelta(days=11)   # até a próxima sexta
    r = planejar(hoje, fim)
    registrar_evento(None, "PLANO_REAJUSTADO", r)
    return r


# ── Consulta e operação ─────────────────────────────────────────
def listar(de: str | None = None, ate: str | None = None,
           status: str | None = "ABERTA", responsavel_id: str | None = None) -> list[dict]:
    q = get_db().table("tarefas").select(
        "*, casos(numero_processo,clientes(nome)), membros_equipe(nome)")
    if status and status != "TODAS":
        q = q.eq("status", status)
    if de:
        q = q.gte("data", de)
    if ate:
        q = q.lte("data", ate)
    if responsavel_id:
        q = q.eq("responsavel_id", responsavel_id)
    linhas = q.order("data").limit(500).execute().data
    linhas.sort(key=lambda t: (t.get("data") or "9999",
                               PESO.get(t.get("prioridade"), 9)))
    return linhas


def concluir(tarefa_id: str, quem: str = "", nota: str = "") -> dict:
    db = get_db()
    achado = db.table("tarefas").select(
        "historico,caso_id,prazo_id,intimacao_id,titulo") \
        .eq("id", tarefa_id).limit(1).execute().data
    if not achado:
        raise ValueError("Tarefa não encontrada.")
    hist = (achado[0].get("historico") or [])
    hist.append({"em": _agora(), "quem": quem, "acao": "CONCLUIDA", "nota": nota})
    db.table("tarefas").update({
        "status": "FEITA", "concluida_em": _agora(), "historico": hist,
    }).eq("id", tarefa_id).execute()
    # CONCLUIR A TAREFA TEM DE FECHAR A ORIGEM.
    #
    # Não basta marcar a tarefa como feita: o prazo continuava ABERTO e
    # a intimação continuava A_RESOLVER, então no dia seguinte o
    # levantamento encontrava tudo de novo e criava a tarefa outra vez.
    # Fechar a origem é o que faz o trabalho ficar feito de verdade.
    fechados = []
    if achado[0].get("prazo_id"):
        db.table("prazos").update({"status": "CONCLUIDO"}) \
            .eq("id", achado[0]["prazo_id"]).execute()
        fechados.append("prazo")
        if achado[0].get("caso_id"):
            try:
                from . import fase_judicial
                fase_judicial.recalcular(achado[0]["caso_id"])
            except Exception:
                pass
    if achado[0].get("intimacao_id"):
        try:
            db.table("intimacoes").update({"status": "RESOLVIDA"}) \
                .eq("id", achado[0]["intimacao_id"]).execute()
            fechados.append("intimação")
        except Exception as e:
            print(f"[tarefas] intimação não fechada: {e}")

    # `resultado` e não só `nota`: é esta chave que o histórico do caso
    # lê para mostrar O QUE foi feito, e não apenas que foi feito.
    registrar_evento(achado[0].get("caso_id"), "TAREFA_CONCLUIDA",
                     {"tarefa": tarefa_id, "quem": quem, "nota": nota,
                      "resultado": nota, "titulo": achado[0].get("titulo"),
                      "fechou": fechados})
    return {"ok": True, "fechou": fechados}


def reagendar(tarefa_id: str, nova_data: str, quem: str = "",
              motivo: str = "") -> dict:
    """Mudar o dia é normal; sumir com a tarefa não é. O histórico
    guarda quantas vezes ela foi empurrada — três adiamentos dizem algo
    que o card sozinho não diz."""
    db = get_db()
    achado = db.table("tarefas").select("data,historico,caso_id") \
        .eq("id", tarefa_id).limit(1).execute().data
    if not achado:
        raise ValueError("Tarefa não encontrada.")
    hist = (achado[0].get("historico") or [])
    hist.append({"em": _agora(), "quem": quem, "acao": "REAGENDADA",
                 "de": achado[0].get("data"), "para": nova_data, "motivo": motivo})
    db.table("tarefas").update({
        "data": nova_data, "status": "REAGENDADA", "historico": hist,
        "adiamentos": len([h for h in hist if h.get("acao") == "REAGENDADA"]),
    }).eq("id", tarefa_id).execute()
    registrar_evento(achado[0].get("caso_id"), "TAREFA_REAGENDADA",
                     {"tarefa": tarefa_id, "para": nova_data, "motivo": motivo})
    return {"ok": True, "data": nova_data}


def atribuir(tarefa_id: str, responsavel_id: str, quem: str = "") -> dict:
    """Responsável definido é responsável avisado — o e-mail sai aqui."""
    db = get_db()
    achado = db.table("tarefas").select("titulo,data,historico,caso_id") \
        .eq("id", tarefa_id).limit(1).execute().data
    if not achado:
        raise ValueError("Tarefa não encontrada.")
    t = achado[0]
    hist = (t.get("historico") or [])
    hist.append({"em": _agora(), "quem": quem, "acao": "ATRIBUIDA",
                 "para": responsavel_id})
    db.table("tarefas").update({
        "responsavel_id": responsavel_id, "historico": hist,
    }).eq("id", tarefa_id).execute()

    try:
        m = db.table("membros_equipe").select("nome,email") \
            .eq("id", responsavel_id).limit(1).execute().data
        if m and m[0].get("email"):
            from ..integracoes import avisos
            quando = (t.get("data") or "")[:10]
            avisos.enviar_email(
                m[0]["email"], f"Tarefa para você — {t.get('titulo')}",
                f"{t.get('titulo')}\n\nData: {quando}\n\n"
                f"Abra a plataforma para ver os detalhes.",
                f"<p style='font-family:Arial;font-size:14px'><b>{t.get('titulo')}</b>"
                f"<br>Data: {quando}</p>")
    except Exception as e:
        print(f"[tarefas] responsável não avisado: {e}")

    registrar_evento(t.get("caso_id"), "TAREFA_ATRIBUIDA",
                     {"tarefa": tarefa_id, "responsavel": responsavel_id})
    return {"ok": True}
