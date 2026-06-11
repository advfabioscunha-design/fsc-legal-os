"""
CÉREBRO JURISPRUDENCIAL — versão CLOUD.

Espelha o fluxo local: PDFs de acórdãos organizados por nicho/subnicho,
engenharia reversa do ratio decidendi, teses por GRUPO, reforço sem
duplicar, e OVERRULING com EXCLUSÃO da tese antiga (arquivada em
teses_arquivadas) — diretriz do escritório.

Entrada: bucket 'jurisprudencia' no Supabase Storage, caminhos:
  <GRUPO>/<SUBNICHO>/arquivo.pdf      (subnicho fixa o subtipo)
  <GRUPO>/arquivo.pdf
Processados são movidos para .../_processados/.

Endpoint: POST /api/v1/cerebro/processar  (chamado pelo CRM ou cron)
"""
import io
import json
import uuid
from datetime import datetime, timezone

import anthropic
import fitz  # PyMuPDF

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento

BUCKET = "jurisprudencia"
GRUPOS_VALIDOS = ["BANCARIO", "IMOBILIARIO", "TRIBUTARIO", "CONSUMIDOR"]

SYSTEM_PROMPT = """
Você é um Especialista em Jurimetria e Engenharia de Teses Jurídicas.
Analise decisões judiciais brasileiras e extraia informações estruturadas.

REGRAS ABSOLUTAS:
- Nunca invente dados, números de processo, datas ou nomes; ausente = null.
- Identifique o Ratio Decidendi (motivo determinante), não o obiter dictum.
- Extraia os DOCUMENTOS VITAIS (provas decisivas para o deferimento).
- Formule a DIRETRIZ DE REDAÇÃO (como enquadrar um caso novo no padrão aceito).
- Compare com o banco atual: REFORCA (anexa jurisprudência à tese existente),
  OVERRULING (virada pacificada: a antiga será EXCLUÍDA e substituída) ou NOVA.
- OVERRULING só por entendimento pacificado/vinculante, nunca decisão isolada.
- Responda APENAS JSON válido.
"""


def _claude():
    return anthropic.Anthropic(api_key=get_settings().claude_api_key)


def _resumo_banco(grupo: str) -> list:
    teses = get_db().table("teses").select(
        "id,grupo,subtipo,titulo,tribunal_origem,ratio_decidendi"
    ).eq("grupo", grupo).execute().data
    for t in teses:
        t["ratio_decidendi"] = (t.get("ratio_decidendi") or "")[:300]
    return teses


