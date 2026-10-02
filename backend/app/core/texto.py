"""
COMO O ESCRITÓRIO ESCREVE PARA O CLIENTE.

Um texto entrega quem o escreveu antes do conteúdo. Dois hábitos, em
particular, denunciam máquina em três palavras:

  O TRAVESSÃO NO MEIO DA FRASE. "O valor fica em R$ 230 — e esse é o
  preço com desconto." Ninguém digita isso no celular, e quase ninguém
  digita no computador. Gente escreve vírgula, ponto ou dois pontos.

  O ASTERISCO DO NEGRITO. O modelo escreve `**R$ 230,00**` porque foi
  treinado em texto formatado, mas a caixa de conversa não interpreta
  markdown: o cliente lê os asteriscos na tela, do jeito que estão.

Esta função é a última peneira antes de qualquer fala sair para o
cliente. Ela não melhora o texto nem corrige o conteúdo: tira o que
denuncia a origem e devolve a pontuação de quem escreve à mão.

O que ela NÃO toca: hífen dentro de palavra. "Pré-pago", "guarda-chuva"
e "sub-rogação" continuam inteiros, porque ali o hífen é ortografia, e
não pontuação.
"""
from __future__ import annotations

import re

# Travessão e meia risca cercados de espaço, que é o uso como
# pontuação. Vira vírgula, que é o que a pessoa escreveria.
_TRAVESSAO_NO_MEIO = re.compile(r"\s+[—–]\s+")

# O mesmo no começo da linha, onde o travessão é marca de fala ou de
# item de lista. Ali ele simplesmente sai.
_TRAVESSAO_NA_ABERTURA = re.compile(r"(?m)^[ \t]*[—–][ \t]*")

# Hífen usado como travessão: espaço, hífen, espaço. Dentro de palavra
# não casa, e é isso que preserva "pré-pago".
_HIFEN_DE_PONTUACAO = re.compile(r"(?<=[^\s])\s+-\s+(?=[^\s])")

# Item de lista escrito com hífen no começo da linha vira ponto, que é
# o que se usa numa conversa.
_HIFEN_DE_LISTA = re.compile(r"(?m)^[ \t]*-[ \t]+")

# Negrito e itálico de markdown. A caixa de conversa não os interpreta.
_NEGRITO = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALICO = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", re.S)
_TITULO = re.compile(r"(?m)^#{1,6}\s*")


