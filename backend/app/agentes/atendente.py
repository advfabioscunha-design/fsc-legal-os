"""
AGENTE DE ATENDIMENTO — responde o cliente olhando o estado real.

O problema que este módulo resolve é antigo e caro. O cliente escreve
"olá, como está meu contrato" e recebe uma resposta genérica, ou pior,
uma resposta que repete a pergunta que ele já respondeu ontem. Ele
conclui, com razão, que ninguém está olhando o caso dele.

A regra aqui é uma só: NINGUÉM RESPONDE SEM OLHAR.

Antes de escrever qualquer linha, o atendimento faz uma varredura do
que existe: em que fase o serviço está, quando foi a última ação, o
que ainda falta, qual é o prazo combinado e quanto dele já correu, o
que já foi dito nas últimas mensagens. Esse retrato vai para o modelo
como fato, e o modelo responde a partir dele. O que não estiver na
varredura não existe, e o atendimento diz que vai confirmar em vez de
inventar.

TRÊS COISAS QUE ELE SEMPRE FAZ

1. DIZ ONDE ESTÁ. Não "estamos cuidando", e sim a fase, com a data da
   última ação. Quem pergunta o andamento quer o andamento.

2. DIZ SE O PRAZO ESTÁ DE PÉ. Quando ainda há prazo, isso acalma mais
   do que qualquer adjetivo: "o combinado é entregar até quinta às 14h,
   e estamos dentro disso". Quando o prazo já passou, ele não maquia,
   avisa o escritório e diz ao cliente que avisou.

3. ESCUTA A URGÊNCIA. Se o cliente indica pressa, perda de negócio,
   audiência marcada ou qualquer coisa que não espere, o atendimento
   registra um alerta de prioridade alta para quem cuida do caso e
   informa isso ao cliente, com todas as letras. Urgência que fica só
   na conversa é urgência que ninguém viu.

E LÊ O QUE CHEGA

Documento enviado pelo cliente não fica esperando alguém abrir. O
atendimento lê o arquivo, transcreve o que está escrito e joga a
transcrição na mesma porta por onde entram as respostas de texto,
que é quem sabe preencher a informação que estava faltando. Uma foto
do RG do fiador tirada às 23h preenche o campo às 23h.

O QUE ELE NUNCA FAZ

Não promete resultado, não dá prazo que não foi combinado, não fala de
ferramenta, agente, robô ou revisão automática. Do lado do cliente
quem responde é o escritório, e é assim que o texto sai.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timedelta, timezone

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..core.texto import REGRA_DE_ESCRITA, humanizar


# ── Rótulos de fase, na língua do cliente ──────────────────────
#
# A tabela guarda REVISAO_ADV; o cliente lê "conferência final do
# escritório". Nenhum rótulo daqui menciona revisão automática nem
# etapa de máquina: o que o cliente contrata é o escritório.
FASE_PARA_O_CLIENTE = {
    "PAGAMENTO": "aguardando a confirmação do pagamento",
    "COLETA": "reunindo as informações do documento",
    "CIENCIA": "orientação e ciência",
    "REDACAO": "em elaboração",
    "REVISAO_IA": "em revisão",
    "AJUSTE": "em ajuste",
    "REVISAO_ADV": "em conferência final pelo escritório",
    "APROVACAO": "aguardando a sua aprovação",
    "ASSINATURA": "em assinatura",
    "ENTREGUE": "entregue",
    "ARQUIVADO": "arquivado",
}

ESTADO_PARA_O_CLIENTE = {
    "LEAD": "primeiro contato",
    "QUALIFICACAO": "levantamento das informações do caso",
    "ANALISE": "análise do caso pelo escritório",
    "PROPOSTA": "proposta enviada, aguardando a sua resposta",
    "CONTRATO": "contrato enviado para assinatura",
    "PAGAMENTO": "aguardando a confirmação do pagamento",
    "PETICAO": "preparando a petição",
    "PROTOCOLADO": "petição protocolada",
    "JUDICIAL": "em andamento no Judiciário",
    "ESCALADO_HUMANO": "com o advogado responsável",
    "AGENDADO": "reunião agendada",
    "ENCERRADO": "encerrado",
}

# ── O QUE SE PODE DIZER EM CADA FASE ───────────────────────────
#
# O rótulo da fase sozinho não segurava o modelo. Com "em elaboração"
# escrito na situação, ele ainda respondia que o contrato estava
# pronto, ou oferecia marcar uma reunião com advogado, que é um
# serviço que este balcão não vende. Rótulo é informação; o que faltava
# era limite.
#
# Cada fase passa a levar junto duas listas curtas: o que é verdade
# agora e o que não pode ser dito de jeito nenhum. Escrito assim,
# frase a frase, porque instrução genérica de "não invente" não segura
# um modelo que quer ser útil.
LIMITES_DA_FASE = {
    "PAGAMENTO": {
        "pode": "que o trabalho começa assim que o pagamento for confirmado, "
                "e que o PIX está na tela do pedido",
        "nao": "dizer que o documento já está sendo escrito, porque não está",
    },
    "COLETA": {
        "pode": "pedir as informações que faltam e explicar por que cada uma "
                "importa",
        "nao": "prometer data de entrega antes de as informações estarem "
               "completas",
    },
    "CIENCIA": {
        "pode": "explicar a orientação que está na tela e que o cliente "
                "escolhe entre adequar ou seguir assim mesmo",
        "nao": "decidir pelo cliente qual caminho ele deve escolher",
    },
    "REDACAO": {
        "pode": "que o documento está sendo escrito agora, e que ele segue "
                "para revisão e depois para a conferência final",
        "nao": "dizer que está pronto, que já foi revisado, que já pode ler "
               "ou que já foi enviado. Nada disso aconteceu ainda",
    },
    "REVISAO_IA": {
        "pode": "que o texto já existe e está sendo revisado",
        "nao": "dizer que está pronto ou mandar o cliente conferir agora",
    },
    "AJUSTE": {
        "pode": "que os pontos apontados na revisão estão sendo corrigidos",
        "nao": "dizer que está pronto ou detalhar o que a revisão apontou",
    },
    "REVISAO_ADV": {
        "pode": "que o escritório está com o documento para a conferência "
                "final, e que nada é enviado antes dela",
        "nao": "dar hora exata para essa conferência terminar",
    },
    "APROVACAO": {
        "pode": "que o documento está na tela para o cliente ler, aprovar ou "
                "pedir ajuste",
        "nao": "dizer que já está assinado ou entregue",
    },
    "ASSINATURA": {
        "pode": "que o documento foi para assinatura e que a via final chega "
                "por e-mail quando todos assinarem",
        "nao": "afirmar que alguém já assinou sem que a situação diga isso",
    },
    "ENTREGUE": {
        "pode": "que o documento foi entregue e até quando cabem ajustes sem "
                "custo",
        "nao": "dizer que ainda está sendo feito",
    },
    "ARQUIVADO": {
        "pode": "que o pedido foi arquivado e que dá para pedir o "
                "desarquivamento pela tela",
        "nao": "prometer reabertura automática",
    },
}


SYSTEM = """Você é o atendimento do escritório FC Advocacia e Recuperação
Patrimonial, falando com um cliente pela plataforma.

