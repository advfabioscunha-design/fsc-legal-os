"""QUEM É QUE ESTÁ FALANDO.

Um cliente antigo escreve do telefone da esposa, ou trocou de número, ou
nunca falou pelo WhatsApp e só conhece o escritório do processo que
corre há dois anos. O número não está no cadastro, e até aqui ele caía
na triagem como se fosse gente nova: o sistema abria um caso novo e o
agente respondia como se nunca o tivesse visto.

Este módulo é a porta de identificação. Ele recebe o que a pessoa
escreveu e tenta achar o cadastro e o caso.

A LINHA QUE NÃO SE ATRAVESSA

Andamento de processo é informação sigilosa, e quem escreve um nome num
WhatsApp não provou ser aquela pessoa. "Bom dia, sou o Fábio Silva
Cunha, como está meu processo?" é uma frase que qualquer um digita, e
responder a ela é entregar o caso de um cliente a um estranho.

Por isso há duas categorias de informação, e elas valem coisas bem
diferentes:

  IDENTIFICADOR FORTE — CPF, e-mail cadastrado, número do processo ou
  número de atendimento. São dados que a própria pessoa tem porque é a
  pessoa: o CPF é dela, o número do processo foi dado a ela, o
  protocolo saiu no e-mail dela. Com um destes, o andamento sai.

  PISTA — nome, ou o relato do que o caso trata. Serve para ENCONTRAR o
  cadastro, nunca para abrir. Com uma pista o agente diz que encontrou e
  pede um identificador forte para confirmar; não diz quantos casos
  existem, nem do que tratam, nem em que fase estão, porque isso já é
  informação.

A diferença parece burocrática e não é: é a diferença entre um
escritório que protege o cliente e um que entrega o processo para quem
souber o nome dele.

MAIS DE UM CASO

Identificado o cliente, se houver mais de um caso ele escolhe pelo
número do processo ou pelo número de atendimento. Aqui pode-se listar os
protocolos, porque a essa altura a pessoa já se identificou.
"""
from __future__ import annotations

import re

from ..core.db import get_db
from ..core.cpf import limpar as _limpar_cpf, cpf_valido

# ── O que dá para extrair de uma frase solta ─────────────────────
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Número de processo no padrão do CNJ, com ou sem pontuação.
_PROCESSO = re.compile(r"\d{7}[-.]?\d{2}[.]?\d{4}[.]?\d[.]?\d{2}[.]?\d{4}")
# Protocolo do escritório: FSC-2026-0001, FSC-C-2026-0009.
_PROTOCOLO = re.compile(r"\bFSC-[A-Z]?-?\d{4}-\d{3,6}\b", re.IGNORECASE)
# Sequência de 11 dígitos isolada, candidata a CPF.
_ONZE = re.compile(r"(?<!\d)(\d{3}\D?\d{3}\D?\d{3}\D?\d{2})(?!\d)")


def pistas(texto: str) -> dict:
    """O que a mensagem carrega, separado por força.

    O CPF só entra como forte se for VÁLIDO no dígito verificador: onze
    dígitos quaisquer podem ser um número de telefone digitado sem
    pontuação, e procurar cadastro por telefone achando que é CPF traz o
    cliente errado."""
    t = texto or ""
    achados: dict = {"email": None, "processo": None, "protocolo": None,
                     "cpf": None}

    m = _EMAIL.search(t)
    if m:
        achados["email"] = m.group(0).lower()

    m = _PROTOCOLO.search(t)
    if m:
        achados["protocolo"] = m.group(0).upper()

    m = _PROCESSO.search(t)
    if m:
        so_numero = re.sub(r"\D", "", m.group(0))
        if len(so_numero) == 20:
            achados["processo"] = so_numero

    for m in _ONZE.finditer(t):
        candidato = _limpar_cpf(m.group(1))
        if len(candidato) == 11 and cpf_valido(candidato):
            achados["cpf"] = candidato
            break

    achados["tem_forte"] = any(achados[k] for k in
                               ("email", "processo", "protocolo", "cpf"))
    return achados


# ── A busca ──────────────────────────────────────────────────────
def _casos_do_cliente(cliente_ids: list[str]) -> list[dict]:
    if not cliente_ids:
        return []
    try:
        return get_db().table("casos").select(
            "id,titulo,grupo,estado,numero_processo,numero_atendimento,"
            "tribunal,relato_inicial,atualizado_em,cliente_id"
        ).in_("cliente_id", cliente_ids) \
            .order("atualizado_em", desc=True).limit(20).execute().data or []
    except Exception as e:
        print(f"[identificacao] casos não lidos: {e}")
        return []


def por_identificador_forte(p: dict) -> dict:
    """Procura com o que prova quem a pessoa é. Abre o andamento."""
    db = get_db()
    clientes: list[dict] = []
    casos: list[dict] = []

    if p.get("processo"):
        try:
            casos = db.table("casos").select("*,clientes(id,nome)") \
                .eq("numero_processo", p["processo"]).limit(5).execute().data or []
        except Exception:
            casos = []
        if not casos:
            # o número pode estar gravado com pontuação
            try:
                casos = db.table("casos").select("*,clientes(id,nome)") \
                    .ilike("numero_processo", f"%{p['processo'][-8:]}%") \
                    .limit(5).execute().data or []
            except Exception:
                casos = []

    if not casos and p.get("protocolo"):
        try:
            casos = db.table("casos").select("*,clientes(id,nome)") \
                .ilike("numero_atendimento", p["protocolo"]) \
                .limit(5).execute().data or []
        except Exception:
            casos = []

    if casos:
        ids = {(c.get("clientes") or {}).get("id") or c.get("cliente_id")
               for c in casos}
        clientes = [{"id": i} for i in ids if i]
        return {"achou": True, "por": "processo" if p.get("processo")
                else "protocolo", "clientes": clientes, "casos": casos}

    coluna, valor = (None, None)
    if p.get("cpf"):
        coluna, valor = "cpf_cnpj", p["cpf"]
    elif p.get("email"):
        coluna, valor = "email", p["email"]
    if coluna:
        try:
            clientes = db.table("clientes").select("id,nome,email,cpf_cnpj") \
                .ilike(coluna, f"%{valor}%").limit(5).execute().data or []
        except Exception:
            clientes = []
        if clientes:
            casos = _casos_do_cliente([c["id"] for c in clientes])
            return {"achou": True, "por": coluna, "clientes": clientes,
                    "casos": casos}

    return {"achou": False, "clientes": [], "casos": []}


