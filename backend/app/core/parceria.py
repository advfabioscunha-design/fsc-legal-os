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
SITUACOES_FORA_DA_VISTA = ("ARQUIVADO",)


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
    try:
        vivas = (db.table("parcerias").select("caso_id")
                 .eq("parceiro_id", parceiro_id)
                 .is_("encerrada_em", "null").execute().data or [])
    except Exception:
        return []
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
    try:
        linhas = (db.table("casos").select("id,situacao")
                  .in_("id", list(ids)).execute().data or [])
    except Exception:
        return []
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
    except Exception:
        # Tabela ausente (migração não aplicada) não pode travar o
        # sistema inteiro: sem regras, ninguém tem liberação nem
        # bloqueio extra, que é o estado anterior a esta migração.
        return set(), set()
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
