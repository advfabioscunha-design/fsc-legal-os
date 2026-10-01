"""O AGENTE QUE CUIDA DA BASE DE CLIENTES.

Roda duas vezes por dia e faz o trabalho chato que ninguém faz à mão:
arruma o que está torto, traz para o cadastro o que já existe espalhado
pelo sistema, e aponta o que falta para alguém preencher.

A LINHA QUE ELE NÃO ATRAVESSA: NÃO INVENTA DADO.

"Completar o cadastro" aqui significa UMA coisa só: pegar informação que
JÁ EXISTE em outro lugar do sistema e que pertence àquela mesma pessoa.
A data de nascimento que o cliente digitou na coleta do contrato, o CPF
que está na qualificação da parte, o endereço que ele preencheu no
pedido. Isso não é descobrir nada: é parar de guardar a mesma informação
em dois lugares, com um deles vazio.

O que ele NUNCA faz é deduzir. Não adivinha sobrenome, não estima idade,
não completa CPF, não "corrige" nome para o que parece mais provável.
Base de cliente com dado inventado é pior do que base incompleta: a
incompleta alguém preenche, e a inventada ninguém desconfia.

O QUE ELE ARRUMA, E POR QUE CADA UM IMPORTA

  TELEFONE SEM PADRÃO. "(69) 99322-5383", "69993225383" e "5569993225383"
  são a mesma pessoa e três cadastros diferentes para o sistema. É isso
  que faz o WhatsApp não reconhecer quem escreve.

  NOME EM CAIXA ALTA OU TUDO MINÚSCULO. Vem assim de importação e de
  formulário. O cliente recebe "Feliz aniversário, MARIA" e sabe que
  saiu de uma planilha.

  E-MAIL COM ESPAÇO E MAIÚSCULA. Quebra a busca por e-mail, que é como
  a área do cliente encontra o cadastro de quem faz login.

  DUPLICADO. Mesma pessoa em duas linhas recebe dois parabéns no mesmo
  dia. Ele NÃO junta sozinho, porque juntar cadastro errado apaga
  histórico: ele aponta, e quem decide é gente.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from ..core.db import get_db, registrar_evento
from ..core import dados as _dados

# Brasília. É o relógio que o escritório usa para falar de horário
# comercial, e o que o Dr. Fábio pediu.
FUSO = timezone(timedelta(hours=-3))

# As partículas que não levam maiúscula num nome brasileiro.
_MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o"}


def _agora() -> datetime:
    return datetime.now(FUSO)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── As arrumações ────────────────────────────────────────────────
def arrumar_telefone(valor) -> str | None:
    """Só dígitos, com 55 na frente. None quando não é telefone."""
    d = "".join(c for c in str(valor or "") if c.isdigit())
    if len(d) < 10:
        return None
    if d.startswith("55") and len(d) >= 12:
        return d
    if len(d) in (10, 11):
        return "55" + d
    return d


def arrumar_nome(valor) -> str | None:
    """Caixa certa, sem espaço dobrado. None quando não há nome.

    Nome que já vem com maiúscula e minúscula misturadas é deixado como
    está: pode ser "McDonald", "d'Ávila" ou um sobrenome estrangeiro, e
    arrumar isso estragaria mais do que conserta. Só mexe no que está
    INTEIRO em caixa alta ou inteiro em minúscula, que é o que vem de
    planilha e de formulário."""
    bruto = " ".join(str(valor or "").split())
    if len(bruto) < 2:
        return None
    if not (bruto.isupper() or bruto.islower()):
        return bruto
    partes = []
    for i, p in enumerate(bruto.lower().split(" ")):
        if i > 0 and p in _MINUSCULAS:
            partes.append(p)
        else:
            partes.append(p[:1].upper() + p[1:])
    return " ".join(partes)


def arrumar_email(valor) -> str | None:
    e = str(valor or "").strip().lower().replace(" ", "")
    return e if re.fullmatch(r"[\w.+-]+@[\w-]+\.[\w.-]+", e) else None


def arrumar_data(valor) -> str | None:
    """Aceita 1990-05-10, 10/05/1990 e 10-05-1990. Recusa o resto.

    Data fora de faixa é recusada: ano 1890 ou 2030 num cadastro de
    cliente é erro de digitação, e guardar faz a felicitação sair no dia
    errado para sempre."""
    t = str(valor or "").strip()[:10]
    if not t:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
    if not m:
        m2 = re.fullmatch(r"(\d{2})[/-](\d{2})[/-](\d{4})", t)
        if not m2:
            return None
        d, mes, ano = m2.groups()
    else:
        ano, mes, d = m.groups()
    try:
        data = datetime(int(ano), int(mes), int(d))
    except ValueError:
        return None
    if not (1900 <= data.year <= _agora().year - 10):
        return None
    return data.strftime("%Y-%m-%d")


# ── De onde o agente tira o que falta ────────────────────────────
_DO_PEDIDO = {
    "data_nascimento": ("data_nascimento", "nascimento", "data_de_nascimento"),
    "cpf_cnpj": ("cpf", "cpf_cnpj", "cnpj"),
    "profissao": ("profissao",),
    "estado_civil": ("estado_civil",),
    "nacionalidade": ("nacionalidade",),
    "endereco_rua": ("endereco", "endereco_rua", "logradouro"),
    "endereco_cidade": ("cidade", "endereco_cidade"),
    "endereco_uf": ("uf", "estado", "endereco_uf"),
    "endereco_cep": ("cep", "endereco_cep"),
}


def _colher_do_pedido(cliente_id: str) -> dict:
    """O que o cliente já digitou nos pedidos de contrato dele.

    Não é descoberta: é a mesma pessoa, o mesmo sistema, e a informação
    estava guardada numa tabela e faltando na outra."""
    try:
        pedidos = get_db().table("pedidos_contrato") \
            .select("dados,partes,atualizado_em").eq("cliente_id", cliente_id) \
            .order("atualizado_em", desc=True).limit(10).execute().data or []
    except Exception as e:
        print(f"[cadastrador] pedidos não lidos: {e}")
        return {}

    achado: dict = {}
    for p in pedidos:
        fontes = [_dados.como_dict(p.get("dados"))]
        fontes += [x for x in _dados.lista_de_dicts(p.get("partes"))]
        for fonte in fontes:
            minusculas = {str(k).lower(): v for k, v in fonte.items()}
            for destino, apelidos in _DO_PEDIDO.items():
                if destino in achado:
                    continue
                for a in apelidos:
                    if minusculas.get(a):
                        achado[destino] = minusculas[a]
                        break
    return achado


# ── A varredura ──────────────────────────────────────────────────
def varrer(limite: int = 500, aplicar: bool = True) -> dict:
    """Passa pela base, arruma o que dá e aponta o que falta.

    `aplicar=False` devolve o mesmo relatório sem gravar nada, que é como
    se confere o que o agente FARIA antes de deixá-lo fazer."""
    db = get_db()
    try:
        clientes = db.table("clientes").select(
            "id,nome,cpf_cnpj,email,whatsapp,data_nascimento,origem,"
            "profissao,estado_civil,nacionalidade,endereco_rua,"
            "endereco_cidade,endereco_uf,endereco_cep,descadastrado_em"
        ).order("atualizado_em", desc=True).limit(limite).execute().data or []
    except Exception as e:
        return {"erro": f"base não lida: {e}", "vistos": 0}

    arrumados, completados, falta_nascimento = 0, 0, 0
    por_cpf: dict[str, list] = {}
    por_zap: dict[str, list] = {}
    mudancas: list[dict] = []

    for c in clientes:
        campos: dict = {}

        novo_nome = arrumar_nome(c.get("nome"))
        if novo_nome and novo_nome != c.get("nome"):
            campos["nome"] = novo_nome
        novo_zap = arrumar_telefone(c.get("whatsapp"))
        if novo_zap and novo_zap != c.get("whatsapp"):
            campos["whatsapp"] = novo_zap
        novo_email = arrumar_email(c.get("email"))
        if novo_email and novo_email != c.get("email"):
            campos["email"] = novo_email
        nova_data = arrumar_data(c.get("data_nascimento"))
        if nova_data and nova_data != str(c.get("data_nascimento") or "")[:10]:
            campos["data_nascimento"] = nova_data

        if campos:
            arrumados += 1

        # O que falta, buscado onde já existe.
        vazios = [k for k in _DO_PEDIDO
                  if not (c.get(k) or campos.get(k))]
        if vazios:
            do_pedido = _colher_do_pedido(c["id"])
            for k in vazios:
                bruto = do_pedido.get(k)
                if not bruto:
                    continue
                valor = (arrumar_data(bruto) if k == "data_nascimento"
                         else str(bruto).strip())
                if not valor:
                    continue
                if k == "cpf_cnpj":
                    valor = "".join(x for x in valor if x.isdigit()) or None
                if valor:
                    campos[k] = valor
                    completados += 1

        if campos and aplicar:
            campos["atualizado_em"] = _iso()
            try:
                db.table("clientes").update(campos).eq("id", c["id"]).execute()
            except Exception as e:
                print(f"[cadastrador] {c['id']} não atualizado: {e}")
        if campos:
            mudancas.append({"id": c["id"],
                             "nome": campos.get("nome") or c.get("nome"),
                             "campos": sorted(k for k in campos
                                              if k != "atualizado_em")})

        if not (c.get("data_nascimento") or campos.get("data_nascimento")):
            falta_nascimento += 1

        cpf = "".join(x for x in str(c.get("cpf_cnpj") or "") if x.isdigit())
        if len(cpf) in (11, 14):
            por_cpf.setdefault(cpf, []).append(c.get("nome") or c["id"])
        zap = campos.get("whatsapp") or c.get("whatsapp")
        if zap:
            por_zap.setdefault(str(zap), []).append(c.get("nome") or c["id"])

    # O agente NÃO junta duplicado sozinho. Juntar cadastro errado apaga
    # histórico de caso, e isso não se desfaz.
    duplicados = ([{"por": "CPF", "chave": k[-4:], "nomes": v}
                   for k, v in por_cpf.items() if len(v) > 1]
                  + [{"por": "WhatsApp", "chave": k[-4:], "nomes": v}
                     for k, v in por_zap.items() if len(v) > 1])

    relatorio = {"vistos": len(clientes), "arrumados": arrumados,
                 "completados": completados,
                 "falta_nascimento": falta_nascimento,
                 "duplicados": duplicados[:30],
                 "mudancas": mudancas[:50], "aplicado": aplicar}
    if aplicar:
        registrar_evento(None, "BASE_DE_CLIENTES_VARRIDA",
                         {k: v for k, v in relatorio.items()
                          if k not in ("mudancas", "duplicados")})
    return relatorio


def avisar_o_que_falta(relatorio: dict) -> None:
    """Uma tarefa por dia com o que o agente não pode resolver sozinho.

    Sem isto, a varredura arruma o que dá e o resto fica invisível: a
    base nunca fica completa porque ninguém sabe o que falta nela."""
    faltam = int(relatorio.get("falta_nascimento") or 0)
    dups = relatorio.get("duplicados") or []
    if not faltam and not dups:
        return

    partes = []
    if faltam:
        partes.append(f"{faltam} cliente(s) sem data de nascimento. Sem a "
                      f"data, a felicitação não tem como sair. A tela "
                      f"Clientes tem o filtro 'sem data de nascimento'.")
    if dups:
        linhas = "; ".join(f"{d['por']} final {d['chave']}: "
                           + ", ".join(str(x) for x in d["nomes"][:3])
                           for d in dups[:10])
        partes.append(f"{len(dups)} possível(is) cadastro(s) repetido(s). "
                      f"Repetido manda dois parabéns no mesmo dia. "
                      f"Confira antes de juntar, porque juntar errado apaga "
                      f"histórico: {linhas}")

    try:
        get_db().table("tarefas").insert({
            "titulo": "Base de clientes: o que falta preencher",
            "descricao": "\n\n".join(partes),
            "origem": "TRIAGEM",
            "data": _agora().date().isoformat(),
            "prioridade": "BAIXA",
            "motivo": "Varredura diária da base de clientes.",
            "criado_por": "CADASTRADOR",
        }).execute()
    except Exception as e:
        print(f"[cadastrador] tarefa do que falta não criada: {e}")


# ── A rotina das duas vezes por dia ──────────────────────────────
def rodar(com_felicitacoes: bool = True) -> dict:
    """Varre a base e, se estiver em horário comercial, parabeniza.

    As duas coisas juntas de propósito: a varredura arruma o telefone e
    traz a data de nascimento do pedido, e é justamente isso que faz a
    felicitação encontrar gente que antes ela não encontraria. Rodar a
    felicitação antes da varredura deixaria essas pessoas de fora por
    mais um ano."""
    relatorio = varrer()
    saida = {"base": relatorio}

    if com_felicitacoes:
        from . import relacionamento
        saida["felicitacoes"] = relacionamento.parabenizar_aniversariantes()

    return saida


def rotina_da_manha() -> dict:
    """9h de Brasília: varre, completa e manda os parabéns do dia.

    Nove, e não oito: às 9h em Brasília são 8h em Rondônia, e o
    escritório atende nos dois fusos. Mandando às 8h de Brasília, metade
    dos clientes receberia às 7h, antes de o dia começar."""
    r = rodar(com_felicitacoes=True)
    avisar_o_que_falta(r.get("base") or {})
    return r


def rotina_da_tarde() -> dict:
    """15h de Brasília: a segunda passada.

    Pega quem foi cadastrado durante a manhã e quem teve a data de
    nascimento preenchida hoje. A trava de uma mensagem por pessoa por
    ano garante que ninguém receba duas vezes."""
    return rodar(com_felicitacoes=True)