A SITUAÇÃO ABAIXO É A ÚNICA VERDADE QUE VOCÊ TEM. Ela foi levantada
agora, direto do sistema. Responda a partir dela e apenas dela. Se o
cliente perguntar algo que a situação não responde, diga com
naturalidade que vai confirmar e retornar, e não invente.

COMO RESPONDER

Comece dizendo onde o serviço está, com a data da última ação. Depois
responda exatamente o que ele perguntou. Nada de introdução longa.

Se houver prazo combinado e ele ainda não venceu, diga isso de forma
concreta: até quando é, e que está dentro do prazo. É a informação que
acalma. Se o prazo venceu, não disfarce: reconheça, e use a ferramenta
avisar_o_escritorio.

Se faltar alguma informação da parte do cliente, liste o que falta, na
íntegra, sem resumir. Lista resumida faz a pessoa voltar duas vezes.

Se o cliente demonstrar urgência, pressa, prejuízo iminente, prazo
próprio dele, audiência, negócio prestes a cair ou qualquer coisa que
não possa esperar, use a ferramenta avisar_o_escritorio e diga a ele,
com todas as letras, que o caso foi encaminhado como prioridade para o
advogado que cuida dele e que haverá retorno no menor tempo possível.
Nunca prometa hora exata.

LINGUAGEM

""" + REGRA_DE_ESCRITA + """

NUNCA REPITA A SI MESMO
Se a situação trouxer a lista de frases já usadas nesta conversa, não use
nenhuma delas de novo, nem variação próxima. Diga a mesma coisa de outro
jeito, ou não diga. Saudação e frase de fecho repetidas são o que faz a
pessoa perceber que não tem gente do outro lado.

Português do Brasil. No máximo dois parágrafos, salvo quando houver
lista do que falta. Trate o cliente pelo primeiro nome quando ele
constar da situação.

PROIBIDO, SEM EXCEÇÃO

Oferecer reunião, consulta, ligação, visita ou horário com advogado.
Este é o balcão de documentos, e agendamento não é serviço daqui. Se o
cliente pedir, diga que ele pode escrever aqui mesmo a qualquer hora e
que o escritório responde por este canal.

