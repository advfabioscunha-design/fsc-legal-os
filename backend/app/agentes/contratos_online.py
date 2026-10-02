"""
Balcão de contratos — do pedido do cliente ao documento assinado.

O caminho, e o que cada etapa protege:

  COLETA      o atendente pergunta o que o tipo de contrato exige
  CIENCIA     quando o combinado foge da lei, o cliente lê o que a lei
              diz e escolhe: adequar ou seguir assim mesmo. A escolha
              fica registrada com data, hora e versão do texto
  PAGAMENTO   PIX; o trabalho começa depois de confirmado
  REDACAO     o redator escreve seguindo a lei do tipo
  REVISAO_IA  o revisor lê a íntegra e anota o que precisa mudar
  AJUSTE      o redator corrige — este botão só abre depois da revisão
  REVISAO_ADV o advogado lê e aprova. Nada chega ao cliente sem isso
  APROVACAO   o cliente vê com marca d'água e aprova ou pede mudança
  ASSINATURA  assinatura eletrônica; cópia por e-mail quando todos
              tiverem assinado
  ENTREGUE    fica 7 dias à vista e depois vai para o arquivo

SOBRE ORIENTAR E PROSSEGUIR
---------------------------
O escritório não recusa o serviço porque o cliente quer algo fora do
usual. Orienta com clareza, registra a ciência e segue. Mas há duas
situações diferentes, e tratá-las igual seria desonesto:

  RISCO      a cláusula vale, só não produz o efeito que o cliente
             imagina, ou pode ser revista em juízo. Ciência resolve:
             ele decide com a informação na mão.

  NULIDADE   a lei diz que aquilo não tem efeito nenhum (garantia
             dupla na locação, por exemplo). Aqui a ciência também é
             registrada, e o texto diz com todas as letras que a
             cláusula é nula — mas quem decide se entra no documento é
             o advogado na revisão humana, não o cliente e não a
             máquina. É para isso que existe aquela etapa.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from ..core.ia import TEMPO_LIMITE, TENTATIVAS

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..core import dados as _dados
from . import catalogo_contratos as catalogo

VERSAO_TERMO = "2026-09-v1"
VERSAO_CONTRATACAO = "2026-09-v1"


def _reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def termo_de_contratacao(tipo: str, com_orientacao: bool = False,
                         pedido: dict | None = None) -> dict:
    """As regras da contratação, em texto curto, antes de começar.

    Curto de propósito: termo que ninguém lê não informa ninguém, e o
    que interessa aqui cabe em uma tela — o que o escritório faz, por
    quanto, em quanto tempo, e o que acontece se o cliente desistir.

    O TERMO LÊ O PEDIDO, NÃO A TABELA
    Antes ele mostrava sempre o preço cheio, mesmo quando o cliente
    tinha negociado 20% ou tido a própria proposta aceita. A pessoa
    assinava um texto que dizia um valor e pagava outro, o que é o tipo
    de incoerência que ninguém percebe na hora e todo mundo lembra na
    discussão. Agora o valor sai do pedido, com o desconto, a urgência
    e a proposta aceita discriminados."""
    t = catalogo.detalhe(tipo) or {}
    p = pedido or {}

    valor = float(p.get("valor") or 0) or catalogo.preco(tipo, com_orientacao)
    base = float(p.get("valor_base") or 0)
    desconto = float(p.get("desconto_pct") or 0)
    urgente = bool(p.get("urgente"))
    horas = int(p.get("prazo_entrega_horas") or (
        catalogo.HORAS_URGENTE if urgente else catalogo.HORAS_PADRAO))
    por_proposta = p.get("proposta_status") == "ACEITA"

    linhas = [
        f"CONTRATAÇÃO DE SERVIÇO, {t.get('nome', tipo)}",
        "",
        "O QUE O ESCRITÓRIO FAZ",
        f"Elabora o documento conforme a legislação aplicável "
        f"({t.get('base_legal', ',')}), com revisão e conferência antes de "
        f"ser enviado a você, e disponibiliza assinatura eletrônica com "
        f"validade jurídica (Lei 14.063/2020 e MP 2.200-2/2001).",
        "",
        "VALOR E PAGAMENTO",
        f"{_reais(valor)}, por PIX, à vista. O trabalho começa depois do "
        f"pagamento confirmado.",
    ]

    # A conta, aberta. Só aparece o que de fato aconteceu nesta
    # negociação: linha de desconto sem desconto é ruído.
    detalhe = []
    if base and base != valor:
        detalhe.append(f"Valor de tabela deste documento: {_reais(base)}.")
    if desconto:
        detalhe.append(f"Desconto combinado no atendimento: {desconto:.0f}%.")
    if urgente:
        detalhe.append(
            f"Acréscimo de urgência: entrega em até {horas} horas em vez de "
            f"{catalogo.HORAS_PADRAO}.")
    if p.get("assinatura_digital") is False:
        detalhe.append("Sem assinatura eletrônica, com o desconto "
                       "correspondente. O documento é entregue para baixar.")
    if por_proposta:
        detalhe.append(
            f"Este valor é a proposta que você apresentou e que o escritório "
            f"aceitou em {_br(p.get('proposta_respondida_em'))}.")
    if detalhe:
        linhas += ["", "COMO SE CHEGOU A ESSE VALOR"] + detalhe

    if com_orientacao or p.get("com_orientacao"):
        linhas += ["Inclui atendimento jurídico prévio, por vídeo, com gravação "
                   "de áudio e transcrição, mediante seu consentimento na sala."]
    linhas += [
        "",
        "PRAZO DE ENTREGA",
        f"A primeira versão fica pronta em até {horas} horas contadas do "
        f"pagamento confirmado e do recebimento de todos os dados e "
        f"documentos que o escritório pedir. Cada pedido de alteração seu "
        f"reinicia a contagem.",
    ]
    if urgente:
        linhas += ["Você contratou a entrega urgente: o prazo é de 6 horas, e "
                   "ele só começa quando as informações estiverem completas."]
    linhas += [
        "",
        "REVISÃO E APROVAÇÃO, E O PRAZO DE 7 DIAS",
        "Quando o documento ficar pronto, ele é disponibilizado na sua área "
        "na plataforma e você é avisado por e-mail. A partir dessa "
        "disponibilização você tem 7 dias corridos para ler, pedir alteração "
        "e aprovar.",
        "Passados os 7 dias sem aprovação e sem pedido de alteração, a "
        "solicitação é arquivada automaticamente. O documento não se perde: "
        "para retomá-lo, basta abrir um chamado de desarquivamento na sua "
        "área, explicando o motivo. O escritório analisa e responde.",
        "",
        "REVISÕES",
        "Dentro dos 7 dias você pode pedir alterações quantas vezes precisar, "
        "desde que dentro do que foi contratado. Mudar o tipo de contrato ou "
        "incluir objeto novo é outro serviço.",
        "",
        "O QUE NÃO ESTÁ INCLUÍDO",
        "Custas de cartório, registro, reconhecimento de firma, taxas e "
        "tributos da sua negociação. Representação em processo judicial "
        "também é contratação separada.",
        "",
        "DESISTÊNCIA",
        "Antes de o documento ser redigido, a devolução é integral. Depois "
        "de redigido, o valor não é devolvido, porque o serviço foi "
        "prestado, o documento é seu e fica disponível.",
        "",
        "SEUS DADOS",
        "Seus dados e documentos são usados apenas para elaborar o que você "
        "pediu, conforme a Política de Privacidade do escritório.",
        "",
        f"Versão: {VERSAO_CONTRATACAO}",
    ]
    return {"versao": VERSAO_CONTRATACAO, "tipo": tipo, "valor": valor,
            "horas": horas, "urgente": urgente, "desconto_pct": desconto,
            "por_proposta": por_proposta, "texto": "\n".join(linhas)}


def _br(iso: str | None) -> str:
    """Data em português, ou nada. Usada só no texto do termo."""
    if not iso:
        return ""
    s = str(iso)
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}"


def aceitar_contratacao(pedido_id: str, termo: dict, ip: str | None = None) -> dict:
    """Registra o aceite na mesma trilha das demais ciências: o texto
    inteiro, a versão, a data e o IP."""
    db = get_db()
    row = db.table("pedidos_ciencias").insert({
        "pedido_id": pedido_id,
        "versao": f"CONTRATACAO-{termo.get('versao')}",
        "texto": termo.get("texto"),
        "pontos": None,
        "escolha": "ACEITO",
        "ip": ip,
    }).execute().data[0]
    db.table("pedidos_contrato").update({
        "fase": "PAGAMENTO", "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATACAO_ACEITA",
                     {"pedido": pedido_id, "versao": termo.get("versao")})
    return row

# A ORDEM DAS FASES
#
# O pagamento era a terceira etapa: o cliente preenchia tudo, lia a
# orientação e só então pagava. Isso põe o trabalho antes do sim, e o
# escritório coletava dados de quem ainda podia desistir.
#
# Agora o pagamento é a primeira. Confirmado o PIX, o atendimento volta
# e pergunta o que o documento exige. É também quando se pergunta sobre
# timbre ou folha branca: antes disso a pergunta não significa nada
# para quem nem sabe se vai contratar.
# ── O RITO, E POR QUE ELE TEM DUAS REVISÕES ────────────────────
#
# A primeira revisão olha o contrato contra a lei e contra o que o
# cliente pediu. Ela acha três tipos de coisa: o que o redator corrige
# sozinho, o que é nulo e precisa mudar, e o que o cliente pediu mas a
# lei não admite. O terceiro tipo não se resolve dentro do escritório:
# ninguém pode escolher pelo cliente entre perder o que ele pediu e
# assinar algo que pode cair.
#
# Daí a fase nova. CIENCIA_ALTERACAO é a espera pela decisão dele, com
# o relógio parado. Respondida, o redator refaz o texto com a escolha
# registrada, e a SEGUNDA revisão confere justamente isso: se o que
# voltou está coerente com a decisão que ele tomou.
#
# Sem essa segunda passada, a alteração feita por causa da resposta do
# cliente chegaria ao advogado sem ninguém ter lido depois da mudança,
# que é exatamente o momento em que erro entra.
FASES = [
    # O atendimento, que antes acontecia fora do quadro. O pedido
    # nascia direto em PAGAMENTO, e quem estava conversando sobre
    # preço não aparecia em lugar nenhum: o escritório só via quem já
    # tinha decidido. Agora a esteira começa onde o cliente começa.
    "QUALIFICACAO", "PROPOSTA",
    "PAGAMENTO", "COLETA", "CIENCIA", "REDACAO", "REVISAO_IA", "AJUSTE",
    "CIENCIA_ALTERACAO", "REVISAO_2", "REVISAO_ADV", "APROVACAO",
    "ASSINATURA", "ENTREGUE", "ARQUIVADO",
]


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agora_dt() -> datetime:
    return datetime.now(timezone.utc)


def _quando(iso) -> datetime | None:
    """Lê o carimbo do banco. Devolve None em vez de explodir: data
    ilegível não pode derrubar a tela que só queria saber a hora."""
    if not iso:
        return None
    if isinstance(iso, datetime):
        return iso if iso.tzinfo else iso.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ── Termo de ciência ────────────────────────────────────────────
def termo_de_ciencia(tipo: str, regras_violadas: list[str],
                     dados: dict | None = None) -> dict:
    """Monta o texto que o cliente lê antes de decidir.

    O texto explica, para cada ponto: o que a lei diz, o que acontece
    na prática se seguir do jeito combinado, e qual é a alternativa
    dentro da lei. Sem juridiquês e sem suavizar — o cliente está
    assumindo uma consequência, e precisa saber qual."""
    t = catalogo.detalhe(tipo)
    if not t:
        raise ValueError("Tipo de contrato desconhecido.")

    itens = []
    for r in t.get("regras", []):
        if r["quando"] in regras_violadas:
            itens.append({
                "ponto": r["quando"],
                "o_que_a_lei_diz": r["diz"],
                "como_adequar": r["adequar"],
            })

    # O alerta do tipo (escritura pública, registro em CTPS, cartório de
    # títulos) entra sempre que existir, mesmo sem regra violada: é
    # limite do documento, não escolha do cliente.
    alerta = t.get("alerta")

    partes = [
        f"CIÊNCIA E DECISÃO, {t['nome']}",
        "",
        f"Base legal aplicável: {t['base_legal']}.",
        "",
    ]
    if alerta:
        partes += ["O QUE ESTE DOCUMENTO FAZ E O QUE NÃO FAZ", "", alerta, ""]
    if itens:
        partes.append("PONTOS DO QUE VOCÊ COMBINOU QUE FOGEM DA LEI")
        partes.append("")
        for i, it in enumerate(itens, 1):
            partes += [
                f"{i}. {it['o_que_a_lei_diz']}",
                f"   Como ficaria dentro da lei: {it['como_adequar']}",
                "",
            ]
    partes += [
        "SUA DECISÃO",
        "",
        "Você pode escolher adequar o contrato à lei, e nesse caso é só "
        "avisar o atendente o que prefere mudar. Ou pode escolher seguir "
        "com o que foi combinado entre as partes, ciente do que está "
        "escrito acima.",
        "",
        "Ao clicar em CIENTE E QUERO PROSSEGUIR, você declara que leu e "
        "entendeu as orientações acima, que elas lhe foram prestadas "
        "antes da elaboração do documento, e que opta por seguir assim "
        "mesmo, por sua conta e risco.",
        "",
        "O escritório continua responsável por redigir o documento com "
        "técnica e clareza; não responde pelo efeito de cláusula que "
        "você optou por manter contra a orientação dada.",
        "",
        f"Versão do termo: {VERSAO_TERMO}",
    ]

    return {
        "versao": VERSAO_TERMO,
        "tipo": tipo,
        "texto": "\n".join(partes),
        "pontos": itens,
        "alerta": alerta,
        "precisa_advogado": bool(itens),   # nulidade vai à revisão humana
    }


def registrar_ciencia(pedido_id: str, termo: dict, escolha: str,
                      ip: str | None = None) -> dict:
    """Guarda a decisão. `escolha`: PROSSEGUIR ou ADEQUAR."""
    if escolha not in ("PROSSEGUIR", "ADEQUAR"):
        raise ValueError("Escolha inválida.")
    db = get_db()
    row = db.table("pedidos_ciencias").insert({
        "pedido_id": pedido_id,
        "versao": termo.get("versao"),
        "texto": termo.get("texto"),
        "pontos": termo.get("pontos"),
        "escolha": escolha,
        "ip": ip,
    }).execute().data[0]
    registrar_evento(None, "CONTRATO_CIENCIA",
                     {"pedido": pedido_id, "escolha": escolha,
                      "versao": termo.get("versao")})
    return row


# ── Redator ─────────────────────────────────────────────────────
SYSTEM_REDATOR = """Você é advogado redator de contratos da FC Advocacia,
com trinta anos de prática em direito civil e empresarial brasileiro.

Escreva o contrato completo, pronto para assinatura, seguindo a
legislação informada. Regras da casa:

- Português claro. Cláusula que o cliente não entende é cláusula que
  não protege ninguém.
- Numere as cláusulas. Qualificação completa das partes no preâmbulo.
- Use APENAS os dados fornecidos. Onde faltar dado essencial, escreva
  [A PREENCHER: o que falta] — nunca invente nome, valor, data ou
  documento.
- Inclua as cláusulas que a lei do tipo exige e as que a prática
  recomenda: objeto, preço, prazo, obrigações de cada parte, rescisão,
  multa, foro.
- Quando o cliente optou por manter um ponto contra a orientação,
  redija do jeito que ele pediu E inclua, ao final, uma cláusula de
  ciência registrando que a orientação foi prestada.
- Não escreva parecer, comentário nem explicação: só o contrato.
- TEXTO CORRIDO, SEM MARCAÇÃO. Nada de sustenido para título, asterisco
  para negrito ou linha de hífens para separar seção. Os modelos que
  você recebe como apoio usam esses sinais porque são arquivos de
  texto; o contrato que você escreve é o documento final, e ali eles
  aparecem escritos, à vista do cliente. Título é uma linha curta em
  MAIÚSCULAS; ênfase se faz com a palavra certa, não com asterisco."""

SYSTEM_REVISOR = """Você é advogado revisor da FC Advocacia. Leia o
contrato inteiro e aponte o que precisa mudar antes de ir ao cliente.

Procure, nesta ordem de importância:
1. Cláusula nula ou ineficaz diante da lei aplicável.
2. Dado faltando, contraditório ou inventado — confira contra os dados
   fornecidos, um a um.
3. Cláusula ambígua, que permita duas leituras.
4. Ausência de cláusula essencial para este tipo de contrato.
5. Erro de português, numeração ou referência cruzada.

Seja específico: diga a cláusula, o problema e a redação sugerida. Não
elogie. Se estiver bom, diga que está bom.

NO MÁXIMO DOZE APONTAMENTOS, e comece pelos mais graves. Revisão que
lista trinta pontos não é mais cuidadosa, é mais difícil de aplicar, e
o que importa acaba no meio da lista. Erro de vírgula só entra se não
houver nada de substância a dizer.

O QUE O CLIENTE PEDIU E A LEI NÃO ADMITE

Este é o único caso em que a revisão não decide sozinha. Quando o
cliente pediu algo que contraria a lei ou a jurisprudência, não
silencie o pedido dele nem o mantenha em silêncio: marque
`precisa_autorizacao` e escreva em `o_que_a_lei_diz`, em duas frases e
sem jargão, o que a lei diz e o risco concreto de seguir como ele
pediu. Quem decide entre manter com ciência registrada ou adequar é o
cliente, e essa decisão fica registrada.

O contrato tem de sair impecável e sem lacuna, e respeitar o que o
cliente pediu. Quando as duas coisas não couberem juntas, é ele quem
escolhe, sabendo do risco."""

SYSTEM_REVISAO_2 = """Você é o advogado que faz a conferência final do
escritório antes de o documento chegar à mesa do sócio.

Esta NÃO é uma releitura do contrato inteiro. A primeira revisão já leu
tudo e apontou o que precisava mudar. Você confere uma coisa só: o
texto que voltou depois do ajuste atende ao que foi apontado e ao que
o cliente decidiu?

Procure, nesta ordem:
1. Apontamento da primeira revisão que ficou sem atendimento.
2. Decisão do cliente contrariada no texto. Se ele escolheu manter como
   pediu, o texto tem de estar como ele pediu, e com a cláusula de
   ciência registrando que a orientação foi prestada. Se escolheu
   adequar, a cláusula tem de estar adequada.
3. Estrago colateral: o ajuste que corrigiu um ponto e quebrou outro,
   numeração fora de ordem, referência cruzada apontando para o lugar
   errado, cláusula duplicada.
4. Campo [A PREENCHER] que sobrou.

NÃO aponte preferência de redação, sinônimo melhor nem reorganização de
cláusula que já está correta. Isso aqui não é gosto, é conferência: a
cada rodada de opinião nova o documento atrasa um dia e não melhora.

