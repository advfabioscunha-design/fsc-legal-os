"""
OS MODELOS DO ESCRITÓRIO, E A RÉGUA QUE ELES CARREGAM.

Até aqui o redator recebia o tipo de contrato, a base legal e os dados
do cliente, e escrevia do zero. O texto saía correto e saía diferente
a cada vez: numeração própria, cláusulas em ordem própria, redação
própria. Dois contratos de locação do mesmo escritório não pareciam do
mesmo escritório, e a revisão gastava o tempo dela conferindo forma em
vez de conferir substância.

Agora existe base. Os modelos ficam em `modelos/`, em arquivo de
texto, versionados junto com o código: quem muda o modelo muda o
contrato de todos os clientes dali para a frente, e o histórico diz
quem mudou, quando e o quê. É o oposto de um arquivo numa pasta
compartilhada, que ninguém sabe qual é a última versão.

O QUE ESTE MÓDULO ENTREGA

  `modelo_do_pedido`  o texto base certo para aquele pedido. A escolha
                      não é só pelo tipo: locação de imóvel pode ser
                      residencial, não residencial ou temporada, e a
                      diferença entre elas muda prazo, renovatória e
                      garantia. Quem decide é o campo `finalidade`.
  `guia`              o guia técnico, que o revisor lê inteiro.
  `PROIBIDAS`         a lista curta do que é nulo por lei. Está em
                      código, e não só no texto do guia, porque é
                      trava, e trava não se deixa para o modelo
                      lembrar.

O QUE ELE NÃO FAZ

Não preenche o modelo. Substituir `{{CAMPO}}` por valor parece a parte
fácil e é a parte perigosa: o dado do cliente quase nunca cabe no
campo do jeito que veio, e a colagem cega produz frase quebrada. Quem
encaixa é o redator, que lê o modelo e os dados juntos.
"""
from __future__ import annotations

import functools
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "modelos" / "locacao"


@functools.lru_cache(maxsize=16)
def _ler(nome: str) -> str:
    caminho = PASTA / f"{nome}.md"
    try:
        return caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def guia() -> str:
    """O guia técnico inteiro, com fundamentos e jurisprudência."""
    return _ler("guia")


# ── A ESCOLHA DO MODELO ────────────────────────────────────────
#
# Três modelos para o que o catálogo chama de um tipo só. A diferença
# entre eles não é de estilo:
#
#   residencial      30 meses, para permitir a retomada sem motivo
#                    (art. 46), e vedação de hospedagem curta
#   não residencial  60 meses, porque é o que abre a renovatória com
#                    3 anos no mesmo ramo (art. 51)
#   temporada        até 90 dias, e exige a autorização do condomínio
#
# Usar o residencial numa locação de loja não é imprecisão de forma: é
# perder a renovatória do cliente.

def _finalidade(dados: dict) -> str:
    texto = " ".join(str(v or "") for v in (dados or {}).values()).lower()
    if any(p in texto for p in ("temporada", "curta estadia", "por dia",
                                "diária", "diarias", "airbnb", "veraneio")):
        return "temporada"
    if any(p in texto for p in ("não residencial", "nao residencial",
                                "comercial", "loja", "sala comercial",
                                "galpão", "galpao", "escritório", "escritorio",
                                "consultório", "consultorio", "empresarial")):
        return "nao_residencial"
    return "residencial"


def modelo_do_pedido(tipo: str, dados: dict | None = None) -> dict:
    """O modelo base daquele pedido, ou nada quando não existe um.

    Devolver vazio é resposta legítima: o catálogo tem mais tipos do
    que o escritório tem modelos, e para esses o redator continua
    escrevendo do zero, como sempre fez. O que não pode é inventar um
    modelo parecido, que é o erro que produz contrato de loja com
    cláusula de moradia."""
    if str(tipo).upper() not in ("LOCACAO_IMOVEL", "LOCACAO_RESIDENCIAL",
                                 "LOCACAO_NAO_RESIDENCIAL", "LOCACAO_TEMPORADA"):
        return {"tem": False}

    escolha = _finalidade(dados or {})
    texto = _ler(escolha)
    if not texto:
        return {"tem": False}
    return {"tem": True, "nome": escolha, "texto": texto, "guia": guia()}


# ── O QUE É NULO, E NÃO É OPINIÃO ──────────────────────────────
#
# Estas oito não são preferência do escritório: são nulidade, ou
# contravenção penal, escritas na lei. O cliente pode pedir qualquer
# uma delas, e pede, porque quase todas parecem razoáveis para quem
# não é do ramo. O que o sistema faz com o pedido dele é outra coisa,
# e está em `contratos_online`: registra, explica e pede o aceite.
#
# A lista mora aqui, em código, para poder ser conferida por função e
# não por leitura. Trava que depende de o modelo ter lido o guia até o
# fim não é trava.
PROIBIDAS = [
    {"o_que": "Duas garantias no mesmo contrato",
     "consequencia": "Nulidade e contravenção penal",
     "fundamento": "Lei 8.245/91, arts. 37, parágrafo único, e 43, II"},
    {"o_que": "Aluguel antecipado havendo garantia, salvo na temporada",
     "consequencia": "Contravenção penal",
     "fundamento": "Lei 8.245/91, arts. 20 e 43, III"},
    {"o_que": "Caução acima de três aluguéis",
     "consequencia": "Nulidade do excesso",
     "fundamento": "Lei 8.245/91, art. 38, § 2º"},
    {"o_que": "Reajuste com periodicidade inferior a um ano",
     "consequencia": "Nulidade",
     "fundamento": "Lei 10.192/2001, art. 2º, § 1º"},
    {"o_que": "Aluguel em moeda estrangeira, câmbio ou salário mínimo",
     "consequencia": "Nulidade",
     "fundamento": "Lei 8.245/91, art. 17"},
    {"o_que": "Taxa de intermediação ou cadastro cobrada do locatário",
     "consequencia": "Devolução do valor",
     "fundamento": "Lei 8.245/91, art. 22, VII"},
    {"o_que": "Renúncia à renovatória ou à purgação da mora",
     "consequencia": "Nulidade",
     "fundamento": "Lei 8.245/91, arts. 45 e 62"},
    {"o_que": "Multa integral sem proporcionalidade ao prazo cumprido",
     "consequencia": "Redução judicial",
     "fundamento": "Lei 8.245/91, art. 4º; Código Civil, art. 413"},
]


def texto_das_proibidas() -> str:
    """A lista em prosa, para entrar no prompt sem virar tabela."""
    return "\n".join(
        f"  · {p['o_que']}: {p['consequencia']} ({p['fundamento']})."
        for p in PROIBIDAS)
