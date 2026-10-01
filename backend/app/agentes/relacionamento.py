"""O VÍNCULO COM QUEM JÁ FOI CLIENTE.

Felicitação de aniversário e lembrança em data importante. É pouca
coisa, e é justamente por ser pouca que precisa ser bem feita: uma
mensagem repetida, ou mandada para quem pediu para parar, estraga mais
relação do que o silêncio teria estragado.

AS QUATRO TRAVAS, E POR QUE CADA UMA EXISTE

  NÃO ENVIA DUAS VEZES. A rotina roda todo dia às 9h, e o botão de rodar
  à mão existe. Sem registro do que já saiu, servidor reiniciado ou
  clique repetido mandavam dois "feliz aniversário" no mesmo dia, e
  nada denuncia mais uma máquina do que isso.

  RESPEITA QUEM PEDIU PARA PARAR. Pedido de descadastro ignorado vira
  reclamação na OAB e bloqueio do número na Meta, as duas coisas ao
  mesmo tempo.

  SEPARA CORTESIA DE COMUNICAÇÃO DE MASSA. Parabéns a quem é cliente
  cabe no legítimo interesse: a pessoa confiou um processo ao
  escritório. Informativo periódico é outra natureza, e por isso só sai
  para quem pediu, com o campo próprio ligado.

  NÃO FALA DE PROCESSO. Felicitação é felicitação. Misturar "e o seu
  processo está andando" numa mensagem de aniversário transforma
  cortesia em cobrança, e é o tipo de coisa que faz a pessoa associar o
  escritório a uma preocupação em vez de a um cuidado.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..core.db import get_db, registrar_evento

# Horário de Rondônia e Santa Catarina em termos práticos: o escritório
# atende nos dois, e o aniversário é do dia de quem recebe, não do UTC.
# Sem isto, quem faz aniversário dia 10 recebia o parabéns dia 9 às 21h.
_FUSO = timezone(timedelta(hours=-4))

MSG_ANIVERSARIO = (
    "Feliz aniversário, {nome}! Toda a equipe da FC Advocacia deseja um "
    "dia muito bom para você, com saúde e tranquilidade. É uma satisfação "
    "cuidar dos seus direitos.\n\nDr. Fábio Cunha e equipe"
)


def _hoje() -> datetime:
    return datetime.now(_FUSO)


def _ja_foi(cliente_id: str, tipo: str, referencia: str) -> bool:
    try:
        r = get_db().table("relacionamento_envios").select("id") \
            .eq("cliente_id", cliente_id).eq("tipo", tipo) \
            .eq("referencia", referencia).limit(1).execute().data
        return bool(r)
    except Exception as e:
        # Tabela ausente ou banco fora: NÃO envia. Na dúvida entre
        # repetir e não mandar, não mandar é o erro barato.
        print(f"[relacionamento] não consegui conferir o histórico: {e}")
        return True


def _registrar(cliente_id: str, tipo: str, referencia: str,
               texto: str, erro: str = "") -> None:
    try:
        get_db().table("relacionamento_envios").insert({
            "cliente_id": cliente_id, "tipo": tipo, "referencia": referencia,
            "canal": "WHATSAPP", "texto": texto[:1000],
            "erro": erro[:300] or None,
        }).execute()
    except Exception as e:
        print(f"[relacionamento] envio não registrado: {e}")


def _pode_receber(c: dict, tipo: str) -> tuple[bool, str]:
    """Quem recebe, e o motivo de quem não recebe.

    O motivo volta para a tela do escritório: lista de 400 clientes com
    12 envios e sem explicação faz qualquer um achar que quebrou."""
    if c.get("descadastrado_em"):
        return False, "pediu para não receber"
    if not c.get("whatsapp"):
        return False, "sem WhatsApp no cadastro"
    if tipo == "ANIVERSARIO" and c.get("aceita_felicitacoes") is False:
        return False, "não aceita felicitações"
    if tipo == "INFORMATIVO" and not c.get("aceita_informativos"):
        return False, "não autorizou informativos"
    return True, ""


def aniversariantes_de_hoje() -> list[dict]:
    """Quem faz aniversário hoje, com o motivo de quem não vai receber.

    Serve à tela do escritório, que mostra a lista ANTES de qualquer
    disparo: ver quem vai receber é o que permite corrigir um cadastro
    errado antes de a mensagem sair, e não depois."""
    hoje = _hoje().strftime("%m-%d")
    ano = _hoje().strftime("%Y")
    try:
        clientes = get_db().table("clientes").select(
            "id,nome,whatsapp,data_nascimento,aceita_felicitacoes,"
            "aceita_informativos,descadastrado_em"
        ).not_.is_("data_nascimento", "null").execute().data or []
    except Exception as e:
        print(f"[relacionamento] base não lida: {e}")
        return []

    saida = []
    for c in clientes:
        dn = str(c.get("data_nascimento") or "")
        if len(dn) < 10 or dn[5:10] != hoje:
            continue
        pode, motivo = _pode_receber(c, "ANIVERSARIO")
        saida.append({
            "id": c["id"], "nome": c.get("nome") or "",
            "whatsapp": c.get("whatsapp") or "",
            "vai_receber": pode and not _ja_foi(c["id"], "ANIVERSARIO", ano),
            "motivo": motivo or ("já enviado hoje"
                                 if _ja_foi(c["id"], "ANIVERSARIO", ano)
                                 else ""),
        })
    return saida


def parabenizar_aniversariantes() -> dict:
    """A rotina das 9h. Idempotente: rodar de novo não manda de novo."""
    ano = _hoje().strftime("%Y")
    lista = aniversariantes_de_hoje()
    from ..integracoes.whatsapp import _enviar

    enviados, pulados = 0, []
    for a in lista:
        if not a["vai_receber"]:
            pulados.append({"nome": a["nome"], "motivo": a["motivo"]})
            continue
        primeiro = (a["nome"] or "").strip().split(" ")[0] or "tudo bem"
        texto = MSG_ANIVERSARIO.format(nome=primeiro)
        # O registro vem ANTES do envio. Falhando o envio, fica a linha
        # com o erro e o cliente não recebe duas tentativas; falhando o
        # registro depois do envio, ele receberia de novo amanhã.
        _registrar(a["id"], "ANIVERSARIO", ano, texto)
        try:
            _enviar(a["whatsapp"], texto)
            enviados += 1
        except Exception as e:
            print(f"[relacionamento] parabéns não saiu para {a['nome']}: {e}")
            try:
                get_db().table("relacionamento_envios").update(
                    {"erro": str(e)[:300]}
                ).eq("cliente_id", a["id"]).eq("tipo", "ANIVERSARIO") \
                 .eq("referencia", ano).execute()
            except Exception:
                pass

    registrar_evento(None, "ANIVERSARIOS_ENVIADOS",
                     {"total": enviados, "pulados": len(pulados),
                      "data": _hoje().strftime("%Y-%m-%d")})
    return {"enviados": enviados, "pulados": pulados,
            "aniversariantes": len(lista)}


def descadastrar(cliente_id: str, motivo: str = "") -> dict:
    """O cliente pediu para não receber mais. Vale para tudo."""
    agora = datetime.now(timezone.utc).isoformat()
    get_db().table("clientes").update({
        "descadastrado_em": agora,
        "descadastro_motivo": (motivo or "pedido do cliente")[:300],
        "aceita_felicitacoes": False, "aceita_informativos": False,
        "atualizado_em": agora,
    }).eq("id", cliente_id).execute()
    registrar_evento(None, "RELACIONAMENTO_DESCADASTRO",
                     {"cliente_id": cliente_id, "motivo": motivo})
    return {"ok": True}


def religar(cliente_id: str, origem: str = "") -> dict:
    """O cliente voltou a aceitar. Guarda de onde veio a autorização."""
    agora = datetime.now(timezone.utc).isoformat()
    get_db().table("clientes").update({
        "descadastrado_em": None, "descadastro_motivo": None,
        "aceita_felicitacoes": True,
        "origem_consentimento": (origem or "pedido do cliente")[:200],
        "consentimento_em": agora, "atualizado_em": agora,
    }).eq("id", cliente_id).execute()
    return {"ok": True}
