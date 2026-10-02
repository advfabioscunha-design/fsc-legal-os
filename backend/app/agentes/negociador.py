"""
O agente que apresenta a proposta e conduz a negociação do balcão.

Ele vem ANTES da coleta: não adianta perguntar o CPF de quem ainda não
decidiu contratar. A ordem é proposta → aceite → cadastro → coleta.

COMO ELE NEGOCIA
----------------
Primeiro dá valor ao serviço, e só depois fala de desconto. A ordem
importa: quem abre com desconto ensina o cliente que o preço era
inflado. O valor aqui é concreto e verificável — quem escreve é
advogado inscrito, que responde pelo que assina; o contrato sai
conforme a lei do tipo; e sai em 24 horas, ou em 4 a 6 se o cliente
precisar.

Depois escuta. Quando o cliente resiste ao preço, a instrução é
perguntar o que ele achou — não despejar outro argumento. Objeção de
preço quase nunca é sobre preço: é dúvida se o serviço resolve, ou
comparação com um modelo grátis da internet. As duas se respondem
melhor com pergunta do que com desconto.

A ESCADA TEM TRÊS DEGRAUS, E TODOS TÊM DE ACONTECER
---------------------------------------------------
  10%  assim que o preço vira o ponto da conversa
  20%  se a hesitação continuar — é a última palavra do agente
  a proposta dela, que o agente OFERECE e leva ao advogado

O erro que esta versão corrige é de omissão, e era caro. Cada degrau
estava escrito para esperar o cliente INSISTIR: o de 10% só descia
"quando o cliente resiste", o de 20% "quando ele sinaliza que vai
embora", e a contraproposta era "último recurso", depois de ele dizer
que não conseguia pagar.

Mas muita gente não insiste. Diz "vou pensar", agradece e some — e
some justamente quem mais precisava do desconto, porque pedir abatimento
dá vergonha. Do lado de fora, a negociação simplesmente não existia:
o cliente via um preço, achava caro e ia embora sem saber que havia
conversa a ter.

Agora hesitação basta, e o terceiro degrau é oferecido pelo agente, que
é o único dos dois que sabe que ele existe.

O TETO É DE VERDADE
-------------------
Quem calcula o preço é `catalogo_contratos.precificar`, não o modelo. O
agente pede um degrau de desconto; o código confere se ele já foi dado
e recusa o terceiro. Um modelo de linguagem instruído a negociar, se
lhe derem a calculadora, acaba concedendo mais do que devia para agradar
quem insiste. Aqui ele não tem a calculadora.

O QUE ELE NÃO DIZ
-----------------
Não afirma valor mínimo de tabela da OAB, nem número de tabela nenhuma.
Afirmação de preço a consumidor que não se sustenta é publicidade
enganosa (CDC art. 37) e, vinda de escritório, também é problema ético.
O agente compara com o custo de refazer um contrato malfeito — que é
argumento honesto e não depende de número que ninguém conferiu.

Também não promete resultado, não diz que o contrato é "à prova de
qualquer questionamento", e não chama de definitivo o que exige
cartório: o alerta do tipo continua aparecendo antes do pagamento.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import anthropic

from ..core.ia import TEMPO_LIMITE, TENTATIVAS

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..core.texto import REGRA_DE_ESCRITA, humanizar
from ..core import ia as _ia_nucleo
from . import catalogo_contratos as catalogo

# O modelo vem da configuração, como no resto do sistema: trocar de
# modelo não pode exigir caçar string em cada agente.

# Os dois degraus, e nada além deles.
DEGRAUS = [0, catalogo.DESCONTO_RESISTENCIA, catalogo.DESCONTO_SAIDA]

PIX = {
    "chave": "986.141.852-00",
    "tipo": "CPF",
    "banco": "Caixa Econômica Federal",
    "favorecido": "Fábio Silva Cunha",
    # O escritório está migrando para conta PJ. Quando migrar, muda aqui
    # e em lugar nenhum mais — por isso a chave não está espalhada pelas
    # telas.
    "observacao": "Em breve a chave passará a ser do CNPJ do escritório.",
}


SYSTEM = """Você atende no balcão de contratos da FSC Advocacia, escritório \
do advogado Fábio Silva Cunha (OAB/RO 10.849). Seu trabalho é apresentar a \
proposta de um contrato sob medida e conduzir a conversa até o cliente \
decidir. Você fala português do Brasil, em tom de quem atende gente, não de \
quem vende plano de celular.

O QUE VOCÊ ESTÁ VENDENDO
Um contrato escrito por advogado, sob medida para o caso da pessoa, dentro da \
legislação daquele tipo de contrato, entregue em 24 horas (ou em 4 a 6 horas, \
se ela precisar, com acréscimo). Não é modelo preenchido: o texto é redigido a \
partir do que ela contar, revisado, e conferido por advogado antes de chegar \
às mãos dela.

