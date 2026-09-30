"""
Quem pode chamar o quê.

A API nasceu aberta. Duzentas e trinta e quatro rotas, nenhuma
perguntando quem estava do outro lado, e o CORS liberado para qualquer
origem. A proteção era ninguém saber o endereço, e o endereço está no
JavaScript do site, que todo visitante baixa.

A ESCOLHA: NEGAR POR PADRÃO
---------------------------
Havia duas formas de fechar. Uma era marcar rota por rota o que exige
login. Além do trabalho, o defeito é o que acontece depois: toda rota
nova nasceria aberta, e a que alguém esquecesse de marcar ficaria
aberta para sempre, sem ninguém notar.

Aqui é o contrário. Tudo exige identificação, e o que é público está
numa lista curta, escrita à mão, neste arquivo. Rota nova nasce
fechada. Se precisar ser pública, alguém tem de vir aqui e dizer isso
por escrito, o que é exatamente a conversa que se quer ter.

O QUE É PÚBLICO, E POR QUÊ
--------------------------
Quase tudo que é público aqui é público porque a pessoa ainda não tem
conta. Quem está negociando um contrato no balcão decide o preço antes
de criar acesso, de propósito: pedir CPF e senha a quem ainda não
decidiu contratar é o jeito mais rápido de perder a pessoa.

Onde não há login, o que protege é um identificador sorteado que só
quem recebeu conhece: o token do convite, o id do pedido, o token do
feed da agenda. Não é tão forte quanto uma sessão, e por isso vale para
o que é temporário e endereçado a uma pessoa só.
"""
from __future__ import annotations

import re
import time

from fastapi import HTTPException, Request

from .db import get_db

# ── O que não exige identificação ───────────────────────────────
#
# Expressões regulares, casadas contra o caminho inteiro. A âncora no
# fim existe para que /api/v1/contratos/tipos não abra, por descuido,
# /api/v1/contratos/tipos-secretos.
PUBLICO = [
    r"^/health$",
    r"^/$",

    # O site: formulário de contato e a conversa do atendimento. O caso
    # é identificado por um id sorteado que fica no navegador de quem
    # abriu a conversa.
    r"^/api/v1/leads$",
    r"^/api/v1/casos/[^/]+/mensagens$",
    r"^/api/v1/cep/[^/]+$",
    # Conferência de CPF: usada no balcão, antes de a pessoa ter conta,
    # e nos dados da outra parte do contrato, que nunca terá conta.
    r"^/api/v1/cpf/conferir$",

    # Elaboração de contrato pelo site, antes de existir conta.
    r"^/api/v1/contrato/iniciar$",
    r"^/api/v1/contrato/[^/]+$",

    # O balcão. Toda a negociação acontece antes do cadastro.
    r"^/api/v1/contratos/tipos$",
    r"^/api/v1/contratos/tipos/[^/]+$",
    r"^/api/v1/contratos/pix$",
    r"^/api/v1/contratos/pedidos$",
    r"^/api/v1/contratos/pedidos/[^/]+$",
    r"^/api/v1/contratos/pedidos/[^/]+/(negociar|negociar/abrir|conversa|"
    r"termo-contratacao|dados|escolhas|documentos|coleta-concluida|"
    r"alteracao|aprovar|mensagem|pdf|vincular|proposta|desarquivar|partes|pendencias)$",
    # A urgência: o cliente orça e avisa que pagou. Confirmar, não:
    # essa fica atrás do porteiro, porque é ela que muda o prazo.
    r"^/api/v1/contratos/pedidos/[^/]+/urgencia$",
    # O retrato do cadastro conhecido é lido com o token do cliente,
    # dentro da própria rota. Aberto aqui só para não exigir papel de
    # equipe; sem token ele devolve "não conhecido" e nada mais.
    r"^/api/v1/contratos/pedidos/[^/]+/conhecido$",
    r"^/api/v1/cliente/conhecido$",
    r"^/api/v1/contratos/pedidos/[^/]+/urgencia/paguei$",

    # Convite da equipe: quem recebe ainda não tem conta, e é o token
    # sorteado que faz as vezes de credencial.
    r"^/api/v1/convites/[^/]+$",
    r"^/api/v1/convites/[^/]+/aceitar$",

    # Recuperação de acesso e a porta da equipe, que é lida por quem
    # ainda não entrou.
    r"^/api/v1/acesso/(limite|trocar-email)$",

    # Feed da agenda para o Google Calendar: o calendário não tem como
    # fazer login, e o token assinado na URL é o que protege.
    r"^/api/v1/agenda/feed/[^/]+\.ics$",

    # Webhooks: quem chama é o Asaas, o ZapSign, a Meta. Cada um traz a
    # própria assinatura, conferida dentro da rota.
    r"^/api/v1/webhooks/",
    r"^/webhooks/",
]

# O que, além de login, exige ser da equipe. Na prática é tudo que não
# é do cliente, mas escrever assim deixa o engano difícil.
DO_CLIENTE = [
    r"^/api/v1/cliente/",
    r"^/api/v1/contratos/meus-pedidos$",
]

_PUBLICO = [re.compile(p) for p in PUBLICO]
_CLIENTE = [re.compile(p) for p in DO_CLIENTE]

# Validar o token significa uma chamada ao Supabase. Sem cache, cada
# tela da plataforma faria dezenas por minuto. Cinco minutos é curto o
# bastante para que uma demissão tenha efeito rápido e longo o bastante
# para o cache valer a pena.
_CACHE: dict[str, tuple[float, dict]] = {}
VALIDADE_CACHE = 300


def _usuario(token: str) -> dict | None:
    agora = time.time()
    guardado = _CACHE.get(token)
    if guardado and guardado[0] > agora:
        return guardado[1]

    db = get_db()
    try:
        r = db.auth.get_user(token)
        uid = r.user.id
    except Exception:
        return None

    perfil = db.table("perfis").select("papel,nivel,nome,email") \
        .eq("id", uid).limit(1).execute().data
    dados = {"id": uid, **(perfil[0] if perfil else {"papel": "CLIENTE"})}
    _CACHE[token] = (agora + VALIDADE_CACHE, dados)
    if len(_CACHE) > 500:
        for k, (v, _) in list(_CACHE.items()):
            if v < agora:
                _CACHE.pop(k, None)
    return dados


def checar(request: Request) -> dict | None:
    """Devolve o usuário, ou levanta 401/403. None em rota pública."""
    caminho = request.url.path

    if request.method == "OPTIONS":        # o navegador perguntando as regras
        return None
    if any(p.match(caminho) for p in _PUBLICO):
        return None

    cabecalho = request.headers.get("authorization") or ""
    if not cabecalho.lower().startswith("bearer "):
        raise HTTPException(401, "Faça login para acessar.")

    usuario = _usuario(cabecalho[7:].strip())
    if not usuario:
        raise HTTPException(401, "Sessão expirada. Entre de novo.")

    if any(p.match(caminho) for p in _CLIENTE):
        return usuario

    if usuario.get("papel") not in ("OPERADOR", "ADMIN"):
        raise HTTPException(403, "Esta área é da equipe do escritório.")
    return usuario
