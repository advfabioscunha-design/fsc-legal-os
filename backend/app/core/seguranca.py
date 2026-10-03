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
    # ATENÇÃO AO MÉTODO AQUI
    #
    # Esta rota era pública para qualquer método, e o par POST/GET divide
    # o mesmo caminho. O POST é o que precisa ser aberto: quem está no
    # balcão cria o pedido antes de ter conta.
    #
    # O GET devolvia ATÉ 300 PEDIDOS com nome e e-mail dos clientes, para
    # quem chamasse — sem login, da internet aberta. O endereço está no
    # JavaScript do site, que todo visitante baixa.
    #
    # Agora só o POST é público. A listagem voltou para trás do porteiro,
    # que é onde ela sempre devia ter estado.
    ("POST", r"^/api/v1/contratos/pedidos$"),
    r"^/api/v1/contratos/pedidos/[^/]+$",
    r"^/api/v1/contratos/pedidos/[^/]+/(negociar|negociar/abrir|conversa|"
    r"termo-contratacao|dados|escolhas|documentos|coleta-concluida|"
    r"alteracao|aprovar|mensagem|pdf|vincular|proposta|desarquivar|partes|pendencias)$",
    # A urgência: o cliente orça e avisa que pagou. Confirmar, não:
    # essa fica atrás do porteiro, porque é ela que muda o prazo.
    r"^/api/v1/contratos/pedidos/[^/]+/urgencia$",
    # O sinal de "estou digitando", mandado pela página do cliente. Quem
    # tem o id do pedido é quem está com a página aberta, e o pior uso
    # possível disto é fazer o escritório achar que alguém está
    # escrevendo. O carimbo vence em segundos.
    r"^/api/v1/contratos/pedidos/[^/]+/digitando$",
    # O retrato do cadastro conhecido é lido com o token do cliente,
    # dentro da própria rota. Aberto aqui só para não exigir papel de
    # equipe; sem token ele devolve "não conhecido" e nada mais.
    r"^/api/v1/contratos/pedidos/[^/]+/conhecido$",
    r"^/api/v1/cliente/conhecido$",
    # A decisão sobre o que a lei não admite é do cliente, e ele a toma
    # pela tela do pedido dele, sem conta de operador.
    r"^/api/v1/contratos/pedidos/[^/]+/decisao$",
    r"^/api/v1/contratos/pedidos/[^/]+/urgencia/paguei$",

    # ATENDIMENTO POR VÍDEO — a sala do cliente.
    #
    # O cliente recebe o link por WhatsApp e clica. Ele não tem conta de
    # operador, e muitas vezes nem conta na plataforma: abre o link no
    # navegador do celular e espera entrar. Estas rotas estavam atrás do
    # porteiro, e por isso ele via "Esta área é da equipe do escritório"
    # — uma recusa que não fazia sentido nenhum para quem tinha sido
    # convidado para a conversa.
    #
    # O que protege aqui é o mesmo que protege o convite da equipe: o id
    # sorteado na URL é a credencial, e ele vence. A rota de entrada
    # confere o prazo e devolve `expirado`; a de entrar recusa sala
    # encerrada. E nada do que está atrás destas três rotas é dado de
    # outro cliente: é o termo de consentimento, que é público por
    # natureza, e a decisão desta pessoa sobre a gravação desta conversa.
    #
    # Fora daqui ficam, de propósito, `encerrar`, `transcrever` e
    # `pode-gravar`: essas são do escritório.
    r"^/api/v1/atendimentos/[^/]+/(entrada|entrar|autorizar-gravacao)$",

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

# Cada entrada de PUBLICO é um padrão (vale para qualquer método) ou um
# par (método, padrão). O par existe porque POST e GET compartilham
# caminho em algumas rotas, e abrir o caminho abre os dois — foi assim
# que a listagem de pedidos do balcão ficou exposta.
_PUBLICO = [(None, re.compile(p)) if isinstance(p, str)
            else (p[0].upper(), re.compile(p[1]))
            for p in PUBLICO]
_CLIENTE = [re.compile(p) for p in DO_CLIENTE]


def _e_publico(metodo: str, caminho: str) -> bool:
    return any(rx.match(caminho) and (m is None or m == metodo)
               for m, rx in _PUBLICO)

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


