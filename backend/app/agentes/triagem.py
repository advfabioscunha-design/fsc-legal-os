"""
AGENTE DE TRIAGEM — primeiro contato (Portal/WhatsApp).
Identifica o GRUPO do caso e entrega ao Especialista correspondente.
Usa o modelo rápido (barato) — a triagem é curta.
"""
import json
import anthropic

from ..core.ia import TEMPO_LIMITE, TENTATIVAS
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from .orquestrador import mudar_estado

# Nichos de atuação do escritório (FC ADVOCACIA)
GRUPOS = ["BANCARIO", "IMOBILIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"]

DESCRICAO_NICHOS = """
- BANCARIO: Direito Bancário — tarifas abusivas, revisão de contratos,
  danos por falha de serviço bancário (ex: demora em fila).
- IMOBILIARIO: Distrato Imobiliário — rescisão de compra e venda de imóvel
  na planta, restituição de parcelas, atraso de obra.
- TRIBUTARIO: Execução Fiscal — defesa em execução fiscal, exceção de
  pré-executividade, prescrição de débitos, CDA nula.
- CONSUMIDOR: Recuperação de Consumo — cobrança de "recuperação de consumo"
  por suposta fraude no medidor de energia/água (TOI), corte de
  fornecimento indevido, negativação por fatura eventual.
- OUTROS: o que não se encaixar acima (será escalado a humano).
"""


def identificar_grupo(relato: str) -> dict:
    s = get_settings()
    client = anthropic.Anthropic(api_key=s.claude_api_key,
                               timeout=TEMPO_LIMITE,
                               max_retries=TENTATIVAS)
    resposta = client.messages.create(
        model=s.claude_model_rapido,
        max_tokens=300,
        system=(
            "Você é o triador do escritório FC ADVOCACIA. Classifique o relato "
            f"em um dos nichos:\n{DESCRICAO_NICHOS}\nResponda APENAS JSON: "
            '{"grupo": "...", "confianca": 0.0, "resumo": "..."}'
        ),
        messages=[{"role": "user", "content": relato[:4000]}],
    )
    texto = resposta.content[0].text.strip()
    if texto.startswith("```"):
        texto = "\n".join(texto.split("\n")[1:-1])
    # Resposta em prosa em vez de JSON acontece, e não pode derrubar a
    # entrada do lead. OUTROS é a fila da conferência humana: é o lugar
    # certo para o que a máquina não soube ler.
    try:
        dados = json.loads(texto)
    except (ValueError, TypeError):
        print(f"[triagem] resposta fora do formato: {texto[:200]}")
        return {"grupo": "OUTROS", "confianca": 0, "resumo": texto[:300]}
    if not isinstance(dados, dict):
        return {"grupo": "OUTROS", "confianca": 0, "resumo": texto[:300]}
    if dados.get("grupo") not in GRUPOS:
        dados["grupo"] = "OUTROS"
    return dados


# Estados em que o caso ainda está "vivo": uma nova mensagem do mesmo
# cliente CONTINUA esse caso em vez de abrir outro do zero — é o que
# garante que o atendimento nunca recomece nem repita perguntas.
_ESTADOS_ENCERRADOS = {"PROTOCOLADO", "INVIAVEL", "CANCELADO", "CONCLUIDO"}


def _so_digitos(v: str | None) -> str:
    return "".join(ch for ch in (v or "") if ch.isdigit())


def identificar_cliente(nome: str, email: str | None = None,
                        whatsapp: str | None = None, cpf: str | None = None,
                        canal: str = "PORTAL") -> dict:
    """Encontra o cliente pelo e-mail, CPF ou WhatsApp; se não existir, cria.
    Sempre COMPLETA o cadastro com os dados novos que chegaram — assim o
    e-mail entra no cadastro mesmo que o primeiro contato tenha sido por
    telefone, e o cliente nunca vira um registro duplicado."""
    db = get_db()
    email = (email or "").strip().lower() or None
    whats = _so_digitos(whatsapp) or None
    cpf = _so_digitos(cpf) or None

    achado = None
    for coluna, valor in (("email", email), ("cpf_cnpj", cpf), ("whatsapp", whats)):
        if not valor:
            continue
        try:
            r = db.table("clientes").select("*").eq(coluna, valor) \
                  .limit(1).execute().data
        except Exception:
            r = []
        if r:
            achado = r[0]
            break

    if achado:
        # completa os campos que ainda estavam vazios (não sobrescreve o que já existe)
        faltando = {}
        if email and not achado.get("email"):
            faltando["email"] = email
        if whats and not achado.get("whatsapp"):
            faltando["whatsapp"] = whats
        if cpf and not achado.get("cpf_cnpj"):
            faltando["cpf_cnpj"] = cpf
        if nome and not achado.get("nome"):
            faltando["nome"] = nome
        if faltando:
            db.table("clientes").update(faltando).eq("id", achado["id"]).execute()
            achado.update(faltando)
        return achado

    novo = {"nome": nome or "Cliente", "origem": canal}
    if email:
        novo["email"] = email
    if whats:
        novo["whatsapp"] = whats
    if cpf:
        novo["cpf_cnpj"] = cpf
    return db.table("clientes").insert(novo).execute().data[0]


