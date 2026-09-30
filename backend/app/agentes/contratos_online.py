"""
Balcão de contratos — do pedido do cliente ao documento assinado.

O caminho, e o que cada etapa protege:

  COLETA      o atendente pergunta o que o tipo de contrato exige
  CIENCIA     quando o combinado foge da lei, o cliente lê o que a lei
              diz e escolhe: adequar ou seguir assim mesmo. A escolha
              fica registrada com data, hora e versão do texto
  PAGAMENTO   PIX; o trabalho começa depois de confirmado
  REDACAO     o redator escreve seguindo a lei do tipo
  REVISAO_IA  o revisor lê a íntegra e anota o que precisa mudar
  AJUSTE      o redator corrige — este botão só abre depois da revisão
  REVISAO_ADV o advogado lê e aprova. Nada chega ao cliente sem isso
  APROVACAO   o cliente vê com marca d'água e aprova ou pede mudança
  ASSINATURA  assinatura eletrônica; cópia por e-mail quando todos
              tiverem assinado
  ENTREGUE    fica 7 dias à vista e depois vai para o arquivo

SOBRE ORIENTAR E PROSSEGUIR
---------------------------
O escritório não recusa o serviço porque o cliente quer algo fora do
usual. Orienta com clareza, registra a ciência e segue. Mas há duas
situações diferentes, e tratá-las igual seria desonesto:

  RISCO      a cláusula vale, só não produz o efeito que o cliente
             imagina, ou pode ser revista em juízo. Ciência resolve:
             ele decide com a informação na mão.

  NULIDADE   a lei diz que aquilo não tem efeito nenhum (garantia
             dupla na locação, por exemplo). Aqui a ciência também é
             registrada, e o texto diz com todas as letras que a
             cláusula é nula — mas quem decide se entra no documento é
             o advogado na revisão humana, não o cliente e não a
             máquina. É para isso que existe aquela etapa.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from . import catalogo_contratos as catalogo

VERSAO_TERMO = "2026-09-v1"
VERSAO_CONTRATACAO = "2026-09-v1"


def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def termo_de_contratacao(tipo: str, com_orientacao: bool = False,
                         pedido: dict | None = None) -> dict:
    """As regras da contratação, em texto curto, antes de começar.

    Curto de propósito: termo que ninguém lê não informa ninguém, e o
    que interessa aqui cabe em uma tela — o que o escritório faz, por
    quanto, em quanto tempo, e o que acontece se o cliente desistir.

    O TERMO LÊ O PEDIDO, NÃO A TABELA
    Antes ele mostrava sempre o preço cheio, mesmo quando o cliente
    tinha negociado 20% ou tido a própria proposta aceita. A pessoa
    assinava um texto que dizia um valor e pagava outro, o que é o tipo
    de incoerência que ninguém percebe na hora e todo mundo lembra na
    discussão. Agora o valor sai do pedido, com o desconto, a urgência
    e a proposta aceita discriminados."""
    t = catalogo.detalhe(tipo) or {}
    p = pedido or {}

    valor = float(p.get("valor") or 0) or catalogo.preco(tipo, com_orientacao)
    base = float(p.get("valor_base") or 0)
    desconto = float(p.get("desconto_pct") or 0)
    urgente = bool(p.get("urgente"))
    horas = int(p.get("prazo_entrega_horas") or (
        catalogo.HORAS_URGENTE if urgente else catalogo.HORAS_PADRAO))
    por_proposta = p.get("proposta_status") == "ACEITA"

    linhas = [
        f"CONTRATAÇÃO DE SERVIÇO, {t.get('nome', tipo)}",
        "",
        "O QUE O ESCRITÓRIO FAZ",
        f"Elabora o documento conforme a legislação aplicável "
        f"({t.get('base_legal', ',')}), com revisão e conferência antes de "
        f"ser enviado a você, e disponibiliza assinatura eletrônica com "
        f"validade jurídica (Lei 14.063/2020 e MP 2.200-2/2001).",
        "",
        "VALOR E PAGAMENTO",
        f"{_reais(valor)}, por PIX, à vista. O trabalho começa depois do "
        f"pagamento confirmado.",
    ]

    # A conta, aberta. Só aparece o que de fato aconteceu nesta
    # negociação: linha de desconto sem desconto é ruído.
    detalhe = []
    if base and base != valor:
        detalhe.append(f"Valor de tabela deste documento: {_reais(base)}.")
    if desconto:
        detalhe.append(f"Desconto combinado no atendimento: {desconto:.0f}%.")
    if urgente:
        detalhe.append(
            f"Acréscimo de urgência: entrega em até {horas} horas em vez de "
            f"{catalogo.HORAS_PADRAO}.")
    if p.get("assinatura_digital") is False:
        detalhe.append("Sem assinatura eletrônica, com o desconto "
                       "correspondente. O documento é entregue para baixar.")
    if por_proposta:
        detalhe.append(
            f"Este valor é a proposta que você apresentou e que o escritório "
            f"aceitou em {_br(p.get('proposta_respondida_em'))}.")
    if detalhe:
        linhas += ["", "COMO SE CHEGOU A ESSE VALOR"] + detalhe

    if com_orientacao or p.get("com_orientacao"):
        linhas += ["Inclui atendimento jurídico prévio, por vídeo, com gravação "
                   "de áudio e transcrição, mediante seu consentimento na sala."]
    linhas += [
        "",
        "PRAZO DE ENTREGA",
        f"A primeira versão fica pronta em até {horas} horas contadas do "
        f"pagamento confirmado e do recebimento de todos os dados e "
        f"documentos que o escritório pedir. Cada pedido de alteração seu "
        f"reinicia a contagem.",
    ]
    if urgente:
        linhas += ["Você contratou a entrega urgente: o prazo é de 6 horas, e "
                   "ele só começa quando as informações estiverem completas."]
    linhas += [
        "",
        "REVISÃO E APROVAÇÃO, E O PRAZO DE 7 DIAS",
        "Quando o documento ficar pronto, ele é disponibilizado na sua área "
        "na plataforma e você é avisado por e-mail. A partir dessa "
        "disponibilização você tem 7 dias corridos para ler, pedir alteração "
        "e aprovar.",
        "Passados os 7 dias sem aprovação e sem pedido de alteração, a "
        "solicitação é arquivada automaticamente. O documento não se perde: "
        "para retomá-lo, basta abrir um chamado de desarquivamento na sua "
        "área, explicando o motivo. O escritório analisa e responde.",
        "",
        "REVISÕES",
        "Dentro dos 7 dias você pode pedir alterações quantas vezes precisar, "
        "desde que dentro do que foi contratado. Mudar o tipo de contrato ou "
        "incluir objeto novo é outro serviço.",
        "",
        "O QUE NÃO ESTÁ INCLUÍDO",
        "Custas de cartório, registro, reconhecimento de firma, taxas e "
        "tributos da sua negociação. Representação em processo judicial "
        "também é contratação separada.",
        "",
        "DESISTÊNCIA",
        "Antes de o documento ser redigido, a devolução é integral. Depois "
        "de redigido, o valor não é devolvido, porque o serviço foi "
        "prestado, o documento é seu e fica disponível.",
        "",
        "SEUS DADOS",
        "Seus dados e documentos são usados apenas para elaborar o que você "
        "pediu, conforme a Política de Privacidade do escritório.",
        "",
        f"Versão: {VERSAO_CONTRATACAO}",
    ]
    return {"versao": VERSAO_CONTRATACAO, "tipo": tipo, "valor": valor,
            "horas": horas, "urgente": urgente, "desconto_pct": desconto,
            "por_proposta": por_proposta, "texto": "\n".join(linhas)}


def _br(iso: str | None) -> str:
    """Data em português, ou nada. Usada só no texto do termo."""
    if not iso:
        return ""
    s = str(iso)
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}"


def aceitar_contratacao(pedido_id: str, termo: dict, ip: str | None = None) -> dict:
    """Registra o aceite na mesma trilha das demais ciências: o texto
    inteiro, a versão, a data e o IP."""
    db = get_db()
    row = db.table("pedidos_ciencias").insert({
        "pedido_id": pedido_id,
        "versao": f"CONTRATACAO-{termo.get('versao')}",
        "texto": termo.get("texto"),
        "pontos": None,
        "escolha": "ACEITO",
        "ip": ip,
    }).execute().data[0]
    db.table("pedidos_contrato").update({
        "fase": "PAGAMENTO", "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATACAO_ACEITA",
                     {"pedido": pedido_id, "versao": termo.get("versao")})
    return row

# A ORDEM DAS FASES
#
# O pagamento era a terceira etapa: o cliente preenchia tudo, lia a
# orientação e só então pagava. Isso põe o trabalho antes do sim, e o
# escritório coletava dados de quem ainda podia desistir.
#
# Agora o pagamento é a primeira. Confirmado o PIX, o atendimento volta
# e pergunta o que o documento exige. É também quando se pergunta sobre
# timbre ou folha branca: antes disso a pergunta não significa nada
# para quem nem sabe se vai contratar.
FASES = [
    "PAGAMENTO", "COLETA", "CIENCIA", "REDACAO", "REVISAO_IA", "AJUSTE",
    "REVISAO_ADV", "APROVACAO", "ASSINATURA", "ENTREGUE", "ARQUIVADO",
]


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Termo de ciência ────────────────────────────────────────────
def termo_de_ciencia(tipo: str, regras_violadas: list[str],
                     dados: dict | None = None) -> dict:
    """Monta o texto que o cliente lê antes de decidir.

    O texto explica, para cada ponto: o que a lei diz, o que acontece
    na prática se seguir do jeito combinado, e qual é a alternativa
    dentro da lei. Sem juridiquês e sem suavizar — o cliente está
    assumindo uma consequência, e precisa saber qual."""
    t = catalogo.detalhe(tipo)
    if not t:
        raise ValueError("Tipo de contrato desconhecido.")

    itens = []
    for r in t.get("regras", []):
        if r["quando"] in regras_violadas:
            itens.append({
                "ponto": r["quando"],
                "o_que_a_lei_diz": r["diz"],
                "como_adequar": r["adequar"],
            })

    # O alerta do tipo (escritura pública, registro em CTPS, cartório de
    # títulos) entra sempre que existir, mesmo sem regra violada: é
    # limite do documento, não escolha do cliente.
    alerta = t.get("alerta")

    partes = [
        f"CIÊNCIA E DECISÃO, {t['nome']}",
        "",
        f"Base legal aplicável: {t['base_legal']}.",
        "",
    ]
    if alerta:
        partes += ["O QUE ESTE DOCUMENTO FAZ E O QUE NÃO FAZ", "", alerta, ""]
    if itens:
        partes.append("PONTOS DO QUE VOCÊ COMBINOU QUE FOGEM DA LEI")
        partes.append("")
        for i, it in enumerate(itens, 1):
            partes += [
                f"{i}. {it['o_que_a_lei_diz']}",
                f"   Como ficaria dentro da lei: {it['como_adequar']}",
                "",
            ]
    partes += [
        "SUA DECISÃO",
        "",
        "Você pode escolher adequar o contrato à lei, e nesse caso é só "
        "avisar o atendente o que prefere mudar. Ou pode escolher seguir "
        "com o que foi combinado entre as partes, ciente do que está "
        "escrito acima.",
        "",
        "Ao clicar em CIENTE E QUERO PROSSEGUIR, você declara que leu e "
        "entendeu as orientações acima, que elas lhe foram prestadas "
        "antes da elaboração do documento, e que opta por seguir assim "
        "mesmo, por sua conta e risco.",
        "",
        "O escritório continua responsável por redigir o documento com "
        "técnica e clareza; não responde pelo efeito de cláusula que "
        "você optou por manter contra a orientação dada.",
        "",
        f"Versão do termo: {VERSAO_TERMO}",
    ]

    return {
        "versao": VERSAO_TERMO,
        "tipo": tipo,
        "texto": "\n".join(partes),
        "pontos": itens,
        "alerta": alerta,
        "precisa_advogado": bool(itens),   # nulidade vai à revisão humana
    }


def registrar_ciencia(pedido_id: str, termo: dict, escolha: str,
                      ip: str | None = None) -> dict:
    """Guarda a decisão. `escolha`: PROSSEGUIR ou ADEQUAR."""
    if escolha not in ("PROSSEGUIR", "ADEQUAR"):
        raise ValueError("Escolha inválida.")
    db = get_db()
    row = db.table("pedidos_ciencias").insert({
        "pedido_id": pedido_id,
        "versao": termo.get("versao"),
        "texto": termo.get("texto"),
        "pontos": termo.get("pontos"),
        "escolha": escolha,
        "ip": ip,
    }).execute().data[0]
    registrar_evento(None, "CONTRATO_CIENCIA",
                     {"pedido": pedido_id, "escolha": escolha,
                      "versao": termo.get("versao")})
    return row


# ── Redator ─────────────────────────────────────────────────────
SYSTEM_REDATOR = """Você é advogado redator de contratos da FC Advocacia,
com trinta anos de prática em direito civil e empresarial brasileiro.