Se estiver tudo atendido, diga que está pronto para a conferência do
advogado e deixe a lista de apontamentos vazia."""


FERRAMENTA_REVISAO = {
    "name": "revisao",
    "description": "Apontamentos da revisão do contrato",
    "input_schema": {
        "type": "object",
        "properties": {
            "apontamentos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "clausula": {"type": "string"},
                        "gravidade": {"type": "string",
                                      "enum": ["ALTA", "MEDIA", "BAIXA"]},
                        "problema": {"type": "string"},
                        "sugestao": {"type": "string"},
                        # O PONTO QUE O CLIENTE PRECISA AUTORIZAR
                        #
                        # Nem todo apontamento é decisão do cliente. Erro
                        # de numeração o revisor manda corrigir e pronto.
                        # O que o cliente pediu e a lei não admite é
                        # outra coisa: ninguém pode escolher por ele
                        # entre perder o que pediu e assinar algo que
                        # pode cair. Marcado aqui, vira botão na tela.
                        "precisa_autorizacao": {
                            "type": "boolean",
                            "description": (
                                "Verdadeiro quando o ponto é algo que o "
                                "cliente pediu e que contraria a lei ou a "
                                "jurisprudência. Nesse caso ele decide: "
                                "manter como pediu, com ciência registrada, "
                                "ou adequar."),
                        },
                        "o_que_a_lei_diz": {
                            "type": "string",
                            "description": (
                                "Em duas frases, para o cliente ler: o que a "
                                "lei diz e o risco concreto de manter como "
                                "ele pediu. Sem jargão."),
                        },
                    },
                    "required": ["clausula", "gravidade", "problema", "sugestao"],
                },
            },
            "parecer": {"type": "string"},
            "pronto_para_advogado": {"type": "boolean"},
        },
        "required": ["apontamentos", "parecer", "pronto_para_advogado"],
    },
}


def _claude():
    """O cliente da IA, que avisa quando recusa e quando volta.

    Passa por `core/ia.cliente` para que a esteira saiba parar de
    insistir quando a conta bloqueia, e saiba voltar a trabalhar assim
    que a primeira chamada der certo de novo. Sem isso, o freio ficava
    puxado depois de alguém já ter arrumado a conta."""
    from ..core import ia as _ia
    return _ia.cliente(get_settings().claude_api_key)


def ja_recebido(pedido_id: str) -> str:
    """O que o cliente JÁ mandou, em lista curta, para não pedir de novo.

    PEDIR DUAS VEZES É O QUE MAIS IRRITA QUEM JÁ MANDOU

    O atendimento e a negociação recebiam a conversa e a lista do que
    FALTA, e nunca a lista do que CHEGOU. Documento anexado não vira
    mensagem de texto: o cliente manda a foto do RG, não escreve nada, e
    do lado do agente não aconteceu nada. Aí ele pede o RG de novo, e a
    pessoa que acabou de mandar entende que ninguém olhou.

    Com o campo digitado é parecido: o dado entra pela tela de coleta ou
    é colhido da conversa pelo sistema, e o agente continua lendo só o
    histórico de falas, onde aquilo pode nunca ter sido dito em palavras.

    Esta lista é curta de propósito. Ela não serve para o agente ler o
    documento, serve para ele saber que o documento existe. Quem precisa
    do conteúdo usa `texto_dos_anexos`."""
    db = get_db()
    partes: list[str] = []

    try:
        docs = db.table("pedidos_documentos") \
            .select("nome,rotulo,criado_em,transcricao") \
            .eq("pedido_id", pedido_id).order("criado_em") \
            .limit(40).execute().data or []
    except Exception as e:
        print(f"[balcao] documentos recebidos não lidos: {e}")
        docs = []
    if docs:
        partes.append("ARQUIVOS QUE O CLIENTE JÁ ENVIOU "
                      "(NÃO PEÇA NENHUM DESTES DE NOVO):")
        for d in docs:
            quando = str(d.get("criado_em") or "")[:10]
            rotulo = d.get("rotulo")
            nome = d.get("nome") or "arquivo"
            lido = " [lido pelo sistema]" if (d.get("transcricao") or "").strip() else ""
            partes.append(f"  · {rotulo or nome}"
                          + (f" (arquivo {nome})" if rotulo else "")
                          + (f", enviado em {quando}" if quando else "")
                          + lido)

    try:
        r = db.table("pedidos_contrato").select("dados,partes") \
            .eq("id", pedido_id).limit(1).execute().data
    except Exception:
        r = []
    p = r[0] if r else {}

    dados = {k: v for k, v in _dados.como_dict(p.get("dados")).items()
             if str(v or "").strip()}
    if dados:
        partes.append("")
        partes.append("INFORMAÇÕES QUE JÁ ESTÃO NO PEDIDO "
                      "(NÃO PERGUNTE DE NOVO):")
        for k, v in list(dados.items())[:40]:
            partes.append(f"  · {k}: {str(v)[:120]}")

    qualificadas = []
    for parte in _dados.lista_de_dicts(p.get("partes")):
        papel = _como_se_chama(parte.get("papel") or "")
        campos = [f"{c}" for c in ("nome", "cpf_cnpj", "endereco")
                  if str(parte.get(c) or "").strip()]
        if campos:
            qualificadas.append(f"  · {papel or 'parte'}: já tem "
                                + ", ".join(campos))
    if qualificadas:
        partes.append("")
        partes.append("QUALIFICAÇÃO JÁ CONFERIDA:")
        partes += qualificadas

    if not partes:
        return "O cliente ainda não enviou nenhum arquivo nem informação."
    return "\n".join(partes)


def texto_dos_anexos(pedido_id: str, limite_total: int = 20000) -> str:
    """O que está escrito nos arquivos que o cliente mandou.

    O CLIENTE MANDOU O DOCUMENTO E O REDATOR NÃO VIA

    A foto do RG, a matrícula do imóvel, o comprovante de endereço: tudo
    isso era guardado, lido e transcrito pelo atendimento, e a
    transcrição ficava parada no registro do arquivo. O redator montava
    o contexto a partir dos campos digitados e nunca encostava nela.

    Na prática: o cliente mandava a matrícula do imóvel, o campo
    "matrícula" continuava vazio porque ninguém digitou, e o contrato
    saía com [A PREENCHER] em cima de um dado que estava na mão do
    escritório havia dois dias.

    Devolve texto pronto para entrar no pedido ao modelo, ou vazio
    quando não há anexo lido. Vazio é resposta: não existindo
    transcrição, o redator segue com o que tem, sem inventar."""
    try:
        docs = get_db().table("pedidos_documentos") \
            .select("nome,rotulo,tipo_mime,transcricao,transcrito_em") \
            .eq("pedido_id", pedido_id).order("criado_em") \
            .limit(20).execute().data or []
    except Exception as e:
        print(f"[balcao] anexos não lidos: {e}")
        return ""

    partes, usado = [], 0
    for d in docs:
        texto = (d.get("transcricao") or "").strip()
        if not texto:
            continue
        cabeca = d.get("nome") or "documento"
        if d.get("rotulo"):
            cabeca += f" ({d['rotulo']})"
        pedaco = f"--- {cabeca} ---\n{texto}"
        if usado + len(pedaco) > limite_total:
            partes.append("[os demais anexos ficaram de fora por tamanho]")
            break
        partes.append(pedaco)
        usado += len(pedaco)

    if not partes:
        return ""
    return ("\n\n".join(partes))


def redigir(pedido_id: str, auto: bool = False) -> dict:
    """Escreve a primeira versão a partir dos dados coletados.

    `auto` muda uma coisa só: a fase não avança. A minuta fica pronta e
    guardada, e o pedido continua em REDACAO pelo tempo da janela.

    Parece contraintuitivo escrever e não mostrar, mas é o que o rito
    pede: o cliente acabou de mandar as informações e o documento
    aparecer pronto no mesmo minuto não passa confiança, passa a
    impressão de formulário preenchido por máquina. E o escritório
    ganha a janela para agir antes, se quiser, com o trabalho já
    adiantado em vez de por fazer."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    t = catalogo.detalhe(p["tipo"]) or {}
    s = get_settings()

    ciencias = db.table("pedidos_ciencias").select("texto,escolha,pontos") \
        .eq("pedido_id", pedido_id).execute().data
    optou_manter = [c for c in ciencias if c.get("escolha") == "PROSSEGUIR"]

    contexto = [
        f"TIPO DE CONTRATO: {t.get('nome')}",
        f"LEGISLAÇÃO APLICÁVEL: {t.get('base_legal')}",
        "",
        "DADOS FORNECIDOS PELO CLIENTE:",
        json.dumps(p.get("dados") or {}, ensure_ascii=False, indent=2),
    ]
    if p.get("observacoes"):
        contexto += ["", "O QUE AS PARTES COMBINARAM, NAS PALAVRAS DO CLIENTE:",
                     p["observacoes"]]
    if optou_manter:
        contexto += ["", "PONTOS QUE O CLIENTE OPTOU POR MANTER APÓS ORIENTAÇÃO "
                     "(redija como pedido e inclua cláusula de ciência):"]
        for c in optou_manter:
            for ponto in _dados.como_lista(c.get("pontos")):
                contexto.append(f"- {ponto.get('o_que_a_lei_diz')}")
    if p.get("com_timbre") is False:
        contexto += ["", "O cliente pediu o documento SEM o timbre do escritório."]

    # O QUE ELE PEDIU PARA MUDAR, E SÓ ISSO
    #
    # Quando o cliente pede alteração depois de ler, o documento volta
    # para cá inteiro. Sem esta instrução o redator reescreve tudo de
    # novo, e o cliente recebe de volta um texto diferente do que ele
    # aprovou em tudo menos no ponto que pediu. Mudar o que ninguém
    # pediu é a forma mais rápida de perder a confiança de quem já
    # tinha lido e concordado.
    pedidos_mudanca = [a for a in _dados.lista_de_dicts(
                           p.get("pedidos_alteracao"), "texto")
                       if not a.get("atendido")]
    if pedidos_mudanca:
        contexto += ["", "=" * 60,
                     "O CLIENTE JÁ LEU ESTE DOCUMENTO E PEDIU ESTAS "
                     "MUDANÇAS. Altere APENAS o que está aqui, e mantenha o "
                     "resto do texto exatamente como estava:"]
        for a in pedidos_mudanca:
            contexto.append(f"- {a.get('texto')}")
        if p.get("minuta_anterior"):
            contexto += ["", "VERSÃO QUE ELE LEU E APROVOU NO RESTANTE:",
                         str(p["minuta_anterior"])[:40000]]

    # AS DECISÕES QUE ELE JÁ TOMOU CONTINUAM VALENDO
    if p.get("decisoes"):
        contexto += ["", "PONTOS JÁ DECIDIDOS PELO CLIENTE, não pergunte de "
                     "novo e respeite a escolha:"]
        for d in p["decisoes"]:
            contexto.append(
                f"- {d.get('clausula')}: "
                + ("manter como ele pediu, incluindo a cláusula de ciência "
                   "de que a orientação foi prestada"
                   if d.get("escolha") == "MANTER" else "adequar à lei"))

    # A QUALIFICAÇÃO DAS PARTES VEM DA CAIXA DELAS
    #
    # Ela saiu dos campos livres quando a caixa das partes nasceu, e o
    # redator continuou lendo só `dados`. Resultado: contrato com os
    # dois polos marcados como [A PREENCHER] enquanto a informação
    # estava salva no pedido, uma linha ao lado.
    if p.get("partes"):
        contexto += ["", "QUALIFICAÇÃO DAS PARTES, JÁ CONFERIDA:",
                     json.dumps(p["partes"], ensure_ascii=False, indent=2)]

    # O QUE ESTÁ ESCRITO NOS DOCUMENTOS QUE ELE MANDOU
    #
    # Antes disto, o cliente mandava a matrícula do imóvel, o campo
    # "matrícula" continuava vazio porque ninguém digitou, e o contrato
    # saía com [A PREENCHER] em cima de um dado que o escritório tinha
    # na mão havia dois dias.
    anexos = texto_dos_anexos(pedido_id)
    if anexos:
        contexto += [
            "", "=" * 60,
            "O QUE ESTÁ ESCRITO NOS DOCUMENTOS QUE O CLIENTE ENVIOU. "
            "Use o que servir para preencher o contrato: número de "
            "matrícula, endereço, qualificação, valores. Onde isto "
            "divergir do que foi digitado nos campos, prevalece o que "
            "está no DOCUMENTO, e diga no texto qual documento você "
            "seguiu. O que não estiver aqui nem nos campos continua "
            "sendo [A PREENCHER]: anexo ilegível não vira palpite.",
            "=" * 60, anexos]

    # O MODELO DO ESCRITÓRIO, QUANDO EXISTE UM
    #
    # Escrever do zero produzia contrato correto e diferente a cada
    # vez: outra numeração, outra ordem, outra redação. Dois contratos
    # do mesmo escritório não pareciam do mesmo escritório, e a revisão
    # gastava o tempo dela conferindo forma em vez de substância.
    #
    # O modelo entra como base obrigatória, e o guia técnico entra
    # junto porque é ele que explica o porquê de cada cláusula: sem o
    # porquê, o redator adapta o texto e desmonta a proteção sem saber
    # que ela estava ali.
    from . import modelos_contrato
    base = modelos_contrato.modelo_do_pedido(
        p["tipo"], _dados.como_dict(p.get("dados")))
    if base.get("tem"):
        contexto += [
            "", "=" * 60,
            "MODELO OFICIAL DO ESCRITÓRIO PARA ESTE CASO "
            f"({base['nome'].replace('_', ' ')}). Use como BASE: mantenha a "
            "estrutura, a numeração e a redação das cláusulas, e troque "
            "apenas o que o caso concreto exigir. Preencha os campos entre "
            "chaves duplas com os dados acima. Campo sem dado vira "
            "[A PREENCHER: o que falta], nunca texto inventado. Linha do "
            "Quadro Resumo que ficaria vazia, remova inteira (o RG não é "
            "mais coletado pelo escritório).",
            "=" * 60,
            base["texto"],
            "", "=" * 60,
            "GUIA TÉCNICO. É o porquê de cada cláusula do modelo. Não "
            "copie o guia para o contrato: use-o para não desmontar, sem "
            "querer, uma proteção que está ali de propósito.",
            "=" * 60,
            base["guia"],
        ]

    r = _claude().messages.create(
        model=s.claude_model, max_tokens=8000, system=SYSTEM_REDATOR,
        messages=[{"role": "user", "content": "\n".join(contexto)}],
    )
    texto = "".join(b.text for b in r.content if b.type == "text").strip()

    campos = {"minuta": texto, "redigido_em": _agora(),
              "atualizado_em": _agora()}
    if not auto:
        campos.update({"fase": "REVISAO_IA", "fase_em": _agora(),
                       "avanca_em": _mais(JANELA_REVISAO)})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_REDIGIDO",
                     {"pedido": pedido_id, "tipo": p["tipo"],
                      "caracteres": len(texto), "auto": auto})
    return {"ok": True, "fase": "REDACAO" if auto else "REVISAO_IA",
            "caracteres": len(texto)}


