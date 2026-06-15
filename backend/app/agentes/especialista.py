"""
AGENTE ESPECIALISTA — um por GRUPO de teses.

Quando a triagem identifica o grupo do caso (ex: BANCARIO), o
especialista daquele grupo ASSUME o cliente e conduz toda a jornada:
atendimento humanizado → qualificação do lead → demonstração de
viabilidade → proposta → contrato (ZapSign) → cobrança (Asaas) →
coleta de documentos vitais da tese → depoimentos/provas → análise
→ petição. Se detectar dificuldade, demora ou pedido, escala para
o advogado humano e oferece agendamento.

O system prompt é GERADO a partir das teses ativas do grupo:
o especialista sempre fala com o entendimento jurisprudencial atual.
"""
import json
import anthropic
from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from .orquestrador import mudar_estado, escalar_para_humano

_client = None
def _claude():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=get_settings().claude_api_key)
    return _client


# ── Geração do system prompt do especialista a partir das teses ──
def gerar_system_prompt(grupo: str) -> str:
    db = get_db()
    teses = db.table("teses").select(
        "id,titulo,subtipo,ratio_decidendi,documentos_vitais,argumentos_chave,honorarios"
    ).eq("grupo", grupo).eq("overruled", False).execute().data

    s = get_settings()
    resumo = json.dumps(teses, ensure_ascii=False, indent=1)

    return f"""
Você é o Agente Especialista em {grupo} do escritório FSC ADVOCACIA
(Dr. {s.advogado}, {s.oab}). Você assume o cliente do primeiro contato
até a petição, de forma HUMANIZADA: trate pelo nome, linguagem simples,
empatia real, sem juridiquês desnecessário.

TAMANHO DAS RESPOSTAS (REGRA FORTE): responda SEMPRE curto — no máximo
3 frases por mensagem, como uma conversa de WhatsApp. Nada de textão,
listas ou parágrafos longos. Uma pergunta de cada vez.

CADASTRO NA PLATAFORMA: logo no início, convide o cliente a se cadastrar
em app.fscadvocaciadigital.com.br para acompanhar as fases do caso pela
plataforma. Reforce de forma leve durante o atendimento.

AGENDAMENTO E WHATSAPP: se o cliente quiser falar com o advogado, marcar
uma reunião, ou preferir continuar por WhatsApp, ofereça SEMPRE estas opções:
- Agendar reunião pelo link: {s.link_agenda_padrao or 'https://cal.com/fabio-silva-foo0mb/30min'}
- Falar no WhatsApp do escritório: {('https://wa.me/' + s.humano_whatsapp) if s.humano_whatsapp else 'o botão de WhatsApp no site'}
Compartilhe o link diretamente na conversa quando fizer sentido.

TESES ATIVAS DO SEU GRUPO (sua base de conhecimento — entendimento atual dos tribunais):
{resumo}

SUA CONDUÇÃO, ETAPA POR ETAPA:
1. QUALIFICACAO: entenda o relato, identifique a tese aplicável do seu grupo,
   faça no máximo 2-3 perguntas por mensagem. Ao qualificar, JÁ DEMONSTRE a
   possibilidade concreta de resolução citando o entendimento pacificado
   (sem prometer resultado — diga "os tribunais têm decidido que...").
2. PROPOSTA: explique honorários conforme a tese (MASSA = tabela;
   ALTA_COMPLEXIDADE = 50% do proveito econômico) e colete os dados para o
   contrato: nome completo, CPF, endereço, e-mail, estado civil, profissão.
3. CONTRATO: informe que o contrato chegará por e-mail/WhatsApp via ZapSign
   para assinatura digital. NÃO avance sem assinatura confirmada.
4. PAGAMENTO: informe que o link de pagamento chegará (Asaas).
   NÃO avance sem confirmação.
5. COLETA_DOCS: solicite EXATAMENTE os documentos_vitais da tese aplicável,
   um grupo por vez, explicando POR QUE cada documento importa.
6. COLETA_PROVAS: colha o depoimento detalhado dos fatos (datas, valores,
   nomes) e provas complementares.

REGRAS DE ESCALAÇÃO (use a ferramenta 'escalar'):
- Cliente com dificuldade real (não entende, reclama, situação delicada);
- Demora: documentos prometidos e não enviados;
- Pedido explícito de falar com advogado;
- Caso juridicamente fora das suas teses ou complexo demais.
Ao escalar, ofereça ao cliente agendar atendimento com o advogado
especialista responsável pela demanda.

ÁUDIO: suas respostas podem ser convertidas em mensagem de VOZ
(voz do Dr. {s.advogado}). Por isso escreva como se fala: frases curtas,
sem listas, sem símbolos, sem juridiquês — natural e acolhedor.

REGRAS ABSOLUTAS:
- JAMAIS invente fatos, valores, prazos ou jurisprudência.
- JAMAIS garanta resultado ("você vai ganhar").
- Não dê aconselhamento definitivo: a palavra final é do Dr. {s.advogado}.
- Privacidade: nunca mencione outros clientes ou casos.
"""