Dizer que o documento está pronto, revisado, disponível, assinado ou
entregue quando a fase da situação não disser exatamente isso. Essa é
a mentira mais cara que existe aqui: o cliente para de esperar,
descobre depois, e não volta.

Inventar data ou hora de entrega. O único prazo que existe é o que
está escrito na situação.

Falar em agente, sistema, robô, automação, inteligência artificial,
revisão automática ou esteira. Prometer resultado. Dar prazo que não
esteja na situação. Pedir dado que já consta da situação. Usar
travessão no lugar de vírgula ou de dois pontos."""

FERRAMENTAS = [
    {
        "name": "avisar_o_escritorio",
        "description": (
            "Registra um alerta de prioridade alta para quem cuida deste "
            "caso. Use quando o cliente demonstrar urgência real, quando o "
            "prazo combinado já tiver vencido, quando houver reclamação, ou "
            "quando a pergunta exigir uma decisão que o atendimento não "
            "pode tomar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {
                    "type": "string",
                    "description": "O que o cliente precisa, em uma frase.",
                },
                "gravidade": {
                    "type": "string",
                    "enum": ["ALTA", "MEDIA"],
                    "description": (
                        "ALTA quando há prazo vencido, prejuízo iminente ou "
                        "compromisso do cliente em risco."
                    ),
                },
            },
            "required": ["motivo"],
        },
    },
    # QUEM CALCULA É O CATÁLOGO, NUNCA O MODELO
    #
    # Sem esta ferramenta o atendimento tinha duas saídas ruins diante
    # de um cliente com pressa: dizer que não dava, o que é falso, ou
    # inventar um valor, o que é pior. Agora ele tem uma terceira, e
    # ela devolve o número certo e o PIX junto.
    {
        "name": "orcar_urgencia",
        "description": (
            "Calcula quanto custa acelerar este pedido para entrega em até 6 "
            "horas e devolve o valor e os dados do PIX. Use quando o cliente "
            "disser que está com pressa, que precisa para hoje, que o prazo "
            "dele mudou, ou perguntar se dá para adiantar. Só existe para "
            "pedido de contrato, e só antes da aprovação. Diga ao cliente o "
            "valor exato que a ferramenta devolver, e nunca outro."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def _claude():
    s = get_settings()
    if not s.claude_api_key:
        raise ValueError("Chave da Claude não configurada no servidor.")
    return anthropic.Anthropic(api_key=s.claude_api_key)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _br(iso_ou_dt) -> str:
    """Data e hora em Porto Velho, que é o fuso de quem lê."""
    t = iso_ou_dt if isinstance(iso_ou_dt, datetime) else _dt(iso_ou_dt)
    if not t:
        return "sem registro"
    local = t.astimezone(timezone(timedelta(hours=-4)))
    return local.strftime("%d/%m/%Y às %Hh%M")


def _faz_quanto(iso) -> str:
    t = _dt(iso) if not isinstance(iso, datetime) else iso
    if not t:
        return ""
    h = (_agora() - t).total_seconds() / 3600
    if h < 1:
        return "há menos de uma hora"
    if h < 24:
        return f"há {int(h)} hora{'s' if int(h) != 1 else ''}"
    return f"há {int(h // 24)} dia{'s' if int(h // 24) != 1 else ''}"


# ── A VARREDURA ────────────────────────────────────────────────
#
# É o coração do módulo. Tudo o que o atendimento pode afirmar sai
# daqui, e nada mais. Manter a varredura como função separada, que
# devolve dicionário, permite testá-la sem gastar uma chamada de
# modelo e permite mostrá-la na tela do operador quando for útil.

def situacao_do_pedido(pedido_id: str) -> dict:
    """Retrato do pedido do balcão neste instante."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("*, clientes(nome,email,whatsapp)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    cli = p.get("clientes") or {}

    # A última ação é a mais recente entre os carimbos que existem.
    # Olhar só `atualizado_em` diria "agora" sempre, porque qualquer
    # gravação o mexe, inclusive a que registrou a pergunta.
    marcos = {
        "pagamento confirmado": p.get("pago_em"),
        "informações recebidas": p.get("fase_em") if p.get("fase") != "COLETA" else None,
        "documento redigido": p.get("redigido_em"),
        "documento revisado": p.get("revisado_em"),
        "ajustes aplicados": p.get("ajustado_em"),
        "conferência final concluída": p.get("visto_advogado_em"),
        "documento disponibilizado a você": p.get("disponibilizado_em"),
        "aprovado por você": p.get("aprovado_cliente_em"),
        "entregue": p.get("entregue_em"),
    }
    ultima = ("pedido aberto", p.get("criado_em"))
    for rotulo, quando in marcos.items():
        t, u = _dt(quando), _dt(ultima[1])
        if t and (not u or t > u):
            ultima = (rotulo, quando)

    # O prazo combinado corre do pagamento, que é quando o trabalho
    # começa. Antes disso não há prazo nenhum, e dizer que há seria
    # prometer o que não foi contratado.
    horas = int(p.get("prazo_entrega_horas") or 24)
    pago = _dt(p.get("pago_em"))
    limite = pago + timedelta(hours=horas) if pago else None
    entregue = _dt(p.get("entregue_em")) or _dt(p.get("disponibilizado_em"))
    if limite and entregue:
        dentro = entregue <= limite
    elif limite:
        dentro = _agora() <= limite
    else:
        dentro = None

    pend = p.get("pendencias") or []
    falta_trava = [i.get("rotulo") for i in pend
                   if not i.get("atendida") and i.get("obrigatorio")]
    falta_extra = [i.get("rotulo") for i in pend
                   if not i.get("atendida") and not i.get("obrigatorio")]

    msgs = db.table("pedidos_mensagens").select("autor,texto,criado_em") \
        .eq("pedido_id", pedido_id).order("criado_em", desc=True) \
        .limit(8).execute().data or []
    docs = db.table("pedidos_documentos").select("nome,criado_em,enviado_por") \
        .eq("pedido_id", pedido_id).order("criado_em", desc=True) \
        .limit(6).execute().data or []

    nome = (cli.get("nome") or "").strip()
    servico = p.get("servico_livre") if p.get("tipo") == "OUTRO" else \
        str(p.get("tipo") or "").replace("_", " ").lower()

    return {
        "escopo": "PEDIDO",
        "id": pedido_id,
        "numero": p.get("numero"),
        "cliente": nome,
        "primeiro_nome": nome.split(" ")[0] if nome else "",
        "servico": servico,
        "fase": p.get("fase"),
        "fase_rotulo": FASE_PARA_O_CLIENTE.get(p.get("fase"), p.get("fase")),
        "ultima_acao": ultima[0],
        "ultima_acao_em": ultima[1],
        "valor": float(p.get("valor") or 0),
        "urgente": bool(p.get("urgente")),
        "urgencia_valor": p.get("urgencia_valor"),
        "urgencia_aguardando_pagamento": bool(p.get("urgencia_pedida_em"))
        and not p.get("urgencia_confirmada_em") and not p.get("urgente"),
        "prazo_horas": horas,
        "prazo_limite": limite.isoformat() if limite else None,
        "dentro_do_prazo": dentro,
        "relogio_parado": p.get("avanca_em") is None and p.get("fase") in (
            "REDACAO", "REVISAO_IA", "AJUSTE"),
        "falta_indispensavel": falta_trava,
        "falta_complementar": falta_extra,
        "prazo_alteracao_ate": p.get("prazo_alteracao_ate"),
        "documentos": [d.get("nome") for d in docs],
        "mensagens": list(reversed(msgs)),
    }


