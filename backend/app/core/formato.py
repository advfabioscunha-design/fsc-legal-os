"""O PADRÃO DE CONTRATO DO ESCRITÓRIO.

A tipografia é a mesma das peças: Calibri Light, corpo 12, espaçamento
1,5, justificado, preto. A estrutura é a do contrato, que é outra coisa:
não tem endereçamento ao juízo nem pedido, e tem quadro resumo,
cláusulas numeradas, anexos de vistoria e campo de assinatura.

O QUE ESTE MÓDULO RESOLVE

Os modelos do escritório são arquivos markdown, e o redator escreve como
eles. Antes daqui, tudo o que ele escrevia virava parágrafo: o quadro
resumo saía como trinta linhas com barra vertical no meio, "1. DO
OBJETO" ficava do mesmo tamanho do texto corrido, e a linha de
assinatura caía sozinha no alto da folha seguinte, separada do nome.
O contrato estava certo e parecia rascunho.

Aqui cada linha é reconhecida pelo que ela é, e recebe a formatação
daquilo: quadro resumo e vistoria viram TABELA de verdade, cláusula vira
título que não se separa do primeiro parágrafo, assinatura vira bloco
que não quebra no meio.

UM RENDERIZADOR SÓ, DOIS FORMATOS

A leitura acontece uma vez, em `ler()`. O .docx e o arquivo que abre no
Word saem do mesmo entendimento, porque o advogado confere num e o
cliente recebe no outro: se divergirem, ele aprova uma página e manda
outra.

O CAMPO QUE NÃO FOI PREENCHIDO SAI EM VERMELHO

Se um `{{CAMPO}}` ou um `[A PREENCHER]` sobreviveu até o documento
final, ele aparece em vermelho e negrito. Não é enfeite: é a última
chance de alguém ver o buraco antes da assinatura. Campo faltando que
sai na cor do texto é campo que vai assinado.
"""
from __future__ import annotations

import re

# ── A régua tipográfica ──────────────────────────────────────────
FONTE = "Calibri Light"
CORPO_PT = 12
TABELA_PT = 9.5
MIUDO_PT = 8
ENTRELINHA = 1.5

RECUO_PARAGRAFO_CM = 1.25     # primeira linha do parágrafo corrido
RECUO_ITEM_CM = 1.25          # corpo do item numerado, número na margem
AREA_UTIL_CM = 16.5           # A4 retrato, com as margens do timbre

# ── O que é cada linha ───────────────────────────────────────────
#
# A ordem destes testes importa: "LOCADOR  |  CPF 000" é linha de
# assinatura e também tem barra vertical, e seria lida como tabela se a
# assinatura não fosse decidida antes.

# Só hífen e asterisco. O sublinhado repetido NÃO é separador aqui: é a
# linha de assinatura do contrato, e tratá-la como régua de markdown
# fazia o campo de assinar desaparecer do documento.
_SEPARADOR = re.compile(r"^\s*([-*])\1{2,}\s*$")
_LINHA_ASSINATURA = re.compile(r"^\s*_{6,}\s*$")
_ANEXO = re.compile(r"^\s*ANEXO\s+([IVXLC]+|\d+)\b", re.IGNORECASE)
_BLOCO_LETRA = re.compile(r"^\s*([A-Z])\.\s+(\S.*)$")
_CLAUSULA = re.compile(r"^\s*(\d{1,2})\.\s+(\S.*)$")
_ITEM_NUMERADO = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+(\S.*)$")
_PARAGRAFO_LEI = re.compile(r"^\s*(Parágrafo único|§\s*\d+º?|Parágrafo \d+º?)"
                            r"\s*[.\-–]?\s*(.*)$")
_MARCADOR = re.compile(r"^\s*[-*•]\s+(.*)$")
_LOCAL_DATA = re.compile(r"^\s*[^|]{2,60},\s*(\{\{DATA|\d{1,2}\s+de\s+\w+|"
                         r"\d{1,2}/\d{1,2}/\d{2,4})", re.IGNORECASE)
_TITULO_MD = re.compile(r"^(#{1,6})\s+(.*)$")

# Pendência: campo de modelo que não foi substituído, ou marcador posto
# de propósito pelo redator.
_PENDENCIA = re.compile(r"(\{\{[^}]*\}\}|\[A PREENCHER[^\]]*\]"
                        r"|\[INSERIR[^\]]*\])")

