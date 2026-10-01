"""A PONTE ENTRE O WHATSAPP E A PLATAFORMA.

O cliente que escreve no WhatsApp vira cadastro com número e sem e-mail.
A plataforma, por outro lado, só conhece quem tem login, e procura o
cadastro pelo e-mail do login. Quem chegou pelo WhatsApp caía no vão
entre os dois: criava a senha, entrava, e encontrava a área vazia,
porque o sistema abria um cadastro novo ao lado do que já existia, e o
caso tinha ficado no antigo.

Este módulo é a ponte. Ele faz três coisas:

  gerar_codigo  — um código de uso único para aquele cadastro
  link          — o endereço que vai na mensagem do WhatsApp
  vincular      — amarra o login recém-criado ao cadastro que já existe

POR QUE CÓDIGO, E NÃO O NÚMERO DE TELEFONE

O link é mandado por WhatsApp e WhatsApp se encaminha. Se o link
carregasse o telefone, qualquer pessoa que recebesse o encaminhado
assumiria o cadastro. O código é usado uma vez e morre: o segundo a
clicar não entra, e o primeiro é quem estava com o telefone na mão.

O QUE ESTE MÓDULO NÃO FAZ

Não abre o caso sem senha. Quem clica no link vai para o cadastro, cria
e-mail e senha, e só então vê o andamento. Foi uma decisão do escritório,
e tem razão de ser: a área do cliente mostra documento, conversa e
valores, e isso não fica atrás de um link que circula em conversa.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

# Dez caracteres sem vogal e sem os pares que se confundem na tela do
# telefone (0/O, 1/I/l, 5/S, 2/Z). O cliente não digita isto, mas lê, e
# às vezes lê para outra pessoa.
_ALFABETO = "346789BCDFGHJKLMNPQRTVWXY"


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def gerar_codigo(cliente_id: str, forcar: bool = False) -> str | None:
    """Devolve o código de acesso do cadastro, criando um se não houver.

    Não gera para quem já tem login: esse cliente entra pela porta
    normal, e mandar um convite de cadastro para quem já é cadastrado é
    o tipo de mensagem que faz a pessoa achar que o escritório não sabe
    com quem está falando."""
    db = get_db()
    r = db.table("clientes").select("id,auth_user_id,email,codigo_acesso") \
        .eq("id", cliente_id).limit(1).execute().data
    if not r:
        return None
    c = r[0]
    if c.get("auth_user_id") and not forcar:
        return None
    if c.get("codigo_acesso") and not forcar:
        return str(c["codigo_acesso"])

    codigo = "".join(secrets.choice(_ALFABETO) for _ in range(10))
    try:
        db.table("clientes").update({
            "codigo_acesso": codigo, "codigo_acesso_em": _agora(),
            "codigo_usado_em": None,
        }).eq("id", cliente_id).execute()
    except Exception as e:
        print(f"[acesso] código não gravado: {e}")
        return None
    return codigo


def link(cliente_id: str, forcar: bool = False) -> str | None:
    """O endereço que vai na mensagem. None quando não cabe convite."""
    codigo = gerar_codigo(cliente_id, forcar)
    if not codigo:
        return None
    return f"{get_settings().app_url.rstrip('/')}/acompanhar/{codigo}"


def convite(codigo: str) -> dict:
    """O que a página mostra antes de o cliente criar a conta.

    Devolve só o primeiro nome. Nome inteiro, CPF ou número de caso numa
    página pública é dado de cliente exposto a quem tiver o endereço."""
    codigo = (codigo or "").strip().upper()
    if len(codigo) < 6:
        return {"valido": False, "motivo": "Código inválido."}
    r = get_db().table("clientes") \
        .select("id,nome,auth_user_id,codigo_usado_em") \
        .eq("codigo_acesso", codigo).limit(1).execute().data
    if not r:
        return {"valido": False, "motivo":
                "Este convite não existe mais. Peça um novo pelo WhatsApp."}
    c = r[0]
    if c.get("codigo_usado_em") or c.get("auth_user_id"):
        return {"valido": False, "ja_usado": True, "motivo":
                "Este convite já foi usado. Entre com o e-mail e a senha "
                "que você cadastrou."}
    primeiro = str(c.get("nome") or "").strip().split(" ")[0]
    return {"valido": True, "primeiro_nome": primeiro}


def vincular(codigo: str, auth_user_id: str, email: str) -> dict:
    """Amarra o login recém-criado ao cadastro que veio do WhatsApp.

    É aqui que o caso deixa de estar órfão. Depois desta linha, a busca
    normal da área do cliente encontra o cadastro pelo `auth_user_id`, e
    o cliente vê o que já existia em vez de uma tela vazia.

    O código é queimado na mesma operação. Convite que continua valendo
    depois de usado é convite que o segundo a receber o encaminhado
    também usa."""
    codigo = (codigo or "").strip().upper()
    if not codigo or not auth_user_id:
        raise ValueError("Convite ou login ausente.")

    db = get_db()
    r = db.table("clientes").select("id,nome,email,auth_user_id,codigo_usado_em") \
        .eq("codigo_acesso", codigo).limit(1).execute().data
    if not r:
        raise ValueError("Este convite não existe mais. Peça um novo pelo "
                         "WhatsApp.")
    c = r[0]
    if c.get("codigo_usado_em") or c.get("auth_user_id"):
        raise ValueError("Este convite já foi usado. Entre com o e-mail e a "
                         "senha que você cadastrou.")

    campos = {"auth_user_id": auth_user_id, "codigo_acesso": None,
              "codigo_usado_em": _agora(), "atualizado_em": _agora()}
    # O e-mail do login entra no cadastro quando ele não tinha nenhum. Se
    # já tinha, não se sobrescreve: pode ser o e-mail que o escritório
    # usa para falar com ele, e trocar isso em silêncio desvia o aviso
    # de uma audiência para um endereço que ninguém combinou.
    if email and not (c.get("email") or "").strip():
        campos["email"] = email.strip().lower()

    db.table("clientes").update(campos).eq("id", c["id"]).execute()
    try:
        db.table("perfis").update({"cliente_id": c["id"]}) \
          .eq("id", auth_user_id).execute()
    except Exception:
        pass

    registrar_evento(None, "CLIENTE_ASSUMIU_CADASTRO_DO_WHATSAPP",
                     {"cliente_id": c["id"], "email": email})
    return {"ok": True, "cliente_id": c["id"],
            "nome": c.get("nome") or "", "casos": _quantos_casos(c["id"])}


def _quantos_casos(cliente_id: str) -> int:
    try:
        r = get_db().table("casos").select("id") \
            .eq("cliente_id", cliente_id).execute().data or []
        return len(r)
    except Exception:
        return 0


# ── O convite escrito, do jeito que ele sai no WhatsApp ──────────
def frase_do_convite(cliente_id: str, numero_atendimento: str = "") -> str:
    """O trecho que o agente acrescenta à resposta. Vazio quando não cabe.

    Fica curto de propósito: vai no fim de uma resposta que já disse o
    que importava, e mensagem de WhatsApp que vira parágrafo de bula não
    se lê. O endereço sai em linha própria porque o WhatsApp só
    transforma em link o que está separado."""
    endereco = link(cliente_id)
    if not endereco:
        return ""
    protocolo = (f" O seu número de atendimento é {numero_atendimento}."
                 if numero_atendimento else "")
    return ("\n\nVocê também pode acompanhar tudo pela plataforma do "
            "escritório, com os documentos e o andamento no mesmo lugar."
            + protocolo
            + " Crie o seu acesso por aqui, é uma vez só:\n" + endereco)
