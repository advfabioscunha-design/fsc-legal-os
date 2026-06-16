"""
AGENTE DE ELABORAÇÃO DE CONTRATOS — FC ADVOCACIA.

Recebe a solicitação do cliente, explica a complexidade e o preço logo no
início, coleta as informações necessárias, espelha os termos do contrato e
orienta sobre eventuais abusividades. O contrato é elaborado com base na
legislação específica e na jurisprudência aplicável, com segurança jurídica,
e — com aprovação do cliente — enviado por WhatsApp ou e-mail.

Persiste a conversa na tabela 'mensagens' (reaproveita a estrutura de casos).
"""
import anthropic
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

_client = None
def _claude():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=get_settings().claude_api_key)
    return _client

# Marcador que o frontend usa para abrir o documento no visualizador protegido
MARCADOR = "===CONTRATO EM REVISÃO==="

PRECOS = {"baixa": "R$ 69,90", "media": "R$ 99,90", "alta": "R$ 249,90"}

# Saudação fixa: SEMPRE explica complexidade e preço primeiro
SAUDACAO_CONTRATO = (
    "Olá! Seja muito bem-vindo(a) ao serviço de Elaboração de Contratos da FC Advocacia. "
    "Será um prazer cuidar do seu contrato com total segurança jurídica.\n\n"
    "Antes de tudo, deixe eu te explicar como funciona o valor — ele depende da complexidade do contrato:\n"
    "• Baixa complexidade: R$ 69,90 (contratos simples, ex.: recibos, declarações, acordos básicos)\n"
    "• Média complexidade: R$ 99,90 (cláusulas específicas e obrigações mais detalhadas)\n"
    "• Alta complexidade: R$ 249,90 (garantias, várias partes ou alto valor envolvido)\n\n"
    "Me conte: que tipo de contrato você precisa? Com base na sua resposta eu indico a complexidade "
    "(você pode escolher uma faixa maior, se quiser, nunca menor que a minha análise)."
)

def gerar_system_prompt() -> str:
    s = get_settings()
    return f"""
Você é o Agente Especialista em ELABORAÇÃO DE CONTRATOS do escritório FC ADVOCACIA
(Dr. {s.advogado}, {s.oab}). Atendimento HUMANIZADO, cordial, cristão e cuidadoso:
trate pelo nome, linguagem simples, frases curtas (estilo WhatsApp), uma pergunta de cada vez.

REGRA DE PREÇO (SEMPRE PRIMEIRO): a complexidade define o valor:
- Baixa: {PRECOS['baixa']} | Média: {PRECOS['media']} | Alta: {PRECOS['alta']}.
Logo na primeira informação do cliente sobre o que ele precisa, ANALISE e informe a
complexidade e o valor correspondente. O cliente pode escolher uma faixa MAIOR, nunca
menor que a sua análise. Confirme a faixa e o valor antes de prosseguir.

ORDEM DO ATENDIMENTO:
1) O cliente já assinou o contrato de serviço e fará o pagamento (Asaas) conforme a complexidade.
2) Depois, colete — uma pergunta por vez — as informações necessárias para o contrato:
   partes (nomes/CPF/CNPJ), objeto, valores, forma de pagamento, prazos, garantias,
   penalidades e condições específicas. Não invente nada; pergunte o que faltar.
3) Quando tiver TODAS as informações, ESPELHE o contrato completo: escreva o texto integral
   do contrato, começando OBRIGATORIAMENTE com a linha exata: {MARCADOR}
   e em seguida o contrato em cláusulas numeradas, com qualificação das partes, objeto,
   obrigações, valor, prazo, foro e espaço para assinaturas.
4) Após o espelho, ORIENTE o cliente: aponte de forma simples eventuais pontos de abusividade
   ou risco, e diga que o contrato foi elaborado com base na legislação específica e na
   jurisprudência aplicável, com total segurança jurídica.
5) Peça a APROVAÇÃO do cliente. Só com a aprovação, informe que o contrato final será enviado
   por WhatsApp ou e-mail.

LIMITES ÉTICOS (OAB): jamais minta, jamais garanta resultado, não inclua cláusulas ilegais ou
abusivas; se o cliente pedir algo abusivo, explique o risco e ofereça a alternativa correta.
Privacidade: nunca mencione outros clientes.
"""


def _historico(caso_id: str, limite: int = 50) -> list:
    msgs = get_db().table("mensagens").select("autor,conteudo") \
        .eq("caso_id", caso_id).order("criado_em").limit(limite).execute().data
    return [
        {"role": "user" if m["autor"] == "CLIENTE" else "assistant", "content": m["conteudo"]}
        for m in msgs
    ]


def atender(caso_id: str, mensagem_cliente: str, canal: str = "PORTAL") -> dict:
    db = get_db()
    s = get_settings()
    db.table("mensagens").insert({
        "caso_id": caso_id, "canal": canal, "autor": "CLIENTE", "conteudo": mensagem_cliente,
    }).execute()
    historico = _historico(caso_id)
    try:
        resp = _claude().messages.create(
            model=s.claude_model, max_tokens=2000,
            system=gerar_system_prompt(), messages=historico,
        )
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        if not texto:
            texto = "Recebi sua mensagem e já estou cuidando do seu contrato. Pode me enviar mais um detalhe?"
    except Exception:
        texto = ("Recebi sua mensagem e já estou cuidando da elaboração do seu contrato. "
                 "Me dê só mais um detalhe que eu sigo de onde paramos — não vou te deixar sem resposta.")
    db.table("mensagens").insert({
        "caso_id": caso_id, "canal": canal, "autor": "AGENTE", "conteudo": texto,
    }).execute()
    return {"resposta": texto, "tem_documento": MARCADOR in texto}


def iniciar(nome: str, contato: str, canal: str = "PORTAL", cpf: str | None = None) -> dict:
    """Cria o caso do serviço de contrato e devolve a saudação com a tabela de preços."""
    db = get_db()
    dados_cliente = {"nome": nome, "origem": canal,
                     ("whatsapp" if canal == "WHATSAPP" else "email"): contato}
    if cpf:
        dados_cliente["cpf_cnpj"] = cpf
    cliente = db.table("clientes").insert(dados_cliente).execute().data[0]
    caso = db.table("casos").insert({
        "cliente_id": cliente["id"],
        "relato_inicial": "Solicitação de elaboração de contrato",
        "estado": "LEAD", "grupo": "CONTRATO_SERVICO",
    }).execute().data[0]
    registrar_evento(caso["id"], "CONTRATO_SERVICO_INICIADO", {"nome": nome})
    # grava a saudação fixa (já com a tabela de preços) como primeira mensagem do agente
    db.table("mensagens").insert({
        "caso_id": caso["id"], "canal": canal, "autor": "AGENTE", "conteudo": SAUDACAO_CONTRATO,
    }).execute()
    return {"caso_id": caso["id"], "resposta": SAUDACAO_CONTRATO}
