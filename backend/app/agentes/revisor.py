"""
REVISOR — confere o documento antes de ele sair para assinatura.

O documento gerado é uma minuta, não uma verdade. Entre gerar e enviar,
muita coisa muda: o cliente corrige o endereço, o valor é renegociado no
chat, a comarca muda porque ele se mudou. Quem assina é o cliente, e o que
está escrito no papel é o que vale — então antes de enviar alguém precisa
conferir campo a campo se o documento reflete o cadastro e o que foi
combinado na conversa.

Este módulo faz isso em duas camadas:

  1. CONFERÊNCIA OBJETIVA — compara o texto do documento com o que a
     plataforma tem hoje: qualificação, CPF, endereço, foro, local e data,
     e a cláusula de honorários. Aqui não há interpretação: ou bate ou não
     bate, e o que não bate é corrigível automaticamente.

  2. LEITURA DA CONVERSA — o agente lê o histórico com o cliente e aponta
     o que foi combinado e não está no documento, além de pontos que
     deixam o escritório exposto (obrigação sem contrapartida, prazo
     impossível, promessa de resultado, ausência de cláusula de rescisão).

O revisor APONTA e, quando o senhor manda, o documento é refeito por
inteiro a partir do modelo do escritório com os dados atuais. Documento já
assinado nunca é alterado.
"""
from __future__ import annotations

import json
import re
import unicodedata

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from . import documentos as redator
from . import honorarios as hon


def _limpo(t: str) -> str:
    """Compara texto ignorando acento, caixa e espaço — as diferenças que
    não são diferença de conteúdo."""
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def _texto_do_documento(doc: dict) -> list[str]:
    from docx import Document
    import io
    s = get_settings()
    dados = get_db().storage.from_(s.bucket_documentos).download(doc["storage_path"])
    d = Document(io.BytesIO(dados))
    return [p.text.strip() for p in d.paragraphs if p.text.strip()]


# ── Camada 1: conferência objetiva ───────────────────────────────
def conferir_campos(doc: dict, caso: dict, cli: dict) -> list[dict]:
    """Cada item devolve {campo, esperado, ok, achado}. `ok=False` significa
    que o documento está diferente do cadastro — não necessariamente errado,
    mas precisa de decisão."""
    paragrafos = _texto_do_documento(doc)
    inteiro = _limpo(" ".join(paragrafos))
    itens: list[dict] = []

    def checar(campo: str, esperado: str, obrigatorio: bool = True):
        if not esperado:
            if obrigatorio:
                itens.append({"campo": campo, "esperado": "(não cadastrado)",
                              "ok": False, "achado": "falta no cadastro"})
            return
        itens.append({"campo": campo, "esperado": esperado,
                      "ok": _limpo(esperado) in inteiro,
                      "achado": "confere" if _limpo(esperado) in inteiro
                                else "não encontrado no documento"})

    checar("Nome do cliente", (cli.get("nome") or "").strip())
    cpf = redator._cpf_formatado(cli.get("cpf_cnpj"))
    checar("CPF", cpf)
    checar("Endereço", (cli.get("endereco_rua") or "").strip())
    checar("Cidade", (cli.get("endereco_cidade") or "").strip())
    checar("Qualificação completa", redator.montar_qualificacao(cli))
    checar("Foro", redator.comarca_do_cliente(cli))
    checar("Local e data", redator.local_e_data(cli))

    # honorários: só fazem sentido no contrato
    if doc.get("tipo") == "CONTRATO":
        clausula = hon.clausula_pagamento(caso)
        if not clausula.get("itens"):
            itens.append({"campo": "Honorários", "esperado": "(não cadastrados)",
                          "ok": False,
                          "achado": "o contrato saiu com o texto padrão do modelo; "
                                    "cadastre o combinado em Honorários"})
        else:
            for n, texto in enumerate(clausula["itens"], 1):
                # compara o começo da alínea, que é onde está o valor
                chave = _limpo(texto)[:70]
                itens.append({"campo": f"Honorários — alínea {n}",
                              "esperado": texto[:120],
                              "ok": chave in inteiro,
                              "achado": "confere" if chave in inteiro
                                        else "o documento tem outro valor"})

    # o tópico de comunicação passou a ser obrigatório no contrato
    if doc.get("tipo") == "CONTRATO":
        tem = "canais oficiais do escritorio" in inteiro
        itens.append({"campo": "Cláusula de comunicação", "esperado": "presente",
                      "ok": tem,
                      "achado": "presente" if tem
                                else "falta o tópico de canais oficiais e painel do cliente"})
    return itens


