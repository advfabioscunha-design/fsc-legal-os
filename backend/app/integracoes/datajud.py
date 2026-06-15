"""
DataJud CNJ — API Pública (https://datajud-wiki.cnj.jus.br/api-publica/).

Fonte oficial e GRATUITA dos metadados processuais do Judiciário (Base
Nacional de Dados do Poder Judiciário). Autenticação por Chave Pública
no header `Authorization: APIKey <chave>`.

IMPORTANTE — limite da fonte: o DataJud entrega METADADOS do processo
(número, classe, assuntos, órgão julgador, movimentos e datas), e NÃO a
íntegra/ementa do acórdão. Por isso o robô usa o DataJud como RADAR
JURIMÉTRICO (o que está sendo julgado, onde e com que resultado) e,
quando identifica julgados relevantes, marca os processos como ALVOS
cuja íntegra deve ser captada para virar tese pelo pipeline de PDFs
(jurisprudencial.processar_bucket).

Endpoint por tribunal:
  https://api-publica.datajud.cnj.jus.br/api_publica_<alias>/_search
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx

from ..core.config import get_settings

BASE = "https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search"

# Aliases dos tribunais de atuação do escritório (configurável via .env).
# Ex.: tjro (TJ Rondônia), trt14 (TRT 14ª Região — RO/AC), tjsc, trt12...
TRIBUNAIS_PADRAO = ["tjro", "trt14"]

# Mapa GRUPO → termos de "assuntos" (TPU/CNJ) buscados no DataJud.
# Termos amplos e em português; ajuste fino conforme o seu nicho.
ASSUNTOS_POR_GRUPO: dict[str, list[str]] = {
    "BANCARIO": [
        "Contratos Bancários", "Cartão de Crédito", "Empréstimo consignado",
        "Cédula de Crédito Bancário", "Financiamento de Produto",
        "Capitalização / Anatocismo", "Seguro", "Alienação Fiduciária",
    ],
    "IMOBILIARIO": [
        "Compromisso de Compra e Venda", "Rescisão do contrato e devolução do dinheiro",
        "Promessa de Compra e Venda", "Incorporação Imobiliária",
        "Compra e Venda", "Distrato",
    ],
    "TRIBUTARIO": [
        "Execução Fiscal", "IPTU", "ICMS", "ISS",
        "Crédito Tributário", "Dívida Ativa",
    ],
    "CONSUMIDOR": [
        "Indenização por Dano Moral", "Práticas Abusivas",
        "Rescisão dos contratos e devolução", "Inclusão Indevida em Cadastro de Inadimplentes",
        "Fornecimento de Energia Elétrica", "Telefonia",
    ],
    "TRABALHISTA": [
        "Verbas Rescisórias", "Horas Extras", "Adicional de Insalubridade",
        "Reconhecimento de Vínculo Empregatício", "FGTS", "Aviso Prévio",
    ],
    "PREVIDENCIARIO": [
        "Aposentadoria por Invalidez", "Auxílio-Doença",
        "Benefício Assistencial (LOAS)", "Aposentadoria por Idade",
    ],
}

# Padrões de movimento (TPU/CNJ) que indicam JULGAMENTO DE MÉRITO.
_RE_PROCEDENTE = re.compile(r"\bproced[êe]ncia\b", re.I)
_RE_IMPROCEDENTE = re.compile(r"\bimproced[êe]ncia\b", re.I)
_RE_JULGAMENTO = re.compile(
    r"julgament|proced[êe]ncia|acórd[ãa]o|provimento|senten[çc]a", re.I
)


def _headers() -> dict:
    s = get_settings()
    return {
        "Authorization": f"APIKey {s.datajud_api_key}",
        "Content-Type": "application/json",
    }


def buscar(alias: str, assunto: str, dias: int = 7, size: int = 100) -> list[dict]:
    """Consulta um tribunal por um termo de assunto, trazendo os processos
    mais recentes. O recorte temporal e o filtro de julgamento são feitos
    em Python a partir dos `movimentos` (mais robusto que query aninhada)."""
    corpo = {
        "size": size,
        "query": {
            "bool": {
                "must": [{"match": {"assuntos.nome": assunto}}]
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}],
    }
    url = BASE.format(alias=alias)
    try:
        r = httpx.post(url, headers=_headers(), json=corpo, timeout=60)
        r.raise_for_status()
    except httpx.HTTPError:
        # tribunais sem índice/alias ou instабilidade → ignora silenciosamente
        return []
    hits = (r.json().get("hits") or {}).get("hits") or []
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    out: list[dict] = []
    for h in hits:
        src = h.get("_source") or {}
        julg = _ultimo_julgamento(src.get("movimentos") or [], limite)
        if not julg:
            continue
        out.append({
            "numero": src.get("numeroProcesso"),
            "classe": (src.get("classe") or {}).get("nome"),
            "orgao": (src.get("orgaoJulgador") or {}).get("nome"),
            "assuntos": [a.get("nome") for a in (src.get("assuntos") or []) if a.get("nome")],
            "tribunal": alias,
            "resultado": julg["resultado"],
            "data_julgamento": julg["data"],
            "movimento": julg["nome"],
        })
    return out


def _ultimo_julgamento(movimentos: list[dict], limite: datetime) -> dict | None:
    """Procura o movimento de julgamento de mérito mais recente dentro da
    janela. Retorna {resultado, nome, data} ou None."""
    melhor = None
    for m in movimentos:
        nome = m.get("nome") or ""
        if not _RE_JULGAMENTO.search(nome):
            continue
        dt = _parse_data(m.get("dataHora"))
        if not dt or dt < limite:
            continue
        if melhor is None or dt > melhor["_dt"]:
            if _RE_PROCEDENTE.search(nome):
                res = "PROCEDENTE"
            elif _RE_IMPROCEDENTE.search(nome):
                res = "IMPROCEDENTE"
            else:
                res = "OUTRO"
            melhor = {"resultado": res, "nome": nome,
                      "data": dt.date().isoformat(), "_dt": dt}
    if melhor:
        melhor.pop("_dt", None)
    return melhor


def _parse_data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    v = valor.replace("Z", "+00:00")
    for fmt in (None,):  # tenta ISO direto
        try:
            dt = datetime.fromisoformat(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            break
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor[:26], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def varrer_grupo(grupo: str, dias: int = 7) -> list[dict]:
    """Roda todos os assuntos do grupo em todos os tribunais configurados,
    deduplicando por número de processo."""
    s = get_settings()
    tribunais = s.datajud_tribunais or TRIBUNAIS_PADRAO
    assuntos = ASSUNTOS_POR_GRUPO.get(grupo, [])
    vistos: dict[str, dict] = {}
    for alias in tribunais:
        for assunto in assuntos:
            for proc in buscar(alias, assunto, dias=dias):
                num = proc.get("numero")
                if num and num not in vistos:
                    vistos[num] = proc
    return list(vistos.values())