def por_pista(nome_ou_relato: str) -> dict:
    """Procura por nome ou pelo assunto. NÃO abre o andamento.

    Devolve só quantos cadastros batem, para o agente saber se vale
    pedir a confirmação. Nada do conteúdo sai daqui: nem o nome
    completo, nem o número do processo, nem a fase. Quem ainda não se
    identificou não recebe informação de caso nenhum, nem por tabela."""
    texto = (nome_ou_relato or "").strip()
    if len(texto) < 4:
        return {"candidatos": 0, "pode_abrir": False}

    db = get_db()
    encontrados: set[str] = set()

    # pelo nome, quando a frase parece conter um
    palavras = [w for w in re.split(r"[^\wÀ-ÿ]+", texto) if len(w) > 2]
    for w in palavras[:6]:
        try:
            r = db.table("clientes").select("id").ilike("nome", f"%{w}%") \
                .limit(10).execute().data or []
        except Exception:
            r = []
        for c in r:
            encontrados.add(c["id"])

    # pelo assunto, no relato e no título do caso
    try:
        r = db.table("casos").select("cliente_id") \
            .or_(f"relato_inicial.ilike.%{texto[:60]}%,"
                 f"titulo.ilike.%{texto[:60]}%") \
            .limit(10).execute().data or []
        for c in r:
            if c.get("cliente_id"):
                encontrados.add(c["cliente_id"])
    except Exception:
        pass

    return {"candidatos": len(encontrados), "pode_abrir": False}


def identificar(texto: str) -> dict:
    """A porta única. Devolve o que o agente pode dizer, e só isso.

    Três saídas, e cada uma pede uma conversa diferente:

      liberado   — identificador forte conferido, o andamento pode sair
      confirmar  — há cadastro parecido, falta a prova de quem é
      nao_achou  — nada bate; ou é cliente novo, ou escreveu errado
    """
    p = pistas(texto)

    if p["tem_forte"]:
        r = por_identificador_forte(p)
        if r["achou"]:
            casos = r["casos"]
            return {"situacao": "liberado", "por": r["por"],
                    "clientes": r["clientes"], "casos": casos,
                    "varios": len(casos) > 1,
                    "escolhas": [
                        {"protocolo": c.get("numero_atendimento") or "",
                         "processo": c.get("numero_processo") or "",
                         "titulo": c.get("titulo") or c.get("grupo") or ""}
                        for c in casos]}
        return {"situacao": "nao_achou", "por": "forte_sem_cadastro",
                "casos": [], "clientes": []}

    pista = por_pista(texto)
    if pista["candidatos"]:
        return {"situacao": "confirmar", "candidatos": pista["candidatos"],
                "casos": [], "clientes": []}
    return {"situacao": "nao_achou", "casos": [], "clientes": []}


# ── O andamento, em linguagem de cliente ─────────────────────────
_COMO_SE_EXPLICA = {
    "LEAD": "em análise inicial",
    "QUALIFICACAO": "em análise, entendendo os detalhes do seu caso",
    "PROPOSTA": "com a proposta apresentada, aguardando a sua decisão",
    "CONTRATO": "com o contrato enviado, aguardando a sua assinatura",
    "PAGAMENTO": "aguardando a confirmação do pagamento",
    "COLETA_DOCS": "na coleta dos documentos",
    "COLETA_PROVAS": "na reunião das provas",
    "ANALISE": "em análise técnica pelo escritório",
    "ATIVO": "em andamento no escritório",
    "AJUIZADO": "ajuizado, correndo na Justiça",
    "EM_EXECUCAO": "na fase de execução",
    "CONCLUIDO": "concluído",
    "ARQUIVADO": "arquivado",
    "CANCELADO": "encerrado",
    "INVIAVEL": "encerrado após a análise de viabilidade",
    "ESCALADO_HUMANO": "com o advogado, para uma análise pessoal",
}


def andamento(caso: dict) -> str:
    """Uma frase sobre onde o caso está, para o cliente ler.

    Fase e data, e nada mais. O que acontece entre uma fase e outra é
    trabalho interno, e contar bastidor vira promessa: o cliente ouve
    "a petição já está escrita" e entende "então protocola hoje"."""
    estado = str(caso.get("estado") or "").upper()
    frase = _COMO_SE_EXPLICA.get(estado, "em andamento")
    partes = []
    if caso.get("numero_atendimento"):
        partes.append(f"Atendimento {caso['numero_atendimento']}")
    if caso.get("numero_processo"):
        partes.append(f"processo {caso['numero_processo']}")
    cabeca = ", ".join(partes)
    return (f"{cabeca}: {frase}." if cabeca else f"O caso está {frase}.")