def caso_em_aberto(cliente_id: str) -> dict | None:
    """Último caso ainda em andamento deste cliente (ou None)."""
    try:
        casos = get_db().table("casos").select("*").eq("cliente_id", cliente_id) \
                  .order("atualizado_em", desc=True).limit(10).execute().data
    except Exception:
        return None
    for c in casos or []:
        if c.get("estado") not in _ESTADOS_ENCERRADOS:
            return c
    return None


def criar_caso(nome: str, contato: str, relato: str,
               canal: str = "PORTAL", cpf: str | None = None,
               email: str | None = None, whatsapp: str | None = None) -> dict:
    """Entrada de um lead: identifica (ou cria) o cliente, CONTINUA o caso
    aberto se já houver um, classifica o grupo e entrega ao Especialista."""
    db = get_db()

    # `contato` é o campo legado: pode vir e-mail ou telefone
    if contato and "@" in contato:
        email = email or contato
    elif contato:
        whatsapp = whatsapp or contato
    if canal == "WHATSAPP":
        whatsapp = whatsapp or contato

    cliente = identificar_cliente(nome, email=email, whatsapp=whatsapp,
                                  cpf=cpf, canal=canal)

    # ── conversa interligada: se já existe caso vivo, segue nele ──
    aberto = caso_em_aberto(cliente["id"])
    if aberto:
        from .especialista import atender
        resposta = atender(aberto["id"], relato, canal=canal)
        return {"caso_id": aberto["id"], "grupo": aberto.get("grupo"),
                "continuado": True,
                "primeira_resposta": resposta.get("resposta")}

    # CLASSIFICAR ANTES DE GRAVAR, E NUNCA PERDER O LEAD
    #
    # O caso era gravado primeiro e classificado depois. Falhando a
    # classificação (conta sem saldo, modelo respondendo em prosa em vez
    # de JSON, rede), a exceção subia e o caso ficava no banco em LEAD,
    # sem grupo e sem título. As telas do escritório filtram por esses
    # campos, então o caso existia e não aparecia em lugar nenhum: o
    # cliente escrevia, via erro, desistia, e ninguém no escritório
    # ficava sabendo que ele existiu.
    #
    # Agora a classificação vem antes, e falhar nela não impede o lead
    # de entrar: ele cai em OUTROS, que é a fila da conferência humana.
    # Perder a classificação custa um minuto de alguém; perder o cliente
    # custa o cliente.
    try:
        clas = identificar_grupo(relato)
    except Exception as e:
        print(f"[triagem] não classifiquei, o lead entra como OUTROS: {e}")
        clas = {"grupo": "OUTROS", "confianca": 0,
                "resumo": "Não foi possível classificar automaticamente. "
                          "Confira o relato e defina o grupo."}

    caso = db.table("casos").insert({
        "cliente_id": cliente["id"],
        "relato_inicial": relato,
        "estado": "LEAD",
    }).execute().data[0]

    NOMES = {
        "BANCARIO": "Direito Bancário", "IMOBILIARIO": "Distrato Imobiliário",
        "TRIBUTARIO": "Execução Fiscal", "CONSUMIDOR": "Recuperação de Consumo",
        "TRABALHISTA": "Causa Trabalhista", "PREVIDENCIARIO": "Causa Previdenciária",
    }
    atualiza = {"grupo": clas["grupo"],
                "titulo": NOMES.get(clas["grupo"], "Atendimento jurídico")}
    try:
        db.table("casos").update(atualiza).eq("id", caso["id"]).execute()
    except Exception:  # coluna `titulo` ainda não migrada
        db.table("casos").update({"grupo": clas["grupo"]}).eq("id", caso["id"]).execute()
    registrar_evento(caso["id"], "TRIAGEM", clas)
    mudar_estado(caso["id"], "QUALIFICACAO",
                 motivo=f"Triagem: {clas['grupo']} ({clas.get('confianca')})")

    # O Especialista do grupo assume e responde a primeira mensagem
    from .especialista import atender
    primeira = atender(caso["id"], relato, canal=canal)

    return {"caso_id": caso["id"], "grupo": clas["grupo"],
            "continuado": False,
            "primeira_resposta": primeira.get("resposta")}