# Negrito e itálico do markdown.
_NEGRITO = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_ITALICO = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")

# A BARRA QUE SEPARA CÉLULA E A BARRA QUE É TEXTO
#
# Os modelos usam " | " com um espaço de cada lado para separar coluna,
# e "  |  " com dois para separar duas coisas DENTRO da mesma célula:
# "CPF  |  RG | 000  |  111" é uma linha de duas colunas, não de quatro.
# Quem partir na barra crua quebra o quadro resumo todo.
_CELULA = re.compile(r"(?<! ) \| (?! )")


def _maiuscula(t: str) -> bool:
    """Linha escrita em caixa alta, ignorando número e pontuação."""
    letras = [c for c in t if c.isalpha()]
    return bool(letras) and all(c.isupper() for c in letras)


def pedacos(linha: str) -> list[tuple[str, bool, bool]]:
    """Quebra a linha em (texto, negrito, pendência).

    Pendência é campo não preenchido, e sai em vermelho em todo lugar."""
    linha = _ITALICO.sub(r"\1", linha)

    com_negrito: list[tuple[str, bool]] = []
    fim = 0
    for m in _NEGRITO.finditer(linha):
        if m.start() > fim:
            com_negrito.append((linha[fim:m.start()], False))
        com_negrito.append((m.group(1) or m.group(2) or "", True))
        fim = m.end()
    if fim < len(linha):
        com_negrito.append((linha[fim:], False))

    saida: list[tuple[str, bool, bool]] = []
    for texto, negrito in com_negrito:
        texto = texto.replace("**", "").replace("__", "")
        if not texto:
            continue
        for parte in _PENDENCIA.split(texto):
            if not parte:
                continue
            saida.append((parte, negrito, bool(_PENDENCIA.fullmatch(parte))))
    return saida


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in _CELULA.split(linha.strip().strip("|"))]


def _e_cabecalho(primeira: list[str], resto: list[list[str]],
                 colunas: int) -> bool:
    """A primeira linha do bloco é cabeçalho de tabela?

    É, quando ela nomeia as colunas: tem todas as células preenchidas,
    nenhuma com campo de modelo ou linha de preencher à mão, e as linhas
    de baixo têm. "Ambiente | Estado | Descrição | Fotos" seguido de
    "Sala |" é cabeçalho; "Nome completo | {{LOCADOR_NOME}}" não é, é
    par de rótulo e valor.

    Bloco de duas colunas nunca tem cabeçalho: nos modelos do escritório
    ele é sempre rótulo e valor, e "Modalidade | ( ) Caução ( ) Fiança"
    lido como cabeçalho virava uma faixa cinza no meio do quadro."""
    if colunas < 3 or not resto or len(primeira) < colunas:
        return False
    if any(not c for c in primeira):
        return False
    if any(_PENDENCIA.search(c) or "___" in c for c in primeira):
        return False
    # Linha que vem com menos células que o cabeçalho é linha de
    # preencher à mão: "Sala |" tem uma célula só porque as outras três
    # estão em branco no modelo. Olhar o tamanho cru, sem completar as
    # colunas, fazia a vistoria perder a faixa de cabeçalho.
    return any(
        len(linha) < colunas or any(
            (not c) or "___" in c or _PENDENCIA.search(c) for c in linha)
        for linha in resto)


def _larguras(colunas: int) -> list[float]:
    """Centímetros por coluna, somando a área útil da folha.

    Duas colunas é rótulo e valor, e o valor é o que é longo. Quatro é o
    formato das vistorias, onde a descrição carrega o texto e as outras
    são estado, quantidade ou foto."""
    if colunas <= 1:
        return [AREA_UTIL_CM]
    if colunas == 2:
        return [5.5, AREA_UTIL_CM - 5.5]
    if colunas == 4:
        return [3.6, 2.4, 8.1, 2.4]
    larg = AREA_UTIL_CM / colunas
    return [larg] * colunas


