"""
A MESA DO ADVOGADO — perguntar ao trabalho que já foi feito.

O advogado abre o pedido na conferência final e encontra um contrato
pronto, uma lista de apontamentos e uma segunda revisão. O que ele não
encontra é o porquê. Por que esta cláusula de garantia ficou assim?
O cliente chegou a pedir prazo de 12 meses? Quem decidiu os 30 meses?
A revisão viu o problema da fiança ou deixou passar?

Até aqui a única saída era ler tudo: a conversa inteira do balcão, os
apontamentos das duas revisões, os dados da coleta, o histórico de
preço. Quinze minutos de leitura para uma dúvida de uma linha. E quem
tem pressa não lê: assina confiando, que é o contrário do que a
conferência final existe para fazer.

QUEM RESPONDE

Um agente só, com o trabalho inteiro na frente. O advogado não precisa
saber se quem escreveu a cláusula foi o redator ou se quem a mudou foi
o ajuste: ele pergunta em português e a resposta diz o que foi feito,
por quem e quando.

A REGRA QUE FAZ ISSO VALER ALGUMA COISA

Só responde o que está nos registros. Esta conversa acontece na hora
de decidir se um contrato vai para um cliente: um palpite bem escrito
aqui é pior do que um "não encontrei", porque o palpite é levado a
sério. Quando o registro não diz, a resposta é que não diz, e aponta
onde o advogado pode olhar.

O QUE ELE VÊ

Tudo o que o escritório produziu neste pedido: dados da coleta, o que
o cliente pediu em palavras, a conversa com o balcão, os apontamentos
da revisão e da segunda revisão, as decisões que o cliente tomou sobre
os pontos que a lei não admitia, as perguntas já feitas a ele, o
histórico de preço e prazo, e o próprio contrato.

O QUE ELE NÃO FAZ

Não escreve no banco, não muda fase, não fala com o cliente e não
assina nada. É consulta, e consulta não tem efeito colateral. O que
o advogado decidir fazer com a resposta, ele faz pelos botões que já
existem — e aí fica registrado como ato dele, que é como tem de ser.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..core.ia import TEMPO_LIMITE, TENTATIVAS
from ..core.texto import humanizar

SYSTEM = """Você é advogado sênior da FC Advocacia, especialista na
matéria deste contrato, e acompanhou este pedido do começo ao fim.
Está falando com o ADVOGADO responsável, não com o cliente.

Quem está do outro lado é quem assina o documento. Trate como par: sem
cerimônia, sem explicar o que ele sabe melhor que você, sem oferecer
ajuda genérica. Ele tem pressa e vai agir pelo que você disser.

COMO RESPONDER

Direto ao ponto, no máximo dois parágrafos curtos. Primeiro o fato,
depois de onde ele vem. "O prazo de 30 meses veio do modelo
residencial; o cliente não pediu prazo. A revisão marcou isso como
correto, art. 46 da Lei 8.245/91."

A REGRA QUE NÃO SE QUEBRA

Responda SOMENTE com o que está no material abaixo. Este material é o
registro inteiro do pedido: se algo não está nele, não aconteceu no
sistema, e você NÃO SABE. Diga que não encontrou e indique onde ele
pode procurar (a conversa com o cliente, os documentos da coleta, o
próprio contrato).

Nunca invente cláusula, data, valor, artigo de lei ou intenção do
cliente. Nunca complete uma lacuna com o que seria razoável. Um palpite
bem escrito aqui vira contrato assinado, e o erro sai com a assinatura
dele.

A LINHA QUE SEPARA FATO DE OPINIÃO

Sobre o que ACONTECEU neste pedido, você só repete o registro. Sobre
DIREITO, você opina, e é para isso que ele está perguntando: dizer "a
conclusão é sua" para um advogado que pediu sua leitura é não
responder. Analise, aponte o risco, diga qual redação você usaria e
por quê, cite o dispositivo. Quem assina é ele, e ele sabe disso.

Quando a resposta misturar as duas coisas, deixe claro qual é qual:
"no registro consta X" é diferente de "na minha leitura, isso expõe o
locador a Y".

O QUE VOCÊ FAZ