# ── Camada 2: o que a conversa diz ───────────────────────────────
INSTRUCAO = """Você é o revisor de documentos de um escritório de advocacia
brasileiro. Recebe o texto de um documento (contrato, procuração ou
declaração) e a conversa com o cliente. Sua tarefa é apontar o que está
errado ou arriscado — não reescrever o documento.

Procure, nesta ordem:
1. DIVERGÊNCIA: algo combinado na conversa que o documento contradiz ou
   omite (valores, forma de pagamento, objeto da ação, prazos, condições).
2. RISCO PARA O ESCRITÓRIO: promessa de resultado, obrigação sem
   contrapartida, prazo que não depende do advogado, ausência de previsão
   de rescisão ou de reembolso de custas, cláusula que permita ao cliente
   revogar sem pagar o serviço já prestado.
3. ERRO MATERIAL: nome, número, data ou qualificação inconsistentes DENTRO
   do próprio documento.

Regras:
- Não invente combinação que não esteja na conversa.
- Se a conversa não trata do assunto, não é divergência.
- Seja específico: cite o trecho do documento e o da conversa.
- Gravidade ALTA só para o que impede o envio ou expõe o escritório.

Responda SOMENTE com JSON:
{
  "divergencias": [
    {"gravidade":"ALTA|MEDIA|BAIXA","o_que":"...","no_documento":"...",
     "na_conversa":"...","sugestao":"..."}
  ],
  "riscos": [
    {"gravidade":"ALTA|MEDIA|BAIXA","o_que":"...","sugestao":"..."}
  ],
  "parecer": "uma frase dizendo se pode enviar como está"
}"""


def ler_com_a_conversa(doc: dict, paragrafos: list[str]) -> dict:
    s = get_settings()
    db = get_db()
    msgs = db.table("mensagens").select("autor,conteudo,criado_em") \
             .eq("caso_id", doc["caso_id"]).order("criado_em") \
             .limit(200).execute().data or []
    if not msgs:
        return {"divergencias": [], "riscos": [],
                "parecer": "Não há conversa registrada neste caso para comparar."}

    conversa = "\n".join(
        f"[{(m.get('criado_em') or '')[:10]}] "
        f"{ {'CLIENTE':'CLIENTE','HUMANO':'ESCRITÓRIO'}.get(m['autor'],'ASSISTENTE') }: "
        f"{(m.get('conteudo') or '').strip()}"
        for m in msgs)[-14000:]
    texto = "\n".join(paragrafos)[-24000:]

    cliente = anthropic.Anthropic(api_key=s.claude_api_key)
    r = cliente.messages.create(
        model=s.claude_model, max_tokens=2000, system=INSTRUCAO,
        messages=[{"role": "user", "content":
                   f"DOCUMENTO ({doc.get('titulo')}):\n{texto}\n\n"
                   f"CONVERSA COM O CLIENTE:\n{conversa}"}],
    )
    bruto = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", bruto, re.S)
    if not m:
        return {"divergencias": [], "riscos": [],
                "parecer": "Não foi possível concluir a leitura da conversa."}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"divergencias": [], "riscos": [],
                "parecer": "Não foi possível concluir a leitura da conversa."}