def ler(texto: str) -> list[dict]:
    """Lê o documento e devolve os blocos, já com o tipo de cada um.

    Tipos: titulo_documento, secao, anexo, bloco_letra, clausula,
    item_numerado, paragrafo_lei, marcador, tabela, assinatura,
    local_data, corpo."""
    cruas = [l.rstrip() for l in (texto or "").split("\n")]

    # Primeira passada: tipo provisório de cada linha, sem as vazias e
    # sem os separadores, que não têm equivalente no documento.
    linhas: list[dict] = []
    primeiro_titulo_usado = False
    for crua in cruas:
        limpa = crua.strip()
        if not limpa or _SEPARADOR.match(limpa):
            # A LINHA EM BRANCO NÃO VIRA PARÁGRAFO, MAS SEPARA TABELA
            #
            # O ritmo da página vem do espaçamento de cada bloco, não de
            # parágrafos vazios: por isso ela não vira nada no documento.
            # Mas entre duas tabelas ela é a única coisa que diz onde uma
            # acaba e a outra começa. Sem esta marca, a vistoria e o
            # quadro de leituras saíam grudados numa tabela só, com as
            # colunas de uma valendo para a outra.
            if linhas and linhas[-1]["tipo"] != "quebra":
                linhas.append({"tipo": "quebra"})
            continue

        m = _TITULO_MD.match(limpa)
        if m:
            nivel, limpa = len(m.group(1)), m.group(2).strip()
            tipo = "titulo_documento" if (nivel == 1 and
                                          not primeiro_titulo_usado) else "secao"
            primeiro_titulo_usado = True
            linhas.append({"tipo": tipo, "texto": limpa})
            continue

        if _LINHA_ASSINATURA.match(limpa):
            linhas.append({"tipo": "linha_assinatura", "texto": ""})
            continue

        if _ANEXO.match(limpa):
            linhas.append({"tipo": "anexo", "texto": limpa})
            continue

        if _CELULA.search(limpa) or limpa.endswith("|"):
            linhas.append({"tipo": "celulas", "celulas": _celulas(limpa)})
            continue

        m = _PARAGRAFO_LEI.match(limpa)
        if m:
            linhas.append({"tipo": "paragrafo_lei", "rotulo": m.group(1),
                           "texto": m.group(2).strip()})
            continue

        m = _ITEM_NUMERADO.match(limpa)
        if m:
            linhas.append({"tipo": "item_numerado", "numero": m.group(1),
                           "texto": m.group(2).strip()})
            continue

        m = _CLAUSULA.match(limpa)
        if m and _maiuscula(m.group(2)) and len(limpa) < 110:
            linhas.append({"tipo": "clausula", "numero": m.group(1),
                           "texto": m.group(2).strip()})
            continue

        m = _BLOCO_LETRA.match(limpa)
        if m and _maiuscula(m.group(2)) and len(limpa) < 70:
            linhas.append({"tipo": "bloco_letra", "letra": m.group(1),
                           "texto": m.group(2).strip()})
            continue

        m = _MARCADOR.match(limpa)
        if m:
            linhas.append({"tipo": "marcador", "texto": m.group(1).strip()})
            continue

        if _maiuscula(limpa) and len(limpa) < 90:
            tipo = ("titulo_documento" if not primeiro_titulo_usado
                    else "secao")
            primeiro_titulo_usado = True
            linhas.append({"tipo": tipo, "texto": limpa})
            continue

        if _LOCAL_DATA.match(limpa) and len(limpa) < 80:
            linhas.append({"tipo": "local_data", "texto": limpa})
            continue

        linhas.append({"tipo": "corpo", "texto": limpa})

    # Segunda passada: junta o que só faz sentido em conjunto.
    #
    # Célula solta não existe: ou é parte de uma tabela, ou é texto. E
    # assinatura é um bloco de três linhas (risco, nome, papel) que tem
    # de caber inteiro na mesma folha, senão o nome assina a página
    # seguinte sozinho.
    blocos: list[dict] = []
    i = 0
    while i < len(linhas):
        l = linhas[i]

        if l["tipo"] == "quebra":
            i += 1
            continue

        if l["tipo"] == "celulas":
            j = i
            grupo = []
            while j < len(linhas) and linhas[j]["tipo"] == "celulas":
                grupo.append(linhas[j]["celulas"])
                j += 1
            colunas = max(len(g) for g in grupo)
            if colunas < 2 and len(grupo) == 1:
                blocos.append({"tipo": "corpo",
                               "texto": " ".join(grupo[0]).strip()})
            else:
                cabecalho = _e_cabecalho(grupo[0], grupo[1:], colunas)
                corpo = grupo[1:] if cabecalho else grupo
                blocos.append({
                    "tipo": "tabela", "colunas": colunas,
                    "cabecalho": grupo[0] if cabecalho else None,
                    "linhas": [g + [""] * (colunas - len(g)) for g in corpo]})
            i = j
            continue

        if l["tipo"] == "linha_assinatura":
            # Risco, nome e qualificação são um bloco só. O nome vem como
            # linha em caixa alta e a qualificação costuma ter barra
            # ("LOCADOR  |  CPF 000"), que seria lida como tabela se não
            # fosse consumida aqui.
            def _proxima(desde: int) -> int:
                k = desde
                while k < len(linhas) and linhas[k]["tipo"] == "quebra":
                    k += 1
                return k

            nome = papel = ""
            fim = i + 1
            k = _proxima(fim)
            if k < len(linhas) and linhas[k]["tipo"] in (
                    "corpo", "secao", "titulo_documento", "local_data"):
                nome = linhas[k].get("texto", "")
                fim = k + 1
                k = _proxima(fim)
                if k < len(linhas):
                    prox = linhas[k]
                    if prox["tipo"] == "celulas":
                        papel = "  |  ".join(c for c in prox["celulas"] if c)
                    elif prox["tipo"] in ("corpo", "secao", "titulo_documento"):
                        papel = prox.get("texto", "")
                    if papel:
                        fim = k + 1
            blocos.append({"tipo": "assinatura", "nome": nome, "papel": papel})
            i = fim
            continue

        blocos.append(l)
        i += 1

    return blocos


