"""
AGENTE DE PRECEDENTES — troca as tags da minuta por julgado real do tribunal.

A peça sai do redator com marcações no lugar da jurisprudência:

    [INSERIR_JURISPRUDENCIA_TEMA: "tarifa de cadastro abusiva"]

Este agente varre essas marcações e, para cada uma, escolhe de um a dois
julgados REAIS do banco, escreve a frase que apresenta o entendimento do
tribunal, insere a ementa em citação e, logo abaixo, faz a subsunção — o
paralelo entre o que o tribunal decidiu e o que aconteceu com o cliente.

A TRAVA ANTI-ALUCINAÇÃO NÃO É UMA INSTRUÇÃO, É ARQUITETURA
Pedir ao modelo "não invente ementa" ajuda, mas não garante. Aqui o modelo
nunca escreve a ementa: ele recebe uma lista numerada de candidatos reais e
só pode devolver o ÍNDICE de quais usar. O texto da ementa, o número do
processo, o relator e a data são copiados do banco pelo código, não pelo
modelo. O que o modelo escreve é só o que é dele: a frase de introdução e o
parágrafo de subsunção. Se o banco não tiver julgado aderente, a tag é
removida — a peça sai sem aquela citação, e o relatório diz por quê.

Prioridade do tribunal: julgado do foro onde a ação será protocolada vale
mais que qualquer outro. É o que demonstra ao magistrado que a corte que vai
julgar o recurso já decidiu assim.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone as _tz

import anthropic

from ..core.ia import TEMPO_LIMITE, TENTATIVAS

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..integracoes import jurisprudencia_api

# aceita aspas retas, curvas ou nenhuma, e variações de espaço
TAG = re.compile(
    r"\[\s*INSERIR_JURISPRUDENCIA_TEMA\s*:\s*[\"“']?(.+?)[\"”']?\s*\]",
    re.I | re.S,
)


def varrer_tags(markdown: str) -> list[str]:
    """Temas pedidos na minuta, na ordem em que aparecem, sem repetir."""
    vistos, temas = set(), []
    for m in TAG.finditer(markdown or ""):
        tema = " ".join(m.group(1).split())
        if tema.lower() not in vistos:
            vistos.add(tema.lower())
            temas.append(tema)
    return temas


# ── O comando do agente ──────────────────────────────────────────
INSTRUCAO = """Você é o Agente de Precedentes da FC Advocacia, escritório do
Dr. Fábio Silva Cunha (OAB/RO 10.849), que atua em Rondônia (TJRO) e Santa
Catarina (TJSC).

Recebe UM tema de uma petição inicial já redigida e uma LISTA NUMERADA de
julgados REAIS, extraídos do banco do escritório. Sua tarefa é escolher
quais julgados sustentam aquele tema e escrever o texto que os apresenta.

VOCÊ NÃO ESCREVE EMENTA. Você não redige, não resume e não completa o texto
de nenhum julgado, nem número de processo, relator ou data — tudo isso é
copiado do banco pelo sistema. Você devolve apenas os ÍNDICES escolhidos e o
texto que é seu.

COMO ESCOLHER
- Aderência estrita ao tema. Julgado que trata de matéria próxima, mas não
  da mesma questão, NÃO serve: é pior do que não citar nada, porque expõe a
  peça a uma resposta fácil da parte contrária.
- Prioridade absoluta ao tribunal onde a ação será protocolada. Um acórdão
  do próprio tribunal vale mais do que dez de outro.
- No máximo dois julgados. Um bom precedente convence; uma lista cansa.
- Não havendo julgado estritamente aderente, devolva a lista vazia. Isso é
  uma resposta correta e esperada, não uma falha.

O QUE VOCÊ ESCREVE
1. INTRODUÇÃO (1 a 2 frases): apresenta o entendimento do tribunal, deixando
   claro ao magistrado que a matéria já foi enfrentada e decidida naquela
   corte. Ajuste o tom ao que o banco mostra: se houver vários julgados no
   mesmo sentido, pode afirmar entendimento consolidado; havendo um só, diga
   que o tribunal já reconheceu — nunca chame de pacífico o que não está
   demonstrado.
2. DESTAQUE: indique o trecho EXATO do julgado escolhido que resolve a lide,
   copiado literalmente (uma frase, no máximo duas). O sistema aplica o
   negrito. Se copiar errado, o destaque não é aplicado.