# ── Ferramentas que o especialista pode acionar ──────────────────
TOOLS = [
    {
        "name": "avancar_etapa",
        "description": "Avança o caso para a próxima etapa da jornada quando os requisitos da etapa atual foram cumpridos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "novo_estado": {"type": "string", "enum": [
                    "QUALIFICACAO", "PROPOSTA", "CONTRATO", "COLETA_PROVAS", "ANALISE", "INVIAVEL"]},
                "tese_id": {"type": "string", "description": "Tese identificada (na qualificação)"},
                "resumo": {"type": "string"}
            },
            "required": ["novo_estado", "resumo"]
        }
    },
    {
        "name": "escalar",
        "description": "Escala o caso para o advogado humano (dificuldade, demora, pedido do cliente ou complexidade).",
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string", "enum": [
                    "DIFICULDADE", "DEMORA_DOCS", "PEDIDO_CLIENTE", "JURIDICO_COMPLEXO"]},
                "detalhe": {"type": "string"}
            },
            "required": ["motivo", "detalhe"]
        }
    },
    {
        "name": "registrar_dados_contrato",
        "description": "Registra os dados cadastrais coletados para gerar contrato e cobrança.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string"}, "cpf": {"type": "string"},
                "email": {"type": "string"}, "endereco": {"type": "string"},
                "estado_civil": {"type": "string"}, "profissao": {"type": "string"},
                "valor_honorarios": {"type": "string"}
            },
            "required": ["nome", "cpf", "email"]
        }
    },
]


def _historico(caso_id: str, limite: int = 30) -> list:
    msgs = get_db().table("mensagens").select("autor,conteudo") \
        .eq("caso_id", caso_id).order("criado_em", desc=True).limit(limite) \
        .execute().data
    msgs.reverse()
    return [
        {"role": "user" if m["autor"] == "CLIENTE" else "assistant",
         "content": m["conteudo"]}
        for m in msgs
    ]