# ── O documento em Word (.docx) ──────────────────────────────────
def _borda(celula, cor="BFBFBF", espessura=6) -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pr = celula._tc.get_or_add_tcPr()
    bordas = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(espessura))
        e.set(qn("w:color"), cor)
        bordas.append(e)
    pr.append(bordas)


def _fundo(celula, cor="F2F2F2") -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pr = celula._tc.get_or_add_tcPr()
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:fill"), cor)
    pr.append(sombra)


def _espacar_letras(run, vinte_avos: int = 20) -> None:
    """Abre o espaço entre as letras, em vigésimos de ponto.

    É o que faz o título do contrato parecer composto e não digitado."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    e = OxmlElement("w:spacing")
    e.set(qn("w:val"), str(vinte_avos))
    run._element.get_or_add_rPr().append(e)


def _numero_de_pagina(rodape) -> None:
    """Põe "fl. X de Y" no rodapé, miúdo e centralizado.

    Num contrato isso não é detalhe de impressão: é o que impede trocar
    uma folha depois de assinado sem ninguém notar."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    par = rodape.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(2)
    par.paragraph_format.space_after = Pt(0)

    def campo(instrucao: str):
        run = par.add_run()
        ini = OxmlElement("w:fldChar")
        ini.set(qn("w:fldCharType"), "begin")
        txt = OxmlElement("w:instrText")
        txt.set(qn("xml:space"), "preserve")
        txt.text = instrucao
        fim = OxmlElement("w:fldChar")
        fim.set(qn("w:fldCharType"), "end")
        run._element.append(ini)
        run._element.append(txt)
        run._element.append(fim)
        run.font.size = Pt(MIUDO_PT)
        run.font.name = FONTE

    r = par.add_run("fl. ")
    r.font.size = Pt(MIUDO_PT)
    r.font.name = FONTE
    campo("PAGE")
    r = par.add_run(" de ")
    r.font.size = Pt(MIUDO_PT)
    r.font.name = FONTE
    campo("NUMPAGES")


def _escrever(par, lista, tamanho=None, negrito_tudo=False) -> None:
    """Põe os pedaços no parágrafo, com o vermelho das pendências."""
    from docx.shared import Pt, RGBColor
    for texto, negrito, pendente in lista:
        run = par.add_run(texto)
        run.font.name = FONTE
        if tamanho:
            run.font.size = Pt(tamanho)
        run.bold = bool(negrito or negrito_tudo or pendente)
        if pendente:
            run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


def preparar(doc) -> None:
    """A régua tipográfica aplicada ao documento inteiro."""
    from docx.shared import Pt
    from docx.oxml.ns import qn

    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = Pt(CORPO_PT)
    # O Word guarda a fonte em três lugares. Sem os outros dois, ele cai
    # no Calibri comum em parte do texto, e o documento sai com dois
    # pesos de letra sem ninguém entender por quê.
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    for atributo in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(atributo), FONTE)

    pf = normal.paragraph_format
    pf.line_spacing = ENTRELINHA
    pf.space_after = Pt(6)
    pf.widow_control = True