# ── O QUE O ADVOGADO PARCEIRO ALCANÇA ───────────────────────────
#
# O parceiro é advogado de fora: atua em causa específica, divide o
# honorário dela e não tem nada que ver com o resto da carteira. Não é
# associado do escritório — associado é OPERADOR ou ADMIN e vê tudo.
#
# A LISTA É EXPLÍCITA, E NÃO UMA REGRA ESPERTA
#
# Seria mais curto escrever "parceiro pode tudo que a equipe pode, menos
# X". Seria também o jeito de abrir a carteira inteira no dia em que
# alguém criasse uma rota nova sem lembrar do X.
#
# Aqui é ao contrário: o parceiro não alcança NADA, salvo o que está
# escrito abaixo. Rota nova nasce fechada para ele. Quando faltar
# alguma, ele recebe "este caso não é da sua parceria" — chato, e
# seguro. O contrário seria silencioso e grave.
#
# Alcançar a rota é só a primeira porta. A segunda é o caso: cada uma
# destas rotas confere, por dentro, se AQUELE caso é de uma parceria
# viva dele. É `_casos_do_parceiro`, em main.py.
DO_PARCEIRO = [
    # A identidade e o cadastro dele
    r"^/api/v1/parceiro/(eu|cadastro)$",
    # Os casos da parceria, e o que se faz dentro deles
    r"^/api/v1/parceiro/casos$",
    r"^/api/v1/parceiro/caso/[^/]+$",
    r"^/api/v1/parceiro/caso/[^/]+/(documentos|mensagens|tarefas|comentarios)$",
    r"^/api/v1/parceiro/caso/[^/]+/documentos/[^/]+/baixar$",
    # Cadastrar causa nova: ela entra na esteira do escritório como
    # qualquer outra, e nasce com a parceria proposta por ele.
    r"^/api/v1/parceiro/casos/novo$",
    # O dinheiro dele — e só o dele
    r"^/api/v1/parceiro/valores$",
    r"^/api/v1/parceiro/repasses$",
    r"^/api/v1/parceiro/repasses/[^/]+/recibo$",
    # Serventia geral que não revela nada de ninguém
    r"^/api/v1/cep/[^/]+$",
    r"^/api/v1/ia/estado$",
]
_PARCEIRO = [re.compile(p) for p in DO_PARCEIRO]

# ── O QUE SÓ O ADMINISTRADOR FAZ ────────────────────────────────
#
# Conceder acesso, retirar acesso e passar a chave do escritório a
# outra pessoa. O operador trabalha; quem decide quem trabalha é o dono.
SO_DO_ADMIN = [
    r"^/api/v1/admin/acessos",
    r"^/api/v1/admin/parceiros/[^/]+/(suspender|reativar)$",
    r"^/api/v1/equipe/[^/]+/(promover|rebaixar|remover)$",
]
_SO_ADMIN = [re.compile(p) for p in SO_DO_ADMIN]


def checar(request: Request) -> dict | None:
    """Devolve o usuário, ou levanta 401/403. None em rota pública."""
    caminho = request.url.path

    if request.method == "OPTIONS":        # o navegador perguntando as regras
        return None
    if _e_publico(request.method.upper(), caminho):
        return None

    cabecalho = request.headers.get("authorization") or ""
    if not cabecalho.lower().startswith("bearer "):
        raise HTTPException(401, "Faça login para acessar.")

    usuario = _usuario(cabecalho[7:].strip())
    if not usuario:
        raise HTTPException(401, "Sessão expirada. Entre de novo.")

    papel = usuario.get("papel")

    if any(p.match(caminho) for p in _CLIENTE):
        return usuario

    # O PARCEIRO ANTES DA EQUIPE
    #
    # Esta conferência vem primeiro de propósito. Se viesse depois da
    # trava de equipe, o parceiro levaria "esta área é da equipe" nas
    # próprias rotas dele — e, pior, bastaria alguém marcar o papel
    # errado uma vez para ele cair no mundo da equipe sem ninguém notar.
    if papel == "PARCEIRO":
        if any(p.match(caminho) for p in _PARCEIRO):
            return usuario
        raise HTTPException(
            403, "Esta área é do escritório. Como parceiro, o senhor "
                 "acessa os casos em que consta a sua parceria.")

    if papel not in ("OPERADOR", "ADMIN"):
        raise HTTPException(403, "Esta área é da equipe do escritório.")

    # Conceder e retirar acesso é ato de quem responde pelo escritório.
    # Operador trabalha; quem decide quem trabalha é o dono.
    if papel != "ADMIN" and any(p.match(caminho) for p in _SO_ADMIN):
        raise HTTPException(
            403, "Só o administrador concede ou retira acesso.")

    return usuario
