"""
TRAVA DE PETICIONAMENTO — o que precisa estar certo antes de protocolar.

Duas perguntas diferentes, dois agentes:

  REGRA A — PETIÇÃO INICIAL
  "O kit mínimo está na pasta?" Procuração, contrato, documento de
  identidade e comprovante de endereço. Sem procuração não há capacidade
  postulatória; sem os demais, a inicial nasce pedindo emenda.

  REGRA B — DEMAIS PEÇAS
  "Esta peça cabe agora?" Contestação depois do prazo, réplica antes da
  contestação, recurso de decisão que não comporta aquele recurso — erro
  de momento processual custa prazo, e prazo perdido não volta.

SOBRE O PAPEL DA IA AQUI
O agente não decide se peticiona: ele aponta o que viu e diz se, no que
consegue verificar, está coerente. Quem decide é o advogado — inclusive
para seguir contra o parecer, pelo override. Um sistema que impede o
advogado de peticionar seria pior que o problema que resolve; um que
deixa passar qualquer coisa sem avisar também.

A resposta vem por ferramenta, não por JSON solto no texto. Já erramos
isso nesta plataforma: aspas dentro de citação quebravam o parse e a
análise inteira se perdia.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone as _tz

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

# tipos que entram pela Regra A
INICIAIS = {"INICIAL", "PETICAO_INICIAL", "INICIAL_CUMULATIVA"}

KIT_MINIMO = {
    "PROCURACAO": "Procuração assinada",
    "CONTRATO": "Contrato de honorários assinado",
    "IDENTIDADE": "Documento de identidade com foto (CNH ou carteira de identidade)",
    "ENDERECO": "Comprovante de endereço",
}

# como reconhecer cada item pelo que está gravado na pasta do caso
PISTAS = {
    "PROCURACAO": ("procura",),
    "CONTRATO": ("contrato", "honorar"),
    # "rg" fica na lista de propósito, mesmo o sistema não pedindo mais
    # o número: é palavra que reconhece arquivo enviado pelo cliente, e
    # ele continua batizando a foto do documento de "rg.jpg".
    "IDENTIDADE": ("rg", "cnh", "identidade", "habilita", "documento pessoal"),
    "ENDERECO": ("endereco", "endereço", "comprovante de resid", "residencia",
                 "residência", "conta de luz", "energia", "agua", "água"),
}


FERRAMENTA = {
    "name": "parecer",
    "description": "Registra o parecer da trava de peticionamento.",
    "input_schema": {
        "type": "object",
        "properties": {
            "aprovado": {
                "type": "boolean",
                "description": "true libera o peticionamento; false trava.",
            },
            "motivo": {
                "type": "string",
                "description": "Em uma ou duas frases, em português claro, "
                               "o que impede (ou por que está liberado). "
                               "Escreva para o advogado ler com pressa.",
            },
            "faltando": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Itens que faltam ou pontos a resolver.",
            },
            "gravidade": {
                "type": "string",
                "enum": ["IMPEDITIVO", "ATENCAO"],
                "description": "IMPEDITIVO quando protocolar assim gera nulidade, "
                               "emenda certa ou perda de prazo. ATENCAO quando é "
                               "recomendável revisar, mas o advogado pode ter "
                               "razão para seguir.",
            },
        },
        "required": ["aprovado", "motivo"],
    },
}


def _claude():
    return anthropic.Anthropic(api_key=get_settings().claude_api_key)


def _parecer(system: str, conteudo: str) -> dict:
    s = get_settings()
    r = _claude().messages.create(
        model=s.claude_model, max_tokens=1200, system=system,
        tools=[FERRAMENTA], tool_choice={"type": "tool", "name": "parecer"},
        messages=[{"role": "user", "content": conteudo}],
    )
    for bloco in r.content:
        if bloco.type == "tool_use" and bloco.name == "parecer":
            d = bloco.input or {}
            return {"aprovado": bool(d.get("aprovado")),
                    "motivo": d.get("motivo") or "",
                    "faltando": d.get("faltando") or [],
                    "gravidade": d.get("gravidade") or "ATENCAO"}
    # a trava falhando não pode liberar por omissão
    return {"aprovado": False, "faltando": [],
            "gravidade": "ATENCAO",
            "motivo": "Não foi possível concluir a validação automática. "
                      "Confira manualmente antes de protocolar."}


# ══════════════════════════════════════════════════════════════════
#  REGRA A — petição inicial: o kit mínimo está na pasta?
# ══════════════════════════════════════════════════════════════════
SYSTEM_VALIDADOR = """Você é o Agente Validador de Documentos da FC Advocacia,
escritório do Dr. Fábio Silva Cunha (OAB/RO 10.849).