def atender(caso_id: str, mensagem_cliente: str, canal: str = "PORTAL") -> dict:
    """Ponto de entrada: o especialista do grupo responde o cliente
    e aciona ferramentas (avançar etapa, escalar, registrar dados)."""
    db = get_db()
    s = get_settings()

    caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    grupo = caso.get("grupo") or "OUTROS"

    # grava a mensagem do cliente
    db.table("mensagens").insert({
        "caso_id": caso_id, "canal": canal, "autor": "CLIENTE",
        "conteudo": mensagem_cliente
    }).execute()

    # caso escalado → humano responde; o agente não interfere
    if caso["estado"] in ("ESCALADO_HUMANO", "AGENDADO"):
        return {"resposta": None, "estado": caso["estado"],
                "aviso": "Caso sob condução humana."}

    # dados já conhecidos do cliente — para NÃO repetir perguntas e usar o nome
    cli = db.table("clientes").select("nome,email,cpf_cnpj,whatsapp") \
            .eq("id", caso["cliente_id"]).maybe_single().execute().data or {}
    conhecidos = ", ".join(
        f"{k}={v}" for k, v in {
            "nome": cli.get("nome"), "email": cli.get("email"),
            "cpf": cli.get("cpf_cnpj"), "whatsapp": cli.get("whatsapp"),
        }.items() if v
    )
    primeiro_nome = (cli.get("nome") or "").split(" ")[0] if cli.get("nome") else ""

    system = gerar_system_prompt(grupo) + \
        f"\n\nESTADO ATUAL DO CASO: {caso['estado']}. " \
        f"Tese já identificada: {caso.get('tese_id') or 'ainda não'}." + \
        f"\n\nDADOS JÁ CONHECIDOS DO CLIENTE — é PROIBIDO perguntar de novo " \
        f"qualquer um destes; use-os diretamente: {conhecidos or 'nenhum'}. " \
        f"Dirija-se ao cliente pelo primeiro nome ('{primeiro_nome}') em TODA " \
        f"mensagem. Antes de perguntar algo, confira o histórico: se o cliente " \
        f"já respondeu, NÃO repita a pergunta."

    historico = _historico(caso_id)
    historico.append({"role": "user", "content": mensagem_cliente})

    texto_resposta, acoes = "", []
    try:
        resposta = _claude().messages.create(
            model=s.claude_model,
            max_tokens=600,
            system=system,
            tools=TOOLS,
            messages=historico,
        )
        for bloco in resposta.content:
            if bloco.type == "text":
                texto_resposta += bloco.text
            elif bloco.type == "tool_use":
                try:
                    acoes.append(_executar_ferramenta(caso_id, caso, bloco.name, bloco.input))
                except Exception as e:
                    registrar_evento(caso_id, "ERRO_FERRAMENTA",
                                     {"ferramenta": bloco.name, "erro": str(e)})
    except Exception as e:
        registrar_evento(caso_id, "ERRO_AGENTE", {"erro": str(e)})
        texto_resposta = (f"{primeiro_nome + ', ' if primeiro_nome else ''}"
                          "tive uma instabilidade rápida aqui. Pode repetir a "
                          "última mensagem? Já retomo seu atendimento.")

    if texto_resposta:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": canal, "autor": "AGENTE",
            "conteudo": texto_resposta
        }).execute()

    return {"resposta": texto_resposta, "acoes": acoes,
            "estado": db.table("casos").select("estado").eq("id", caso_id)
                        .single().execute().data["estado"]}


def _executar_ferramenta(caso_id: str, caso: dict, nome: str, dados: dict) -> dict:
    db = get_db()

    if nome == "escalar":
        r = escalar_para_humano(caso_id, dados["motivo"], dados.get("detalhe", ""))
        return {"ferramenta": "escalar", **dados,
                "link_agenda": r.get("link_agenda")}

    if nome == "avancar_etapa":
        novo = dados["novo_estado"]
        if dados.get("tese_id"):
            # grava a tese E o subtipo (subnicho) — espelha a organização das pastas
            tese = db.table("teses").select("subtipo").eq("id", dados["tese_id"]) \
                     .maybe_single().execute().data or {}
            db.table("casos").update({
                "tese_id": dados["tese_id"],
                "subtipo": tese.get("subtipo"),
            }).eq("id", caso_id).execute()
        mudar_estado(caso_id, novo, motivo=dados.get("resumo", ""))

        # gatilhos automáticos das etapas transacionais
        if novo == "CONTRATO":
            from ..integracoes.zapsign import enviar_contrato
            enviar_contrato(caso_id)
        return {"ferramenta": "avancar_etapa", "novo_estado": novo}

    if nome == "registrar_dados_contrato":
        db.table("clientes").update({
            "nome": dados.get("nome"), "cpf_cnpj": dados.get("cpf"),
            "email": dados.get("email"),
        }).eq("id", caso["cliente_id"]).execute()
        if dados.get("valor_honorarios"):
            db.table("casos").update(
                {"honorarios_valor": dados["valor_honorarios"]}
            ).eq("id", caso_id).execute()
        registrar_evento(caso_id, "DADOS_CONTRATO_REGISTRADOS", dados)
        return {"ferramenta": "registrar_dados_contrato", "ok": True}

    return {"ferramenta": nome, "erro": "desconhecida"}
