"""
REDATOR DA INICIAL — monta a minuta e deixa as tags no lugar certo.

Este é o passo anterior ao agente de precedentes. Ele escreve a peça a
partir do relato do cliente e das teses do grupo, mas NÃO cita
jurisprudência: onde a citação deve entrar, ele deixa a marcação

    [INSERIR_JURISPRUDENCIA_TEMA: "tema em poucas palavras"]

A divisão é proposital. Um único agente que redige e cita ao mesmo tempo
tende a produzir a ementa que faria falta — inventando número e texto de
acórdão. Separando as duas tarefas, quem redige não tem como citar, e quem
cita não tem como escrever ementa: só escolhe entre julgados reais do banco.

O que sai daqui é minuta, não peça pronta. O advogado revisa, o agente de
precedentes preenche as citações, e só então vai para protocolo.
"""
from __future__ import annotations

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

INSTRUCAO = """Você é redator de petições iniciais da FC Advocacia, escritório
do Dr. Fábio Silva Cunha (OAB/RO 10.849), que atua em Rondônia e Santa
Catarina. Redige em português jurídico brasileiro, sóbrio e direto.

REGRA QUE NÃO SE QUEBRA: você NÃO cita jurisprudência. Não escreve ementa,
não menciona número de acórdão, não nomeia relator, não inventa precedente.
Onde a citação de julgado seria necessária para sustentar o argumento, você
deixa EXATAMENTE esta marcação, em linha própria:

[INSERIR_JURISPRUDENCIA_TEMA: "matéria em poucas palavras"]

O tema entre aspas deve descrever a QUESTÃO JURÍDICA, não o pedido. Bom:
"abusividade da tarifa de cadastro em contrato bancário". Ruim: "provar que
o banco errou". Use de duas a cinco marcações — uma por tese relevante,
colocada logo após o argumento que ela sustenta.

TAMBÉM NÃO INVENTE FATO. Trabalhe apenas com o que está no relato e nos
documentos informados. Fato que falta vira pedido de diligência ou some da
peça — nunca é preenchido por suposição. Não prometa resultado, não estime
valor de condenação que não decorra do que foi informado.

ESTRUTURA (markdown, com ## nos títulos):
## ENDEREÇAMENTO — juízo competente, conforme a comarca informada
## QUALIFICAÇÃO DAS PARTES — use exatamente os dados fornecidos
## DOS FATOS — narrativa cronológica, cada fato remetendo à prova que o
   demonstra; quando faltar prova, diga que será requerida
## DO DIREITO — fundamentos legais e as marcações de jurisprudência
## DA TUTELA DE URGÊNCIA — só se houver, no relato, elemento concreto de
   urgência e de risco; não havendo, omita a seção inteira
## DOS PEDIDOS — numerados, claros, coerentes com os fatos narrados
## DO VALOR DA CAUSA
## DAS PROVAS

Escreva a peça inteira. Não escreva comentários fora dela."""


def redigir(caso_id: str, instrucao: str | None = None) -> str:
    s = get_settings()
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id) \
             .single().execute().data
    if not caso:
        raise ValueError("Caso não encontrado.")
    cli = caso.get("clientes") or {}
    if not (caso.get("relato_inicial") or "").strip():
        raise ValueError("O caso não tem relato: sem ele não há o que redigir.")

    # as teses do grupo dão a diretriz de redação já validada pelo escritório
    teses = []
    try:
        teses = db.table("teses").select(
            "titulo,ratio_decidendi,argumentos_chave,diretriz_redacao,documentos_vitais"
        ).eq("grupo", caso.get("grupo") or "").limit(6).execute().data or []
    except Exception:
        pass

    docs = []
    try:
        docs = [d.get("observacao") or d.get("tipo") for d in (
            db.table("documentos").select("tipo,observacao")
              .eq("caso_id", caso_id).limit(40).execute().data or [])]
    except Exception:
        pass

    from .documentos import montar_qualificacao, comarca_do_cliente
    contexto = f"""COMARCA: {comarca_do_cliente(cli)}
QUALIFICAÇÃO DO AUTOR: {montar_qualificacao(cli)}
GRUPO/MATÉRIA: {caso.get('grupo') or '—'}
TÍTULO DO CASO: {caso.get('titulo') or '—'}

RELATO DO CLIENTE:
{caso.get('relato_inicial')}

DOCUMENTOS JÁ JUNTADOS AO CASO:
{chr(10).join('- ' + str(d) for d in docs) if docs else '- (nenhum registrado)'}

TESES DO ESCRITÓRIO PARA ESTA MATÉRIA (diretriz interna, não são citações):
{chr(10).join('- ' + (t.get('titulo') or '') + ': ' + (t.get('diretriz_redacao') or t.get('ratio_decidendi') or '')[:400] for t in teses) if teses else '- (banco de teses vazio para este grupo)'}
"""
    if instrucao:
        contexto += f"\nORIENTAÇÃO DO ADVOGADO: {instrucao}\n"

    cliente = anthropic.Anthropic(api_key=s.claude_api_key)
    r = cliente.messages.create(
        model=s.claude_model, max_tokens=8000, system=INSTRUCAO,
        messages=[{"role": "user", "content": contexto}],
    )
    texto = "".join(b.text for b in r.content if b.type == "text").strip()
    registrar_evento(caso_id, "MINUTA_REDIGIDA", {"caracteres": len(texto)})
    return texto
