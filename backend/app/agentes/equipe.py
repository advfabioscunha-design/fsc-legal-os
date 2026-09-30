"""
Quem entra para a equipe, e como.

Antes disto não havia caminho nenhum: para um assessor começar a
trabalhar era preciso criar o usuário na mão no painel do Supabase,
escrever a linha em membros_equipe e mudar o papel direto no banco.
Três passos fora da plataforma, feitos por quem tem a chave do projeto,
e nenhum deles registrado como decisão de alguém.

O RITO
------
1. Alguém da equipe convida, escolhendo o nível.
2. A pessoa recebe um e-mail de boas-vindas com um link de uso único.
3. Ela abre o link, lê o que está sendo convidada a fazer, e cria a
   própria senha. O escritório nunca vê essa senha, nem escolhe uma
   provisória: senha provisória enviada por e-mail é senha publicada.
4. Recebe a confirmação, com o endereço de acesso, e entra.

DOIS CONCEITOS QUE NÃO SE MISTURAM
----------------------------------
  papel   o que o sistema pergunta para deixar alguém entrar numa tela.
          CLIENTE, OPERADOR ou ADMIN. É técnico.
  nível   o que a pessoa faz no escritório. Advogado, assessor e
          estagiário são todos OPERADOR hoje, e é justamente por isso
          que o sistema não consegue tratá-los de forma diferente.
          Guardar a função agora é o que permite, depois, dizer que
          estagiário não peticiona sozinho, sem refazer cadastro nenhum.

ADMINISTRADOR NÃO SE CONVIDA
----------------------------
Link de convite é encaminhado por engano, fica num print, sobra numa
caixa de e-mail antiga. Se esse link criar um administrador, cria junto
o poder de excluir pedido e de forçar peticionamento. Convite nasce
sempre em nível de trabalho; virar administrador é ato de quem já é,
feito dentro da plataforma e gravado com data, hora e autor.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

DIAS_DE_VALIDADE = 7


# ── Os níveis ───────────────────────────────────────────────────
#
# Quatro, e cada um existe porque descreve uma pessoa real do
# escritório. `papel` é o que o sistema usa; `convidavel` diz se o nível
# pode sair de um link de convite.
NIVEIS: dict[str, dict] = {
    "ADMINISTRADOR": {
        "nome": "Administrador",
        "papel": "ADMIN",
        "convidavel": False,
        "resumo": "Acesso a tudo, inclusive ao que não tem volta.",
        "pode": [
            "Tudo o que o advogado faz",
            "Excluir pedidos e arquivos",
            "Forçar peticionamento quando a trava apontar problema",
            "Convidar, promover e desligar membros da equipe",
        ],
    },
    "ADVOGADO": {
        "nome": "Advogado",
        "papel": "OPERADOR",
        "convidavel": True,
        "resumo": "Responde pelo conteúdo jurídico e aprova o que sai do escritório.",
        "pode": [
            "Todas as telas de caso, prazo, agenda e contratos",
            "Aprovar minuta e liberar documento ao cliente",
            "Peticionar",
            "Ver e responder proposta de cliente",
        ],
    },
    "ASSESSOR": {
        "nome": "Assessor",
        "papel": "OPERADOR",
        "convidavel": True,
        "resumo": "Toca a esteira do dia a dia, sem a palavra final.",
        "pode": [
            "Triagem, produção, prazos, agenda e tarefas",
            "Redigir e revisar minuta",
            "Falar com o cliente pela plataforma",
        ],
        "nao_pode": [
            "Forçar peticionamento com a trava acionada",
            "Excluir pedido pago",
        ],
    },
    "ESTAGIARIO": {
        "nome": "Estagiário",
        "papel": "OPERADOR",
        "convidavel": True,
        "resumo": "Aprende operando, com a conferência de alguém acima.",
        "pode": [
            "Consultar casos, prazos e agenda",
            "Preparar minuta e organizar documentos",
            "Registrar andamento e anotação",
        ],
        "nao_pode": [
            "Forçar peticionamento com a trava acionada",
            "Excluir pedido pago",
        ],
    },
}


def niveis_para_convite() -> list[dict]:
    """O que a tela mostra na hora de convidar.

    O administrador aparece na lista, marcado como não convidável, de
    propósito: esconder o nível faria parecer que ele não existe, e a
    pessoa procuraria onde não há. Melhor mostrar e dizer por que não."""
    return [{"id": k, **v} for k, v in NIVEIS.items()]


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _papel_do_nivel(nivel: str) -> str:
    return (NIVEIS.get(nivel) or {}).get("papel", "OPERADOR")


# ══════════════════════════════════════════════════════════════════
# CONVIDAR
# ══════════════════════════════════════════════════════════════════

def convidar(nome: str, email: str, nivel: str = "ASSESSOR",
             especialidades: list[str] | None = None, telefone: str = "",
             quem: str = "") -> dict:
    """Cria o membro, o convite e manda o e-mail de boas-vindas."""
    nome = (nome or "").strip()
    email = (email or "").strip().lower()
    nivel = (nivel or "ASSESSOR").upper()

    if len(nome) < 3:
        raise ValueError("Informe o nome completo da pessoa.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Esse e-mail não parece válido.")
    if nivel not in NIVEIS:
        raise ValueError("Nível de acesso desconhecido.")
    if not NIVEIS[nivel]["convidavel"]:
        raise ValueError(
            "Administrador não se convida por link. Convide em outro nível "
            "e promova depois, dentro da plataforma.")

    db = get_db()

    # Já é da casa? Então não é convite, é convite repetido.
    ja = db.table("perfis").select("id,papel,nome").eq("email", email) \
        .limit(1).execute().data
    if ja and ja[0].get("papel") in ("OPERADOR", "ADMIN"):
        raise ValueError(f"{ja[0].get('nome') or email} já tem acesso à plataforma.")

    aberto = db.table("convites_equipe").select("id,criado_em") \
        .eq("email", email).eq("status", "PENDENTE").limit(1).execute().data
    if aberto:
        raise ValueError(
            "Já existe um convite em aberto para esse e-mail. Reenvie o "
            "convite existente ou cancele antes de criar outro.")

    # O membro nasce agora, antes do aceite. Não é adiantamento: o
    # escritório precisa poder atribuir prazo e tarefa a quem começa
    # segunda-feira, e não só depois que a pessoa clicou no link.
    membro = db.table("membros_equipe").insert({
        "nome": nome, "email": email, "nivel": nivel,
        "especialidades": especialidades or [],
        "lider": nivel in ("ADMINISTRADOR", "ADVOGADO"),
        "ativo": True, "convidado_por": quem or None,
    }).execute().data[0]

    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(days=DIAS_DE_VALIDADE)
    convite = db.table("convites_equipe").insert({
        "nome": nome, "email": email, "nivel": nivel,
        "especialidades": especialidades or [], "telefone": telefone or None,
        "token": token, "expira_em": expira.isoformat(),
        "convidado_por": quem or None, "membro_id": membro["id"],
    }).execute().data[0]

    enviado = _mandar_boas_vindas(convite)
    if enviado:
        db.table("convites_equipe").update({"enviado_em": _agora()}) \
            .eq("id", convite["id"]).execute()

    registrar_evento(None, "EQUIPE_CONVIDADA",
                     {"convite": convite["id"], "email": email,
                      "nivel": nivel, "quem": quem, "email_enviado": enviado})
    return {"ok": True, "convite": convite["id"], "membro": membro["id"],
            "email_enviado": enviado, "link": _link(token)}


def _link(token: str) -> str:
    s = get_settings()
    return f"{s.app_url.rstrip('/')}/convite/{token}"


def _mandar_boas_vindas(convite: dict) -> bool:
    """A carta que abre a porta.

    Não é um e-mail de sistema. Quem recebe está decidindo onde vai
    passar os próximos anos, e a primeira coisa que o escritório diz
    deveria falar do trabalho, não do botão."""
    n = NIVEIS.get(convite["nivel"], {})
    primeiro = (convite["nome"] or "").split(" ")[0]
    url = _link(convite["token"])

    linhas = [
        f"{primeiro}, seja bem-vindo à FC Advocacia.",
        "",
        "Este convite não é para preencher uma vaga. O escritório trabalha "
        "com gente que chegou depois de ter sido cobrada a mais, ter tido a "
        "conta bloqueada, ter comprado um imóvel que não saiu do papel. "
        "Quase sempre é a primeira vez que alguém senta e explica a elas o "
        "que está acontecendo. Esse alguém passa a ser você.",
        "",
        "A advocacia que se faz aqui é digital, e isso não quer dizer "
        "distante: quer dizer que o cliente acompanha o próprio caso, "
        "recebe resposta no mesmo dia e sabe por onde anda o dinheiro dele. "
        "Pouca gente no país trabalha assim. Você está entrando num "
        "escritório que está construindo esse jeito, e o que você fizer "
        "nos próximos meses fica: nas pessoas que você atender e no "
        "escritório que vai existir depois de nós.",
        "",
        f"Sua função aqui é de {n.get('nome', convite['nivel']).lower()}. "
        f"{n.get('resumo', '')}",
    ]
    if n.get("pode"):
        linhas += ["", "O que você vai poder fazer na plataforma:"]
        linhas += [f"  - {p}" for p in n["pode"]]
    linhas += [
        "",
        "Para começar, crie a sua senha de acesso:",
        url,
        "",
        f"O link vale por {DIAS_DE_VALIDADE} dias e só funciona uma vez. "
        "Ninguém no escritório vê a senha que você escolher.",
        "",
        "Até já.",
        "Dr. Fábio Cunha, OAB/RO 10.849",
    ]
    texto = "\n".join(linhas)

    try:
        from ..integracoes import avisos
        avisos.enviar_email(
            convite["email"],
            f"{primeiro}, bem-vindo à equipe da FC Advocacia",
            texto,
            texto.replace("\n", "<br>").replace(
                url, f'<a href="{url}">{url}</a>'))
        return True
    except Exception as e:
        print(f"[equipe] convite não enviado por e-mail: {e}")
        return False


def reenviar(convite_id: str, quem: str = "") -> dict:
    """Mesmo convite, token novo.

    Reenviar com o token antigo deixaria dois links vivos, e o segundo
    sempre parece o certo para quem recebe. O prazo também recomeça: o
    motivo de reenviar costuma ser que o primeiro venceu."""
    db = get_db()
    r = db.table("convites_equipe").select("*").eq("id", convite_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Convite não encontrado.")
    c = r[0]
    if c["status"] not in ("PENDENTE", "EXPIRADO"):
        raise ValueError("Este convite já foi aceito ou cancelado.")

    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(days=DIAS_DE_VALIDADE)
    db.table("convites_equipe").update({
        "token": token, "expira_em": expira.isoformat(),
        "status": "PENDENTE", "reenviado_em": _agora(),
    }).eq("id", convite_id).execute()

    c["token"] = token
    enviado = _mandar_boas_vindas(c)
    registrar_evento(None, "EQUIPE_CONVITE_REENVIADO",
                     {"convite": convite_id, "quem": quem, "enviado": enviado})
    return {"ok": True, "email_enviado": enviado, "link": _link(token)}


def cancelar(convite_id: str, quem: str = "", motivo: str = "") -> dict:
    db = get_db()
    r = db.table("convites_equipe").select("status,membro_id,email") \
        .eq("id", convite_id).limit(1).execute().data
    if not r:
        raise ValueError("Convite não encontrado.")
    if r[0]["status"] == "ACEITO":
        raise ValueError("Este convite já foi aceito. Desligue o membro pela lista.")

    db.table("convites_equipe").update({
        "status": "CANCELADO", "observacao": (motivo or "")[:300] or None,
    }).eq("id", convite_id).execute()

    # O membro criado junto com o convite some também: sem aceite, ele
    # nunca existiu de fato, e membro fantasma na lista de responsáveis
    # é tarefa atribuída a ninguém.
    if r[0].get("membro_id"):
        db.table("membros_equipe").update({"ativo": False}) \
            .eq("id", r[0]["membro_id"]).execute()

    registrar_evento(None, "EQUIPE_CONVITE_CANCELADO",
                     {"convite": convite_id, "quem": quem, "motivo": motivo})
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════
# ACEITAR
# ══════════════════════════════════════════════════════════════════

def ver_convite(token: str) -> dict:
    """O que a página pública mostra antes de a pessoa criar a senha.

    Devolve só o necessário para ela se reconhecer no convite. Nada de
    lista de equipe, nada de e-mail de terceiros: esta rota é aberta,
    basta ter o link."""
    db = get_db()
    r = db.table("convites_equipe").select("*").eq("token", token) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Convite não encontrado. Confira o link do e-mail.")
    c = r[0]

    if c["status"] == "ACEITO":
        raise ValueError("Este convite já foi usado. Entre com o seu e-mail e senha.")
    if c["status"] == "CANCELADO":
        raise ValueError("Este convite foi cancelado pelo escritório.")
    if datetime.fromisoformat(c["expira_em"]) < datetime.now(timezone.utc):
        db.table("convites_equipe").update({"status": "EXPIRADO"}) \
            .eq("id", c["id"]).execute()
        raise ValueError(
            "Este convite venceu. Peça ao escritório para reenviar.")

    n = NIVEIS.get(c["nivel"], {})
    return {
        "nome": c["nome"], "email": c["email"], "nivel": c["nivel"],
        "nivel_nome": n.get("nome", c["nivel"]),
        "resumo": n.get("resumo", ""), "pode": n.get("pode", []),
        "expira_em": c["expira_em"],
    }


def aceitar(token: str, senha: str, ip: str | None = None) -> dict:
    """Cria a conta, liga tudo e devolve a confirmação.

    A senha vem da pessoa e vai direto para o Supabase. O escritório não
    escolhe senha provisória e não guarda a definitiva: senha que o
    escritório conhece é senha que o escritório responde por."""
    dados = ver_convite(token)          # revalida prazo, status e existência
    # SEIS, E NÃO OITO NEM QUATRO
    #
    # Oito afastava gente sem ganho real para um painel que não guarda
    # dinheiro. Quatro seria melhor ainda para a vida de quem usa, mas
    # o Supabase Auth recusa qualquer valor abaixo de seis, e validar
    # aqui um limite que o provedor rejeita depois só produz erro
    # confuso na tela. Seis é o piso possível.
    if len(senha or "") < 6:
        raise ValueError("A senha precisa de pelo menos 6 caracteres.")

    db = get_db()
    c = db.table("convites_equipe").select("*").eq("token", token) \
        .limit(1).execute().data[0]

    try:
        criado = db.auth.admin.create_user({
            "email": c["email"], "password": senha,
            "email_confirm": True,      # o convite já provou o e-mail
            "user_metadata": {"nome": c["nome"]},
        })
        uid = criado.user.id
    except Exception as e:
        texto = str(e).lower()
        if "already" in texto or "registered" in texto or "exists" in texto:
            raise ValueError(
                "Já existe uma conta com esse e-mail. Entre com a sua senha "
                "ou use 'esqueci a senha'.")
        raise ValueError(f"Não foi possível criar o acesso: {e}")

    papel = _papel_do_nivel(c["nivel"])
    db.table("perfis").update({
        "papel": papel, "nivel": c["nivel"], "nome": c["nome"],
        "email": c["email"],
    }).eq("id", uid).execute()

    if c.get("membro_id"):
        db.table("membros_equipe").update({
            "perfil_id": uid, "entrou_em": _agora(), "ativo": True,
        }).eq("id", c["membro_id"]).execute()

    db.table("convites_equipe").update({
        "status": "ACEITO", "aceito_em": _agora(),
        "aceito_ip": (ip or "")[:60] or None, "perfil_id": uid,
    }).eq("id", c["id"]).execute()

    _mandar_confirmacao(c)
    registrar_evento(None, "EQUIPE_CONVITE_ACEITO",
                     {"convite": c["id"], "perfil": uid,
                      "nivel": c["nivel"], "papel": papel})

    s = get_settings()
    return {
        "ok": True,
        "nome": c["nome"], "email": c["email"],
        "nivel_nome": dados["nivel_nome"],
        "entrar": f"{s.app_url.rstrip('/')}/entrar?next=/inicio",
    }


def _mandar_confirmacao(convite: dict) -> None:
    s = get_settings()
    url = f"{s.app_url.rstrip('/')}/entrar?next=/inicio"
    primeiro = (convite["nome"] or "").split(" ")[0]
    n = NIVEIS.get(convite["nivel"], {})
    texto = "\n".join([
        f"Pronto, {primeiro}. Seu cadastro está concluído.",
        "",
        f"E-mail de acesso: {convite['email']}",
        f"Função: {n.get('nome', convite['nivel'])}",
        "A senha é a que você acabou de criar. Ninguém no escritório a vê.",
        "",
        "Entre pela plataforma:",
        url,
        "",
        "No primeiro acesso você verá a tela de Início, com os prazos e as "
        "tarefas do dia. Nos próximos dias alguém da equipe vai fazer a sua "
        "integração, apresentar os documentos do escritório e acompanhar os "
        "seus primeiros atendimentos.",
        "",
        "Bom trabalho.",
        "Dr. Fábio Cunha, OAB/RO 10.849",
    ])
    try:
        from ..integracoes import avisos
        avisos.enviar_email(
            convite["email"], "Seu acesso à plataforma está pronto",
            texto,
            texto.replace("\n", "<br>").replace(url, f'<a href="{url}">{url}</a>'))
    except Exception as e:
        print(f"[equipe] confirmação não enviada: {e}")


# ══════════════════════════════════════════════════════════════════
# A LISTA, E O QUE SE FAZ COM ELA
# ══════════════════════════════════════════════════════════════════

def listar() -> dict:
    """Quem está na equipe e quem foi convidado e ainda não entrou."""
    db = get_db()
    membros = db.table("membros_equipe") \
        .select("id,nome,email,nivel,lider,ativo,especialidades,perfil_id,entrou_em,criado_em") \
        .order("nome").limit(300).execute().data or []
    convites = db.table("convites_equipe") \
        .select("id,nome,email,nivel,status,criado_em,expira_em,enviado_em,convidado_por") \
        .in_("status", ["PENDENTE", "EXPIRADO"]) \
        .order("criado_em", desc=True).limit(100).execute().data or []

    agora = datetime.now(timezone.utc)
    for c in convites:
        if c["status"] == "PENDENTE" and \
                datetime.fromisoformat(c["expira_em"]) < agora:
            c["status"] = "EXPIRADO"

    for m in membros:
        m["nivel_nome"] = (NIVEIS.get(m.get("nivel") or "") or {}).get(
            "nome", m.get("nivel") or "")
        m["aguardando"] = not m.get("perfil_id")

    return {"membros": membros, "convites": convites,
            "niveis": niveis_para_convite()}


def mudar_nivel(perfil_id: str, nivel: str, quem: str = "",
                motivo: str = "") -> dict:
    """Promove ou rebaixa, com o porquê gravado.

    É por aqui que alguém vira administrador, e só por aqui: quem faz a
    mudança está logado, tem nome, e fica registrado junto com a data.
    Acesso que aparece sem explicação é o começo de toda discussão sobre
    quem podia fazer o quê."""
    nivel = (nivel or "").upper()
    if nivel not in NIVEIS:
        raise ValueError("Nível de acesso desconhecido.")

    db = get_db()
    r = db.table("perfis").select("id,papel,nivel,nome").eq("id", perfil_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Pessoa não encontrada.")
    antes = r[0]
    papel = _papel_do_nivel(nivel)

    if nivel == "ADMINISTRADOR" and not (motivo or "").strip():
        raise ValueError("Explique por que esta pessoa passa a administrador.")

    db.table("perfis").update({"papel": papel, "nivel": nivel}) \
        .eq("id", perfil_id).execute()
    db.table("membros_equipe").update({
        "nivel": nivel, "lider": nivel in ("ADMINISTRADOR", "ADVOGADO"),
    }).eq("perfil_id", perfil_id).execute()

    db.table("promocoes_equipe").insert({
        "perfil_id": perfil_id, "de_nivel": antes.get("nivel"),
        "para_nivel": nivel, "de_papel": antes.get("papel"),
        "para_papel": papel, "motivo": (motivo or "")[:400] or None,
        "quem": quem or None,
    }).execute()

    registrar_evento(None, "EQUIPE_NIVEL_ALTERADO",
                     {"perfil": perfil_id, "de": antes.get("nivel"),
                      "para": nivel, "quem": quem})
    return {"ok": True, "papel": papel, "nivel": nivel}


def desligar(membro_id: str, quem: str = "", motivo: str = "") -> dict:
    """Tira o acesso sem apagar o histórico.

    O nome da pessoa continua nos prazos que ela cumpriu e nas tarefas
    que ela fechou. Apagar o membro apagaria a autoria disso, que é
    exatamente o que ninguém pode perder."""
    db = get_db()
    r = db.table("membros_equipe").select("id,nome,perfil_id") \
        .eq("id", membro_id).limit(1).execute().data
    if not r:
        raise ValueError("Membro não encontrado.")
    m = r[0]

    db.table("membros_equipe").update({"ativo": False}) \
        .eq("id", membro_id).execute()
    if m.get("perfil_id"):
        db.table("perfis").update({"papel": "CLIENTE"}) \
            .eq("id", m["perfil_id"]).execute()

    registrar_evento(None, "EQUIPE_DESLIGADA",
                     {"membro": membro_id, "nome": m.get("nome"),
                      "quem": quem, "motivo": motivo})
    return {"ok": True}


def reativar(membro_id: str, quem: str = "") -> dict:
    db = get_db()
    r = db.table("membros_equipe").select("perfil_id,nivel") \
        .eq("id", membro_id).limit(1).execute().data
    if not r:
        raise ValueError("Membro não encontrado.")
    db.table("membros_equipe").update({"ativo": True}) \
        .eq("id", membro_id).execute()
    if r[0].get("perfil_id"):
        db.table("perfis").update({"papel": _papel_do_nivel(r[0].get("nivel") or "")}) \
            .eq("id", r[0]["perfil_id"]).execute()
    registrar_evento(None, "EQUIPE_REATIVADA",
                     {"membro": membro_id, "quem": quem})
    return {"ok": True}
