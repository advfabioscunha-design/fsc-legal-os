"""
O que cada contrato exige — por lei, não por costume.

Este é o catálogo que o atendente segue para coletar informação e que o
redator usa para escrever. Cada tipo traz:

  base_legal   a lei que rege o contrato
  campos       o que precisa ser perguntado, com o porquê
  documentos   o que o cliente pode enviar no lugar de digitar
  regras       o que a lei não admite, e como adequar
  alerta       o aviso que precisa ser dado ANTES de cobrar

Sobre o `alerta`: existe porque há contrato que a assinatura eletrônica
não resolve sozinha. Dizer ao cliente que "assinou, está pronto" quando
a lei exige escritura pública é vender um documento que não serve para
o que ele quer. Esse aviso aparece na tela antes do pagamento.
"""
from __future__ import annotations

# Preços (em reais). Documento simples tem preço próprio.
PRECO_PADRAO = 250.00
PRECO_SIMPLES = 99.90
PRECO_ORIENTACAO = 250.00       # atendimento jurídico prévio, opcional


def _pessoa(papel: str) -> list[dict]:
    """Qualificação completa — CC art. 104 e praxe registral. Faltando
    isso, o contrato existe mas dá trabalho para executar."""
    return [
        {"campo": f"{papel}_nome", "rotulo": f"Nome completo do {papel}", "obrigatorio": True},
        {"campo": f"{papel}_cpf_cnpj", "rotulo": f"CPF ou CNPJ do {papel}", "obrigatorio": True},
        {"campo": f"{papel}_rg", "rotulo": f"RG/órgão emissor do {papel}", "obrigatorio": False},
        {"campo": f"{papel}_nacionalidade", "rotulo": "Nacionalidade", "obrigatorio": False},
        {"campo": f"{papel}_estado_civil", "rotulo": "Estado civil", "obrigatorio": True,
         "porque": "regime de bens pode exigir a assinatura do cônjuge"},
        {"campo": f"{papel}_profissao", "rotulo": "Profissão", "obrigatorio": False},
        {"campo": f"{papel}_endereco", "rotulo": f"Endereço completo do {papel}", "obrigatorio": True},
        {"campo": f"{papel}_email", "rotulo": "E-mail", "obrigatorio": True,
         "porque": "é para onde vai o contrato assinado"},
        {"campo": f"{papel}_telefone", "rotulo": "Telefone/WhatsApp", "obrigatorio": False},
    ]


DOCS_PESSOA = [
    "Documento de identidade com foto (RG ou CNH)",
    "CPF, se não constar no documento de identidade",
    "Comprovante de endereço recente",
    "Certidão de casamento, se casado",
    "Contrato social e cartão CNPJ, se pessoa jurídica",
]


