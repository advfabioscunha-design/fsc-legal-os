"""
AGENTE REDATOR DE DOCUMENTOS — FC ADVOCACIA.

Gera contrato de honorários, procuração e declaração de hipossuficiência a
partir dos MODELOS OFICIAIS do escritório (backend/modelos/*.docx).

Princípio: o modelo é lei. O agente **não reescreve o documento** — ele
troca apenas o que varia de um cliente para outro:

  Contrato de honorários
    · qualificação do contratante
    · objeto (item 3) — redigido pela IA a partir do relato do cliente
    · foro (item 10.1) — comarca do domicílio do cliente
    · local e data · nome do cliente com o CPF abaixo

  Procuração
    · qualificação do outorgante
    · tipo de ação (fecho do item III)
    · local e data · nome do cliente como outorgante

  Declaração de hipossuficiência
    · qualificação · local e data · nome e CPF do cliente

Toda a formatação original (fonte, recuos, negrito, alinhamento) é
preservada: o texto é trocado dentro do run existente, nunca recriado.
"""
from __future__ import annotations

import copy
import json
import os
import re
from datetime import date

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

MODELOS_DIR = os.getenv(
    "MODELOS_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "modelos"),
)

ARQUIVOS = {
    "CONTRATO": "contrato_honorarios.docx",
    "PROCURACAO": "procuracao.docx",
    "HIPOSSUFICIENCIA": "declaracao_hipossuficiencia.docx",
}

NOMES = {
    "CONTRATO": "Contrato de Honorários",
    "PROCURACAO": "Procuração ad judicia et extra",
    "HIPOSSUFICIENCIA": "Declaração de Hipossuficiência",
    "OUTRO": "Documento",
}

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


# ══════════════════════════════════════════════════════════════════
#  1. QUALIFICAÇÃO — montada do cadastro, sem IA (zero invenção)
# ══════════════════════════════════════════════════════════════════
CAMPOS_QUALIFICACAO = [
    ("nome", "nome completo"),
    ("cpf_cnpj", "CPF"),
    ("estado_civil", "estado civil"),
    ("profissao", "profissão"),
    ("endereco_rua", "rua"),
    ("endereco_numero", "número"),
    ("endereco_bairro", "bairro"),
    ("endereco_cidade", "cidade"),
    ("endereco_uf", "UF"),
    ("endereco_cep", "CEP"),
]


def campos_faltando(cli: dict) -> list[str]:
    """Rótulos dos dados que ainda faltam para qualificar o cliente."""
    return [rot for campo, rot in CAMPOS_QUALIFICACAO if not (cli.get(campo) or "").strip()]


def _cpf_formatado(v: str | None) -> str:
    n = re.sub(r"\D", "", v or "")
    if len(n) == 11:
        return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"
    if len(n) == 14:
        return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"
    return v or ""


def _cep_formatado(v: str | None) -> str:
    n = re.sub(r"\D", "", v or "")
    return f"{n[:5]}-{n[5:]}" if len(n) == 8 else (v or "")


def montar_qualificacao(cli: dict) -> str:
    """Parágrafo de qualificação civil, no padrão dos modelos do escritório."""
    partes = [
        (cli.get("nome") or "").strip(),
        (cli.get("nacionalidade") or "brasileiro(a)").strip(),
        (cli.get("estado_civil") or "").strip(),
        (cli.get("profissao") or "").strip(),
    ]
    txt = ", ".join(p for p in partes if p)
    if cli.get("rg"):
        txt += f", portador(a) do RG nº {cli['rg']}"
    txt += f", inscrito(a) no CPF sob o nº {_cpf_formatado(cli.get('cpf_cnpj'))}"

    # não repete o tipo de logradouro quando ele já vem no endereço
    rua = (cli.get("endereco_rua") or "").strip()
    tem_logradouro = re.match(
        r"^(rua|av\.?|avenida|travessa|alameda|rodovia|estrada|praça|praca|"
        r"linha|quadra|setor|condom[ií]nio|residencial|viela|largo)\b",
        rua, re.I,
    )
    end = f", residente e domiciliado(a) {'na' if tem_logradouro else 'na Rua'} {rua}"
    if cli.get("endereco_numero"):
        end += f", nº {cli['endereco_numero']}"
    if cli.get("endereco_complemento"):
        end += f", {cli['endereco_complemento']}"
    if cli.get("endereco_bairro"):
        end += f", Bairro {cli['endereco_bairro']}"
    cidade_uf = "/".join(x for x in [cli.get("endereco_cidade"), cli.get("endereco_uf")] if x)
    if cidade_uf:
        end += f", {cidade_uf}"
    if cli.get("endereco_cep"):
        end += f", CEP: {_cep_formatado(cli['endereco_cep'])}"
    txt += end
    if cli.get("email"):
        txt += f", endereço eletrônico: {cli['email']}"
    return txt + "."


