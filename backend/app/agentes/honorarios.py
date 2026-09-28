"""
HONORÁRIOS — o que foi combinado com o cliente vira cláusula de contrato.

Antes, o valor combinado ficava solto: uma frase no chat, um texto livre no
cadastro do caso e um número fixo dentro do modelo de contrato ("30%",
"10 salários mínimos"). Renegociou? Alguém tinha que lembrar de editar o
documento à mão — e é exatamente aí que entra erro em cláusula de honorários.

Aqui os honorários são dados: percentual, salários mínimos, valor fixo,
entrada e parcelamento. A partir deles a cláusula 4 é escrita por inteiro,
sempre igual ao que está combinado. Toda alteração é registrada com o que
mudou e por quê.

O agente também lê a conversa com o cliente (chat e e-mail) para localizar
o ajuste MAIS RECENTE e propô-lo ao advogado. Ele propõe; quem aplica é o
escritório. Valor de honorários é cláusula contratual, não palpite.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone as _tz

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

CAMPOS = ("hon_percentual", "hon_salarios_minimos", "hon_valor_fixo",
          "hon_entrada", "hon_parcelas", "hon_parcela_valor",
          "hon_vencimento", "hon_forma_pagamento", "hon_observacao")


# ── Formatação em português ──────────────────────────────────────
UNIDADES = ("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete",
            "oito", "nove", "dez", "onze", "doze", "treze", "catorze", "quinze",
            "dezesseis", "dezessete", "dezoito", "dezenove", "vinte")
DEZENAS = {30: "trinta", 40: "quarenta", 50: "cinquenta", 60: "sessenta",
           70: "setenta", 80: "oitenta", 90: "noventa", 100: "cem"}


def por_extenso(n: float) -> str:
    """Número por extenso para os casos que aparecem num contrato: contagem
    de parcelas, de salários mínimos e percentuais. Fora desse alcance,
    devolve o próprio número — melhor do que escrever errado."""
    if n != int(n):
        return f"{n:.1f}".replace(".", ",")
    i = int(n)
    if 0 <= i <= 20:
        return UNIDADES[i]
    if i in DEZENAS:
        return DEZENAS[i]
    if 20 < i < 100:
        d, u = divmod(i, 10)
        base = DEZENAS.get(d * 10)
        if base and u:
            return f"{base} e {UNIDADES[u]}"
        if base:
            return base
    return str(i)


def reais(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


# ── A cláusula ───────────────────────────────────────────────────
def clausula_pagamento(caso: dict) -> dict:
    """Monta o item 4 do contrato a partir do que está combinado.

    Devolve {'titulo', 'itens': [...], 'forma': str, 'resumo': str}. Quando
    nada foi preenchido, devolve itens vazios e o modelo é mantido como
    está — assim um contrato nunca sai sem cláusula de honorários por
    esquecimento de preencher os campos.
    """
    pct = _num(caso.get("hon_percentual"))
    sm = _num(caso.get("hon_salarios_minimos"))
    fixo = _num(caso.get("hon_valor_fixo"))
    entrada = _num(caso.get("hon_entrada"))
    parcelas = int(_num(caso.get("hon_parcelas")) or 0)
    parcela_valor = _num(caso.get("hon_parcela_valor"))
    vencimento = (caso.get("hon_vencimento") or "").strip()
    forma = (caso.get("hon_forma_pagamento") or "").strip()
    obs = (caso.get("hon_observacao") or "").strip()

    itens: list[str] = []
    resumo: list[str] = []

    if pct:
        inteiro = pct == int(pct)
        p = f"{int(pct)}" if inteiro else f"{pct:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        # só escrevemos o percentual por extenso quando ele é inteiro:
        # "33,5% (trinta e três vírgula cinco por cento)" não ajuda ninguém
        extenso = f" ({por_extenso(pct)} por cento)" if inteiro else ""
        itens.append(
            f"{p}%{extenso} sobre o valor total de todo o "
            "proveito econômico obtido na demanda. Entende-se por proveito "
            "econômico toda e qualquer vantagem financeira auferida pelo "
            "CONTRATANTE em razão da presente contratação, incluindo valores "
            "retroativos, parcelas vencidas e vincendas, acordos e condenações."
        )
        resumo.append(f"{p}% do proveito econômico")

    if sm:
        itens.append(
            f"O valor equivalente a {por_extenso(sm)} "
            f"({f'{sm:.0f}' if sm == int(sm) else f'{sm:.1f}'.replace('.', ',')}) "
            "salários mínimos nacionais, vigentes na época do efetivo pagamento, "
            "de modo que o valor devido será apurado pelo salário mínimo em vigor "
            "na data em que o pagamento for realizado."
        )
        resumo.append(f"{por_extenso(sm)} salários mínimos (na data do pagamento)")

    if fixo:
        texto = f"O valor fixo de {reais(fixo)}"
        if entrada and parcelas:
            restante = fixo - entrada
            valor_p = parcela_valor or (restante / parcelas if parcelas else restante)
            texto += (f", sendo {reais(entrada)} a título de entrada, paga na "
                      f"assinatura deste instrumento, e o saldo de {reais(restante)} "
                      f"em {por_extenso(parcelas)} ({parcelas}) parcelas de "
                      f"{reais(valor_p)}")
        elif entrada:
            texto += (f", sendo {reais(entrada)} pagos na assinatura deste "
                      f"instrumento e o saldo de {reais(fixo - entrada)} ao final")
        elif parcelas:
            valor_p = parcela_valor or (fixo / parcelas)
            texto += (f", a ser pago em {por_extenso(parcelas)} ({parcelas}) "
                      f"parcelas de {reais(valor_p)}")
        if vencimento:
            texto += f", com vencimento {vencimento}"
        itens.append(texto + ".")
        resumo.append(reais(fixo) + (f" em {parcelas}x" if parcelas else ""))

    if not itens:
        return {"itens": [], "forma": "", "resumo": ""}

    # 4.2 — como o dinheiro entra. Sujeito sempre no masculino singular
    # ("o valor total dos honorários"), para a concordância não quebrar
    # quando houver uma ou várias alíneas.
    soma = ("O valor total dos honorários, correspondente à soma das verbas "
            "acima," if len(itens) > 1 else "O valor dos honorários acima")
    if forma:
        texto_forma = f"Da Forma de Pagamento: {soma} será pago por meio de {forma}."
    elif pct:
        texto_forma = (f"Da Forma de Pagamento: {soma} será deduzido e pago "
                       "integralmente no momento do efetivo recebimento dos "
                       "valores pelo CONTRATANTE, autorizando este, desde já, "
                       "a retenção da verba honorária.")
    else:
        texto_forma = (f"Da Forma de Pagamento: {soma} será pago diretamente "
                       "pelo CONTRATANTE ao CONTRATADO, nas datas ajustadas.")
    if obs:
        texto_forma += f" {obs}"

    return {"itens": itens, "forma": texto_forma, "resumo": " + ".join(resumo)}


def resumo_curto(caso: dict) -> str:
    return clausula_pagamento(caso).get("resumo", "")


# ── Gravação e histórico ─────────────────────────────────────────
def _so_campos(d: dict) -> dict:
    return {c: d.get(c) for c in CAMPOS}


def salvar(caso_id: str, valores: dict, autor: str = "ESCRITORIO",
           origem: str = "ESCRITORIO", justificativa: str = "") -> dict:
    """Grava os honorários, registra o que mudou e devolve o caso atualizado.

    Não apaga o histórico nem sobrescreve em silêncio: a versão anterior
    fica guardada, com a justificativa da mudança."""
    db = get_db()
    antes = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    novo = {c: valores.get(c) for c in CAMPOS if c in valores}
    if not novo:
        raise ValueError("Nenhum valor de honorários informado.")

    agora = datetime.now(_tz.utc).isoformat()
    novo.update({"hon_atualizado_em": agora, "hon_atualizado_por": autor,
                 "hon_origem": origem, "atualizado_em": agora})
    depois = db.table("casos").update(novo).eq("id", caso_id) \
               .execute().data[0]

    if _so_campos(antes) != _so_campos(depois):
        try:
            db.table("honorarios_historico").insert({
                "caso_id": caso_id, "anterior": _so_campos(antes),
                "novo": _so_campos(depois), "origem": origem,
                "justificativa": justificativa[:2000] or None, "autor": autor,
            }).execute()
        except Exception:
            pass
        registrar_evento(caso_id, "HONORARIOS_ALTERADOS",
                         {"anterior": _so_campos(antes), "novo": _so_campos(depois),
                          "origem": origem, "resumo": resumo_curto(depois)})
        # o combinado também entra na conversa, para ficar no histórico que
        # o cliente e o escritório enxergam
        try:
            db.table("mensagens").insert({
                "caso_id": caso_id, "canal": "CRM", "autor": "HUMANO",
                "conteudo": f"💼 Honorários ajustados: {resumo_curto(depois)}."
                            + (f"\nMotivo: {justificativa}" if justificativa else ""),
            }).execute()
        except Exception:
            pass
        depois["_refeitos"] = refazer_documentos(caso_id)
    return depois


# ── Documentos acompanham os valores ─────────────────────────────
def refazer_documentos(caso_id: str) -> dict:
    """Depois de mudar os honorários, acerta os documentos do caso.

    Quem ainda está EM_REVISAO é refeito na hora, com os novos valores.
    Quem já foi ENVIADO ou ASSINADO não se toca: o cliente tem aquela via
    na mão, e trocar o texto por baixo seria o pior dos mundos. Esses ficam
    sinalizados, e o advogado decide se emite uma nova via.
    """
    from . import documentos as redator
    db = get_db()
    refeitos, desatualizados, erros = [], [], []

    docs = db.table("documentos_assinatura").select("id,tipo,titulo,status") \
             .eq("caso_id", caso_id).neq("tipo", "OUTRO").execute().data or []
    for d in docs:
        if d["tipo"] != "CONTRATO":
            continue          # só o contrato carrega cláusula de honorários
        if d["status"] == "EM_REVISAO":
            try:
                novo = redator.gerar(caso_id, "CONTRATO", titulo_livre=d["titulo"])
                if novo.get("ok"):
                    db.table("documentos_assinatura").update({"status": "SUBSTITUIDO"}) \
                      .eq("id", d["id"]).execute()
                    refeitos.append(d["titulo"])
                else:
                    erros.append(novo.get("mensagem") or "não foi possível refazer")
            except Exception as e:
                erros.append(str(e)[:200])
        elif d["status"] in ("ENVIADO", "APROVADO", "ASSINADO"):
            desatualizados.append(d["titulo"])

    if desatualizados:
        try:
            db.table("mensagens").insert({
                "caso_id": caso_id, "canal": "CRM", "autor": "HUMANO",
                "conteudo": "⚠ Os honorários mudaram e estes documentos já "
                            "estavam com o cliente: " + ", ".join(desatualizados)
                            + ". Eles NÃO foram alterados. Gere uma nova via se "
                              "quiser que o cliente assine com os novos valores.",
            }).execute()
        except Exception:
            pass

    return {"refeitos": refeitos, "desatualizados": desatualizados, "erros": erros}


def documento_desatualizado(doc: dict, caso: dict) -> bool:
    """O documento foi gerado antes da última mudança de honorários?"""
    if doc.get("tipo") != "CONTRATO":
        return False
    mudou = caso.get("hon_atualizado_em")
    if not mudou:
        return False
    versao = doc.get("honorarios_versao")
    return (versao or "") < mudou


# ── Leitura da conversa ──────────────────────────────────────────
INSTRUCAO = """Você lê a conversa entre um escritório de advocacia e seu cliente
e identifica APENAS o que foi combinado sobre HONORÁRIOS ADVOCATÍCIOS.

