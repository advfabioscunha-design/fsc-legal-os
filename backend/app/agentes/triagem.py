"""
AGENTE DE TRIAGEM — primeiro contato (Portal/WhatsApp).
Identifica o GRUPO do caso e entrega ao Especialista correspondente.
Usa o modelo rápido (barato) — a triagem é curta.
"""
import json
import anthropic
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
    client = anthropic.Anthropic(api_key=s.claude_api_key)
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
    dados = json.loads(texto)
    if dados.get("grupo") not in GRUPOS:
        dados["grupo"] = "OUTROS"
    return dados


def criar_caso(nome: str, contato: str, relato: str,
               canal: str = "PORTAL", cpf: str | None = None) -> dict:
    """Entrada de um novo lead: cria cliente + caso, classifica o grupo
    e passa o controle ao Agente Especialista do grupo."""
    db = get_db()

    dados_cliente = {
        "nome": nome,
        "whatsapp" if canal == "WHATSAPP" else "email": contato,
        "origem": canal,
    }
    if cpf:
        dados_cliente["cpf_cnpj"] = cpf
    cliente = db.table("clientes").insert(dados_cliente).execute().data[0]

    caso = db.table("casos").insert({
        "cliente_id": cliente["id"],
        "relato_inicial": relato,
        "estado": "LEAD",
    }).execute().data[0]

    clas = identificar_grupo(relato)
    db.table("casos").update({"grupo": clas["grupo"]}).eq("id", caso["id"]).execute()
    registrar_evento(caso["id"], "TRIAGEM", clas)
    mudar_estado(caso["id"], "QUALIFICACAO",
                 motivo=f"Triagem: {clas['grupo']} ({clas.get('confianca')})")

    # O Especialista do grupo assume e responde a primeira mensagem
    from .especialista import atender
    primeira = atender(caso["id"], relato, canal=canal)

    return {"caso_id": caso["id"], "grupo": clas["grupo"],
            "primeira_resposta": primeira.get("resposta")}