def _tabela(doc, bloco) -> None:
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    colunas = bloco["colunas"]
    larguras = _larguras(colunas)
    tem_cabecalho = bool(bloco["cabecalho"])
    total = len(bloco["linhas"]) + (1 if tem_cabecalho else 0)
    if not total:
        return

    tab = doc.add_table(rows=total, cols=colunas)
    try:
        tab.style = "Table Grid"
    except Exception:
        pass
    tab.autofit = False

    def celula(linha_idx, col, texto, negrito=False, cabecalho=False):
        cel = tab.cell(linha_idx, col)
        cel.width = Cm(larguras[col])
        par = cel.paragraphs[0]
        par.paragraph_format.line_spacing = 1
        par.paragraph_format.space_before = Pt(1)
        par.paragraph_format.space_after = Pt(1)
        par.alignment = (WD_ALIGN_PARAGRAPH.CENTER if cabecalho
                         else WD_ALIGN_PARAGRAPH.LEFT)
        _escrever(par, pedacos(texto), tamanho=TABELA_PT,
                  negrito_tudo=negrito)
        _borda(cel)
        if cabecalho:
            _fundo(cel)

    deslocamento = 0
    if tem_cabecalho:
        cab = bloco["cabecalho"] + [""] * (colunas - len(bloco["cabecalho"]))
        for c, texto in enumerate(cab[:colunas]):
            celula(0, c, texto, negrito=True, cabecalho=True)
        deslocamento = 1
        # O cabeçalho repete quando a tabela passa de folha. Tabela longa
        # sem isso vira, na segunda página, um bloco de dados sem nome de
        # coluna nenhum.
        try:
            from docx.oxml.ns import qn
            from docx.oxml import OxmlElement
            pr = tab.rows[0]._tr.get_or_add_trPr()
            rep = OxmlElement("w:tblHeader")
            rep.set(qn("w:val"), "true")
            pr.append(rep)
        except Exception:
            pass

    for i, linha in enumerate(bloco["linhas"]):
        for c in range(colunas):
            # Primeira coluna de tabela de duas é rótulo, e rótulo em
            # negrito é o que faz o quadro resumo ser lido de relance.
            rotulo = colunas == 2 and c == 0
            celula(i + deslocamento, c, linha[c] if c < len(linha) else "",
                   negrito=rotulo)


