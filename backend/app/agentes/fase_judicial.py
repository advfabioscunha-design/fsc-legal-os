"""
Em que ponto do processo o caso está — lido das publicações.

A tela Judicializado deixa de ser três colunas genéricas e passa a
seguir o caminho real de um processo:

    1º grau → audiência → perícia → concluso → julgado em 1º grau →
    2º grau → acórdão → STJ → STF → trânsito em julgado

com duas colunas de espera: **prazo em 1º grau** e **prazo em 2º grau**.

COMO A FASE É DECIDIDA
----------------------
Lendo as publicações do caso da mais nova para a mais antiga. A
primeira que traz um marco forte decide. Publicação sem marco (juntada
de petição, ato ordinatório) não muda nada — o processo continua onde
estava.

Três regras que vieram da prática, e não do código:

1. **Audiência e perícia são estados temporários.** Passada a data, se
   nada indicar que os autos foram conclusos, o caso volta para o
   começo (1º grau). Um card parado em "audiência" três meses depois da
   audiência é pior que inútil: mente sobre onde o trabalho está.

2. **Prazo aberto cobre a fase.** Enquanto houver prazo em aberto, o
   caso aparece na coluna de prazo do grau em que está. Cumprido o
   prazo, ele volta sozinho para a coluna de onde veio — a fase de base
   nunca é esquecida, fica guardada em `fase_judicial_base`.

3. **Trânsito em julgado é a última parada do judicial.** Quando a
   certidão aparece, o caso vai para lá. Quando os autos voltam ao 1º
   grau para cumprimento, ele sai do judicial e vira execução.

O QUE ISTO NÃO É
----------------
Não é certidão de andamento. É leitura de texto de publicação, que
varia por juízo e por redator. Erra. Por isso: a fase lida fica sempre
visível com a data em que foi lida, qualquer pessoa pode corrigir a
coluna na mão, e a correção manual NÃO é sobrescrita pela leitura
automática — quem viu o processo sabe mais que o classificador.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from ..core.db import get_db, registrar_evento

# ── As colunas, na ordem em que aparecem na tela ────────────────
COLUNAS = [
    "PRIMEIRO_GRAU", "PRAZO_1G", "AUDIENCIA", "PERICIA", "CONCLUSO",
    "JULGADO_1G", "SEGUNDO_GRAU", "PRAZO_2G", "ACORDAO", "STJ", "STF",
    "TRANSITO",
]

# Da fase para o grau — é o que decide qual coluna de prazo usar.
SEGUNDO_GRAU_EM_DIANTE = {"SEGUNDO_GRAU", "ACORDAO", "STJ", "STF"}

# Quanto tempo um "audiência designada" continua valendo quando o texto
# não traz a data. Quarenta e cinco dias é o intervalo comum entre a
# publicação e a audiência; passado isso, sem notícia, o caso volta ao
# 1º grau em vez de envelhecer numa coluna errada.
DIAS_SEM_DATA = 45


# ── Marcos, do mais específico para o mais genérico ─────────────
# A ordem importa: "trânsito em julgado" tem que ser testado antes de
# "julgado", e "acórdão" antes de "2º grau".
MARCOS: list[tuple[str, re.Pattern]] = [
    ("TRANSITO", re.compile(
        r"tr[âa]nsit(?:o|ou)\s+em\s+julgado|certid[ãa]o\s+de\s+tr[âa]nsito|"
        r"certifico\s+o\s+tr[âa]nsito", re.I)),
    # STF e STJ exigem AÇÃO, não menção. Sentença e acórdão citam esses
    # tribunais o tempo todo ("conforme entendimento do STJ..."), e a
    # primeira versão mandou para lá processos que estavam na 2ª Vara
    # Federal e no Núcleo 4.0 do TJRO. O padrão agora pede um verbo de
    # tramitação perto do termo.
    ("STF", re.compile(
        r"(?:interpos|admit|inadmit|remet|encaminh|distribu|subir?am?|sobrest)\w*"
        r"[^.]{0,90}(?:recurso\s+extraordin[áa]rio|supremo\s+tribunal\s+federal|\bSTF\b)"
        r"|(?:recurso\s+extraordin[áa]rio|\bARE\b)[^.]{0,80}"
        r"(?:interpost|admitid|inadmitid|provid|conhecid|distribu)", re.I)),
    ("STJ", re.compile(
        r"(?:interpos|admit|inadmit|remet|encaminh|distribu|subir?am?|sobrest)\w*"
        r"[^.]{0,90}(?:recurso\s+especial|superior\s+tribunal\s+de\s+justi[çc]a|\bSTJ\b)"
        r"|(?:recurso\s+especial|\bREsp\b|\bAREsp\b)[^.]{0,80}"
        r"(?:interpost|admitid|inadmitid|provid|conhecid|distribu)", re.I)),
    ("ACORDAO", re.compile(
        r"ac[óo]rd[ãa]o|ementa\s*:|vistos,?\s+relatados|"
        r"deram\s+provimento|negaram\s+provimento|"
        r"por\s+unanimidade|julgamento\s+realizado", re.I)),
    ("SEGUNDO_GRAU", re.compile(
        r"remetid[ao]s?\s+(?:os\s+autos\s+)?(?:ao|para\s+o)\s+(?:e\.?\s*)?"
        r"(?:tribunal|trt|trf|tj)|distribu[íi]d[ao]\s+(?:ao|para)\s+"
        r"(?:relator|desembargador|turma|c[âa]mara)|"
        r"recurso\s+(?:de\s+apela[çc][ãa]o\s+)?recebido|"
        r"pauta\s+de\s+julgament|"
        r"\b\d+[ªa]\s+(?:c[âa]mara|turma)\b|relator[a]?\s*:", re.I)),
    # CONCLUSO vem ANTES de JULGADO_1G de propósito: "vieram os autos
    # conclusos para sentença" é a frase mais comum do despacho que
    # antecede a sentença, e a palavra "sentença" nela levava o caso
    # para a coluna de julgado — uma coluna adiantada demais.
    ("CONCLUSO", re.compile(
        r"conclus[oa]s?\s+(?:para|ao\s+ju[íi]z)|vieram\s+os\s+autos\s+conclusos|"
        r"fa[çc]o\s+os\s+autos\s+conclusos|autos\s+conclusos", re.I)),
    ("JULGADO_1G", re.compile(
        r"julgo\s+(?:proced|improced|extint|parcial)|resolvo\s+o\s+m[ée]rito|"
        r"ante\s+o\s+exposto|^\s*senten[çc]a\s*$|dispositivo\s*:", re.I | re.M)),
    ("PERICIA", re.compile(
        r"per[íi]cia\s+(?:designada|agendada|marcada)|nomei?[ao]\s+(?:o\s+)?perit|"
        r"per[íi]cia\s+(?:m[ée]dica|t[ée]cnica|cont[áa]bil)\s+"
        r"(?:designada|agendada|marcada|no\s+dia)|"
        r"comparecer\s+[àa]\s+per[íi]cia", re.I)),
    ("AUDIENCIA", re.compile(
        r"audi[êe]ncia\s+(?:de\s+\w+\s+)?(?:designada|agendada|marcada|"
        r"redesignada|no\s+dia|para\s+o\s+dia)|"
        r"designo\s+(?:a\s+)?audi[êe]ncia|"
        r"comparecer\s+[àa]\s+audi[êe]ncia", re.I)),
]

# Autos que voltam ao 1º grau depois do trânsito: é a deixa para virar
# execução.
_RE_BAIXA = re.compile(
    r"baixa\s+dos?\s+autos|remessa\s+(?:dos\s+autos\s+)?(?:ao|para\s+o)\s+"
    r"ju[íi]zo\s+de\s+origem|autos\s+recebidos\s+(?:do|no)\s+"
    r"(?:tribunal|ju[íi]zo)|cumprimento\s+de\s+senten[çc]a|"
    r"execu[çc][ãa]o\s+(?:de\s+t[íi]tulo|da\s+senten[çc]a)", re.I)

# Data no texto: "no dia 14/10/2026", "para 14.10.2026 às 14h"
_RE_DATA = re.compile(r"\b(\d{2})[/.\-](\d{2})[/.\-](\d{4})\b")


def _data_no_texto(texto: str, perto_de: re.Pattern) -> date | None:
    """Procura uma data logo depois do marco (audiência, perícia).

    Só olha os 300 caracteres seguintes: mais que isso e a data pode ser
    de outra coisa — o prazo de uma petição, a data da publicação."""
    m = perto_de.search(texto or "")
    if not m:
        return None
    trecho = texto[m.start(): m.start() + 300]
    for d, mes, a in _RE_DATA.findall(trecho):
        try:
            return date(int(a), int(mes), int(d))
        except ValueError:
            continue
    return None


def classificar(publicacoes: list[dict]) -> tuple[str, str]:
    """(fase, motivo). `publicacoes` em ordem cronológica crescente.

    Cada item precisa de `texto` e `data` (ISO)."""
    if not publicacoes:
        return "PRIMEIRO_GRAU", "sem publicações"

    hoje = date.today()
    for pub in reversed(publicacoes):          # da mais nova para a mais velha
        texto = pub.get("texto") or pub.get("conteudo") or ""
        if not texto:
            continue

        # O Diário classifica o próprio documento (campo tipoDocumento),
        # e isso vale mais que qualquer palavra no corpo: "Sentença" dita
        # pelo tribunal é sentença; "sentença" no meio de um despacho é
        # só uma palavra. Quando o tipo é claro, ele decide.
        # A CLASSE do processo, quando o Diário informa, é o sinal mais
        # forte de todos: "RECURSO ESPECIAL" é o processo, não uma
        # citação dentro dele.
        classe = (pub.get("classe") or "").upper()
        if "EXTRAORDIN" in classe:
            return "STF", "classe do processo: recurso extraordinário"
        if "RECURSO ESPECIAL" in classe:
            return "STJ", "classe do processo: recurso especial"

        tipo = (pub.get("tipo") or "").lower()
        if tipo:
            if "acórdão" in tipo or "acordao" in tipo:
                return "ACORDAO", "acórdão publicado"
            if "sentença" in tipo or "sentenca" in tipo:
                return "JULGADO_1G", "sentença publicada"
            if "pauta" in tipo:
                return "SEGUNDO_GRAU", "incluído em pauta de julgamento"
        try:
            quando = date.fromisoformat((pub.get("data")
                                         or pub.get("data_movimento") or "")[:10])
        except ValueError:
            quando = hoje

        for fase, padrao in MARCOS:
            if not padrao.search(texto):
                continue

            # Audiência e perícia valem enquanto não passam. Depois, o
            # caso volta ao começo — a menos que algo mais novo já
            # tivesse decidido, o que não é o caso aqui, porque estamos
            # varrendo do mais novo para o mais antigo.
            if fase in ("AUDIENCIA", "PERICIA"):
                marcada = _data_no_texto(texto, padrao)
                if marcada and marcada < hoje:
                    return ("PRIMEIRO_GRAU",
                            f"{fase.lower()} de {marcada:%d/%m/%Y} já passou "
                            f"e os autos não vieram conclusos")
                if not marcada and (hoje - quando).days > DIAS_SEM_DATA:
                    return ("PRIMEIRO_GRAU",
                            f"{fase.lower()} designada em {quando:%d/%m/%Y}, "
                            f"sem notícia desde então")
                quando_txt = f" para {marcada:%d/%m/%Y}" if marcada else ""
                return fase, f"{fase.lower()} designada{quando_txt}"

            return fase, f"publicação de {quando:%d/%m/%Y}"

    return "PRIMEIRO_GRAU", "nenhum marco encontrado nas publicações"


def voltou_ao_primeiro_grau(publicacoes: list[dict]) -> bool:
    """Depois do trânsito, os autos baixaram? É a hora da execução."""
    for pub in reversed(publicacoes[-5:]):
        if _RE_BAIXA.search(pub.get("texto") or pub.get("conteudo") or ""):
            return True
    return False


# ── Aplicação no caso ───────────────────────────────────────────
def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def recalcular(caso_id: str, respeitar_manual: bool = True) -> dict:
    """Relê as publicações do caso e ajusta a coluna."""
    db = get_db()
    achado = db.table("casos").select(
        "id,estado,fase_judicial,fase_judicial_base,fase_judicial_fonte"
    ).eq("id", caso_id).limit(1).execute().data
    if not achado:
        return {"ok": False, "erro": "caso não encontrado"}
    caso = achado[0]

    # Quem corrigiu à mão viu o processo; o classificador não.
    if respeitar_manual and caso.get("fase_judicial_fonte") == "MANUAL":
        return {"ok": True, "fase": caso.get("fase_judicial"), "manual": True}

    pubs = db.table("intimacoes").select("conteudo,data_movimento,tipo,payload") \
        .eq("caso_id", caso_id).order("data_movimento").limit(200).execute().data
    publicacoes = [{"texto": p.get("conteudo"), "tipo": p.get("tipo"),
                    "classe": (p.get("payload") or {}).get("classe"),
                    "data": (p.get("data_movimento") or "")[:10]} for p in pubs]

    base, motivo = classificar(publicacoes)

    # Prazo em aberto cobre a fase — e a fase de base fica guardada,
    # para o caso voltar exatamente para onde estava quando o prazo
    # for cumprido.
    abertos = db.table("prazos").select("id,data,prazo_fatal") \
        .eq("caso_id", caso_id).eq("status", "ABERTO").limit(1).execute().data
    fase = base
    if abertos:
        fase = "PRAZO_2G" if base in SEGUNDO_GRAU_EM_DIANTE else "PRAZO_1G"
        motivo = f"prazo em aberto — volta para {base.lower()} quando cumprido"

    campos = {"fase_judicial": fase, "fase_judicial_base": base,
              "fase_judicial_em": _agora(), "fase_judicial_motivo": motivo[:300],
              "fase_judicial_fonte": "AUTO", "atualizado_em": _agora()}

    # Trânsito com autos baixados: sai do judicial e vira execução.
    virou_execucao = False
    if base == "TRANSITO" and voltou_ao_primeiro_grau(publicacoes):
        campos["estado"] = "RECEBIMENTO"
        campos["recebimento_em"] = _agora()
        campos["transito_em"] = campos.get("transito_em") or _agora()
        virou_execucao = True
    elif base == "TRANSITO" and caso.get("estado") == "JUDICIAL":
        campos["transito_em"] = _agora()

    if fase != caso.get("fase_judicial"):
        db.table("casos").update(campos).eq("id", caso_id).execute()
        registrar_evento(caso_id, "FASE_JUDICIAL", {
            "de": caso.get("fase_judicial"), "para": fase, "motivo": motivo,
            "virou_execucao": virou_execucao,
        })
    else:
        db.table("casos").update({
            "fase_judicial_base": base, "fase_judicial_motivo": motivo[:300],
            "fase_judicial_em": _agora(),
        }).eq("id", caso_id).execute()

    return {"ok": True, "fase": fase, "base": base, "motivo": motivo,
            "virou_execucao": virou_execucao}


def recalcular_todos(limite: int = 500) -> dict:
    """Passa por todo o acervo judicial. Roda na controladoria diária e
    depois de cada importação."""
    db = get_db()
    casos = db.table("casos").select("id").eq("situacao", "ATIVO") \
        .in_("estado", ["JUDICIAL", "PROTOCOLADO", "TRANSITO_JULGADO"]) \
        .limit(limite).execute().data
    mudados, execucao, erros = 0, 0, 0
    for c in casos:
        try:
            r = recalcular(c["id"])
            if r.get("ok") and not r.get("manual"):
                mudados += 1
                if r.get("virou_execucao"):
                    execucao += 1
        except Exception:
            erros += 1
    return {"casos": len(casos), "reavaliados": mudados,
            "viraram_execucao": execucao, "erros": erros}


def mover_a_mao(caso_id: str, fase: str, motivo: str = "") -> dict:
    """Correção humana. Fica marcada como MANUAL e o classificador passa
    a não mexer mais — quem olhou o processo tem mais informação que a
    leitura de texto."""
    if fase not in COLUNAS:
        raise ValueError(f"Coluna desconhecida: {fase}")
    get_db().table("casos").update({
        "fase_judicial": fase, "fase_judicial_base": fase,
        "fase_judicial_fonte": "MANUAL", "fase_judicial_em": _agora(),
        "fase_judicial_motivo": (motivo or "movido à mão")[:300],
        "atualizado_em": _agora(),
    }).eq("id", caso_id).execute()
    registrar_evento(caso_id, "FASE_JUDICIAL_MANUAL",
                     {"para": fase, "motivo": motivo})
    return {"ok": True, "fase": fase}


def voltar_ao_automatico(caso_id: str) -> dict:
    """Desfaz a trava manual e relê as publicações."""
    get_db().table("casos").update({"fase_judicial_fonte": "AUTO"}) \
        .eq("id", caso_id).execute()
    return recalcular(caso_id, respeitar_manual=False)