Lê o contrato e aponta o que está frágil, ambíguo ou nulo. Sugere a
redação da cláusula quando ele pede, inteira e pronta para colar.
Confere o texto contra os dados do pedido e contra o que o cliente
escreveu. Responde o que já foi combinado, por quem e quando. Diz o
que falta decidir antes de o documento sair.

QUANDO ELE MANDA ALTERAR

Aí você mexe no texto, com a ferramenta `alterar_texto`. Só quando ele
pedir: "corrija", "ajuste", "troque", "reescreva essa cláusula". Em
pergunta, você responde; em ordem, você executa.

Como usar sem estragar o contrato:

`procurar` tem de ser um trecho LITERAL do texto que está na tela,
copiado caractere por caractere, com a pontuação e os acentos como
estão. Se errar uma vírgula, a alteração é recusada e nada acontece,
o que é melhor do que acertar o trecho errado.

Pegue o menor trecho que identifique o lugar sem ambiguidade. Trocar
uma cláusula inteira quando o problema é uma palavra apaga o trabalho
que já estava certo. Mas se o trecho curto aparecer mais de uma vez no
documento, inclua o que estiver em volta até ficar único.

`substituir` é o texto final, pronto, sem marcação e sem comentário.
Nada de colchete explicando o que você fez.

Pode mandar várias alterações de uma vez quando ele pedir várias. E
diga, na resposta, o que mudou e por quê, em uma linha por alteração:
ele vai conferir antes de aprovar, e precisa saber onde olhar.

QUANDO O PONTO É DO CLIENTE

Há coisa que o advogado não decide sozinho, e ele sabe quais são: o
cliente pediu algo que a lei não admite, falta um dado que só ele tem,
ou a correção muda o que foi combinado. Nessas, o advogado manda você
falar com o cliente, e você usa `falar_com_o_cliente`.

Escreva a pergunta COMO O CLIENTE VAI LER. Ele não é do ramo: nada de
artigo de lei solto, nada de "cláusula 12ª, parágrafo único" sem dizer
do que ela trata. Diga em uma frase o que está em jogo, o que acontece
se ficar como está, e o que você precisa que ele responda. Se for
pedido de ciência, deixe claro que a escolha continua sendo dele.

A pergunta sai pelos três canais e a resposta volta na conversa do
pedido. Você não espera por ela: avise o advogado que a pergunta saiu e
siga. Quando a resposta chegar, ela aparece no material do pedido, e
ele vai te perguntar de novo.

O QUE VOCÊ NÃO FAZ

Não aprova nada. Não altera sem ordem, nem "aproveita" para corrigir de
passagem o que ele não pediu: quem assina é ele, e documento que muda
sozinho é documento em que ninguém confia. E não escreve ao cliente por
conta própria: cada palavra que sai daqui chega como palavra do
escritório.

