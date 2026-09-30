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
vez, sempre no fim."""