def humanizar(texto: str) -> str:
    """Passa o texto pela peneira antes de ele chegar ao cliente."""
    if not texto:
        return texto
    t = str(texto)
    t = _NEGRITO.sub(r"\1", t)
    t = _ITALICO.sub(r"\1", t)
    t = _TITULO.sub("", t)
    t = _TRAVESSAO_NA_ABERTURA.sub("", t)
    t = _TRAVESSAO_NO_MEIO.sub(", ", t)
    t = _HIFEN_DE_LISTA.sub("", t)
    t = _HIFEN_DE_PONTUACAO.sub(", ", t)
    # A vírgula que sobra encostada em outra pontuação, e o espaço
    # dobrado que a substituição às vezes deixa.
    t = re.sub(r",\s*([,.;:!?])", r"\1", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# A instrução que vai junto no prompt. Peneirar depois conserta o
# texto; dizer antes evita que ele nasça torto, e os dois juntos é o
# que faz a regra valer também quando o modelo inventa formatação nova.
REGRA_DE_ESCRITA = """COMO ESCREVER
Escreva como uma pessoa do escritório escreve numa conversa: direto,
educado, sem formalidade de cartório e sem entusiasmo de vendedor.

NUNCA use travessão nem hífen no lugar de pontuação. Onde você usaria
travessão, use vírgula, ponto ou dois pontos.

NUNCA use asterisco, negrito, itálico, título ou qualquer marcação:
a tela mostra os sinais como texto, e o cliente lê os asteriscos.

Frases curtas. Parágrafos de no máximo três linhas. Uma pergunta por
vez, sempre no fim.

QUEM ESTÁ LENDO

Pode ser alguém de setenta anos lendo no celular, com a letra pequena e
sem óculos por perto. Pode ser alguém que terminou a escola há quarenta
anos, ou que não terminou. Pode ser alguém com pressa, no ônibus, entre
uma coisa e outra.

Escreva para essa pessoa, sempre. Quem lê rápido e tem estudo entende
o texto simples na mesma velocidade; quem não tem, entende só esse.

CURTO, MAS NÃO PELA METADE

Três ou quatro linhas por mensagem, e esse é o alvo de verdade, não um
teto que se estoura sempre. Mensagem comprida em tela de celular não é
lida, é rolada: quem rola decide pelo que viu no começo.

Mas encurtar cortando o que importa é pior do que o texto longo. Prazo,
valor, o que a pessoa precisa fazer e até quando: isso nunca sai. Se
não couber, diga a parte que importa AGORA e ofereça o resto: "te
explico o restante se quiser".

AS PALAVRAS

Troque a palavra difícil pela que a pessoa usa. "Prazo" no lugar de
"interregno". "Vai ser analisado" no lugar de "será submetido a
apreciação". "O juiz decidiu" no lugar de "houve decisão interlocutória".

Precisando usar um termo técnico, explique na mesma frase, sem fazer
rodeio nem dar aula: "a contestação, que é a resposta da outra parte".

Número e data por extenso quando ajudar: "até sexta, dia 10" é mais
claro que "em 10/10". Valor sempre com o real na frente: R$ 230,00.

Frase na ordem direta. "O documento fica pronto amanhã", e não "amanhã
estará concluída a elaboração do documento".

O QUE SOA MAL SEM VOCÊ PERCEBER

"Conforme já informado", "reiteramos", "favor providenciar", "segue
anexo", "prezado(a)", "venho por meio desta". Nada disso é conversa, é
ofício, e põe uma mesa entre você e a pessoa.

"É simples", "é só", "basta", "é fácil": se fosse, ela não teria
perguntado.

E nunca peça desculpa por escrever simples. Explicar com clareza é
respeito, não é tratar ninguém como criança."""


# ══════════════════════════════════════════════════════════════════
# O DOCUMENTO QUE SAI EM WORD E EM PDF
#
# Os modelos do escritório são arquivos markdown, e o redator aprendeu
# a escrever como eles: `## CAPÍTULO I`, `**Cláusula 1ª**`, `---` para
# separar seções. Dentro do prompt isso é ótimo, porque marca a
# hierarquia sem ambiguidade.
#
# No documento entregue é constrangedor. O contrato chegava ao cliente
# com `## CAPÍTULO I — DO OBJETO` e `**Cláusula 2ª — Finalidade.**`
# escritos com os sinais à mostra, como se ninguém tivesse lido antes
# de mandar. Um contrato assim não parece redigido por advogado.
#
# A SAÍDA NÃO É PEDIR AO MODELO QUE PARE
#
# Pedir ajuda e não resolve: o modelo escorrega de volta para o
# markdown porque é assim que ele aprendeu a marcar ênfase, e quando
# escorregar ninguém vai estar olhando. Além disso há contratos já
# gravados com os sinais dentro, e eles precisam sair limpos hoje.
#
# Então a leitura acontece na saída, uma vez só, e serve aos dois
# formatos: o .docx que vira PDF e o .doc que abre no Word. O que era
# marcação vira o que ela significava — negrito é negrito, título é
# título centralizado — e o que não significa nada, como a linha de
# três hífens, simplesmente some.
# ══════════════════════════════════════════════════════════════════

# `## Título` ou `#### Título`. O número de sustenidos é a profundidade.
_TITULO_MD = re.compile(r"^(#{1,6})\s+(.*)$")

# Linha que só separa seções: ---, ***, ___, com três ou mais.
_SEPARADOR_MD = re.compile(r"^\s*([-*_])\1{2,}\s*$")

# Item de lista: -, * ou • no começo.
_ITEM_MD = re.compile(r"^\s*[-*•]\s+(.*)$")

# `**negrito**` e `__negrito__`. Sem ganância, para dois trechos na
# mesma linha não virarem um só.
_NEGRITO_MD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")

# Itálico de um asterisco só. Vira texto normal: itálico em contrato é
# raro e o risco de comer um asterisco legítimo é maior que o ganho.
_ITALICO_MD = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")


def pedacos_com_negrito(linha: str) -> list[tuple[str, bool]]:
    """Quebra a linha em pedaços, dizendo quais são negrito.

    Devolve [(texto, negrito)]. Quem escreve o documento percorre a
    lista e aplica a formatação; quem escreve HTML envolve em <b>."""
    linha = _ITALICO_MD.sub(r"\1", linha)
    saida: list[tuple[str, bool]] = []
    fim = 0
    for m in _NEGRITO_MD.finditer(linha):
        if m.start() > fim:
            saida.append((linha[fim:m.start()], False))
        saida.append((m.group(1) or m.group(2) or "", True))
        fim = m.end()
    if fim < len(linha):
        saida.append((linha[fim:], False))
    # Asterisco solto que sobrou de marcação malformada não vai para o
    # documento: ele não significa nada e denuncia a origem.
    return [(t.replace("**", "").replace("__", ""), b)
            for t, b in saida if t]


def linhas_do_documento(texto: str) -> list[dict]:
    """Lê o texto da minuta e diz o que é cada linha.

    Cada item traz `tipo` (titulo, item, paragrafo ou vazio) e, nos que
    têm texto, os `pedacos` já separados por negrito. A linha separadora
    some aqui mesmo: ela existia para marcar seção no markdown e não tem
    equivalente no documento."""
    linhas: list[dict] = []
    for bruta in (texto or "").split("\n"):
        crua = bruta.rstrip()
        if not crua.strip():
            linhas.append({"tipo": "vazio"})
            continue
        if _SEPARADOR_MD.match(crua):
            continue

        m = _TITULO_MD.match(crua.strip())
        if m:
            linhas.append({"tipo": "titulo", "nivel": len(m.group(1)),
                           "pedacos": pedacos_com_negrito(m.group(2).strip())})
            continue

        m = _ITEM_MD.match(crua)
        if m:
            linhas.append({"tipo": "item",
                           "pedacos": pedacos_com_negrito(m.group(1).strip())})
            continue

        limpo = crua.strip()
        # Linha inteira em negrito é título de cláusula, e era assim que
        # os modelos marcavam antes de os sustenidos existirem.
        so_negrito = bool(_NEGRITO_MD.fullmatch(limpo))
        maiuscula = limpo.isupper() and len(limpo) < 90
        linhas.append({
            "tipo": "titulo" if (so_negrito or maiuscula) else "paragrafo",
            "nivel": 3 if so_negrito else 2,
            "pedacos": pedacos_com_negrito(limpo)})
    return linhas


def documento_em_html(texto: str) -> str:
    """O corpo do documento em HTML, para o arquivo que abre no Word.

    Quem monta é `core/formato`, que é onde está o padrão do escritório:
    quadro resumo em tabela, cláusula com título que não se separa do
    texto, assinatura em bloco. Esta função continua existindo com o
    nome antigo porque as rotas a chamam assim, e porque o fallback
    abaixo é o que mantém o documento saindo se o padrão quebrar."""
    try:
        from . import formato
        return formato.em_html(texto)
    except Exception as e:
        print(f"[formato] caí no formato simples: {e!r}")
    return _html_simples(texto)


def _html_simples(texto: str) -> str:
    """O formato antigo, sem tabela e sem hierarquia. Rede de proteção:
    documento feio sai; documento que não sai deixa o cliente esperando."""
    def escapar(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;"))

    partes: list[str] = []
    for l in linhas_do_documento(texto):
        if l["tipo"] == "vazio":
            partes.append("<p>&nbsp;</p>")
            continue
        corpo = "".join(
            f"<b>{escapar(t)}</b>" if b else escapar(t)
            for t, b in l["pedacos"])
        if l["tipo"] == "titulo":
            # Título já é negrito inteiro: marcar de novo os pedaços que
            # vieram em negrito produziria <b> dentro de <b>, que alguns
            # conversores para PDF tratam como erro.
            puro = escapar("".join(t for t, _ in l["pedacos"]))
            partes.append(
                f'<p style="text-align:center;margin:14pt 0 8pt">'
                f"<b>{puro}</b></p>")
        elif l["tipo"] == "item":
            partes.append(
                f'<p style="margin-left:1.25cm;text-indent:-0.5cm">'
                f"• {corpo}</p>")
        else:
            partes.append(
                f'<p style="text-align:justify;text-indent:1.25cm;'
                f'margin:0 0 6pt">{corpo}</p>')
    return "".join(partes)