POR QUE SAI MAIS BARATO
Porque a pessoa participa. Ela mesma informa as condições do negócio pela \
plataforma, e isso poupa as horas de reunião que um escritório comum cobra. O \
que barateia é a participação dela, nunca o cuidado com o documento. Diga isso \
quando falar de preço: é a explicação honesta de um valor abaixo do mercado, e \
evita que o barato pareça descuido.

COMO CONDUZIR
1. Comece pelo valor, nunca pelo preço. NÃO DIGA NÚMERO NA ABERTURA. Primeiro \
ela precisa entender que não vai receber modelo pronto, e sim documento \
redigido por profissional que responde pelo que assina.
2. O preço só entra quando ela pedir, ou quando já tiver dito que entendeu o \
serviço. Aí sim, diga com naturalidade, sem pedir desculpa por ele, e explique \
em uma frase por que é abaixo do mercado.
3. Se ela hesitar, PERGUNTE o que achou do valor e o que a está segurando. \
Não despeje outro argumento e não ofereça desconto antes de ouvir.
4. Ouvida a objeção, responda o que ela de fato disse. Se for comparação com \
modelo grátis da internet, fale do custo de refazer um contrato que não \
sustenta o combinado. Se for dúvida sobre o serviço, explique o rito.
5. Respondida a objeção, se o preço continuar sendo o problema, desça o \
primeiro degrau.

A ESCADA DA NEGOCIAÇÃO, E ELA TEM DE ACONTECER

São três degraus, nesta ordem, e nenhum deles pode ficar guardado no \
bolso. Muita gente não pede desconto por vergonha, e some em silêncio: \
quem espera a pessoa brigar pelo preço perde justamente quem mais \
precisava do desconto.

PRIMEIRO DEGRAU, 10%. Desça assim que o preço aparecer como o ponto da \
conversa. Não espere a pessoa reclamar nem insistir. Qualquer um destes \
sinais já basta: "vou pensar", "está um pouco acima do que eu posso", \
"depois eu vejo", "preciso conversar em casa", "tá puxado", "é caro", ou \
ela simplesmente parar de responder sobre o valor e mudar de assunto. \
Hesitação é pedido de desconto feito com educação.

SEGUNDO DEGRAU, 20%. Se depois do primeiro ela continuar hesitando, ou \
agradecer e não seguir, desça o segundo. Diga que é o melhor que você \
consegue fazer, porque é verdade.

TERCEIRO DEGRAU, A PROPOSTA DELA. Esgotados os dois descontos, se o valor \
ainda não couber, VOCÊ oferece: pergunte quanto ela conseguiria pagar e \
diga que leva ao escritório para analisar. Não espere ela pedir essa \
chance, porque ela não sabe que existe. Use `registrar_proposta` com o \
valor e com o motivo nas palavras dela.

Nunca diga que a proposta será aceita, nem dê a entender que sim. Diga \
que leva para análise e que retorna com a resposta. Quem decide é o \
advogado.

QUEM ESTÁ DO OUTRO LADO

Uma pessoa que precisa de um documento e está contando dinheiro. O país \
não está fácil, e quem procura advogado pela internet em vez de ir a um \
escritório quase sempre está apertado. Isso não é motivo para ter pena \
dela, é motivo para tratá-la bem.

Na prática, isso quer dizer:

Quem pede desconto não está pedindo favor. Nunca faça a pessoa se sentir \
mal por perguntar o preço, por achar caro, por querer pensar ou por dizer \
não. Nada de "esse valor já é simbólico", "é o mínimo que dá para fazer" \
nem qualquer frase que cobre gratidão pelo desconto.

Não insista. Se ela disse que vai pensar, agradeça e deixe a porta \
aberta: "fico à disposição, me chama quando quiser". Perseguir cliente \
com mensagem atrás de mensagem é o que faz as pessoas bloquearem o \
número do escritório.

Diga o preço sem rodeio e sem pedir desculpa por ele. Enrolar para falar \
de valor deixa a pessoa desconfortável, e constrangimento afasta mais \
que preço alto.

Se ela decidir não contratar, encerre bem. Agradeça de verdade, diga que \
o escritório fica à disposição, e não tente mais nada. Gente que foi bem \
tratada volta, e indica.

REGRAS DURAS
- Você NUNCA calcula preço de cabeça. Para qualquer valor, chame \
`propor_valor`. O que ela devolver é o preço, e é o único número que você diz.
- Nunca ofereça mais de dois descontos. A ferramenta recusa o terceiro; se \
recusar, diga com franqueza que esse é o melhor valor e passe para o terceiro \
degrau, que é a proposta dela.
- A ordem dos degraus não se pula. Enquanto houver desconto a dar, pedir \
contraproposta é ensinar a pechinchar; mas depois do segundo desconto, \
segurar a proposta é perder a venda calado.
- Nunca afirme valor mínimo de tabela da OAB, nem cite tabela de honorários, \
nem diga "abaixo do mínimo da categoria". Você não tem essa informação.
- Nunca prometa resultado, nem diga que o contrato é imune a questionamento, \
nem que substitui escritura pública quando o tipo exige cartório.
- Não invente prazo, forma de pagamento ou serviço que não esteja aqui.
- Se a pessoa perguntar algo jurídico do caso dela, responda o geral e diga \
que a análise do caso concreto é o atendimento jurídico prévio, que é um \
serviço à parte e pode ser somado.

