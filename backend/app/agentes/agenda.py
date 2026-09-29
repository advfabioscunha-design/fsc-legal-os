"""
A agenda do escritório.

O que a tela de Agenda mostrava até aqui eram os prazos — só o que nasce
de intimação. Faltava o resto do dia: a reunião, a audiência designada
por telefone, o atendimento combinado no chat, a perícia que a perita
remarcou. Este módulo é onde essas coisas passam a existir.

Quatro coisas que estão no código e convém saber:

  · UM COMPROMISSO NÃO É UMA TAREFA. A tarefa é trabalho a fazer e pode
    ser empurrada para amanhã; o compromisso tem hora e alguém do outro
    lado esperando. Por isso reagendar um compromisso com convidado
    REENVIA o convite — o calendário de quem foi chamado precisa mudar
    junto, senão a pessoa aparece no fórum no dia errado.

  · FECHAR O DIA TEM DOIS SENTIDOS e o escritório usa os dois. Fechar é
    declarar o dia conferido, nada ficou para trás. Bloquear é não
    aceitar agendamento nesta data — feriado, viagem, júri. São campos
    separados porque encerrar o expediente de hoje não impede marcar
    alguma coisa para hoje.

  · O CONVITE NÃO DÁ ACESSO A NADA. O convidado recebe um link com um
    token aleatório que só serve para dizer "confirmo" ou "não posso"
    naquele compromisso. Não é login, não abre o caso, não mostra outro
    compromisso.

  · REALIZADO NÃO APAGA. Compromisso realizado, cancelado ou reagendado
    continua na base com o histórico do que houve. A agenda de três
    meses atrás é prova de diligência, não lixo.
"""
from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta

from ..core.db import get_db, registrar_evento
from ..core.config import get_settings

TIPOS = ["TAREFA", "EVENTO", "AUDIENCIA", "PERICIA", "ATENDIMENTO",
         "REUNIAO", "PRAZO"]

# Quem o escritório costuma esperar em cada tipo. Serve para a tela
# sugerir, não para impedir.
ROTULO = {
    "TAREFA": "Tarefa", "EVENTO": "Evento", "AUDIENCIA": "Audiência",
    "PERICIA": "Perícia", "ATENDIMENTO": "Atendimento",
    "REUNIAO": "Reunião", "PRAZO": "Prazo",
}

# Compromisso com pessoa do outro lado. Nestes, reagendar sem avisar é
# falta grave, então o reenvio do convite é automático.
COM_TERCEIRO = {"AUDIENCIA", "PERICIA", "ATENDIMENTO", "REUNIAO"}

STATUS_VIVO = ("ABERTO", "REAGENDADO")


def _agora() -> str:
    return datetime.utcnow().isoformat()


def _uid(item_id: str) -> str:
    return f"agenda-{item_id}"


def _anotar(item: dict, o_que: str, quem: str | None = None,
            extra: dict | None = None) -> list:
    h = list(item.get("historico") or [])
    h.append({"em": _agora(), "o_que": o_que, "quem": quem or "sistema",
              **(extra or {})})
    return h[-60:]


# ── Dias fechados ───────────────────────────────────────────────
def dia_bloqueado(dia: str) -> dict | None:
    """Devolve o registro se a data não aceita novo agendamento."""
    r = get_db().table("agenda_dias_fechados").select("*") \
        .eq("data", dia).eq("bloqueia_novos", True).limit(1).execute().data
    return r[0] if r else None


def fechar_dia(dia: str, motivo: str = "", quem: str = "",
               bloqueia_novos: bool = False) -> dict:
    db = get_db()
    db.table("agenda_dias_fechados").upsert({
        "data": dia, "motivo": (motivo or "")[:400],
        "bloqueia_novos": bool(bloqueia_novos),
        "fechado_por": quem or "escritório",
    }, on_conflict="data").execute()
    registrar_evento(None, "AGENDA_DIA_FECHADO",
                     {"data": dia, "bloqueia": bloqueia_novos, "quem": quem})
    return {"ok": True, "data": dia, "bloqueia_novos": bool(bloqueia_novos)}