def local_e_data(cli: dict, quando: date | None = None) -> str:
    """Local = domicílio do cliente. É a regra do escritório."""
    d = quando or date.today()
    cidade = (cli.get("endereco_cidade") or "").strip()
    uf = (cli.get("endereco_uf") or "").strip()
    local = f"{cidade}/{uf}" if cidade and uf else (cidade or "____")
    return f"{local}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def comarca_do_cliente(cli: dict) -> str:
    cidade = (cli.get("endereco_cidade") or "").strip()
    uf = (cli.get("endereco_uf") or "").strip()
    return f"{cidade}/{uf}" if cidade and uf else (cidade or "____")


# ══════════════════════════════════════════════════════════════════
#  2. IA — só o objeto do contrato e o tipo de ação da procuração
# ══════════════════════════════════════════════════════════════════
SYSTEM_REDATOR = """Você é o redator de documentos do escritório {advogado} ({oab}).

Sua ÚNICA tarefa é redigir o OBJETO de um contrato de honorários e indicar o
TIPO DE AÇÃO, a partir do relato do cliente. Você NÃO escreve o contrato
inteiro — as demais cláusulas são do modelo oficial e não se alteram.

REGRAS:
1. Escreva em português jurídico formal, na terceira pessoa, como um advogado
   sênior redige o objeto contratual.
2. O objeto descreve O QUE SERÁ FEITO: a ação a ser proposta (ou a defesa) e
   os pedidos principais e subsidiários que dela decorrem.
3. Cada item é um pedido concreto e autônomo, com um título curto em negrito
   seguido de dois-pontos e a descrição. Entre 2 e 6 itens.
4. NUNCA prometa resultado. Escreva "requerimento de", "pedido de",
   "propositura de" — jamais "garantia de" ou "obtenção certa".
5. Use apenas fatos que constem do relato. Se algo essencial faltar, escreva
   o item de forma genérica em vez de inventar (ex.: valores, datas, nomes de
   terceiros que não aparecem no relato).
6. O tipo de ação vai em CAIXA ALTA, no formato usado em procurações
   (ex.: "AÇÃO REVISIONAL DE CONTRATO BANCÁRIO C/C REPETIÇÃO DE INDÉBITO").

Responda APENAS com JSON, sem comentários:
{{"introducao": "...", "itens": [{{"titulo": "...", "texto": "..."}}],
  "tipo_acao": "...", "resumo": "..."}}

- introducao: uma frase que abre o item 3.1, no formato
  "Propositura de <ação>, compreendendo a adoção de todas as medidas judiciais
   cabíveis para a resolução integral da lide, com os seguintes objetivos
   principais e subsidiários:"
- resumo: uma linha explicando ao advogado o que você entendeu do caso.
"""