def situacao_do_caso(caso_id: str) -> dict:
    """Retrato do processo judicial ou da causa em análise."""
    db = get_db()
    r = db.table("casos").select("*, clientes(nome,email,whatsapp)") \
        .eq("id", caso_id).limit(1).execute().data
    if not r:
        raise ValueError("Caso não encontrado.")
    c = r[0]
    cli = c.get("clientes") or {}

    intimacoes = db.table("intimacoes") \
        .select("conteudo,data_movimento,prazo_em,status") \
        .eq("caso_id", caso_id).order("data_movimento", desc=True) \
        .limit(3).execute().data or []
    prazos = db.table("prazos").select("titulo,data,status") \
        .eq("caso_id", caso_id).eq("status", "ABERTO") \
        .order("data").limit(3).execute().data or []
    msgs = db.table("mensagens").select("autor,conteudo,criado_em") \
        .eq("caso_id", caso_id).order("criado_em", desc=True) \
        .limit(8).execute().data or []

    ultimo_movimento = intimacoes[0] if intimacoes else None
    nome = (cli.get("nome") or "").strip()

    return {
        "escopo": "CASO",
        "id": caso_id,
        "cliente": nome,
        "primeiro_nome": nome.split(" ")[0] if nome else "",
        "estado": c.get("estado"),
        "estado_rotulo": ESTADO_PARA_O_CLIENTE.get(c.get("estado"), c.get("estado")),
        "grupo": c.get("grupo"),
        "numero_processo": c.get("numero_processo"),
        "tribunal": c.get("tribunal"),
        "ultima_acao_em": c.get("atualizado_em"),
        "ultimo_movimento": ultimo_movimento,
        "prazos_abertos": prazos,
        "sob_conducao_humana": c.get("estado") in ("ESCALADO_HUMANO", "AGENDADO"),
        "mensagens": list(reversed([
            {"autor": m.get("autor"), "texto": m.get("conteudo"),
             "criado_em": m.get("criado_em")} for m in msgs])),
    }


