"""
AGUARDANDO DOCUMENTOS — os dois relógios e a régua de cobrança.

Quando o escritório pede um documento, o caso deixa de depender de nós.
A partir daí:

  * o caso entra no estado AGUARDANDO_DOCUMENTOS e some da esteira de
    produção — quem está redigindo petição não precisa ver card parado;
  * o relógio do SLA do escritório PAUSA, porque o atraso não é nosso;
  * o relógio do cliente começa, e é ele que move a régua:

      dia 3   lembrete cordial;
      dia 7   urgência;
      dia 10  encerramento (lead) ou sinalização (cliente com contrato).

Sobre a urgência do dia 7: a mensagem só fala em perda de direito quando o
caso tem PRAZO REAL cadastrado (prazo_fatal) — prescrição, decadência ou
prazo processual —, e nesse caso cita a data. Sem prazo cadastrado, ela usa
urgência operacional honesta: o atendimento está parado e será encerrado.
Dizer a um cliente que o direito dele "pode ficar fragilizado" quando nada
está correndo é afirmação inverídica, e o problema não é só ético: é o
escritório afirmando por escrito algo que não se sustenta.

Sobre o dia 10: caso SEM contrato assinado é arquivado como lead frio, e
sai da esteira. Caso COM contrato ou processo em andamento nunca é
arquivado pelo robô — ele apenas para de cobrar e entra na lista "parados",
porque abandonar causa com mandato ativo gera responsabilidade do advogado.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as _tz

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..integracoes import avisos

ESTADO_AGUARDANDO = "AGUARDANDO_DOCUMENTOS"
ESTADO_RETORNO = "PRONTO_PARA_ANALISE"
ESTADO_FRIO = "LEAD_FRIO"

DIAS = (3, 7, 10)
# estados em que já existe contrato/processo: aqui o robô não arquiva
COM_VINCULO = ("CONTRATO", "PAGAMENTO", "PETICAO", "PROTOCOLADO",
               "ANDAMENTO", "ANALISE", "COLETA_PROVAS", "EXECUCAO")


def _agora():
    return datetime.now(_tz.utc)


def _iso(d):
    return d.isoformat()


# ── Entrada e saída do estado ────────────────────────────────────
def marcar_aguardando(caso_id: str, descricao: str,
                      solicitacao_id: str | None = None) -> dict:
    """O escritório pediu algo ao cliente: pausa o nosso relógio, inicia o
    dele e tira o card da produção."""
    db = get_db()
    caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    if not caso:
        raise ValueError("Caso não encontrado.")

    agora = _agora()
    mudanca = {
        "aguardando_cliente": True,
        "aguardando_desc": descricao,
        "aguardando_desde": _iso(agora),
        "cobranca_etapa": 0,
        "cobranca_ultima_em": None,
        "parado_sinalizado_em": None,
        "atualizado_em": _iso(agora),
    }
    # guarda de onde o caso saiu, para devolvê-lo ao mesmo lugar depois
    if caso.get("estado") != ESTADO_AGUARDANDO:
        mudanca["estado_anterior"] = caso.get("estado")
        mudanca["estado"] = ESTADO_AGUARDANDO
    # pausa o SLA do escritório
    if not caso.get("sla_pausado_em"):
        mudanca["sla_pausado_em"] = _iso(agora)

    db.table("casos").update(mudanca).eq("id", caso_id).execute()
    registrar_evento(caso_id, "AGUARDANDO_CLIENTE",
                     {"descricao": descricao, "solicitacao_id": solicitacao_id,
                      "estado_anterior": mudanca.get("estado_anterior")})
    return {"ok": True, "estado": ESTADO_AGUARDANDO,
            "aguardando_desde": mudanca["aguardando_desde"]}


def retomar(caso_id: str, motivo: str = "documento recebido") -> dict:
    """O cliente respondeu: soma o tempo parado ao SLA, encerra a régua e
    devolve o card para a esteira de produção."""
    db = get_db()
    caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    if not caso:
        return {"ok": False}

    agora = _agora()
    mudanca = {
        "aguardando_cliente": False, "aguardando_desc": None,
        "aguardando_desde": None, "cobranca_etapa": 0,
        "cobranca_ultima_em": None, "parado_sinalizado_em": None,
        "atualizado_em": _iso(agora),
    }
    # fecha a pausa do SLA, acumulando o tempo que foi do cliente
    if caso.get("sla_pausado_em"):
        try:
            inicio = datetime.fromisoformat(caso["sla_pausado_em"].replace("Z", "+00:00"))
            parado = int((agora - inicio).total_seconds())
        except Exception:
            parado = 0
        mudanca["sla_parado_segundos"] = int(caso.get("sla_parado_segundos") or 0) + max(parado, 0)
        mudanca["sla_pausado_em"] = None

    if caso.get("estado") in (ESTADO_AGUARDANDO, ESTADO_FRIO):
        mudanca["estado"] = ESTADO_RETORNO
        mudanca["estado_anterior"] = None

    db.table("casos").update(mudanca).eq("id", caso_id).execute()
    registrar_evento(caso_id, "CASO_RETOMADO",
                     {"motivo": motivo, "estado": mudanca.get("estado"),
                      "tempo_parado_s": mudanca.get("sla_parado_segundos")})
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "CRM", "autor": "HUMANO",
            "conteudo": f"✅ O cliente respondeu ({motivo}). O caso voltou para a "
                        "esteira, pronto para análise.",
        }).execute()
    except Exception:
        pass
    return {"ok": True, "estado": mudanca.get("estado")}


# ── Textos da régua ──────────────────────────────────────────────
def _prazo_vivo(caso: dict) -> tuple[bool, str]:
    """Há prazo real correndo? Devolve (sim, texto do prazo)."""
    pf = caso.get("prazo_fatal")
    if not pf:
        return False, ""
    try:
        d = date.fromisoformat(str(pf)[:10])
    except Exception:
        return False, ""
    if d < date.today():
        return False, ""
    faltam = (d - date.today()).days
    desc = (caso.get("prazo_descricao") or "").strip()
    quando = d.strftime("%d/%m/%Y")
    texto = f"{desc} em {quando}" if desc else f"prazo em {quando}"
    return True, f"{texto} (faltam {faltam} dia{'s' if faltam != 1 else ''})"


def texto_cobranca(etapa: int, caso: dict, cliente: dict, doc: str) -> tuple[str, str]:
    """Devolve (título, mensagem) da etapa. O dia 7 só fala em risco ao
    direito quando existe prazo cadastrado."""
    nome = (cliente.get("nome") or "").split(" ")[0].title()
    tem_prazo, prazo = _prazo_vivo(caso)

    # `doc` é o texto livre que o escritório escreveu ao pedir ("a foto da
    # CNH", "extrato dos últimos 3 meses"). Como o gênero e o número variam,
    # ele entra sempre depois de dois-pontos — assim a frase não quebra a
    # concordância seja qual for a redação do pedido.
    if etapa == 3:
        return ("Falta um documento para avançarmos",
                f"Olá, {nome}! Passando para lembrar: o seu processo está pronto "
                f"para avançar e só falta o seguinte:\n\n{doc}\n\n"
                "Você pode enviar pelo seu painel, em poucos toques — é o caminho "
                "mais rápido e fica tudo registrado no seu processo. Se preferir, "
                "pode responder este e-mail com o arquivo em anexo.")

    if etapa == 7:
        if tem_prazo:
            return ("Documento pendente — há prazo correndo",
                    f"{nome}, seguimos aguardando:\n\n{doc}\n\n"
                    f"Este caso tem {prazo}. Sem esse documento não conseguimos "
                    "protocolar a tempo, e a perda do prazo pode comprometer o "
                    "direito discutido.\n\n"
                    "Envie pelo painel ou responda este e-mail com o arquivo. "
                    "Se estiver com dificuldade para obtê-lo, responda avisando "
                    "— conseguimos orientar você.")
        return ("Seu atendimento está parado à espera de um documento",
                f"{nome}, seu atendimento está parado há uma semana aguardando:"
                f"\n\n{doc}\n\n"
                "Sem esse documento não temos como seguir com a análise do seu "
                "caso.\n\n"
                "Se ainda tiver interesse, envie pelo painel ou responda este "
                "e-mail com o arquivo. Não recebendo retorno nos próximos dias, "
                "vamos encerrar este atendimento — e você poderá reabri-lo quando "
                "quiser.\n\n"
                "Se estiver com dificuldade para conseguir o documento, é só "
                "responder avisando.")

    # dia 10
    if tem_prazo:
        return ("Atendimento parado — precisamos falar com você",
                f"{nome}, seguimos sem receber:\n\n{doc}\n\n"
                f"E este caso tem {prazo}.\n\n"
                "Não vamos encerrar o seu atendimento, mas precisamos do seu "
                "retorno para agir a tempo. Responda este e-mail ou entre no seu "
                "painel assim que puder.")
    return ("Encerramos este atendimento por falta de retorno",
            f"{nome}, como não recebemos o documento solicitado nem retorno seu, "
            f"estamos encerrando este atendimento por ora.\n\nO que faltava:"
            f"\n{doc}\n\n"
            "Não se preocupe: nada se perde. Seus dados e o histórico ficam "
            "guardados e, quando quiser retomar, basta enviar o documento pelo "
            "painel ou responder este e-mail — o atendimento é reaberto "
            "automaticamente, do ponto onde parou.")


# ── A rotina ─────────────────────────────────────────────────────
def rodar(agora: datetime | None = None) -> dict:
    """Percorre os casos aguardando documento e aplica a régua. Roda de hora
    em hora; cada etapa só dispara uma vez por caso."""
    db = get_db()
    agora = agora or _agora()
    saida = {"verificados": 0, "cobrancas": 0, "arquivados": 0,
             "sinalizados": 0, "erros": []}

    try:
        casos = db.table("casos").select("*, clientes(nome,email,whatsapp)") \
                  .not_.is_("aguardando_desde", "null") \
                  .execute().data or []
    except Exception as e:
        return {"ok": False, "motivo": str(e)[:200]}

    for caso in casos:
        saida["verificados"] += 1
        try:
            inicio = datetime.fromisoformat(
                str(caso["aguardando_desde"]).replace("Z", "+00:00"))
        except Exception:
            continue
        dias = (agora - inicio).days
        etapa_feita = int(caso.get("cobranca_etapa") or 0)
        etapa = 0
        for d in DIAS:
            if dias >= d and etapa_feita < d:
                etapa = d
        if not etapa:
            continue

        cli = caso.get("clientes") or {}
        doc = (caso.get("aguardando_desc") or "o documento solicitado").strip()
        titulo, mensagem = texto_cobranca(etapa, caso, cli, doc)
        tem_prazo, _ = _prazo_vivo(caso)
        com_vinculo = (caso.get("estado_anterior") or "") in COM_VINCULO

        try:
            envio = avisos.notificar(caso["id"], "COBRANCA", titulo, mensagem)
        except Exception as e:
            envio = {"erros": [str(e)[:200]]}
            saida["erros"].append(f"{caso.get('numero_atendimento')}: {e}"[:200])

        # a mensagem também fica na conversa do painel — é o canal que o
        # cliente pode consultar a qualquer hora
        try:
            db.table("mensagens").insert({
                "caso_id": caso["id"], "canal": "PORTAL", "autor": "AGENTE",
                "conteudo": mensagem,
            }).execute()
        except Exception:
            pass

        try:
            db.table("cobrancas").insert({
                "caso_id": caso["id"], "etapa": etapa, "motivo": doc,
                "com_prazo": tem_prazo,
                "canais": ",".join(
                    [c for c, ok in (("PAINEL", True),
                                     ("EMAIL", bool(envio.get("enviado_email"))),
                                     ("WHATSAPP", bool(envio.get("enviado_whatsapp"))))
                     if ok]),
            }).execute()
        except Exception:
            pass

        mudanca = {"cobranca_etapa": etapa, "cobranca_ultima_em": _iso(agora),
                   "atualizado_em": _iso(agora)}

        if etapa == 10:
            if com_vinculo or tem_prazo:
                # contrato assinado ou prazo correndo: não se arquiva sozinho
                mudanca["parado_sinalizado_em"] = _iso(agora)
                saida["sinalizados"] += 1
                registrar_evento(caso["id"], "CASO_PARADO_SINALIZADO",
                                 {"dias": dias, "documento": doc,
                                  "com_contrato": com_vinculo, "com_prazo": tem_prazo})
                try:
                    db.table("mensagens").insert({
                        "caso_id": caso["id"], "canal": "CRM", "autor": "HUMANO",
                        "conteudo": f"⏳ 10 dias sem retorno do cliente sobre: {doc}. "
                                    "O caso NÃO foi arquivado automaticamente porque "
                                    + ("há prazo correndo. " if tem_prazo else
                                       "já existe contrato/processo. ")
                                    + "Decida o que fazer.",
                    }).execute()
                except Exception:
                    pass
            else:
                mudanca["estado"] = ESTADO_FRIO
                mudanca["aguardando_desde"] = None
                saida["arquivados"] += 1
                registrar_evento(caso["id"], "CASO_ARQUIVADO_LEAD_FRIO",
                                 {"dias": dias, "documento": doc})
                try:
                    db.table("mensagens").insert({
                        "caso_id": caso["id"], "canal": "CRM", "autor": "HUMANO",
                        "conteudo": f"🧊 Arquivado como lead frio: 10 dias sem "
                                    f"retorno sobre {doc}, sem contrato assinado. "
                                    "Volta sozinho à esteira se o cliente enviar "
                                    "o documento.",
                    }).execute()
                except Exception:
                    pass

        db.table("casos").update(mudanca).eq("id", caso["id"]).execute()
        saida["cobrancas"] += 1

    return {"ok": True, **saida}