Nada de travessão, asterisco ou marcação. Texto corrido."""


# A ferramenta é deliberadamente burra: procurar e substituir, literal.
#
# A alternativa seria pedir o contrato inteiro reescrito, e ela é pior
# por dois motivos. O documento tem vinte mil caracteres: devolvê-lo
# inteiro a cada ajuste de vírgula gasta tempo e dinheiro, e cada
# reescrita é uma chance nova de o texto correto mudar sozinho.
# Segundo, com trecho literal dá para CONFERIR antes de aplicar: ou o
# pedaço existe exatamente como veio, ou a alteração é recusada.
# Reescrita completa não tem como ser conferida: só comparando tudo.
FERRAMENTA_ALTERAR = {
    "name": "alterar_texto",
    "description": ("Aplica alterações no contrato que está na tela do "
                    "advogado. Use só quando ele pedir para corrigir, "
                    "ajustar, trocar ou reescrever algo."),
    "input_schema": {
        "type": "object",
        "properties": {
            "alteracoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "procurar": {
                            "type": "string",
                            "description": ("Trecho literal do texto atual, "
                                            "copiado exatamente. Precisa ser "
                                            "único no documento."),
                        },
                        "substituir": {
                            "type": "string",
                            "description": "O texto que entra no lugar.",
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Em uma linha, por que mudou.",
                        },
                    },
                    "required": ["procurar", "substituir", "motivo"],
                },
            },
        },
        "required": ["alteracoes"],
    },
}


FERRAMENTA_CLIENTE = {
    "name": "falar_com_o_cliente",
    "description": ("Manda uma pergunta ao cliente pelos três canais e "
                    "registra a pendência no pedido. Use quando o advogado "
                    "mandar consultar o cliente, pedir ciência dele ou "
                    "buscar um dado que só ele tem."),
    "input_schema": {
        "type": "object",
        "properties": {
            "pergunta": {
                "type": "string",
                "description": ("A mensagem como o cliente vai ler: sem "
                                "jargão, dizendo o que está em jogo e o "
                                "que ele precisa responder."),
            },
            "assunto": {
                "type": "string",
                "description": "O ponto do contrato, em poucas palavras.",
            },
        },
        "required": ["pergunta", "assunto"],
    },
}


def _aplicar(minuta: str, alteracoes: list[dict]) -> tuple[str, list, list]:
    """Aplica as trocas no texto, uma a uma, conferindo cada uma.

    Devolve (texto novo, as que entraram, as que foram recusadas).

    A conferência é literal e sem perdão: o trecho tem de existir
    exatamente como veio, e uma vez só. Casar "mais ou menos" num
    contrato é como assinar "mais ou menos": o trecho parecido pode ser
    outra cláusula, e a troca silenciosa só apareceria depois da
    assinatura."""
    feitas: list[dict] = []
    recusadas: list[dict] = []
    texto = minuta

    for a in alteracoes or []:
        procurar = (a.get("procurar") or "")
        substituir = a.get("substituir") or ""
        if not procurar.strip():
            recusadas.append({**a, "porque": "veio sem o trecho a procurar"})
            continue
        quantas = texto.count(procurar)
        if quantas == 0:
            recusadas.append({**a, "porque": "não achei esse trecho no texto"})
            continue
        if quantas > 1:
            recusadas.append({
                **a, "porque": f"esse trecho aparece {quantas} vezes; "
                               "seria impossível saber qual trocar"})
            continue
        texto = texto.replace(procurar, substituir, 1)
        feitas.append(a)

    return texto, feitas, recusadas


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claude():
    return anthropic.Anthropic(api_key=get_settings().claude_api_key,
                               timeout=TEMPO_LIMITE,
                               max_retries=TENTATIVAS)


def _linha(rotulo: str, valor) -> str:
    return f"{rotulo}: {valor}" if valor not in (None, "", [], {}) else ""


def dossie(pedido_id: str) -> str:
    """Tudo o que o escritório produziu neste pedido, em texto.

    É montado inteiro a cada pergunta, de propósito. Guardar um resumo
    e consultá-lo seria mais barato e responderia sobre o pedido de
    ontem: num pedido que anda de hora em hora, a resposta velha é
    resposta errada."""
    db = get_db()
    r = db.table("pedidos_contrato").select("*, clientes(nome,email)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    cli = p.get("clientes") or {}

    partes: list[str] = ["=== O PEDIDO ==="]
    partes += [x for x in [
        _linha("Protocolo", p.get("protocolo")),
        _linha("Cliente", cli.get("nome")),
        _linha("Tipo de contrato", p.get("tipo")),
        _linha("Serviço digitado pelo cliente", p.get("servico_livre")),
        _linha("Fase atual", p.get("fase")),
        _linha("Valor de tabela", p.get("valor_base")),
        _linha("Desconto aplicado", p.get("desconto_pct")),
        _linha("Valor fechado", p.get("valor")),
        _linha("Prazo de entrega contratado, em horas", p.get("prazo_entrega_horas")),
        _linha("Urgência contratada em", p.get("urgencia_paga_em")),
        _linha("Pago em", p.get("pago_em")),
        _linha("Redigido em", p.get("redigido_em")),
        _linha("Revisado em", p.get("revisado_em")),
        _linha("Ajustado em", p.get("ajustado_em")),
        _linha("Segunda revisão em", p.get("revisado_2_em")),
    ] if x]

    if p.get("dados"):
        partes += ["", "=== O QUE O CLIENTE INFORMOU NA COLETA ===",
                   json.dumps(p["dados"], ensure_ascii=False, indent=1)]
    if (p.get("observacoes") or "").strip():
        partes += ["", "=== O QUE O CLIENTE PEDIU, NAS PALAVRAS DELE ===",
                   p["observacoes"][:4000]]
    if (p.get("clausulas_extras") or "").strip():
        partes += ["", "=== CLÁUSULA PEDIDA PELO CLIENTE ===",
                   p["clausulas_extras"][:4000]]

    rev = p.get("revisao") or {}
    if rev:
        partes += ["", "=== PRIMEIRA REVISÃO ===",
                   _linha("Parecer", rev.get("parecer"))]
        for a in (rev.get("apontamentos") or []):
            if isinstance(a, dict):
                partes.append(
                    f"- [{a.get('gravidade')}] {a.get('clausula')}: "
                    f"{a.get('problema')} | sugestão: {a.get('sugestao')}"
                    + (" | DEPENDE DE AUTORIZAÇÃO DO CLIENTE"
                       if a.get("precisa_autorizacao") else ""))
            else:
                partes.append(f"- {a}")

    rev2 = p.get("revisao_2") or {}
    if rev2:
        partes += ["", "=== SEGUNDA REVISÃO, DEPOIS DO AJUSTE ===",
                   _linha("Parecer", rev2.get("parecer"))]
        for a in (rev2.get("apontamentos") or []):
            partes.append(f"- {a.get('clausula')}: {a.get('problema')}"
                          if isinstance(a, dict) else f"- {a}")

    for a in (p.get("decisoes") or []):
        partes.append(f"DECISÃO DO CLIENTE: {a.get('ponto')} -> "
                      f"{a.get('escolha')} em {a.get('em')}")
    for d in (p.get("duvidas_advogado") or []):
        partes.append(f"PERGUNTA JÁ FEITA AO CLIENTE: {d.get('pergunta')} "
                      f"(em {d.get('em')})")

    pend = [i for i in (p.get("pendencias") or []) if not i.get("atendida")]
    if pend:
        partes += ["", "=== PENDÊNCIAS EM ABERTO COM O CLIENTE ==="]
        partes += [f"- {i.get('rotulo')}"
                   + (" (indispensável)" if i.get("obrigatorio") else "")
                   for i in pend]

    try:
        msgs = db.table("pedidos_mensagens").select("autor,texto,criado_em") \
            .eq("pedido_id", pedido_id).order("criado_em").limit(120) \
            .execute().data or []
    except Exception:
        msgs = []
    if msgs:
        partes += ["", "=== CONVERSA COM O CLIENTE ==="]
        quem = {"CLIENTE": "Cliente", "AGENTE": "Atendimento",
                "ESCRITORIO": "Escritório"}
        partes += [f"[{(m.get('criado_em') or '')[:16]}] "
                   f"{quem.get(m.get('autor'), m.get('autor'))}: "
                   f"{(m.get('texto') or '')[:600]}" for m in msgs]

    try:
        docs = db.table("pedidos_documentos") \
            .select("rotulo,nome,criado_em,transcricao") \
            .eq("pedido_id", pedido_id).limit(60).execute().data or []
    except Exception:
        docs = []
    if docs:
        partes += ["", "=== DOCUMENTOS RECEBIDOS ==="]
        for d in docs:
            partes.append(f"- {d.get('rotulo') or d.get('nome')} "
                          f"({(d.get('criado_em') or '')[:10]})")
            if (d.get("transcricao") or "").strip():
                partes.append(f"  transcrição: {d['transcricao'][:800]}")

    if (p.get("minuta") or "").strip():
        partes += ["", "=== O CONTRATO COMO ESTÁ AGORA ===",
                   p["minuta"][:30000]]

    return "\n".join(partes)


def _consultar_cliente(pedido_id: str, dados: dict, quem: str) -> dict:
    """Manda a pergunta ao cliente e registra a pendência no pedido.

    Reaproveita o caminho que o advogado já usava à mão, o mesmo que
    grava a dúvida em `duvidas_advogado` e manda pelos três canais.
    Ter duas portas para a mesma coisa é ter duas que envelhecem
    diferente: um dia uma passa a registrar e a outra não, e ninguém
    descobre até alguém procurar a pergunta que sumiu."""
    pergunta = (dados.get("pergunta") or "").strip()
    if len(pergunta) < 10:
        return {"enviada": False,
                "porque": "a pergunta ficou curta demais para o cliente "
                          "entender do que se trata"}
    try:
        from . import contratos_online
        contratos_online.perguntar_ao_cliente(
            pedido_id, pergunta, quem=quem or "advogado")
        return {"enviada": True,
                "aviso": "A pergunta saiu pelos três canais. A resposta do "
                         "cliente entra na conversa do pedido."}
    except Exception as e:
        print(f"[mesa] pergunta ao cliente não saiu: {e}")
        return {"enviada": False, "porque": str(e)[:200]}


def perguntar(pedido_id: str, pergunta: str, quem: str = "",
              minuta_na_tela: str = "",
              anteriores: list[dict] | None = None) -> dict:
    """O advogado pergunta, o especialista responde.

    `minuta_na_tela` é o texto que ele está editando AGORA, com as
    alterações que ainda não foram salvas. Sem isso o especialista leria
    a versão do banco e comentaria um parágrafo que já não existe, que é
    o jeito mais rápido de perder a confiança de quem está trabalhando.

    `anteriores` é a conversa até aqui. Perguntar "e a terceira?" só faz
    sentido para quem lembra das duas primeiras."""
    pergunta = (pergunta or "").strip()
    if len(pergunta) < 3:
        raise ValueError("Escreva a pergunta.")

    material = dossie(pedido_id)
    if (minuta_na_tela or "").strip():
        material += ("\n\n=== O TEXTO QUE O ADVOGADO ESTÁ EDITANDO AGORA ===\n"
                     "Esta é a versão da tela, com as alterações dele. Onde "
                     "divergir do contrato acima, vale esta.\n"
                     + minuta_na_tela[:30000])

    # A conversa anterior entra como turnos de verdade, e não espremida
    # dentro do pedido: é assim que o modelo entende quem disse o quê.
    mensagens: list[dict] = []
    for t in (anteriores or [])[-10:]:
        if t.get("pergunta"):
            mensagens.append({"role": "user", "content": t["pergunta"][:2000]})
        if t.get("resposta"):
            mensagens.append({"role": "assistant", "content": t["resposta"][:3000]})
    mensagens.append({"role": "user", "content":
                      f"MATERIAL DO PEDIDO (é tudo o que existe registrado):\n"
                      f"{material}\n\n"
                      f"=== PERGUNTA DO ADVOGADO ===\n{pergunta}"})

    s = get_settings()
    cliente = _claude()
    base = minuta_na_tela or ""
    feitas: list[dict] = []
    recusadas: list[dict] = []
    perguntas: list[dict] = []
    texto = ""

    # Duas voltas, não mais. A primeira é o modelo responder, e talvez
    # pedir alterações; a segunda é ele comentar o que foi aplicado e o
    # que foi recusado. Mais do que isso só serviria para ele insistir
    # num trecho que não existe, gastando o tempo de quem está esperando
    # com a tela aberta.
    for volta in range(2):
        r = cliente.messages.create(
            model=s.claude_model, max_tokens=2500, system=SYSTEM,
            tools=[FERRAMENTA_ALTERAR, FERRAMENTA_CLIENTE],
            messages=mensagens,
        )
        texto = "".join(b.text for b in r.content if b.type == "text").strip()
        usos = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
        if not usos:
            break

        mensagens.append({"role": "assistant", "content": r.content})
        resultados = []
        for u in usos:
            if u.name == "falar_com_o_cliente":
                dados = u.input or {}
                saida = _consultar_cliente(pedido_id, dados, quem)
                if saida.get("enviada"):
                    perguntas.append({"assunto": dados.get("assunto", ""),
                                      "pergunta": dados.get("pergunta", "")})
            else:
                pedidas = (u.input or {}).get("alteracoes") or []
                base, ok, nao = _aplicar(base, pedidas)
                feitas += ok
                recusadas += nao
                saida = {
                    "aplicadas": len(ok),
                    "recusadas": [{"procurar": x.get("procurar", "")[:120],
                                   "porque": x.get("porque")} for x in nao],
                }
            resultados.append({
                "type": "tool_result", "tool_use_id": u.id,
                "content": json.dumps(saida, ensure_ascii=False)})
        mensagens.append({"role": "user", "content": resultados})

    texto = humanizar(texto)
    if not texto:
        texto = ("Não consegui montar a resposta agora. Tente de novo em "
                 "instantes.")

    # O que foi recusado tem de aparecer para o advogado, e não só no
    # log. Alteração que o modelo achou que fez e não fez é pior do que
    # alteração nenhuma: ele aprovaria o documento confiando num ajuste
    # que não está lá.
    if recusadas:
        texto += ("\n\nNão consegui aplicar "
                  + ("1 alteração" if len(recusadas) == 1
                     else f"{len(recusadas)} alterações")
                  + ": " + "; ".join(
                      f"{x.get('porque')}" for x in recusadas)
                  + ". O trecho pode ter mudado depois que eu li. Peça de "
                    "novo que eu tento com o texto atual.")

    resumo_alteracoes = [{"motivo": a.get("motivo", "")} for a in feitas]

    # O QUE FICA GRAVADO É O QUE REAPARECE AMANHÃ
    #
    # O evento é o histórico das tratativas: quem reabrir o documento
    # daqui a uma semana precisa ver não só o que foi perguntado, mas o
    # que foi alterado no texto e o que foi consultado com o cliente.
    # Sem isso, a conversa reaberta vira um monte de perguntas sem
    # consequência, e ninguém sabe se a cláusula mudou porque o
    # especialista mexeu ou porque alguém editou à mão.
    registrar_evento(None, "ADVOGADO_CONSULTOU", {
        "pedido": pedido_id, "quem": quem,
        "pergunta": pergunta[:500], "resposta": texto[:1000],
        "alteracoes": resumo_alteracoes,
        "recusadas": len(recusadas),
        "ao_cliente": perguntas})

    saida = {"pergunta": pergunta, "resposta": texto, "em": _agora(),
             "ao_cliente": perguntas,
             "alteracoes": [{"procurar": a.get("procurar", "")[:200],
                             "substituir": a.get("substituir", "")[:200],
                             "motivo": a.get("motivo", "")} for a in feitas]}
    # O texto novo só volta se alguma coisa mudou de fato. Devolver o
    # mesmo texto faria a tela marcar alterações pendentes à toa e pedir
    # confirmação ao sair de uma página onde nada foi alterado.
    if feitas:
        saida["minuta"] = base
    return saida


def consultas(pedido_id: str, limite: int = 50) -> list[dict]:
    """O que já foi perguntado neste pedido, em ordem.

    Serve a duas coisas: o advogado não repete a pergunta que já fez, e
    quem pegar o pedido depois dele vê o que foi conferido antes de
    aprovar."""
    try:
        linhas = get_db().table("eventos") \
            .select("payload,criado_em").eq("tipo", "ADVOGADO_CONSULTOU") \
            .order("criado_em").limit(300).execute().data or []
    except Exception:
        return []
    saida = []
    for l in linhas:
        pay = l.get("payload") or {}
        if pay.get("pedido") != pedido_id:
            continue
        alt = pay.get("alteracoes")
        # QUEM FALOU FICA DITO, E NÃO DEDUZIDO
        #
        # Reaberto uma semana depois, o fio sem autor vira monólogo: não
        # se sabe se a frase é instrução do advogado ou conclusão do
        # especialista, e as duas têm peso diferente na hora de
        # justificar o que foi assinado.
        quem = (pay.get("quem") or "").strip()
        saida.append({"quem_rotulo": (f"{quem} (advogado)" if quem
                                      and quem.lower() != "advogado"
                                      else "Advogado"),
                      "pergunta": pay.get("pergunta"),
                      "resposta": pay.get("resposta"),
                      "quem": pay.get("quem"),
                      # Versões antigas gravavam só a contagem. Virar
                      # lista aqui evita a tela ter de saber disso.
                      "alteracoes": alt if isinstance(alt, list)
                      else ([{"motivo": "alteração aplicada"}] * int(alt or 0)),
                      "ao_cliente": pay.get("ao_cliente") or [],
                      "em": l.get("criado_em")})
    return saida[-limite:]
