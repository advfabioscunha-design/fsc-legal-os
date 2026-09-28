"""
FONTES DE JURISPRUDÊNCIA — de onde vêm as ementas que entram na petição.

Ponto que precisa ficar claro, porque o comando original partia de outra
premissa: o DataJud do CNJ, que a plataforma já usa no radar, devolve
MOVIMENTAÇÃO PROCESSUAL — classe, assunto, órgão julgador, andamentos. Ele
não devolve ementa nem inteiro teor. Não dá, portanto, para montar o "banco
de julgados locais" com ementas a partir dele.

As ementas vêm de duas fontes, com a mesma interface:

  INTERNO   — o banco do próprio escritório, alimentado pelos acórdãos em
              PDF que sobem para o bucket de jurisprudência. Ementa real,
              com tribunal e número verificáveis. Funciona hoje, sem
              contratar nada.

  API       — provedor de pesquisa de jurisprudência (Escavador ou
              JusBrasil, conforme o plano contratado). O encaixe está
              pronto: basta a chave no .env. Sem chave, devolve lista
              vazia e o fluxo segue apenas com o banco interno.

Toda ementa devolvida carrega `fonte` e, quando há, `url` — é o que permite
conferir a citação antes do protocolo.
"""
from __future__ import annotations

import re
import unicodedata

import httpx

from ..core.config import get_settings
from ..core.db import get_db

# palavras que não ajudam a distinguir um julgado do outro
VAZIAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no",
    "na", "nos", "nas", "um", "uma", "por", "para", "com", "sem", "que",
    "ao", "aos", "à", "às", "pela", "pelo", "sobre", "the", "of",
}


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def _termos(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-z]{4,}", _normalizar(texto))
            if p not in VAZIAS}


def _pontuar(alvo: set[str], prec: dict) -> float:
    """Aderência do precedente ao tema, medida pela sobreposição de termos.
    O tema pesa mais que a ementa: é a matéria, não o texto inteiro."""
    if not alvo:
        return 0.0
    t_tema = _termos(prec.get("tema") or "")
    t_ementa = _termos(prec.get("ementa") or "")
    return (2.0 * len(alvo & t_tema) + len(alvo & t_ementa)) / len(alvo)


# ── Fonte 1: banco do escritório ─────────────────────────────────
def _do_banco(tema: str, tribunal: str | None, grupo: str | None,
              limite: int) -> list[dict]:
    db = get_db()
    try:
        q = db.table("precedentes").select("*")
        if grupo:
            q = q.eq("grupo", grupo)
        linhas = q.limit(400).execute().data or []
    except Exception:
        return []

    alvo = _termos(tema)
    for p in linhas:
        p["_score"] = _pontuar(alvo, p)
        # prioridade absoluta ao tribunal onde a ação será protocolada
        if tribunal and (p.get("tribunal") or "").upper() == tribunal.upper():
            p["_score"] += 1.5
    linhas = [p for p in linhas if p["_score"] > 0]
    linhas.sort(key=lambda p: p["_score"], reverse=True)
    return linhas[:limite]


# ── Fonte 2: API contratada ──────────────────────────────────────
def _do_escavador(tema: str, tribunal: str | None, limite: int) -> list[dict]:
    s = get_settings()
    if not s.escavador_api_token:
        return []
    try:
        r = httpx.get(
            f"{s.escavador_base_url}/api/v2/jurisprudencias/busca",
            headers={"Authorization": f"Bearer {s.escavador_api_token}",
                     "Accept": "application/json"},
            params={"q": tema, "tribunais": tribunal or "", "limit": limite},
            timeout=25,
        )
        r.raise_for_status()
        itens = (r.json() or {}).get("items") or []
    except Exception:
        return []
    return [{
        "tribunal": i.get("tribunal") or tribunal or "",
        "orgao_julgador": i.get("orgao_julgador"),
        "tipo": i.get("tipo"), "numero": i.get("numero_processo") or i.get("numero"),
        "relator": i.get("relator"), "data_julgamento": i.get("data_julgamento"),
        "ementa": i.get("ementa") or "", "tema": tema,
        "fonte": "API", "fonte_ref": str(i.get("id") or ""), "url": i.get("url"),
    } for i in itens if (i.get("ementa") or "").strip()]


class LimiteDaApi(RuntimeError):
    """Quota diária da API de jurisprudência esgotada."""