Recebe a lista dos documentos que existem na pasta de um cliente e decide se
a PETIÇÃO INICIAL pode ser protocolada.

KIT MÍNIMO EXIGIDO
1. Procuração assinada pelo cliente — sem ela não há capacidade postulatória
   e a inicial é inepta. A falta é sempre IMPEDITIVA.
2. Contrato de honorários assinado — protege o escritório. A falta é
   IMPEDITIVA.
3. Documento de identidade do cliente, com foto.
4. Comprovante de endereço — fixa a competência territorial.

COMO DECIDIR
- Trabalhe SOMENTE com a lista recebida. Não presuma que um documento
  existe porque "normalmente existe".
- Documento gerado mas ainda NÃO assinado pelo cliente não conta como
  presente: minuta não é procuração.
- Se faltar qualquer item do kit, aprovado = false, e liste o que falta com
  o nome que o advogado reconhece.
- Se estiver tudo presente, aprovado = true, e o motivo diz em uma linha o
  que foi conferido.
- Gravidade IMPEDITIVO quando faltar procuração ou contrato. Para
  identidade e comprovante de endereço, avalie: costumam gerar emenda, o
  que também é IMPEDITIVO na prática, mas diga isso com clareza.

Não invente documento que não está na lista. Não sugira protocolar "assim
mesmo": essa decisão é do advogado, por outro caminho."""


def _documentos_do_caso(caso_id: str) -> list[dict]:
    """Junta o que veio do cliente e o que a plataforma gerou/recebeu
    assinado. Um item só conta como presente se estiver de fato lá."""
    db = get_db()
    itens: list[dict] = []

    try:
        for d in (db.table("documentos").select(
                "tipo,observacao,storage_path,enviado_por,criado_em")
                .eq("caso_id", caso_id).limit(200).execute().data or []):
            itens.append({
                "origem": "pasta do caso",
                "tipo": d.get("tipo") or "",
                "descricao": (d.get("observacao") or d.get("tipo") or "").strip(),
                "enviado_por": d.get("enviado_por") or "",
            })
    except Exception:
        pass

    try:
        for d in (db.table("documentos_assinatura").select(
                "tipo,titulo,status,assinado_em")
                .eq("caso_id", caso_id).limit(100).execute().data or []):
            itens.append({
                "origem": "documento da plataforma",
                "tipo": d.get("tipo") or "",
                "descricao": d.get("titulo") or "",
                "status": d.get("status") or "",
                "assinado": bool(d.get("assinado_em")),
            })
    except Exception:
        pass
    return itens


def _conferencia_objetiva(itens: list[dict]) -> dict:
    """Antes da IA, uma conferência determinística: o que bate por nome de
    tipo e por assinatura. Serve de base e evita que o modelo 'ache' que um
    documento existe."""
    achados = {k: None for k in KIT_MINIMO}
    for it in itens:
        texto = f"{it.get('tipo','')} {it.get('descricao','')}".lower()
        assinado = it.get("assinado") or it.get("origem") == "pasta do caso" \
            or str(it.get("tipo", "")).upper().startswith("ASSINADO_")
        for chave, pistas in PISTAS.items():
            if achados[chave]:
                continue
            if any(p in texto for p in pistas):
                # procuração e contrato só valem assinados
                if chave in ("PROCURACAO", "CONTRATO") and not assinado:
                    continue
                achados[chave] = it.get("descricao") or it.get("tipo")
    return achados


