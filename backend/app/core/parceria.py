"""
A SEGUNDA PORTA DO PARCEIRO — quais casos são dele.

O porteiro de `seguranca.py` decide se o parceiro pode CHAMAR a rota.
Este módulo decide se ele pode ver AQUELE caso. São coisas diferentes, e
é a segunda que impede o vazamento: sem ela, o parceiro chamaria a rota
dos casos dele passando o id do caso de outro.

A REGRA, EM UMA FRASE

O parceiro vê o caso quando existe parceria viva dele naquele caso, o
caso não está arquivado, e o administrador não bloqueou expressamente.

Por que arquivado some: o senhor pediu, e a razão é boa. Causa encerrada
e arquivada não é mais trabalho em curso — é acervo do escritório. O
parceiro recebeu o que lhe cabia; manter a pasta aberta para ele é
manter aberto o acesso a dado de cliente que já não o envolve. O
histórico financeiro dele continua visível, porque o que ele recebeu é
informação dele.

O BLOQUEIO VENCE A LIBERAÇÃO

Quando houver uma regra liberando e outra bloqueando o mesmo caso para a
mesma pessoa, vence o bloqueio. Em dúvida, o sistema esconde. É a única
direção de erro aceitável quando o que está em jogo é sigilo
profissional.
"""
from __future__ import annotations

from .db import get_db

# Causa encerrada some da vista do parceiro. ARQUIVADO é a situação que
# o escritório grava ao encerrar; CONCLUIDO aparece como fase em alguns
# fluxos antigos e entra junto para não deixar brecha.
SITUACOES_FORA_DA_VISTA = ("ARQUIVADO", "CONCLUIDO", "ENCERRADO")


def parceiro_do_login(auth_user_id: str) -> dict | None:
    """O cadastro de parceiro ligado a este login, se houver."""
    if not auth_user_id:
        return None
    try:
        return (get_db().table("parceiros").select("*")
                .eq("auth_user_id", auth_user_id)
                .limit(1).execute().data or [None])[0]
    except Exception:
        return None


def casos_do_parceiro(parceiro_id: str) -> list[str]:
    """Os ids dos casos que este parceiro pode enxergar agora.

    Lista vazia é resposta legítima: parceiro recém-cadastrado, ou cujas
    parcerias terminaram, não vê caso nenhum. Isso é o correto — e é
    diferente de erro, que levantaria exceção."""
    db = get_db()
    # Falha de leitura aqui também sobe: lista vazia por erro é
    # indistinguível de "ele não tem caso nenhum", e as duas levam a
    # telas iguais — só que uma esconde um defeito.
    vivas = (db.table("parcerias").select("caso_id")
             .eq("parceiro_id", parceiro_id)
             .is_("encerrada_em", "null").execute().data or [])
    ids = {p["caso_id"] for p in vivas if p.get("caso_id")}

    # O que o administrador liberou à mão (caso fora de parceria que ele
    # quis mostrar a este parceiro) entra; o que ele bloqueou sai.
    liberados, bloqueados = _regras_do_admin(parceiro_id=parceiro_id)
    ids |= liberados
    ids -= bloqueados
    if not ids:
        return []

    # Arquivado some. A consulta pede a situação em vez de confiar no
    # que estava gravado na parceria: quem arquiva o caso é o escritório,
    # e a parceria não fica sabendo.
    linhas = (db.table("casos").select("id,situacao")
              .in_("id", list(ids)).execute().data or [])
    return [c["id"] for c in linhas
            if (c.get("situacao") or "ATIVO") not in SITUACOES_FORA_DA_VISTA]


def pode_ver(parceiro_id: str, caso_id: str) -> bool:
    """A conferência de um caso só, usada em toda rota que recebe id."""
    return caso_id in set(casos_do_parceiro(parceiro_id))


def parceria_no_caso(parceiro_id: str, caso_id: str) -> dict | None:
    try:
        return (get_db().table("parcerias").select("*")
                .eq("parceiro_id", parceiro_id).eq("caso_id", caso_id)
                .is_("encerrada_em", "null")
                .limit(1).execute().data or [None])[0]
    except Exception:
        return None


def parceiros_do_caso(caso_id: str) -> list[dict]:
    """Quem divide este caso, para a tela do escritório e para o cálculo."""
    db = get_db()
    try:
        vivas = (db.table("parcerias").select("*")
                 .eq("caso_id", caso_id)
                 .is_("encerrada_em", "null").execute().data or [])
    except Exception:
        return []
    saida = []
    for p in vivas:
        quem = (db.table("parceiros").select(
                    "id,nome,oab_numero,oab_uf,email,whatsapp,pix_tipo,pix_chave")
                .eq("id", p["parceiro_id"]).maybe_single().execute().data or {})
        saida.append({**p, "parceiro": quem})
    return saida