def reabrir_dia(dia: str, quem: str = "") -> dict:
    get_db().table("agenda_dias_fechados").delete().eq("data", dia).execute()
    registrar_evento(None, "AGENDA_DIA_REABERTO", {"data": dia, "quem": quem})
    return {"ok": True, "data": dia}


def dias_fechados(de: str, ate: str) -> list[dict]:
    return get_db().table("agenda_dias_fechados").select("*") \
        .gte("data", de).lte("data", ate).order("data").execute().data or []


# ── Notas do dia ────────────────────────────────────────────────
def anotar_no_dia(dia: str, texto: str, autor: str = "") -> dict:
    r = get_db().table("agenda_notas").insert({
        "data": dia, "texto": texto.strip()[:2000],
        "autor": autor or "escritório",
    }).execute().data
    return r[0] if r else {}


def notas(de: str, ate: str) -> list[dict]:
    return get_db().table("agenda_notas").select("*") \
        .gte("data", de).lte("data", ate) \
        .order("data").order("criado_em").execute().data or []


def apagar_nota(nota_id: str) -> dict:
    get_db().table("agenda_notas").delete().eq("id", nota_id).execute()
    return {"ok": True}


# ── Compromissos ────────────────────────────────────────────────
def criar(dados: dict, quem: str = "", forcar: bool = False) -> dict:
    """Marca um compromisso. `forcar` passa por cima do dia bloqueado."""
    db = get_db()
    dia = str(dados.get("data") or date.today().isoformat())[:10]

    bloqueio = None if forcar else dia_bloqueado(dia)
    if bloqueio:
        raise ValueError(
            f"A agenda do dia {dia[8:10]}/{dia[5:7]} está bloqueada"
            + (f": {bloqueio.get('motivo')}" if bloqueio.get("motivo") else "")
            + ". Marque em outra data ou reabra o dia."
        )

    tipo = (dados.get("tipo") or "EVENTO").upper()
    if tipo not in TIPOS:
        tipo = "EVENTO"

    novo = {
        "tipo": tipo,
        "titulo": (dados.get("titulo") or ROTULO[tipo])[:200],
        "descricao": (dados.get("descricao") or "")[:4000] or None,
        "data": dia,
        "hora_inicio": dados.get("hora_inicio") or None,
        "hora_fim": dados.get("hora_fim") or None,
        "dia_inteiro": not dados.get("hora_inicio"),
        "local": (dados.get("local") or "")[:300] or None,
        "link": (dados.get("link") or "")[:600] or None,
        "caso_id": dados.get("caso_id") or None,
        "cliente_id": dados.get("cliente_id") or None,
        "numero_processo": dados.get("numero_processo") or None,
        "prazo_id": dados.get("prazo_id") or None,
        "tarefa_id": dados.get("tarefa_id") or None,
        "anotacao_id": dados.get("anotacao_id") or None,
        "responsavel_id": dados.get("responsavel_id") or None,
        "status": "ABERTO",
        "criado_por": quem or "escritório",
        "historico": [{"em": _agora(), "o_que": "CRIADO",
                       "quem": quem or "escritório"}],
    }
    r = db.table("agenda_itens").insert(novo).execute().data
    if not r:
        raise ValueError("Não consegui gravar o compromisso.")
    item = r[0]

    # O UID do iCalendar só pode ser atribuído depois do id existir.
    db.table("agenda_itens").update({"uid_ics": _uid(item["id"])}) \
        .eq("id", item["id"]).execute()
    item["uid_ics"] = _uid(item["id"])

    if item.get("caso_id"):
        registrar_evento(item["caso_id"], "AGENDA_CRIADA",
                         {"tipo": tipo, "data": dia,
                          "titulo": item["titulo"], "quem": quem})

    for c in (dados.get("convidados") or []):
        try:
            convidar(item["id"], c.get("email"), c.get("nome"),
                     c.get("papel"), enviar=True)
        except Exception as e:
            print(f"[agenda] convidado não incluído: {e}")

    if item.get("responsavel_id"):
        try:
            avisar_responsavel(item["id"])
        except Exception as e:
            print(f"[agenda] responsável não avisado: {e}")

    return item