def redigir_objeto(caso: dict, tese: dict | None = None) -> dict:
    """Pede à IA o objeto do contrato e o tipo de ação para este caso."""
    s = get_settings()
    contexto = [
        f"GRUPO/NICHO: {caso.get('grupo') or 'não classificado'}",
        f"NOME DO CASO: {caso.get('titulo') or '—'}",
        f"RELATO DO CLIENTE: {caso.get('relato_inicial') or '—'}",
    ]
    if tese:
        contexto.append(f"TESE APLICÁVEL: {tese.get('titulo')} — {tese.get('ratio_decidendi')}")

    cliente = anthropic.Anthropic(api_key=s.claude_api_key)
    r = cliente.messages.create(
        model=s.claude_model,
        max_tokens=1600,
        system=SYSTEM_REDATOR.format(advogado=s.advogado, oab=s.oab),
        messages=[{"role": "user", "content": "\n\n".join(contexto)}],
    )
    txt = "".join(b.text for b in r.content if b.type == "text").strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-z]*\n|\n```$", "", txt)
    try:
        dados = json.loads(txt)
    except json.JSONDecodeError:
        dados = {
            "introducao": "Propositura da ação cabível, compreendendo todas as "
                          "medidas judiciais necessárias à resolução integral da lide:",
            "itens": [{"titulo": "Objeto", "texto": caso.get("relato_inicial") or "A definir."}],
            "tipo_acao": "AÇÃO CÍVEL",
            "resumo": "Não foi possível estruturar o objeto automaticamente — revise.",
        }
    dados.setdefault("tipo_acao", "AÇÃO CÍVEL")
    dados["tipo_acao"] = str(dados["tipo_acao"]).upper()
    return dados


# ══════════════════════════════════════════════════════════════════
#  3. Motor de substituição no .docx (preserva a formatação)
# ══════════════════════════════════════════════════════════════════
def _trocar_texto(par, novo: str) -> None:
    """Troca o texto do parágrafo mantendo a formatação do primeiro run."""
    if not par.runs:
        par.add_run(novo)
        return
    par.runs[0].text = novo
    for r in par.runs[1:]:
        r.text = ""


def _clonar_apos(par, texto: str, negrito_ate: int = 0):
    """Cria um parágrafo igual ao modelo logo depois dele, com outro texto.
    `negrito_ate` deixa os N primeiros caracteres em negrito (usado nos
    títulos dos itens do objeto)."""
    novo = copy.deepcopy(par._p)
    par._p.addnext(novo)
    from docx.text.paragraph import Paragraph
    p = Paragraph(novo, par._parent)
    for r in list(p.runs)[1:]:
        r._r.getparent().remove(r._r)
    if not p.runs:
        p.add_run("")
    base = p.runs[0]
    if negrito_ate > 0:
        base.text = texto[:negrito_ate]
        base.bold = True
        resto = p.add_run(texto[negrito_ate:])
        resto.bold = False
        resto.font.size = base.font.size
        resto.font.name = base.font.name
    else:
        base.text = texto
        base.bold = False
    return p


def _indice(doc, predicado) -> int:
    for i, p in enumerate(doc.paragraphs):
        if predicado(p.text.strip()):
            return i
    return -1


# ══════════════════════════════════════════════════════════════════
#  4. Geradores por tipo de documento
# ══════════════════════════════════════════════════════════════════
def _abrir(tipo: str):
    from docx import Document
    caminho = os.path.join(MODELOS_DIR, ARQUIVOS[tipo])
    if not os.path.exists(caminho):
        raise RuntimeError(f"Modelo não encontrado no servidor: {caminho}")
    return Document(caminho)


def gerar_hipossuficiencia(cli: dict, dados: dict):
    doc = _abrir("HIPOSSUFICIENCIA")
    ps = doc.paragraphs
    for p in ps:
        t = p.text.strip()
        if t.startswith("Eu, nome"):
            _trocar_texto(p, f"Eu, {dados['qualificacao']}")
        elif t.startswith(", venho respeitosamente"):
            _trocar_texto(p, "Venho respeitosamente à presença de Vossa Excelência, "
                             + t.split("à presença de Vossa Excelência,", 1)[1].strip())
        elif t.startswith("Cidade/Estado,"):
            _trocar_texto(p, dados["local_data"] + ".")
        elif t == "nome":
            _trocar_texto(p, (cli.get("nome") or "").upper())
        elif t.startswith("CPF:"):
            _trocar_texto(p, f"CPF: {_cpf_formatado(cli.get('cpf_cnpj'))}")
    return doc


def gerar_procuracao(cli: dict, dados: dict):
    doc = _abrir("PROCURACAO")
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("I–OUTORGANTE") or t.startswith("I-OUTORGANTE"):
            _trocar_texto(p, f"I–OUTORGANTE: {dados['qualificacao']}")
        elif "AÇÃO CÍVEL" in t and "PODERES" in t.upper()[:40]:
            _trocar_texto(p, t.replace("AÇÃO CÍVEL", dados["tipo_acao"]))
        elif re.match(r"^.+,\s*_+\s*de\s*_+\s*de\s*\d{4}\.?$", t):
            _trocar_texto(p, dados["local_data"] + ".")
        elif set(t) <= set("_ ") and len(t) > 10:
            _trocar_texto(p, (cli.get("nome") or "").upper())
    return doc


def gerar_contrato(cli: dict, dados: dict):
    doc = _abrir("CONTRATO")

    # 1) qualificação do contratante — parágrafo logo após "1. Contratante"
    i = _indice(doc, lambda t: t.startswith("1. Contratante"))
    if i >= 0 and i + 1 < len(doc.paragraphs):
        _trocar_texto(doc.paragraphs[i + 1], dados["qualificacao"])

    # 2) objeto (item 3) — troca o bloco 3.1 + alíneas pelo texto do caso
    ini = _indice(doc, lambda t: t.startswith("3.1."))
    fim = _indice(doc, lambda t: t.startswith("4. Do Pagamento"))
    if ini >= 0 and fim > ini:
        base = doc.paragraphs[ini]
        obj = dados["objeto"]
        _trocar_texto(base, f"3.1. {obj.get('introducao', '')}")
        anterior = base
        letras = "abcdefghij"
        for n, item in enumerate(obj.get("itens", [])):
            titulo = f"{letras[n]}) {item.get('titulo', '').strip()}: "
            anterior = _clonar_apos(anterior, titulo + item.get("texto", "").strip(),
                                    negrito_ate=len(titulo))
        # remove as alíneas antigas do modelo (entre o 3.1 e o item 4)
        for p in list(doc.paragraphs):
            t = p.text.strip()
            if re.match(r"^[a-e]\)\s", t) and t not in [x.text.strip() for x in doc.paragraphs[:1]]:
                # só remove as do modelo original: elas citam união estável/pensão
                if any(k in t for k in ("União Estável", "de cujus", "pensão por morte",
                                        "Nulidade/Anulação de Casamento",
                                        "Restituição de Valores Ingressos",
                                        "Habilitação para Recebimento")):
                    p._p.getparent().remove(p._p)

    # 3) foro — comarca do cliente
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("10.1.") and "foro" in t:
            _trocar_texto(p, re.sub(r"o foro de .+?\.$", f"o foro de {dados['foro']}.", t))
        elif re.match(r"^Palhoça/SC,\s*\d{1,2}\s+de\s+\w+\s+de\s+\d{4}", t):
            _trocar_texto(p, dados["local_data"])
        elif t == "GEOVANA SOUZA SILVA":
            _trocar_texto(p, (cli.get("nome") or "").upper())
        elif t.startswith("CPF nº"):
            _trocar_texto(p, f"CPF nº {_cpf_formatado(cli.get('cpf_cnpj'))}")
    return doc


GERADORES = {
    "CONTRATO": gerar_contrato,
    "PROCURACAO": gerar_procuracao,
    "HIPOSSUFICIENCIA": gerar_hipossuficiencia,
}


# ══════════════════════════════════════════════════════════════════
#  5. Ponto de entrada
# ══════════════════════════════════════════════════════════════════
def gerar(caso_id: str, tipo: str, titulo_livre: str | None = None,
          instrucao: str | None = None) -> dict:
    """Gera o documento, salva o .docx no storage e devolve o registro
    em EM_REVISAO — nada vai para assinatura sem o advogado aprovar."""
    import io, uuid
    s = get_settings()
    db = get_db()
    tipo = (tipo or "").upper()
    if tipo not in GERADORES and tipo != "OUTRO":
        raise ValueError(f"Tipo de documento desconhecido: {tipo}")

    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
    cli = caso.get("clientes") or {}

    faltando = campos_faltando(cli)
    if faltando:
        return {"ok": False, "faltando": faltando,
                "mensagem": "Complete a qualificação do cliente antes de gerar: "
                            + ", ".join(faltando)}

    tese = None
    if caso.get("tese_id"):
        tese = db.table("teses").select("titulo,ratio_decidendi") \
                 .eq("id", caso["tese_id"]).maybe_single().execute().data

    # a IA só entra onde o conteúdo depende do caso
    redacao = {"tipo_acao": "AÇÃO CÍVEL", "objeto": {}, "resumo": ""}
    if tipo in ("CONTRATO", "PROCURACAO", "OUTRO"):
        caso_ia = dict(caso)
        if instrucao:
            caso_ia["relato_inicial"] = f"{caso.get('relato_inicial') or ''}\n\n" \
                                        f"ORIENTAÇÃO DO ADVOGADO: {instrucao}"
        r = redigir_objeto(caso_ia, tese)
        redacao = {"tipo_acao": r.get("tipo_acao", "AÇÃO CÍVEL"),
                   "objeto": {k: r.get(k) for k in ("introducao", "itens")},
                   "resumo": r.get("resumo", "")}

    dados = {
        "qualificacao": montar_qualificacao(cli),
        "local_data": local_e_data(cli),
        "foro": comarca_do_cliente(cli),
        "tipo_acao": redacao["tipo_acao"],
        "objeto": redacao["objeto"],
    }

    if tipo == "OUTRO":
        return {"ok": False,
                "mensagem": "Para 'Outros' o documento é redigido no chat de "
                            "elaboração de contratos e depois anexado ao caso."}

    doc = GERADORES[tipo](cli, dados)
    buf = io.BytesIO()
    doc.save(buf)

    nome_arq = f"{NOMES[tipo].replace(' ', '_')}_{(cli.get('nome') or '').split(' ')[0]}.docx"
    path = f"{caso_id}/gerados/{uuid.uuid4().hex}_{re.sub(r'[^A-Za-z0-9._-]', '_', nome_arq)}"
    db.storage.from_(s.bucket_documentos).upload(
        path, buf.getvalue(),
        {"content-type": "application/vnd.openxmlformats-officedocument."
                         "wordprocessingml.document", "upsert": "true"},
    )

    linha = db.table("documentos_assinatura").insert({
        "caso_id": caso_id, "tipo": tipo,
        "titulo": titulo_livre or f"{NOMES[tipo]} — {cli.get('nome')}",
        "status": "EM_REVISAO",
        "qualificacao": dados["qualificacao"],
        "objeto": dados["objeto"] or None,
        "local_data": dados["local_data"], "foro": dados["foro"],
        "tipo_acao": dados["tipo_acao"], "storage_path": path,
        "gerado_por": "AGENTE",
    }).execute().data[0]

    registrar_evento(caso_id, "DOCUMENTO_GERADO",
                     {"tipo": tipo, "documento_id": linha["id"]})
    return {"ok": True, "documento": linha, "resumo_ia": redacao.get("resumo", "")}


# ══════════════════════════════════════════════════════════════════
#  Conversão para PDF — é assim que o documento chega ao cliente
# ══════════════════════════════════════════════════════════════════
def converter_para_pdf(docx_bytes: bytes) -> bytes:
    """Converte o .docx em PDF com o LibreOffice, preservando a formatação
    do modelo do escritório. Levanta exceção se a conversão falhar — quem
    chama decide se manda o .docx como alternativa."""
    import subprocess, tempfile, os as _os, glob as _glob

    with tempfile.TemporaryDirectory() as tmp:
        entrada = _os.path.join(tmp, "documento.docx")
        with open(entrada, "wb") as f:
            f.write(docx_bytes)
        perfil = _os.path.join(tmp, "perfil")
        try:
            subprocess.run(
                ["soffice", "--headless", "--norestore", "--nolockcheck",
                 f"-env:UserInstallation=file://{perfil}",
                 "--convert-to", "pdf:writer_pdf_Export",
                 "--outdir", tmp, entrada],
                check=True, capture_output=True, timeout=120,
            )
        except FileNotFoundError:
            raise RuntimeError("LibreOffice não está instalado no servidor.")
        except subprocess.TimeoutExpired:
            raise RuntimeError("A conversão para PDF demorou demais.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"LibreOffice falhou: {(e.stderr or b'').decode()[:200]}")

        saidas = _glob.glob(_os.path.join(tmp, "*.pdf"))
        if not saidas:
            raise RuntimeError("O LibreOffice não gerou o PDF.")
        with open(saidas[0], "rb") as f:
            return f.read()


def gerar_pdf_do_documento(documento_id: str) -> dict:
    """Converte o documento gerado em PDF e guarda o caminho no registro.
    Chamado quando o documento é enviado ao cliente para assinatura."""
    from datetime import datetime, timezone as _tz2
    import uuid
    s = get_settings()
    db = get_db()
    d = db.table("documentos_assinatura").select("*").eq("id", documento_id) \
          .single().execute().data

    docx = db.storage.from_(s.bucket_documentos).download(d["storage_path"])
    pdf = converter_para_pdf(docx)

    path = f"{d['caso_id']}/gerados/{uuid.uuid4().hex}_{d['tipo'].lower()}.pdf"
    db.storage.from_(s.bucket_documentos).upload(
        path, pdf, {"content-type": "application/pdf", "upsert": "true"},
    )
    db.table("documentos_assinatura").update({
        "pdf_path": path, "atualizado_em": datetime.now(_tz2.utc).isoformat(),
    }).eq("id", documento_id).execute()
    registrar_evento(d["caso_id"], "DOCUMENTO_CONVERTIDO_PDF",
                     {"documento_id": documento_id})
    return {"ok": True, "pdf_path": path, "tamanho": len(pdf)}


ESTILOS_TITULO = ("Title", "Heading")


def ler_paragrafos(documento_id: str) -> dict:
    """Devolve o documento gerado como uma lista de parágrafos editáveis.
    É o que o advogado vê e ajusta na aba do navegador antes de mandar
    para o cliente assinar."""
    from docx import Document
    import io
    s = get_settings()
    db = get_db()
    d = db.table("documentos_assinatura").select("*").eq("id", documento_id) \
          .single().execute().data
    arq = db.storage.from_(s.bucket_documentos).download(d["storage_path"])
    doc = Document(io.BytesIO(arq))

    paragrafos = []
    for i, p in enumerate(doc.paragraphs):
        alin = str(p.alignment or "").split(" ")[0].lower()
        negrito = bool(p.runs and p.runs[0].bold)
        titulo = p.style.name.startswith(ESTILOS_TITULO) if p.style else False
        paragrafos.append({
            "indice": i, "texto": p.text,
            "alinhamento": ("center" if "center" in alin else
                            "right" if "right" in alin else
                            "justify" if "justify" in alin else "left"),
            "negrito": negrito or titulo,
            "vazio": not p.text.strip(),
        })
    return {"documento": d, "paragrafos": paragrafos}


def gravar_paragrafos(documento_id: str, paragrafos: list[dict]) -> dict:
    """Aplica no .docx o texto ajustado pelo advogado, parágrafo a parágrafo.
    A formatação do modelo é preservada: só o texto do run muda."""
    from docx import Document
    from datetime import datetime, timezone as _tz2
    import io, uuid
    s = get_settings()
    db = get_db()
    d = db.table("documentos_assinatura").select("*").eq("id", documento_id) \
          .single().execute().data
    if d["status"] == "ASSINADO":
        raise RuntimeError("Documento já assinado não pode ser alterado.")

    arq = db.storage.from_(s.bucket_documentos).download(d["storage_path"])
    doc = Document(io.BytesIO(arq))
    por_indice = {int(p["indice"]): (p.get("texto") or "") for p in paragrafos}
    for i, p in enumerate(doc.paragraphs):
        if i in por_indice and por_indice[i] != p.text:
            _trocar_texto(p, por_indice[i])

    buf = io.BytesIO()
    doc.save(buf)
    path = f"{d['caso_id']}/gerados/{uuid.uuid4().hex}_{d['tipo'].lower()}.docx"
    db.storage.from_(s.bucket_documentos).upload(
        path, buf.getvalue(),
        {"content-type": "application/vnd.openxmlformats-officedocument."
                         "wordprocessingml.document", "upsert": "true"},
    )
    # o texto mudou: o PDF anterior não vale mais e será refeito no envio
    atualizado = db.table("documentos_assinatura").update({
        "storage_path": path, "gerado_por": "HUMANO", "pdf_path": None,
        "atualizado_em": datetime.now(_tz2.utc).isoformat(),
    }).eq("id", documento_id).execute().data[0]
    registrar_evento(d["caso_id"], "DOCUMENTO_EDITADO",
                     {"documento_id": documento_id})
    return {"ok": True, "documento": atualizado}


def regravar(documento_id: str, alteracoes: dict) -> dict:
    """O advogado ajustou a qualificação, o objeto, o foro ou a data:
    o .docx é refeito a partir do modelo com os dados corrigidos.
    Só funciona enquanto o documento está EM_REVISAO ou APROVADO."""
    import io, uuid
    from datetime import datetime, timezone as _tz2
    s = get_settings()
    db = get_db()

    d = db.table("documentos_assinatura").select("*").eq("id", documento_id) \
          .single().execute().data
    if d["status"] in ("ENVIADO", "ASSINADO"):
        raise RuntimeError("Este documento já foi enviado para assinatura — "
                           "cancele e gere outro para alterar o conteúdo.")
    caso = db.table("casos").select("clientes(*)").eq("id", d["caso_id"]) \
             .single().execute().data
    cli = caso.get("clientes") or {}

    campos = {k: v for k, v in alteracoes.items()
              if k in ("qualificacao", "objeto", "local_data", "foro",
                       "tipo_acao", "titulo", "observacoes") and v is not None}
    novo = {**d, **campos}

    dados = {
        "qualificacao": novo.get("qualificacao") or montar_qualificacao(cli),
        "local_data": novo.get("local_data") or local_e_data(cli),
        "foro": novo.get("foro") or comarca_do_cliente(cli),
        "tipo_acao": novo.get("tipo_acao") or "AÇÃO CÍVEL",
        "objeto": novo.get("objeto") or {},
    }
    doc = GERADORES[d["tipo"]](cli, dados)
    buf = io.BytesIO()
    doc.save(buf)

    path = f"{d['caso_id']}/gerados/{uuid.uuid4().hex}_{d['tipo'].lower()}.docx"
    db.storage.from_(s.bucket_documentos).upload(
        path, buf.getvalue(),
        {"content-type": "application/vnd.openxmlformats-officedocument."
                         "wordprocessingml.document", "upsert": "true"},
    )
    campos["storage_path"] = path
    campos["gerado_por"] = "HUMANO"
    campos["atualizado_em"] = datetime.now(_tz2.utc).isoformat()
    atualizado = db.table("documentos_assinatura").update(campos) \
                   .eq("id", documento_id).execute().data[0]
    registrar_evento(d["caso_id"], "DOCUMENTO_AJUSTADO",
                     {"documento_id": documento_id, "campos": list(campos)})
    return {"ok": True, "documento": atualizado}