CATALOGO: dict[str, dict] = {

    "LOCACAO_IMOVEL": {
        "nome": "Locação de imóvel",
        "base_legal": "Lei 8.245/1991 (Lei do Inquilinato) e Código Civil",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("locador") + _pessoa("locatario") + [
            {"campo": "imovel_endereco", "rotulo": "Endereço completo do imóvel", "obrigatorio": True},
            {"campo": "imovel_matricula", "rotulo": "Matrícula e cartório de registro", "obrigatorio": False},
            {"campo": "finalidade", "rotulo": "Residencial ou não residencial", "obrigatorio": True,
             "porque": "muda o prazo, a renovação e as hipóteses de retomada"},
            {"campo": "prazo_meses", "rotulo": "Prazo da locação, em meses", "obrigatorio": True},
            {"campo": "valor_aluguel", "rotulo": "Valor mensal do aluguel", "obrigatorio": True},
            {"campo": "dia_vencimento", "rotulo": "Dia do vencimento", "obrigatorio": True},
            {"campo": "indice_reajuste", "rotulo": "Índice de reajuste (IGP-M, IPCA…)", "obrigatorio": True},
            {"campo": "garantia", "rotulo": "Garantia: caução, fiador, seguro-fiança ou nenhuma",
             "obrigatorio": True,
             "porque": "a lei admite UMA só; duas invalidam a segunda"},
            {"campo": "encargos", "rotulo": "Quem paga IPTU, condomínio, água, luz", "obrigatorio": True},
            {"campo": "estado_imovel", "rotulo": "Estado do imóvel e benfeitorias existentes", "obrigatorio": False},
        ],
        "documentos": DOCS_PESSOA + [
            "Matrícula atualizada do imóvel ou IPTU",
            "Documento do fiador, se houver",
        ],
        "regras": [
            {"quando": "garantia_multipla",
             "diz": "A Lei do Inquilinato (art. 37, parágrafo único) admite apenas UMA "
                    "garantia por contrato. Exigir caução e fiador juntos torna a segunda "
                    "nula, e o locador fica sem a proteção que pensava ter.",
             "adequar": "Escolher uma: caução (até 3 aluguéis), fiador ou seguro-fiança."},
            {"quando": "caucao_acima_3",
             "diz": "Caução em dinheiro é limitada a 3 meses de aluguel (art. 38, §2º). "
                    "O excedente pode ser cobrado de volta pelo inquilino.",
             "adequar": "Reduzir a caução a até três aluguéis ou trocar a garantia."},
            {"quando": "reajuste_menor_12",
             "diz": "Reajuste de aluguel só pode ser anual (Lei 9.069/1995, art. 28). "
                    "Cláusula de reajuste em prazo menor é nula.",
             "adequar": "Fixar reajuste anual pelo índice escolhido."},
            {"quando": "multa_acima_3",
             "diz": "Multa por rescisão antecipada é proporcional ao tempo restante "
                    "(art. 4º). Multa cheia, independentemente do cumprimento, costuma "
                    "ser reduzida em juízo.",
             "adequar": "Prever multa de até 3 aluguéis, reduzida proporcionalmente."},
        ],
        "alerta": "Contrato de locação NÃO precisa de escritura pública nem de registro "
                  "para valer entre as partes. O registro na matrícula só é necessário "
                  "se você quiser a cláusula de vigência oponível a um futuro comprador "
                  "do imóvel (art. 8º).",
    },

    "LOCACAO_VEICULO": {
        "nome": "Locação de veículo",
        "base_legal": "Código Civil, arts. 565 a 578 (locação de coisas) e CTB",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("locador") + _pessoa("locatario") + [
            {"campo": "veiculo", "rotulo": "Marca, modelo, ano, cor", "obrigatorio": True},
            {"campo": "placa_renavam", "rotulo": "Placa, chassi e RENAVAM", "obrigatorio": True},
            {"campo": "km_atual", "rotulo": "Quilometragem na entrega", "obrigatorio": True},
            {"campo": "prazo", "rotulo": "Prazo da locação", "obrigatorio": True},
            {"campo": "valor", "rotulo": "Valor e forma de pagamento", "obrigatorio": True},
            {"campo": "seguro", "rotulo": "Há seguro? Quem contrata e quem paga a franquia",
             "obrigatorio": True,
             "porque": "sem isso, um sinistro vira discussão sobre quem responde"},
            {"campo": "uso_permitido", "rotulo": "Uso permitido (particular, aplicativo, carga)",
             "obrigatorio": True,
             "porque": "uso remunerado costuma estar fora da cobertura do seguro comum"},
            {"campo": "multas", "rotulo": "Quem responde por multas e infrações", "obrigatorio": True},
        ],
        "documentos": DOCS_PESSOA + ["CRLV do veículo", "Apólice de seguro", "CNH do condutor"],
        "regras": [
            {"quando": "multas_locador",
             "diz": "As infrações são do condutor. O CTB (art. 257, §7º) permite a "
                    "indicação do real infrator, e o contrato deve obrigar o locatário a "
                    "isso — senão os pontos ficam no prontuário do proprietário.",
             "adequar": "Incluir obrigação de indicação do condutor no prazo legal."},
        ],
        "alerta": None,
    },

    "COMODATO": {
        "nome": "Comodato (empréstimo gratuito)",
        "base_legal": "Código Civil, arts. 579 a 585",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("comodante") + _pessoa("comodatario") + [
            {"campo": "bem", "rotulo": "Descrição do bem emprestado", "obrigatorio": True},
            {"campo": "prazo", "rotulo": "Prazo do empréstimo", "obrigatorio": True},
            {"campo": "finalidade", "rotulo": "Para que o bem será usado", "obrigatorio": True},
            {"campo": "despesas", "rotulo": "Quem paga as despesas de uso e conservação",
             "obrigatorio": True},
        ],
        "documentos": DOCS_PESSOA + ["Documento de propriedade do bem"],
        "regras": [
            {"quando": "comodato_com_pagamento",
             "diz": "Comodato é, por definição, GRATUITO (art. 579). Se há pagamento, o "
                    "contrato é locação — e será tratado como locação em juízo, com todas "
                    "as regras da locação.",
             "adequar": "Ou retirar a contraprestação, ou mudar para contrato de locação."},
        ],
        "alerta": None,
    },

    "PRESTACAO_SERVICO": {
        "nome": "Prestação de serviços",
        "base_legal": "Código Civil, arts. 593 a 609; CDC quando o tomador é consumidor",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("contratante") + _pessoa("contratado") + [
            {"campo": "objeto", "rotulo": "O que exatamente será feito", "obrigatorio": True,
             "porque": "objeto vago é a principal causa de briga nesse contrato"},
            {"campo": "prazo_execucao", "rotulo": "Prazo de execução ou cronograma", "obrigatorio": True},
            {"campo": "valor_forma", "rotulo": "Valor, forma e datas de pagamento", "obrigatorio": True},
            {"campo": "categoria_profissional",
             "rotulo": "O serviço é de profissão regulamentada? Qual (engenharia, medicina, "
                       "contabilidade, advocacia, corretagem…)",
             "obrigatorio": True,
             "porque": "cada conselho tem regra própria de contrato, honorário e publicidade"},
            {"campo": "registro_conselho", "rotulo": "Registro no conselho de classe, se houver",
             "obrigatorio": False},
            {"campo": "obrigacao", "rotulo": "É obrigação de meio ou de resultado", "obrigatorio": True},
            {"campo": "subcontratacao", "rotulo": "Pode subcontratar?", "obrigatorio": False},
        ],
        "documentos": DOCS_PESSOA + [
            "Certidão ou carteira do conselho de classe, se profissão regulamentada",
            "Proposta ou orçamento já combinado",
        ],
        "regras": [
            {"quando": "servico_pessoal_continuo",
             "diz": "Serviço prestado por pessoa física, com pessoalidade, habitualidade, "
                    "subordinação e salário é RELAÇÃO DE EMPREGO (CLT, art. 3º), ainda que "
                    "o papel diga 'prestação de serviços'. Contrato assim costuma ser "
                    "desconsiderado na Justiça do Trabalho, com todos os encargos.",
             "adequar": "Ou ajustar a realidade (autonomia, sem exclusividade e sem "
                        "controle de jornada), ou formalizar como contrato de trabalho."},
            {"quando": "conselho_regulamentado",
             "diz": "Profissão regulamentada segue o regramento do seu conselho, que pode "
                    "vedar certas formas de remuneração e de publicidade.",
             "adequar": "Conferir a resolução do conselho antes de fixar o modelo de "
                        "honorários."},
        ],
        "alerta": None,
    },

    "CONTRATO_TRABALHO": {
        "nome": "Contrato de trabalho",
        "base_legal": "CLT e convenção coletiva da categoria",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("empregador") + _pessoa("empregado") + [
            {"campo": "funcao", "rotulo": "Função e descrição das atividades", "obrigatorio": True},
            {"campo": "salario", "rotulo": "Salário e forma de pagamento", "obrigatorio": True},
            {"campo": "jornada", "rotulo": "Jornada e horário", "obrigatorio": True},
            {"campo": "local", "rotulo": "Local de trabalho (presencial, híbrido, teletrabalho)",
             "obrigatorio": True},
            {"campo": "experiencia", "rotulo": "Haverá contrato de experiência? Quantos dias",
             "obrigatorio": True},
            {"campo": "sindicato", "rotulo": "Sindicato/categoria e convenção aplicável",
             "obrigatorio": True,
             "porque": "a convenção pode fixar piso e benefícios acima da lei"},
        ],
        "documentos": DOCS_PESSOA + [
            "CTPS digital ou número do PIS",
            "Exame admissional (ASO)",
            "Convenção coletiva da categoria",
        ],
        "regras": [
            {"quando": "experiencia_acima_90",
             "diz": "Contrato de experiência não passa de 90 dias, somadas as prorrogações, "
                    "e admite uma prorrogação só (CLT, art. 445, parágrafo único, e 451).",
             "adequar": "Ajustar para até 90 dias no total."},
            {"quando": "salario_abaixo_piso",
             "diz": "Salário não pode ficar abaixo do mínimo nacional nem do piso da "
                    "convenção coletiva da categoria.",
             "adequar": "Elevar ao piso aplicável."},
        ],
        "alerta": "O contrato de trabalho deve ser acompanhado do registro na CTPS digital "
                  "e no eSocial. O documento sozinho não substitui o registro.",
    },

    "RESCISAO": {
        "nome": "Rescisão / distrato",
        "base_legal": "Código Civil, art. 472 e seguintes",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("parte1") + _pessoa("parte2") + [
            {"campo": "contrato_origem", "rotulo": "Qual contrato está sendo desfeito, com data",
             "obrigatorio": True},
            {"campo": "motivo", "rotulo": "Motivo da rescisão", "obrigatorio": True},
            {"campo": "acerto", "rotulo": "Valores a pagar ou devolver, e prazos", "obrigatorio": True},
            {"campo": "quitacao", "rotulo": "Haverá quitação recíproca?", "obrigatorio": True,
             "porque": "é o que impede uma cobrança futura sobre o mesmo contrato"},
        ],
        "documentos": DOCS_PESSOA + ["Contrato original que será rescindido",
                                     "Comprovantes de pagamentos já feitos"],
        "regras": [
            {"quando": "forma_do_original",
             "diz": "O distrato se faz pela MESMA forma do contrato original (art. 472). "
                    "Se o contrato foi por escritura pública, o distrato também precisa ser.",
             "adequar": "Conferir a forma do contrato original antes de assinar."},
        ],
        "alerta": None,
    },

    "NOTIFICACAO_EXTRAJUDICIAL": {
        "nome": "Notificação extrajudicial",
        "base_legal": "Código Civil, art. 397, parágrafo único (constituição em mora)",
        "preco": PRECO_SIMPLES,
        "campos": _pessoa("remetente") + [
            {"campo": "destinatario_nome", "rotulo": "Nome de quem será notificado", "obrigatorio": True},
            {"campo": "destinatario_cpf_cnpj", "rotulo": "CPF/CNPJ do destinatário", "obrigatorio": False},
            {"campo": "destinatario_endereco", "rotulo": "Endereço do destinatário", "obrigatorio": True,
             "porque": "a notificação precisa chegar ao destinatário para produzir efeito"},
            {"campo": "fato", "rotulo": "O que aconteceu, com datas", "obrigatorio": True},
            {"campo": "exigencia", "rotulo": "O que está sendo exigido", "obrigatorio": True},
            {"campo": "prazo_dado", "rotulo": "Prazo dado para cumprir", "obrigatorio": True},
            {"campo": "consequencia", "rotulo": "O que acontece se não cumprir", "obrigatorio": True},
        ],
        "documentos": ["Documento de identidade do remetente",
                       "Contrato, nota fiscal ou prova do que se exige",
                       "Comprovantes de cobranças anteriores, se houver"],
        "regras": [
            {"quando": "ameaca_indevida",
             "diz": "Notificação não pode conter ameaça de dano ilícito nem exposição do "
                    "devedor. Cobrança vexatória gera dano moral (CDC, art. 42, e CC 187).",
             "adequar": "Manter o texto firme e factual: o que se exige, o prazo e a "
                        "medida judicial cabível."},
        ],
        "alerta": "Esta é uma notificação por carta/e-mail, feita pelo escritório. Ela "
                  "serve para constituir em mora e provar a cobrança. Se o caso exigir "
                  "notificação com fé pública (despejo, purgação de mora em alienação "
                  "fiduciária), aí sim é preciso o Cartório de Títulos e Documentos.",
    },

    "COMPRA_VENDA_MOVEL": {
        "nome": "Compra e venda de bem móvel",
        "base_legal": "Código Civil, arts. 481 a 532",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("vendedor") + _pessoa("comprador") + [
            {"campo": "bem", "rotulo": "Descrição detalhada do bem", "obrigatorio": True},
            {"campo": "preco", "rotulo": "Preço e forma de pagamento", "obrigatorio": True},
            {"campo": "entrega", "rotulo": "Quando e onde será entregue", "obrigatorio": True},
            {"campo": "estado", "rotulo": "Estado do bem e garantia dada", "obrigatorio": True},
        ],
        "documentos": DOCS_PESSOA + ["Documento de propriedade do bem", "Nota fiscal, se houver"],
        "regras": [],
        "alerta": None,
    },

    "CONFISSAO_DIVIDA": {
        "nome": "Confissão de dívida",
        "base_legal": "Código Civil, art. 389 e seguintes; CPC art. 784, III",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("credor") + _pessoa("devedor") + [
            {"campo": "origem", "rotulo": "De onde vem a dívida", "obrigatorio": True},
            {"campo": "valor", "rotulo": "Valor total confessado", "obrigatorio": True},
            {"campo": "parcelamento", "rotulo": "Parcelas, vencimentos e juros", "obrigatorio": True},
            {"campo": "garantia", "rotulo": "Há garantia? Qual", "obrigatorio": False},
        ],
        "documentos": DOCS_PESSOA + ["Comprovantes da dívida"],
        "regras": [
            {"quando": "sem_testemunhas",
             "diz": "Para valer como título executivo extrajudicial, o documento particular "
                    "precisa ser assinado pelo devedor e por DUAS TESTEMUNHAS (CPC, art. "
                    "784, III). Sem isso, a cobrança vira ação de conhecimento, bem mais "
                    "demorada.",
             "adequar": "Incluir duas testemunhas com nome e CPF, que também assinam."},
            {"quando": "juros_acima_legal",
             "diz": "Entre particulares, os juros de mora seguem o limite legal; juros "
                    "muito acima disso costumam ser reduzidos em juízo.",
             "adequar": "Fixar juros dentro do limite legal e multa de até 2% se for "
                        "relação de consumo."},
        ],
        "alerta": None,
    },

    "COMPRA_VENDA_IMOVEL": {
        "nome": "Compra e venda de imóvel (instrumento particular)",
        "base_legal": "Código Civil, arts. 481 e seguintes e art. 108; Lei 6.015/1973",
        "preco": PRECO_PADRAO,
        "campos": _pessoa("vendedor") + _pessoa("comprador") + [
            {"campo": "imovel_endereco", "rotulo": "Endereço completo do imóvel", "obrigatorio": True},
            {"campo": "imovel_matricula", "rotulo": "Matrícula e cartório", "obrigatorio": True},
            {"campo": "preco", "rotulo": "Preço e forma de pagamento", "obrigatorio": True},
            {"campo": "posse", "rotulo": "Quando a posse é transferida", "obrigatorio": True},
            {"campo": "onus", "rotulo": "Há ônus, financiamento ou penhora sobre o imóvel?",
             "obrigatorio": True},
        ],
        "documentos": DOCS_PESSOA + [
            "Matrícula atualizada do imóvel",
            "Certidões negativas do vendedor e do imóvel",
            "IPTU do ano corrente",
        ],
        "regras": [],
        "alerta": "ATENÇÃO — este é o ponto mais importante deste contrato. A transferência "
                  "da propriedade de imóvel acima de 30 salários mínimos exige ESCRITURA "
                  "PÚBLICA lavrada em cartório de notas (CC, art. 108) e registro na "
                  "matrícula (Lei 6.015/1973). O instrumento particular assinado aqui vale "
                  "como compromisso entre as partes e obriga a fazer a escritura, mas NÃO "
                  "transfere a propriedade e NÃO dispensa o cartório. A assinatura "
                  "eletrônica não muda isso.",
    },
}


def listar() -> list[dict]:
    """Para a tela de escolha do cliente."""
    return [{
        "id": k, "nome": v["nome"], "base_legal": v["base_legal"],
        "preco": v["preco"],
        "campos": len(v["campos"]), "documentos": v["documentos"],
        "alerta": v.get("alerta"),
    } for k, v in CATALOGO.items()]


def detalhe(tipo: str) -> dict | None:
    v = CATALOGO.get(tipo)
    if not v:
        return None
    return {"id": tipo, **v}


def preco(tipo: str, com_orientacao: bool = False) -> float:
    base = (CATALOGO.get(tipo) or {}).get("preco", PRECO_PADRAO)
    return round(base + (PRECO_ORIENTACAO if com_orientacao else 0), 2)
