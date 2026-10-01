"""As consultas do especialista — julgados, teses e legislação.

Este módulo é a calibração do agente especialista, e tem uma ideia só
atrás dele: tirar da memória do modelo tudo que é verificável.

Número de acórdão, nome de relator, data de julgamento, enunciado de
súmula, número de artigo — nada disso o especialista produz de cabeça.
Ou vem de uma destas três consultas, que leem o material conferido pelo
escritório, ou o especialista diz ao advogado que precisa confirmar.

É isso que significa "sem margem de erro" aqui: não é o modelo ficar
infalível, é ele nunca afirmar o que não pode provar. A régua escrita
está em `skills/especialista_juridico.md` e entra no SYSTEM dos dois
especialistas (mesa do contrato e mesa da peça).
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.db import get_db

# ── A régua ──────────────────────────────────────────────────────
_ARQUIVO = Path(__file__).parent / "skills" / "especialista_juridico.md"


def regua() -> str:
    """O texto da calibração. Se o arquivo faltar, o agente não fica sem
    régua: cai numa versão mínima que mantém a trava dos números."""
    try:
        return _ARQUIVO.read_text(encoding="utf-8").strip()
    except Exception:
        return (
            "REGRA DE FONTE: só afirme o que está no material do caso ou "
            "no que vier das consultas. Nunca produza de memória número de "
            "artigo, de súmula ou de acórdão, nem relator ou data de "
            "julgamento. Sem a fonte na mão, escreva o que a regra diz e "
            "marque 'confirmar o dispositivo'."
        )


# ── As três ferramentas ──────────────────────────────────────────
FERRAMENTA_JULGADOS = {
    "name": "consultar_julgados",
    "description": (
        "Busca julgados REAIS no banco de precedentes do escritório (e na "
        "API de jurisprudência, quando configurada). Use SEMPRE antes de "
        "citar qualquer acórdão: o que não voltar daqui você não cita. "
        "Devolve tribunal, órgão julgador, tipo, número, relator, data e "
        "ementa — cite exatamente como vier, sem completar nada."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tema": {
                "type": "string",
                "description": (
                    "A matéria, em palavras de pesquisa. Ex.: 'devolução de "
                    "valores em distrato imobiliário', 'nulidade de TOI por "
                    "unilateralidade da perícia'. Seja específico: tema largo "
                    "traz julgado que não serve."
                ),
            },
            "tribunal": {
                "type": "string",
                "description": "Opcional. Ex.: STJ, STF, TJRO, TRF1.",
            },
            "grupo": {
                "type": "string",
                "description": (
                    "Opcional. Grupo de tese do escritório, quando souber "
                    "(ex.: IMOBILIARIO, ENERGIA, BANCARIO, MILITAR)."
                ),
            },
        },
        "required": ["tema"],
    },
}

FERRAMENTA_TESES = {
    "name": "consultar_teses",
    "description": (
        "Lê o banco de teses do escritório: ratio decidendi, argumentos "
        "chave, documentos vitais e diretriz de redação de cada tese, já "
        "conferidos por advogado daqui. Use para fundamentar o pedido e "
        "para saber que prova a tese exige. Mostra também se a tese está "
        "SUPERADA — e tese superada não se usa."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "grupo": {
                "type": "string",
                "description": "Grupo de tese. Ex.: IMOBILIARIO, ENERGIA.",
            },
            "termo": {
                "type": "string",
                "description": (
                    "Palavra do título ou da ratio, para filtrar. Ex.: "
                    "'retenção', 'recuperação de consumo', 'reforma'."
                ),
            },
        },
        "required": [],
    },
}

FERRAMENTA_LEGISLACAO = {
    "name": "consultar_legislacao",
    "description": (
        "Consulta o texto de lei conferido e guardado pelo escritório. Use "
        "SEMPRE antes de citar artigo, inciso ou parágrafo. Se a consulta "
        "devolver que o dispositivo não está no acervo, NÃO cite o número "
        "de cabeça: diga ao advogado o que a regra determina e escreva "
        "'confirmar o dispositivo'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "lei": {
                "type": "string",
                "description": (
                    "A lei, como se fala. Ex.: 'Lei 8.245/91', '8245', "
                    "'CDC', 'CPC', 'Código Civil', 'Lei 6.830/80'."
                ),
            },
            "artigo": {
                "type": "string",
                "description": (
                    "Opcional. O artigo. Ex.: '46', '51', 'art. 927'. Sem "
                    "artigo, devolve o que o acervo tem daquela lei."
                ),
            },
            "termo": {
                "type": "string",
                "description": (
                    "Opcional. Palavra a procurar no texto, quando você não "
                    "sabe o número do artigo. Ex.: 'denúncia vazia'."
                ),
            },
        },
        "required": ["lei"],
    },
}

FERRAMENTAS = [FERRAMENTA_JULGADOS, FERRAMENTA_TESES, FERRAMENTA_LEGISLACAO]
NOMES = {f["name"] for f in FERRAMENTAS}


# ── Execução ─────────────────────────────────────────────────────
def _lista(valor) -> list:
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            v = json.loads(valor)
            return v if isinstance(v, list) else [valor]
        except Exception:
            return [valor]
    return []


def _julgados(dados: dict) -> str:
    from ..integracoes import jurisprudencia_api

    tema = (dados.get("tema") or "").strip()
    if not tema:
        return "Consulta sem tema. Diga a matéria que você quer pesquisar."

    try:
        achado = jurisprudencia_api.buscar(
            tema, dados.get("tribunal") or None, dados.get("grupo") or None,
            limite=6,
        )
    except Exception as e:
        return (
            f"A consulta de julgados falhou ({type(e).__name__}). NÃO cite "
            "acórdão nenhum: avise o advogado que a pesquisa não rodou."
        )

    candidatos = achado.get("candidatos") or []
    if not candidatos:
        aviso = achado.get("aviso")
        extra = f" ({aviso})" if aviso else ""
        return (
            f"Nenhum julgado no acervo sobre “{tema}”{extra}.\n\n"
            "Portanto você NÃO tem precedente para citar neste ponto. Diga "
            "ao advogado que o banco não tem julgado sobre o tema e que é "
            "preciso rodar a pesquisa de precedentes antes de fundamentar "
            "em jurisprudência. Não cite acórdão de memória."
        )

    MINIMO_EMENTA = 400
    linhas = [f"{len(candidatos)} julgado(s) no acervo sobre “{tema}”. "
              "Cite exatamente como está abaixo.\n"]
    for i, p in enumerate(candidatos, 1):
        texto = " ".join((p.get("ementa") or "").split())
        completa = bool(p.get("integral")) or len(texto) >= MINIMO_EMENTA
        cab = [p.get("tribunal") or "", p.get("tipo") or "", p.get("numero") or ""]
        cab = " — ".join([x for x in cab if x])
        extras = []
        if p.get("orgao_julgador"):
            extras.append(p["orgao_julgador"])
        if p.get("relator"):
            extras.append(f"Rel. {p['relator']}")
        if p.get("data_julgamento"):
            extras.append(f"j. {str(p['data_julgamento'])[:10]}")
        if extras:
            cab += f" ({', '.join(extras)})"
        rotulo = ("EMENTA" if completa
                  else "TRECHO DO JULGADO — não é a ementa completa, "
                       "não transcreva como se fosse")
        linhas.append(f"[{i}] {cab}\n{rotulo}: {texto[:1800]}")
        if p.get("url"):
            linhas.append(f"inteiro teor: {p['url']}")
        linhas.append("")
    linhas.append(
        "Depois de citar, faça o paralelo com ESTE caso: o que no registro "
        "corresponde ao que o tribunal considerou decisivo."
    )
    return "\n".join(linhas)


def _teses(dados: dict) -> str:
    grupo = (dados.get("grupo") or "").strip().upper()
    termo = (dados.get("termo") or "").strip()

    try:
        q = get_db().table("teses").select(
            "id,grupo,subtipo,titulo,status,tribunal_origem,ratio_decidendi,"
            "documentos_vitais,argumentos_chave,diretriz_redacao,"
            "jurisprudencia,overruled,tese_substituta,motivo_overruling"
        )
        if grupo:
            q = q.eq("grupo", grupo)
        if termo:
            q = q.or_(f"titulo.ilike.%{termo}%,ratio_decidendi.ilike.%{termo}%")
        achadas = (q.limit(5).execute().data or [])
    except Exception as e:
        return (f"A consulta ao banco de teses falhou ({type(e).__name__}). "
                "Avise o advogado em vez de improvisar a fundamentação.")

    if not achadas:
        alvo = " / ".join([x for x in (grupo, termo) if x]) or "a busca"
        return (f"Nenhuma tese no banco para {alvo}. Fundamente pelo material "
                "do caso e pela lei, sem atribuir ao escritório tese que não "
                "existe no banco.")

    partes = []
    for t in achadas:
        b = [f"TESE {t.get('id')} — {t.get('titulo')}",
             f"grupo: {t.get('grupo')}"
             + (f" / {t.get('subtipo')}" if t.get("subtipo") else ""),
             f"status: {t.get('status')}"]
        if t.get("overruled"):
            b.append("*** SUPERADA — NÃO USE. "
                     + (f"substituída pela tese {t['tese_substituta']}. "
                        if t.get("tese_substituta") else "")
                     + (t.get("motivo_overruling") or ""))
        if t.get("tribunal_origem"):
            b.append(f"origem: {t['tribunal_origem']}")
        if t.get("ratio_decidendi"):
            b.append(f"ratio decidendi: {t['ratio_decidendi']}")
        arg = _lista(t.get("argumentos_chave"))
        if arg:
            b.append("argumentos chave:\n" + "\n".join(
                f"  - {a if isinstance(a, str) else json.dumps(a, ensure_ascii=False)}"
                for a in arg[:8]))
        doc = _lista(t.get("documentos_vitais"))
        if doc:
            b.append("documentos vitais (a prova que a tese exige):\n" + "\n".join(
                f"  - {d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)}"
                for d in doc[:8]))
        if t.get("diretriz_redacao"):
            b.append(f"diretriz de redação: {t['diretriz_redacao']}")
        jur = _lista(t.get("jurisprudencia"))
        if jur:
            b.append("jurisprudência registrada na tese:\n" + "\n".join(
                f"  - {j if isinstance(j, str) else json.dumps(j, ensure_ascii=False)}"
                for j in jur[:6]))
        partes.append("\n".join(b))

    return ("\n\n---\n\n".join(partes)
            + "\n\nConfira os documentos vitais contra o que o caso tem. O que "
              "faltar, aponte ao advogado antes de a peça sair.")


def _legislacao(dados: dict) -> str:
    lei = (dados.get("lei") or "").strip()
    artigo = (dados.get("artigo") or "").strip()
    termo = (dados.get("termo") or "").strip()
    if not lei:
        return "Consulta sem a lei. Diga qual norma você quer."

    # só o que é dígito interessa para casar "Lei 8.245/91" com "8245"
    numeros = "".join(c for c in lei if c.isdigit())[:5]
    artigo_num = "".join(c for c in artigo if c.isdigit())

    try:
        q = get_db().table("legislacao").select(
            "lei,apelido,artigo,texto,fonte,conferido_por,conferido_em")
        alvos = [f"lei.ilike.%{lei}%", f"apelido.ilike.%{lei}%"]
        if numeros:
            alvos.append(f"lei.ilike.%{numeros}%")
        q = q.or_(",".join(alvos))
        if artigo_num:
            q = q.eq("artigo", artigo_num)
        elif termo:
            q = q.ilike("texto", f"%{termo}%")
        achados = (q.order("artigo").limit(12).execute().data or [])
    except Exception as e:
        achados = []
        falha = type(e).__name__
    else:
        falha = None

    if not achados:
        alvo = lei + (f", art. {artigo}" if artigo else "")
        aviso = (f" (a consulta falhou: {falha})" if falha else "")
        return (
            f"{alvo} NÃO está no acervo conferido do escritório{aviso}.\n\n"
            "Então, nesta resposta:\n"
            "- NÃO escreva o número do artigo de cabeça;\n"
            "- diga, em palavras suas, o que a regra determina e por que ela "
            "resolve o ponto;\n"
            "- feche com “confirmar o dispositivo”, para o advogado conferir "
            "antes de assinar.\n\n"
            "Se o dispositivo aparecer no próprio material do caso (guia "
            "técnico do modelo, tese, parecer da revisão, publicação do "
            "tribunal), copie o número como está lá e diga de onde veio."
        )

    partes = [f"{len(achados)} dispositivo(s) no acervo conferido. "
              "Cite exatamente este texto.\n"]
    for a in achados:
        cab = f"{a.get('lei')}" + (f" ({a['apelido']})" if a.get("apelido") else "")
        partes.append(f"{cab} — art. {a.get('artigo')}\n{a.get('texto')}")
        selo = []
        if a.get("fonte"):
            selo.append(a["fonte"])
        if a.get("conferido_por"):
            selo.append(f"conferido por {a['conferido_por']}")
        if selo:
            partes.append("  [" + " · " .join(selo) + "]")
        partes.append("")
    return "\n".join(partes)


_EXECUTORES = {
    "consultar_julgados": _julgados,
    "consultar_teses": _teses,
    "consultar_legislacao": _legislacao,
}


def atender(nome: str, dados: dict) -> str:
    """Roda a consulta e devolve o texto que volta ao modelo.

    Nunca levanta exceção: consulta que quebra tem de virar aviso ao
    advogado, não erro 500 no meio da conversa."""
    f = _EXECUTORES.get(nome)
    if not f:
        return f"Consulta desconhecida: {nome}."
    try:
        return f(dados or {})
    except Exception as e:
        return (f"A consulta {nome} falhou ({type(e).__name__}: {e}). Avise o "
                "advogado e não afirme nada que dependeria dela.")