def _texto_da_situacao(s: dict) -> str:
    """A varredura escrita em português, que é o que o modelo lê."""
    L: list[str] = []
    if s["escopo"] == "PEDIDO":
        L.append(f"Serviço: {s['servico']}, protocolo {s['numero']}.")
        L.append(f"Cliente: {s['cliente'] or 'não informado'}.")
        L.append(f"Fase atual: {s['fase_rotulo']}.")
        lim = LIMITES_DA_FASE.get(s["fase"])
        if lim:
            L.append(f"NESTA FASE VOCÊ PODE DIZER: {lim['pode']}.")
            L.append(f"NESTA FASE É PROIBIDO: {lim['nao']}.")
        L.append(f"Última ação: {s['ultima_acao']}, em {_br(s['ultima_acao_em'])} "
                 f"({_faz_quanto(s['ultima_acao_em'])}).")
        if s["prazo_limite"]:
            L.append(f"Prazo combinado: {s['prazo_horas']} horas a contar do "
                     f"pagamento, ou seja, até {_br(s['prazo_limite'])}.")
            if s["dentro_do_prazo"] is True:
                L.append("O prazo AINDA NÃO VENCEU. Diga isso ao cliente.")
            elif s["dentro_do_prazo"] is False:
                L.append("ATENÇÃO: o prazo combinado JÁ VENCEU. Reconheça, "
                         "peça desculpa em uma linha e avise o escritório.")
        else:
            L.append("Ainda não há prazo correndo: ele começa quando o "
                     "pagamento é confirmado.")
        if s["falta_indispensavel"]:
            L.append("FALTA, e sem isso o documento não se conclui: "
                     + "; ".join(s["falta_indispensavel"]) + ".")
            L.append("Enquanto faltar, o relógio do prazo fica parado, e é "
                     "justo dizer isso ao cliente sem soar como cobrança.")
        if s["falta_complementar"]:
            L.append("Falta, mas pode vir depois e não atrasa: "
                     + "; ".join(s["falta_complementar"]) + ".")
        if s["prazo_alteracao_ate"]:
            L.append(f"Ajustes sem custo até {s['prazo_alteracao_ate']}.")
        if s.get("urgente"):
            L.append("Este pedido JÁ tem urgência contratada, entrega em até "
                     "6 horas. Não ofereça urgência de novo.")
        elif s.get("urgencia_aguardando_pagamento"):
            L.append(f"A urgência já foi orçada em "
                     f"R$ {float(s.get('urgencia_valor') or 0):.2f} e está "
                     f"esperando o pagamento. Não orce de novo: lembre o "
                     f"cliente de que o PIX está na tela do pedido e que o "
                     f"prazo muda assim que o escritório conferir.")
        elif s["fase"] in ("COLETA", "CIENCIA", "REDACAO", "REVISAO_IA",
                           "AJUSTE", "REVISAO_ADV"):
            L.append("Se o cliente disser que está com pressa, que precisa "
                     "para hoje ou que o prazo dele mudou, use a ferramenta "
                     "orcar_urgencia. Ela devolve o valor e o PIX. Nunca diga "
                     "um valor que não tenha vindo dela.")
        if s["documentos"]:
            L.append("Documentos já recebidos: " + ", ".join(s["documentos"]) + ".")
    else:
        L.append(f"Cliente: {s['cliente'] or 'não informado'}.")
        L.append(f"Situação do caso: {s['estado_rotulo']}.")
        if s["numero_processo"]:
            L.append(f"Processo {s['numero_processo']}"
                     + (f", {s['tribunal']}" if s["tribunal"] else "") + ".")
        L.append(f"Última movimentação registrada no sistema: "
                 f"{_br(s['ultima_acao_em'])} ({_faz_quanto(s['ultima_acao_em'])}).")
        mv = s["ultimo_movimento"]
        if mv:
            L.append("Último andamento: "
                     + str(mv.get("conteudo") or "")[:400]
                     + f" (movimento de {_br(mv.get('data_movimento'))}).")
        if s["prazos_abertos"]:
            L.append("Prazos em aberto no escritório: " + "; ".join(
                f"{p.get('titulo')} até {p.get('data')}" for p in s["prazos_abertos"]
            ) + ".")
            L.append("O escritório está DENTRO do prazo para esses atos. "
                     "Pode dizer isso ao cliente.")
        if s["sob_conducao_humana"]:
            L.append("Este caso está sob condução direta do advogado. "
                     "Não prometa nada; registre o pedido e diga que ele "
                     "será retornado pelo advogado responsável.")

    if s["mensagens"]:
        L.append("\nÚltimas mensagens desta conversa, da mais antiga para a "
                 "mais nova:")
        for m in s["mensagens"]:
            quem = "cliente" if str(m.get("autor", "")).upper() == "CLIENTE" \
                else "escritório"
            L.append(f"  [{quem}, {_br(m.get('criado_em'))}] "
                     + str(m.get("texto") or "")[:500])

        # O QUE VOCÊ JÁ DISSE, PARA NÃO DIZER DE NOVO
        #
        # Instrução genérica de "varie o texto" não funciona: o modelo
        # responde ao último turno e não relê a própria conversa
        # procurando repetição. A lista das aberturas e dos fechos já
        # usados vai escrita, como o resto da varredura.
        usados = _frases_ja_usadas(s["mensagens"])
        if usados:
            L.append("\nFRASES QUE O ESCRITÓRIO JÁ USOU NESTA CONVERSA. Não "
                     "repita nenhuma delas, nem variação próxima. Diga a "
                     "mesma coisa de outro jeito:")
            for u in usados:
                L.append(f"  · {u}")
    return "\n".join(L)


