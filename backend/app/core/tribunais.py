"""
Os tribunais onde o escritório atua — e por qual canal se chega a cada um.

O QUE PRECISA FICAR CLARO ANTES DE CONFIGURAR QUALQUER COISA
------------------------------------------------------------
"e-SAJ", "eproc", "PJe", "Projudi" e "SEEU" são SISTEMAS, não fontes de
dados. Não se consulta o e-SAJ e o eproc separadamente para saber das
publicações: quem publica é o tribunal, e desde 2025 a publicação de
todos eles sai num lugar só, o Diário de Justiça Eletrônico Nacional
(DJEN). Por isso a busca por OAB já traz TRF4, TJSP, TRT14 e TJRO na
mesma consulta, mesmo rodando cada um em software diferente.

São dois canais, com papéis distintos:

  DJEN / Comunica CNJ  — o que foi PUBLICADO (intimações, sentenças,
      despachos, pautas). Nacional, gratuito, busca por OAB ou por
      número. É o canal que abastece a esteira e os prazos.

  DataJud CNJ          — os METADADOS do processo (classe, assunto,
      órgão julgador, movimentos e datas). Gratuito, por tribunal,
      busca por número. É o canal que confirma se o processo está vivo
      e enriquece o cadastro. NÃO traz texto de decisão.

O que NENHUM dos dois cobre, e é honesto dizer:
  · intimação feita só no portal do tribunal, sem publicação no Diário
    (o PJe chama de "intimação eletrônica"): ela só aparece entrando no
    sistema com o certificado do advogado;
  · processos em segredo de justiça;
  · o SEEU (execução penal), que não está no DataJud e publica pouco no
    DJEN — esses precisam de cadastro manual e acompanhamento no portal.
"""
from __future__ import annotations

# alias DataJud: é o pedaço que vai na URL api_publica_<alias>
TRIBUNAIS: dict[str, dict] = {
    # ── Justiça Estadual ─────────────────────────────────────────
    "TJRO": {"nome": "TJ Rondônia", "sistemas": ["PJe"], "datajud": "tjro",
             "graus": "1º e 2º", "uf": "RO"},
    "TJSC": {"nome": "TJ Santa Catarina", "sistemas": ["eproc"], "datajud": "tjsc",
             "graus": "1º e 2º", "uf": "SC"},
    "TJRS": {"nome": "TJ Rio Grande do Sul", "sistemas": ["eproc"], "datajud": "tjrs",
             "graus": "1º e 2º", "uf": "RS"},
    "TJPR": {"nome": "TJ Paraná", "sistemas": ["Projudi", "PJe"], "datajud": "tjpr",
             "graus": "1º e 2º", "uf": "PR"},
    "TJMT": {"nome": "TJ Mato Grosso", "sistemas": ["PJe"], "datajud": "tjmt",
             "graus": "1º e 2º", "uf": "MT"},
    "TJBA": {"nome": "TJ Bahia", "sistemas": ["PJe", "Projudi"], "datajud": "tjba",
             "graus": "1º e 2º", "uf": "BA"},
    "TJSP": {"nome": "TJ São Paulo", "sistemas": ["e-SAJ"], "datajud": "tjsp",
             "graus": "1º e 2º", "uf": "SP"},

    # ── Justiça do Trabalho ──────────────────────────────────────
    "TRT12": {"nome": "TRT 12ª Região (SC)", "sistemas": ["PJe"], "datajud": "trt12",
              "graus": "1º e 2º", "uf": "SC"},
    "TRT14": {"nome": "TRT 14ª Região (RO/AC)", "sistemas": ["PJe"], "datajud": "trt14",
              "graus": "1º e 2º", "uf": "RO"},

    # ── Justiça Federal ──────────────────────────────────────────
    "TRF1": {"nome": "TRF 1ª Região", "sistemas": ["PJe"], "datajud": "trf1",
             "graus": "1º e 2º", "uf": "—"},
    "TRF4": {"nome": "TRF 4ª Região", "sistemas": ["eproc"], "datajud": "trf4",
             "graus": "1º e 2º", "uf": "—"},

    # ── Execução penal ───────────────────────────────────────────
    "SEEU": {"nome": "SEEU — execução penal", "sistemas": ["SEEU"], "datajud": None,
             "graus": "execução", "uf": "—",
             "observacao": "Fora do DataJud e com pouca publicação no DJEN. "
                           "Cadastrar o processo pelo número, à mão, e acompanhar "
                           "pelo portal — a plataforma guarda o prazo, mas não "
                           "descobre o movimento sozinha."},
}

# Aliases do DataJud que a varredura usa por padrão.
ALIASES_DATAJUD = [t["datajud"] for t in TRIBUNAIS.values() if t.get("datajud")]

# Siglas como o DJEN as devolve (campo siglaTribunal). Servem para
# filtrar a importação por tribunal e para medir cobertura.
SIGLAS_DJEN = [s for s in TRIBUNAIS if s != "SEEU"]


def do_numero(numero: str) -> str | None:
    """Descobre o tribunal pelo número CNJ.

    O número unificado (Resolução CNJ 65/2008) tem a forma
    NNNNNNN-DD.AAAA.J.TR.OOOO, onde J é o segmento da Justiça e TR o
    tribunal. Ler daí evita depender do que veio escrito na publicação.
    """
    import re
    d = re.sub(r"\D", "", numero or "")
    if len(d) != 20:
        return None
    j, tr = d[13], d[14:16]
    if j == "8":                      # Justiça Estadual
        estaduais = {"22": "TJRO", "24": "TJSC", "21": "TJRS", "16": "TJPR",
                     "11": "TJMT", "05": "TJBA", "26": "TJSP"}
        return estaduais.get(tr)
    if j == "5":                      # Justiça do Trabalho
        return {"12": "TRT12", "14": "TRT14"}.get(tr)
    if j == "4":                      # Justiça Federal
        return {"01": "TRF1", "04": "TRF4"}.get(tr)
    return None


def resumo() -> list[dict]:
    """Lista para a tela: quem é, em que sistema roda e por onde chega."""
    saida = []
    for sigla, t in TRIBUNAIS.items():
        saida.append({
            "sigla": sigla, "nome": t["nome"], "uf": t["uf"],
            "sistemas": t["sistemas"], "graus": t["graus"],
            "publicacoes": "DJEN (nacional)" if sigla != "SEEU" else "não cobre",
            "movimentos": f"DataJud ({t['datajud']})" if t.get("datajud") else "não cobre",
            "observacao": t.get("observacao"),
        })
    return saida
