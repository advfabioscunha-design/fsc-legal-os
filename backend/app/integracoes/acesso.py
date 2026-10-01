"""
Recuperação de acesso à conta do cliente.

O desenho segue o que é consenso em segurança de aplicação (OWASP
Forgot Password; NIST SP 800-63B) e o que a prática mostra:

  · O canal de recuperação é o e-mail, que já foi verificado no
    cadastro. Token de uso único, validade curta.
  · A resposta é a MESMA exista ou não a conta. Tela que diz "e-mail
    não cadastrado" vira consulta: dá para descobrir quem é cliente do
    escritório testando endereços.
  · Limite de tentativas por e-mail e por IP.
  · Toda troca de senha avisa o dono no e-mail e derruba as outras
    sessões — se não foi ele, ele fica sabendo enquanto dá tempo.
  · Nada de pergunta secreta. O NIST desaconselha desde 2017: nome da
    mãe e cidade natal estão em rede social.
  · Senha nunca viaja por e-mail.

Perder o acesso ao e-mail é outro problema, e não tem solução
automática segura — o único canal verificado se perdeu. Aqui vira
pedido para conferência humana (ver solicitacoes_acesso).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from ..core.db import get_db, registrar_evento
from ..core import dados as _dados

# Janela e teto do limite de tentativas. Números baixos de propósito:
# quem esqueceu a senha tenta uma vez, quem está varrendo tenta cem.
JANELA_MINUTOS = 60
MAX_POR_EMAIL = 5
MAX_POR_IP = 15


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def dentro_do_limite(email: str, ip: str | None) -> bool:
    """Conta as tentativas da última hora pela trilha de eventos.

    Usa a tabela de eventos em vez de uma tabela nova porque o volume é
    baixo e a trilha já existe — e um contador que ninguém consegue
    auditar depois é pior que contador nenhum."""
    db = get_db()
    desde = (_agora() - timedelta(minutes=JANELA_MINUTOS)).isoformat()
    try:
        recentes = db.table("eventos").select("payload") \
            .eq("tipo", "RECUPERACAO_SENHA").gte("criado_em", desde) \
            .limit(500).execute().data
    except Exception:
        return True          # falha no contador não pode travar quem precisa
    por_email = sum(1 for e in recentes
                    if _dados.como_dict(e.get("payload")).get("email") == email)
    por_ip = sum(1 for e in recentes
                 if ip and _dados.como_dict(e.get("payload")).get("ip") == ip)
    return por_email < MAX_POR_EMAIL and por_ip < MAX_POR_IP


def registrar_tentativa(email: str, ip: str | None) -> None:
    registrar_evento(None, "RECUPERACAO_SENHA", {"email": email, "ip": ip})


def avisar_senha_alterada(email: str, nome: str | None = None) -> bool:
    """Aviso no e-mail do dono. É o que transforma um acesso indevido em
    algo que a pessoa descobre no mesmo dia, e não meses depois."""
    from . import avisos
    quando = _agora().astimezone().strftime("%d/%m/%Y às %H:%M")
    texto = (
        f"Olá{', ' + nome.split()[0] if nome else ''}.\n\n"
        f"A senha de acesso à sua área na FC Advocacia foi alterada em "
        f"{quando}.\n\n"
        f"Se foi você, não precisa fazer nada.\n\n"
        f"Se NÃO foi você, entre em contato com o escritório agora mesmo "
        f"pelos canais oficiais — sua conta pode ter sido acessada por "
        f"outra pessoa e podemos bloqueá-la imediatamente."
    )
    html = (
        f"<p style='font-family:Arial,sans-serif;font-size:14px'>"
        f"Olá{', <b>' + nome.split()[0] + '</b>' if nome else ''}.</p>"
        f"<p style='font-family:Arial,sans-serif;font-size:14px'>A senha de "
        f"acesso à sua área na FC Advocacia foi alterada em <b>{quando}</b>.</p>"
        f"<p style='font-family:Arial,sans-serif;font-size:14px'>Se foi você, "
        f"não precisa fazer nada.</p>"
        f"<p style='font-family:Arial,sans-serif;font-size:14px;color:#a00'>"
        f"<b>Se não foi você</b>, fale com o escritório agora mesmo pelos "
        f"canais oficiais: sua conta pode ter sido acessada por outra pessoa "
        f"e podemos bloqueá-la imediatamente.</p>"
    )
    try:
        avisos.enviar_email(email, "Sua senha de acesso foi alterada", texto, html)
        return True
    except Exception as e:
        print(f"[acesso] aviso de senha não enviado para {email}: {e}")
        return False


# ── Perdeu o acesso ao e-mail ───────────────────────────────────
def pedir_troca_de_email(cpf: str, nascimento: str | None, email_novo: str,
                         ip: str | None = None) -> dict:
    """Abre o pedido. NÃO troca nada — só entra na fila do escritório.

    A data de nascimento não prova identidade; serve para separar quem
    realmente conhece o cadastro de quem está testando CPF. Quem prova é
    a ligação para o telefone já cadastrado."""
    from ..core.cpf import cpf_valido
    db = get_db()
    cpf_limpo = re.sub(r"\D", "", cpf or "")
    email_novo = (email_novo or "").strip().lower()

    if not cpf_valido(cpf_limpo):
        raise ValueError("CPF inválido — confira os números.")
    if "@" not in email_novo or "." not in email_novo.split("@")[-1]:
        raise ValueError("Informe um e-mail válido.")

    achado = db.table("clientes").select("id,nome,email,data_nascimento") \
        .eq("cpf_cnpj", cpf_limpo).limit(1).execute().data
    cliente = achado[0] if achado else None

    bate = None
    if cliente and nascimento:
        try:
            bate = (str(cliente.get("data_nascimento") or "")[:10]
                    == date.fromisoformat(nascimento[:10]).isoformat())
        except ValueError:
            bate = False

    if cliente:
        db.table("solicitacoes_acesso").insert({
            "cliente_id": cliente["id"],
            "cpf_informado": cpf_limpo[-4:],       # só o suficiente para conferir
            "nascimento_bate": bate,
            "email_atual": cliente.get("email"),
            "email_novo": email_novo,
            "ip": ip,
        }).execute()
        registrar_evento(None, "PEDIDO_TROCA_EMAIL", {
            "cliente_id": cliente["id"], "nascimento_bate": bate,
            "email_novo": email_novo,
        })
        # Avisa no e-mail antigo: se a conta ainda é acessível, o dono
        # fica sabendo que alguém está tentando mudá-la.
        if cliente.get("email"):
            try:
                from . import avisos
                avisos.enviar_email(
                    cliente["email"],
                    "Pedido de troca do e-mail de acesso",
                    "Alguém pediu para trocar o e-mail de acesso da sua conta "
                    f"na FC Advocacia para {email_novo}. O escritório vai "
                    "confirmar por telefone antes de fazer qualquer mudança. "
                    "Se não foi você, avise-nos imediatamente.",
                    "<p style='font-family:Arial;font-size:14px'>Alguém pediu "
                    f"para trocar o e-mail de acesso da sua conta para "
                    f"<b>{email_novo}</b>. O escritório vai confirmar por "
                    "telefone antes de mudar qualquer coisa.</p>"
                    "<p style='font-family:Arial;font-size:14px;color:#a00'>"
                    "Se não foi você, avise-nos imediatamente.</p>")
            except Exception:
                pass

    # Mesma resposta exista ou não o CPF.
    return {"ok": True, "mensagem":
            "Recebemos o pedido. Por segurança, o escritório vai confirmar sua "
            "identidade por telefone ou WhatsApp no número já cadastrado antes "
            "de liberar o novo e-mail. Em dia útil, isso costuma levar algumas "
            "horas."}


def listar_pedidos(status: str = "PENDENTE") -> list[dict]:
    return get_db().table("solicitacoes_acesso") \
        .select("*, clientes(nome,email,whatsapp,cpf_cnpj)") \
        .eq("status", status).order("criado_em", desc=True).limit(100).execute().data


def decidir(pedido_id: str, aprovar: bool, quem: str = "",
            observacao: str = "") -> dict:
    """O escritório decide depois de falar com a pessoa.

    Aprovar troca o e-mail no cadastro. O link para criar a nova senha
    sai pelo caminho normal de 'esqueci a senha', agora para o endereço
    novo — assim o token continua de uso único e curto, sem inventar um
    caminho paralelo."""
    db = get_db()
    achado = db.table("solicitacoes_acesso").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    if p["status"] != "PENDENTE":
        raise ValueError(f"Este pedido já foi {p['status'].lower()}.")

    agora = _agora().isoformat()
    if aprovar:
        db.table("clientes").update({"email": p["email_novo"]}) \
            .eq("id", p["cliente_id"]).execute()
    db.table("solicitacoes_acesso").update({
        "status": "APROVADA" if aprovar else "RECUSADA",
        "conferido_por": quem or None, "conferido_em": agora,
        "observacao": observacao or None,
    }).eq("id", pedido_id).execute()

    registrar_evento(None, "TROCA_EMAIL_DECIDIDA", {
        "pedido": pedido_id, "aprovada": aprovar, "por": quem,
        "cliente_id": p["cliente_id"],
    })
    return {"ok": True, "status": "APROVADA" if aprovar else "RECUSADA",
            "email": p["email_novo"] if aprovar else None,
            "proximo_passo": ("Peça ao cliente para usar 'Esqueci a senha' com o "
                              "e-mail novo." if aprovar else None)}
