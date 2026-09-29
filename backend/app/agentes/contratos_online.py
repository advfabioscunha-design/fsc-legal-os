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

FASES = [
    "COLETA", "CIENCIA", "PAGAMENTO", "REDACAO", "REVISAO_IA", "AJUSTE",
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
        f"CIÊNCIA E DECISÃO — {t['nome']}",
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


def redigir(pedido_id: str) -> dict:
    """Escreve a primeira versão a partir dos dados coletados."""
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

    db.table("pedidos_contrato").update({
        "minuta": texto, "fase": "REVISAO_IA", "redigido_em": _agora(),
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_REDIGIDO",
                     {"pedido": pedido_id, "tipo": p["tipo"], "caracteres": len(texto)})
    return {"ok": True, "fase": "REVISAO_IA", "caracteres": len(texto)}


def revisar(pedido_id: str) -> dict:
    """O revisor lê a íntegra e anota. Só depois disso o ajuste abre."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    if not p.get("minuta"):
        raise ValueError("Não há minuta para revisar — redija primeiro.")
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

    db.table("pedidos_contrato").update({
        "revisao": dados, "fase": "AJUSTE", "revisado_em": _agora(),
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_REVISADO",
                     {"pedido": pedido_id, "apontamentos": len(apontamentos)})
    return {"ok": True, "fase": "AJUSTE", "apontamentos": apontamentos,
            "parecer": dados.get("parecer", "")}


def ajustar(pedido_id: str) -> dict:
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
                "aviso": "A revisão não apontou correções; segue para o advogado."}

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

    db.table("pedidos_contrato").update({
        "minuta": texto, "minuta_anterior": p["minuta"],
        "fase": "REVISAO_ADV", "ajustado_em": _agora(), "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_AJUSTADO",
                     {"pedido": pedido_id, "apontamentos": len(apontamentos)})
    return {"ok": True, "fase": "REVISAO_ADV", "aplicados": len(apontamentos)}


def liberar_para_cliente(pedido_id: str, quem: str = "") -> dict:
    """Revisão humana aprovada. É o único caminho até o cliente."""
    db = get_db()
    db.table("pedidos_contrato").update({
        "fase": "APROVACAO", "aprovado_advogado_em": _agora(),
        "aprovado_advogado_por": quem or None, "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_LIBERADO", {"pedido": pedido_id, "por": quem})
    return {"ok": True, "fase": "APROVACAO"}


def pedir_alteracao(pedido_id: str, texto: str) -> dict:
    """O cliente leu e quer mudança. Volta para ajuste, com o pedido
    dele junto — e a fila do escritório mostra que voltou."""
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