# ── O QUE A EQUIPE VÊ, QUANDO O ADMIN RESTRINGE ─────────────────
#
# Membro da equipe vê tudo por padrão — essa é a natureza do trabalho.
# Mas há causa que não pode circular: o processo do próprio sócio, a
# causa de um familiar, o cliente que pediu reserva. Até aqui a única
# forma de impedir alguém de ver um caso era tirar a pessoa da equipe.

def casos_bloqueados_para(perfil_id: str) -> set[str]:
    _, bloqueados = _regras_do_admin(perfil_id=perfil_id)
    return bloqueados


def _regras_do_admin(perfil_id: str | None = None,
                     parceiro_id: str | None = None) -> tuple[set, set]:
    """Devolve (liberados, bloqueados) desta pessoa, ignorando revogados."""
    db = get_db()
    try:
        consulta = db.table("acessos_por_caso").select("caso_id,efeito") \
                     .is_("revogado_em", "null")
        if perfil_id:
            consulta = consulta.eq("perfil_id", perfil_id)
        elif parceiro_id:
            consulta = consulta.eq("parceiro_id", parceiro_id)
        else:
            return set(), set()
        linhas = consulta.execute().data or []
    except Exception as e:
        # AQUI NÃO SE PODE ENGOLIR ERRO
        #
        # Esta função devolvia (vazio, vazio) em qualquer falha. Parece
        # inofensivo — "sem regras extras" —, mas descartava justamente
        # os BLOQUEAR: timeout, tabela fora do ar ou erro de rede faziam
        # um caso expressamente escondido pelo administrador voltar a
        # aparecer. Falhar aberto na única regra que existe para esconder
        # causa sensível é o avesso do que ela serve.
        #
        # Agora a falha sobe. A rota responde 503, o parceiro vê "tente
        # de novo", e ninguém vê o que não devia. Não ver um caso por um
        # minuto é incômodo; ver o caso errado uma vez é quebra de
        # sigilo.
        raise RuntimeError(
            "Não foi possível conferir as regras de acesso aos casos. "
            f"Tente de novo em instantes. ({str(e)[:120]})")
    liberados = {l["caso_id"] for l in linhas if l.get("efeito") == "LIBERAR"}
    bloqueados = {l["caso_id"] for l in linhas if l.get("efeito") == "BLOQUEAR"}
    return liberados, bloqueados


# ── O DINHEIRO DO PARCEIRO ──────────────────────────────────────

def calcular_parte(percentual: float, honorarios_contratuais: float,
                   honorarios_sucumbenciais: float,
                   inclui_sucumbencia: bool = True) -> dict:
    """Quanto cabe ao parceiro, sobre o BRUTO.

    Sobre o bruto porque foi o combinado: o percentual incide sobre o
    honorário cheio, sem descontar despesa. É mais simples de explicar
    ao parceiro, e simplicidade em divisão de dinheiro vale mais do que
    exatidão contábil — o escritório absorve as despesas sozinho, e sabe
    disso ao combinar o percentual.

    A sucumbência entra com o MESMO percentual, também por combinação.
    `inclui_sucumbencia` existe para a parceria que decidir diferente,
    sem obrigar uma migração nova no dia em que isso acontecer."""
    pct = max(0.0, min(100.0, float(percentual or 0))) / 100.0
    base_c = float(honorarios_contratuais or 0)
    base_s = float(honorarios_sucumbenciais or 0) if inclui_sucumbencia else 0.0
    return {
        "base_contratual": round(base_c, 2),
        "base_sucumbencia": round(base_s, 2),
        "percentual": round(float(percentual or 0), 2),
        "valor_devido": round((base_c + base_s) * pct, 2),
    }