def validar_inicial(caso_id: str) -> dict:
    itens = _documentos_do_caso(caso_id)
    achados = _conferencia_objetiva(itens)
    faltando_obj = [KIT_MINIMO[k] for k, v in achados.items() if not v]

    conteudo = (
        "DOCUMENTOS ENCONTRADOS NA PASTA DO CASO:\n"
        + (json.dumps(itens, ensure_ascii=False, indent=1) if itens
           else "(a pasta está vazia)")
        + "\n\nCONFERÊNCIA AUTOMÁTICA POR NOME (pode falhar em nomes atípicos):\n"
        + json.dumps({KIT_MINIMO[k]: (v or "NÃO ENCONTRADO")
                      for k, v in achados.items()}, ensure_ascii=False, indent=1)
        + "\n\nConfirme ou corrija a conferência acima e dê o parecer."
    )
    r = _parecer(SYSTEM_VALIDADOR, conteudo)
    # a conferência objetiva é rede de segurança: se faltou item, não libera
    if faltando_obj and r["aprovado"]:
        r = {"aprovado": False,
             "motivo": "Faltam documentos do kit mínimo: "
                       + ", ".join(faltando_obj) + ".",
             "faltando": faltando_obj, "gravidade": "IMPEDITIVO"}
    r["regra"] = "A"
    return r


# ══════════════════════════════════════════════════════════════════
#  REGRA B — demais peças: cabe agora?
# ══════════════════════════════════════════════════════════════════
SYSTEM_CONTROLLER = """Você é o Agente Controller Processual da FC Advocacia,
escritório do Dr. Fábio Silva Cunha (OAB/RO 10.849), que atua em Rondônia e
Santa Catarina.

Recebe o ÚLTIMO ANDAMENTO conhecido de um processo e o TIPO DE PEÇA que o
advogado quer protocolar. Decide se a peça é adequada àquele momento
processual.

O QUE VERIFICAR
- Sequência: a peça pressupõe um ato que já ocorreu? (réplica pressupõe
  contestação; embargos pressupõem decisão embargável; cumprimento de
  sentença pressupõe trânsito em julgado.)
- Prazo: o andamento indica prazo em curso, encerrado ou nem iniciado? Se o
  prazo aparenta estar vencido, isso é IMPEDITIVO e deve ser dito.
- Cabimento: o recurso escolhido é o cabível contra aquela decisão?
- Duplicidade: o andamento sugere que essa peça já foi protocolada?

COMO DECIDIR
- Você trabalha com o andamento informado, que pode estar desatualizado ou
  incompleto. Quando a informação não permitir concluir, NÃO invente: diga
  que o andamento disponível não permite confirmar e classifique como
  ATENCAO, não como IMPEDITIVO.
- IMPEDITIVO é para o que gera nulidade, intempestividade ou não
  conhecimento. Divergência de estratégia não é impedimento — o advogado
  conhece o caso melhor que você.
- aprovado = true quando a peça é compatível, ou quando nada no andamento
  a contraindica.
- O motivo deve citar o andamento em que você se baseou.

Não sugira teses nem redija a peça. Sua função é de conferência de momento
processual, e só."""


def _ultimo_andamento(caso_id: str) -> dict | None:
    db = get_db()
    caso = db.table("casos").select("numero_processo").eq("id", caso_id) \
             .maybe_single().execute().data or {}
    try:
        q = db.table("intimacoes").select(
            "conteudo,tribunal,numero_processo,data_movimento,prazo_em,status") \
            .order("data_movimento", desc=True).limit(1)
        linhas = q.eq("caso_id", caso_id).execute().data or []
        if not linhas and caso.get("numero_processo"):
            linhas = (db.table("intimacoes").select(
                "conteudo,tribunal,numero_processo,data_movimento,prazo_em,status")
                .eq("numero_processo", caso["numero_processo"])
                .order("data_movimento", desc=True).limit(1).execute().data or [])
        return linhas[0] if linhas else None
    except Exception:
        return None