def _data_br(v: str | None) -> str | None:
    """'09/09/2026' → '2026-09-09'. Devolve None quando não reconhece."""
    if not v:
        return None
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v.strip())
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return v.strip()[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", v.strip()) else None


def _do_jurisprudencias_ai(tema: str, tribunal: str | None, limite: int) -> list[dict]:
    """Jurisprudências.ai — API REST pública, plano gratuito.

    Duas observações que mudam como o resultado é usado:

    1. A busca devolve `excerpt`, que é um RECORTE do acórdão: começa e
       termina no meio de frases. Tem uns 700 caracteres, mas não é a
       ementa completa. Por isso `integral=False` — a petição vai citá-lo
       como trecho do julgado, com o link do inteiro teor, e nunca como
       ementa transcrita.
    2. O plano gratuito é diário (5 buscas). Cada tema da petição consome
       uma busca. Quando o limite estoura, a API responde 429 e nós
       seguimos só com o banco interno, avisando no relatório — melhor do
       que a petição sair sem precedente sem explicação.
    """
    s = get_settings()
    token = getattr(s, "jurisprudencias_api_token", "")
    if not token or not tribunal:
        return []
    slug = re.sub(r"[^a-z0-9]", "", tribunal.lower())
    try:
        r = httpx.get(
            f"https://jurisprudencias.ai/api/v1/courts/{slug}/decisions",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"q": tema, "page": 0},
            timeout=30,
        )
        if r.status_code == 429:
            raise LimiteDaApi("limite diário de buscas da API atingido")
        r.raise_for_status()
        itens = (r.json() or {}).get("data") or []
    except LimiteDaApi:
        raise
    except Exception:
        return []

    return [{
        "tribunal": tribunal.upper(),
        "orgao_julgador": i.get("adjudicating_body"),
        "tipo": i.get("process_type"),
        "numero": i.get("process_number"),
        "relator": i.get("rapporteur"),
        "data_julgamento": _data_br(i.get("trial_date") or i.get("publication_date")),
        "ementa": " ".join((i.get("excerpt") or "").split()),
        "tema": tema,
        "integral": False,          # é recorte, não a ementa inteira
        "fonte": "API", "fonte_ref": i.get("url") or "", "url": i.get("url"),
    } for i in itens[:limite] if (i.get("excerpt") or "").strip()]


def _do_jusbrasil(tema: str, tribunal: str | None, limite: int) -> list[dict]:
    s = get_settings()
    token = getattr(s, "jusbrasil_api_token", "")
    if not token:
        return []
    try:
        r = httpx.get(
            "https://api.jusbrasil.com.br/v1/jurisprudencia/search",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"q": tema, "court": tribunal or "", "size": limite},
            timeout=25,
        )
        r.raise_for_status()
        itens = (r.json() or {}).get("results") or []
    except Exception:
        return []
    return [{
        "tribunal": i.get("court") or tribunal or "",
        "orgao_julgador": i.get("chamber"), "tipo": i.get("kind"),
        "numero": i.get("case_number"), "relator": i.get("reporter"),
        "data_julgamento": i.get("judgment_date"),
        "ementa": i.get("summary") or "", "tema": tema,
        "fonte": "API", "fonte_ref": str(i.get("id") or ""), "url": i.get("url"),
    } for i in itens if (i.get("summary") or "").strip()]


PROVEDORES = {"JURISPRUDENCIAS": _do_jurisprudencias_ai,
              "ESCAVADOR": _do_escavador,
              "JUSBRASIL": _do_jusbrasil}


def buscar(tema: str, tribunal: str | None = None, grupo: str | None = None,
           limite: int = 8) -> dict:
    """Devolve candidatos reais para um tema, do banco interno e da API.

    Nunca gera ementa: o que não existe em alguma das fontes simplesmente
    não aparece aqui — e, mais à frente, faz a tag ser removida da peça."""
    s = get_settings()
    internos = _do_banco(tema, tribunal, grupo, limite)

    externos: list[dict] = []
    aviso = None
    provedor = (getattr(s, "jurisprudencia_provedor", "") or "").upper()
    if provedor in PROVEDORES:
        try:
            externos = PROVEDORES[provedor](tema, tribunal, limite)
        except LimiteDaApi as e:
            aviso = str(e)
        # o que vem da API é guardado, para não pagar duas vezes pela
        # mesma pesquisa e para ficar disponível offline no protocolo
        for e in externos:
            try:
                get_db().table("precedentes").upsert(
                    {k: v for k, v in e.items() if k != "_score"},
                    on_conflict="tribunal,numero",
                ).execute()
            except Exception:
                pass

    vistos, saida = set(), []
    for p in internos + externos:
        chave = ((p.get("tribunal") or "").upper(), (p.get("numero") or "").strip())
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(p)
    return {"candidatos": saida[:limite],
            "internos": len(internos), "externos": len(externos),
            "provedor": provedor or "INTERNO", "aviso": aviso}