# ── DA PRESTAÇÃO DE CONTAS PARA A CONTA A PAGAR ─────────────────
#
# Fechar o caso com o cliente e lembrar de pagar o parceiro eram dois
# atos separados, e o segundo dependia da memória de alguém. Dívida que
# depende de memória é dívida que atrasa — e atraso com parceiro não
# custa juros, custa o parceiro.
#
# TRÊS CUIDADOS QUE NÃO SÃO OPCIONAIS
#
# 1. FALHA FECHADA. Se não der para ler as parcerias, isto levanta erro
#    e a prestação de contas não conclui. O contrário — seguir em frente
#    com a lista vazia — fecharia o caso sem a dívida do parceiro, e
#    ninguém descobriria: não há tela que mostre um repasse que nunca
#    foi criado. `parceiros_do_caso` devolve [] quando falha, e é por
#    isso que esta função não usa aquela.
#
# 2. UMA VEZ SÓ. Se já existe repasse desta prestação para esta
#    parceria, não cria outro. Prestação de contas é refeita (valor
#    corrigido, resultado reescrito), e cada refação viraria uma segunda
#    conta a pagar do mesmo dinheiro.
#
# 3. NADA A PAGAR NÃO É CONTA. Parceria com percentual zero, ou caso sem
#    honorário recebido, não gera lançamento — conta a pagar de R$ 0,00
#    só suja a lista de quem confere.

def provisionar_repasses(prestacao_id: str, caso_id: str,
                         honorarios_contratuais: float,
                         honorarios_sucumbenciais: float,
                         criado_por: str = "") -> list[dict]:
    """Cria a dívida com cada parceiro do caso: um `repasses_parceiro` e a
    conta a pagar correspondente em `fin_lancamentos`.

    Devolve a lista do que foi provisionado, para o escritório ver na
    hora o que passou a deve a quem."""
    from datetime import date

    db = get_db()
    # Sem try/except de propósito: ver cuidado 1 acima.
    vivas = (db.table("parcerias").select("*")
             .eq("caso_id", caso_id)
             .is_("encerrada_em", "null").execute().data or [])
    if not vivas:
        return []

    ja_feitos = {r.get("parceria_id") for r in (
        db.table("repasses_parceiro").select("parceria_id")
        .eq("prestacao_id", prestacao_id).execute().data or [])}

    hoje = date.today().isoformat()
    feitos: list[dict] = []

    for p in vivas:
        if p["id"] in ja_feitos:
            continue
        conta = calcular_parte(p.get("percentual"),
                              honorarios_contratuais, honorarios_sucumbenciais,
                              bool(p.get("inclui_sucumbencia", True)))
        if conta["valor_devido"] <= 0:
            continue

        quem = (db.table("parceiros").select("id,nome,pix_tipo,pix_chave,"
                                             "banco_nome,agencia,conta")
                .eq("id", p["parceiro_id"]).maybe_single().execute().data or {})
        nome = quem.get("nome") or "parceiro"
        numero = (db.table("casos").select("numero_atendimento,numero_processo")
                  .eq("id", caso_id).maybe_single().execute().data or {})
        ref = numero.get("numero_processo") or numero.get("numero_atendimento") or ""

        lanc = db.table("fin_lancamentos").insert({
            "tipo": "SAIDA", "categoria": "REPASSE_PARCEIRO",
            "descricao": f"Repasse a {nome} — {conta['percentual']:.2f}% "
                         f"do caso {ref}".strip(),
            "valor": conta["valor_devido"],
            "data": hoje, "vencimento": hoje,
            "caso_id": caso_id, "parceiro_id": p["parceiro_id"],
            "pessoa": nome, "origem": "REPASSE",
            "criado_por": criado_por or "sistema",
        }).execute().data[0]

        repasse = db.table("repasses_parceiro").insert({
            "prestacao_id": prestacao_id, "caso_id": caso_id,
            "parceiro_id": p["parceiro_id"], "parceria_id": p["id"],
            "base_contratual": conta["base_contratual"],
            "base_sucumbencia": conta["base_sucumbencia"],
            "percentual": conta["percentual"],
            "valor_devido": conta["valor_devido"],
            "lancamento_id": lanc["id"],
        }).execute().data[0]

        # Os dados de pagamento vão junto na resposta porque é exatamente
        # a hora em que alguém vai pagar: obrigar a abrir outra tela para
        # descobrir o PIX do parceiro é o que faz o repasse esperar.
        feitos.append({**repasse, "parceiro_nome": nome,
                       "pix_tipo": quem.get("pix_tipo"),
                       "pix_chave": quem.get("pix_chave"),
                       "banco_nome": quem.get("banco_nome"),
                       "agencia": quem.get("agencia"),
                       "conta": quem.get("conta"),
                       "falta_dados_de_pagamento": not (
                           quem.get("pix_chave") or quem.get("conta"))})

    if feitos:
        from .db import registrar_evento
        registrar_evento(caso_id, "REPASSES_PROVISIONADOS", {
            "quantos": len(feitos),
            "total": round(sum(float(f["valor_devido"]) for f in feitos), 2),
        })
    return feitos