def listar(de: str, ate: str, responsavel_id: str | None = None,
           caso_id: str | None = None, tipo: str | None = None,
           incluir_cancelados: bool = False) -> list[dict]:
    q = get_db().table("agenda_itens").select(
        "*,clientes(nome,email),casos(numero_processo),"
        "membros_equipe(nome),agenda_convidados(id,nome,email,papel,resposta)"
    ).gte("data", de).lte("data", ate)
    if responsavel_id:
        q = q.eq("responsavel_id", responsavel_id)
    if caso_id:
        q = q.eq("caso_id", caso_id)
    if tipo:
        q = q.eq("tipo", tipo.upper())
    if not incluir_cancelados:
        q = q.neq("status", "CANCELADO")
    itens = q.order("data").order("hora_inicio").limit(1500).execute().data or []
    return itens


def do_dia(dia: str) -> dict:
    """Tudo que existe sobre uma data: compromissos, notas e o fechamento.

    É o que a tela abre quando alguém clica num dia do calendário — a
    pergunta ali não é "quais compromissos", é "como está esse dia".
    """
    fechado = get_db().table("agenda_dias_fechados").select("*") \
        .eq("data", dia).limit(1).execute().data
    return {
        "data": dia,
        "itens": listar(dia, dia),
        "notas": notas(dia, dia),
        "fechado": fechado[0] if fechado else None,
    }