ATENÇÃO AO TIPO DE REGISTRO: alguns itens da lista vêm marcados como
"TRECHO DO JULGADO (não é a ementa completa)". Nesses, a introdução que você
escrever NÃO pode dizer que a ementa está transcrita nem sugerir que aquele
é o texto integral do acórdão — o sistema os apresenta como referência ao
que foi decidido, com aspas apenas no que é literal.
3. SUBSUNÇÃO (1 parágrafo): o paralelo entre o julgado e o caso concreto —
   por que o que o tribunal decidiu se aplica exatamente a este autor, com
   os fatos deste processo. É o parágrafo mais importante: sem ele a ementa
   é enfeite. Use os fatos do caso que foram fornecidos; não invente fato.

LINGUAGEM: português jurídico brasileiro, sóbrio, sem adjetivação excessiva.
Trate o julgador por "Vossa Excelência" apenas se o texto da peça já o fizer.
Nunca prometa resultado."""

FERRAMENTA = {
    "name": "precedentes_escolhidos",
    "description": "Registra os julgados escolhidos e o texto que os acompanha.",
    "input_schema": {
        "type": "object",
        "properties": {
            "indices": {
                "type": "array",
                "description": "Índices (números) dos julgados escolhidos na lista "
                               "fornecida. Vazio quando nenhum for aderente.",
                "items": {"type": "integer"},
            },
            "introducao": {
                "type": "string",
                "description": "1 a 2 frases apresentando o entendimento do tribunal.",
            },
            "destaques": {
                "type": "array",
                "description": "Para cada julgado escolhido, na mesma ordem, o trecho "
                               "LITERAL da ementa que resolve a lide.",
                "items": {"type": "string"},
            },
            "subsuncao": {
                "type": "string",
                "description": "Parágrafo ligando o julgado aos fatos do caso concreto.",
            },
            "motivo_descarte": {
                "type": "string",
                "description": "Quando indices vier vazio, por que nenhum julgado serve.",
            },
            "local_contraria": {
                "type": "boolean",
                "description": "true quando os julgados encontrados no tribunal do "
                               "protocolo decidem CONTRA a tese do cliente. É a "
                               "informação mais importante que você pode devolver: "
                               "muda a estratégia da ação, não só a citação.",
            },
        },
        "required": ["indices"],
    },
}


# ── Montagem do bloco em Markdown ────────────────────────────────
def _cabecalho(p: dict) -> str:
    partes = [p.get("tribunal") or "", p.get("tipo") or "", p.get("numero") or ""]
    linha = " — ".join([x for x in partes if x])
    extras = []
    if p.get("orgao_julgador"):
        extras.append(p["orgao_julgador"])
    if p.get("relator"):
        extras.append(f"Rel. {p['relator']}")
    if p.get("data_julgamento"):
        extras.append(f"j. {str(p['data_julgamento'])[:10]}")
    return linha + (f" ({', '.join(extras)})" if extras else "")


MINIMO_EMENTA = 400        # abaixo disso não é ementa, é trecho


def _citacao(p: dict, destaque: str | None) -> str:
    """Transcreve a ementa em bloco de citação — quando é ementa mesmo.

    O banco guarda dois tipos de registro: ementas completas, vindas dos
    acórdãos em PDF ou da API, e TRECHOS curtos extraídos na leitura das
    decisões. Transcrever um trecho de duas linhas como se fosse a ementa
    do acórdão é afirmação falsa, e a parte contrária confere o inteiro
    teor. Por isso o trecho entra como referência ao que foi decidido, com
    aspas no que é citação literal, e não em bloco de ementa.

    O negrito é aplicado pelo código sobre o texto do banco: se o trecho
    indicado não existir literalmente, sai sem destaque — o texto do
    julgado nunca é alterado para caber no destaque."""
    texto = " ".join((p.get("ementa") or "").split())
    integral = bool(p.get("integral")) or len(texto) >= MINIMO_EMENTA

    if destaque:
        limpo = " ".join(destaque.split())
        if limpo and limpo in texto:
            texto = texto.replace(limpo, f"**{limpo}**", 1)

    if integral:
        linhas = [f"> {_cabecalho(p)}", ">", f"> {texto}"]
        if p.get("url"):
            linhas += [">", f"> [inteiro teor]({p['url']})"]
        return "\n".join(linhas)

    # referência: diz o que o tribunal decidiu, sem simular transcrição
    ref = f"({_cabecalho(p)})"
    if p.get("url"):
        ref = f"([inteiro teor]({p['url']}) — {_cabecalho(p)})"
    return f"Nesse julgado, o tribunal consignou que “{texto}” {ref}."


def _bloco(escolhidos: list[dict], destaques: list[str],
           introducao: str, subsuncao: str) -> str:
    partes = [introducao.strip()] if introducao.strip() else []
    for i, p in enumerate(escolhidos):
        partes.append(_citacao(p, destaques[i] if i < len(destaques) else None))
    if subsuncao.strip():
        partes.append(subsuncao.strip())
    return "\n\n".join(partes)


# ── O trabalho por tema ──────────────────────────────────────────
def _resolver_tema(tema: str, contexto: str, tribunal: str | None,
                   grupo: str | None) -> dict:
    s = get_settings()
    achado = jurisprudencia_api.buscar(tema, tribunal, grupo, limite=8)
    candidatos = achado["candidatos"]
    if not candidatos:
        motivo = "nenhum julgado no banco trata desta matéria"
        if achado.get("aviso"):
            # quota da API estourada é coisa diferente de "não existe julgado":
            # o advogado precisa saber para rodar de novo amanhã
            motivo = f"{achado['aviso']} — pesquisado apenas no banco interno"
        return {"tema": tema, "usado": False, "provedor": achado["provedor"],
                "aviso": achado.get("aviso"),
                "motivo": motivo, "bloco": "", "julgados": []}

    def _rotulo(p):
        texto = " ".join((p.get("ementa") or "").split())
        tipo = ("EMENTA" if (p.get("integral") or len(texto) >= MINIMO_EMENTA)
                else "TRECHO DO JULGADO (não é a ementa completa)")
        return (f"[{candidatos.index(p)}] {_cabecalho(p)}\n"
                f"TEMA: {p.get('tema') or '—'}\n{tipo}: {texto[:2500]}")

    lista = "\n\n".join(_rotulo(p) for p in candidatos)

    cliente = anthropic.Anthropic(api_key=s.claude_api_key,
                               timeout=TEMPO_LIMITE,
                               max_retries=TENTATIVAS)
    r = cliente.messages.create(
        model=s.claude_model, max_tokens=2500, system=INSTRUCAO,
        tools=[FERRAMENTA],
        tool_choice={"type": "tool", "name": "precedentes_escolhidos"},
        messages=[{"role": "user", "content":
                   f"TRIBUNAL DO PROTOCOLO: {tribunal or 'não informado'}\n\n"
                   f"TEMA A SUSTENTAR: {tema}\n\n"
                   f"FATOS DO CASO CONCRETO:\n{contexto[:6000]}\n\n"
                   f"JULGADOS DISPONÍVEIS:\n{lista}"}],
    )
    dados = {}
    for bloco in r.content:
        if bloco.type == "tool_use":
            dados = bloco.input or {}
            break

    indices = [i for i in (dados.get("indices") or [])
               if isinstance(i, int) and 0 <= i < len(candidatos)][:2]
    if not indices:
        return {"tema": tema, "usado": False, "provedor": achado["provedor"],
                "aviso": achado.get("aviso"),
                "local_contraria": bool(dados.get("local_contraria")),
                "motivo": dados.get("motivo_descarte")
                          or "nenhum julgado com aderência estrita ao tema",
                "bloco": "", "julgados": []}

    escolhidos = [candidatos[i] for i in indices]
    texto = _bloco(escolhidos, dados.get("destaques") or [],
                   dados.get("introducao") or "",
                   dados.get("subsuncao") or "")
    return {
        "tema": tema, "usado": True, "provedor": achado["provedor"],
        "aviso": achado.get("aviso"), "bloco": texto,
        "julgados": [{"tribunal": p.get("tribunal"), "numero": p.get("numero"),
                      "fonte": p.get("fonte"), "url": p.get("url")}
                     for p in escolhidos],
        "do_tribunal_do_protocolo": bool(tribunal) and all(
            (p.get("tribunal") or "").upper() == (tribunal or "").upper()
            for p in escolhidos),
    }


# ── Ponto de entrada ─────────────────────────────────────────────
def injetar(peticao_id: str) -> dict:
    db = get_db()
    pet = db.table("peticoes").select("*").eq("id", peticao_id) \
            .single().execute().data
    if not pet:
        raise ValueError("Petição não encontrada.")

    caso = db.table("casos").select("grupo,titulo,relato_inicial,clientes(nome)") \
             .eq("id", pet["caso_id"]).single().execute().data or {}
    contexto = (f"Caso: {caso.get('titulo') or ''}\n"
                f"Cliente: {(caso.get('clientes') or {}).get('nome') or ''}\n"
                f"Relato: {caso.get('relato_inicial') or ''}")

    base = pet["markdown_base"]
    temas = varrer_tags(base)
    if not temas:
        return {"ok": False,
                "mensagem": "Nenhuma tag [INSERIR_JURISPRUDENCIA_TEMA: \"…\"] "
                            "encontrada na minuta."}

    resultados = {}
    for tema in temas:
        try:
            resultados[tema.lower()] = _resolver_tema(
                tema, contexto, pet.get("tribunal"), caso.get("grupo"))
        except Exception as e:
            resultados[tema.lower()] = {
                "tema": tema, "usado": False, "bloco": "", "julgados": [],
                "motivo": f"falha ao pesquisar: {str(e)[:160]}"}

    def trocar(m):
        tema = " ".join(m.group(1).split()).lower()
        r = resultados.get(tema) or {}
        # tag sem julgado aderente sai do texto: nunca fica marcação na peça
        return r.get("bloco") or ""

    final = TAG.sub(trocar, base)
    # não deixa buraco de linhas em branco onde a tag foi removida
    final = re.sub(r"\n{3,}", "\n\n", final).strip() + "\n"

    usados = [r for r in resultados.values() if r.get("usado")]
    avisos = sorted({r.get("aviso") for r in resultados.values() if r.get("aviso")})
    contrarios = [r["tema"] for r in resultados.values() if r.get("local_contraria")]
    relatorio = {
        "avisos": avisos,
        # tese em que o tribunal do protocolo decide contra: é alerta de
        # estratégia, não de formatação
        "tribunal_contrario": contrarios,
        "tags": len(temas),
        "preenchidas": len(usados),
        "removidas": len(temas) - len(usados),
        "detalhe": list(resultados.values()),
        "rodado_em": datetime.now(_tz.utc).isoformat(),
    }

    db.table("peticoes").update({
        "markdown_final": final, "relatorio": relatorio,
        "status": "COM_PRECEDENTES",
        "atualizado_em": datetime.now(_tz.utc).isoformat(),
    }).eq("id", peticao_id).execute()

    registrar_evento(pet["caso_id"], "PRECEDENTES_INJETADOS",
                     {"peticao_id": peticao_id, "tags": len(temas),
                      "preenchidas": len(usados)})
    return {"ok": True, "markdown": final, "relatorio": relatorio}


# ── Alimentar o banco a partir das teses ─────────────────────────
def sincronizar_do_banco_de_teses() -> dict:
    """Achata as ementas guardadas em `teses.jurisprudencia` na tabela de
    precedentes, que é onde a busca por tema acontece. Pode rodar quantas
    vezes for preciso: o índice único evita duplicar."""
    db = get_db()
    teses = db.table("teses").select(
        "id,grupo,subtipo,titulo,tribunal_origem,jurisprudencia").execute().data or []
    novos = 0
    for t in teses:
        for j in (t.get("jurisprudencia") or []):
            ementa = " ".join((j.get("ementa") or "").split())
            if len(ementa) < 40:
                continue          # fragmento curto demais para citar
            linha = {
                "integral": len(ementa) >= MINIMO_EMENTA,
                "tribunal": (j.get("tribunal") or t.get("tribunal_origem")
                             or "").upper() or "NAO_INFORMADO",
                "tipo": j.get("tipo"), "numero": j.get("numero"),
                "ementa": ementa,
                "tema": j.get("aplicacao_ao_caso") or t.get("titulo"),
                "grupo": t.get("grupo"), "subtipo": t.get("subtipo"),
                "fonte": "BANCO_TESES", "fonte_ref": t["id"],
            }
            try:
                if linha["numero"]:
                    db.table("precedentes").upsert(
                        linha, on_conflict="tribunal,numero").execute()
                else:
                    ja = db.table("precedentes").select("id") \
                           .eq("fonte_ref", t["id"]).ilike("ementa", ementa[:60] + "%") \
                           .limit(1).execute().data
                    if ja:
                        continue
                    db.table("precedentes").insert(linha).execute()
                novos += 1
            except Exception:
                pass
    total = len(db.table("precedentes").select("id").execute().data or [])
    return {"ok": True, "processados": novos, "total_no_banco": total}