def no_docx(doc, texto: str) -> None:
    """Escreve o documento inteiro no padrão do escritório."""
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK

    preparar(doc)
    blocos = ler(texto)
    primeiro = True

    for b in blocos:
        tipo = b["tipo"]

        if tipo == "tabela":
            _tabela(doc, b)
            # Respiro depois da tabela, senão o parágrafo seguinte nasce
            # colado na última borda.
            folga = doc.add_paragraph()
            folga.paragraph_format.space_after = Pt(0)
            folga.paragraph_format.line_spacing = 1
            folga.add_run("").font.size = Pt(4)
            continue

        par = doc.add_paragraph()
        pf = par.paragraph_format
        pf.line_spacing = ENTRELINHA
        pf.space_after = Pt(6)

        if tipo == "titulo_documento":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.line_spacing = 1
            pf.space_before = Pt(0 if primeiro else 18)
            pf.space_after = Pt(16)
            pf.keep_with_next = True
            run = par.add_run(b["texto"].upper())
            run.bold = True
            run.font.name = FONTE
            run.font.size = Pt(CORPO_PT + 1)
            _espacar_letras(run, 24)

        elif tipo == "anexo":
            # Anexo começa em folha nova. Vistoria que começa no pé da
            # página anterior é vistoria que ninguém acha depois.
            if not primeiro:
                par.add_run().add_break(WD_BREAK.PAGE)
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.line_spacing = 1
            pf.space_after = Pt(10)
            pf.keep_with_next = True
            run = par.add_run(b["texto"].upper())
            run.bold = True
            run.font.name = FONTE
            run.font.size = Pt(CORPO_PT)
            _espacar_letras(run, 16)

        elif tipo == "secao":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.line_spacing = 1
            pf.space_before = Pt(0 if primeiro else 14)
            pf.space_after = Pt(8)
            pf.keep_with_next = True
            run = par.add_run(b["texto"].upper())
            run.bold = True
            run.font.name = FONTE
            _espacar_letras(run, 12)

        elif tipo == "clausula":
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.line_spacing = 1
            pf.space_before = Pt(14)
            pf.space_after = Pt(6)
            # O título da cláusula não se separa do primeiro parágrafo
            # dela. É o defeito que mais entrega documento montado às
            # pressas: "7. DA RESCISÃO" sozinho no fim da folha.
            pf.keep_with_next = True
            run = par.add_run(f"{b['numero']}. {b['texto'].upper()}")
            run.bold = True
            run.font.name = FONTE

        elif tipo == "bloco_letra":
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.line_spacing = 1
            pf.space_before = Pt(10)
            pf.space_after = Pt(3)
            pf.keep_with_next = True
            run = par.add_run(f"{b['letra']}. {b['texto'].upper()}")
            run.bold = True
            run.font.name = FONTE
            run.font.size = Pt(CORPO_PT - 1.5)

        elif tipo == "item_numerado":
            # Número na margem, texto recuado: os números ficam alinhados
            # numa coluna e dá para percorrer o contrato pelo olho.
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.left_indent = Cm(RECUO_ITEM_CM)
            pf.first_line_indent = Cm(-RECUO_ITEM_CM)
            run = par.add_run(f"{b['numero']}. ")
            run.font.name = FONTE
            _escrever(par, pedacos(b["texto"]))

        elif tipo == "paragrafo_lei":
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.first_line_indent = Cm(RECUO_PARAGRAFO_CM)
            run = par.add_run(f"{b['rotulo']}. ")
            run.bold = True
            run.font.name = FONTE
            _escrever(par, pedacos(b["texto"]))

        elif tipo == "marcador":
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.left_indent = Cm(RECUO_ITEM_CM)
            pf.first_line_indent = Cm(-0.5)
            par.add_run("• ").font.name = FONTE
            _escrever(par, pedacos(b["texto"]))

        elif tipo == "local_data":
            par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            pf.space_before = Pt(20)
            pf.space_after = Pt(10)
            pf.keep_with_next = True
            _escrever(par, pedacos(b["texto"]))

        elif tipo == "assinatura":
            # O BLOCO DE ASSINATURA NÃO QUEBRA
            #
            # Risco, nome e qualificação são uma coisa só. Separados por
            # quebra de página, o cliente recebe uma folha com um risco
            # no pé e outra que abre com o nome dele solto no alto.
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.line_spacing = 1
            pf.space_before = Pt(22)
            pf.space_after = Pt(0)
            pf.keep_with_next = True
            pf.keep_together = True
            par.add_run("_" * 46).font.name = FONTE

            if b.get("nome"):
                p2 = doc.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p2.paragraph_format.line_spacing = 1
                p2.paragraph_format.space_after = Pt(0)
                p2.paragraph_format.keep_with_next = bool(b.get("papel"))
                p2.paragraph_format.keep_together = True
                _escrever(p2, pedacos(b["nome"]), negrito_tudo=True)

            if b.get("papel"):
                p3 = doc.add_paragraph()
                p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p3.paragraph_format.line_spacing = 1
                p3.paragraph_format.space_after = Pt(0)
                p3.paragraph_format.keep_together = True
                _escrever(p3, pedacos(b["papel"]), tamanho=CORPO_PT - 2)

        else:
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.first_line_indent = Cm(RECUO_PARAGRAFO_CM)
            _escrever(par, pedacos(b["texto"]))

        primeiro = False