def reagendar(item_id: str, nova_data: str, motivo: str = "",
              quem: str = "", nova_hora: str | None = None) -> dict:
    db = get_db()
    r = db.table("agenda_itens").select("*").eq("id", item_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Compromisso não encontrado.")
    item = r[0]

    atual = {
        "data": nova_data[:10],
        "hora_inicio": nova_hora if nova_hora is not None else item.get("hora_inicio"),
        "status": "REAGENDADO",
        "adiamentos": int(item.get("adiamentos") or 0) + 1,
        # A sequência do iCalendar precisa subir, senão o calendário de
        # quem recebeu o convite ignora a atualização por achar que é
        # cópia do que já tem.
        "sequencia_ics": int(item.get("sequencia_ics") or 0) + 1,
        "atualizado_em": _agora(),
        "historico": _anotar(item, "REAGENDADO", quem, {
            "de": item.get("data"), "para": nova_data[:10], "motivo": motivo}),
    }
    if nova_hora is not None:
        atual["dia_inteiro"] = not nova_hora
    db.table("agenda_itens").update(atual).eq("id", item_id).execute()

    if item.get("caso_id"):
        registrar_evento(item["caso_id"], "AGENDA_REAGENDADA", {
            "de": item.get("data"), "para": nova_data[:10],
            "motivo": motivo, "titulo": item.get("titulo"), "quem": quem})

    reenviados = 0
    if item.get("tipo") in COM_TERCEIRO:
        for c in _convidados(item_id):
            try:
                _mandar_convite(item_id, c["id"], atualizacao=True)
                reenviados += 1
            except Exception as e:
                print(f"[agenda] convite não reenviado: {e}")

    return {"ok": True, "data": nova_data[:10], "convites_reenviados": reenviados,
            "adiamentos": atual["adiamentos"]}


def concluir(item_id: str, resultado: str = "", quem: str = "") -> dict:
    """Marca como realizado e escreve o que houve no histórico do caso."""
    db = get_db()
    r = db.table("agenda_itens").select("*,casos(id)").eq("id", item_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Compromisso não encontrado.")
    item = r[0]

    db.table("agenda_itens").update({
        "status": "REALIZADO",
        "atualizado_em": _agora(),
        "historico": _anotar(item, "REALIZADO", quem, {"resultado": resultado}),
    }).eq("id", item_id).execute()

    if item.get("caso_id"):
        registrar_evento(item["caso_id"], "AGENDA_REALIZADA", {
            "tipo": item.get("tipo"), "titulo": item.get("titulo"),
            "data": item.get("data"), "resultado": resultado, "quem": quem})
    return {"ok": True}


def cancelar(item_id: str, motivo: str = "", quem: str = "") -> dict:
    db = get_db()
    r = db.table("agenda_itens").select("*").eq("id", item_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Compromisso não encontrado.")
    item = r[0]

    db.table("agenda_itens").update({
        "status": "CANCELADO",
        "sequencia_ics": int(item.get("sequencia_ics") or 0) + 1,
        "atualizado_em": _agora(),
        "historico": _anotar(item, "CANCELADO", quem, {"motivo": motivo}),
    }).eq("id", item_id).execute()

    if item.get("caso_id"):
        registrar_evento(item["caso_id"], "AGENDA_CANCELADA", {
            "titulo": item.get("titulo"), "data": item.get("data"),
            "motivo": motivo, "quem": quem})

    # Quem foi convidado precisa saber que não há mais compromisso — o
    # cancelamento também é um .ics, e apaga o evento do calendário dele.
    avisados = 0
    for c in _convidados(item_id):
        try:
            _mandar_convite(item_id, c["id"], cancelamento=True)
            avisados += 1
        except Exception as e:
            print(f"[agenda] cancelamento não avisado: {e}")
    return {"ok": True, "convidados_avisados": avisados}


def atribuir(item_id: str, responsavel_id: str | None, quem: str = "") -> dict:
    db = get_db()
    r = db.table("agenda_itens").select("*").eq("id", item_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Compromisso não encontrado.")
    db.table("agenda_itens").update({
        "responsavel_id": responsavel_id,
        # Trocou de dono: o novo ainda não sabe.
        "responsavel_avisado_em": None,
        "atualizado_em": _agora(),
        "historico": _anotar(r[0], "RESPONSAVEL", quem,
                             {"responsavel_id": responsavel_id}),
    }).eq("id", item_id).execute()
    if responsavel_id:
        try:
            avisar_responsavel(item_id)
        except Exception as e:
            print(f"[agenda] responsável não avisado: {e}")
    return {"ok": True}


# ── Convidados ──────────────────────────────────────────────────
def _convidados(item_id: str) -> list[dict]:
    return get_db().table("agenda_convidados").select("*") \
        .eq("item_id", item_id).execute().data or []


def convidar(item_id: str, email: str, nome: str = "", papel: str = "OUTRO",
             enviar: bool = True) -> dict:
    if not email or "@" not in email:
        raise ValueError("E-mail do convidado inválido.")
    db = get_db()
    ja = db.table("agenda_convidados").select("*").eq("item_id", item_id) \
        .ilike("email", email.strip()).limit(1).execute().data
    if ja:
        c = ja[0]
    else:
        r = db.table("agenda_convidados").insert({
            "item_id": item_id, "email": email.strip().lower(),
            "nome": (nome or "").strip()[:150] or None,
            "papel": (papel or "OUTRO").upper(),
            "token": secrets.token_urlsafe(32),
        }).execute().data
        if not r:
            raise ValueError("Não consegui gravar o convidado.")
        c = r[0]
    if enviar:
        _mandar_convite(item_id, c["id"])
    return c


def desconvidar(convidado_id: str) -> dict:
    get_db().table("agenda_convidados").delete().eq("id", convidado_id).execute()
    return {"ok": True}


def _mandar_convite(item_id: str, convidado_id: str,
                    atualizacao: bool = False,
                    cancelamento: bool = False) -> dict:
    from ..integracoes import agenda_ics, avisos
    db = get_db()
    s = get_settings()

    item = db.table("agenda_itens").select("*,casos(numero_processo)") \
        .eq("id", item_id).limit(1).execute().data
    conv = db.table("agenda_convidados").select("*") \
        .eq("id", convidado_id).limit(1).execute().data
    if not item or not conv:
        raise ValueError("Convite sem compromisso ou sem convidado.")
    item, conv = item[0], conv[0]

    dia = date.fromisoformat(str(item["data"])[:10])
    dia_br = dia.strftime("%d/%m/%Y")
    hora = str(item.get("hora_inicio") or "")[:5]
    quando = f"{dia_br}" + (f" às {hora}" if hora else " (dia inteiro)")
    rotulo = ROTULO.get(item.get("tipo"), "Compromisso")

    processo = (item.get("casos") or {}).get("numero_processo") \
        or item.get("numero_processo") or ""
    partes = [f"{rotulo}: {item.get('titulo')}", f"Quando: {quando}"]
    if item.get("local"):
        partes.append(f"Onde: {item['local']}")
    if processo:
        partes.append(f"Processo: {processo}")
    if item.get("descricao"):
        partes.append("")
        partes.append(item["descricao"])
    descricao = "\n".join(partes)

    ics = agenda_ics.compromisso(
        uid=item.get("uid_ics") or _uid(item_id),
        titulo=f"{rotulo} — {item.get('titulo')}",
        descricao=descricao, dia=dia,
        hora_inicio=item.get("hora_inicio"), hora_fim=item.get("hora_fim"),
        sequencia=int(item.get("sequencia_ics") or 0),
        local=item.get("local"), link=item.get("link"),
        cancelar=cancelamento,
        convidados=[(conv.get("nome") or "", conv["email"])],
    )

    base = f"{s.api_url.rstrip('/')}/api/v1/agenda/confirmar/{conv['token']}"
    if cancelamento:
        assunto = f"[Cancelado] {rotulo} — {item.get('titulo')}"
        cabeca = (f"O compromisso de <b>{quando}</b> foi <b>cancelado</b>. "
                  f"O anexo remove o evento do seu calendário.")
        botoes = ""
    else:
        assunto = (f"[{'Remarcado' if atualizacao else 'Convite'}] "
                   f"{rotulo} — {item.get('titulo')}")
        cabeca = (f"{'A data mudou. O novo horário é' if atualizacao else 'Você foi convidado para'} "
                  f"<b>{quando}</b>.")
        botoes = (
            f"<p style='margin:18px 0'>"
            f"<a href='{base}?r=aceito' style='background:#1DB954;color:#fff;"
            f"padding:10px 18px;border-radius:8px;text-decoration:none;"
            f"font-family:Arial,sans-serif;font-size:14px'>Confirmo presença</a>"
            f"&nbsp;&nbsp;"
            f"<a href='{base}?r=recusado' style='background:#eee;color:#333;"
            f"padding:10px 18px;border-radius:8px;text-decoration:none;"
            f"font-family:Arial,sans-serif;font-size:14px'>Não poderei ir</a></p>"
        )

    corpo = "\n".join([cabeca.replace("<b>", "").replace("</b>", ""), "",
                       descricao])
    html = (
        f"<p style='font-family:Arial,sans-serif;font-size:14px'>{cabeca}</p>"
        f"<p style='font-family:Arial,sans-serif;font-size:14px;"
        f"white-space:pre-line'>{descricao}</p>{botoes}"
        f"<p style='font-family:Arial,sans-serif;font-size:12px;color:#667'>"
        f"O anexo adiciona (ou atualiza) o compromisso no seu calendário."
        f"</p>"
    )

    avisos.enviar_email(conv["email"], assunto, corpo, html,
                        anexos=[("compromisso.ics", ics, "text/calendar")])
    db.table("agenda_convidados").update(
        {"convite_enviado_em": _agora()}).eq("id", convidado_id).execute()
    return {"ok": True, "email": conv["email"]}


def responder_convite(token: str, resposta: str, ip: str = "") -> dict:
    """O convidado clicou no botão do e-mail.

    Resposta idempotente de propósito: quem clica duas vezes vê a mesma
    confirmação, e não um erro que o faça achar que não deu certo.
    """
    db = get_db()
    r = db.table("agenda_convidados").select("*,agenda_itens(*)") \
        .eq("token", token).limit(1).execute().data
    if not r:
        raise ValueError("Convite não encontrado ou já expirado.")
    conv = r[0]
    valor = "ACEITO" if str(resposta).lower().startswith("a") else "RECUSADO"

    db.table("agenda_convidados").update({
        "resposta": valor, "respondido_em": _agora(),
        "ip_resposta": (ip or "")[:60] or None,
    }).eq("id", conv["id"]).execute()

    item = conv.get("agenda_itens") or {}
    if item.get("id"):
        atual = db.table("agenda_itens").select("historico,caso_id") \
            .eq("id", item["id"]).limit(1).execute().data
        if atual:
            db.table("agenda_itens").update({
                "historico": _anotar(atual[0], f"CONVIDADO_{valor}",
                                     conv.get("email"))
            }).eq("id", item["id"]).execute()
            if atual[0].get("caso_id"):
                registrar_evento(atual[0]["caso_id"], "AGENDA_RESPOSTA", {
                    "quem": conv.get("email"), "resposta": valor,
                    "titulo": item.get("titulo"), "data": item.get("data")})
    return {"ok": True, "resposta": valor,
            "titulo": item.get("titulo"), "data": item.get("data")}


# ── Responsável ─────────────────────────────────────────────────
def avisar_responsavel(item_id: str) -> dict:
    """Avisa quem ficou com o compromisso.

    Designar alguém sem contar não designa nada — o compromisso fica com
    dono no banco e órfão na vida real.
    """
    from ..integracoes import avisos
    db = get_db()
    s = get_settings()
    r = db.table("agenda_itens").select(
        "*,membros_equipe(nome,email,google_email),casos(numero_processo)"
    ).eq("id", item_id).limit(1).execute().data
    if not r:
        raise ValueError("Compromisso não encontrado.")
    item = r[0]
    membro = item.get("membros_equipe") or {}
    # `google_email` é o campo antigo; cadastros velhos só têm ele.
    email = membro.get("email") or membro.get("google_email")
    if not email:
        return {"ok": False, "motivo": "responsável sem e-mail cadastrado"}

    dia = date.fromisoformat(str(item["data"])[:10]).strftime("%d/%m/%Y")
    hora = str(item.get("hora_inicio") or "")[:5]
    quando = dia + (f" às {hora}" if hora else "")
    rotulo = ROTULO.get(item.get("tipo"), "Compromisso")
    processo = (item.get("casos") or {}).get("numero_processo") or ""
    link = f"{s.app_url.rstrip('/')}/agenda?dia={str(item['data'])[:10]}"

    texto = (f"{rotulo}: {item.get('titulo')}\nQuando: {quando}\n"
             + (f"Onde: {item['local']}\n" if item.get("local") else "")
             + (f"Processo: {processo}\n" if processo else "")
             + f"\nAbrir na agenda: {link}")
    html = (
        f"<p style='font-family:Arial,sans-serif;font-size:14px'>"
        f"Você ficou responsável por este compromisso:</p>"
        f"<p style='font-family:Arial,sans-serif;font-size:14px;"
        f"white-space:pre-line'>{texto}</p>"
    )
    avisos.enviar_email(email, f"[Agenda] {rotulo} — {quando}", texto, html)
    db.table("agenda_itens").update({"responsavel_avisado_em": _agora()}) \
        .eq("id", item_id).execute()
    return {"ok": True, "email": email}


# ── A semana, com tudo dentro ───────────────────────────────────
def semana(de: str | None = None, dias: int = 7) -> dict:
    """A agenda dia a dia, juntando compromissos, notas e fechamentos.

    A controladoria já responde "o que vence"; esta responde "como está
    a minha semana", que é a pergunta de segunda de manhã.
    """
    inicio = date.fromisoformat(de) if de else date.today()
    fim = inicio + timedelta(days=dias)
    itens = listar(inicio.isoformat(), fim.isoformat())
    notas_ = notas(inicio.isoformat(), fim.isoformat())
    fechados = {f["data"]: f for f in dias_fechados(inicio.isoformat(),
                                                    fim.isoformat())}

    por_dia: dict[str, dict] = {}
    for i in range(dias + 1):
        d = (inicio + timedelta(days=i)).isoformat()
        por_dia[d] = {"data": d, "itens": [], "notas": [],
                      "fechado": fechados.get(d)}
    for it in itens:
        d = str(it.get("data"))[:10]
        if d in por_dia:
            por_dia[d]["itens"].append(it)
    for n in notas_:
        d = str(n.get("data"))[:10]
        if d in por_dia:
            por_dia[d]["notas"].append(n)

    lista = list(por_dia.values())
    return {"de": inicio.isoformat(), "ate": fim.isoformat(),
            "dias": lista,
            "total": sum(len(d["itens"]) for d in lista)}


# ── Prazos que viram compromisso ────────────────────────────────
def espelhar_prazos(dias: int = 60) -> dict:
    """Põe na agenda os prazos que ainda não estão lá.

    A agenda tem que mostrar o dia inteiro, e prazo faz parte do dia. Mas
    o prazo continua morando em `prazos` — aqui entra só o espelho, ligado
    pelo prazo_id, para que a tela mostre tudo junto sem duplicar a
    verdade em dois lugares.
    """
    db = get_db()
    hoje = date.today()
    limite = (hoje + timedelta(days=dias)).isoformat()

    ja = {x["prazo_id"] for x in db.table("agenda_itens")
          .select("prazo_id").in_("status", list(STATUS_VIVO))
          .limit(3000).execute().data if x.get("prazo_id")}

    prazos = db.table("prazos").select(
        "id,titulo,descricao,data,prazo_fatal,tipo,caso_id,responsavel_id,"
        "casos(numero_processo)"
    ).eq("status", "ABERTO").gte("data", hoje.isoformat()) \
        .lte("data", limite).limit(500).execute().data or []

    criados = 0
    for p in prazos:
        if p["id"] in ja:
            continue
        try:
            criar({
                "tipo": "PRAZO",
                "titulo": (p.get("titulo") or "Prazo")[:200],
                "descricao": (p.get("descricao") or "")[:1500],
                "data": str(p.get("data"))[:10],
                "caso_id": p.get("caso_id"),
                "numero_processo": (p.get("casos") or {}).get("numero_processo"),
                "prazo_id": p["id"],
                "responsavel_id": p.get("responsavel_id"),
            }, quem="controladoria", forcar=True)
            criados += 1
        except Exception as e:
            print(f"[agenda] prazo não espelhado: {e}")
    return {"criados": criados, "considerados": len(prazos)}


# ── Feed para assinar no Google Calendar ────────────────────────
def feed_ics(meses_atras: int = 2, meses_a_frente: int = 12) -> bytes:
    from ..integracoes import agenda_ics
    hoje = date.today()
    de = (hoje - timedelta(days=31 * meses_atras)).isoformat()
    ate = (hoje + timedelta(days=31 * meses_a_frente)).isoformat()
    itens = listar(de, ate, incluir_cancelados=True)
    for i in itens:
        rotulo = ROTULO.get(i.get("tipo"), "")
        i["titulo"] = f"{rotulo} — {i.get('titulo')}" if rotulo else i.get("titulo")
        proc = (i.get("casos") or {}).get("numero_processo") \
            or i.get("numero_processo")
        cli = (i.get("clientes") or {}).get("nome")
        extra = [x for x in [f"Cliente: {cli}" if cli else "",
                             f"Processo: {proc}" if proc else ""] if x]
        if extra:
            i["descricao"] = "\n".join([*extra, "", i.get("descricao") or ""])
    return agenda_ics.feed(itens)