# ── Ponto de entrada ─────────────────────────────────────────────
def revisar(documento_id: str) -> dict:
    db = get_db()
    doc = db.table("documentos_assinatura").select("*") \
            .eq("id", documento_id).single().execute().data
    if not doc:
        raise ValueError("Documento não encontrado.")
    caso = db.table("casos").select("*, clientes(*)") \
             .eq("id", doc["caso_id"]).single().execute().data
    cli = caso.get("clientes") or {}

    if doc.get("tipo") == "OUTRO" or not doc.get("storage_path", "").endswith(".docx"):
        return {"ok": True, "tipo": doc.get("tipo"),
                "aviso": "Documento anexado pelo escritório: a revisão automática "
                         "vale para os documentos que a plataforma redige.",
                "conferencia": [], "divergencias": [], "riscos": []}

    paragrafos = _texto_do_documento(doc)
    conferencia = conferir_campos(doc, caso, cli)
    leitura = ler_com_a_conversa(doc, paragrafos)

    fora = [c for c in conferencia if not c["ok"]]
    graves = [d for d in (leitura.get("divergencias") or [])
              if d.get("gravidade") == "ALTA"]
    pode_enviar = not fora and not graves

    registrar_evento(doc["caso_id"], "DOCUMENTO_REVISADO",
                     {"documento_id": documento_id, "fora_do_cadastro": len(fora),
                      "divergencias": len(leitura.get("divergencias") or []),
                      "riscos": len(leitura.get("riscos") or []),
                      "pode_enviar": pode_enviar})

    return {"ok": True, "titulo": doc.get("titulo"), "status": doc.get("status"),
            "conferencia": conferencia,
            "divergencias": leitura.get("divergencias") or [],
            "riscos": leitura.get("riscos") or [],
            "parecer": leitura.get("parecer") or "",
            "pode_enviar": pode_enviar,
            "pode_atualizar": doc.get("status") != "ASSINADO"}


def atualizar_na_integra(documento_id: str) -> dict:
    """Refaz o documento inteiro a partir do modelo do escritório, com os
    dados que a plataforma tem hoje. O anterior fica guardado como
    substituído; documento assinado não se toca."""
    db = get_db()
    doc = db.table("documentos_assinatura").select("*") \
            .eq("id", documento_id).single().execute().data
    if not doc:
        raise ValueError("Documento não encontrado.")
    if doc["status"] == "ASSINADO":
        raise ValueError("Este documento já foi assinado pelo cliente e não "
                         "pode ser alterado. Gere um aditivo ou uma nova via.")
    if doc["tipo"] == "OUTRO":
        raise ValueError("Documento anexado pelo escritório: substitua o "
                         "arquivo em 'Outros'.")

    novo = redator.gerar(doc["caso_id"], doc["tipo"], titulo_livre=doc["titulo"])
    if not novo.get("ok"):
        raise ValueError(novo.get("mensagem") or "Não foi possível refazer o documento.")

    db.table("documentos_assinatura").update({"status": "SUBSTITUIDO"}) \
      .eq("id", documento_id).execute()
    registrar_evento(doc["caso_id"], "DOCUMENTO_ATUALIZADO_INTEGRAL",
                     {"anterior": documento_id, "novo": novo["documento"]["id"],
                      "tipo": doc["tipo"], "status_anterior": doc["status"]})
    try:
        db.table("mensagens").insert({
            "caso_id": doc["caso_id"], "canal": "CRM", "autor": "HUMANO",
            "conteudo": f"📝 {doc['titulo']} foi refeito por inteiro com os dados "
                        "atuais do cadastro e o combinado na conversa."
                        + (" A via anterior já estava com o cliente — envie a nova "
                           "se quiser que ele assine esta."
                           if doc["status"] in ("ENVIADO", "APROVADO") else ""),
        }).execute()
    except Exception:
        pass
    return {"ok": True, "documento": novo["documento"],
            "substituiu": documento_id,
            "aviso": ("A via anterior já havia sido enviada ao cliente."
                      if doc["status"] in ("ENVIADO", "APROVADO") else "")}
