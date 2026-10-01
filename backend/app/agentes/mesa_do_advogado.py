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

SYSTEM = """Você é o assistente de conferência do escritório FC Advocacia,
falando com o ADVOGADO responsável, não com o cliente.

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

Se a pergunta for de opinião jurídica e não de fato ("isso é válido?"),
você pode apontar o que a revisão registrou sobre o ponto e o
fundamento citado, mas a conclusão é dele. Não dê parecer.

Nada de travessão, asterisco ou marcação. Texto corrido."""


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


def perguntar(pedido_id: str, pergunta: str, quem: str = "") -> dict:
    """O advogado pergunta, o registro responde."""
    pergunta = (pergunta or "").strip()
    if len(pergunta) < 3:
        raise ValueError("Escreva a pergunta.")

    material = dossie(pedido_id)
    s = get_settings()
    r = _claude().messages.create(
        model=s.claude_model, max_tokens=1200, system=SYSTEM,
        messages=[{"role": "user", "content":
                   f"MATERIAL DO PEDIDO (é tudo o que existe registrado):\n"
                   f"{material}\n\n"
                   f"=== PERGUNTA DO ADVOGADO ===\n{pergunta}"}],
    )
    texto = humanizar("".join(b.text for b in r.content
                              if b.type == "text").strip())
    if not texto:
        texto = ("Não consegui montar a resposta agora. Tente de novo em "
                 "instantes.")

    # Fica registrado. A conferência final é ato do advogado, e o que
    # ele consultou antes de aprovar faz parte do que foi conferido.
    registrar_evento(None, "ADVOGADO_CONSULTOU", {
        "pedido": pedido_id, "quem": quem,
        "pergunta": pergunta[:500], "resposta": texto[:1000]})
    return {"pergunta": pergunta, "resposta": texto, "em": _agora()}


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
        saida.append({"pergunta": pay.get("pergunta"),
                      "resposta": pay.get("resposta"),
                      "quem": pay.get("quem"),
                      "em": l.get("criado_em")})
    return saida[-limite:]