COMO CONVIDAR A FECHAR, SEM PARECER GRAVAÇÃO
Nunca repita o mesmo convite duas vezes na mesma conversa. Nem a mesma \
frase, nem variação próxima dela. Quem lê "Topa por R$ 230,00?" duas vezes \
percebe na hora que não tem gente do outro lado.

Prefira o convite indireto, que soa a quem está tocando o serviço e não a \
quem está vendendo. Alterne entre caminhos diferentes, e escolha o que faz \
sentido para o que ela acabou de dizer:

  · dar andamento: "Vamos dar andamento?", "Sigo com o seu documento?", \
"Posso começar a preparar?"
  · ensinar o caminho: "Se estiver bom para você, é só escrever aceito \
aqui, ou clicar no botão verde Quero contratar, que eu sigo."
  · perguntar o que falta: "Ficou alguma dúvida antes de eu começar?", \
"Tem algo que você queira ajustar antes?"
  · falar do próximo passo: "O passo seguinte é o pagamento e a lista do \
que eu preciso saber. Quer que eu já abra?"
  · silêncio de convite: às vezes a melhor saída é responder a dúvida dela \
e parar. Não é obrigatório convidar em toda mensagem.

PELO MENOS UMA VEZ, ENSINE COMO SE CONTRATA
Muita gente não fecha porque não sabe o que clicar. Em algum momento da \
conversa, de preferência logo depois do primeiro valor, diga em uma linha \
que basta escrever aceito ou quero contratar, ou clicar no botão verde \
Quero contratar. Diga uma vez, com naturalidade, e não repita a cada fala.

QUANDO ELA ACEITAR
Chame `fechar` com o valor combinado. Depois disso, diga que o próximo passo é \
o pagamento, e que logo em seguida você volta para pedir as informações do \
contrato.

MUDANÇA DE IDEIA VALE, E VALE SEMPRE
Se a pessoa já tiver deixado uma proposta para o escritório analisar e depois \
disser que aceita o valor que você ofereceu, é o aceite que vale. Não pergunte \
se ela tem certeza, não diga que a proposta dela está em análise, não a mande \
esperar: chame `fechar` na hora, com o último valor que VOCÊ ofereceu, e diga \
em uma frase que a proposta anterior fica sem efeito.

Isso serve para qualquer frase com esse sentido: "aceito", "pode ser", "fechou", \
"vamos nesse valor", "tudo bem então", "aceito a sua proposta". Em caso de \
dúvida entre aceitar e continuar negociando, aceite: é o que a pessoa quer, e \
ela sempre pode voltar a falar.

O contrário também vale. Se ela já tiver aceitado e depois quiser propor outro \
valor, o pedido volta a ficar em aberto.

""" + REGRA_DE_ESCRITA + """

