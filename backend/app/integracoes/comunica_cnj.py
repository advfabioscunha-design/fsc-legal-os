"""
Comunica CNJ — API pública e GRATUITA das comunicações processuais
(https://comunicaapi.pje.jus.br/api/v1/comunicacao).

É o Diário de Justiça Eletrônico Nacional aberto por API. Aceita busca
POR OAB (número + UF) e POR NÚMERO DE PROCESSO, e devolve, em cada
comunicação: tribunal, órgão, tipo do ato, classe, texto integral,
link para o documento e a lista de partes com o advogado de cada polo.

Por que esta fonte, e não um monitoramento pago:
  · é do próprio CNJ, sem chave, sem custo e sem limite contratual;
  · traz o texto do ato, não só o metadado — dá para ler a sentença;
  · identifica o advogado destinatário, o que permite achar o cliente.

O que ela NÃO faz, e é honesto registrar:
  · não informa o prazo em dias — quem estima é `agentes.controladoria`,
    e todo prazo estimado nasce marcado para conferência humana;
  · cobre o que foi publicado no DJEN. Intimação em portal (sem
    publicação) não aparece aqui — para essas, o Escavador segue valendo.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from html import unescape

import httpx

BASE = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

# O CNJ responde "sistema muito ocupado" com frequência; é instabilidade
# normal da fonte, não erro de chamada. Tentamos de novo antes de desistir.
TENTATIVAS = 3


class FonteOcupada(RuntimeError):
    """O CNJ recusou a consulta por carga. Vale tentar de novo depois."""


def _pedir(params: dict) -> dict:
    ultimo = ""
    for tentativa in range(TENTATIVAS):
        try:
            r = httpx.get(BASE, params=params, timeout=60)
            r.raise_for_status()
            dados = r.json()
        except (httpx.HTTPError, ValueError) as e:
            ultimo = str(e)
            continue
        if (dados.get("status") or "").lower() == "success":
            return dados
        ultimo = dados.get("message") or "resposta sem sucesso"
    raise FonteOcupada(f"Comunica CNJ indisponível: {ultimo}")


# ── Leitura do texto ────────────────────────────────────────────
_TAG = re.compile(r"<[^>]+>")
_ESPACO = re.compile(r"[ \t\xa0]+")
_LINHAS = re.compile(r"\n{3,}")


def texto_limpo(html: str | None) -> str:
    """O campo `texto` vem como HTML de editor (às vezes um documento
    inteiro, com <style> e seções). Aqui fica só o que se lê."""
    if not html:
        return ""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>|</tr>|</section>|</div>", "\n", t, flags=re.I)
    t = _TAG.sub(" ", t)
    t = unescape(t)
    t = _ESPACO.sub(" ", t)
    t = re.sub(r" +([,.;:)])", r"\1", t)      # o strip de tags deixa espaço antes da vírgula
    t = re.sub(r"\( +", "(", t)
    t = "\n".join(linha.strip() for linha in t.split("\n"))
    return _LINHAS.sub("\n\n", t).strip()


def _nome_do_advogado(item: dict) -> str:
    for adv in item.get("destinatarioadvogados") or []:
        nome = ((adv or {}).get("advogado") or {}).get("nome")
        if nome:
            return nome
    return ""


def cliente_provavel(item: dict, texto: str) -> str | None:
    """Qual das partes é o nosso cliente.

    No corpo da publicação o advogado aparece imediatamente depois da
    parte que ele representa ("AGRAVANTE: X / ADVOGADO: FABIO..."). Então
    a parte mais próxima ANTES do nome do advogado é o cliente. Se o
    texto não permitir essa leitura, devolve None em vez de adivinhar —
    um cliente errado no cadastro custa mais do que um campo vazio.
    """
    advogado = _nome_do_advogado(item)
    partes = [(p or {}).get("nome") for p in (item.get("destinatarios") or [])]
    partes = [p for p in partes if p]
    if not advogado or not partes:
        return None

    alvo = texto.upper().find(advogado.upper())
    if alvo < 0:
        return None
    melhor, melhor_pos = None, -1
    for nome in partes:
        pos = texto.upper().rfind(nome.upper(), 0, alvo)
        if pos > melhor_pos:
            melhor, melhor_pos = nome, pos
    return melhor


def _normalizar(item: dict) -> dict:
    texto = texto_limpo(item.get("texto"))
    return {
        "fonte": "COMUNICA_CNJ",
        "evento_id": f"cnj-{item.get('id')}",
        "numero_processo": (item.get("numeroprocessocommascara")
                            or item.get("numero_processo") or "").strip() or None,
        "numero_sem_mascara": (item.get("numero_processo") or "").strip() or None,
        "tribunal": item.get("siglaTribunal"),
        "orgao": item.get("nomeOrgao"),
        "tipo": item.get("tipoComunicacao"),
        "tipo_documento": item.get("tipoDocumento"),
        "classe": item.get("nomeClasse"),
        "data": item.get("data_disponibilizacao"),
        "link": item.get("link"),
        "texto": texto,
        "partes": [{"nome": (p or {}).get("nome"), "polo": (p or {}).get("polo")}
                   for p in (item.get("destinatarios") or []) if (p or {}).get("nome")],
        "advogado": _nome_do_advogado(item),
        "cliente_provavel": cliente_provavel(item, texto),
    }


# ── Buscas ──────────────────────────────────────────────────────
def por_oab(numero: str, uf: str, dias: int = 30,
            paginas: int = 10, por_pagina: int = 100) -> list[dict]:
    """Todas as comunicações da OAB nos últimos `dias`, mais recentes
    primeiro. Pagina até `paginas` para não varrer anos por acidente."""
    inicio = (date.today() - timedelta(days=max(dias, 1))).isoformat()
    fim = date.today().isoformat()
    saida: list[dict] = []
    for pagina in range(1, paginas + 1):
        dados = _pedir({
            "numeroOab": re.sub(r"\D", "", numero),
            "ufOab": uf.upper(),
            "dataDisponibilizacaoInicio": inicio,
            "dataDisponibilizacaoFim": fim,
            "itensPorPagina": por_pagina,
            "pagina": pagina,
        })
        itens = dados.get("items") or []
        saida.extend(_normalizar(i) for i in itens)
        if len(itens) < por_pagina:
            break
    return saida


def por_processo(numero: str, por_pagina: int = 100) -> list[dict]:
    """Histórico de publicações de um processo, do mais antigo ao mais
    novo — é o que permite montar a linha do tempo de um processo que
    está sendo cadastrado agora."""
    dados = _pedir({
        "numeroProcesso": re.sub(r"\D", "", numero),
        "itensPorPagina": por_pagina, "pagina": 1,
    })
    itens = [_normalizar(i) for i in dados.get("items") or []]
    return sorted(itens, key=lambda i: i.get("data") or "")


def agrupar_por_processo(comunicacoes: list[dict]) -> dict[str, list[dict]]:
    """Junta as comunicações por processo, cada lista em ordem
    cronológica — um processo por card na tela do judicial."""
    mapa: dict[str, list[dict]] = {}
    for c in comunicacoes:
        num = c.get("numero_processo")
        if num:
            mapa.setdefault(num, []).append(c)
    for lista in mapa.values():
        lista.sort(key=lambda i: i.get("data") or "")
    return mapa