def _analisar(texto: str, nome: str, grupo: str, subtipo: str | None) -> dict | None:
    s = get_settings()
    fixacao = f"O campo 'area' DEVE ser '{grupo}'."
    if subtipo:
        fixacao += f" O campo 'subtipo' DEVE ser '{subtipo}'."

    prompt = f"""
BANCO DE TESES ATUAL DO GRUPO {grupo}:
{json.dumps(_resumo_banco(grupo), ensure_ascii=False)}

{fixacao}

DECISÃO (PDF "{nome}"):
{texto[:80000]}

Retorne UM objeto JSON:
{{"area":"{grupo}","subtipo":"...","titulo":"máx 100 chars",
"tribunal_origem":"...","numero_processo":null,"ratio_decidendi":"min 2 frases",
"documentos_vitais":[],"argumentos_chave":[],"diretriz_redacao":"...",
"jurisprudencia_citada":[{{"tribunal":"","tipo":"","numero":"","ementa":"","aplicacao_ao_caso":""}}],
"relacao_com_banco":"NOVA|REFORCA|OVERRULING","tese_relacionada_id":null,
"motivo_overruling":null,"honorarios_modelo":"MASSA|ALTA_COMPLEXIDADE"}}
APENAS o JSON."""

    r = _claude().messages.create(model=s.claude_model, max_tokens=4096,
                                  system=SYSTEM_PROMPT,
                                  messages=[{"role": "user", "content": prompt}])
    txt = r.content[0].text.strip()
    if txt.startswith("```"):
        txt = "\n".join(txt.split("\n")[1:-1])
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def _aplicar(dados: dict, grupo: str, fonte: str) -> dict:
    """NOVA cria; REFORCA enriquece; OVERRULING exclui a antiga (arquivada)."""
    db = get_db()
    rel = dados.get("relacao_com_banco", "NOVA")

    if rel == "REFORCA" and dados.get("tese_relacionada_id"):
        t = db.table("teses").select("*").eq("id", dados["tese_relacionada_id"]) \
              .maybe_single().execute().data
        if t:
            vistos = {(j.get("tipo"), j.get("numero")) for j in t["jurisprudencia"]}
            novos = [j for j in dados.get("jurisprudencia_citada", [])
                     if (j.get("tipo"), j.get("numero")) not in vistos]
            db.table("teses").update({
                "jurisprudencia": t["jurisprudencia"] + novos,
                "documentos_vitais": sorted(set(t["documentos_vitais"])
                                            | set(dados.get("documentos_vitais", []))),
                "atualizado_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", t["id"]).execute()
            return {"acao": "REFORCO", "tese": t["id"], "novos_julgados": len(novos)}

    nova_id = f"{grupo[:3]}_{str(uuid.uuid4())[:4].upper()}"
    if rel == "OVERRULING" and dados.get("tese_relacionada_id"):
        antiga = db.table("teses").select("*").eq("id", dados["tese_relacionada_id"]) \
                   .maybe_single().execute().data
        if antiga:
            db.table("teses_arquivadas").upsert({
                "id": antiga["id"], "tese": antiga,
                "motivo_exclusao": dados.get("motivo_overruling"),
                "substituida_por": nova_id,
            }).execute()
            db.table("teses").delete().eq("id", antiga["id"]).execute()
            registrar_evento(None, "TESE_EXCLUIDA_OVERRULING",
                             {"antiga": antiga["id"], "nova": nova_id})

    db.table("teses").insert({
        "id": nova_id, "grupo": grupo,
        "subtipo": dados.get("subtipo"), "titulo": dados.get("titulo", ""),
        "tribunal_origem": dados.get("tribunal_origem"),
        "ratio_decidendi": dados.get("ratio_decidendi", ""),
        "documentos_vitais": dados.get("documentos_vitais", []),
        "argumentos_chave": dados.get("argumentos_chave", []),
        "diretriz_redacao": dados.get("diretriz_redacao"),
        "jurisprudencia": dados.get("jurisprudencia_citada", []),
        "honorarios": {"modelo": dados.get("honorarios_modelo", "MASSA")},
        "fonte_pdf": fonte,
    }).execute()
    return {"acao": "OVERRULING_RENOVACAO" if rel == "OVERRULING" else "NOVA",
            "tese": nova_id}


def processar_bucket() -> dict:
    """Varre o bucket jurisprudencia/<GRUPO>[/<SUBNICHO>]/, processa cada PDF
    e o move para _processados/ da mesma pasta (movimento automático)."""
    db = get_db()
    storage = db.storage.from_(BUCKET)
    resultados = []

    def listar(caminho: str):
        try:
            return storage.list(caminho) or []
        except Exception:
            return []

    for grupo in GRUPOS_VALIDOS:
        alvos = [(grupo, None, f"{grupo}")]
        for item in listar(grupo):
            if item.get("id") is None and item["name"] not in ("_processados",):
                alvos.append((grupo, item["name"].replace("_", " ").title(),
                              f"{grupo}/{item['name']}"))

        for g, subtipo, pasta in alvos:
            for arq in listar(pasta):
                if not arq["name"].lower().endswith(".pdf"):
                    continue
                caminho = f"{pasta}/{arq['name']}"
                blob = storage.download(caminho)
                doc = fitz.open(stream=io.BytesIO(blob), filetype="pdf")
                texto = "".join(p.get_text() for p in doc).strip()
                doc.close()
                if not texto:
                    resultados.append({"pdf": caminho, "erro": "sem texto (OCR?)"})
                    continue

                dados = _analisar(texto, arq["name"], g, subtipo)
                if not dados:
                    resultados.append({"pdf": caminho, "erro": "análise falhou"})
                    continue

                r = _aplicar(dados, g, arq["name"])
                storage.move(caminho, f"{pasta}/_processados/{arq['name']}")
                registrar_evento(None, "CEREBRO_CLOUD", {"pdf": caminho, **r})
                resultados.append({"pdf": caminho, **r})

    return {"processados": len(resultados), "detalhes": resultados}