def _frases_ja_usadas(mensagens: list[dict]) -> list[str]:
    """Primeira e última frase de cada fala do escritório.

    São as duas posições em que a repetição aparece e incomoda: a
    saudação de abertura e o convite do fim. O meio muda sozinho,
    porque responde ao que o cliente escreveu."""
    vistos: list[str] = []
    for m in mensagens:
        if str(m.get("autor", "")).upper() == "CLIENTE":
            continue
        texto = (m.get("texto") or "").strip()
        if not texto:
            continue
        frases = [f.strip() for f in re.split(r"(?<=[.?!])\s+", texto) if f.strip()]
        for f in ([frases[0]] if frases else []) + ([frases[-1]] if len(frases) > 1 else []):
            f = f[:160]
            if f and f not in vistos:
                vistos.append(f)
    return vistos[-10:]


# ── O ALERTA PARA QUEM CUIDA DO CASO ───────────────────────────

def avisar_o_escritorio(escopo: str, alvo_id: str, motivo: str,
                        gravidade: str = "ALTA",
                        pergunta: str = "") -> dict:
    """Uma tarefa de prioridade alta, na data de hoje.

    Tarefa, e não e-mail interno: e-mail se perde na caixa, tarefa
    aparece no plano do dia de quem trabalha e cobra conclusão."""
    db = get_db()
    hoje = _agora().astimezone(timezone(timedelta(hours=-4))).date().isoformat()
    linha = {
        "titulo": f"Cliente pediu prioridade: {motivo[:120]}",
        "descricao": (f"Pedido do cliente pelo atendimento.\n\n"
                      f"O que ele escreveu: {pergunta[:1500]}\n\n"
                      f"Motivo identificado: {motivo[:500]}"),
        "origem": "CONTRATO" if escopo == "PEDIDO" else "TRIAGEM",
        "data": hoje,
        "prioridade": "ALTA" if gravidade.upper() == "ALTA" else "MEDIA",
        "motivo": "Urgência relatada pelo cliente no atendimento.",
        "criado_por": "ATENDIMENTO",
    }
    if escopo == "PEDIDO":
        linha["pedido_id"] = alvo_id
    else:
        linha["caso_id"] = alvo_id

    criada = None
    try:
        criada = db.table("tarefas").insert(linha).execute().data
    except Exception as e:
        print(f"[atendimento] tarefa de urgência não criada: {e}")

    registrar_evento(alvo_id if escopo == "CASO" else None,
                     "ATENDIMENTO_URGENCIA",
                     {"escopo": escopo, "alvo": alvo_id, "motivo": motivo,
                      "gravidade": gravidade})
    return {"avisado": True, "tarefa": (criada or [{}])[0].get("id")}


# ── A RESPOSTA ─────────────────────────────────────────────────