# ── O mesmo documento em HTML ────────────────────────────────────
#
# Serve ao arquivo que abre no Word e à conferência na tela. Vale o
# cuidado de não divergir do .docx: o advogado aprova o que vê aqui.
def _fuga(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _html_pedacos(lista) -> str:
    saida = []
    for texto, negrito, pendente in lista:
        t = _fuga(texto)
        if pendente:
            saida.append(f'<b style="color:#C00000">{t}</b>')
        elif negrito:
            saida.append(f"<b>{t}</b>")
        else:
            saida.append(t)
    return "".join(saida)


_P_CORPO = ("text-align:justify;text-indent:1.25cm;margin:0 0 6pt;"
            "line-height:1.5")


def em_html(texto: str) -> str:
    """O corpo do documento em HTML, no mesmo padrão do .docx."""
    partes: list[str] = []
    primeiro = True

    for b in ler(texto):
        tipo = b["tipo"]

        if tipo == "tabela":
            colunas = b["colunas"]
            larguras = _larguras(colunas)
            linhas = []
            if b["cabecalho"]:
                cab = b["cabecalho"] + [""] * (colunas - len(b["cabecalho"]))
                linhas.append("<tr>" + "".join(
                    f'<th style="border:1px solid #BFBFBF;background:#F2F2F2;'
                    f'padding:3px 5px;font-size:9.5pt;text-align:center;'
                    f'width:{larguras[i]}cm">{_html_pedacos(pedacos(c))}</th>'
                    for i, c in enumerate(cab[:colunas])) + "</tr>")
            for linha in b["linhas"]:
                celulas = []
                for i in range(colunas):
                    v = linha[i] if i < len(linha) else ""
                    peso = ("font-weight:bold;" if colunas == 2 and i == 0
                            else "")
                    celulas.append(
                        f'<td style="border:1px solid #BFBFBF;padding:3px 5px;'
                        f'font-size:9.5pt;vertical-align:top;{peso}'
                        f'width:{larguras[i]}cm">'
                        f"{_html_pedacos(pedacos(v)) or '&nbsp;'}</td>")
                linhas.append("<tr>" + "".join(celulas) + "</tr>")
            partes.append(
                '<table cellspacing="0" cellpadding="0" style="width:100%;'
                'border-collapse:collapse;margin:4pt 0 10pt">'
                + "".join(linhas) + "</table>")
            primeiro = False
            continue

        if tipo == "titulo_documento":
            partes.append(
                f'<p style="text-align:center;margin:{0 if primeiro else 18}pt'
                f' 0 16pt;font-size:13pt;letter-spacing:1.2px">'
                f'<b>{_fuga(b["texto"].upper())}</b></p>')

        elif tipo == "anexo":
            quebra = "" if primeiro else "page-break-before:always;"
            partes.append(
                f'<p style="{quebra}text-align:center;margin:0 0 10pt;'
                f'letter-spacing:0.8px"><b>{_fuga(b["texto"].upper())}</b></p>')

        elif tipo == "secao":
            partes.append(
                f'<p style="text-align:center;margin:{0 if primeiro else 14}pt'
                f' 0 8pt;letter-spacing:0.6px">'
                f'<b>{_fuga(b["texto"].upper())}</b></p>')

        elif tipo == "clausula":
            partes.append(
                f'<p style="text-align:left;margin:14pt 0 6pt">'
                f'<b>{_fuga(b["numero"])}. {_fuga(b["texto"].upper())}</b></p>')

        elif tipo == "bloco_letra":
            partes.append(
                f'<p style="text-align:left;margin:10pt 0 3pt;font-size:10.5pt">'
                f'<b>{_fuga(b["letra"])}. {_fuga(b["texto"].upper())}</b></p>')

        elif tipo == "item_numerado":
            partes.append(
                f'<p style="text-align:justify;margin:0 0 6pt;line-height:1.5;'
                f'padding-left:1.25cm;text-indent:-1.25cm">'
                f'{_fuga(b["numero"])}. {_html_pedacos(pedacos(b["texto"]))}</p>')

        elif tipo == "paragrafo_lei":
            partes.append(
                f'<p style="{_P_CORPO}"><b>{_fuga(b["rotulo"])}.</b> '
                f'{_html_pedacos(pedacos(b["texto"]))}</p>')

        elif tipo == "marcador":
            partes.append(
                f'<p style="text-align:justify;margin:0 0 6pt;line-height:1.5;'
                f'padding-left:1.25cm;text-indent:-0.5cm">• '
                f'{_html_pedacos(pedacos(b["texto"]))}</p>')

        elif tipo == "local_data":
            partes.append(
                f'<p style="text-align:right;margin:20pt 0 10pt">'
                f'{_html_pedacos(pedacos(b["texto"]))}</p>')

        elif tipo == "assinatura":
            bloco = ['<div style="page-break-inside:avoid;text-align:center;'
                     'margin:22pt 0 0">',
                     '<p style="margin:0">' + "_" * 46 + "</p>"]
            if b.get("nome"):
                bloco.append('<p style="margin:0"><b>'
                             + _html_pedacos(pedacos(b["nome"])) + "</b></p>")
            if b.get("papel"):
                bloco.append('<p style="margin:0;font-size:10pt">'
                             + _html_pedacos(pedacos(b["papel"])) + "</p>")
            bloco.append("</div>")
            partes.append("".join(bloco))

        else:
            partes.append(f'<p style="{_P_CORPO}">'
                          f'{_html_pedacos(pedacos(b["texto"]))}</p>')

        primeiro = False

    return "".join(partes)