Escreva o contrato completo, pronto para assinatura, seguindo a
legislação informada. Regras da casa:

- Português claro. Cláusula que o cliente não entende é cláusula que
  não protege ninguém.
- Numere as cláusulas. Qualificação completa das partes no preâmbulo.
- Use APENAS os dados fornecidos. Onde faltar dado essencial, escreva
  [A PREENCHER: o que falta] — nunca invente nome, valor, data ou
  documento.
- Inclua as cláusulas que a lei do tipo exige e as que a prática
  recomenda: objeto, preço, prazo, obrigações de cada parte, rescisão,
  multa, foro.
- Quando o cliente optou por manter um ponto contra a orientação,
  redija do jeito que ele pediu E inclua, ao final, uma cláusula de
  ciência registrando que a orientação foi prestada.
- Não escreva parecer, comentário nem explicação: só o contrato."""

SYSTEM_REVISOR = """Você é advogado revisor da FC Advocacia. Leia o
contrato inteiro e aponte o que precisa mudar antes de ir ao cliente.

Procure, nesta ordem de importância:
1. Cláusula nula ou ineficaz diante da lei aplicável.
2. Dado faltando, contraditório ou inventado — confira contra os dados
   fornecidos, um a um.
3. Cláusula ambígua, que permita duas leituras.
4. Ausência de cláusula essencial para este tipo de contrato.
5. Erro de português, numeração ou referência cruzada.

Seja específico: diga a cláusula, o problema e a redação sugerida. Não
elogie. Se estiver bom, diga que está bom."""

FERRAMENTA_REVISAO = {
    "name": "revisao",
    "description": "Apontamentos da revisão do contrato",
    "input_schema": {
        "type": "object",
        "properties": {
            "apontamentos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "clausula": {"type": "string"},
                        "gravidade": {"type": "string",
                                      "enum": ["ALTA", "MEDIA", "BAIXA"]},
                        "problema": {"type": "string"},
                        "sugestao": {"type": "string"},
                    },
                    "required": ["clausula", "gravidade", "problema", "sugestao"],
                },
            },
            "parecer": {"type": "string"},
            "pronto_para_advogado": {"type": "boolean"},
        },
        "required": ["apontamentos", "parecer", "pronto_para_advogado"],
    },
}


def _claude():
    return anthropic.Anthropic(api_key=get_settings().claude_api_key)


def redigir(pedido_id: str, auto: bool = False) -> dict:
    """Escreve a primeira versão a partir dos dados coletados.

    `auto` muda uma coisa só: a fase não avança. A minuta fica pronta e
    guardada, e o pedido continua em REDACAO pelo tempo da janela.

    Parece contraintuitivo escrever e não mostrar, mas é o que o rito
    pede: o cliente acabou de mandar as informações e o documento
    aparecer pronto no mesmo minuto não passa confiança, passa a
    impressão de formulário preenchido por máquina. E o escritório
    ganha a janela para agir antes, se quiser, com o trabalho já
    adiantado em vez de por fazer."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    t = catalogo.detalhe(p["tipo"]) or {}
    s = get_settings()

    ciencias = db.table("pedidos_ciencias").select("texto,escolha,pontos") \
        .eq("pedido_id", pedido_id).execute().data
    optou_manter = [c for c in ciencias if c.get("escolha") == "PROSSEGUIR"]

    contexto = [
        f"TIPO DE CONTRATO: {t.get('nome')}",
        f"LEGISLAÇÃO APLICÁVEL: {t.get('base_legal')}",
        "",
        "DADOS FORNECIDOS PELO CLIENTE:",
        json.dumps(p.get("dados") or {}, ensure_ascii=False, indent=2),
    ]
    if p.get("observacoes"):
        contexto += ["", "O QUE AS PARTES COMBINARAM, NAS PALAVRAS DO CLIENTE:",
                     p["observacoes"]]
    if optou_manter:
        contexto += ["", "PONTOS QUE O CLIENTE OPTOU POR MANTER APÓS ORIENTAÇÃO "
                     "(redija como pedido e inclua cláusula de ciência):"]
        for c in optou_manter:
            for ponto in (c.get("pontos") or []):
                contexto.append(f"- {ponto.get('o_que_a_lei_diz')}")
    if p.get("com_timbre") is False:
        contexto += ["", "O cliente pediu o documento SEM o timbre do escritório."]

    r = _claude().messages.create(
        model=s.claude_model, max_tokens=8000, system=SYSTEM_REDATOR,
        messages=[{"role": "user", "content": "\n".join(contexto)}],
    )
    texto = "".join(b.text for b in r.content if b.type == "text").strip()

    campos = {"minuta": texto, "redigido_em": _agora(),
              "atualizado_em": _agora()}
    if not auto:
        campos.update({"fase": "REVISAO_IA", "fase_em": _agora(),
                       "avanca_em": _mais(JANELA_REVISAO)})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_REDIGIDO",
                     {"pedido": pedido_id, "tipo": p["tipo"],
                      "caracteres": len(texto), "auto": auto})
    return {"ok": True, "fase": "REDACAO" if auto else "REVISAO_IA",
            "caracteres": len(texto)}


def revisar(pedido_id: str, auto: bool = False) -> dict:
    """O revisor lê a íntegra e anota. Só depois disso o ajuste abre."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    if not p.get("minuta"):
        raise ValueError("Não há minuta para revisar, redija primeiro.")
    t = catalogo.detalhe(p["tipo"]) or {}
    s = get_settings()

    r = _claude().messages.create(
        model=s.claude_model, max_tokens=4000, system=SYSTEM_REVISOR,
        tools=[FERRAMENTA_REVISAO],
        tool_choice={"type": "tool", "name": "revisao"},
        messages=[{"role": "user", "content":
                   f"TIPO: {t.get('nome')}\n"
                   f"LEGISLAÇÃO: {t.get('base_legal')}\n\n"
                   f"DADOS FORNECIDOS:\n"
                   f"{json.dumps(p.get('dados') or {}, ensure_ascii=False)}\n\n"
                   f"CONTRATO:\n{p['minuta'][:40000]}"}],
    )
    dados = {}
    for bloco in r.content:
        if bloco.type == "tool_use" and bloco.name == "revisao":
            dados = bloco.input or {}
    apontamentos = dados.get("apontamentos") or []

    campos = {"revisao": dados, "revisado_em": _agora(),
              "atualizado_em": _agora()}
    if not auto:
        campos.update({"fase": "AJUSTE", "fase_em": _agora(),
                       "avanca_em": _mais(JANELA_AJUSTE)})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_REVISADO",
                     {"pedido": pedido_id, "apontamentos": len(apontamentos),
                      "auto": auto})
    return {"ok": True, "fase": "REVISAO_IA" if auto else "AJUSTE",
            "apontamentos": apontamentos,
            "parecer": dados.get("parecer", "")}


def ajustar(pedido_id: str, auto: bool = False) -> dict:
    """O redator corrige o que o revisor apontou.

    A trava está aqui: sem revisão feita, não há o que ajustar, e
    deixar este botão aberto o tempo todo convidaria a pular a etapa."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    if not p.get("revisao"):
        raise ValueError("O ajuste só abre depois da revisão. "
                         "Acione o revisor primeiro.")
    apontamentos = (p["revisao"] or {}).get("apontamentos") or []
    if not apontamentos:
        db.table("pedidos_contrato").update({
            "fase": "REVISAO_ADV", "atualizado_em": _agora()}).eq("id", pedido_id).execute()
        return {"ok": True, "fase": "REVISAO_ADV",
                "aviso": "A revisão não apontou correções; segue para a conferência final."}

    s = get_settings()
    lista = "\n".join(
        f"- [{a.get('gravidade')}] {a.get('clausula')}: {a.get('problema')}\n"
        f"  Sugestão: {a.get('sugestao')}" for a in apontamentos)
    r = _claude().messages.create(
        model=s.claude_model, max_tokens=8000, system=SYSTEM_REDATOR,
        messages=[{"role": "user", "content":
                   f"Reescreva o contrato abaixo aplicando TODOS os apontamentos "
                   f"da revisão. Mantenha o que está correto; mude só o que foi "
                   f"apontado. Devolva o contrato completo.\n\n"
                   f"APONTAMENTOS:\n{lista}\n\nCONTRATO ATUAL:\n{p['minuta'][:40000]}"}],
    )
    texto = "".join(b.text for b in r.content if b.type == "text").strip()

    campos = {"minuta": texto, "minuta_anterior": p["minuta"],
              "ajustado_em": _agora(), "atualizado_em": _agora()}
    if not auto:
        # A conferência final não tem relógio: é onde a esteira para.
        campos.update({"fase": "REVISAO_ADV", "fase_em": _agora(),
                       "avanca_em": None})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_AJUSTADO",
                     {"pedido": pedido_id, "apontamentos": len(apontamentos),
                      "auto": auto})
    return {"ok": True, "fase": "AJUSTE" if auto else "REVISAO_ADV",
            "aplicados": len(apontamentos)}