def responder(escopo: str, alvo_id: str, pergunta: str) -> dict:
    """Varre, pensa e devolve o texto da resposta.

    Não grava nada na conversa: quem grava é quem chamou, porque só
    ele sabe por quais canais a resposta deve sair."""
    situacao = (situacao_do_pedido(alvo_id) if escopo == "PEDIDO"
                else situacao_do_caso(alvo_id))
    s = get_settings()

    contexto = (
        "SITUAÇÃO LEVANTADA AGORA NO SISTEMA\n"
        "===================================\n"
        + _texto_da_situacao(situacao)
        + "\n\nPERGUNTA DO CLIENTE\n===================\n"
        + pergunta.strip()
    )

    texto, avisos = "", []
    mensagens: list[dict] = [{"role": "user", "content": contexto}]
    try:
        cliente = _claude()
        # DUAS VOLTAS, E A SEGUNDA É A QUE IMPORTA
        #
        # Numa volta só, quando o modelo usa a ferramenta de urgência
        # ele devolve o pedido de ferramenta e mais nada: a resposta
        # ficava vazia e caía no texto de reserva, que é justamente o
        # "recebi e retorno depois" que não diz nada. Devolvendo o
        # resultado da ferramenta, ele volta e escreve a resposta de
        # verdade, já sabendo que o alerta foi registrado.
        for _ in range(3):
            r = cliente.messages.create(
                model=s.claude_model,
                max_tokens=700,
                system=SYSTEM,
                tools=FERRAMENTAS,
                messages=mensagens,
            )
            usos = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
            texto = "".join(b.text for b in r.content
                            if getattr(b, "type", "") == "text").strip() or texto
            if not usos:
                break
            mensagens.append({"role": "assistant", "content": r.content})
            resultados = []
            for u in usos:
                if u.name == "avisar_o_escritorio":
                    d = u.input or {}
                    saida = avisar_o_escritorio(
                        escopo, alvo_id, d.get("motivo", "sem motivo declarado"),
                        d.get("gravidade", "ALTA"), pergunta)
                    avisos.append(saida)
                elif u.name == "orcar_urgencia" and escopo == "PEDIDO":
                    from . import contratos_online
                    try:
                        saida = contratos_online.orcar_urgencia(alvo_id)
                    except Exception as e:
                        saida = {"erro": str(e)}
                else:
                    saida = {"erro": "ferramenta desconhecida"}
                resultados.append({"type": "tool_result", "tool_use_id": u.id,
                                   "content": json.dumps(saida, ensure_ascii=False)})
            mensagens.append({"role": "user", "content": resultados})
    except Exception as e:
        print(f"[atendimento] não consegui responder agora: {e}")
        # Silêncio é pior do que uma frase honesta. O cliente precisa
        # saber que a mensagem chegou.
        return {"texto": ("Recebi a sua mensagem e ela já está registrada no "
                          "seu pedido. Vou conferir o andamento e retorno em "
                          "seguida."),
                "situacao": situacao, "avisos": [], "falhou": True}

    texto = humanizar(texto or "")
    if not texto:
        texto = ("Recebi a sua mensagem. Vou conferir o andamento e retorno "
                 "em seguida.")
    return {"texto": texto, "situacao": situacao, "avisos": avisos}


# ── LEITURA DO DOCUMENTO QUE O CLIENTE MANDA ───────────────────
#
# O caminho é: baixa o arquivo, transcreve, e entrega a transcrição
# para quem já sabe preencher pendência a partir de texto livre. Ter
# duas etapas em vez de uma é de propósito: a transcrição fica
# guardada e auditável, e quem preenche continua sendo um só lugar.

_TIPOS_IMAGEM = {"image/jpeg", "image/jpg", "image/png", "image/webp",
                 "image/gif"}

PROMPT_TRANSCRICAO = """Transcreva o documento em anexo.

Escreva em português do Brasil, em texto corrido, TUDO o que estiver
legível: nomes completos, CPF, CNPJ, RG quando houver, endereços,
datas, valores, números de matrícula, de contrato ou de processo,
qualificação das partes, e o teor das cláusulas ou do conteúdo.

Comece por uma linha dizendo que documento é este, no formato:
TIPO: <o que é, por exemplo: CNH, comprovante de residência, matrícula
de imóvel, contrato de locação anterior, holerite>

Depois transcreva. Não resuma, não interprete, não comente, não opine.
Se algum trecho estiver ilegível, escreva [ilegível] no lugar, e siga.
Se o arquivo não tiver nada legível, responda apenas: SEM CONTEUDO."""