def validar_peca(caso_id: str, tipo_peticao: str) -> dict:
    db = get_db()
    caso = db.table("casos").select(
        "numero_processo,estado,titulo,grupo,prazo_fatal,prazo_descricao"
    ).eq("id", caso_id).single().execute().data or {}
    andamento = _ultimo_andamento(caso_id)

    if not andamento and not caso.get("numero_processo"):
        return {"aprovado": False, "regra": "B", "gravidade": "IMPEDITIVO",
                "faltando": ["número do processo"],
                "motivo": "Este caso não tem número de processo cadastrado nem "
                          "andamento registrado. Para peça que não seja a "
                          "inicial, é preciso saber em que processo e em que "
                          "momento ela entra."}

    conteudo = (
        f"PEÇA QUE O ADVOGADO QUER PROTOCOLAR: {tipo_peticao}\n\n"
        f"PROCESSO: {caso.get('numero_processo') or 'não informado'}\n"
        f"MATÉRIA: {caso.get('grupo') or '—'} · {caso.get('titulo') or '—'}\n"
        f"ETAPA NA ESTEIRA: {caso.get('estado') or '—'}\n"
        f"PRAZO CADASTRADO: {caso.get('prazo_fatal') or 'nenhum'}"
        f" {caso.get('prazo_descricao') or ''}\n"
        f"HOJE: {date.today().isoformat()}\n\n"
        "ÚLTIMO ANDAMENTO CONHECIDO:\n"
        + (json.dumps(andamento, ensure_ascii=False, indent=1, default=str)
           if andamento else
           "(nenhum andamento registrado — o processo pode não estar sendo "
           "monitorado, ou ainda não houve movimentação captada)")
    )
    r = _parecer(SYSTEM_CONTROLLER, conteudo)
    r["regra"] = "B"
    return r


# ══════════════════════════════════════════════════════════════════
#  Ponto de entrada
# ══════════════════════════════════════════════════════════════════
def validar(caso_id: str, tipo_peticao: str, usuario_email: str = "") -> dict:
    tipo = (tipo_peticao or "").strip()
    if not tipo:
        raise ValueError("Informe o tipo de petição.")

    regra_a = tipo.upper().replace(" ", "_") in INICIAIS
    r = validar_inicial(caso_id) if regra_a else validar_peca(caso_id, tipo)
    r["tipo_peticao"] = tipo

    try:
        get_db().table("validacoes_peticionamento").insert({
            "caso_id": caso_id, "tipo_peticao": tipo, "regra": r.get("regra"),
            "aprovado": r["aprovado"], "motivo": r.get("motivo"),
            "faltando": r.get("faltando") or [],
            "usuario_email": usuario_email or None,
        }).execute()
    except Exception:
        pass

    registrar_evento(caso_id, "PETICIONAMENTO_VALIDADO",
                     {"tipo": tipo, "regra": r.get("regra"),
                      "aprovado": r["aprovado"], "motivo": r.get("motivo")})
    return r


def registrar_override(caso_id: str, tipo_peticao: str, motivo_da_trava: str,
                       justificativa: str, usuario: dict, regra: str) -> dict:
    """Grava quem forçou, o que a trava dizia e por que decidiu seguir.

    Sem a justificativa, a auditoria responde "quem", mas não "por quê" — e
    é o "por quê" que se discute depois."""
    db = get_db()
    linha = {
        "caso_id": caso_id, "usuario_id": usuario.get("id"),
        "usuario_email": usuario.get("email"), "usuario_papel": usuario.get("papel"),
        "tipo_peticao": tipo_peticao, "motivo_da_trava": motivo_da_trava or "—",
        "justificativa": (justificativa or "").strip() or None, "regra": regra,
    }
    try:
        db.table("overrides_peticionamento").insert(linha).execute()
    except Exception:
        pass

    registrar_evento(caso_id, "PETICIONAMENTO_FORCADO", {
        "usuario": usuario.get("email"), "papel": usuario.get("papel"),
        "tipo": tipo_peticao, "trava": motivo_da_trava,
        "justificativa": justificativa,
    })
    # o override aparece no histórico do caso, não só numa tabela de log
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "CRM", "autor": "HUMANO",
            "conteudo": f"⚠ Peticionamento FORÇADO por {usuario.get('email')} "
                        f"({usuario.get('papel')}) — {tipo_peticao}.\n"
                        f"A trava apontava: {motivo_da_trava}\n"
                        + (f"Justificativa: {justificativa}" if justificativa
                           else "Sem justificativa informada."),
        }).execute()
    except Exception:
        pass
    return {"ok": True, "registrado_em": datetime.now(_tz.utc).isoformat()}