TAMANHO DA RESPOSTA
Curta. No máximo três frases, e frases curtas. Uma pergunta por vez, sempre no \
fim. Texto comprido em tela de atendimento não é lido, é pulado, e quem pula a \
explicação decide só pelo preço. Se precisar explicar algo longo, diga a parte \
que importa agora e ofereça detalhar."""


FERRAMENTAS = [
    {
        "name": "propor_valor",
        "description": (
            "Calcula e devolve o preço. Use SEMPRE que precisar dizer um "
            "valor, inclusive o primeiro. Você não calcula nada de cabeça."),
        "input_schema": {
            "type": "object",
            "properties": {
                "desconto": {
                    "type": "integer",
                    "description": (
                        "0 no primeiro valor. 10 assim que o preço virar o "
                        "ponto da conversa: basta hesitação, e hesitação é "
                        "pedido de desconto feito com educação ('vou "
                        "pensar', 'tá puxado', 'é mais do que eu posso', "
                        "ou parar de responder sobre o valor). NÃO espere a "
                        "pessoa insistir nem reclamar. 20 quando, depois do "
                        "de 10, ela continuar hesitando ou agradecer sem "
                        "seguir. Nunca outro número."),
                },
                "urgente": {
                    "type": "boolean",
                    "description": "Cliente quer em 4 a 6 horas em vez de 24.",
                },
                "assinatura_digital": {
                    "type": "boolean",
                    "description": (
                        "Falso se o cliente dispensou a assinatura eletrônica "
                        "e prefere só baixar o documento."),
                },
                "com_orientacao": {
                    "type": "boolean",
                    "description": "Cliente quer o atendimento jurídico prévio.",
                },
                "porque": {
                    "type": "string",
                    "description": (
                        "Em uma frase, o que na conversa justifica este "
                        "degrau. Fica registrado."),
                },
            },
            "required": ["desconto"],
        },
    },
    {
        "name": "fechar",
        "description": "O cliente aceitou. Registra o combinado e encerra a negociação.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resumo": {
                    "type": "string",
                    "description": "O que ficou combinado, em uma frase.",
                },
            },
            "required": ["resumo"],
        },
    },
    {
        "name": "registrar_proposta",
        "description": (
            "O TERCEIRO E ÚLTIMO DEGRAU. Use depois que o desconto de 20% "
            "já foi oferecido e o valor ainda não coube no bolso dela. "
            "VOCÊ oferece esta saída, não espera ela pedir: a pessoa não "
            "sabe que essa chance existe, e cala em vez de perguntar. "
            "Pergunte quanto ela conseguiria pagar e registre aqui, com o "
            "motivo nas palavras dela. Você NÃO aceita a proposta nem diz "
            "que ela será aceita: leva para o advogado analisar e retorna "
            "com a resposta."),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor": {
                    "type": "number",
                    "description": "Quanto o cliente se dispõe a pagar, em reais.",
                },
                "motivo": {
                    "type": "string",
                    "description": (
                        "Por que esse valor, nas palavras dele. É a parte mais "
                        "útil para quem vai decidir: anote o que ele disse, não "
                        "um resumo genérico."),
                },
            },
            "required": ["valor"],
        },
    },
]


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claude():
    s = get_settings()
    if not s.claude_api_key:
        raise ValueError("Chave da Claude não configurada no servidor.")
    return _ia_nucleo.cliente(s.claude_api_key)


def _pedido(pedido_id: str) -> dict:
    r = get_db().table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    return r[0]


def _maior_desconto_ja_dado(pedido: dict) -> int:
    dados = pedido.get("negociacao") or []
    return max([int(t.get("desconto") or 0) for t in dados
                if t.get("tipo") == "PROPOSTA"] or [0])


def _anotar(pedido_id: str, turno: dict) -> None:
    db = get_db()
    atual = db.table("pedidos_contrato").select("negociacao") \
        .eq("id", pedido_id).limit(1).execute().data
    hist = list((atual[0].get("negociacao") if atual else None) or [])
    hist.append({"em": _agora(), **turno})
    db.table("pedidos_contrato").update({"negociacao": hist[-80:]}) \
        .eq("id", pedido_id).execute()


def _guardar_mensagem(pedido_id: str, autor: str, texto: str,
                      meta: dict | None = None) -> None:
    get_db().table("pedidos_mensagens").insert({
        "pedido_id": pedido_id, "autor": autor, "texto": texto,
        "meta": meta or {},
    }).execute()


# ── As ferramentas, executadas aqui e não pelo modelo ───────────
def _executar_propor(pedido: dict, args: dict) -> dict:
    """Calcula o preço e aplica o teto dos dois degraus."""
    pedido_id = pedido["id"]
    pedido_atual = _pedido(pedido_id)
    ja_dado = _maior_desconto_ja_dado(pedido_atual)
    pedido_desconto = int(args.get("desconto") or 0)

    # Só os degraus previstos existem. 15% não existe; 5% não existe.
    if pedido_desconto not in DEGRAUS:
        pedido_desconto = min(
            [d for d in DEGRAUS if d >= pedido_desconto] or [catalogo.DESCONTO_SAIDA])

    recusado = None
    if pedido_desconto > catalogo.DESCONTO_SAIDA:
        pedido_desconto, recusado = catalogo.DESCONTO_SAIDA, "acima do teto"
    elif pedido_desconto < ja_dado:
        # Voltar atrás no desconto já oferecido seria desonesto com quem
        # já ouviu o número.
        pedido_desconto = ja_dado
    elif ja_dado >= catalogo.DESCONTO_SAIDA and pedido_desconto > ja_dado:
        recusado = "o teto já foi usado"

    conta = catalogo.precificar(
        pedido_atual["tipo"],
        com_orientacao=bool(args.get("com_orientacao",
                                     pedido_atual.get("com_orientacao"))),
        desconto_pct=pedido_desconto,
        urgente=bool(args.get("urgente", pedido_atual.get("urgente"))),
        assinatura_digital=bool(args.get("assinatura_digital",
                                         pedido_atual.get("assinatura_digital", True))),
    )

    _anotar(pedido_id, {"tipo": "PROPOSTA", "desconto": pedido_desconto,
                        "total": conta["total"],
                        "porque": (args.get("porque") or "")[:300],
                        "recusado": recusado})

    # O QUADRO ACOMPANHA A CONVERSA
    #
    # Dito o primeiro valor, o pedido sai da qualificação e passa para
    # a proposta. Sem isso, o cartão ficava parado na primeira coluna
    # até o cliente aceitar, e quem olhasse o quadro não saberia
    # distinguir quem ainda está explicando o que precisa de quem já
    # está decidindo sobre um número.
    try:
        if pedido_atual.get("fase") == "QUALIFICACAO":
            get_db().table("pedidos_contrato").update({
                "fase": "PROPOSTA", "fase_em": _agora(),
                "atualizado_em": _agora(),
            }).eq("id", pedido_id).execute()
    except Exception as e:
        print(f"[negociador] fase não atualizada: {e}")

    resposta = dict(conta)
    resposta["pode_descontar_mais"] = pedido_desconto < catalogo.DESCONTO_SAIDA
    if recusado:
        resposta["aviso"] = (
            "Este é o melhor valor. Não há outro desconto disponível, "
            "diga isso com franqueza e volte a falar do serviço.")
    return resposta


def _executar_proposta(pedido: dict, args: dict) -> dict:
    """Guarda a contraproposta do cliente e avisa o escritório.

    Existe para não jogar informação fora. Sem isto, quem não consegue
    pagar o último valor fecha a página e ninguém fica sabendo que
    existiu. Três pessoas oferecendo R$ 150 pelo mesmo tipo de contrato
    na mesma semana dizem mais sobre o preço do que qualquer palpite.

    O agente não decide nada aqui. Ele registra e diz que o escritório
    responde, o que é verdade.
    """
    db = get_db()
    pedido_atual = _pedido(pedido["id"])
    try:
        valor = round(float(args.get("valor") or 0), 2)
    except (TypeError, ValueError):
        valor = 0.0
    if valor <= 0:
        return {"erro": "Pergunte quanto ele consegue pagar antes de registrar."}

    de_tabela = catalogo.precificar(
        pedido_atual["tipo"],
        com_orientacao=bool(pedido_atual.get("com_orientacao")),
    )["total"]

    db.table("pedidos_contrato").update({
        "proposta_valor": valor,
        "proposta_motivo": (args.get("motivo") or "")[:1000] or None,
        "proposta_em": _agora(),
        "proposta_status": "PENDENTE",
        "atualizado_em": _agora(),
    }).eq("id", pedido["id"]).execute()

    _anotar(pedido["id"], {"tipo": "PROPOSTA_CLIENTE", "total": valor,
                           "porque": (args.get("motivo") or "")[:300]})
    registrar_evento(None, "BALCAO_PROPOSTA_CLIENTE",
                     {"pedido_id": pedido["id"], "valor": valor,
                      "de_tabela": de_tabela,
                      "motivo": (args.get("motivo") or "")[:300]})

    try:
        _avisar_escritorio(pedido_atual, valor, args.get("motivo") or "")
    except Exception as e:
        print(f"[balcao] proposta não avisada por e-mail: {e}")

    # Honestidade com quem propôs: abaixo de 40% do valor de tabela a
    # chance é pequena, e é melhor ele saber agora do que esperar dois
    # dias por um não.
    resposta = {
        "registrada": True, "valor": valor, "de_tabela": de_tabela,
        "prazo_resposta": "até 1 dia útil",
    }
    if valor < de_tabela * 0.4:
        resposta["aviso"] = (
            "Registre, mas diga com franqueza que propostas muito abaixo do "
            "valor do serviço raramente são aceitas, para ele não criar "
            "expectativa.")
    return resposta


def _avisar_escritorio(pedido: dict, valor: float, motivo: str) -> None:
    from ..integracoes import avisos
    s = get_settings()
    t = catalogo.detalhe(pedido["tipo"]) or {}
    link = f"{s.app_url.rstrip('/')}/contratos"
    texto = (
        f"Proposta recebida no balcão.\n\n"
        f"Pedido: {pedido.get('numero')}\n"
        f"Documento: {t.get('nome', pedido.get('tipo'))}\n"
        f"Valor proposto: R$ {valor:.2f}\n"
        f"Motivo: {motivo or 'não informado'}\n\n"
        f"Responder em: {link}"
    )
    avisos.enviar_email(
        s.email_escritorio,
        f"[Balcão] Proposta de R$ {valor:.2f} para análise",
        texto, texto.replace("\n", "<br>"))


def _executar_fechar(pedido: dict, args: dict) -> dict:
    """Grava o combinado e manda o pedido para o pagamento.

    Três coisas acontecem aqui, e as três vieram de erro real.

    1. A PROPOSTA PENDENTE MORRE. O cliente que deixou uma proposta e
       depois aceita o valor do escritório mudou de ideia, e mudança de
       ideia vale. Deixar a proposta viva faria o escritório responder
       dias depois a uma negociação que já acabou.

    2. O VALOR É O COMBINADO, NÃO O DE TABELA. Se o escritório aceitou
       a proposta do cliente, é ela que vale. Se não, vale a conta com
       desconto, urgência e assinatura. O contrato mostrava o valor
       cheio mesmo quando o cliente tinha pago menos.

    3. O PRAZO ACOMPANHA A URGÊNCIA. Urgência contratada são 6 horas, e
       é isso que precisa aparecer no termo e no card."""
    db = get_db()
    p = _pedido(pedido["id"])
    campos: dict = {"atualizado_em": _agora()}
    cancelou_proposta = False

    if p.get("proposta_status") == "PENDENTE":
        campos.update({
            "proposta_status": "CANCELADA",
            "proposta_resposta": "O cliente aceitou a proposta do escritório "
                                 "antes da análise.",
            "proposta_respondida_em": _agora(),
            "proposta_respondida_por": "cliente",
        })
        cancelou_proposta = True

    # O escritório aceitou a proposta do cliente: é ela o preço.
    if p.get("proposta_status") == "ACEITA" and p.get("proposta_valor"):
        total = float(p["proposta_valor"])
        horas = catalogo.HORAS_URGENTE if p.get("urgente") else catalogo.HORAS_PADRAO
        conta = {
            "base": float(p.get("valor_base") or total), "desconto_pct": 0,
            "total": total, "horas": horas, "urgente": bool(p.get("urgente")),
            "origem": "PROPOSTA_DO_CLIENTE",
        }
    else:
        conta = catalogo.precificar(
            p["tipo"],
            com_orientacao=bool(p.get("com_orientacao")),
            desconto_pct=_maior_desconto_ja_dado(p),
            urgente=bool(p.get("urgente")),
            assinatura_digital=bool(p.get("assinatura_digital", True)),
        )
        conta["origem"] = "NEGOCIACAO"

    campos.update({
        "valor_base": conta["base"],
        "desconto_pct": conta["desconto_pct"],
        "valor": conta["total"],
        "prazo_entrega_horas": conta["horas"],
        # Aceito o valor, o cartão sai da proposta e vai para o
        # pagamento, que é onde o escritório precisa olhar: PIX
        # esperando conferência.
        "fase": "PAGAMENTO", "fase_em": _agora(),
    })
    db.table("pedidos_contrato").update(campos).eq("id", pedido["id"]).execute()

    _anotar(pedido["id"], {"tipo": "FECHADO", "total": conta["total"],
                           "origem": conta["origem"],
                           "proposta_cancelada": cancelou_proposta,
                           "resumo": (args.get("resumo") or "")[:300]})
    registrar_evento(None, "BALCAO_NEGOCIACAO_FECHADA",
                     {"pedido_id": pedido["id"], "total": conta["total"],
                      "desconto_pct": conta["desconto_pct"],
                      "origem": conta["origem"],
                      "proposta_cancelada": cancelou_proposta})
    return {"fechado": True, **conta, "pix": PIX,
            "proposta_cancelada": cancelou_proposta}


# ── A conversa ──────────────────────────────────────────────────
def abrir(pedido_id: str) -> dict:
    """A primeira fala: o que o cliente leva. Preço, ainda não.

    O preço saía aqui, na abertura, e junto com ele aparecia o valor no
    alto da tela antes de a pessoa ter ouvido uma linha sobre o que
    está comprando. Número antes de motivo é como o cliente compara
    contrato de advogado com modelo de internet: pelo preço, que é a
    única coisa que ele tem na mão.

    Agora a abertura diz três coisas e cala: não é modelo pronto, quem
    escreve responde pelo que assina, e o valor é menor do que o
    praticado justamente porque o cliente participa da elaboração em
    vez de pagar por horas de reunião. O número vem depois, quando ele
    pedir, e é aí que o painel de valor acende."""
    pedido = _pedido(pedido_id)
    t = catalogo.detalhe(pedido["tipo"]) or {}

    texto = (
        f"Você está pedindo um {t.get('nome', 'contrato')} feito sob medida.\n\n"
        f"Não é modelo pronto. O texto é redigido por advogado inscrito na "
        f"OAB, a partir do seu caso, seguindo a lei que rege esse tipo de "
        f"contrato. Fica pronto em até 24 horas.\n\n"
        f"Como você mesmo informa as condições aqui pela plataforma, o "
        f"serviço sai abaixo do praticado no mercado: o que barateia é a sua "
        f"participação, não o cuidado com o documento.\n\n"
        f"Quer que eu já passe o valor?"
    )
    _guardar_mensagem(pedido_id, "AGENTE", texto, {"abertura": True})
    return {"texto": texto, "tipo": t.get("nome"), "alerta": t.get("alerta")}


def _fechos_ja_usados(historico: list[dict]) -> list[str]:
    """As últimas frases de cada fala do agente, que é onde mora o convite.

    Pega a última frase porque é ali que o convite a fechar aparece, e
    é ela que soa robótica quando se repete. Guarda na ordem em que
    saíram e sem duplicar, para a lista não virar um parágrafo."""
    vistos: list[str] = []
    for m in historico:
        if str(m.get("autor", "")).upper() not in ("AGENTE", "ESCRITORIO"):
            continue
        texto = (m.get("texto") or "").strip()
        if not texto:
            continue
        # A última frase terminada em interrogação, se houver; senão, a
        # última linha não vazia.
        frases = [f.strip() for f in re.split(r"(?<=[.?!])\s+", texto) if f.strip()]
        ultima = ""
        for f in reversed(frases):
            if f.endswith("?"):
                ultima = f
                break
        if not ultima:
            linhas = [l.strip() for l in texto.splitlines() if l.strip()]
            ultima = linhas[-1] if linhas else ""
        ultima = ultima[:160]
        if ultima and ultima not in vistos:
            vistos.append(ultima)
    return vistos[-8:]


def conversar(pedido_id: str, mensagem: str,
              vai_sair: bool = False) -> dict:
    """Um turno da negociação.

    `vai_sair` é o sinal da tela de que o cliente está fechando a página.
    Não é o modelo que adivinha intenção de saída: quem sabe disso é o
    navegador.
    """
    pedido = _pedido(pedido_id)
    t = catalogo.detalhe(pedido["tipo"]) or {}
    db = get_db()

    # O sinal de saída chega sem texto: o cliente não escreveu nada, só
    # moveu o mouse para fora da janela. Gravar isso como fala dele
    # encheria a conversa de mensagens em branco — e a API recusa bloco
    # de texto vazio, que era o 500 que aparecia aqui.
    mensagem = (mensagem or "").strip()
    if mensagem:
        _guardar_mensagem(pedido_id, "CLIENTE", mensagem[:4000])

    historico = db.table("pedidos_mensagens").select("autor,texto") \
        .eq("pedido_id", pedido_id).order("criado_em").limit(40).execute().data or []
    mensagens = [{"role": "user" if m["autor"] == "CLIENTE" else "assistant",
                  "content": m["texto"]}
                 for m in historico if (m.get("texto") or "").strip()]

    # A conversa precisa terminar com a vez do cliente, senão não há o
    # que responder. Na saída sem texto, a "fala" é o próprio gesto.
    if not mensagens or mensagens[-1]["role"] != "user":
        mensagens.append({"role": "user",
                          "content": "[o cliente está fechando a página]"
                          if vai_sair else "[sem resposta]"})

    # ESTADO DA NEGOCIAÇÃO, DITO EM TODO TURNO
    #
    # Antes, o modelo recebia só o maior desconto já dado, e o resto
    # tinha de deduzir lendo a conversa. Num teste real isso falhou: o
    # cliente deixou uma proposta, mudou de ideia duas falas depois e
    # escreveu "aceito a proposta"; o agente não percebeu que havia algo
    # a cancelar e tratou como se a proposta dele continuasse valendo.
    #
    # O estado agora vem escrito, não deduzido. Modelo que precisa
    # reconstruir situação lendo histórico erra justamente quando a
    # pessoa muda de ideia, que é quando mais importa acertar.
    desconto_atual = _maior_desconto_ja_dado(pedido)
    conta_atual = catalogo.precificar(
        pedido["tipo"],
        com_orientacao=bool(pedido.get("com_orientacao")),
        desconto_pct=desconto_atual,
        urgente=bool(pedido.get("urgente")),
        assinatura_digital=bool(pedido.get("assinatura_digital", True)),
    )
    contexto = (
        f"Tipo de contrato pedido: {t.get('nome')}.\n"
        f"Base legal: {t.get('base_legal', '')}.\n"
        f"Maior desconto já oferecido nesta conversa: {desconto_atual}%.\n"
        f"Último valor que você ofereceu: R$ {conta_atual['total']:.2f}.\n"
        f"Urgência contratada: {'sim' if pedido.get('urgente') else 'não'}."
    )

    # O QUE VOCÊ JÁ DISSE, PARA NÃO DIZER DE NOVO
    #
    # "Topa por R$ 230,00?" duas vezes seguidas é o que faz a pessoa
    # perceber que está falando com máquina, e é um defeito que nenhuma
    # instrução genérica de "varie" resolve: o modelo não relê a
    # própria conversa procurando repetição, ele responde ao último
    # turno. Então a lista das frases de fecho já usadas vai escrita,
    # do mesmo jeito que o estado da negociação.
    usados = _fechos_ja_usados(historico)
    if usados:
        contexto += ("\n\nFRASES DE FECHO QUE VOCÊ JÁ USOU NESTA CONVERSA. "
                     "Não repita nenhuma delas, nem variação próxima. "
                     "Escolha outro caminho:\n"
                     + "\n".join(f"  · {u}" for u in usados))
    if pedido.get("proposta_status") == "PENDENTE":
        contexto += (
            f"\n\nATENÇÃO: este cliente já deixou uma proposta de "
            f"R$ {float(pedido.get('proposta_valor') or 0):.2f} para o "
            f"escritório analisar. Se ele agora aceitar o seu valor de "
            f"R$ {conta_atual['total']:.2f}, o aceite prevalece: chame "
            f"`fechar` imediatamente e avise, em uma frase, que a proposta "
            f"anterior fica sem efeito. Não o mande esperar resposta.")
    elif pedido.get("proposta_status") == "ACEITA":
        contexto += (
            f"\n\nO escritório ACEITOU a proposta deste cliente, de "
            f"R$ {float(pedido.get('proposta_valor') or 0):.2f}. Esse é o "
            f"valor do serviço. Não ofereça desconto nem recalcule: ao "
            f"fechar, o sistema usa esse valor.")
    elif pedido.get("proposta_status") == "CONTRAPROPOSTA":
        contexto += (
            f"\n\nO escritório respondeu à proposta deste cliente com uma "
            f"contraproposta de R$ {float(pedido.get('proposta_contra') or 0):.2f}. "
            f"Se ele aceitar, chame `fechar`.")
    if vai_sair:
        contexto += (
            "\n\nSINAL DA TELA: o cliente está saindo da página agora. Se "
            "ele ainda não ouviu o desconto de 20%, é o momento, faça a "
            "última proposta com `propor_valor` e desconto 20, em uma "
            "frase curta e sem drama. Se ele já ouviu, apenas agradeça e "
            "diga que o pedido fica guardado.")

    cliente = _claude()
    resposta_final, conta_final, fechou = "", None, False
    proposta = False

    # O QUE JÁ FOI FECHADO NÃO PODE SUMIR PORQUE A FRASE FALHOU
    #
    # O laço chama o modelo até quatro vezes, e no meio dele as
    # ferramentas ESCREVEM no banco: `fechar` trava o preço, cancela a
    # proposta pendente, muda a fase e começa a contar o prazo. Se a
    # chamada seguinte falhasse, a exceção subia inteira e a mensagem
    # nunca era guardada.
    #
    # O resultado era o pior desencontro possível: o pedido fechado no
    # banco, com relógio correndo, e o cliente vendo erro na tela, sem
    # PIX e sem nada na conversa. Ele tentava de novo, e o agente
    # trabalhava em cima de um pedido que já estava fechado.
    #
    # Agora a falha interrompe o laço e segue para o fecho da função: o
    # que foi gravado continua gravado, o cliente recebe o PIX se fechou,
    # e a frase que falta é substituída por uma honesta.
    falhou = False
    for _ in range(4):                    # trava contra laço infinito
        try:
            r = cliente.messages.create(
                model=get_settings().claude_model, max_tokens=900,
                system=SYSTEM + "\n\n" + contexto,
                tools=FERRAMENTAS, messages=mensagens,
            )
        except Exception as e:
            print(f"[negociador] parei no meio da conversa: {e}")
            falhou = True
            break
        usos = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
        texto = "".join(getattr(b, "text", "") for b in r.content
                        if getattr(b, "type", "") == "text").strip()
        if not usos:
            resposta_final = texto
            break

        mensagens.append({"role": "assistant", "content": r.content})
        resultados = []
        for u in usos:
            if u.name == "propor_valor":
                saida = _executar_propor(pedido, u.input or {})
                conta_final = saida
            elif u.name == "fechar":
                saida = _executar_fechar(pedido, u.input or {})
                conta_final, fechou = saida, True
            elif u.name == "registrar_proposta":
                saida = _executar_proposta(pedido, u.input or {})
                proposta = bool(saida.get("registrada"))
            else:
                saida = {"erro": "ferramenta desconhecida"}
            resultados.append({"type": "tool_result", "tool_use_id": u.id,
                               "content": json.dumps(saida, ensure_ascii=False)})
        mensagens.append({"role": "user", "content": resultados})
        resposta_final = texto or resposta_final

    if not resposta_final:
        # Fechou e a frase não saiu: o cliente precisa saber que fechou,
        # porque o PIX vai junto e o prazo já começou a contar.
        if fechou:
            resposta_final = ("Fechado. Já registrei aqui e o seu pedido "
                              "entrou na fila. O PIX está logo abaixo, e "
                              "assim que o pagamento cair eu sigo com você.")
        elif falhou:
            resposta_final = ("Recebi a sua mensagem e ela está guardada. "
                              "Tive um problema para responder agora; me "
                              "mande de novo em um minuto, ou siga pelo "
                              "botão aqui ao lado, que funciona igual.")
        else:
            resposta_final = ("Me diga o que você achou do valor, quero "
                              "entender o que está te segurando.")

    # A peneira antes de sair. O modelo insiste em travessão e em
    # asterisco de negrito, e a caixa de conversa mostra os dois como
    # texto cru. Instruir no prompt reduz; peneirar aqui garante.
    resposta_final = humanizar(resposta_final)

    _guardar_mensagem(pedido_id, "AGENTE", resposta_final,
                      {"total": (conta_final or {}).get("total"),
                       "fechou": fechou})
    return {"texto": resposta_final, "conta": conta_final, "fechou": fechou,
            "proposta_registrada": proposta,
            "pix": PIX if fechou else None}


def historico(pedido_id: str) -> list[dict]:
    return get_db().table("pedidos_mensagens").select("*") \
        .eq("pedido_id", pedido_id).order("criado_em") \
        .limit(200).execute().data or []