def transcrever_documento(documento_id: str) -> dict:
    """Lê o arquivo e devolve o que está escrito nele."""
    s, db = get_settings(), get_db()
    r = db.table("pedidos_documentos").select("*").eq("id", documento_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Documento não encontrado.")
    doc = r[0]

    mime = (doc.get("tipo_mime") or "").lower()
    if mime not in _TIPOS_IMAGEM and mime != "application/pdf":
        return {"transcrito": False, "motivo": f"formato não lido: {mime}"}

    try:
        conteudo = db.storage.from_(s.bucket_documentos).download(doc["url"])
    except Exception as e:
        return {"transcrito": False, "motivo": f"não consegui abrir: {e}"}

    # Acima disso a chamada fica cara e lenta sem ganho real: documento
    # de identidade e comprovante cabem folgados em poucos megabytes.
    if len(conteudo) > 12 * 1024 * 1024:
        return {"transcrito": False, "motivo": "arquivo grande demais para leitura"}

    dado = base64.standard_b64encode(conteudo).decode("ascii")
    anexo = ({"type": "document",
              "source": {"type": "base64", "media_type": "application/pdf",
                         "data": dado}}
             if mime == "application/pdf" else
             {"type": "image",
              "source": {"type": "base64",
                         "media_type": "image/jpeg" if mime == "image/jpg" else mime,
                         "data": dado}})

    try:
        r = _claude().messages.create(
            model=s.claude_model,
            max_tokens=2000,
            messages=[{"role": "user",
                       "content": [anexo, {"type": "text",
                                           "text": PROMPT_TRANSCRICAO}]}],
        )
        texto = "".join(b.text for b in r.content if b.type == "text").strip()
    except Exception as e:
        return {"transcrito": False, "motivo": f"leitura falhou: {e}"}

    if not texto or texto.upper().startswith("SEM CONTEUDO"):
        return {"transcrito": False, "motivo": "nada legível no arquivo"}

    # A transcrição fica no próprio registro do documento. Quem abrir a
    # pasta do pedido lê o que o sistema entendeu, e não precisa
    # confiar na palavra de ninguém.
    try:
        db.table("pedidos_documentos").update({
            "transcricao": texto[:20000],
            "transcrito_em": _agora().isoformat(),
        }).eq("id", documento_id).execute()
    except Exception as e:
        print(f"[atendimento] transcrição não gravada no documento: {e}")

    return {"transcrito": True, "texto": texto, "nome": doc.get("nome"),
            "pedido_id": doc.get("pedido_id")}


def ler_e_encaminhar(pedido_id: str, documentos: list[dict]) -> dict:
    """Lê os arquivos que acabaram de chegar e preenche o que faltava.

    Roda depois do upload, fora do caminho da resposta, para o cliente
    não ficar olhando uma barra de progresso enquanto o documento é
    lido. Falha aqui não perde o arquivo: ele já está guardado, e o
    operador continua podendo abrir e digitar."""
    from . import contratos_online

    lidos, preenchidos = [], 0
    partes: list[str] = []
    for d in documentos or []:
        try:
            r = transcrever_documento(d["id"])
        except Exception as e:
            print(f"[atendimento] documento não lido: {e}")
            continue
        if not r.get("transcrito"):
            continue
        lidos.append(d.get("nome"))
        partes.append(f"[{d.get('nome')}]\n{r['texto']}")

    if not partes:
        return {"lidos": 0, "preenchidos": 0}

    transcricao = "\n\n".join(partes)
    # A transcrição entra pela mesma porta da resposta escrita. É ela
    # que sabe casar cada dado com a pendência que o esperava e que
    # destrava o relógio quando o que faltava chega.
    try:
        saida = contratos_online.complementar_com_a_resposta(
            pedido_id,
            "Segue o que consta nos documentos que enviei:\n\n" + transcricao)
        preenchidos = int(saida.get("preenchidos") or 0)
    except Exception as e:
        print(f"[atendimento] transcrição não aproveitada agora: {e}")
        saida = {}

    # A conversa registra o que foi lido e o que entrou. Sem esta
    # linha, o cliente manda a foto e não vê nada acontecer.
    try:
        db = get_db()
        if preenchidos:
            aviso = (f"Recebi e li {'o documento' if len(lidos) == 1 else 'os documentos'} "
                     + ", ".join(str(x) for x in lidos)
                     + f". Já aproveitei {preenchidos} informação"
                     + ("ões" if preenchidos > 1 else "")
                     + " que estavam faltando.")
        else:
            aviso = ("Recebi e li " + ("o documento " if len(lidos) == 1
                                       else "os documentos ")
                     + ", ".join(str(x) for x in lidos)
                     + ". Está guardado com o seu pedido.")
        falta = (saida.get("pendencias") or {}).get("obrigatorias") or []
        if falta:
            aviso += (" Ainda preciso de: "
                      + "; ".join(str(f.get("rotulo") or f) for f in falta) + ".")
        db.table("pedidos_mensagens").insert({
            "pedido_id": pedido_id, "autor": "AGENTE",
            "texto": aviso[:4000], "canais": ["PLATAFORMA"],
        }).execute()
    except Exception as e:
        print(f"[atendimento] aviso de leitura não registrado: {e}")

    registrar_evento(None, "ATENDIMENTO_DOCUMENTO_LIDO",
                     {"pedido_id": pedido_id, "arquivos": lidos,
                      "preenchidos": preenchidos})
    return {"lidos": len(lidos), "arquivos": lidos, "preenchidos": preenchidos}