def liberar_para_cliente(pedido_id: str, quem: str = "",
                         forcar: bool = False) -> dict:
    """Revisão humana aprovada. É o único caminho até o cliente.

    Exige que o advogado tenha aberto o PDF antes. Não é burocracia: o
    texto pode estar impecável e a página sair com a cláusula quebrada
    no meio ou o timbre em cima do primeiro parágrafo, e quem recebe
    isso é o cliente. `forcar` existe para o dia em que o LibreOffice
    estiver fora do ar e o documento precisar sair mesmo assim."""
    db = get_db()
    r = db.table("pedidos_contrato").select("visto_advogado_em,numero") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    if not r[0].get("visto_advogado_em") and not forcar:
        raise ValueError("Abra o PDF e confira o layout antes de liberar.")

    # O RELÓGIO DOS 7 DIAS COMEÇA AQUI
    #
    # Antes ele começava na entrega, que é depois da assinatura. Mas o
    # que o termo promete ao cliente é prazo para revisar e aprovar, e
    # isso acontece agora, quando o documento fica disponível. Contar da
    # entrega dava ao cliente um prazo que ele já tinha gastado.
    from datetime import date, timedelta
    ate = (date.today() + timedelta(days=DIAS_PARA_ALTERAR)).isoformat()

    db.table("pedidos_contrato").update({
        "fase": "APROVACAO", "aprovado_advogado_em": _agora(),
        "aprovado_advogado_por": quem or None,
        "disponibilizado_em": _agora(), "prazo_alteracao_ate": ate,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    try:
        recado(pedido_id,
               f"O seu documento está pronto e já passou pela revisão do "
               f"advogado. Acesse a sua página para ler e aprovar, ou pedir "
               f"ajuste se algo não refletir o que foi combinado. Você tem "
               f"até {ate[8:10]}/{ate[5:7]}/{ate[:4]}, sete dias a contar de "
               f"hoje; depois disso a solicitação é arquivada e a reabertura "
               f"passa a depender de um chamado.",
               canais=["EMAIL", "WHATSAPP"], autor="ESCRITORIO",
               assunto=f"Seu documento está pronto para revisão, "
                       f"{r[0].get('numero')}")
    except Exception as e:
        print(f"[balcao] cliente não avisado da liberação: {e}")

    registrar_evento(None, "CONTRATO_LIBERADO", {"pedido": pedido_id, "por": quem})
    return {"ok": True, "fase": "APROVACAO"}


def pedir_alteracao(pedido_id: str, texto: str) -> dict:
    """O cliente leu e quer mudança. Volta para ajuste, com o pedido
    dele junto, e a fila do escritório mostra que voltou."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("pedidos_alteracao") \
        .eq("id", pedido_id).limit(1).execute().data
    anteriores = (achado[0].get("pedidos_alteracao") if achado else None) or []
    anteriores.append({"em": _agora(), "texto": texto})
    db.table("pedidos_contrato").update({
        "pedidos_alteracao": anteriores, "fase": "REDACAO",
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_ALTERACAO_PEDIDA",
                     {"pedido": pedido_id, "texto": texto[:300]})
    return {"ok": True, "fase": "REDACAO"}


# ── O fim do rito: entrega, janela de alteração e arquivo ───────
#
# As fases ENTREGUE e ARQUIVADO existiam na lista desde o começo e
# nenhuma função levava o pedido até elas — o pedido chegava a
# ASSINATURA e parava ali para sempre. É isto que faltava.

DIAS_PARA_ALTERAR = 7


def registrar_pagamento(pedido_id: str, txid: str = "",
                        quem: str = "") -> dict:
    """Confirma o PIX e devolve a conversa ao cliente.

    A confirmação é humana de propósito: não há integração com o banco,
    e inventar uma baixa automática seria pior do que não ter nenhuma —
    o escritório escreveria o contrato de alguém que não pagou e
    descobriria depois. Quando o banco digital entrar, é esta função que
    passa a ser chamada pelo webhook, e o resto do rito não muda.

    O pedido vai para COLETA, e não direto para REDACAO: é agora que o
    atendimento pergunta o que o documento exige. O recado sai pelos
    canais que o cliente tiver, porque quem acabou de pagar fecha a
    página e vai fazer outra coisa."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("fase,numero,tipo,servico_livre,cliente_id") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]

    db.table("pedidos_contrato").update({
        "pago_em": _agora(), "pix_txid": (txid or "")[:120] or None,
        "fase": "COLETA", "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    nome_doc = (catalogo.detalhe(p.get("tipo") or "") or {}).get("nome") \
        or p.get("servico_livre") or "documento"
    abertura = (
        f"Pagamento confirmado. Obrigado pela confiança.\n\n"
        f"Agora preciso das informações para escrever o seu {nome_doc}. "
        f"Você pode digitar aqui ou enviar cópia dos documentos por foto "
        f"ou PDF, o que for mais fácil, e dá para misturar os dois.\n\n"
        f"Uma escolha antes de começar: o documento pode sair no papel "
        f"timbrado do escritório, que mostra quem redigiu e costuma pesar "
        f"quando a outra parte lê, ou em folha branca, sem identificação. "
        f"Os dois têm o mesmo valor jurídico. Qual você prefere?")
    try:
        db.table("pedidos_mensagens").insert({
            "pedido_id": pedido_id, "autor": "AGENTE", "texto": abertura,
            "canais": ["PLATAFORMA"],
        }).execute()
    except Exception as e:
        print(f"[balcao] abertura da coleta não registrada: {e}")

    try:
        recado(pedido_id,
               f"Recebemos o seu pagamento do pedido {p.get('numero')}. "
               f"Acesse a sua página para informar os dados do documento.",
               canais=["EMAIL", "WHATSAPP"], autor="AGENTE",
               assunto=f"Pagamento confirmado, pedido {p.get('numero')}")
    except Exception as e:
        print(f"[balcao] cliente não avisado do pagamento: {e}")

    registrar_evento(None, "BALCAO_PAGO",
                     {"pedido_id": pedido_id, "quem": quem, "txid": txid})
    return {"ok": True, "fase": "COLETA"}


def concluir_coleta(pedido_id: str, com_timbre: bool | None = None) -> dict:
    """O cliente terminou de informar. Daqui o redator assume.

    `com_timbre` chega agora, e não na primeira tela: é aqui que a
    pergunta faz sentido. Quem não responde fica com o timbre, que é o
    padrão, e `timbre_escolhido` guarda a diferença entre ter escolhido
    e ter aceitado o padrão."""
    db = get_db()
    r = db.table("pedidos_contrato").select("fase,dados,pago_em") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    if not r[0].get("pago_em"):
        raise ValueError("A coleta começa depois do pagamento confirmado.")

    # O QUE FALTA NÃO IMPEDE COMEÇAR
    #
    # Antes, faltando qualquer coisa a coleta era recusada e o cliente
    # ficava parado. Agora o trabalho começa: a maior parte do contrato
    # não depende daquele dado, e escrever o que já dá para escrever
    # adianta o prazo de todo mundo.
    #
    # O que falta vira pendência, e é a pendência que decide o rito:
    # a que é indispensável segura a entrega e para o relógio; a que é
    # complementar só avisa, e pode chegar até o fim da confecção.
    pend = pendencias_do_pedido(pedido_id)

    campos = {"fase": "REDACAO", "fase_em": _agora(),
              "pendencias": pend["itens"],
              "atualizado_em": _agora()}
    if com_timbre is not None:
        campos["com_timbre"] = bool(com_timbre)
        campos["timbre_escolhido"] = True

    # O RELÓGIO SÓ ANDA COM O PEDIDO COMPLETO
    #
    # Faltando informação indispensável, contar as quatro horas seria
    # medir uma espera que não é do escritório. `avanca_em` nulo é o
    # relógio parado; ele volta a andar quando a última pendência for
    # atendida.
    campos["avanca_em"] = None if pend["trava"] else _mais(JANELA_REDACAO)

    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_COLETA_CONCLUIDA",
                     {"pedido_id": pedido_id, "com_timbre": com_timbre,
                      "pendencias": len(pend["itens"]), "trava": pend["trava"]})

    if pend["itens"]:
        try:
            _guardar_recado_de_pendencia(pedido_id, pend)
        except Exception as e:
            print(f"[balcao] aviso de pendência não registrado: {e}")

    # A REDAÇÃO COMEÇA AGORA, NÃO NO PRÓXIMO CICLO
    #
    # Esperar o agendador significaria até quinze minutos de nada
    # acontecendo logo depois do gesto mais importante do cliente, que
    # é terminar de informar. A minuta fica pronta em cerca de um
    # minuto; a fase é que continua em elaboração pelas quatro horas.
    #
    # A falha aqui não derruba a conclusão da coleta: se a redação
    # falhar, o agendador tenta de novo no próximo ciclo, e o cliente
    # nem fica sabendo que houve um tropeço.
    try:
        redigir(pedido_id, auto=True)
    except Exception as e:
        print(f"[balcao] redação imediata falhou, fica para a esteira: {e}")

    return {"ok": True, "fase": "REDACAO"}


def entregar(pedido_id: str, link: str = "", quem: str = "") -> dict:
    """Entrega ao cliente e abre a janela de sete dias.

    A janela é contada a partir daqui, e não da aprovação: o prazo de
    reclamar começa quando a pessoa tem o documento na mão."""
    from datetime import date, timedelta
    db = get_db()
    r = db.table("pedidos_contrato").select("*,clientes(nome,email)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    pedido = r[0]
    ate = (date.today() + timedelta(days=DIAS_PARA_ALTERAR)).isoformat()

    db.table("pedidos_contrato").update({
        "fase": "ENTREGUE", "entregue_em": _agora(),
        "prazo_alteracao_ate": ate,
        "entrega_link": (link or "")[:600] or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    cliente = pedido.get("clientes") or {}
    if cliente.get("email"):
        try:
            from ..integracoes import avisos
            s = get_settings()
            url = link or f"{s.app_url.rstrip('/')}/balcao/{pedido_id}"
            texto = (
                f"Seu contrato está pronto.\n\n"
                f"Pedido {pedido.get('numero')}.\n"
                f"Acesse: {url}\n\n"
                f"Você tem até {ate[8:10]}/{ate[5:7]}/{ate[:4]} para pedir "
                f"ajustes sem custo. Depois dessa data o pedido é arquivado.")
            avisos.enviar_email(
                cliente["email"], f"Seu contrato está pronto, {pedido.get('numero')}",
                texto, texto.replace("\n", "<br>"))
        except Exception as e:
            print(f"[balcao] entrega não avisada por e-mail: {e}")

    registrar_evento(None, "BALCAO_ENTREGUE",
                     {"pedido_id": pedido_id, "quem": quem, "ate": ate})
    return {"ok": True, "fase": "ENTREGUE", "prazo_alteracao_ate": ate}


def arquivar(pedido_id: str, quem: str = "") -> dict:
    db = get_db()
    db.table("pedidos_contrato").update({
        "fase": "ARQUIVADO", "arquivado_em": _agora(),
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_ARQUIVADO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True, "fase": "ARQUIVADO"}


def arquivar_vencidos() -> dict:
    """Tira da vista o que passou dos sete dias.

    Roda com a controladoria. Sem isto a coluna Entregue vira depósito:
    em três meses ninguém distingue o que foi entregue ontem do que foi
    entregue em março."""
    from datetime import date
    db = get_db()
    hoje = date.today().isoformat()
    # Duas fases, e não uma. ENTREGUE é quem já assinou e tem os sete
    # dias de ajuste. APROVACAO é quem recebeu o documento para revisar
    # e sumiu: é justamente esse que o termo promete arquivar, e era o
    # que ficava parado para sempre na coluna do operador.
    vencidos = db.table("pedidos_contrato").select("id,numero,fase") \
        .in_("fase", ["ENTREGUE", "APROVACAO"]) \
        .lt("prazo_alteracao_ate", hoje) \
        .is_("excluido_em", "null") \
        .limit(200).execute().data or []
    for p in vencidos:
        try:
            arquivar(p["id"], quem="sistema")
            if p.get("fase") == "APROVACAO":
                recado(p["id"],
                       "Passaram os sete dias para revisão e o seu documento "
                       "foi arquivado. Ele não se perdeu: abra um pedido de "
                       "desarquivamento na sua área, explicando o motivo, e o "
                       "escritório retoma.",
                       canais=["EMAIL"], autor="AGENTE",
                       assunto=f"Pedido {p.get('numero')} arquivado")
        except Exception as e:
            print(f"[balcao] não arquivou {p.get('numero')}: {e}")
    return {"arquivados": len(vencidos)}


# ══════════════════════════════════════════════════════════════════
# RECADO AO CLIENTE, PELOS CANAIS QUE ELE TIVER
#
# O escritório escrevia na conversa do pedido e pronto. Quem não abrisse
# a plataforma não ficava sabendo de nada, e a plataforma é justamente o
# lugar em que ninguém entra sem motivo.
#
# Três canais, com papéis diferentes:
#
#   PLATAFORMA  é a própria linha da tabela, e por isso nunca falha. É
#               também o único registro que fica, com data e hora.
#   EMAIL       o que chega a quem não está com o celular na mão.
#   WHATSAPP    o que a pessoa realmente lê. Ainda não está ligado: a
#               função tenta, falha com elegância e anota a falha, e no
#               dia em que o número for aprovado nada mais muda aqui.
#
# A falha de um canal não derruba os outros, e fica gravada. "Ninguém me
# avisou" se responde com a linha desta tabela, não com memória.
# ══════════════════════════════════════════════════════════════════

CANAIS = ("PLATAFORMA", "EMAIL", "WHATSAPP")


def recado(pedido_id: str, texto: str, canais: list[str] | None = None,
           autor: str = "ESCRITORIO", assunto: str = "") -> dict:
    """Manda um recado ao cliente do balcão e registra por onde saiu."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("A mensagem está vazia.")

    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("numero,cliente_id,clientes(nome,email,whatsapp)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    cli = p.get("clientes") or {}

    pedidos = [c.upper() for c in (canais or ["PLATAFORMA", "EMAIL"])
               if c.upper() in CANAIS]
    if "PLATAFORMA" not in pedidos:
        pedidos.insert(0, "PLATAFORMA")

    s = get_settings()
    url = f"{s.app_url.rstrip('/')}/balcao/{pedido_id}"
    falhas: list[str] = []
    email_em = whats_em = None

    if "EMAIL" in pedidos and cli.get("email"):
        try:
            from ..integracoes import avisos
            corpo = (f"{texto}\n\n"
                     f"Pedido {p.get('numero')}.\n"
                     f"Acesse a sua página: {url}")
            avisos.enviar_email(
                cli["email"],
                assunto or f"Sobre o seu pedido {p.get('numero')}",
                corpo, corpo.replace("\n", "<br>"))
            email_em = _agora()
        except Exception as e:
            falhas.append(f"email: {e}")

    if "WHATSAPP" in pedidos and cli.get("whatsapp"):
        try:
            from ..integracoes import avisos
            phone_id, _ = avisos.escolher_origem(cli.get("whatsapp"))
            avisos.enviar_whatsapp(
                cli["whatsapp"], f"{texto}\n\nPedido {p.get('numero')}\n{url}",
                phone_id)
            whats_em = _agora()
        except Exception as e:
            falhas.append(f"whatsapp: {e}")

    linha = db.table("pedidos_mensagens").insert({
        "pedido_id": pedido_id,
        "autor": autor if autor in ("ESCRITORIO", "AGENTE", "CLIENTE") else "ESCRITORIO",
        "texto": texto[:4000], "canais": pedidos,
        "email_em": email_em, "whatsapp_em": whats_em,
        "falha": "; ".join(falhas)[:500] or None,
    }).execute().data

    registrar_evento(None, "BALCAO_RECADO",
                     {"pedido_id": pedido_id, "canais": pedidos,
                      "falhas": falhas})
    return {"ok": True, "canais": pedidos, "falhas": falhas,
            "mensagem": linha[0] if linha else None}


def excluir(pedido_id: str, quem: str = "", motivo: str = "") -> dict:
    """Tira o pedido da esteira sem apagar a prova de que ele existiu.

    Exclusão física levaria junto a conversa, o comprovante do PIX e a
    ciência registrada, que são exatamente as três coisas de que o
    escritório precisaria se o cliente reclamasse depois. O pedido sai
    da vista e permanece no banco."""
    db = get_db()
    r = db.table("pedidos_contrato").select("numero,fase,pago_em") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    if p.get("pago_em") and not motivo.strip():
        raise ValueError("Este pedido foi pago. Explique o motivo da exclusão.")

    db.table("pedidos_contrato").update({
        "excluido_em": _agora(), "excluido_por": quem or "escritório",
        "excluido_motivo": (motivo or "")[:500] or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_EXCLUIDO",
                     {"pedido_id": pedido_id, "numero": p.get("numero"),
                      "fase": p.get("fase"), "quem": quem, "motivo": motivo})
    return {"ok": True, "numero": p.get("numero")}


def restaurar(pedido_id: str, quem: str = "") -> dict:
    """Desfaz a exclusão. Existe porque todo botão de excluir erra um dia."""
    get_db().table("pedidos_contrato").update({
        "excluido_em": None, "excluido_por": None, "excluido_motivo": None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_RESTAURADO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════
# O PDF QUE O ADVOGADO VÊ ANTES DO CLIENTE
#
# Texto aprovado e página torta chegam tortos ao cliente. Aprovar o
# conteúdo e conferir o layout são duas coisas, e o sistema tratava como
# uma só: a minuta ia como texto puro e ninguém via a página montada.
#
# Agora a aprovação do advogado gera o PDF, ele abre, confere, e só
# então o botão de liberar fica disponível. É o mesmo cuidado de sempre,
# com um passo a mais e uma marca de tempo para cada um.
# ══════════════════════════════════════════════════════════════════

CABECALHO = [
    "FÁBIO SILVA CUNHA SOCIEDADE INDIVIDUAL DE ADVOCACIA",
    "Dr. Fábio Cunha, OAB/RO 10.849",
    "Porto Velho, RO e Florianópolis, SC",
]


def _docx_da_minuta(texto: str, com_timbre: bool, numero: str = "") -> bytes:
    """Monta o .docx da minuta, com ou sem a identificação do escritório.

    Sem modelo pronto de propósito: contrato de balcão não tem a
    estrutura fixa das peças do escritório, e forçar um modelo aqui daria
    margem esquisita em metade dos tipos."""
    import io
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(2.5 if com_timbre else 3)
        sec.bottom_margin = Cm(2.5)
        sec.left_margin = Cm(3)
        sec.right_margin = Cm(2)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(12)

    if com_timbre:
        for i, linha in enumerate(CABECALHO):
            par = doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = par.add_run(linha)
            run.bold = i == 0
            run.font.size = Pt(11 if i == 0 else 9)
        doc.add_paragraph()

    for bloco in (texto or "").split("\n"):
        bloco = bloco.rstrip()
        if not bloco:
            doc.add_paragraph()
            continue
        par = doc.add_paragraph()
        limpo = bloco.strip()
        titulo = limpo.isupper() and len(limpo) < 90
        par.alignment = (WD_ALIGN_PARAGRAPH.CENTER if titulo
                         else WD_ALIGN_PARAGRAPH.JUSTIFY)
        par.paragraph_format.first_line_indent = None if titulo else Cm(1.25)
        par.paragraph_format.space_after = Pt(6)
        run = par.add_run(limpo)
        run.bold = titulo

    if com_timbre and numero:
        rodape = doc.add_paragraph()
        rodape.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = rodape.add_run(f"Documento elaborado pelo escritório. Pedido {numero}.")
        r.font.size = Pt(8)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def gerar_pdf(pedido_id: str) -> tuple[bytes, str]:
    """Devolve (bytes do PDF, nome do arquivo) da minuta atual."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("minuta,com_timbre,numero,tipo,servico_livre") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    if not (p.get("minuta") or "").strip():
        raise ValueError("Este pedido ainda não tem minuta.")

    from . import documentos
    docx = _docx_da_minuta(p["minuta"], p.get("com_timbre") is not False,
                           p.get("numero") or "")
    pdf = documentos.converter_para_pdf(docx)

    db.table("pedidos_contrato").update({
        "pdf_gerado_em": _agora(), "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    nome = (catalogo.detalhe(p.get("tipo") or "") or {}).get("nome") \
        or p.get("servico_livre") or "documento"
    arquivo = f"{(p.get('numero') or 'pedido')}_{nome}.pdf".replace(" ", "_")
    registrar_evento(None, "BALCAO_PDF_GERADO",
                     {"pedido_id": pedido_id, "bytes": len(pdf)})
    return pdf, arquivo


def marcar_visto(pedido_id: str, quem: str = "") -> dict:
    """O advogado abriu o PDF e o layout está de pé."""
    get_db().table("pedidos_contrato").update({
        "visto_advogado_em": _agora(), "visto_advogado_por": quem or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_LAYOUT_CONFERIDO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════
# DESARQUIVAMENTO
#
# O termo promete ao cliente que o documento não se perde: passados os
# sete dias, a solicitação arquiva e ele pode abrir um chamado para
# retomá-la. Sem isto, a promessa não teria como ser cumprida, e o
# cliente arquivado só teria o telefone do escritório.
#
# Não é botão que reabre sozinho. Reabertura automática torna o prazo
# decorativo, e há casos em que retomar custa trabalho de verdade,
# porque o contrato envelheceu ou a outra parte desistiu. Quem decide é
# quem vai fazer, lendo o motivo escrito pelo cliente.
# ══════════════════════════════════════════════════════════════════

def pedir_desarquivamento(pedido_id: str, motivo: str,
                          cliente_id: str | None = None) -> dict:
    """O cliente explica por que quer o pedido de volta."""
    motivo = (motivo or "").strip()
    if len(motivo) < 15:
        raise ValueError(
            "Conte com um pouco mais de detalhe o que você precisa. "
            "É o que o escritório lê para decidir.")

    db = get_db()
    r = db.table("pedidos_contrato").select("id,numero,fase,cliente_id") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    if p.get("fase") != "ARQUIVADO":
        raise ValueError("Este pedido não está arquivado.")

    aberto = db.table("pedidos_desarquivamento").select("id,criado_em") \
        .eq("pedido_id", pedido_id).eq("status", "PENDENTE") \
        .limit(1).execute().data
    if aberto:
        raise ValueError(
            "Você já tem um pedido de desarquivamento em análise para este "
            "documento. O escritório responde por e-mail.")

    linha = db.table("pedidos_desarquivamento").insert({
        "pedido_id": pedido_id,
        "cliente_id": cliente_id or p.get("cliente_id"),
        "motivo": motivo[:2000],
    }).execute().data[0]

    try:
        s = get_settings()
        from ..integracoes import avisos
        avisos.enviar_email(
            s.email_escritorio,
            f"Pedido de desarquivamento, {p.get('numero')}",
            f"Um cliente pediu para reabrir o pedido {p.get('numero')}.\n\n"
            f"Motivo:\n{motivo}\n\n"
            f"Responda pela tela de Contratos.",
            "")
    except Exception as e:
        print(f"[balcao] escritório não avisado do desarquivamento: {e}")

    registrar_evento(None, "BALCAO_DESARQUIVAMENTO_PEDIDO",
                     {"pedido_id": pedido_id, "chamado": linha["id"]})
    return {"ok": True, "chamado": linha["id"]}


def responder_desarquivamento(chamado_id: str, aprovado: bool,
                              resposta: str = "", quem: str = "") -> dict:
    """O escritório decide. Aprovado, o pedido volta com prazo novo."""
    db = get_db()
    r = db.table("pedidos_desarquivamento").select("*").eq("id", chamado_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Chamado não encontrado.")
    c = r[0]
    if c["status"] != "PENDENTE":
        raise ValueError("Este chamado já foi respondido.")
    if not aprovado and not (resposta or "").strip():
        raise ValueError("Explique ao cliente por que não é possível reabrir.")

    db.table("pedidos_desarquivamento").update({
        "status": "APROVADO" if aprovado else "RECUSADO",
        "resposta": (resposta or "")[:2000] or None,
        "respondido_em": _agora(), "respondido_por": quem or "escritório",
    }).eq("id", chamado_id).execute()

    if aprovado and c.get("pedido_id"):
        # Volta para a revisão do cliente, com sete dias novos. Devolver
        # sem prazo faria o pedido ficar aberto para sempre, que é o que
        # o arquivamento existia para evitar.
        from datetime import date, timedelta
        ate = (date.today() + timedelta(days=DIAS_PARA_ALTERAR)).isoformat()
        db.table("pedidos_contrato").update({
            "fase": "APROVACAO", "arquivado_em": None,
            "prazo_alteracao_ate": ate, "atualizado_em": _agora(),
        }).eq("id", c["pedido_id"]).execute()

    if c.get("pedido_id"):
        try:
            texto = (
                f"Seu pedido de desarquivamento foi aprovado. O documento "
                f"voltou a ficar disponível na sua área para revisão e "
                f"aprovação, com prazo novo de {DIAS_PARA_ALTERAR} dias."
                if aprovado else
                f"Sobre o seu pedido de desarquivamento: {resposta}")
            recado(c["pedido_id"], texto, canais=["EMAIL"],
                   autor="ESCRITORIO",
                   assunto="Resposta ao seu pedido de desarquivamento")
        except Exception as e:
            print(f"[balcao] cliente não avisado da decisão: {e}")

    registrar_evento(None, "BALCAO_DESARQUIVAMENTO_RESPONDIDO",
                     {"chamado": chamado_id, "aprovado": aprovado,
                      "quem": quem})
    return {"ok": True, "aprovado": aprovado}


def desarquivamentos(status: str = "PENDENTE") -> list[dict]:
    return get_db().table("pedidos_desarquivamento") \
        .select("*,pedidos_contrato(numero,tipo,servico_livre,clientes(nome,email))") \
        .eq("status", status).order("criado_em", desc=True) \
        .limit(100).execute().data or []


# ══════════════════════════════════════════════════════════════════
# AS PARTES DO CONTRATO
#
# Todo contrato tem pelo menos duas partes, e o cliente é uma delas. Os
# dados da outra ficavam soltos dentro de `dados`, um JSON sem forma em
# que cada tipo usava nomes diferentes de campo. Conferir o que faltava
# era impossível, e a falta só aparecia na redação, com o redator
# inventando ou o escritório ligando para perguntar.
#
# Aqui a lista ganha forma, e com forma vem a conferência: antes de
# mandar para a redação, o atendimento diz exatamente o que falta e de
# quem. É a diferença entre "faltam informações" e "falta o CPF do
# fiador e o endereço do locatário".
# ══════════════════════════════════════════════════════════════════

# O mínimo para qualificar alguém num contrato. Não é a lista completa
# do Código Civil: é o que, faltando, dá trabalho para executar depois.
OBRIGATORIOS_PARTE = [
    ("nome", "nome completo"),
    ("cpf_cnpj", "CPF ou CNPJ"),
    ("endereco", "endereço completo"),
]
DESEJAVEIS_PARTE = [
    ("estado_civil", "estado civil"),
    ("email", "e-mail"),
]


def _papeis_do_tipo(tipo: str) -> list[str]:
    """Quem são as partes daquele tipo de contrato.

    Sai do próprio catálogo, lendo os campos de qualificação que ele já
    declara. Assim, tipo novo no catálogo já nasce com as partes certas
    aqui, sem ninguém precisar lembrar de atualizar uma segunda lista,
    que é o tipo de duplicação que envelhece mal."""
    t = catalogo.detalhe(tipo) or {}
    papeis: list[str] = []
    for c in t.get("campos") or []:
        campo = c.get("campo") or ""
        if campo.endswith("_nome"):
            papel = campo[:-5]
            if papel not in papeis:
                papeis.append(papel)
    return papeis or ["contratante", "contratada"]


def partes_do_pedido(pedido_id: str) -> dict:
    """O que já está preenchido, e o que falta, parte por parte."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("id,tipo,partes,dados,cliente_id,clientes(*)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]

    papeis = _papeis_do_tipo(p["tipo"])
    guardadas = {x.get("papel"): x for x in (p.get("partes") or [])}

    # A primeira parte nasce preenchida com o cadastro do cliente. Ele
    # já informou tudo isso uma vez, e pedir de novo é a forma mais
    # rápida de fazer alguém desistir no meio.
    cli = p.get("clientes") or {}
    if papeis and papeis[0] not in guardadas and cli.get("nome"):
        guardadas[papeis[0]] = {
            "papel": papeis[0], "do_cliente": True,
            "nome": cli.get("nome"), "cpf_cnpj": cli.get("cpf_cnpj"),
            "estado_civil": cli.get("estado_civil"),
            "profissao": cli.get("profissao"),
            "nacionalidade": cli.get("nacionalidade"),
            "email": cli.get("email"), "telefone": cli.get("whatsapp"),
            "endereco": _endereco_do_cliente(cli),
        }

    partes, faltas = [], []
    for papel in papeis:
        parte = dict(guardadas.get(papel) or {"papel": papel})
        parte["papel"] = papel
        falta = [rot for campo, rot in OBRIGATORIOS_PARTE
                 if not str(parte.get(campo) or "").strip()]
        parte["falta"] = falta
        partes.append(parte)
        if falta:
            faltas.append({"papel": papel, "falta": falta})

    return {"partes": partes, "faltas": faltas,
            "completo": not faltas,
            "obrigatorios": [{"campo": c, "rotulo": r} for c, r in OBRIGATORIOS_PARTE],
            "desejaveis": [{"campo": c, "rotulo": r} for c, r in DESEJAVEIS_PARTE]}


def _endereco_do_cliente(cli: dict) -> str:
    pedacos = [cli.get("endereco_rua"), cli.get("endereco_numero"),
               cli.get("endereco_complemento"), cli.get("endereco_bairro"),
               cli.get("endereco_cidade"), cli.get("endereco_uf"),
               cli.get("endereco_cep")]
    return ", ".join(str(x).strip() for x in pedacos if str(x or "").strip())


def salvar_partes(pedido_id: str, partes: list[dict]) -> dict:
    """Guarda o que o cliente informou e devolve o que ainda falta.

    Salva mesmo incompleto, de propósito: quem está no ônibus preenche
    metade e volta depois. O que não acontece é o pedido seguir para a
    redação incompleto, e disso cuida `partes_completas`."""
    db = get_db()
    limpas = []
    for x in partes or []:
        limpas.append({k: (str(v).strip() if isinstance(v, str) else v)
                       for k, v in x.items() if k != "falta"})

    db.table("pedidos_contrato").update({
        "partes": limpas, "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    estado = partes_do_pedido(pedido_id)
    db.table("pedidos_contrato").update({
        "partes_completas": estado["completo"],
    }).eq("id", pedido_id).execute()

    # Salvar parte é uma das formas de atender pendência, e é aqui que
    # o relógio pode voltar a andar.
    try:
        revisar_pendencias(pedido_id)
    except Exception as e:
        print(f"[balcao] pendências não recalculadas: {e}")

    registrar_evento(None, "BALCAO_PARTES_SALVAS",
                     {"pedido_id": pedido_id, "completo": estado["completo"],
                      "faltas": estado["faltas"]})
    return estado


def recado_do_que_falta(estado: dict) -> str:
    """A frase que o atendimento diz quando algo falta.

    Escrita aqui, e não deixada para o modelo, porque é uma lista: o
    modelo resume, esquece um item, e o cliente volta duas vezes."""
    if estado.get("completo"):
        return ""
    partes = []
    for f in estado["faltas"]:
        itens = ", ".join(f["falta"])
        partes.append(f"do {f['papel'].replace('_', ' ')}: {itens}")
    return ("Antes de mandar para a redação, falta "
            + "; ".join(partes)
            + ". Sem isso o contrato até sai, mas fica difícil de executar "
              "se um dia precisar ir para a Justiça.")


# ══════════════════════════════════════════════════════════════════
# A ESTEIRA QUE ANDA SOZINHA, ATÉ ONDE PODE
#
# O pedido parava em cada fase esperando alguém clicar. Num escritório
# de duas pessoas, isso significa que um contrato pago às nove da noite
# fica parado até a manhã seguinte, não porque falte trabalho, mas
# porque falta um clique.
#
# Agora as três primeiras fases andam sozinhas, com janelas:
#
#   REDACAO      a minuta é escrita assim que a coleta fecha, mas o
#                pedido fica visível como "em elaboração" por 4 horas
#   REVISAO_IA   +2 horas
#   AJUSTE       +2 horas
#   REVISAO_ADV  para. Daqui em diante só com o advogado.
#
# POR QUE ESCREVER ANTES E MOSTRAR DEPOIS
#
# Porque o trabalho estar pronto e o rito estar cumprido são coisas
# diferentes. Documento que aparece pronto no minuto seguinte ao
# pagamento não passa confiança, passa impressão de formulário
# automático. E o escritório ganha a janela para agir antes, se quiser,
# com o trabalho adiantado em vez de por fazer.
#
# POR QUE PARA NA REVISÃO DO ADVOGADO
#
# Porque é a única etapa que a máquina não pode cumprir. Tudo antes
# dela é rascunho; o que sai daqui leva a assinatura de alguém inscrito
# na OAB, que responde pelo que assina. Automatizar esse passo seria
# assinar sem ler.
#
# A ação humana sempre atropela o relógio: quem clicar antes, avança
# antes. As janelas são teto, não piso.
# ══════════════════════════════════════════════════════════════════

JANELA_REDACAO = 4        # horas em "em elaboração", à vista do cliente
JANELA_REVISAO = 2
JANELA_AJUSTE = 2

_PROXIMA = {
    "REDACAO": ("REVISAO_IA", JANELA_REDACAO),
    "REVISAO_IA": ("AJUSTE", JANELA_REVISAO),
    "AJUSTE": ("REVISAO_ADV", JANELA_AJUSTE),
}


def _horas_desde(iso: str | None) -> float:
    if not iso:
        return 999.0
    from datetime import datetime as _d, timezone as _t
    try:
        t = _d.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return 999.0
    if t.tzinfo is None:
        t = t.replace(tzinfo=_t.utc)
    return (_d.now(_t.utc) - t).total_seconds() / 3600.0


def esteira_automatica() -> dict:
    """Roda de tempos em tempos e empurra o que já pode andar.

    Duas responsabilidades, e é importante que sejam as duas: produzir
    o trabalho da fase quando ele ainda não existe, e avançar a fase
    quando a janela vence. Fazer só a segunda deixaria o pedido mudar
    de nome sem mudar de estado, que é pior do que não mudar nada."""
    db = get_db()
    pendentes = db.table("pedidos_contrato") \
        .select("id,numero,fase,fase_em,avanca_em,minuta,revisao,ajustado_em,"
                "redigido_em,revisado_em,pago_em,pendencias") \
        .in_("fase", list(_PROXIMA)) \
        .is_("excluido_em", "null") \
        .limit(100).execute().data or []

    feitos = {"redigidos": 0, "revisados": 0, "ajustados": 0, "avancados": 0}

    for p in pendentes:
        fase = p["fase"]
        proxima, janela = _PROXIMA[fase]
        try:
            # 1. O trabalho daquela fase ainda não foi feito? Faz agora.
            if fase == "REDACAO" and not (p.get("minuta") or "").strip():
                redigir(p["id"], auto=True)
                feitos["redigidos"] += 1
                continue                       # a janela conta da fase, não daqui
            if fase == "REVISAO_IA" and not p.get("revisao"):
                revisar(p["id"], auto=True)
                feitos["revisados"] += 1
                continue
            if fase == "AJUSTE" and _horas_desde(p.get("ajustado_em")) > \
                    _horas_desde(p.get("fase_em")):
                # ajustado antes de entrar nesta fase quer dizer que o
                # ajuste desta rodada ainda não aconteceu
                ajustar(p["id"], auto=True)
                feitos["ajustados"] += 1
                continue

            # 2. O relógio está parado esperando o cliente? Não anda.
            #
            # `avanca_em` nulo significa pendência indispensável em
            # aberto. O documento continua sendo escrito, mas a fase
            # não muda: prometer revisão de um texto que ainda vai
            # mudar é prometer duas vezes o mesmo trabalho.
            if p.get("avanca_em") is None:
                continue

            # 3. Chegou a hora? Avança.
            if _horas_desde(p["avanca_em"]) >= 0:
                seguinte = _PROXIMA.get(proxima)
                db.table("pedidos_contrato").update({
                    "fase": proxima, "fase_em": _agora(),
                    # A fase seguinte já nasce com o próprio relógio.
                    # REVISAO_ADV não tem: é onde para.
                    "avanca_em": _mais(seguinte[1]) if seguinte else None,
                    "atualizado_em": _agora(),
                }).eq("id", p["id"]).execute()
                registrar_evento(None, "BALCAO_FASE_AUTOMATICA",
                                 {"pedido_id": p["id"], "de": fase,
                                  "para": proxima, "numero": p.get("numero")})
                feitos["avancados"] += 1
        except Exception as e:
            # Um pedido com problema não pode parar a fila inteira.
            print(f"[balcao] esteira parou em {p.get('numero')}: {e}")

    return feitos


# ══════════════════════════════════════════════════════════════════
# PENDÊNCIAS: O QUE FALTA, E O QUE ISSO IMPEDE
#
# Antes havia uma resposta só para qualquer falta: recusar a coleta e
# deixar o cliente parado. Mas nem toda falta é igual.
#
#   INDISPENSÁVEL   sem isso o documento não se conclui. Nome e CPF de
#                   quem assina, endereço do imóvel, valor do aluguel.
#                   O trabalho começa, o documento é escrito até onde
#                   dá, e a entrega espera.
#
#   COMPLEMENTAR    melhora o documento e não o impede. Profissão,
#                   telefone, estado civil em contrato que não depende
#                   dele. Pode chegar a qualquer momento antes do fim.
#
# A diferença muda três coisas: o que se diz ao cliente, se o relógio
# anda, e se a peça pode ser entregue.
#
# O RELÓGIO PARADO
#
# Enquanto houver pendência indispensável, `avanca_em` fica nulo e a
# esteira não move o pedido. Não é castigo: contar quatro horas de uma
# espera que é do cliente seria medir o tempo errado e prometer prazo
# que não se cumpre.
#
# Atendida a última, o relógio volta. Se as quatro horas já tinham
# passado enquanto se esperava, o pedido não salta direto para a fase
# seguinte: ganha uma hora, que é o tempo de o redator incorporar o que
# chegou. Avançar no mesmo segundo entregaria um documento sem a
# informação que acabou de chegar.
# ══════════════════════════════════════════════════════════════════

HORA_DE_GRACA = 1        # depois de atendida a pendência atrasada


def _mais(horas: float) -> str:
    from datetime import datetime as _d, timedelta as _td, timezone as _t
    return (_d.now(_t.utc) + _td(hours=horas)).isoformat()


def pendencias_do_pedido(pedido_id: str) -> dict:
    """O que falta, separado entre o que trava e o que não trava."""
    db = get_db()
    r = db.table("pedidos_contrato").select("id,tipo,dados,partes") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    t = catalogo.detalhe(p["tipo"]) or {}
    dados = p.get("dados") or {}

    itens: list[dict] = []

    # 1. Os campos do tipo de contrato. O catálogo já diz o que é
    #    obrigatório, e essa marcação foi escrita caso a caso, com o
    #    motivo ao lado. É ela que manda aqui.
    for c in t.get("campos") or []:
        campo = c.get("campo") or ""
        if str(dados.get(campo) or "").strip():
            continue
        # A qualificação das partes é conferida no bloco seguinte, com
        # a estrutura própria. Aqui ficariam duplicadas.
        if any(campo.endswith(suf) for suf in
               ("_nome", "_cpf_cnpj", "_endereco", "_email", "_telefone",
                "_estado_civil", "_profissao", "_nacionalidade")):
            continue
        itens.append({
            "campo": campo, "rotulo": c.get("rotulo") or campo,
            "obrigatorio": bool(c.get("obrigatorio")),
            "porque": c.get("porque"), "origem": "CONTRATO",
        })

    # 2. A qualificação de quem assina.
    estado = partes_do_pedido(pedido_id)
    for f in estado["faltas"]:
        for rotulo in f["falta"]:
            itens.append({
                "campo": f"{f['papel']}_{rotulo}", "rotulo": rotulo,
                "obrigatorio": True, "papel": f["papel"], "origem": "PARTE",
            })

    trava = any(i["obrigatorio"] for i in itens)
    return {"itens": itens, "trava": trava,
            "obrigatorias": [i for i in itens if i["obrigatorio"]],
            "complementares": [i for i in itens if not i["obrigatorio"]]}


def recado_de_pendencia(pend: dict) -> str:
    """O que o atendimento diz ao cliente sobre o que falta.

    Escrito aqui, e não deixado para o modelo, porque é lista com
    consequência: o modelo resume, perde um item, e o cliente volta
    duas vezes. E a frase precisa separar o que segura a entrega do que
    não segura, senão a pessoa trata tudo como urgente ou nada como
    urgente."""
    if not pend["itens"]:
        return ""

    partes = []
    if pend["obrigatorias"]:
        lista = ", ".join(_rotulo(i) for i in pend["obrigatorias"])
        partes.append(
            f"Para concluir o seu documento, o escritório precisa de: {lista}. "
            f"O trabalho já começou e a redação está em andamento, mas a "
            f"entrega só acontece com essa informação em mãos. Assim que você "
            f"enviar, o prazo volta a correr.")
    if pend["complementares"]:
        lista = ", ".join(_rotulo(i) for i in pend["complementares"])
        partes.append(
            f"Há ainda o que ajuda a deixar o documento mais completo: "
            f"{lista}. Isso não segura nada: pode mandar depois, a qualquer "
            f"momento antes de o documento ficar pronto.")
    return "\n\n".join(partes)


def _rotulo(item: dict) -> str:
    if item.get("papel"):
        return f"{item['rotulo']} do {str(item['papel']).replace('_', ' ')}"
    return item["rotulo"]


def _guardar_recado_de_pendencia(pedido_id: str, pend: dict) -> None:
    texto = recado_de_pendencia(pend)
    if not texto:
        return
    get_db().table("pedidos_mensagens").insert({
        "pedido_id": pedido_id, "autor": "AGENTE", "texto": texto,
        "canais": ["PLATAFORMA"],
    }).execute()
    try:
        recado(pedido_id, texto, canais=["EMAIL"], autor="AGENTE",
               assunto="Falta uma informação para concluir o seu documento")
    except Exception as e:
        print(f"[balcao] pendência não enviada por e-mail: {e}")


def revisar_pendencias(pedido_id: str) -> dict:
    """Roda toda vez que o cliente salva algo. Solta o relógio se der.

    É aqui que o relógio volta a andar, e a hora de graça nasce: se as
    quatro horas já passaram enquanto o pedido esperava, avançar no
    mesmo segundo entregaria um documento sem a informação que acabou
    de chegar. A hora é o tempo de incorporá-la."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("id,fase,fase_em,avanca_em,pendencias").eq("id", pedido_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    antes_travava = p.get("avanca_em") is None and p.get("fase") in _PROXIMA

    pend = pendencias_do_pedido(pedido_id)
    campos = {"pendencias": pend["itens"], "atualizado_em": _agora()}

    if p.get("fase") in _PROXIMA:
        if pend["trava"]:
            campos["avanca_em"] = None
        elif antes_travava:
            _, janela = _PROXIMA[p["fase"]]
            ja_passou = _horas_desde(p.get("fase_em")) >= janela
            campos["avanca_em"] = _mais(HORA_DE_GRACA if ja_passou else
                                        janela - _horas_desde(p.get("fase_em")))

    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()

    if antes_travava and not pend["trava"]:
        registrar_evento(None, "BALCAO_PENDENCIA_ATENDIDA",
                         {"pedido_id": pedido_id})
        try:
            recado(pedido_id,
                   "Recebemos a informação que faltava. O documento está sendo "
                   "complementado e segue para a revisão em cerca de uma hora.",
                   canais=["PLATAFORMA"], autor="AGENTE")
        except Exception as e:
            print(f"[balcao] confirmação não registrada: {e}")

    return {**pend, "recado": recado_de_pendencia(pend),
            "travado": bool(pend["trava"])}


# ══════════════════════════════════════════════════════════════════
# A RÉGUA DE COBRANÇA, E OS TRÊS CANAIS QUE VOLTAM PARA O MESMO LUGAR
#
# Pendência que ninguém cobra é pedido que morre. O cliente mandou o
# que lembrou, ficou faltando um dado, e a vida seguiu: uma semana
# depois ele não lembra mais que havia algo pendente, e o escritório
# tem um pedido pago parado na esteira.
#
# De seis em seis horas, enquanto faltar algo indispensável, sai um
# comunicado com a lista do que falta e a explicação de por que aquilo
# importa. Seis horas é curto o bastante para não deixar o pedido
# esfriar e longo o bastante para não soar cobrança de agiota.
#
# OS TRÊS CANAIS SÃO UMA PORTA SÓ
#
# O comunicado sai pela plataforma, pelo e-mail e pelo WhatsApp, e a
# resposta volta por onde o cliente preferir. Seja qual for o caminho,
# ela cai na conversa do pedido, e o mesmo código trata as três: quem
# responde por e-mail não pode ter um atendimento pior do que quem
# responde pelo chat.
#
# E A RESPOSTA NÃO FICA ESPERANDO ALGUÉM LER
#
# Chegando qualquer coisa do cliente num pedido travado, o redator lê
# o que veio, separa o que corresponde ao que faltava e preenche. O
# relógio volta a andar na mesma hora, com a hora de graça quando as
# quatro já passaram.
# ══════════════════════════════════════════════════════════════════

INTERVALO_COBRANCA = 6        # horas


def _texto_da_cobranca(pedido: dict, pend: dict, vez: int) -> str:
    """O comunicado. Muda de tom conforme a vez, sem perder a educação."""
    itens = "\n".join(f"  • {_rotulo(i)}" for i in pend["obrigatorias"])
    complementares = ""
    if pend["complementares"]:
        complementares = (
            "\n\nAproveitando, isto aqui não segura nada e deixa o documento "
            "mais completo, se você tiver à mão:\n"
            + "\n".join(f"  • {i['rotulo']}" for i in pend["complementares"]))

    abertura = {
        1: "Passando para lembrar de uma informação que ficou faltando.",
        2: "Voltando ao seu pedido: ainda falta uma informação para "
           "concluirmos.",
    }.get(vez, "O seu documento continua parado esperando uma informação.")

    return (
        f"{abertura}\n\n"
        f"Pedido {pedido.get('numero')}.\n\n"
        f"O que falta:\n{itens}{complementares}\n\n"
        f"Por que isso importa: o texto do seu documento já está escrito na "
        f"parte que não depende disso, e a conferência final é a última etapa "
        f"antes de ele ir para a sua aprovação. Sem essa informação, o "
        f"documento não pode ser concluído, e é só isso que está segurando a "
        f"entrega.\n\n"
        f"Como responder: do jeito que for mais fácil para você. Responda "
        f"este e-mail escrevendo a informação, mande pelo chat da sua área na "
        f"plataforma, ou responda no WhatsApp. Chega tudo no mesmo lugar, e "
        f"assim que chegar o prazo volta a correr."
    )


def cobrar_pendencias() -> dict:
    """De seis em seis horas, enquanto faltar o indispensável."""
    db = get_db()
    parados = db.table("pedidos_contrato") \
        .select("id,numero,fase,fase_em,avanca_em,pendencia_cobrada_em,"
                "pendencia_cobrancas,pago_em") \
        .in_("fase", list(_PROXIMA)) \
        .is_("avanca_em", "null") \
        .is_("excluido_em", "null") \
        .limit(100).execute().data or []

    enviados, erros = 0, []
    for p in parados:
        try:
            pend = pendencias_do_pedido(p["id"])
            if not pend["trava"]:
                # O relógio devia estar andando. Conserta em vez de
                # cobrar: cobrar o que já foi enviado é o jeito mais
                # rápido de perder a confiança do cliente.
                revisar_pendencias(p["id"])
                continue

            ultimo = p.get("pendencia_cobrada_em") or p.get("fase_em") or p.get("pago_em")
            if _horas_desde(ultimo) < INTERVALO_COBRANCA:
                continue

            vez = int(p.get("pendencia_cobrancas") or 0) + 1
            recado(p["id"], _texto_da_cobranca(p, pend, vez),
                   canais=["PLATAFORMA", "EMAIL", "WHATSAPP"], autor="AGENTE",
                   assunto=f"Falta uma informação para concluir o seu "
                           f"documento, {p.get('numero')}")
            db.table("pedidos_contrato").update({
                "pendencia_cobrada_em": _agora(),
                "pendencia_cobrancas": vez,
                "atualizado_em": _agora(),
            }).eq("id", p["id"]).execute()
            registrar_evento(None, "BALCAO_PENDENCIA_COBRADA",
                             {"pedido_id": p["id"], "vez": vez,
                              "faltam": len(pend["obrigatorias"])})
            enviados += 1
        except Exception as e:
            erros.append(f"{p.get('numero')}: {e}")

    return {"cobrados": enviados, "erros": erros}


# ── A resposta do cliente, venha de onde vier ───────────────────

SYSTEM_COMPLEMENTO = """Você recebe a resposta de um cliente que estava \
devendo informações para um contrato, e a lista do que faltava. Sua tarefa é \
só uma: dizer quais desses campos a mensagem responde, e com que valor.

REGRAS
- Só preencha campo que a mensagem responde de forma clara. Na dúvida, deixe \
de fora: campo preenchido errado é pior do que campo vazio, porque ninguém \
vai conferir de novo.
- Não invente, não complete, não deduza. Se a pessoa escreveu "moro na Rua \
das Flores", isso é a rua, e não o endereço completo.
- Copie o valor como a pessoa escreveu, corrigindo só maiúsculas óbvias.
- Se a mensagem não responder nada da lista, devolva a lista vazia."""

FERRAMENTA_COMPLEMENTO = [{
    "name": "preencher",
    "description": "Registra os campos que a mensagem do cliente respondeu.",
    "input_schema": {
        "type": "object",
        "properties": {
            "campos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "campo": {"type": "string"},
                        "valor": {"type": "string"},
                    },
                    "required": ["campo", "valor"],
                },
            },
        },
        "required": ["campos"],
    },
}]


def complementar_com_a_resposta(pedido_id: str, texto: str) -> dict:
    """Lê o que o cliente mandou e preenche o que dá.

    A leitura é feita por modelo porque a resposta vem em português
    corrido, do jeito que a pessoa fala: "o CPF dele é 123, e ele é
    casado". O que o modelo NÃO faz é decidir se aquilo basta: quem
    decide é `pendencias_do_pedido`, comparando o que ficou preenchido
    com o que o tipo de contrato exige."""
    texto = (texto or "").strip()
    if not texto:
        return {"preenchidos": 0}

    pend = pendencias_do_pedido(pedido_id)
    if not pend["itens"]:
        return {"preenchidos": 0}

    lista = "\n".join(
        f"- {i['campo']}: {_rotulo(i)}"
        + (" (indispensável)" if i["obrigatorio"] else " (complementar)")
        for i in pend["itens"])

    try:
        r = _claude().messages.create(
            model=get_settings().claude_model, max_tokens=1200,
            system=SYSTEM_COMPLEMENTO,
            tools=FERRAMENTA_COMPLEMENTO,
            tool_choice={"type": "tool", "name": "preencher"},
            messages=[{"role": "user", "content":
                       f"CAMPOS QUE FALTAM:\n{lista}\n\n"
                       f"MENSAGEM DO CLIENTE:\n{texto[:4000]}"}],
        )
    except Exception as e:
        print(f"[balcao] leitura da resposta falhou: {e}")
        return {"preenchidos": 0, "erro": str(e)}

    achados = []
    for bloco in r.content:
        if getattr(bloco, "type", "") == "tool_use" and bloco.name == "preencher":
            achados = (bloco.input or {}).get("campos") or []

    if not achados:
        return {"preenchidos": 0}

    db = get_db()
    atual = db.table("pedidos_contrato").select("dados,partes") \
        .eq("id", pedido_id).limit(1).execute().data[0]
    dados = dict(atual.get("dados") or {})
    partes = list(atual.get("partes") or [])
    por_papel = {p.get("papel"): p for p in partes}

    preenchidos = []
    for a in achados:
        campo = (a.get("campo") or "").strip()
        valor = (a.get("valor") or "").strip()
        if not campo or not valor:
            continue
        item = next((i for i in pend["itens"] if i["campo"] == campo), None)
        if not item:
            continue
        if item.get("origem") == "PARTE":
            papel = item.get("papel")
            alvo = por_papel.setdefault(papel, {"papel": papel})
            # o campo da parte vem como "papel_rótulo"; o que interessa
            # é o rótulo, que é o nome do campo na estrutura da parte
            chave = {"nome completo": "nome", "CPF ou CNPJ": "cpf_cnpj",
                     "endereço completo": "endereco"}.get(item["rotulo"],
                                                          item["rotulo"])
            alvo[chave] = valor
        else:
            dados[campo] = valor
        preenchidos.append(_rotulo(item))

    if not preenchidos:
        return {"preenchidos": 0}

    db.table("pedidos_contrato").update({
        "dados": dados, "partes": list(por_papel.values()) or partes,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    estado = revisar_pendencias(pedido_id)
    registrar_evento(None, "BALCAO_PENDENCIA_COMPLEMENTADA",
                     {"pedido_id": pedido_id, "campos": preenchidos,
                      "ainda_falta": estado.get("travado")})

    # O redator refaz a minuta com o que chegou. Sem isto, o documento
    # seguiria para a conferência final sem a informação que acabou de
    # ser prestada, que é o pior desfecho possível desta espera.
    if not estado.get("travado"):
        try:
            redigir(pedido_id, auto=True)
        except Exception as e:
            print(f"[balcao] minuta não refeita agora, fica para a esteira: {e}")

    return {"preenchidos": len(preenchidos), "campos": preenchidos,
            "ainda_falta": estado.get("travado"),
            "pendencias": estado}


def resposta_do_cliente(pedido_id: str, texto: str, canal: str = "PLATAFORMA",
                        anexos: list[str] | None = None,
                        responder: bool = True) -> dict:
    """Porta única para o que o cliente responde, venha de onde vier.

    Chat, e-mail e WhatsApp entram por aqui. Ter uma porta só é o que
    garante que a experiência não dependa do canal escolhido, e o que
    evita três implementações que envelhecem em ritmos diferentes."""
    db = get_db()
    if texto.strip():
        db.table("pedidos_mensagens").insert({
            "pedido_id": pedido_id, "autor": "CLIENTE",
            "texto": texto[:4000], "canais": [canal.upper()],
        }).execute()

    registrar_evento(None, "BALCAO_RESPOSTA_CLIENTE",
                     {"pedido_id": pedido_id, "canal": canal.upper(),
                      "anexos": len(anexos or [])})

    r = db.table("pedidos_contrato").select("avanca_em,fase") \
        .eq("id", pedido_id).limit(1).execute().data
    travado = bool(r) and r[0].get("avanca_em") is None \
        and r[0].get("fase") in _PROXIMA

    saida: dict = {"registrado": True, "travado_antes": travado}
    if travado:
        saida.update(complementar_com_a_resposta(pedido_id, texto))
        # Anexo também destrava: documento que chega costuma trazer a
        # informação que faltava, mesmo sem uma linha escrita.
        if anexos and saida.get("preenchidos", 0) == 0:
            saida["pendencias"] = revisar_pendencias(pedido_id)

    # NINGUÉM FICA SEM RESPOSTA
    #
    # Antes, a mensagem do cliente era só matéria prima: ela preenchia
    # o que faltava e morria ali. Do lado dele, escrever "como está meu
    # contrato" era falar com a parede. Agora o atendimento varre o
    # estado do pedido, responde o que foi perguntado e, se houver
    # urgência, abre um alerta de prioridade para quem cuida do caso.
    #
    # A resposta é gerada depois do preenchimento de propósito: assim
    # ela já conta o que mudou com a mensagem que acabou de chegar.
    if responder and texto.strip():
        try:
            from . import atendente
            r = atendente.responder("PEDIDO", pedido_id, texto)
            # Volta pelo mesmo canal por onde veio. Responder um chat
            # também por e-mail e WhatsApp é encher a caixa de quem
            # está com a tela aberta na frente.
            canais = ["PLATAFORMA"]
            if canal.upper() in ("EMAIL", "WHATSAPP"):
                canais.append(canal.upper())
            recado(pedido_id, r["texto"], canais=canais, autor="AGENTE",
                   assunto="Sobre o seu pedido")
            saida["resposta"] = r["texto"]
            saida["urgencia_registrada"] = bool(r.get("avisos"))
        except Exception as e:
            print(f"[balcao] atendimento não respondeu agora: {e}")
    return saida


def pedido_por_numero(numero: str) -> dict | None:
    """Acha o pedido pelo protocolo. Usado pela entrada de e-mail."""
    if not numero:
        return None
    r = get_db().table("pedidos_contrato") \
        .select("id,numero,cliente_id,fase,avanca_em") \
        .eq("numero", numero.upper()).limit(1).execute().data
    return r[0] if r else None


def pedido_travado_do_cliente(cliente_id: str) -> dict | None:
    """O pedido daquele cliente que está esperando informação.

    Serve ao WhatsApp, que chega sem número de protocolo: a mensagem é
    do cliente, e se ele tem exatamente um pedido parado esperando algo,
    é sobre esse que ele está falando. Com mais de um, não se adivinha:
    a conversa vai para o caso, como antes."""
    r = get_db().table("pedidos_contrato").select("id,numero") \
        .eq("cliente_id", cliente_id) \
        .in_("fase", list(_PROXIMA)) \
        .is_("avanca_em", "null") \
        .is_("excluido_em", "null") \
        .limit(2).execute().data or []
    return r[0] if len(r) == 1 else None