def revisar(pedido_id: str, auto: bool = False) -> dict:
    """O revisor lê a íntegra e anota. Só depois disso o ajuste abre."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    if not p.get("minuta"):
        raise ValueError("Não há minuta para revisar, redija primeiro.")
    t = catalogo.detalhe(p["tipo"]) or {}
    s = get_settings()

    from . import modelos_contrato
    base = modelos_contrato.modelo_do_pedido(
        p["tipo"], _dados.como_dict(p.get("dados")))

    partes = ["=" * 60,
              "O QUE É NULO POR LEI, E NÃO É QUESTÃO DE OPINIÃO. Encontrando "
              "qualquer uma destas no contrato, ou no que o cliente pediu, "
              "marque gravidade ALTA e preencha `precisa_autorizacao`:",
              modelos_contrato.texto_das_proibidas(), "=" * 60]

    # O DOCUMENTO É A FONTE MAIS FORTE DAS TRÊS
    #
    # O revisor confere a minuta contra o cadastro e contra a conversa.
    # O documento enviado é a terceira fonte, e vale mais que as outras
    # duas: cadastro tem erro de digitação e conversa tem erro de
    # memória, mas a matrícula do imóvel é o que está escrito nela.
    anexos_revisao = texto_dos_anexos(pedido_id, limite_total=12000)
    if anexos_revisao:
        partes += [
            "O QUE ESTÁ ESCRITO NOS DOCUMENTOS QUE O CLIENTE ENVIOU. "
            "Confira a minuta contra isto: número, nome, endereço e valor "
            "que divergirem do documento são apontamento de gravidade "
            "ALTA, porque saem no contrato assinado.",
            anexos_revisao, "=" * 60]
    if base.get("tem"):
        partes += ["GUIA TÉCNICO DO ESCRITÓRIO, com os fundamentos de cada "
                   "cláusula do modelo. Confira o contrato contra ele:",
                   base["guia"], "=" * 60]

    # ESPAÇO PARA A REVISÃO CABER INTEIRA
    #
    # Eram 4000 fichas, e a revisão de um contrato de locação não cabe
    # nisso: cada apontamento leva cláusula, problema e a redação
    # sugerida, e agora leva também a explicação para o cliente quando
    # o ponto depende da autorização dele. Estourando o limite, a
    # resposta vem cortada no meio da ferramenta, o que chega aqui
    # como estrutura incompleta, não como erro.
    #
    # Era esta a origem da revisão vazia que empurrava o pedido para o
    # ajuste sem ter revisado nada.
    r = _claude().messages.create(
        model=s.claude_model, max_tokens=8000, system=SYSTEM_REVISOR,
        tools=[FERRAMENTA_REVISAO],
        tool_choice={"type": "tool", "name": "revisao"},
        messages=[{"role": "user", "content":
                   f"TIPO: {t.get('nome')}\n"
                   f"LEGISLAÇÃO: {t.get('base_legal')}\n\n"
                   f"DADOS FORNECIDOS:\n"
                   f"{json.dumps(p.get('dados') or {}, ensure_ascii=False)}\n\n"
                   + "\n".join(partes) + "\n\n"
                   f"O QUE O CLIENTE PEDIU, NAS PALAVRAS DELE:\n"
                   f"{(p.get('observacoes') or '')[:3000]}\n"
                   f"{(p.get('clausulas_extras') or '')[:3000]}\n\n"
                   f"CONTRATO:\n{p['minuta'][:40000]}"}],
    )
    dados = {}
    veio_resposta = False
    for bloco in r.content:
        if bloco.type == "tool_use" and bloco.name == "revisao":
            veio_resposta = True
            dados = _dados.como_dict(bloco.input)

    # A FORMA CERTA ANTES DE GRAVAR, E NÃO DEPOIS
    #
    # O esquema pede lista de objetos, mas quem responde é um modelo, e
    # de vez em quando ele manda a mesma coisa como texto. Gravar assim
    # contamina o pedido: quem for ler depois quebra, e o erro aparece
    # numa tela que não tem nada a ver com a revisão. Arrumar aqui é
    # arrumar uma vez só, no lugar em que o dado nasce.
    dados["apontamentos"] = _dados.lista_de_dicts(
        dados.get("apontamentos"), "problema")
    dados["parecer"] = _dados.texto_de(dados.get("parecer"))

    # Resposta cortada no limite não é resposta. Guardar o pedaço que
    # chegou seria pior do que não guardar nada: o pedido seguiria em
    # frente com meia revisão, e ninguém saberia qual metade faltou.
    if getattr(r, "stop_reason", "") == "max_tokens":
        registrar_evento(None, "CONTRATO_REVISAO_CORTADA",
                         {"pedido": pedido_id})
        raise ValueError("A revisão ficou longa demais e veio cortada. "
                         "Tente de novo; se repetir, o contrato precisa "
                         "ser revisado em partes.")

    apontamentos = dados.get("apontamentos") or []

    # REVISÃO VAZIA NÃO É REVISÃO FEITA
    #
    # Quando o modelo não devolvia a ferramenta, `dados` ficava vazio,
    # e o pedido avançava mesmo assim para o ajuste. Lá, o ajuste
    # conferia "tem revisão?", não tinha, e travava: o pedido ficava
    # numa fase de onde nenhum botão saía, e o operador só via a frase
    # "acione o revisor primeiro" sem ter como acionar ninguém.
    #
    # Falhar é aceitável; avançar tendo falhado, não. O pedido fica
    # onde está, e quem clicou lê o motivo em vez de descobrir o
    # problema duas fases adiante.
    # Olha se a FERRAMENTA foi usada, e não se o dicionário tem chave:
    # depois da normalização acima ele sempre tem, e o teste antigo
    # deixaria passar uma revisão que nunca aconteceu.
    if not veio_resposta:
        registrar_evento(None, "CONTRATO_REVISAO_VAZIA", {"pedido": pedido_id})
        raise ValueError("A revisão não retornou apontamentos. O pedido "
                         "continua nesta fase; tente de novo em instantes.")

    campos = {"revisao": dados, "revisado_em": _agora(),
              "atualizado_em": _agora()}
    if not auto:
        campos.update({"fase": "AJUSTE", "fase_em": _agora(),
                       "avanca_em": _mais(JANELA_AJUSTE)})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_REVISADO",
                     {"pedido": pedido_id, "apontamentos": len(apontamentos),
                      "auto": auto})
    return {"ok": True, "fase": "REVISAO_IA" if auto else "AJUSTE",
            "apontamentos": apontamentos,
            "parecer": dados.get("parecer", "")}


def ajustar(pedido_id: str, auto: bool = False) -> dict:
    """O redator corrige o que o revisor apontou.

    A trava está aqui: sem revisão feita, não há o que ajustar, e
    deixar este botão aberto o tempo todo convidaria a pular a etapa."""
    db = get_db()
    achado = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not achado:
        raise ValueError("Pedido não encontrado.")
    p = achado[0]
    # SEM REVISÃO, REVISA AGORA, EM VEZ DE TRAVAR
    #
    # A trava original estava certa na intenção: não se ajusta o que
    # ninguém revisou. Mas a mensagem mandava "acionar o revisor
    # primeiro" e o botão do revisor não existe nesta fase, então o
    # pedido ficava sem saída nenhuma. Beco sem saída em esteira é
    # pior do que etapa pulada: alguém tem de mexer no banco para
    # destravar.
    #
    # Agora o ajuste chama o revisor ele mesmo, com `auto` para não
    # mexer na fase, e segue com o que ele apontar.
    # REVISÃO GUARDADA COM A FORMA ERRADA CONTA COMO REVISÃO QUE FALTA
    #
    # Não basta a coluna estar preenchida. Um pedido antigo pode ter
    # guardado ali uma frase em vez do objeto com os apontamentos, e
    # nesse caso o ajuste seguia em frente achando que não havia nada a
    # corrigir: o contrato ia para a conferência do advogado SEM as
    # correções, e ninguém era avisado. Pular etapa em silêncio é pior
    # do que travar, porque o erro só aparece com o cliente.
    if not _dados.lista_de_dicts(
            _dados.como_dict(p.get("revisao")).get("apontamentos"), "problema") \
            and not _dados.como_dict(p.get("revisao")).get("parecer"):
        try:
            revisar(pedido_id, auto=True)
        except Exception as e:
            raise ValueError(
                "Não consegui revisar agora, e sem revisão não há o que "
                f"ajustar. Tente de novo em instantes. ({e})")
        p = db.table("pedidos_contrato").select("*").eq("id", pedido_id) \
            .limit(1).execute().data[0]
        if not p.get("revisao"):
            raise ValueError("A revisão não retornou apontamentos. Tente de "
                             "novo em instantes.")

    # A LISTA QUE AS VEZES NAO VEM COMO LISTA
    #
    # O esquema da ferramenta pede uma lista de objetos, e o modelo
    # quase sempre entrega isso. Quando entrega texto, o `for` abaixo
    # percorria letra por letra e estourava em `a.get(...)`: o
    # operador clicava em aplicar os apontamentos e recebia um erro de
    # servidor, com o pedido parado na fase.
    apontamentos = _dados.lista_de_dicts(
        _dados.como_dict(p.get("revisao")).get("apontamentos"), "problema")
    if not apontamentos:
        db.table("pedidos_contrato").update({
            "fase": "REVISAO_ADV", "atualizado_em": _agora()}).eq("id", pedido_id).execute()
        return {"ok": True, "fase": "REVISAO_ADV",
                "aviso": "A revisão não apontou correções; segue para a conferência final."}

    s = get_settings()
    def _linha_do_apontamento(a: dict) -> str:
        # Campo que não veio não entra como a palavra "None": o modelo lê
        # isso como se fosse conteúdo, e devolve cláusula com "None"
        # escrito dentro.
        cabeca = " ".join(x for x in [
            f"[{_dados.texto_de(a.get('gravidade'))}]" if a.get("gravidade") else "",
            f"{_dados.texto_de(a.get('clausula'))}:" if a.get("clausula") else "",
            _dados.texto_de(a.get("problema") or a.get("texto")),
        ] if x)
        sugestao = _dados.texto_de(a.get("sugestao"))
        return f"- {cabeca}" + (f"\n  Sugestão: {sugestao}" if sugestao else "")

    lista = "\n".join(_linha_do_apontamento(a) for a in apontamentos)
    r = _claude().messages.create(
        model=s.claude_model, max_tokens=8000, system=SYSTEM_REDATOR,
        messages=[{"role": "user", "content":
                   f"Reescreva o contrato abaixo aplicando TODOS os apontamentos "
                   f"da revisão. Mantenha o que está correto; mude só o que foi "
                   f"apontado. Devolva o contrato completo.\n\n"
                   f"APONTAMENTOS:\n{lista}\n\nCONTRATO ATUAL:\n{p['minuta'][:40000]}"}],
    )
    texto = "".join(b.text for b in r.content if b.type == "text").strip()

    # AS DUAS TRAVAS QUE A REVISÃO JÁ TINHA, E O AJUSTE NÃO
    #
    # Aqui o contrato inteiro é SUBSTITUÍDO pelo que voltou do modelo.
    # Resposta vazia gravava `minuta = ""` e empurrava o pedido para a
    # segunda revisão, que recusa minuta vazia logo na primeira linha. O
    # pedido ficava preso numa fase sem saída, com o relógio andando e o
    # prazo prometido ao cliente vencendo — e o contrato bom, que
    # existia um instante antes, sobrescrito por nada.
    #
    # Resposta cortada no limite é pior ainda: grava um contrato que
    # termina no meio de uma cláusula e tem cara de documento pronto.
    #
    # Falhar aqui é barato: o pedido fica onde está, com o texto que já
    # tinha, e quem clicou tenta de novo.
    if getattr(r, "stop_reason", "") == "max_tokens":
        registrar_evento(None, "CONTRATO_AJUSTE_CORTADO", {"pedido": pedido_id})
        raise ValueError("O contrato ajustado veio cortado no limite de "
                         "tamanho. O texto anterior foi mantido; tente de "
                         "novo, e se repetir o contrato precisa ser "
                         "ajustado em partes.")
    if len(texto) < 500:
        registrar_evento(None, "CONTRATO_AJUSTE_VAZIO",
                         {"pedido": pedido_id, "caracteres": len(texto)})
        raise ValueError("O ajuste não devolveu o contrato. O texto anterior "
                         "foi mantido; tente de novo em instantes.")

    campos = {"minuta": texto, "minuta_anterior": p["minuta"],
              "ajustado_em": _agora(), "atualizado_em": _agora()}

    # O QUE O AJUSTE DESCOBRIU QUE FALTA, E SÓ O CLIENTE TEM
    #
    # O redator marca o que não pode inventar com [A PREENCHER: ...].
    # Até aqui essas marcas seguiam em frente e chegavam à conferência
    # final, quando já era tarde: o advogado devolvia o documento e o
    # pedido perdia um dia por um dado de uma linha.
    #
    # Agora o ajuste lê as próprias marcas, transforma cada uma em
    # pendência e pergunta ao cliente pelos três canais. O relógio
    # para enquanto a resposta não vem, que é o mesmo tratamento das
    # pendências da coleta: esperar o cliente não pode consumir o
    # prazo que o escritório prometeu.
    # O QUE DEPENDE DA DECISÃO DO CLIENTE
    #
    # A revisão marca esses pontos um a um. Eles não se resolvem aqui
    # dentro: o cliente pediu uma coisa, a lei diz outra, e a escolha
    # entre perder o que pediu e assinar algo frágil é dele. O pedido
    # para em CIENCIA_ALTERACAO, com o relógio parado, e a pergunta
    # sai pelos três canais.
    a_decidir = [a for a in apontamentos if a.get("precisa_autorizacao")]
    if a_decidir and not auto and not _ja_perguntado(p, a_decidir):
        campos.update({"fase": "CIENCIA_ALTERACAO", "fase_em": _agora(),
                       "avanca_em": None})
        db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
        _pedir_ciencia_da_alteracao(pedido_id, p, a_decidir)
        return {"ok": True, "fase": "CIENCIA_ALTERACAO",
                "aguardando_decisao": [a.get("clausula") for a in a_decidir]}

    faltas = _faltas_da_minuta(texto)
    if faltas and not auto:
        campos["avanca_em"] = None
        db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
        estado = revisar_pendencias(pedido_id)
        try:
            recado(pedido_id,
                   "Estou finalizando o seu documento e preciso de "
                   + ("uma informação" if len(faltas) == 1 else
                      f"{len(faltas)} informações")
                   + " que só você tem:\n\n"
                   + "\n".join(f"· {f}" for f in faltas)
                   + "\n\nPode responder por aqui, pelo e-mail ou pelo "
                     "WhatsApp, como for melhor. Assim que chegar, eu "
                     "complemento e o documento segue.",
                   canais=["PLATAFORMA", "EMAIL", "WHATSAPP"], autor="AGENTE",
                   assunto="Falta uma informação para concluir o seu documento")
        except Exception as e:
            print(f"[balcao] pedido de informação não enviado: {e}")
        registrar_evento(None, "CONTRATO_AJUSTE_PEDIU_INFORMACAO",
                         {"pedido": pedido_id, "faltas": faltas})
        return {"ok": True, "fase": "AJUSTE", "aguardando_cliente": True,
                "faltas": faltas, "pendencias": estado}

    if not auto:
        # Direto para o advogado. A conferência automática que havia
        # aqui repetia, pior, o trabalho de quem lê a íntegra logo
        # depois, e custava uma hora de prazo por pedido.
        campos.update({"fase": "REVISAO_ADV", "fase_em": _agora(),
                       "avanca_em": None})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_AJUSTADO",
                     {"pedido": pedido_id, "apontamentos": len(apontamentos),
                      "auto": auto})
    return {"ok": True, "fase": "AJUSTE" if auto else "REVISAO_ADV",
            "aplicados": len(apontamentos)}


_MARCA_DE_FALTA = re.compile(r"\[A PREENCHER:?\s*([^\]]{3,160})\]", re.I)


def _faltas_da_minuta(texto: str) -> list[str]:
    """As marcas que o redator deixou onde não podia inventar.

    Sem duplicar: o mesmo dado costuma aparecer no quadro resumo e no
    corpo, e pedir duas vezes a mesma coisa faz o cliente achar que
    ninguém leu a resposta dele."""
    vistos: list[str] = []
    for achado in _MARCA_DE_FALTA.findall(texto or ""):
        limpo = " ".join(achado.split()).strip(" .:;,")
        chave = limpo.lower()
        if limpo and chave not in [v.lower() for v in vistos]:
            vistos.append(limpo)
    return vistos[:12]



# ── A DECISÃO QUE É DO CLIENTE, E DE MAIS NINGUÉM ──────────────
#
# A revisão encontra um ponto em que o que o cliente pediu contraria a
# lei ou a jurisprudência. O escritório tem duas saídas honestas, e
# nenhuma delas é decidir sozinho: escrever do jeito que ele pediu,
# com a ciência do risco registrada, ou adequar. Quem escolhe é ele.
#
# O registro importa tanto quanto a pergunta. Se um dia a cláusula
# cair, a diferença entre o escritório ter avisado e não ter avisado
# está guardada aqui, com data, hora e o texto exato que ele leu.

def _chave_do_ponto(a: dict) -> str:
    return f"{a.get('clausula', '')}|{(a.get('problema') or '')[:80]}".lower()


def _ja_perguntado(pedido: dict, pontos: list[dict]) -> bool:
    """Evita perguntar duas vezes a mesma coisa.

    O ajuste roda de novo a cada resposta do cliente, e sem isto a
    segunda passada repetiria a pergunta que ele acabou de responder."""
    decididos = {d.get("chave")
                 for d in _dados.lista_de_dicts(pedido.get("decisoes"), "chave")}
    return all(_chave_do_ponto(a) in decididos for a in pontos)


def _pedir_ciencia_da_alteracao(pedido_id: str, pedido: dict,
                                pontos: list[dict]) -> None:
    db = get_db()
    abertos = []
    for a in pontos:
        abertos.append({
            "chave": _chave_do_ponto(a),
            "clausula": a.get("clausula"),
            "o_que_a_lei_diz": a.get("o_que_a_lei_diz") or a.get("problema"),
            "sugestao": a.get("sugestao"),
            "perguntado_em": _agora(),
            "escolha": None,
        })
    db.table("pedidos_contrato").update({
        "decisoes_pendentes": abertos, "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    lista = "\n\n".join(
        f"{i + 1}. {a['clausula']}\n{a['o_que_a_lei_diz']}"
        for i, a in enumerate(abertos))
    texto = (
        "Terminei a primeira revisão do seu documento e preciso de uma "
        "decisão sua antes de seguir.\n\n" + lista + "\n\n"
        "Você escolhe: manter do jeito que pediu, e fica registrado que "
        "o escritório te explicou o risco, ou adequar à lei. Pode "
        "responder por aqui, pelo e-mail ou pelo WhatsApp. O prazo fica "
        "parado até a sua resposta.")
    try:
        recado(pedido_id, texto, canais=["PLATAFORMA", "EMAIL", "WHATSAPP"],
               autor="AGENTE",
               assunto="Uma decisão sua para concluir o documento")
    except Exception as e:
        print(f"[balcao] ciência da alteração não enviada: {e}")

    registrar_evento(None, "BALCAO_CIENCIA_PEDIDA",
                     {"pedido_id": pedido_id,
                      "pontos": [a["clausula"] for a in abertos]})


def registrar_decisao(pedido_id: str, chave: str, escolha: str,
                      observacao: str = "") -> dict:
    """MANTER ou ADEQUAR, com data, hora e o texto que ele leu.

    Só quando a última pendência é decidida o pedido volta a andar: um
    contrato com metade das escolhas feitas não pode ir para a segunda
    revisão, porque o revisor não teria como saber o que é definitivo."""
    db = get_db()
    p = _pedido(pedido_id)
    escolha = (escolha or "").upper()
    if escolha not in ("MANTER", "ADEQUAR"):
        raise ValueError("A escolha precisa ser MANTER ou ADEQUAR.")

    pendentes = list(p.get("decisoes_pendentes") or [])
    decisoes = _dados.lista_de_dicts(p.get("decisoes"), "chave")
    achou = None
    for item in pendentes:
        if item.get("chave") == chave:
            achou = item
            break
    if not achou:
        raise ValueError("Este ponto não está pendente de decisão.")

    achou["escolha"] = escolha
    achou["observacao"] = (observacao or "")[:1000]
    achou["decidido_em"] = _agora()
    decisoes.append(achou)
    pendentes = [x for x in pendentes if x.get("chave") != chave]

    campos = {"decisoes": decisoes, "decisoes_pendentes": pendentes,
              "atualizado_em": _agora()}
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_DECISAO_REGISTRADA",
                     {"pedido_id": pedido_id, "clausula": achou.get("clausula"),
                      "escolha": escolha})

    if pendentes:
        return {"ok": True, "faltam": len(pendentes)}

    # Todas decididas. O redator refaz o texto com as escolhas, e a
    # segunda revisão confere se o que voltou está coerente com elas.
    try:
        ajustar(pedido_id, auto=True)
    except Exception as e:
        print(f"[balcao] minuta não refeita agora: {e}")
    db.table("pedidos_contrato").update({
        "fase": "REVISAO_ADV", "fase_em": _agora(),
        "avanca_em": None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    try:
        recado(pedido_id,
               "Obrigado, já registrei a sua decisão. O documento foi "
               "atualizado e está com o advogado para a revisão final "
               "antes de chegar até você.",
               canais=["PLATAFORMA", "EMAIL"], autor="AGENTE")
    except Exception as e:
        print(f"[balcao] confirmação da decisão não enviada: {e}")
    return {"ok": True, "faltam": 0, "fase": "REVISAO_ADV"}


def revisar_segunda(pedido_id: str, auto: bool = False) -> dict:
    """A conferência do que mudou, não uma releitura do contrato todo.

    A primeira revisão já leu tudo. Esta olha uma coisa só: o texto
    que voltou depois do ajuste está coerente com o que foi apontado e
    com o que o cliente decidiu? Reler o contrato inteiro de novo
    produziria uma lista nova de preferências de redação e um ciclo
    que não fecha nunca."""
    db = get_db()
    p = _pedido(pedido_id)
    if not (p.get("minuta") or "").strip():
        raise ValueError("Não há minuta para conferir.")

    # ESTA FASE SAIU DO RITO
    #
    # Do ajuste o pedido vai direto para o advogado. Isto aqui existe só
    # para os pedidos que estavam nesta fase quando a mudança subiu.
    #
    # Já tendo conferência feita, o botão do operador só MOVE: gastar
    # uma chamada de IA para reler o que já foi lido atrasa quem está
    # esperando e, com a conta de IA bloqueada, impediria o pedido de
    # sair daqui.
    if p.get("revisao_2") and not auto:
        db.table("pedidos_contrato").update({
            "fase": "REVISAO_ADV", "fase_em": _agora(),
            "avanca_em": None, "atualizado_em": _agora(),
        }).eq("id", pedido_id).execute()
        registrar_evento(None, "CONTRATO_SAIU_DA_FASE_ANTIGA",
                         {"pedido": pedido_id, "de": "REVISAO_2"})
        return {"ok": True, "fase": "REVISAO_ADV", "ja_conferido": True}

    anteriores = _dados.lista_de_dicts(
        _dados.como_dict(p.get("revisao")).get("apontamentos"), "problema")
    decisoes = _dados.lista_de_dicts(p.get("decisoes"), "chave")
    s = get_settings()

    contexto = [
        "O QUE A PRIMEIRA REVISÃO APONTOU:",
        "\n".join(f"- [{a.get('gravidade')}] {a.get('clausula')}: "
                   f"{a.get('problema')}" for a in anteriores) or "nada",
    ]
    if decisoes:
        contexto += ["", "O QUE O CLIENTE DECIDIU, e que é definitivo:"]
        for d in decisoes:
            contexto.append(
                f"- {d.get('clausula')}: o cliente escolheu "
                f"{'MANTER como pediu, ciente do risco' if d.get('escolha') == 'MANTER' else 'ADEQUAR à lei'}."
                + (f" Observação dele: {d.get('observacao')}"
                   if d.get("observacao") else ""))
    contexto += ["", "CONTRATO ATUAL:", p["minuta"][:40000]]

    r = _claude().messages.create(
        model=s.claude_model, max_tokens=4000, system=SYSTEM_REVISAO_2,
        tools=[FERRAMENTA_REVISAO],
        tool_choice={"type": "tool", "name": "revisao"},
        messages=[{"role": "user", "content": "\n".join(contexto)}],
    )
    if getattr(r, "stop_reason", "") == "max_tokens":
        raise ValueError("A conferência veio cortada. Tente de novo.")
    dados = {}
    veio_resposta = False
    for bloco in r.content:
        if bloco.type == "tool_use" and bloco.name == "revisao":
            veio_resposta = True
            dados = _dados.como_dict(bloco.input)

    # A FORMA CERTA ANTES DE GRAVAR, E NÃO DEPOIS
    #
    # O esquema pede lista de objetos, mas quem responde é um modelo, e
    # de vez em quando ele manda a mesma coisa como texto. Gravar assim
    # contamina o pedido: quem for ler depois quebra, e o erro aparece
    # numa tela que não tem nada a ver com a revisão. Arrumar aqui é
    # arrumar uma vez só, no lugar em que o dado nasce.
    dados["apontamentos"] = _dados.lista_de_dicts(
        dados.get("apontamentos"), "problema")
    dados["parecer"] = _dados.texto_de(dados.get("parecer"))
    if not veio_resposta:
        raise ValueError("A conferência não retornou resultado. Tente de novo.")

    campos = {"revisao_2": dados, "revisado_2_em": _agora(),
              "atualizado_em": _agora()}
    if not auto:
        campos.update({"fase": "REVISAO_ADV", "fase_em": _agora(),
                       "avanca_em": None})
    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "CONTRATO_SEGUNDA_REVISAO",
                     {"pedido": pedido_id,
                      "apontamentos": len(dados.get("apontamentos") or []),
                      "auto": auto})
    return {"ok": True, "fase": "REVISAO_2" if auto else "REVISAO_ADV",
            "apontamentos": dados.get("apontamentos") or [],
            "parecer": dados.get("parecer", "")}



# ── A DÚVIDA DO ADVOGADO, NA CONFERÊNCIA FINAL ─────────────────
#
# Lendo o documento, o advogado percebe que falta um dado, ou que uma
# cláusula ficou ambígua porque o cliente descreveu o combinado de um
# jeito que cabe em duas leituras. Até aqui ele tinha duas saídas
# ruins: devolver o pedido para ajuste, o que refaz o caminho inteiro
# por causa de uma pergunta, ou escrever no WhatsApp por fora, o que
# deixa a resposta fora do registro do pedido.
#
# Agora ele pergunta daqui. A pergunta sai pelos três canais, a
# resposta do cliente volta pela conversa do pedido, por qualquer
# canal, e fica onde deve ficar. O relógio não anda porque nesta fase
# não existe relógio: a conferência final espera o advogado.

def perguntar_ao_cliente(pedido_id: str, pergunta: str,
                         quem: str = "") -> dict:
    """Uma dúvida do advogado sobre o documento, pelos três canais."""
    pergunta = (pergunta or "").strip()
    if len(pergunta) < 5:
        raise ValueError("Escreva a pergunta.")
    p = _pedido(pedido_id)

    db = get_db()
    abertas = list(p.get("duvidas_advogado") or [])
    abertas.append({"em": _agora(), "quem": quem or "advogado",
                    "pergunta": pergunta[:2000], "respondida_em": None})
    db.table("pedidos_contrato").update({
        "duvidas_advogado": abertas, "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    try:
        recado(pedido_id,
               "Estou com o seu documento na conferência final e preciso "
               "confirmar um ponto com você:\n\n" + pergunta
               + "\n\nPode responder por aqui, pelo e-mail ou pelo "
                 "WhatsApp. Assim que responder, eu concluo.",
               canais=["PLATAFORMA", "EMAIL", "WHATSAPP"], autor="ESCRITORIO",
               assunto="Uma dúvida sobre o seu documento")
    except Exception as e:
        print(f"[balcao] dúvida do advogado não enviada: {e}")

    registrar_evento(None, "BALCAO_DUVIDA_DO_ADVOGADO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True, "duvidas": len(abertas)}


def devolver_para_ajuste(pedido_id: str, motivo: str, quem: str = "") -> dict:
    """O advogado prefere que o redator refaça, em vez de editar à mão.

    Volta para AJUSTE, e não para REDACAO: o texto está quase pronto e
    reescrever do zero jogaria fora as duas revisões já feitas. O que
    o advogado escreveu entra como apontamento de gravidade alta, do
    lado dos que a revisão já tinha levantado."""
    motivo = (motivo or "").strip()
    if len(motivo) < 5:
        raise ValueError("Escreva o que precisa ser corrigido.")
    p = _pedido(pedido_id)

    revisao = _dados.como_dict(p.get("revisao"))
    apontamentos = _dados.lista_de_dicts(
        revisao.get("apontamentos"), "problema")
    apontamentos.append({
        "clausula": "Apontado pelo advogado na conferência final",
        "gravidade": "ALTA", "problema": motivo[:2000],
        "sugestao": motivo[:2000],
    })
    revisao["apontamentos"] = apontamentos

    get_db().table("pedidos_contrato").update({
        "revisao": revisao, "revisao_2": None,
        "fase": "AJUSTE", "fase_em": _agora(),
        "avanca_em": _mais(_janela("AJUSTE", bool(p.get("urgente")))),
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    try:
        ajustar(pedido_id, auto=True)
    except Exception as e:
        print(f"[balcao] ajuste não refeito agora: {e}")

    registrar_evento(None, "BALCAO_DEVOLVIDO_PELO_ADVOGADO",
                     {"pedido_id": pedido_id, "quem": quem,
                      "motivo": motivo[:300]})
    return {"ok": True, "fase": "AJUSTE"}


def liberar_para_cliente(pedido_id: str, quem: str = "",
                         forcar: bool = False) -> dict:
    """Revisão humana aprovada. É o único caminho até o cliente.

    Exige que o advogado tenha aberto o PDF antes. Não é burocracia: o
    texto pode estar impecável e a página sair com a cláusula quebrada
    no meio ou o timbre em cima do primeiro parágrafo, e quem recebe
    isso é o cliente. `forcar` existe para o dia em que o LibreOffice
    estiver fora do ar e o documento precisar sair mesmo assim."""
    db = get_db()
    r = db.table("pedidos_contrato").select("visto_advogado_em,numero") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    if not r[0].get("visto_advogado_em") and not forcar:
        raise ValueError("Abra o PDF e confira o layout antes de liberar.")

    # O RELÓGIO DOS 7 DIAS COMEÇA AQUI
    #
    # Antes ele começava na entrega, que é depois da assinatura. Mas o
    # que o termo promete ao cliente é prazo para revisar e aprovar, e
    # isso acontece agora, quando o documento fica disponível. Contar da
    # entrega dava ao cliente um prazo que ele já tinha gastado.
    from datetime import date, timedelta
    ate = (date.today() + timedelta(days=DIAS_PARA_ALTERAR)).isoformat()

    # Liberado ao cliente, o prazo do escritório acabou: o
    # compromisso sai da agenda em vez de ficar vencendo sozinho.
    try:
        from . import agenda as _ag
        _ag.fechar_espelho(pedido_id=pedido_id)
    except Exception as e:
        print(f"[balcao] espelho do prazo não fechado: {e}")

    db.table("pedidos_contrato").update({
        "fase": "APROVACAO", "aprovado_advogado_em": _agora(),
        "aprovado_advogado_por": quem or None,
        "disponibilizado_em": _agora(), "prazo_alteracao_ate": ate,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    try:
        recado(pedido_id,
               f"O seu documento está pronto e já passou pela revisão do "
               f"advogado. Acesse a sua página para ler e aprovar, ou pedir "
               f"ajuste se algo não refletir o que foi combinado. Você tem "
               f"até {ate[8:10]}/{ate[5:7]}/{ate[:4]}, sete dias a contar de "
               f"hoje; depois disso a solicitação é arquivada e a reabertura "
               f"passa a depender de um chamado.",
               canais=["EMAIL", "WHATSAPP"], autor="ESCRITORIO",
               assunto=f"Seu documento está pronto para revisão, "
                       f"{r[0].get('numero')}")
    except Exception as e:
        print(f"[balcao] cliente não avisado da liberação: {e}")

    registrar_evento(None, "CONTRATO_LIBERADO", {"pedido": pedido_id, "por": quem})
    return {"ok": True, "fase": "APROVACAO"}


def pedir_alteracao(pedido_id: str, texto: str) -> dict:
    """O cliente leu e quer mudança. O documento volta ao começo.

    Volta para o redator e refaz o caminho inteiro, primeira revisão
    inclusive. Parece caro, e é o único jeito honesto: mudar uma
    cláusula mexe em outras, e emendar direto na versão que o advogado
    já tinha aprovado entregaria ao cliente um texto que ninguém leu
    depois da emenda.

    O que não se refaz é a conversa já tida. As decisões que ele já
    tomou ficam gravadas e valem: a revisão não vai perguntar de novo
    o que ele já respondeu, e o redator mexe SÓ no que foi pedido
    agora. Repetir a mesma pergunta a cada rodada é o jeito mais
    rápido de fazer alguém desistir de pedir ajuste."""
    db = get_db()
    achado = db.table("pedidos_contrato") \
        .select("pedidos_alteracao,minuta,urgente") \
        .eq("id", pedido_id).limit(1).execute().data
    p = achado[0] if achado else {}
    anteriores = _dados.lista_de_dicts(p.get("pedidos_alteracao"), "texto")
    anteriores.append({"em": _agora(), "texto": texto, "atendido": False})

    db.table("pedidos_contrato").update({
        "pedidos_alteracao": anteriores,
        "fase": "REDACAO", "fase_em": _agora(),
        "avanca_em": _mais(_janela("REDACAO", bool(p.get("urgente")))),
        # A revisão anterior sai de cena: ela leu um texto que vai
        # mudar. As decisões do cliente, não: aquilo ele já respondeu.
        "revisao": None, "revisao_2": None,
        "minuta_anterior": p.get("minuta"),
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    # O redator já começa, sem esperar a esteira. Quem pediu ajuste
    # está olhando a tela agora.
    try:
        redigir(pedido_id, auto=True)
    except Exception as e:
        print(f"[balcao] minuta não refeita agora, fica para a esteira: {e}")

    registrar_evento(None, "CONTRATO_ALTERACAO_PEDIDA",
                     {"pedido": pedido_id, "texto": texto[:300]})
    return {"ok": True, "fase": "REDACAO"}


# ── O fim do rito: entrega, janela de alteração e arquivo ───────
#
# As fases ENTREGUE e ARQUIVADO existiam na lista desde o começo e
# nenhuma função levava o pedido até elas — o pedido chegava a
# ASSINATURA e parava ali para sempre. É isto que faltava.

DIAS_PARA_ALTERAR = 7


def registrar_pagamento(pedido_id: str, txid: str = "",
                        quem: str = "") -> dict:
    """Confirma o PIX e devolve a conversa ao cliente.

    A confirmação é humana de propósito: não há integração com o banco,
    e inventar uma baixa automática seria pior do que não ter nenhuma —
    o escritório escreveria o contrato de alguém que não pagou e
    descobriria depois. Quando o banco digital entrar, é esta função que
    passa a ser chamada pelo webhook, e o resto do rito não muda.

    O pedido vai para COLETA, e não direto para REDACAO: é agora que o
    atendimento pergunta o que o documento exige. O recado sai pelos
    canais que o cliente tiver, porque quem acabou de pagar fecha a
    página e vai fazer outra coisa."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("fase,numero,tipo,servico_livre,cliente_id") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]

    db.table("pedidos_contrato").update({
        "pago_em": _agora(), "pix_txid": (txid or "")[:120] or None,
        "fase": "COLETA", "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    nome_doc = (catalogo.detalhe(p.get("tipo") or "") or {}).get("nome") \
        or p.get("servico_livre") or "documento"
    abertura = (
        f"Pagamento confirmado. Obrigado pela confiança.\n\n"
        f"Agora preciso das informações para escrever o seu {nome_doc}. "
        f"Você pode digitar aqui ou enviar cópia dos documentos por foto "
        f"ou PDF, o que for mais fácil, e dá para misturar os dois.\n\n"
        f"Uma escolha antes de começar: o documento pode sair no papel "
        f"timbrado do escritório, que mostra quem redigiu e costuma pesar "
        f"quando a outra parte lê, ou em folha branca, sem identificação. "
        f"Os dois têm o mesmo valor jurídico. Qual você prefere?")
    try:
        db.table("pedidos_mensagens").insert({
            "pedido_id": pedido_id, "autor": "AGENTE", "texto": abertura,
            "canais": ["PLATAFORMA"],
        }).execute()
    except Exception as e:
        print(f"[balcao] abertura da coleta não registrada: {e}")

    try:
        recado(pedido_id,
               f"Recebemos o seu pagamento do pedido {p.get('numero')}. "
               f"Acesse a sua página para informar os dados do documento.",
               canais=["EMAIL", "WHATSAPP"], autor="AGENTE",
               assunto=f"Pagamento confirmado, pedido {p.get('numero')}")
    except Exception as e:
        print(f"[balcao] cliente não avisado do pagamento: {e}")

    # O PRAZO ENTRA NA AGENDA AGORA
    #
    # É daqui que o relógio corre, então é daqui que o compromisso
    # existe. Antes o prazo de entrega vivia só no card do balcão, e
    # quem olhava a agenda não via nada: o escritório tinha contrato
    # para entregar às 14h e nenhuma das telas de trabalho dizia isso.
    try:
        from . import agenda as _ag
        _ag.sincronizar_pedido(pedido_id)
    except Exception as e:
        print(f"[balcao] prazo não entrou na agenda: {e}")

    registrar_evento(None, "BALCAO_PAGO",
                     {"pedido_id": pedido_id, "quem": quem, "txid": txid})
    return {"ok": True, "fase": "COLETA"}


def concluir_coleta(pedido_id: str, com_timbre: bool | None = None) -> dict:
    """O cliente terminou de informar. Daqui o redator assume.

    `com_timbre` chega agora, e não na primeira tela: é aqui que a
    pergunta faz sentido. Quem não responde fica com o timbre, que é o
    padrão, e `timbre_escolhido` guarda a diferença entre ter escolhido
    e ter aceitado o padrão."""
    db = get_db()
    r = db.table("pedidos_contrato").select("fase,dados,pago_em") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    if not r[0].get("pago_em"):
        raise ValueError("A coleta começa depois do pagamento confirmado.")

    # O QUE FALTA NÃO IMPEDE COMEÇAR
    #
    # Antes, faltando qualquer coisa a coleta era recusada e o cliente
    # ficava parado. Agora o trabalho começa: a maior parte do contrato
    # não depende daquele dado, e escrever o que já dá para escrever
    # adianta o prazo de todo mundo.
    #
    # O que falta vira pendência, e é a pendência que decide o rito:
    # a que é indispensável segura a entrega e para o relógio; a que é
    # complementar só avisa, e pode chegar até o fim da confecção.
    pend = pendencias_do_pedido(pedido_id)

    campos = {"fase": "REDACAO", "fase_em": _agora(),
              "pendencias": pend["itens"],
              "atualizado_em": _agora()}
    if com_timbre is not None:
        campos["com_timbre"] = bool(com_timbre)
        campos["timbre_escolhido"] = True

    # O RELÓGIO SÓ ANDA COM O PEDIDO COMPLETO
    #
    # Faltando informação indispensável, contar as quatro horas seria
    # medir uma espera que não é do escritório. `avanca_em` nulo é o
    # relógio parado; ele volta a andar quando a última pendência for
    # atendida.
    campos["avanca_em"] = None if pend["trava"] else _mais(JANELA_REDACAO)
    # Nascendo travado, a espera começa a contar agora.
    if pend["trava"]:
        campos["relogio_parado_em"] = _agora()

    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_COLETA_CONCLUIDA",
                     {"pedido_id": pedido_id, "com_timbre": com_timbre,
                      "pendencias": len(pend["itens"]), "trava": pend["trava"]})

    if pend["itens"]:
        try:
            _guardar_recado_de_pendencia(pedido_id, pend)
        except Exception as e:
            print(f"[balcao] aviso de pendência não registrado: {e}")

    # A REDAÇÃO COMEÇA AGORA, NÃO NO PRÓXIMO CICLO
    #
    # Esperar o agendador significaria até quinze minutos de nada
    # acontecendo logo depois do gesto mais importante do cliente, que
    # é terminar de informar. A minuta fica pronta em cerca de um
    # minuto; a fase é que continua em elaboração pelas quatro horas.
    #
    # A falha aqui não derruba a conclusão da coleta: se a redação
    # falhar, o agendador tenta de novo no próximo ciclo, e o cliente
    # nem fica sabendo que houve um tropeço.
    try:
        redigir(pedido_id, auto=True)
    except Exception as e:
        print(f"[balcao] redação imediata falhou, fica para a esteira: {e}")

    return {"ok": True, "fase": "REDACAO"}


def entregar(pedido_id: str, link: str = "", quem: str = "") -> dict:
    """Entrega ao cliente e abre a janela de sete dias.

    A janela é contada a partir daqui, e não da aprovação: o prazo de
    reclamar começa quando a pessoa tem o documento na mão."""
    from datetime import date, timedelta
    db = get_db()
    r = db.table("pedidos_contrato").select("*,clientes(nome,email)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    pedido = r[0]
    ate = (date.today() + timedelta(days=DIAS_PARA_ALTERAR)).isoformat()

    db.table("pedidos_contrato").update({
        "fase": "ENTREGUE", "entregue_em": _agora(),
        "prazo_alteracao_ate": ate,
        "entrega_link": (link or "")[:600] or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    cliente = pedido.get("clientes") or {}
    if cliente.get("email"):
        try:
            from ..integracoes import avisos
            s = get_settings()
            url = link or f"{s.app_url.rstrip('/')}/balcao/{pedido_id}"
            texto = (
                f"Seu contrato está pronto.\n\n"
                f"Pedido {pedido.get('numero')}.\n"
                f"Acesse: {url}\n\n"
                f"Você tem até {ate[8:10]}/{ate[5:7]}/{ate[:4]} para pedir "
                f"ajustes sem custo. Depois dessa data o pedido é arquivado.")
            avisos.enviar_email(
                cliente["email"], f"Seu contrato está pronto, {pedido.get('numero')}",
                texto, texto.replace("\n", "<br>"))
        except Exception as e:
            print(f"[balcao] entrega não avisada por e-mail: {e}")

    registrar_evento(None, "BALCAO_ENTREGUE",
                     {"pedido_id": pedido_id, "quem": quem, "ate": ate})
    return {"ok": True, "fase": "ENTREGUE", "prazo_alteracao_ate": ate}


def arquivar(pedido_id: str, quem: str = "") -> dict:
    db = get_db()
    db.table("pedidos_contrato").update({
        "fase": "ARQUIVADO", "arquivado_em": _agora(),
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_ARQUIVADO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True, "fase": "ARQUIVADO"}


def arquivar_vencidos() -> dict:
    """Tira da vista o que passou dos sete dias.

    Roda com a controladoria. Sem isto a coluna Entregue vira depósito:
    em três meses ninguém distingue o que foi entregue ontem do que foi
    entregue em março."""
    from datetime import date
    db = get_db()
    hoje = date.today().isoformat()
    # Duas fases, e não uma. ENTREGUE é quem já assinou e tem os sete
    # dias de ajuste. APROVACAO é quem recebeu o documento para revisar
    # e sumiu: é justamente esse que o termo promete arquivar, e era o
    # que ficava parado para sempre na coluna do operador.
    vencidos = db.table("pedidos_contrato").select("id,numero,fase") \
        .in_("fase", ["ENTREGUE", "APROVACAO"]) \
        .lt("prazo_alteracao_ate", hoje) \
        .is_("excluido_em", "null") \
        .limit(200).execute().data or []
    for p in vencidos:
        try:
            arquivar(p["id"], quem="sistema")
            if p.get("fase") == "APROVACAO":
                recado(p["id"],
                       "Passaram os sete dias para revisão e o seu documento "
                       "foi arquivado. Ele não se perdeu: abra um pedido de "
                       "desarquivamento na sua área, explicando o motivo, e o "
                       "escritório retoma.",
                       canais=["EMAIL"], autor="AGENTE",
                       assunto=f"Pedido {p.get('numero')} arquivado")
        except Exception as e:
            print(f"[balcao] não arquivou {p.get('numero')}: {e}")
    return {"arquivados": len(vencidos)}


# ══════════════════════════════════════════════════════════════════
# RECADO AO CLIENTE, PELOS CANAIS QUE ELE TIVER
#
# O escritório escrevia na conversa do pedido e pronto. Quem não abrisse
# a plataforma não ficava sabendo de nada, e a plataforma é justamente o
# lugar em que ninguém entra sem motivo.
#
# Três canais, com papéis diferentes:
#
#   PLATAFORMA  é a própria linha da tabela, e por isso nunca falha. É
#               também o único registro que fica, com data e hora.
#   EMAIL       o que chega a quem não está com o celular na mão.
#   WHATSAPP    o que a pessoa realmente lê. Ainda não está ligado: a
#               função tenta, falha com elegância e anota a falha, e no
#               dia em que o número for aprovado nada mais muda aqui.
#
# A falha de um canal não derruba os outros, e fica gravada. "Ninguém me
# avisou" se responde com a linha desta tabela, não com memória.
# ══════════════════════════════════════════════════════════════════

CANAIS = ("PLATAFORMA", "EMAIL", "WHATSAPP")


def recado(pedido_id: str, texto: str, canais: list[str] | None = None,
           autor: str = "ESCRITORIO", assunto: str = "") -> dict:
    """Manda um recado ao cliente do balcão e registra por onde saiu."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("A mensagem está vazia.")

    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("numero,cliente_id,clientes(nome,email,whatsapp)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    cli = p.get("clientes") or {}

    pedidos = [c.upper() for c in (canais or ["PLATAFORMA", "EMAIL"])
               if c.upper() in CANAIS]
    if "PLATAFORMA" not in pedidos:
        pedidos.insert(0, "PLATAFORMA")

    s = get_settings()
    url = f"{s.app_url.rstrip('/')}/balcao/{pedido_id}"

    # A CONVERSA PRIMEIRO, OS CANAIS DEPOIS
    #
    # A mensagem era gravada só DEPOIS de tentar o e-mail e o WhatsApp.
    # Parece detalhe e custava vinte segundos: o SMTP leva alguns, e o
    # WhatsApp de um número ainda não aprovado espera o tempo inteiro
    # do timeout antes de falhar. Durante tudo isso a linha não existia
    # no banco, então a tela do cliente, relendo de quatro em quatro
    # segundos, não tinha o que mostrar. O advogado digitava "oi" e o
    # cliente via "oi" vinte segundos depois.
    #
    # A plataforma é a conversa, e conversa não espera correio. A linha
    # entra agora, aparece na próxima batida, e os carimbos de entrega
    # voltam para ela quando os canais responderem — inclusive a falha,
    # que continua registrada onde sempre esteve.
    linha = db.table("pedidos_mensagens").insert({
        "pedido_id": pedido_id,
        "autor": autor if autor in ("ESCRITORIO", "AGENTE", "CLIENTE") else "ESCRITORIO",
        "texto": texto[:4000], "canais": pedidos,
    }).execute().data
    msg_id = (linha[0] or {}).get("id") if linha else None

    # ESCREVER É ASSUMIR, MAS SÓ NOS CANAIS QUE SÃO CONVERSA
    #
    # Quem do escritório fala com o cliente pelo chat ou pelo WhatsApp
    # está numa conversa: o cliente está do outro lado, agora, e vai
    # responder em seguida. Aí o agente precisa calar, ou os dois
    # escrevem por cima um do outro.
    #
    # Fica aqui, antes dos envios externos, e não depois: nos segundos
    # que o e-mail leva para sair, o cliente pode escrever de novo, e o
    # agente responderia por cima de quem acabou de assumir.
    #
    # E-mail é outra coisa. Ele tem o ritmo dele, manda-se e espera-se o
    # dia seguinte. Calar o agente por causa de um e-mail enviado de
    # manhã deixaria o cliente que abre o chat à tarde sem ninguém para
    # responder, por uma troca que nem era ao vivo.
    if autor == "ESCRITORIO" and ("PLATAFORMA" in pedidos
                                  or "WHATSAPP" in pedidos):
        assumir_conversa(pedido_id, quem=assunto or "escritório")

    falhas: list[str] = []
    email_em = whats_em = None

    if "EMAIL" in pedidos and cli.get("email"):
        try:
            from ..integracoes import avisos
            corpo = (f"{texto}\n\n"
                     f"Pedido {p.get('numero')}.\n"
                     f"Acesse a sua página: {url}")
            avisos.enviar_email(
                cli["email"],
                assunto or f"Sobre o seu pedido {p.get('numero')}",
                corpo, corpo.replace("\n", "<br>"))
            email_em = _agora()
        except Exception as e:
            falhas.append(f"email: {e}")

    if "WHATSAPP" in pedidos and cli.get("whatsapp"):
        try:
            from ..integracoes import avisos
            phone_id, _ = avisos.escolher_origem(cli.get("whatsapp"))
            avisos.enviar_whatsapp(
                cli["whatsapp"], f"{texto}\n\nPedido {p.get('numero')}\n{url}",
                phone_id)
            whats_em = _agora()
        except Exception as e:
            falhas.append(f"whatsapp: {e}")

    if msg_id and (email_em or whats_em or falhas):
        try:
            db.table("pedidos_mensagens").update({
                "email_em": email_em, "whatsapp_em": whats_em,
                "falha": "; ".join(falhas)[:500] or None,
            }).eq("id", msg_id).execute()
            linha[0].update({"email_em": email_em, "whatsapp_em": whats_em,
                             "falha": "; ".join(falhas)[:500] or None})
        except Exception as e:
            print(f"[balcao] carimbo de entrega não gravado: {e}")

    registrar_evento(None, "BALCAO_RECADO",
                     {"pedido_id": pedido_id, "canais": pedidos,
                      "falhas": falhas})
    return {"ok": True, "canais": pedidos, "falhas": falhas,
            "mensagem": linha[0] if linha else None,
            "atendimento": quem_atende(pedido_id)}


def excluir(pedido_id: str, quem: str = "", motivo: str = "") -> dict:
    """Tira o pedido da esteira sem apagar a prova de que ele existiu.

    Exclusão física levaria junto a conversa, o comprovante do PIX e a
    ciência registrada, que são exatamente as três coisas de que o
    escritório precisaria se o cliente reclamasse depois. O pedido sai
    da vista e permanece no banco."""
    db = get_db()
    r = db.table("pedidos_contrato").select("numero,fase,pago_em") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    if p.get("pago_em") and not motivo.strip():
        raise ValueError("Este pedido foi pago. Explique o motivo da exclusão.")

    db.table("pedidos_contrato").update({
        "excluido_em": _agora(), "excluido_por": quem or "escritório",
        "excluido_motivo": (motivo or "")[:500] or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_EXCLUIDO",
                     {"pedido_id": pedido_id, "numero": p.get("numero"),
                      "fase": p.get("fase"), "quem": quem, "motivo": motivo})
    return {"ok": True, "numero": p.get("numero")}


def restaurar(pedido_id: str, quem: str = "") -> dict:
    """Desfaz a exclusão. Existe porque todo botão de excluir erra um dia."""
    get_db().table("pedidos_contrato").update({
        "excluido_em": None, "excluido_por": None, "excluido_motivo": None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_RESTAURADO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════
# O PDF QUE O ADVOGADO VÊ ANTES DO CLIENTE
#
# Texto aprovado e página torta chegam tortos ao cliente. Aprovar o
# conteúdo e conferir o layout são duas coisas, e o sistema tratava como
# uma só: a minuta ia como texto puro e ninguém via a página montada.
#
# Agora a aprovação do advogado gera o PDF, ele abre, confere, e só
# então o botão de liberar fica disponível. É o mesmo cuidado de sempre,
# com um passo a mais e uma marca de tempo para cada um.
# ══════════════════════════════════════════════════════════════════

# ── O TIMBRE É A LOGO, E SÓ ELA ────────────────────────────────
#
# O cabeçalho era três linhas de texto: a razão social, o nome do
# advogado com a OAB e as cidades. Saía como qualquer parágrafo do
# contrato, em Arial preto, e o documento abria parecendo um ofício
# datilografado. Pior: repetia o nome do advogado no topo de um
# contrato entre duas outras pessoas, onde o escritório não é parte.
#
# Papel timbrado é a marca do escritório, uma vez, no alto. Quem
# redigiu se identifica no rodapé, com o número do pedido, e é só o que
# precisa estar ali.
#
# O papel timbrado mora em core/timbre, porque não é só do balcão: o
# relatório do caso e tudo o mais que sai em nome do escritório usam
# o mesmo. Duas cópias da mesma faixa divergem no dia em que uma for
# atualizada.
from ..core import timbre as _timbre

TIMBRE_TOPO = _timbre.TOPO
TIMBRE_PE = _timbre.PE


def _docx_da_minuta(texto: str, com_timbre: bool, numero: str = "") -> bytes:
    """Monta o .docx da minuta no padrão de contrato do escritório.

    A régua tipográfica e o reconhecimento da estrutura estão em
    `core/formato`: é lá que se decide o que é título de cláusula, o que
    é quadro resumo e o que é campo de assinatura. Aqui fica só a folha
    (margem, timbre, numeração de página), porque é a folha que muda
    entre o contrato timbrado e a versão sem marca."""
    import io
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    from ..core import formato

    doc = Document()
    for sec in doc.sections:
        # Com timbre, as margens são as do papel do escritório: a faixa
        # ocupa o alto e o texto começa abaixo dela. Sem timbre, a
        # margem superior maior é o que dá ao documento o respiro que a
        # faixa daria.
        sec.left_margin = Cm(2.5 if com_timbre else 3)
        sec.right_margin = Cm(2)
        if com_timbre:
            # `aplicar` também acerta as margens: a faixa tem 3,3 cm de
            # altura, e margem superior curta faz o primeiro parágrafo
            # nascer por cima do brasão.
            _timbre.aplicar(sec)
        else:
            sec.top_margin = Cm(3)
            sec.bottom_margin = Cm(2.5)

    # O QUE ERA MARCAÇÃO VIRA FORMATAÇÃO
    #
    # Os modelos do escritório são arquivos markdown e o redator escreve
    # como eles. Jogar essas linhas cruas no documento fazia o contrato
    # chegar ao cliente com o quadro resumo em barras verticais e o
    # título da cláusula do mesmo tamanho do texto corrido.
    #
    # Quem decide o que é cada linha é `core/formato`, e o arquivo que
    # abre no Word sai do mesmo entendimento: o advogado confere num e o
    # cliente recebe no outro, então os dois têm de ser a mesma página.
    formato.no_docx(doc, texto)

    # A NUMERAÇÃO DE FOLHA
    #
    # Num contrato ela não é detalhe de impressão: é o que impede que uma
    # folha seja trocada depois da assinatura sem ninguém notar. Vai no
    # rodapé, miúda, abaixo da tarja de contatos quando há timbre.
    for sec in doc.sections:
        try:
            formato._numero_de_pagina(sec.footer)
        except Exception as e:
            print(f"[formato] numeração de folha não entrou: {e}")

    # O número do pedido fecha o documento, no corpo e na última folha,
    # que é onde alguém procura quando precisa citar o documento numa
    # conversa.
    if numero:
        rodape = doc.add_paragraph()
        rodape.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rodape.paragraph_format.space_before = Pt(18)
        r = rodape.add_run(f"Documento elaborado pelo escritório. Pedido {numero}.")
        r.font.size = Pt(8)
        r.font.name = formato.FONTE

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def gerar_pdf(pedido_id: str) -> tuple[bytes, str]:
    """Devolve (bytes do PDF, nome do arquivo) da minuta atual."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("minuta,com_timbre,numero,tipo,servico_livre") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    if not (p.get("minuta") or "").strip():
        raise ValueError("Este pedido ainda não tem minuta.")

    from . import documentos
    docx = _docx_da_minuta(p["minuta"], p.get("com_timbre") is not False,
                           p.get("numero") or "")
    pdf = documentos.converter_para_pdf(docx)

    db.table("pedidos_contrato").update({
        "pdf_gerado_em": _agora(), "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    nome = (catalogo.detalhe(p.get("tipo") or "") or {}).get("nome") \
        or p.get("servico_livre") or "documento"
    arquivo = f"{(p.get('numero') or 'pedido')}_{nome}.pdf".replace(" ", "_")
    registrar_evento(None, "BALCAO_PDF_GERADO",
                     {"pedido_id": pedido_id, "bytes": len(pdf)})
    return pdf, arquivo


def marcar_visto(pedido_id: str, quem: str = "") -> dict:
    """O advogado abriu o PDF e o layout está de pé."""
    get_db().table("pedidos_contrato").update({
        "visto_advogado_em": _agora(), "visto_advogado_por": quem or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()
    registrar_evento(None, "BALCAO_LAYOUT_CONFERIDO",
                     {"pedido_id": pedido_id, "quem": quem})
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════
# DESARQUIVAMENTO
#
# O termo promete ao cliente que o documento não se perde: passados os
# sete dias, a solicitação arquiva e ele pode abrir um chamado para
# retomá-la. Sem isto, a promessa não teria como ser cumprida, e o
# cliente arquivado só teria o telefone do escritório.
#
# Não é botão que reabre sozinho. Reabertura automática torna o prazo
# decorativo, e há casos em que retomar custa trabalho de verdade,
# porque o contrato envelheceu ou a outra parte desistiu. Quem decide é
# quem vai fazer, lendo o motivo escrito pelo cliente.
# ══════════════════════════════════════════════════════════════════

def pedir_desarquivamento(pedido_id: str, motivo: str,
                          cliente_id: str | None = None) -> dict:
    """O cliente explica por que quer o pedido de volta."""
    motivo = (motivo or "").strip()
    if len(motivo) < 15:
        raise ValueError(
            "Conte com um pouco mais de detalhe o que você precisa. "
            "É o que o escritório lê para decidir.")

    db = get_db()
    r = db.table("pedidos_contrato").select("id,numero,fase,cliente_id") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    if p.get("fase") != "ARQUIVADO":
        raise ValueError("Este pedido não está arquivado.")

    aberto = db.table("pedidos_desarquivamento").select("id,criado_em") \
        .eq("pedido_id", pedido_id).eq("status", "PENDENTE") \
        .limit(1).execute().data
    if aberto:
        raise ValueError(
            "Você já tem um pedido de desarquivamento em análise para este "
            "documento. O escritório responde por e-mail.")

    linha = db.table("pedidos_desarquivamento").insert({
        "pedido_id": pedido_id,
        "cliente_id": cliente_id or p.get("cliente_id"),
        "motivo": motivo[:2000],
    }).execute().data[0]

    try:
        s = get_settings()
        from ..integracoes import avisos
        avisos.enviar_email(
            s.email_escritorio,
            f"Pedido de desarquivamento, {p.get('numero')}",
            f"Um cliente pediu para reabrir o pedido {p.get('numero')}.\n\n"
            f"Motivo:\n{motivo}\n\n"
            f"Responda pela tela de Contratos.",
            "")
    except Exception as e:
        print(f"[balcao] escritório não avisado do desarquivamento: {e}")

    registrar_evento(None, "BALCAO_DESARQUIVAMENTO_PEDIDO",
                     {"pedido_id": pedido_id, "chamado": linha["id"]})
    return {"ok": True, "chamado": linha["id"]}


def responder_desarquivamento(chamado_id: str, aprovado: bool,
                              resposta: str = "", quem: str = "") -> dict:
    """O escritório decide. Aprovado, o pedido volta com prazo novo."""
    db = get_db()
    r = db.table("pedidos_desarquivamento").select("*").eq("id", chamado_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Chamado não encontrado.")
    c = r[0]
    if c["status"] != "PENDENTE":
        raise ValueError("Este chamado já foi respondido.")
    if not aprovado and not (resposta or "").strip():
        raise ValueError("Explique ao cliente por que não é possível reabrir.")

    db.table("pedidos_desarquivamento").update({
        "status": "APROVADO" if aprovado else "RECUSADO",
        "resposta": (resposta or "")[:2000] or None,
        "respondido_em": _agora(), "respondido_por": quem or "escritório",
    }).eq("id", chamado_id).execute()

    if aprovado and c.get("pedido_id"):
        # Volta para a revisão do cliente, com sete dias novos. Devolver
        # sem prazo faria o pedido ficar aberto para sempre, que é o que
        # o arquivamento existia para evitar.
        from datetime import date, timedelta
        ate = (date.today() + timedelta(days=DIAS_PARA_ALTERAR)).isoformat()
        db.table("pedidos_contrato").update({
            "fase": "APROVACAO", "arquivado_em": None,
            "prazo_alteracao_ate": ate, "atualizado_em": _agora(),
        }).eq("id", c["pedido_id"]).execute()

    if c.get("pedido_id"):
        try:
            texto = (
                f"Seu pedido de desarquivamento foi aprovado. O documento "
                f"voltou a ficar disponível na sua área para revisão e "
                f"aprovação, com prazo novo de {DIAS_PARA_ALTERAR} dias."
                if aprovado else
                f"Sobre o seu pedido de desarquivamento: {resposta}")
            recado(c["pedido_id"], texto, canais=["EMAIL"],
                   autor="ESCRITORIO",
                   assunto="Resposta ao seu pedido de desarquivamento")
        except Exception as e:
            print(f"[balcao] cliente não avisado da decisão: {e}")

    registrar_evento(None, "BALCAO_DESARQUIVAMENTO_RESPONDIDO",
                     {"chamado": chamado_id, "aprovado": aprovado,
                      "quem": quem})
    return {"ok": True, "aprovado": aprovado}


def desarquivamentos(status: str = "PENDENTE") -> list[dict]:
    return get_db().table("pedidos_desarquivamento") \
        .select("*,pedidos_contrato(numero,tipo,servico_livre,clientes(nome,email))") \
        .eq("status", status).order("criado_em", desc=True) \
        .limit(100).execute().data or []


# ══════════════════════════════════════════════════════════════════
# AS PARTES DO CONTRATO
#
# Todo contrato tem pelo menos duas partes, e o cliente é uma delas. Os
# dados da outra ficavam soltos dentro de `dados`, um JSON sem forma em
# que cada tipo usava nomes diferentes de campo. Conferir o que faltava
# era impossível, e a falta só aparecia na redação, com o redator
# inventando ou o escritório ligando para perguntar.
#
# Aqui a lista ganha forma, e com forma vem a conferência: antes de
# mandar para a redação, o atendimento diz exatamente o que falta e de
# quem. É a diferença entre "faltam informações" e "falta o CPF do
# fiador e o endereço do locatário".
# ══════════════════════════════════════════════════════════════════

# O mínimo para qualificar alguém num contrato. Não é a lista completa
# do Código Civil: é o que, faltando, dá trabalho para executar depois.
OBRIGATORIOS_PARTE = [
    ("nome", "nome completo"),
    ("cpf_cnpj", "CPF ou CNPJ"),
    ("endereco", "endereço completo"),
]
DESEJAVEIS_PARTE = [
    ("estado_civil", "estado civil"),
    ("email", "e-mail"),
]


def _papeis_do_tipo(tipo: str) -> list[str]:
    """Quem são as partes daquele tipo de contrato.

    Sai do próprio catálogo, lendo os campos de qualificação que ele já
    declara. Assim, tipo novo no catálogo já nasce com as partes certas
    aqui, sem ninguém precisar lembrar de atualizar uma segunda lista,
    que é o tipo de duplicação que envelhece mal."""
    t = catalogo.detalhe(tipo) or {}
    papeis: list[str] = []
    for c in t.get("campos") or []:
        campo = c.get("campo") or ""
        if campo.endswith("_nome"):
            papel = campo[:-5]
            if papel not in papeis:
                papeis.append(papel)
    return papeis or ["contratante", "contratada"]


def partes_do_pedido(pedido_id: str) -> dict:
    """O que já está preenchido, e o que falta, parte por parte."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("id,tipo,partes,dados,cliente_id,clientes(*)") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]

    papeis = _papeis_do_tipo(p["tipo"])
    guardadas = {x.get("papel"): x for x in (p.get("partes") or [])}

    # A primeira parte nasce preenchida com o cadastro do cliente. Ele
    # já informou tudo isso uma vez, e pedir de novo é a forma mais
    # rápida de fazer alguém desistir no meio.
    cli = p.get("clientes") or {}
    if papeis and papeis[0] not in guardadas and cli.get("nome"):
        guardadas[papeis[0]] = {
            "papel": papeis[0], "do_cliente": True,
            "nome": cli.get("nome"), "cpf_cnpj": cli.get("cpf_cnpj"),
            "estado_civil": cli.get("estado_civil"),
            "profissao": cli.get("profissao"),
            "nacionalidade": cli.get("nacionalidade"),
            "email": cli.get("email"), "telefone": cli.get("whatsapp"),
            "endereco": _endereco_do_cliente(cli),
        }

    partes, faltas = [], []
    for papel in papeis:
        parte = dict(guardadas.get(papel) or {"papel": papel})
        parte["papel"] = papel
        falta = [rot for campo, rot in OBRIGATORIOS_PARTE
                 if not str(parte.get(campo) or "").strip()]
        parte["falta"] = falta
        partes.append(parte)
        if falta:
            faltas.append({"papel": papel, "falta": falta})

    return {"partes": partes, "faltas": faltas,
            "completo": not faltas,
            "obrigatorios": [{"campo": c, "rotulo": r} for c, r in OBRIGATORIOS_PARTE],
            "desejaveis": [{"campo": c, "rotulo": r} for c, r in DESEJAVEIS_PARTE]}


def _endereco_do_cliente(cli: dict) -> str:
    pedacos = [cli.get("endereco_rua"), cli.get("endereco_numero"),
               cli.get("endereco_complemento"), cli.get("endereco_bairro"),
               cli.get("endereco_cidade"), cli.get("endereco_uf"),
               cli.get("endereco_cep")]
    return ", ".join(str(x).strip() for x in pedacos if str(x or "").strip())


def salvar_partes(pedido_id: str, partes: list[dict]) -> dict:
    """Guarda o que o cliente informou e devolve o que ainda falta.

    Salva mesmo incompleto, de propósito: quem está no ônibus preenche
    metade e volta depois. O que não acontece é o pedido seguir para a
    redação incompleto, e disso cuida `partes_completas`."""
    db = get_db()
    limpas = []
    for x in partes or []:
        limpas.append({k: (str(v).strip() if isinstance(v, str) else v)
                       for k, v in x.items() if k != "falta"})

    db.table("pedidos_contrato").update({
        "partes": limpas, "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    estado = partes_do_pedido(pedido_id)
    db.table("pedidos_contrato").update({
        "partes_completas": estado["completo"],
    }).eq("id", pedido_id).execute()

    # Salvar parte é uma das formas de atender pendência, e é aqui que
    # o relógio pode voltar a andar.
    try:
        revisar_pendencias(pedido_id)
    except Exception as e:
        print(f"[balcao] pendências não recalculadas: {e}")

    registrar_evento(None, "BALCAO_PARTES_SALVAS",
                     {"pedido_id": pedido_id, "completo": estado["completo"],
                      "faltas": estado["faltas"]})
    return estado


def recado_do_que_falta(estado: dict) -> str:
    """A frase que o atendimento diz quando algo falta.

    Escrita aqui, e não deixada para o modelo, porque é uma lista: o
    modelo resume, esquece um item, e o cliente volta duas vezes."""
    if estado.get("completo"):
        return ""
    partes = []
    for f in estado["faltas"]:
        itens = ", ".join(f["falta"])
        partes.append(f"do {f['papel'].replace('_', ' ')}: {itens}")
    return ("Antes de mandar para a redação, falta "
            + "; ".join(partes)
            + ". Sem isso o contrato até sai, mas fica difícil de executar "
              "se um dia precisar ir para a Justiça.")


# ══════════════════════════════════════════════════════════════════
# A ESTEIRA QUE ANDA SOZINHA, ATÉ ONDE PODE
#
# O pedido parava em cada fase esperando alguém clicar. Num escritório
# de duas pessoas, isso significa que um contrato pago às nove da noite
# fica parado até a manhã seguinte, não porque falte trabalho, mas
# porque falta um clique.
#
# Agora as três primeiras fases andam sozinhas, com janelas:
#
#   REDACAO      a minuta é escrita assim que a coleta fecha, mas o
#                pedido fica visível como "em elaboração" por 4 horas
#   REVISAO_IA   +2 horas
#   AJUSTE       +2 horas
#   REVISAO_ADV  para. Daqui em diante só com o advogado.
#
# POR QUE ESCREVER ANTES E MOSTRAR DEPOIS
#
# Porque o trabalho estar pronto e o rito estar cumprido são coisas
# diferentes. Documento que aparece pronto no minuto seguinte ao
# pagamento não passa confiança, passa impressão de formulário
# automático. E o escritório ganha a janela para agir antes, se quiser,
# com o trabalho adiantado em vez de por fazer.
#
# POR QUE PARA NA REVISÃO DO ADVOGADO
#
# Porque é a única etapa que a máquina não pode cumprir. Tudo antes
# dela é rascunho; o que sai daqui leva a assinatura de alguém inscrito
# na OAB, que responde pelo que assina. Automatizar esse passo seria
# assinar sem ler.
#
# A ação humana sempre atropela o relógio: quem clicar antes, avança
# antes. As janelas são teto, não piso.
# ══════════════════════════════════════════════════════════════════

# ── AS JANELAS DE CADA FASE ────────────────────────────────────
#
# Somam quatro horas e meia da redação até a mesa do advogado, o que
# cabe folgado nas vinte e quatro combinadas e deixa margem para a
# conferência humana, que é a única sem relógio.
#
# Nenhuma delas é piso: o botão de avançar existe em todas, e quem
# clicar passa na frente do relógio. A janela é teto, para o documento
# não parar quando ninguém está olhando, não para segurar quem quer
# andar.
JANELA_REDACAO = 2        # horas em "em elaboração", à vista do cliente
JANELA_REVISAO = 1        # a primeira revisão
JANELA_AJUSTE = 0.5       # aplicar apontamento é trabalho curto

JANELA_REVISAO_2 = 1      # a segunda revisão é confirmação, não releitura

_PROXIMA = {
    "REDACAO": ("REVISAO_IA", JANELA_REDACAO),
    "REVISAO_IA": ("AJUSTE", JANELA_REVISAO),
    # DO AJUSTE DIRETO PARA O ADVOGADO
    #
    # Havia uma segunda conferência automática entre o ajuste e a
    # revisão do advogado. A ideia era boa no papel — texto que acabou
    # de mudar ser lido de novo antes de subir — e na prática atrasava o
    # pedido para repetir o trabalho de quem lê a sério logo depois.
    #
    # Quem confere o contrato é o advogado, e ele lê a íntegra. Uma
    # máquina conferindo antes dele não acrescenta segurança: acrescenta
    # uma hora de espera e mais uma chamada de IA por pedido.
    "AJUSTE": ("REVISAO_ADV", JANELA_AJUSTE),
    # Continua aqui para os pedidos que JÁ estavam nesta fase quando a
    # mudança subiu. Sem esta linha eles ficariam parados para sempre,
    # porque a esteira só toca o que está em `_PROXIMA`.
    "REVISAO_2": ("REVISAO_ADV", JANELA_REVISAO_2),
}

# ── O RELÓGIO DE QUEM PAGOU URGÊNCIA ───────────────────────────
#
# As janelas normais somam oito horas até a conferência final, o que
# cabe folgado nas vinte e quatro combinadas. Quem paga a urgência
# comprou seis horas, e as mesmas oito não cabem mais.
#
# Estas somam uma hora e três quartos, de propósito: quem contrata a
# urgência já com o pedido em andamento há seis horas ou mais recebe
# dentro de uma a duas horas, e é isso que estas janelas garantem sem
# precisar de nenhuma conta de exceção espalhada pelo código.
JANELAS_URGENTE = {"REDACAO": 0.75, "REVISAO_IA": 0.5, "AJUSTE": 0.5,
                   "REVISAO_2": 0.25}


def _janela(fase: str, urgente: bool) -> float:
    if urgente and fase in JANELAS_URGENTE:
        return JANELAS_URGENTE[fase]
    return _PROXIMA[fase][1]


def _horas_desde(iso: str | None) -> float:
    if not iso:
        return 999.0
    from datetime import datetime as _d, timezone as _t
    try:
        t = _d.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return 999.0
    if t.tzinfo is None:
        t = t.replace(tzinfo=_t.utc)
    return (_d.now(_t.utc) - t).total_seconds() / 3600.0


# ── URGÊNCIA PEDIDA NO MEIO DO CAMINHO ─────────────────────────
#
# A urgência era uma escolha da negociação e acabava ali. Só que a
# pressa quase nunca nasce com o pedido: nasce depois, quando a
# assinatura foi antecipada, quando a outra parte marcou a entrega das
# chaves, quando apareceu uma reunião. Quem descobria isso no meio não
# tinha caminho nenhum, e o atendimento improvisava, oferecendo coisa
# que não existia.
#
# O caminho agora tem três passos, e o dinheiro entra no meio deles:
#
#   1. `orcar_urgencia`   diz quanto custa a diferença e devolve o PIX.
#      Quem calcula é o catálogo, nunca o modelo.
#   2. o cliente paga e avisa (`urgencia_paga`), o que não muda prazo
#      nenhum: é só um recado, e vira tarefa de prioridade alta.
#   3. `confirmar_urgencia` é o escritório dizendo que o dinheiro
#      entrou. Só aqui o prazo muda.
#
# Prazo declarado por quem não conferiu o extrato é prazo que o
# escritório assume sem receber.

def _pedido(pedido_id: str) -> dict:
    """O pedido inteiro, ou erro com nome.

    Este módulo buscava o pedido copiando a mesma consulta em cada
    função. Funciona até alguém escrever a décima e esquecer, que foi o
    que aconteceu aqui."""
    r = get_db().table("pedidos_contrato").select("*").eq("id", pedido_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    return r[0]


def orcar_urgencia(pedido_id: str) -> dict:
    """Quanto custa acelerar este pedido, e como pagar."""
    from . import catalogo_contratos as catalogo
    from . import negociador
    p = _pedido(pedido_id)

    if p.get("urgente"):
        return {"ja_e_urgente": True,
                "mensagem": "Este pedido já está com a entrega em até 6 horas."}
    if p.get("fase") in ("APROVACAO", "ASSINATURA", "ENTREGUE", "ARQUIVADO"):
        return {"tarde_demais": True,
                "mensagem": ("O documento já passou da elaboração. Acelerar "
                             "agora não muda a data de entrega.")}

    comum = catalogo.precificar(
        p["tipo"], com_orientacao=bool(p.get("com_orientacao")),
        desconto_pct=float(p.get("desconto_pct") or 0),
        urgente=False,
        assinatura_digital=bool(p.get("assinatura_digital", True)))
    corrido = catalogo.precificar(
        p["tipo"], com_orientacao=bool(p.get("com_orientacao")),
        desconto_pct=float(p.get("desconto_pct") or 0),
        urgente=True,
        assinatura_digital=bool(p.get("assinatura_digital", True)))
    diferenca = round(float(corrido["total"]) - float(comum["total"]), 2)

    get_db().table("pedidos_contrato").update({
        "urgencia_pedida_em": _agora(),
        "urgencia_valor": diferenca,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    registrar_evento(None, "BALCAO_URGENCIA_ORCADA",
                     {"pedido_id": pedido_id, "valor": diferenca})
    return {"valor": diferenca, "total_com_urgencia": corrido["total"],
            "prazo_horas": 6, "pix": negociador.PIX,
            "numero": p.get("numero")}


def urgencia_paga(pedido_id: str, txid: str = "") -> dict:
    """O cliente avisa que pagou. Não muda prazo, chama quem confere."""
    p = _pedido(pedido_id)
    if not p.get("urgencia_pedida_em"):
        raise ValueError("Não há urgência pedida neste pedido.")

    get_db().table("pedidos_contrato").update({
        "urgencia_txid": (txid or "")[:120] or None,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    try:
        from ..core.db import get_db as _db
        from datetime import datetime as _d, timedelta as _td, timezone as _tz
        hoje = (_d.now(_tz.utc) - _td(hours=4)).date().isoformat()
        _db().table("tarefas").insert({
            "titulo": f"Conferir PIX da urgência, pedido {p.get('numero')}",
            "descricao": (f"O cliente informou o pagamento da urgência de "
                          f"R$ {float(p.get('urgencia_valor') or 0):.2f}."
                          + (f" Comprovante/txid: {txid}" if txid else "")
                          + "\n\nConfirmado o recebimento, use o botão de "
                            "confirmar urgência: o prazo passa a 6 horas e a "
                            "esteira acelera sozinha."),
            "origem": "CONTRATO", "pedido_id": pedido_id,
            "data": hoje, "prioridade": "ALTA",
            "motivo": "Urgência paga, prazo muda assim que o PIX for conferido.",
            "criado_por": "ATENDIMENTO",
        }).execute()
    except Exception as e:
        print(f"[balcao] tarefa da urgência não criada: {e}")

    registrar_evento(None, "BALCAO_URGENCIA_PAGA",
                     {"pedido_id": pedido_id, "txid": txid})
    return {"registrado": True,
            "mensagem": ("Recebi o aviso do pagamento. Assim que o escritório "
                         "conferir o PIX, o prazo passa a ser de 6 horas e "
                         "você vê a mudança aqui na tela.")}


def confirmar_urgencia(pedido_id: str, quem: str = "", txid: str = "") -> dict:
    """O escritório conferiu o PIX. Agora sim o relógio muda.

    Duas contas acontecem aqui. A primeira é o preço, que passa a
    incluir o adicional. A segunda é o prazo, e ela tem um caso que
    parece exceção mas não é: quem pede urgência depois de seis horas
    de trabalho não pode receber uma data que já passou. Nesse caso o
    que vale é o tempo que ainda falta, e as janelas de urgência
    entregam isso dentro de uma a duas horas."""
    from . import catalogo_contratos as catalogo
    p = _pedido(pedido_id)
    if p.get("urgencia_confirmada_em"):
        return {"ja_confirmada": True}

    conta = catalogo.precificar(
        p["tipo"], com_orientacao=bool(p.get("com_orientacao")),
        desconto_pct=float(p.get("desconto_pct") or 0),
        urgente=True,
        assinatura_digital=bool(p.get("assinatura_digital", True)))

    campos = {
        "urgente": True,
        "prazo_entrega_horas": 6,
        "valor": conta["total"],
        "urgencia_confirmada_em": _agora(),
        "urgencia_confirmada_por": (quem or "escritório")[:120],
        "atualizado_em": _agora(),
    }
    if txid:
        campos["urgencia_txid"] = txid[:120]

    # O relógio da fase atual é refeito com a janela de urgência. Se a
    # janela nova já venceu, `_mais` de um número negativo devolveria
    # uma hora no passado, e a esteira avançaria na próxima passada,
    # que é exatamente o desejado: sem atalho e sem espera à toa.
    fase = p.get("fase")
    if fase in _PROXIMA and p.get("avanca_em") is not None:
        falta = JANELAS_URGENTE.get(fase, 0.5) - _horas_desde(p.get("fase_em"))
        campos["avanca_em"] = _mais(max(falta, 0.0))

    get_db().table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()

    texto = ("Pagamento da urgência confirmado. O seu documento passou para a "
             "frente da fila e a entrega está prevista para até 6 horas "
             "contadas do pedido. Se já passou desse tempo, a entrega sai "
             "nas próximas 1 a 2 horas.")
    try:
        recado(pedido_id, texto, canais=["PLATAFORMA", "EMAIL", "WHATSAPP"],
               autor="AGENTE", assunto="Urgência confirmada no seu documento")
    except Exception as e:
        print(f"[balcao] aviso da urgência não enviado: {e}")

    # A AGENDA ANDA JUNTO, E ÀS VEZES PARA TRÁS
    #
    # Urgência confirmada encurta a entrega de 24 para 6 horas, e o
    # vencimento pode cair para o dia anterior ao que estava marcado.
    # O compromisso é recalculado da mesma conta, e não corrigido na
    # mão: duas contas do mesmo prazo acabam divergindo.
    try:
        from . import agenda as _ag
        _ag.sincronizar_pedido(pedido_id)
    except Exception as e:
        print(f"[balcao] agenda não acompanhou a urgência: {e}")

    registrar_evento(None, "BALCAO_URGENCIA_CONFIRMADA",
                     {"pedido_id": pedido_id, "quem": quem,
                      "valor": conta["total"]})
    return {"confirmada": True, "valor": conta["total"], "prazo_horas": 6}


def esteira_automatica() -> dict:
    """Roda de tempos em tempos e empurra o que já pode andar.

    Duas responsabilidades, e é importante que sejam as duas: produzir
    o trabalho da fase quando ele ainda não existe, e avançar a fase
    quando a janela vence. Fazer só a segunda deixaria o pedido mudar
    de nome sem mudar de estado, que é pior do que não mudar nada."""
    db = get_db()
    pendentes = db.table("pedidos_contrato") \
        .select("id,numero,fase,fase_em,avanca_em,minuta,revisao,ajustado_em,"
                "redigido_em,revisado_em,pago_em,pendencias,urgente,"
                "revisao,revisao_2") \
        .in_("fase", list(_PROXIMA)) \
        .is_("excluido_em", "null") \
        .limit(100).execute().data or []

    feitos = {"redigidos": 0, "revisados": 0, "ajustados": 0, "avancados": 0}

    # A IA FORA DO AR NÃO VIRA CEM TENTATIVAS POR RODADA
    #
    # Com a conta bloqueada, cada rodada tentava redigir, revisar e
    # ajustar CADA pedido em andamento, e cada tentativa falhava igual.
    # Cem erros no log a cada quinze minutos escondem o erro de verdade
    # quando ele aparecer, e no caso de sobrecarga insistir é exatamente
    # o que faz a sobrecarga durar mais.
    #
    # O AVANÇO DE FASE CONTINUA. Ele não depende da IA: é relógio, e
    # parar o relógio porque a IA caiu puniria o cliente por um problema
    # que é do escritório.
    from ..core import ia as _ia
    fora = _ia.indisponivel()
    if fora:
        feitos["ia_fora"] = fora["motivo"]
        feitos["aviso"] = fora["detalhe"]

    for p in pendentes:
        fase = p["fase"]
        proxima = _PROXIMA[fase][0]
        try:
            # 1. O trabalho daquela fase ainda não foi feito? Faz agora.
            if not fora and fase == "REDACAO" and not (p.get("minuta") or "").strip():
                redigir(p["id"], auto=True)
                feitos["redigidos"] += 1
                continue                       # a janela conta da fase, não daqui
            if not fora and fase == "REVISAO_IA" and not p.get("revisao"):
                revisar(p["id"], auto=True)
                feitos["revisados"] += 1
                continue
            # O PEDIDO QUE CHEGOU AO AJUSTE SEM REVISÃO
            #
            # Não deveria acontecer, e aconteceu: revisão cortada no
            # limite de fichas virava registro vazio e o pedido
            # avançava assim mesmo. A esteira agora repara isso na
            # passagem seguinte, em vez de deixar o pedido parado à
            # espera de alguém notar.
            if not fora and fase == "REVISAO_2" and not p.get("revisao_2"):
                revisar_segunda(p["id"], auto=True)
                feitos["revisados"] += 1
                continue

            if not fora and fase == "AJUSTE" and not p.get("revisao"):
                revisar(p["id"], auto=True)
                feitos["revisados"] += 1
                continue

            if not fora and fase == "AJUSTE" and _horas_desde(p.get("ajustado_em")) > \
                    _horas_desde(p.get("fase_em")):
                # ajustado antes de entrar nesta fase quer dizer que o
                # ajuste desta rodada ainda não aconteceu
                ajustar(p["id"], auto=True)
                feitos["ajustados"] += 1
                continue

            # 2. O relógio está parado esperando o cliente? Não anda.
            #
            # `avanca_em` nulo significa pendência indispensável em
            # aberto. O documento continua sendo escrito, mas a fase
            # não muda: prometer revisão de um texto que ainda vai
            # mudar é prometer duas vezes o mesmo trabalho.
            if p.get("avanca_em") is None:
                continue

            # 3. Chegou a hora? Avança.
            #
            # Menos quando o trabalho da fase não existe. Avançar sem
            # ele leva o pedido para uma fase que depende do que não
            # foi feito, e é assim que nasce pedido travado.
            if fase == "REVISAO_IA" and not p.get("revisao"):
                continue
            if fase == "REDACAO" and not (p.get("minuta") or "").strip():
                continue
            if _horas_desde(p["avanca_em"]) >= 0:
                urgente = bool(p.get("urgente"))
                db.table("pedidos_contrato").update({
                    "fase": proxima, "fase_em": _agora(),
                    # A fase seguinte já nasce com o próprio relógio, e
                    # com a janela do regime dela: quem pagou urgência
                    # anda em minutos, não em horas. REVISAO_ADV não
                    # ganha relógio: é onde a automação termina.
                    "avanca_em": (_mais(_janela(proxima, urgente))
                                  if proxima in _PROXIMA else None),
                    "atualizado_em": _agora(),
                }).eq("id", p["id"]).execute()
                registrar_evento(None, "BALCAO_FASE_AUTOMATICA",
                                 {"pedido_id": p["id"], "de": fase,
                                  "para": proxima, "numero": p.get("numero")})
                feitos["avancados"] += 1

                # O TRABALHO DA FASE NOVA COMEÇA AGORA, NÃO NA PRÓXIMA
                # PASSADA
                #
                # A esteira roda de quinze em quinze minutos. Avançar
                # para a revisão e só revisar no ciclo seguinte jogava
                # fora até quinze minutos por fase, três vezes, o que
                # num pedido com urgência de seis horas é muito. Quem
                # chega na fase já sai trabalhando.
                try:
                    if proxima == "REVISAO_IA":
                        revisar(p["id"], auto=True)
                        feitos["revisados"] += 1
                    elif proxima == "AJUSTE":
                        ajustar(p["id"], auto=True)
                        feitos["ajustados"] += 1
                    elif proxima == "REVISAO_2":
                        revisar_segunda(p["id"], auto=True)
                        feitos["revisados"] += 1
                except Exception as e:
                    print(f"[balcao] fase nova ainda sem trabalho em "
                          f"{p.get('numero')}: {e}")
        except Exception as e:
            # Um pedido com problema não pode parar a fila inteira.
            print(f"[balcao] esteira parou em {p.get('numero')}: {e}")

    return feitos


# ══════════════════════════════════════════════════════════════════
# PENDÊNCIAS: O QUE FALTA, E O QUE ISSO IMPEDE
#
# Antes havia uma resposta só para qualquer falta: recusar a coleta e
# deixar o cliente parado. Mas nem toda falta é igual.
#
#   INDISPENSÁVEL   sem isso o documento não se conclui. Nome e CPF de
#                   quem assina, endereço do imóvel, valor do aluguel.
#                   O trabalho começa, o documento é escrito até onde
#                   dá, e a entrega espera.
#
#   COMPLEMENTAR    melhora o documento e não o impede. Profissão,
#                   telefone, estado civil em contrato que não depende
#                   dele. Pode chegar a qualquer momento antes do fim.
#
# A diferença muda três coisas: o que se diz ao cliente, se o relógio
# anda, e se a peça pode ser entregue.
#
# O RELÓGIO PARADO
#
# Enquanto houver pendência indispensável, `avanca_em` fica nulo e a
# esteira não move o pedido. Não é castigo: contar quatro horas de uma
# espera que é do cliente seria medir o tempo errado e prometer prazo
# que não se cumpre.
#
# Atendida a última, o relógio volta. Se as quatro horas já tinham
# passado enquanto se esperava, o pedido não salta direto para a fase
# seguinte: ganha uma hora, que é o tempo de o redator incorporar o que
# chegou. Avançar no mesmo segundo entregaria um documento sem a
# informação que acabou de chegar.
# ══════════════════════════════════════════════════════════════════

HORA_DE_GRACA = 1        # depois de atendida a pendência atrasada


def _mais(horas: float) -> str:
    from datetime import datetime as _d, timedelta as _td, timezone as _t
    return (_d.now(_t.utc) + _td(hours=horas)).isoformat()


def pendencias_do_pedido(pedido_id: str) -> dict:
    """O que falta, separado entre o que trava e o que não trava."""
    db = get_db()
    r = db.table("pedidos_contrato").select("id,tipo,dados,partes") \
        .eq("id", pedido_id).limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    t = catalogo.detalhe(p["tipo"]) or {}
    dados = _dados.como_dict(p.get("dados"))

    itens: list[dict] = []

    # 1. Os campos do tipo de contrato. O catálogo já diz o que é
    #    obrigatório, e essa marcação foi escrita caso a caso, com o
    #    motivo ao lado. É ela que manda aqui.
    for c in t.get("campos") or []:
        campo = c.get("campo") or ""
        if str(dados.get(campo) or "").strip():
            continue
        # A qualificação das partes é conferida no bloco seguinte, com
        # a estrutura própria. Aqui ficariam duplicadas.
        if any(campo.endswith(suf) for suf in
               ("_nome", "_cpf_cnpj", "_endereco", "_email", "_telefone",
                "_estado_civil", "_profissao", "_nacionalidade")):
            continue
        itens.append({
            "campo": campo, "rotulo": c.get("rotulo") or campo,
            "obrigatorio": bool(c.get("obrigatorio")),
            "porque": c.get("porque"), "origem": "CONTRATO",
        })

    # 2. A qualificação de quem assina.
    estado = partes_do_pedido(pedido_id)
    for f in estado["faltas"]:
        for rotulo in f["falta"]:
            itens.append({
                "campo": f"{f['papel']}_{rotulo}", "rotulo": rotulo,
                "obrigatorio": True, "papel": f["papel"], "origem": "PARTE",
            })

    trava = any(i["obrigatorio"] for i in itens)
    return {"itens": itens, "trava": trava,
            "obrigatorias": [i for i in itens if i["obrigatorio"]],
            "complementares": [i for i in itens if not i["obrigatorio"]]}


def recado_de_pendencia(pend: dict) -> str:
    """O que o atendimento diz ao cliente sobre o que falta.

    Escrito aqui, e não deixado para o modelo, porque é lista com
    consequência: o modelo resume, perde um item, e o cliente volta
    duas vezes. E a frase precisa separar o que segura a entrega do que
    não segura, senão a pessoa trata tudo como urgente ou nada como
    urgente."""
    if not pend["itens"]:
        return ""

    partes = []
    if pend["obrigatorias"]:
        lista = ", ".join(_rotulo(i) for i in pend["obrigatorias"])
        partes.append(
            f"Para concluir o seu documento, o escritório precisa de: {lista}. "
            f"O trabalho já começou e a redação está em andamento, mas a "
            f"entrega só acontece com essa informação em mãos. Assim que você "
            f"enviar, o prazo volta a correr.")
    if pend["complementares"]:
        lista = ", ".join(_rotulo(i) for i in pend["complementares"])
        partes.append(
            f"Há ainda o que ajuda a deixar o documento mais completo: "
            f"{lista}. Isso não segura nada: pode mandar depois, a qualquer "
            f"momento antes de o documento ficar pronto.")
    return "\n\n".join(partes)


# O papel vem do nome do campo no catálogo ("locatario_nome"), e nome de
# campo não leva acento. Mas quem lê isto é o cliente, na conversa: pedir
# "o endereço completo do locatario" é escrever errado na cara dele.
_COMO_SE_ESCREVE = {
    "locatario": "locatário", "comodatario": "comodatário",
    "cessionario": "cessionário", "mutuario": "mutuário",
    "outorgado": "outorgado", "conjuge": "cônjuge",
    "contratada": "contratada", "beneficiario": "beneficiário",
    "procurador": "procurador", "testemunha": "testemunha",
    "destinatario": "destinatário", "proprietario": "proprietário",
    "arrendatario": "arrendatário", "devedor_solidario": "devedor solidário",
}


def _como_se_chama(papel: str) -> str:
    bruto = str(papel or "").strip().lower()
    return _COMO_SE_ESCREVE.get(bruto, bruto.replace("_", " "))


def _rotulo(item: dict) -> str:
    if item.get("papel"):
        return f"{item['rotulo']} do {_como_se_chama(item['papel'])}"
    return item["rotulo"]


def conferencia_do_que_chegou(pedido_id: str, abertura: str = "") -> dict:
    """O recado que o cliente recebe depois de mandar alguma coisa.

    É aqui que se decide o que dizer a quem respondeu PELA METADE, que é
    o caso mais comum e o pior de tratar. Três desfechos, e cada um pede
    uma frase diferente:

    CHEGOU TUDO. Diz que está completo e que segue para a conferência
    final. O cliente precisa ouvir que acabou a parte dele, senão fica
    esperando uma cobrança que não vem e acha que o pedido parou.

    FALTA SÓ O QUE NÃO TRAVA. Agradece, diz o que ainda ajuda e deixa
    claro que o documento NÃO está parado por isso. Cobrar com a mesma
    urgência o que não é indispensável ensina o cliente a ignorar a
    cobrança seguinte, que pode ser a que importa.

    FALTA O INDISPENSÁVEL. Lista item por item, sem resumir, e PERGUNTA
    se ele consegue agora ou prefere mandar depois. A pergunta não é
    gentileza: quem não consegue no momento costuma sumir de vergonha,
    e uma pergunta aberta devolve a conversa. E diz, sem culpar
    ninguém, que o prazo fica parado enquanto faltar, porque o
    escritório não pode escrever o contrato sem aquilo.

    Nunca repete a lista inteira quando só um item ficou faltando: o
    cliente que mandou quatro de cinco coisas e recebe de volta os cinco
    pedidos de novo entende que ninguém olhou o que ele mandou."""
    pend = pendencias_do_pedido(pedido_id)
    faltam = [_rotulo(i) for i in pend["obrigatorias"]]
    extras = [_rotulo(i) for i in pend["complementares"]]
    abertura = (abertura or "").strip()

    if not faltam and not extras:
        texto = ((abertura + " ") if abertura else "") + (
            "Com isso, está completo: tenho tudo o que preciso da sua "
            "parte. Agora o documento segue para a conferência final e eu "
            "te aviso assim que estiver pronto para você ler.")
        return {"texto": texto, "completo": True, "travado": False,
                "faltam": [], "complementares": []}

    if not faltam:
        texto = ((abertura + " ") if abertura else "") + (
            "O essencial já está aqui e o documento não está parado. "
            "Quando puder, me mande ainda: " + "; ".join(extras) + ". "
            "Pode ser depois, sem pressa.")
        return {"texto": texto, "completo": False, "travado": False,
                "faltam": [], "complementares": extras}

    partes = [abertura] if abertura else []
    if len(faltam) == 1:
        partes.append("Para eu conseguir fechar o documento, ainda preciso "
                      "de uma informação: " + faltam[0] + ".")
    else:
        partes.append("Para eu conseguir fechar o documento, ainda faltam "
                      f"{len(faltam)} informações: " + "; ".join(faltam) + ".")
    partes.append("Você consegue me passar isso agora, ou prefere me mandar "
                  "mais tarde? Se precisar procurar em algum lugar, me diga "
                  "e eu aguardo.")
    partes.append("Enquanto faltar, o prazo fica parado, porque o documento "
                  "não pode ser escrito sem essa parte. Assim que chegar, o "
                  "relógio volta a andar do ponto em que parou.")
    if extras:
        partes.append("Se tiver em mãos, aproveite e me mande também: "
                      + "; ".join(extras) + ". Isso não é indispensável.")
    return {"texto": " ".join(partes), "completo": False, "travado": True,
            "faltam": faltam, "complementares": extras}


def _guardar_recado_de_pendencia(pedido_id: str, pend: dict) -> None:
    texto = recado_de_pendencia(pend)
    if not texto:
        return
    get_db().table("pedidos_mensagens").insert({
        "pedido_id": pedido_id, "autor": "AGENTE", "texto": texto,
        "canais": ["PLATAFORMA"],
    }).execute()
    try:
        recado(pedido_id, texto, canais=["EMAIL"], autor="AGENTE",
               assunto="Falta uma informação para concluir o seu documento")
    except Exception as e:
        print(f"[balcao] pendência não enviada por e-mail: {e}")


def revisar_pendencias(pedido_id: str) -> dict:
    """Roda toda vez que o cliente salva algo. Solta o relógio se der.

    É aqui que o relógio volta a andar, e a hora de graça nasce: se as
    quatro horas já passaram enquanto o pedido esperava, avançar no
    mesmo segundo entregaria um documento sem a informação que acabou
    de chegar. A hora é o tempo de incorporá-la.

    O RELÓGIO DA ENTREGA TAMBÉM PARA
    --------------------------------
    São dois relógios diferentes, e os dois tinham de parar. O da fase
    já parava: `avanca_em` nulo segura a esteira. O da ENTREGA não, e
    era o que importava para o cliente: o escritório prometeu 24 horas,
    o cliente demorou oito para mandar o CPF do fiador, e o prazo
    continuava correndo contra quem estava esperando. Quem combinou 24
    horas de trabalho não combinou 16.

    Agora o tempo parado é contado e somado ao vencimento. Esperar o
    cliente não consome o prazo do escritório, e o prazo do escritório
    continua sendo o que foi vendido."""
    db = get_db()
    r = db.table("pedidos_contrato") \
        .select("id,fase,fase_em,avanca_em,pendencias,urgente,"
                "relogio_parado_em,horas_paradas").eq("id", pedido_id) \
        .limit(1).execute().data
    if not r:
        raise ValueError("Pedido não encontrado.")
    p = r[0]
    antes_travava = p.get("avanca_em") is None and p.get("fase") in _PROXIMA

    pend = pendencias_do_pedido(pedido_id)
    campos = {"pendencias": pend["itens"], "atualizado_em": _agora()}

    if p.get("fase") in _PROXIMA:
        if pend["trava"]:
            campos["avanca_em"] = None
            # Marca o início da espera uma vez só. Remarcar a cada
            # salvamento zeraria o tempo parado justamente de quem
            # mandou metade da informação e sumiu.
            if not p.get("relogio_parado_em"):
                campos["relogio_parado_em"] = _agora()
        elif antes_travava:
            janela = _janela(p["fase"], bool(p.get("urgente")))
            ja_passou = _horas_desde(p.get("fase_em")) >= janela
            campos["avanca_em"] = _mais(HORA_DE_GRACA if ja_passou else
                                        janela - _horas_desde(p.get("fase_em")))
            # Fecha a conta da espera e devolve o tempo ao prazo.
            if p.get("relogio_parado_em"):
                parado = _horas_desde(p["relogio_parado_em"])
                campos["horas_paradas"] = round(
                    float(p.get("horas_paradas") or 0) + max(parado, 0), 3)
                campos["relogio_parado_em"] = None

    db.table("pedidos_contrato").update(campos).eq("id", pedido_id).execute()

    # A agenda acompanha: o compromisso de entrega anda para a frente
    # pelo tempo que ficou esperando, e muda de dia quando precisa.
    try:
        from . import agenda as _ag
        _ag.sincronizar_pedido(pedido_id)
    except Exception as e:
        print(f"[balcao] agenda não acompanhou a pendência: {e}")

    if antes_travava and not pend["trava"]:
        registrar_evento(None, "BALCAO_PENDENCIA_ATENDIDA",
                         {"pedido_id": pedido_id})
        try:
            recado(pedido_id,
                   "Recebemos a informação que faltava. O documento está sendo "
                   "complementado e segue para a revisão em cerca de uma hora.",
                   canais=["PLATAFORMA"], autor="AGENTE")
        except Exception as e:
            print(f"[balcao] confirmação não registrada: {e}")

    return {**pend, "recado": recado_de_pendencia(pend),
            "travado": bool(pend["trava"])}


# ══════════════════════════════════════════════════════════════════
# A RÉGUA DE COBRANÇA, E OS TRÊS CANAIS QUE VOLTAM PARA O MESMO LUGAR
#
# Pendência que ninguém cobra é pedido que morre. O cliente mandou o
# que lembrou, ficou faltando um dado, e a vida seguiu: uma semana
# depois ele não lembra mais que havia algo pendente, e o escritório
# tem um pedido pago parado na esteira.
#
# De seis em seis horas, enquanto faltar algo indispensável, sai um
# comunicado com a lista do que falta e a explicação de por que aquilo
# importa. Seis horas é curto o bastante para não deixar o pedido
# esfriar e longo o bastante para não soar cobrança de agiota.
#
# OS TRÊS CANAIS SÃO UMA PORTA SÓ
#
# O comunicado sai pela plataforma, pelo e-mail e pelo WhatsApp, e a
# resposta volta por onde o cliente preferir. Seja qual for o caminho,
# ela cai na conversa do pedido, e o mesmo código trata as três: quem
# responde por e-mail não pode ter um atendimento pior do que quem
# responde pelo chat.
#
# E A RESPOSTA NÃO FICA ESPERANDO ALGUÉM LER
#
# Chegando qualquer coisa do cliente num pedido travado, o redator lê
# o que veio, separa o que corresponde ao que faltava e preenche. O
# relógio volta a andar na mesma hora, com a hora de graça quando as
# quatro já passaram.
# ══════════════════════════════════════════════════════════════════

INTERVALO_COBRANCA = 6        # horas


def _texto_da_cobranca(pedido: dict, pend: dict, vez: int) -> str:
    """O comunicado. Muda de tom conforme a vez, sem perder a educação."""
    itens = "\n".join(f"  • {_rotulo(i)}" for i in pend["obrigatorias"])
    complementares = ""
    if pend["complementares"]:
        complementares = (
            "\n\nAproveitando, isto aqui não segura nada e deixa o documento "
            "mais completo, se você tiver à mão:\n"
            + "\n".join(f"  • {i['rotulo']}" for i in pend["complementares"]))

    abertura = {
        1: "Passando para lembrar de uma informação que ficou faltando.",
        2: "Voltando ao seu pedido: ainda falta uma informação para "
           "concluirmos.",
    }.get(vez, "O seu documento continua parado esperando uma informação.")

    return (
        f"{abertura}\n\n"
        f"Pedido {pedido.get('numero')}.\n\n"
        f"O que falta:\n{itens}{complementares}\n\n"
        f"Por que isso importa: o texto do seu documento já está escrito na "
        f"parte que não depende disso, e a conferência final é a última etapa "
        f"antes de ele ir para a sua aprovação. Sem essa informação, o "
        f"documento não pode ser concluído, e é só isso que está segurando a "
        f"entrega.\n\n"
        f"Como responder: do jeito que for mais fácil para você. Responda "
        f"este e-mail escrevendo a informação, mande pelo chat da sua área na "
        f"plataforma, ou responda no WhatsApp. Chega tudo no mesmo lugar, e "
        f"assim que chegar o prazo volta a correr."
    )


def cobrar_pendencias() -> dict:
    """De seis em seis horas, enquanto faltar o indispensável."""
    db = get_db()
    parados = db.table("pedidos_contrato") \
        .select("id,numero,fase,fase_em,avanca_em,pendencia_cobrada_em,"
                "pendencia_cobrancas,pago_em") \
        .in_("fase", list(_PROXIMA)) \
        .is_("avanca_em", "null") \
        .is_("excluido_em", "null") \
        .limit(100).execute().data or []

    enviados, erros = 0, []
    for p in parados:
        try:
            pend = pendencias_do_pedido(p["id"])
            if not pend["trava"]:
                # O relógio devia estar andando. Conserta em vez de
                # cobrar: cobrar o que já foi enviado é o jeito mais
                # rápido de perder a confiança do cliente.
                revisar_pendencias(p["id"])
                continue

            ultimo = p.get("pendencia_cobrada_em") or p.get("fase_em") or p.get("pago_em")
            if _horas_desde(ultimo) < INTERVALO_COBRANCA:
                continue

            vez = int(p.get("pendencia_cobrancas") or 0) + 1
            recado(p["id"], _texto_da_cobranca(p, pend, vez),
                   canais=["PLATAFORMA", "EMAIL", "WHATSAPP"], autor="AGENTE",
                   assunto=f"Falta uma informação para concluir o seu "
                           f"documento, {p.get('numero')}")
            db.table("pedidos_contrato").update({
                "pendencia_cobrada_em": _agora(),
                "pendencia_cobrancas": vez,
                "atualizado_em": _agora(),
            }).eq("id", p["id"]).execute()
            registrar_evento(None, "BALCAO_PENDENCIA_COBRADA",
                             {"pedido_id": p["id"], "vez": vez,
                              "faltam": len(pend["obrigatorias"])})
            enviados += 1
        except Exception as e:
            erros.append(f"{p.get('numero')}: {e}")

    return {"cobrados": enviados, "erros": erros}


# ── A resposta do cliente, venha de onde vier ───────────────────

SYSTEM_COMPLEMENTO = """Você recebe a resposta de um cliente que estava \
devendo informações para um contrato, e a lista do que faltava. Sua tarefa é \
só uma: dizer quais desses campos a mensagem responde, e com que valor.

REGRAS
- Só preencha campo que a mensagem responde de forma clara. Na dúvida, deixe \
de fora: campo preenchido errado é pior do que campo vazio, porque ninguém \
vai conferir de novo.
- Não invente, não complete, não deduza. Se a pessoa escreveu "moro na Rua \
das Flores", isso é a rua, e não o endereço completo.
- Copie o valor como a pessoa escreveu, corrigindo só maiúsculas óbvias.
- Se a mensagem não responder nada da lista, devolva a lista vazia."""

FERRAMENTA_COMPLEMENTO = [{
    "name": "preencher",
    "description": "Registra os campos que a mensagem do cliente respondeu.",
    "input_schema": {
        "type": "object",
        "properties": {
            "campos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "campo": {"type": "string"},
                        "valor": {"type": "string"},
                    },
                    "required": ["campo", "valor"],
                },
            },
        },
        "required": ["campos"],
    },
}]


# Mensagem com cara de trazer informação. Serve para não gastar uma
# chamada de modelo em "ok", "obrigado" e "bom dia", que é metade do que
# se escreve numa conversa de atendimento.
#
# O critério é generoso de propósito: deixar passar uma mensagem útil
# custa um dado perdido, e deixar passar uma inútil custa centavos.
def _pode_ter_dado(texto: str) -> bool:
    t = (texto or "").strip()
    if len(t) < 12:
        return False
    if any(c.isdigit() for c in t):
        return True          # CPF, data, valor, número, CEP, telefone
    if len(t.split()) >= 6:
        return True          # frase inteira costuma trazer nome ou endereço
    return "@" in t          # e-mail


def varrer_a_conversa(pedido_id: str, limite: int = 60) -> dict:
    """Lê a conversa inteira e preenche o quadro com o que já foi dito.

    O CLIENTE JÁ TINHA MANDADO, E NINGUÉM TINHA OLHADO

    Quem contrata conta tudo na conversa: o nome do outro contratante, o
    endereço do imóvel, o valor combinado, o prazo. Isso acontece
    enquanto ele espera a confirmação do pagamento, antes de a tela de
    coleta existir.

    Até aqui essa informação ficava na conversa e morria lá: a tela de
    coleta abria em branco e perguntava de novo tudo o que ele já tinha
    escrito. É o jeito mais rápido de fazer uma pessoa achar que ninguém
    leu o que ela mandou.

    Esta varredura junta o que ele disse, de todas as mensagens dele, e
    preenche o quadro. O que não foi dito continua em branco, que é a
    única resposta honesta para o que não se sabe.

    POR QUE A CONVERSA INTEIRA, E NÃO MENSAGEM POR MENSAGEM

    Porque o dado quase nunca vem inteiro numa frase só. "O imóvel é na
    rua das Acácias" numa mensagem, "número 120" na seguinte, "Porto
    Velho" três mensagens depois. Lida isolada, cada uma é um pedaço
    inútil; lidas juntas, são um endereço."""
    db = get_db()
    pend = pendencias_do_pedido(pedido_id)
    if not pend["itens"]:
        return {"preenchidos": 0, "nada_a_preencher": True}

    try:
        falas = db.table("pedidos_mensagens") \
            .select("autor,texto,criado_em").eq("pedido_id", pedido_id) \
            .order("criado_em").limit(limite).execute().data or []
    except Exception as e:
        print(f"[balcao] conversa não lida para a varredura: {e}")
        return {"preenchidos": 0, "erro": str(e)}

    # SÓ O QUE O CLIENTE ESCREVEU
    #
    # As falas do agente contêm os mesmos rótulos ("me manda o CPF do
    # fiador") e, lidas junto, fazem o modelo preencher o campo com a
    # pergunta em vez da resposta.
    dele = [f"{(x.get('texto') or '').strip()}" for x in falas
            if str(x.get("autor") or "").upper() == "CLIENTE"
            and (x.get("texto") or "").strip()]
    if not dele:
        return {"preenchidos": 0, "sem_conversa": True}

    junto = "\n".join(dele)[:12000]
    saida = complementar_com_a_resposta(pedido_id, junto)
    registrar_evento(None, "BALCAO_CONVERSA_VARRIDA",
                     {"pedido_id": pedido_id, "mensagens": len(dele),
                      "preenchidos": saida.get("preenchidos", 0)})
    return saida


def complementar_com_a_resposta(pedido_id: str, texto: str) -> dict:
    """Lê o que o cliente mandou e preenche o que dá.

    A leitura é feita por modelo porque a resposta vem em português
    corrido, do jeito que a pessoa fala: "o CPF dele é 123, e ele é
    casado". O que o modelo NÃO faz é decidir se aquilo basta: quem
    decide é `pendencias_do_pedido`, comparando o que ficou preenchido
    com o que o tipo de contrato exige."""
    texto = (texto or "").strip()
    if not texto:
        return {"preenchidos": 0}

    pend = pendencias_do_pedido(pedido_id)
    if not pend["itens"]:
        return {"preenchidos": 0}

    lista = "\n".join(
        f"- {i['campo']}: {_rotulo(i)}"
        + (" (indispensável)" if i["obrigatorio"] else " (complementar)")
        for i in pend["itens"])

    try:
        r = _claude().messages.create(
            model=get_settings().claude_model, max_tokens=1200,
            system=SYSTEM_COMPLEMENTO,
            tools=FERRAMENTA_COMPLEMENTO,
            tool_choice={"type": "tool", "name": "preencher"},
            messages=[{"role": "user", "content":
                       f"CAMPOS QUE FALTAM:\n{lista}\n\n"
                       f"MENSAGEM DO CLIENTE:\n{texto[:4000]}"}],
        )
    except Exception as e:
        print(f"[balcao] leitura da resposta falhou: {e}")
        return {"preenchidos": 0, "erro": str(e)}

    achados = []
    for bloco in r.content:
        if getattr(bloco, "type", "") == "tool_use" and bloco.name == "preencher":
            achados = (bloco.input or {}).get("campos") or []

    if not achados:
        return {"preenchidos": 0}

    db = get_db()
    atual = db.table("pedidos_contrato").select("dados,partes") \
        .eq("id", pedido_id).limit(1).execute().data[0]
    dados = _dados.como_dict(atual.get("dados"))
    partes = list(atual.get("partes") or [])
    por_papel = {p.get("papel"): p for p in partes}

    preenchidos = []
    for a in achados:
        campo = (a.get("campo") or "").strip()
        valor = (a.get("valor") or "").strip()
        if not campo or not valor:
            continue
        item = next((i for i in pend["itens"] if i["campo"] == campo), None)
        if not item:
            continue
        if item.get("origem") == "PARTE":
            papel = item.get("papel")
            alvo = por_papel.setdefault(papel, {"papel": papel})
            # o campo da parte vem como "papel_rótulo"; o que interessa
            # é o rótulo, que é o nome do campo na estrutura da parte
            chave = {"nome completo": "nome", "CPF ou CNPJ": "cpf_cnpj",
                     "endereço completo": "endereco"}.get(item["rotulo"],
                                                          item["rotulo"])
            alvo[chave] = valor
        else:
            dados[campo] = valor
        preenchidos.append(_rotulo(item))

    if not preenchidos:
        return {"preenchidos": 0}

    db.table("pedidos_contrato").update({
        "dados": dados, "partes": list(por_papel.values()) or partes,
        "atualizado_em": _agora(),
    }).eq("id", pedido_id).execute()

    estado = revisar_pendencias(pedido_id)
    registrar_evento(None, "BALCAO_PENDENCIA_COMPLEMENTADA",
                     {"pedido_id": pedido_id, "campos": preenchidos,
                      "ainda_falta": estado.get("travado")})

    # O redator refaz a minuta com o que chegou. Sem isto, o documento
    # seguiria para a conferência final sem a informação que acabou de
    # ser prestada, que é o pior desfecho possível desta espera.
    # CADA FASE REFAZ O SEU PRÓPRIO TRABALHO
    #
    # Isto chamava o redator sempre, e o redator reescreve a minuta do
    # zero. Num pedido que já estava em ajuste, a resposta do cliente
    # apagava as correções da revisão e o documento voltava ao ponto
    # de partida, sem ninguém perceber.
    if not estado.get("travado"):
        fase = (db.table("pedidos_contrato").select("fase")
                .eq("id", pedido_id).limit(1).execute().data or [{}])[0].get("fase")
        trabalho = {"REDACAO": redigir, "REVISAO_IA": revisar,
                    "AJUSTE": ajustar}.get(fase)
        if trabalho:
            try:
                trabalho(pedido_id, auto=True)
            except Exception as e:
                print(f"[balcao] {fase} não refeita agora, fica para a esteira: {e}")

    return {"preenchidos": len(preenchidos), "campos": preenchidos,
            "ainda_falta": estado.get("travado"),
            "pendencias": estado}


# ── OS DOIS CANAIS AO VIVO ANDAM JUNTOS ────────────────────────
#
# Chat e WhatsApp são a mesma conversa vista de dois lugares. O cliente
# começa pelo chat no computador, sai para a rua e continua pelo
# WhatsApp no telefone, e espera encontrar lá o que foi dito aqui. Se
# cada canal guardar só a própria metade, ele lê a resposta pela metade
# e pergunta de novo o que já foi respondido.
#
# Por isso a resposta sai nos dois, sempre, sem depender de por onde a
# pergunta entrou. O custo é uma mensagem a mais; o que se evita é o
# cliente achar que ninguém respondeu.
#
# E-MAIL NÃO ENTRA
#
# E-mail tem outro ritmo: manda-se e espera-se o dia seguinte. Copiar
# cada linha de uma conversa de chat para o e-mail enche a caixa de
# quem está com a tela aberta na frente, e o que era atendimento vira
# spam do próprio escritório. Ele só entra quando a pergunta veio por
# e-mail, que é quando a pessoa está esperando ali.

CANAIS_AO_VIVO = ("PLATAFORMA", "WHATSAPP")


def canais_ao_vivo(pedido_id: str, origem: str = "") -> list[str]:
    """Por onde a resposta sai: os dois canais ao vivo, mais o e-mail
    quando foi por e-mail que a pessoa escreveu.

    O WhatsApp só entra se o cliente tiver número. Mandar para um
    cadastro sem telefone registraria uma falha a cada mensagem, e o
    histórico ficaria cheio de erro que não é erro."""
    canais = ["PLATAFORMA"]
    try:
        r = get_db().table("pedidos_contrato").select("clientes(whatsapp)") \
            .eq("id", pedido_id).limit(1).execute().data
        tem_whats = bool(((r[0] if r else {}).get("clientes") or {}).get("whatsapp"))
    except Exception:
        tem_whats = False
    if tem_whats:
        canais.append("WHATSAPP")
    if (origem or "").upper() == "EMAIL":
        canais.append("EMAIL")
    return canais


# ── QUEM ESTÁ FALANDO COM O CLIENTE AGORA ──────────────────────
#
# Cinco minutos. Curto o bastante para o cliente não ficar esperando
# quando quem assumiu saiu para uma audiência e esqueceu; longo o
# bastante para caber uma resposta pensada, com consulta ao processo no
# meio. Quem continuar atendendo renova o prazo a cada mensagem, sem
# precisar saber que existe prazo.
SILENCIO_DO_AGENTE_MIN = 5


def _humano_no_comando(pedido_id: str) -> bool:
    """Alguém do escritório falou com este cliente nos últimos minutos?"""
    try:
        r = get_db().table("pedidos_contrato").select("humano_em") \
            .eq("id", pedido_id).limit(1).execute().data
    except Exception as e:                     # coluna ainda não migrada
        print(f"[balcao] não consegui ver quem está no comando: {e}")
        return False
    quando = _quando(r[0].get("humano_em")) if r else None
    if not quando:
        return False
    return (_agora_dt() - quando).total_seconds() < SILENCIO_DO_AGENTE_MIN * 60


def quem_atende(pedido_id: str) -> dict:
    """Para a tela: quem está no comando e quanto falta para o agente voltar.

    Devolve sempre, inclusive quando ninguém assumiu, porque é isso que
    a tela precisa saber para mostrar a faixa certa."""
    try:
        r = get_db().table("pedidos_contrato") \
            .select("humano_em,humano_quem,cliente_digitando_em") \
            .eq("id", pedido_id).limit(1).execute().data
    except Exception:
        return {"quem": "AGENTE"}
    if not r:
        return {"quem": "AGENTE"}
    p = r[0]
    agora = _agora_dt()

    humano = _quando(p.get("humano_em"))
    faltam = 0
    if humano:
        passou = (agora - humano).total_seconds()
        faltam = max(0, int(SILENCIO_DO_AGENTE_MIN * 60 - passou))

    digit = _quando(p.get("cliente_digitando_em"))
    # Oito segundos: o sinal é renovado a cada poucos segundos enquanto
    # a pessoa digita, então mais do que isso significa que ela parou.
    digitando = bool(digit and (agora - digit).total_seconds() < 8)

    return {"quem": "HUMANO" if faltam > 0 else "AGENTE",
            "humano_quem": p.get("humano_quem") if faltam > 0 else None,
            "humano_em": p.get("humano_em"),
            "segundos_para_o_agente_voltar": faltam,
            "cliente_digitando": digitando}


def assumir_conversa(pedido_id: str, quem: str = "") -> dict:
    """Carimba que o escritório está no comando. Chamado pelo próprio
    envio da mensagem, e também pelo botão de quem quer calar o agente
    antes de escrever."""
    try:
        get_db().table("pedidos_contrato").update({
            "humano_em": _agora(), "humano_quem": (quem or "escritório")[:120],
        }).eq("id", pedido_id).execute()
    except Exception as e:
        print(f"[balcao] não consegui registrar quem assumiu: {e}")
    return quem_atende(pedido_id)


def devolver_ao_agente(pedido_id: str) -> dict:
    """Devolve a conversa antes dos cinco minutos, para quem terminou e
    não quer deixar o cliente esperando o relógio."""
    try:
        get_db().table("pedidos_contrato").update({"humano_em": None}) \
            .eq("id", pedido_id).execute()
    except Exception as e:
        print(f"[balcao] não consegui devolver ao agente: {e}")
    return quem_atende(pedido_id)


def cliente_digitando(pedido_id: str) -> dict:
    """A tela do cliente avisa que ele está escrevendo."""
    try:
        get_db().table("pedidos_contrato") \
            .update({"cliente_digitando_em": _agora()}) \
            .eq("id", pedido_id).execute()
    except Exception:
        pass
    return {"ok": True}


def resposta_do_cliente(pedido_id: str, texto: str, canal: str = "PLATAFORMA",
                        anexos: list[str] | None = None,
                        responder: bool = True) -> dict:
    """Porta única para o que o cliente responde, venha de onde vier.

    Chat, e-mail e WhatsApp entram por aqui. Ter uma porta só é o que
    garante que a experiência não dependa do canal escolhido, e o que
    evita três implementações que envelhecem em ritmos diferentes."""
    db = get_db()
    if texto.strip():
        db.table("pedidos_mensagens").insert({
            "pedido_id": pedido_id, "autor": "CLIENTE",
            "texto": texto[:4000], "canais": [canal.upper()],
        }).execute()

    registrar_evento(None, "BALCAO_RESPOSTA_CLIENTE",
                     {"pedido_id": pedido_id, "canal": canal.upper(),
                      "anexos": len(anexos or [])})

    r = db.table("pedidos_contrato").select("avanca_em,fase") \
        .eq("id", pedido_id).limit(1).execute().data
    travado = bool(r) and r[0].get("avanca_em") is None \
        and r[0].get("fase") in _PROXIMA

    saida: dict = {"registrado": True, "travado_antes": travado}

    # APROVEITAR O QUE ELE ESCREVEU, EM QUALQUER FASE
    #
    # Isto só rodava quando o pedido estava PARADO esperando informação,
    # nas fases de redação em diante. Mas o cliente conta as coisas
    # bem antes: enquanto espera a confirmação do pagamento, ele escreve
    # o nome do outro contratante, o endereço do imóvel, o valor
    # combinado. Tudo isso ficava na conversa e morria lá, e a tela de
    # coleta abria em branco perguntando de novo o que ele já tinha dito.
    #
    # Agora vale em qualquer fase. A trava passa a ser outra, e melhor:
    # só roda se houver pendência a preencher e se a mensagem tiver cara
    # de trazer dado. Mensagem de "ok, obrigado" não precisa de leitura
    # por modelo, e cobrar uma chamada de IA por "bom dia" é desperdício
    # que o cliente paga em lentidão.
    if _pode_ter_dado(texto) or anexos:
        try:
            saida.update(complementar_com_a_resposta(pedido_id, texto))
        except Exception as e:
            print(f"[balcao] não aproveitei a mensagem agora: {e}")
    if travado and anexos and saida.get("preenchidos", 0) == 0:
        # Anexo também destrava: documento que chega costuma trazer a
        # informação que faltava, mesmo sem uma linha escrita.
        saida["pendencias"] = revisar_pendencias(pedido_id)

    # NINGUÉM FICA SEM RESPOSTA
    #
    # Antes, a mensagem do cliente era só matéria prima: ela preenchia
    # o que faltava e morria ali. Do lado dele, escrever "como está meu
    # contrato" era falar com a parede. Agora o atendimento varre o
    # estado do pedido, responde o que foi perguntado e, se houver
    # urgência, abre um alerta de prioridade para quem cuida do caso.
    #
    # A resposta é gerada depois do preenchimento de propósito: assim
    # ela já conta o que mudou com a mensagem que acabou de chegar.
    # O CLIENTE RESPONDEU AO QUE O ESCRITÓRIO PERGUNTOU
    #
    # Quando há pergunta do advogado em aberto, a mensagem que chega
    # quase sempre é a resposta dela. O especialista trata na hora: lê,
    # aplica no contrato o que decorre dali, fecha a pendência e deixa o
    # recado. Sem isso a resposta ficava parada esperando alguém abrir o
    # documento, e num pedido de seis horas essa espera é metade do
    # prazo.
    #
    # Fica antes da resposta do atendimento de propósito: assim a frase
    # que o cliente recebe já sabe que o ponto foi tratado, em vez de
    # dizer que vai encaminhar algo que já foi feito.
    if texto.strip():
        try:
            from . import mesa_do_advogado
            tratado = mesa_do_advogado.tratar_resposta_do_cliente(
                pedido_id, texto)
            if tratado.get("tratou"):
                saida["duvida_tratada"] = tratado
        except Exception as e:
            print(f"[balcao] resposta do cliente não foi tratada: {e}")

    # SALVO QUANDO TEM GENTE NA CONVERSA
    #
    # Alguém do escritório assumiu há pouco: o agente cala. Os dois
    # escrevendo ao mesmo tempo produzem o pior efeito que um
    # atendimento pode ter — a pessoa explica o caso com cuidado e,
    # logo abaixo, o agente responde outra coisa. O cliente vê dois
    # atendentes que não se falam, e passa a não confiar em nenhum.
    #
    # Quem manda é o carimbo no servidor, e não um botão: quem está com
    # pressa de responder, responde, e não clica em "assumir". O ato de
    # escrever é que assume.
    if responder and texto.strip() and _humano_no_comando(pedido_id):
        saida["com_humano"] = True
        responder = False

    if responder and texto.strip():
        try:
            from . import atendente
            r = atendente.responder("PEDIDO", pedido_id, texto)
            # Volta pelo mesmo canal por onde veio. Responder um chat
            # também por e-mail e WhatsApp é encher a caixa de quem
            # está com a tela aberta na frente.
            recado(pedido_id, r["texto"],
                   canais=canais_ao_vivo(pedido_id, origem=canal),
                   autor="AGENTE", assunto="Sobre o seu pedido")
            saida["resposta"] = r["texto"]
            saida["urgencia_registrada"] = bool(r.get("avisos"))
        except Exception as e:
            print(f"[balcao] atendimento não respondeu agora: {e}")
    return saida


def pedido_por_numero(numero: str) -> dict | None:
    """Acha o pedido pelo protocolo. Usado pela entrada de e-mail."""
    if not numero:
        return None
    r = get_db().table("pedidos_contrato") \
        .select("id,numero,cliente_id,fase,avanca_em") \
        .eq("numero", numero.upper()).limit(1).execute().data
    return r[0] if r else None


# As fases em que o pedido ainda é uma conversa viva. Fora destas, o
# documento já foi entregue ou arquivado, e a mensagem que chega é sobre
# outra coisa.
FASES_EM_CONVERSA = ("QUALIFICACAO", "PROPOSTA", "PAGAMENTO", "COLETA",
                     "CIENCIA", "REDACAO", "REVISAO_IA", "AJUSTE",
                     "CIENCIA_ALTERACAO", "REVISAO_2", "REVISAO_ADV",
                     "APROVACAO", "ASSINATURA")


def pedido_em_conversa_do_cliente(cliente_id: str) -> dict | None:
    """O pedido de contrato sobre o qual este cliente está falando.

    É MAIS LARGO QUE O PEDIDO TRAVADO, E DE PROPÓSITO

    A busca de antes só enxergava pedido PARADO esperando informação.
    Quem estava negociando preço, ou esperando o pagamento, ou lendo a
    minuta, escrevia no WhatsApp e a mensagem ia parar no especialista
    do processo judicial, ou abria um caso novo. O cliente perguntava
    "consigo desconto?" e recebia resposta de outro assunto.

    Agora qualquer pedido em fase de conversa serve, e quem responde é o
    mesmo agente do chat da plataforma: o atendimento e a negociação são
    uma conversa só, vista de dois lugares.

    Havendo mais de um, fica com o mexido por último. Adivinhar errado
    entre dois é pior do que não adivinhar, mas o pedido tocado agora há
    pouco é quase sempre o assunto de quem acabou de escrever."""
    r = get_db().table("pedidos_contrato") \
        .select("id,numero,fase,atualizado_em") \
        .eq("cliente_id", cliente_id) \
        .in_("fase", list(FASES_EM_CONVERSA)) \
        .is_("excluido_em", "null") \
        .order("atualizado_em", desc=True).limit(1).execute().data or []
    return r[0] if r else None


def pedido_travado_do_cliente(cliente_id: str) -> dict | None:
    """O pedido daquele cliente que está esperando informação.

    Serve ao WhatsApp, que chega sem número de protocolo: a mensagem é
    do cliente, e se ele tem exatamente um pedido parado esperando algo,
    é sobre esse que ele está falando. Com mais de um, não se adivinha:
    a conversa vai para o caso, como antes."""
    r = get_db().table("pedidos_contrato").select("id,numero") \
        .eq("cliente_id", cliente_id) \
        .in_("fase", list(_PROXIMA)) \
        .is_("avanca_em", "null") \
        .is_("excluido_em", "null") \
        .limit(2).execute().data or []
    return r[0] if len(r) == 1 else None