Regras:
- Vale o ajuste MAIS RECENTE. Se o valor mudou ao longo da conversa, devolva
  o último combinado e ignore os anteriores.
- Só considere valor efetivamente ACORDADO ou PROPOSTO pelo escritório. Não
  invente, não arredonde, não complete o que não foi dito.
- Se a conversa não trata de honorários, devolva tudo nulo e encontrado=false.
- Não confunda o valor da causa, o valor do benefício ou a dívida discutida
  com os honorários do advogado.

Responda SOMENTE com JSON, neste formato:
{
  "encontrado": true|false,
  "hon_percentual": número ou null,
  "hon_salarios_minimos": número ou null,
  "hon_valor_fixo": número ou null,
  "hon_entrada": número ou null,
  "hon_parcelas": inteiro ou null,
  "hon_parcela_valor": número ou null,
  "hon_vencimento": "texto curto" ou null,
  "hon_forma_pagamento": "texto curto" ou null,
  "hon_observacao": "condição combinada fora do padrão" ou null,
  "trecho": "a frase exata da conversa em que o valor foi combinado",
  "confianca": "ALTA"|"MEDIA"|"BAIXA"
}"""


def ler_da_conversa(caso_id: str) -> dict:
    """Lê a conversa do caso e devolve o que o agente entendeu por honorários.

    Devolve sugestão, nunca grava: o advogado confere o trecho de origem e
    aplica se estiver correto."""
    s = get_settings()
    db = get_db()
    msgs = db.table("mensagens").select("autor,canal,conteudo,criado_em") \
             .eq("caso_id", caso_id).order("criado_em").limit(200).execute().data or []
    if not msgs:
        return {"encontrado": False, "motivo": "Ainda não há conversa neste caso."}

    linhas = []
    for m in msgs:
        quem = {"CLIENTE": "CLIENTE", "HUMANO": "ESCRITÓRIO"}.get(m["autor"], "ASSISTENTE")
        data = (m.get("criado_em") or "")[:10]
        linhas.append(f"[{data}] {quem}: {(m.get('conteudo') or '').strip()}")
    conversa = "\n".join(linhas)[-18000:]

    caso = db.table("casos").select("hon_percentual,hon_salarios_minimos,"
                                    "hon_valor_fixo,honorarios_valor") \
             .eq("id", caso_id).single().execute().data or {}

    cliente = anthropic.Anthropic(api_key=s.claude_api_key)
    r = cliente.messages.create(
        model=s.claude_model,
        max_tokens=1200,
        system=INSTRUCAO,
        messages=[{"role": "user", "content":
                   f"Honorários hoje cadastrados no caso: {json.dumps(caso, default=str)}\n\n"
                   f"CONVERSA:\n{conversa}"}],
    )
    bruto = "".join(b.text for b in r.content if b.type == "text").strip()
    m = re.search(r"\{.*\}", bruto, re.S)
    if not m:
        return {"encontrado": False, "motivo": "Não foi possível interpretar a conversa."}
    try:
        dados = json.loads(m.group(0))
    except Exception:
        return {"encontrado": False, "motivo": "Não foi possível interpretar a conversa."}

    registrar_evento(caso_id, "HONORARIOS_LIDOS_DA_CONVERSA",
                     {"encontrado": bool(dados.get("encontrado")),
                      "confianca": dados.get("confianca"),
                      "trecho": (dados.get("trecho") or "")[:300]})
    return dados
