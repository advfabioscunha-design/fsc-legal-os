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

O desconto tem dois degraus e para aí:
  10%  quando o cliente resiste depois de ouvir a proposta
  20%  quando ele sinaliza que vai embora — é a última palavra

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
from datetime import datetime, timezone

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
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

COMO CONDUZIR
1. Comece pelo valor, nunca pelo preço. Diga o que ela leva e por que isso \
importa no caso dela.
2. Só então diga o preço, com naturalidade, sem pedir desculpa por ele.
3. Se ela hesitar, PERGUNTE o que achou do valor e o que a está segurando. \
Não despeje outro argumento e não ofereça desconto antes de ouvir.
4. Ouvida a objeção, responda o que ela de fato disse. Se for comparação com \
modelo grátis da internet, fale do custo de refazer um contrato que não \
sustenta o combinado. Se for dúvida sobre o serviço, explique o rito.
5. Só depois disso, se ela seguir resistente, use a ferramenta de desconto.

REGRAS DURAS
- Você NUNCA calcula preço de cabeça. Para qualquer valor, chame \
`propor_valor`. O que ela devolver é o preço, e é o único número que você diz.
- Nunca ofereça mais de dois descontos. A ferramenta recusa o terceiro; se \
recusar, diga com franqueza que esse é o melhor valor e volte a falar do serviço.
- Esgotados os dois descontos, se o cliente disser que mesmo assim não \
consegue, ofereça a ele deixar uma proposta para o escritório analisar e use \
`registrar_proposta`. Não ofereça isso antes: enquanto houver desconto a dar, \
pedir contraproposta é ensinar a pechinchar. E nunca diga que a proposta será \
aceita, nem dê a entender que sim. O escritório responde depois.
- Nunca afirme valor mínimo de tabela da OAB, nem cite tabela de honorários, \
nem diga "abaixo do mínimo da categoria". Você não tem essa informação.
- Nunca prometa resultado, nem diga que o contrato é imune a questionamento, \
nem que substitui escritura pública quando o tipo exige cartório.
- Não invente prazo, forma de pagamento ou serviço que não esteja aqui.
- Se a pessoa perguntar algo jurídico do caso dela, responda o geral e diga \
que a análise do caso concreto é o atendimento jurídico prévio, que é um \
serviço à parte e pode ser somado.

QUANDO ELA ACEITAR
Chame `fechar` com o valor combinado. Depois disso, diga que o próximo passo é \
criar o acesso dela e reúna as informações do contrato.

Respostas curtas: duas a quatro frases. Uma pergunta por vez."""


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
                        "0 para o preço cheio; 10 quando o cliente resistiu "
                        "depois de ouvir a proposta; 20 só quando ele "
                        "sinalizou que vai embora. Nunca outro número."),
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
            "ÚLTIMO RECURSO. Use só depois que o desconto de 20% já foi "
            "oferecido e o cliente disse que ainda não consegue pagar. "
            "Registra o valor que ele propõe para o escritório analisar. "
            "Você NÃO aceita a proposta nem diz que ela será aceita: "
            "quem decide é o advogado."),
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
    return anthropic.Anthropic(api_key=s.claude_api_key)


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
    """Grava o combinado e deixa o pedido pronto para o cadastro."""
    db = get_db()
    pedido_atual = _pedido(pedido["id"])
    desconto = _maior_desconto_ja_dado(pedido_atual)
    conta = catalogo.precificar(
        pedido_atual["tipo"],
        com_orientacao=bool(pedido_atual.get("com_orientacao")),
        desconto_pct=desconto,
        urgente=bool(pedido_atual.get("urgente")),
        assinatura_digital=bool(pedido_atual.get("assinatura_digital", True)),
    )
    db.table("pedidos_contrato").update({
        "valor_base": conta["base"],
        "desconto_pct": conta["desconto_pct"],
        "valor": conta["total"],
        "prazo_entrega_horas": conta["horas"],
        "atualizado_em": _agora(),
    }).eq("id", pedido["id"]).execute()

    _anotar(pedido["id"], {"tipo": "FECHADO", "total": conta["total"],
                           "resumo": (args.get("resumo") or "")[:300]})
    registrar_evento(None, "BALCAO_NEGOCIACAO_FECHADA",
                     {"pedido_id": pedido["id"], "total": conta["total"],
                      "desconto_pct": conta["desconto_pct"]})
    return {"fechado": True, **conta, "pix": PIX}


# ── A conversa ──────────────────────────────────────────────────
def abrir(pedido_id: str) -> dict:
    """A primeira fala: o que o cliente leva, e depois quanto custa."""
    pedido = _pedido(pedido_id)
    t = catalogo.detalhe(pedido["tipo"]) or {}
    conta = catalogo.precificar(
        pedido["tipo"], com_orientacao=bool(pedido.get("com_orientacao")))

    texto = (
        f"Você está pedindo um {t.get('nome', 'contrato')} feito sob medida.\n\n"
        f"Quem escreve é advogado inscrito na OAB, que responde pelo que "
        f"assina. O texto é redigido a partir do seu caso, não é modelo "
        f"preenchido, segue a legislação aplicável a esse tipo de contrato, "
        f"passa por revisão e é conferido por advogado antes de chegar até "
        f"você. Fica pronto em até 24 horas.\n\n"
        f"O investimento é de R$ {conta['total']:.2f}."
    )
    _guardar_mensagem(pedido_id, "AGENTE", texto,
                      {"proposta": conta["total"], "desconto": 0})
    _anotar(pedido_id, {"tipo": "PROPOSTA", "desconto": 0,
                        "total": conta["total"], "porque": "abertura"})
    return {"texto": texto, "conta": conta, "tipo": t.get("nome"),
            "alerta": t.get("alerta")}


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

    contexto = (
        f"Tipo de contrato pedido: {t.get('nome')}.\n"
        f"Base legal: {t.get('base_legal', '')}.\n"
        f"Maior desconto já oferecido nesta conversa: "
        f"{_maior_desconto_ja_dado(pedido)}%."
    )
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

    for _ in range(4):                    # trava contra laço infinito
        r = cliente.messages.create(
            model=get_settings().claude_model, max_tokens=900,
            system=SYSTEM + "\n\n" + contexto,
            tools=FERRAMENTAS, messages=mensagens,
        )
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
        resposta_final = ("Me diga o que você achou do valor, quero entender "
                          "o que está te segurando.")

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
