"""
Importador de processos — carrega o acervo já judicializado.

Duas portas, as duas gratuitas:

  POR OAB      lê o DJEN pelo número da OAB e lista todo processo em que
               o escritório aparece, com a parte que ele representa.
  POR NÚMERO   um processo por vez, com o histórico de publicações dele.

O fluxo é de duas etapas de propósito: `previa_*` mostra o que foi
encontrado e o que disso já existe na plataforma; `importar` grava só o
que o advogado marcou. Importação automática de acervo inteiro é o tipo
de coisa que duplica cliente e polui a esteira — a conferência fica.

Cada processo importado entra como caso na fase escolhida (JUDICIAL ou
RECEBIMENTO), com as publicações viradas intimações e, quando o ato tem
prazo, com o prazo criado pela controladoria.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from ..core.config import get_settings
from ..core.datas import antecipar_uteis, somar_uteis
from ..core.db import get_db, registrar_evento
from ..integracoes import comunica_cnj

# Prazos-padrão por tipo de ato, em dias úteis. É estimativa de partida,
# não leitura do texto: tudo que sai daqui vai marcado `prazo_estimado`.
PRAZO_PADRAO: dict[str, int] = {
    "sentença": 15,          # apelação
    "sentenca": 15,
    "acórdão": 15,           # embargos / recurso
    "acordao": 15,
    "decisão": 15,
    "decisao": 15,
    "despacho": 5,
    "intimação": 15,
    "intimacao": 15,
    "embargos": 5,
    "citação": 15,
    "citacao": 15,
}

# Atos que não abrem prazo para a parte — não viram prazo na agenda.
SEM_PRAZO = ("pauta de julgamento", "certidão", "certidao", "ato ordinatório",
             "ato ordinatorio", "publicação de acórdão", "edital")

_RE_TRANSITO = re.compile(
    r"tr[âa]nsit(?:o|ou)\s+em\s+julgado|certid[ãa]o\s+de\s+tr[âa]nsito", re.I)
_RE_CUMPRIMENTO = re.compile(
    r"cumprimento\s+de\s+senten[çc]a|execu[çc][ãa]o\s+de\s+t[íi]tulo|"
    r"alvar[áa]|expedi[çc][ãa]o\s+de\s+(?:RPV|precat[óo]rio)", re.I)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def transitou(texto: str | None) -> bool:
    return bool(texto and _RE_TRANSITO.search(texto))


def em_recebimento(texto: str | None) -> bool:
    return bool(texto and _RE_CUMPRIMENTO.search(texto))


def prazo_do_ato(item: dict) -> int | None:
    """Dias úteis do prazo, ou None quando o ato não abre prazo."""
    rotulo = f"{item.get('tipo_documento') or ''} {item.get('tipo') or ''}".lower()
    if any(s in rotulo for s in SEM_PRAZO):
        return None
    for chave, dias in PRAZO_PADRAO.items():
        if chave in rotulo:
            return dias
    return None


# ── Prévia ──────────────────────────────────────────────────────
def _casos_por_numero(numeros: list[str]) -> dict[str, dict]:
    if not numeros:
        return {}
    db = get_db()
    achados: dict[str, dict] = {}
    for num in set(numeros):
        r = db.table("casos").select("id,estado,numero_processo,cliente_id,clientes(nome)") \
            .eq("numero_processo", num).limit(1).execute().data
        if r:
            achados[num] = r[0]
    return achados


def _resumir(numero: str, comunicacoes: list[dict], existente: dict | None) -> dict:
    ultima = comunicacoes[-1]
    cliente = next((c.get("cliente_provavel") for c in reversed(comunicacoes)
                    if c.get("cliente_provavel")), None)
    texto_todo = "\n".join(c.get("texto") or "" for c in comunicacoes)
    return {
        "numero_processo": numero,
        "tribunal": ultima.get("tribunal"),
        "orgao": ultima.get("orgao"),
        "classe": ultima.get("classe"),
        "ultimo_ato": ultima.get("tipo_documento") or ultima.get("tipo"),
        "ultima_data": ultima.get("data"),
        "publicacoes": len(comunicacoes),
        "cliente_provavel": cliente,
        "transitou": transitou(texto_todo),
        "fase_sugerida": ("RECEBIMENTO" if (transitou(texto_todo)
                                           or em_recebimento(texto_todo))
                          else "JUDICIAL"),
        "ja_na_plataforma": bool(existente),
        "caso_id": (existente or {}).get("id"),
        "cliente_cadastrado": ((existente or {}).get("clientes") or {}).get("nome"),
        "comunicacoes": comunicacoes,
    }


def previa_por_oab(numero: str | None = None, uf: str | None = None,
                   dias: int = 60) -> dict:
    """O que a OAB devolve, agrupado por processo, já cruzado com o que
    existe na plataforma."""
    s = get_settings()
    if not numero or not uf:
        # OAB do escritório, do .env: "OAB/RO 10.849"
        m = re.search(r"OAB/?\s*([A-Z]{2})\s*([\d.]+)", s.oab or "", re.I)
        if not m:
            raise ValueError("Informe o número e a UF da OAB.")
        uf = uf or m.group(1)
        numero = numero or m.group(2)

    comunicacoes = comunica_cnj.por_oab(numero, uf, dias=dias)
    grupos = comunica_cnj.agrupar_por_processo(comunicacoes)
    existentes = _casos_por_numero(list(grupos))
    processos = [_resumir(n, c, existentes.get(n)) for n, c in grupos.items()]
    processos.sort(key=lambda p: p.get("ultima_data") or "", reverse=True)
    return {
        "oab": f"OAB/{uf.upper()} {numero}", "dias": dias,
        "publicacoes": len(comunicacoes),
        "processos": len(processos),
        "novos": sum(1 for p in processos if not p["ja_na_plataforma"]),
        "itens": processos,
    }


def previa_de_comunicacoes(itens: list[dict]) -> dict:
    """Mesma prévia, mas a partir de publicações que o NAVEGADOR leu.

    O Comunica CNJ recusa requisição vinda de fora do Brasil, e o nosso
    servidor está nos Estados Unidos. Então a consulta sai do navegador
    do escritório — que está no Brasil — e o resultado chega aqui já
    normalizado. O cruzamento com o acervo e a gravação continuam no
    servidor, onde é o lugar deles."""
    grupos: dict[str, list[dict]] = {}
    for c in itens or []:
        num = (c.get("numero_processo") or "").strip()
        if num:
            grupos.setdefault(num, []).append(c)
    for lista in grupos.values():
        lista.sort(key=lambda i: i.get("data") or "")
    existentes = _casos_por_numero(list(grupos))
    processos = [_resumir(n, c, existentes.get(n)) for n, c in grupos.items()]
    processos.sort(key=lambda p: p.get("ultima_data") or "", reverse=True)
    return {
        "publicacoes": len(itens or []),
        "processos": len(processos),
        "novos": sum(1 for p in processos if not p["ja_na_plataforma"]),
        "itens": processos,
    }


def sincronizar_conhecidos(itens: list[dict]) -> dict:
    """Grava as publicações novas dos processos que JÁ estão aqui, cria
    os prazos e deixa os processos desconhecidos para conferência."""
    from . import controladoria
    db = get_db()
    previa = previa_de_comunicacoes(itens)
    novas, prazos = 0, 0
    for p in previa["itens"]:
        if not p["ja_na_plataforma"]:
            continue
        for com in p["comunicacoes"]:
            nova = _gravar_intimacao(p["caso_id"], com)
            if not nova:
                continue
            novas += 1
            if nova.get("prazo_em"):
                _gravar_prazo(p["caso_id"], nova,
                              f"{nova.get('tipo') or 'Intimação'} — {p['numero_processo']}")
                db.table("prazos").update({
                    "depende_do_cliente": controladoria.depende_do_cliente(
                        nova.get("conteudo"), nova.get("tipo")),
                }).eq("intimacao_id", nova["id"]).execute()
                prazos += 1
    return {"publicacoes": previa["publicacoes"], "intimacoes": novas,
            "prazos": prazos, "novos_para_conferir": previa["novos"],
            "processos": previa["processos"]}


def previa_por_numero(numero: str) -> dict:
    comunicacoes = comunica_cnj.por_processo(numero)
    if not comunicacoes:
        return {"processos": 0, "itens": [],
                "aviso": "Nada publicado no DJEN para este número. Confira o "
                         "número ou cadastre o processo manualmente."}
    limpo = comunicacoes[-1].get("numero_processo") or numero
    existente = _casos_por_numero([limpo]).get(limpo)
    return {"processos": 1, "publicacoes": len(comunicacoes),
            "itens": [_resumir(limpo, comunicacoes, existente)]}


# ── Gravação ────────────────────────────────────────────────────
def _achar_ou_criar_cliente(nome: str | None) -> str:
    db = get_db()
    nome = (nome or "").strip() or "A identificar"
    r = db.table("clientes").select("id,nome").ilike("nome", nome).limit(1).execute().data
    if r:
        return r[0]["id"]
    novo = db.table("clientes").insert({
        "nome": nome, "origem": "IMPORTADO_CNJ",
    }).execute().data[0]
    return novo["id"]


def _gravar_intimacao(caso_id: str, com: dict) -> dict | None:
    """Insere a publicação como intimação, sem duplicar (evento_id)."""
    db = get_db()
    existe = db.table("intimacoes").select("id").eq("evento_id", com["evento_id"]) \
        .limit(1).execute().data
    if existe:
        return None
    dias = prazo_do_ato(com)
    prazo_fatal = None
    if dias and com.get("data"):
        try:
            prazo_fatal = somar_uteis(date.fromisoformat(com["data"][:10]), dias).isoformat()
        except ValueError:
            prazo_fatal = None
    return db.table("intimacoes").insert({
        "caso_id": caso_id, "evento_id": com["evento_id"],
        "tribunal": com.get("tribunal"), "orgao": com.get("orgao"),
        "numero_processo": com.get("numero_processo"),
        "conteudo": (com.get("texto") or "")[:20000],
        "tipo": com.get("tipo_documento") or com.get("tipo"),
        "link": com.get("link"), "origem": "COMUNICA_CNJ",
        "status": "A_RESOLVER", "data_movimento": com.get("data"),
        "prazo_em": prazo_fatal, "prazo_dias": dias,
        "prazo_estimado": bool(dias),
        "payload": {k: v for k, v in com.items() if k != "texto"},
    }).execute().data[0]


def _gravar_prazo(caso_id: str, intimacao: dict, titulo: str) -> None:
    """Prazo de trabalho = prazo fatal recuado dois dias úteis."""
    if not intimacao.get("prazo_em"):
        return
    db = get_db()
    fatal = date.fromisoformat(intimacao["prazo_em"][:10])
    db.table("prazos").upsert({
        "caso_id": caso_id, "intimacao_id": intimacao["id"],
        "titulo": titulo[:140],
        "descricao": (intimacao.get("conteudo") or "")[:1000],
        "data": antecipar_uteis(fatal, 2).isoformat(),
        "prazo_fatal": fatal.isoformat(),
        "tipo": intimacao.get("tipo"),
        "origem": "CONTROLADORIA",
        "depende_do_cliente": False,
        "atualizado_em": _agora(),
    }, on_conflict="intimacao_id").execute()


def importar(processos: list[dict], fase: str = "JUDICIAL") -> dict:
    """Grava os processos marcados na tela.

    Cada item precisa de `numero_processo` e `comunicacoes`; aceita
    `cliente_nome`, `caso_id` (para anexar a um caso que já existe),
    `grupo` e `fase`."""
    if fase not in ("JUDICIAL", "RECEBIMENTO"):
        raise ValueError("Fase deve ser JUDICIAL ou RECEBIMENTO.")
    db = get_db()
    criados, atualizados, intimacoes, prazos = 0, 0, 0, 0

    for p in processos:
        numero = (p.get("numero_processo") or "").strip()
        coms = p.get("comunicacoes") or []
        if not numero:
            continue
        destino = p.get("fase") or fase
        ultima = coms[-1] if coms else {}

        caso_id = p.get("caso_id")
        if not caso_id:
            achado = _casos_por_numero([numero]).get(numero)
            caso_id = (achado or {}).get("id")

        dados = {
            "numero_processo": numero,
            "tribunal": ultima.get("tribunal"),
            "orgao_julgador": ultima.get("orgao"),
            "classe_judicial": ultima.get("classe"),
            "importado_de": "COMUNICA_CNJ",
            "atualizado_em": _agora(),
        }
        if caso_id:
            # Caso que já existe só avança de fase, nunca retrocede:
            # quem está em RECEBIMENTO não volta para JUDICIAL por causa
            # de uma publicação antiga que apareceu na varredura.
            atual = db.table("casos").select("estado").eq("id", caso_id) \
                .single().execute().data or {}
            if atual.get("estado") != "RECEBIMENTO":
                dados["estado"] = destino
            db.table("casos").update(dados).eq("id", caso_id).execute()
            atualizados += 1
        else:
            dados.update({
                "cliente_id": _achar_ou_criar_cliente(p.get("cliente_nome")
                                                      or p.get("cliente_provavel")),
                "estado": destino,
                "situacao": "ATIVO",
                "grupo": p.get("grupo"),
                "titulo": f"{ultima.get('classe') or 'Processo'} {numero}",
                "protocolado_em": (coms[0].get("data") if coms else None),
                "judicial_em": _agora(),
            })
            if destino == "RECEBIMENTO":
                dados["recebimento_em"] = _agora()
            caso_id = db.table("casos").insert(dados).execute().data[0]["id"]
            criados += 1

        for com in coms:
            nova = _gravar_intimacao(caso_id, com)
            if not nova:
                continue
            intimacoes += 1
            if nova.get("prazo_em"):
                titulo = (f"{nova.get('tipo') or 'Intimação'} — "
                          f"{numero} ({com.get('tribunal') or ''})")
                _gravar_prazo(caso_id, nova, titulo)
                prazos += 1

        registrar_evento(caso_id, "PROCESSO_IMPORTADO", {
            "numero": numero, "fase": destino, "fonte": "COMUNICA_CNJ",
            "publicacoes": len(coms),
        })

    return {"criados": criados, "atualizados": atualizados,
            "intimacoes": intimacoes, "prazos": prazos}
