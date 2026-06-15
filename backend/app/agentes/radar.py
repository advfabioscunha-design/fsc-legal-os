"""
RADAR JURIMÉTRICO SEMANAL — orquestra o DataJud CNJ.

Toda semana, para cada GRUPO de tese:
  1. Varre o DataJud (TJRO, TRT14...) por assuntos do grupo nos últimos 7 dias;
  2. Agrega jurimetria (julgados, procedência/improcedência, órgãos e
     assuntos em alta, taxa de êxito);
  3. Gera uma LEITURA ESTRATÉGICA com a IA a partir dos metadados;
  4. Persiste o snapshot (radar_jurimetrico) e marca os processos
     monitorados (datajud_monitorados) sem recontar;
  5. Aponta ALVOS cuja íntegra deve ser captada para virar tese;
  6. Em seguida roda o pipeline de PDFs (jurisprudencial.processar_bucket),
     mantendo as TESES atualizadas a partir das íntegras já no bucket;
  7. Notifica o Dr. Fábio com o resumo da semana no WhatsApp.

Limite honesto: o DataJud NÃO traz a íntegra do acórdão. A criação/reforço
de TESE (ratio decidendi) continua vindo das íntegras (PDFs). O radar diz
ONDE estão os julgados que valem a captação da íntegra.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..integracoes import datajud, whatsapp
from . import jurisprudencial

GRUPOS = jurisprudencial.GRUPOS_VALIDOS


def _segunda_da_semana() -> date:
    hoje = datetime.now(timezone.utc).date()
    return hoje - timedelta(days=hoje.weekday())


def _claude():
    return anthropic.Anthropic(api_key=get_settings().claude_api_key)


def _leitura_estrategica(grupo: str, agg: dict) -> str:
    """Síntese curta e acionável a partir dos metadados agregados."""
    s = get_settings()
    try:
        prompt = f"""Você é o estrategista de jurimetria do escritório.
A partir DESTES METADADOS (DataJud/CNJ, sem íntegra) do grupo {grupo} na
última semana, escreva uma leitura ESTRATÉGICA e acionável (máx. 6 linhas):
o que está sendo julgado, em quais órgãos há tendência favorável, quais
assuntos subiram, e qual movimento o escritório deve fazer (ex.: captar a
íntegra de X para virar tese, priorizar tal subnicho). Não invente dados.

DADOS:
{json.dumps(agg, ensure_ascii=False)}"""
        r = _claude().messages.create(
            model=s.claude_model_rapido, max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text.strip()
    except Exception as e:  # nunca derruba o radar por falha de IA
        return f"(Leitura automática indisponível: {e})"


def _agregar(grupo: str, processos: list[dict], novos: list[dict]) -> dict:
    proced = sum(1 for p in processos if p["resultado"] == "PROCEDENTE")
    improc = sum(1 for p in processos if p["resultado"] == "IMPROCEDENTE")
    julgados = len(processos)
    orgaos = Counter(p["orgao"] for p in processos if p.get("orgao"))
    assuntos = Counter(a for p in processos for a in p.get("assuntos", []))
    base = proced + improc
    return {
        "grupo": grupo,
        "total_julgados": julgados,
        "novos_na_semana": len(novos),
        "procedentes": proced,
        "improcedentes": improc,
        "taxa_exito": round(proced / base, 3) if base else None,
        "orgaos_destaque": [{"orgao": o, "qtd": q} for o, q in orgaos.most_common(5)],
        "assuntos_alta": [{"assunto": a, "qtd": q} for a, q in assuntos.most_common(6)],
    }


def radar_grupo(grupo: str, dias: int = 7) -> dict:
    db = get_db()
    encontrados = datajud.varrer_grupo(grupo, dias=dias)

    # deduplicação por banco: só conta como "novo" quem o radar nunca viu
    nums = [p["numero"] for p in encontrados if p.get("numero")]
    ja_vistos: set[str] = set()
    if nums:
        for i in range(0, len(nums), 100):
            lote = nums[i:i + 100]
            res = db.table("datajud_monitorados").select("numero_processo") \
                    .in_("numero_processo", lote).execute().data
            ja_vistos |= {r["numero_processo"] for r in res}
    novos = [p for p in encontrados if p.get("numero") not in ja_vistos]

    # persiste novos monitorados
    for p in novos:
        try:
            db.table("datajud_monitorados").upsert({
                "numero_processo": p["numero"], "grupo": grupo,
                "tribunal": p["tribunal"], "orgao_julgador": p.get("orgao"),
                "classe": p.get("classe"), "assuntos": p.get("assuntos", []),
                "resultado": p.get("resultado"),
                "data_julgamento": p.get("data_julgamento"),
            }, on_conflict="numero_processo").execute()
        except Exception:
            pass

    agg = _agregar(grupo, encontrados, novos)
    leitura = _leitura_estrategica(grupo, agg) if encontrados else \
        "Nenhum julgado novo no período para os assuntos monitorados."

    # alvos para captação de íntegra: procedentes inéditos (viram tese)
    alvos = [{"numero": p["numero"], "orgao": p.get("orgao"),
              "tribunal": p["tribunal"], "assuntos": p.get("assuntos", [])}
             for p in novos if p.get("resultado") == "PROCEDENTE"][:20]

    semana = _segunda_da_semana().isoformat()
    try:
        db.table("radar_jurimetrico").upsert({
            "grupo": grupo, "semana_ref": semana,
            "tribunais": get_settings().datajud_tribunais or datajud.TRIBUNAIS_PADRAO,
            "total_julgados": agg["total_julgados"],
            "procedentes": agg["procedentes"],
            "improcedentes": agg["improcedentes"],
            "taxa_exito": agg["taxa_exito"],
            "orgaos_destaque": agg["orgaos_destaque"],
            "assuntos_alta": agg["assuntos_alta"],
            "leitura_ia": leitura, "alvos_integra": alvos,
        }, on_conflict="grupo,semana_ref").execute()
    except Exception:
        pass

    registrar_evento(None, "RADAR_DATAJUD",
                     {"grupo": grupo, **agg, "alvos": len(alvos)})
    return {"grupo": grupo, **agg, "alvos_integra": alvos, "leitura_ia": leitura}


def radar_semanal(processar_pdfs: bool = True) -> dict:
    """Ponto de entrada do agendamento semanal."""
    resultados = [radar_grupo(g) for g in GRUPOS]

    # mantém as TESES atualizadas a partir das íntegras já no bucket
    bucket = {}
    if processar_pdfs:
        try:
            bucket = jurisprudencial.processar_bucket()
        except Exception as e:
            bucket = {"erro": str(e)}

    _notificar_resumo(resultados, bucket)
    return {"semana": _segunda_da_semana().isoformat(),
            "radar": resultados, "bucket_pdfs": bucket}


def _notificar_resumo(resultados: list[dict], bucket: dict):
    linhas = ["📡 *Radar Jurimétrico — semana*", ""]
    for r in resultados:
        if r["total_julgados"] == 0:
            continue
        exito = f"{round(r['taxa_exito'] * 100)}%" if r.get("taxa_exito") is not None else "—"
        linhas.append(
            f"• *{r['grupo']}*: {r['total_julgados']} julgados "
            f"({r['novos_na_semana']} novos) · êxito {exito} · "
            f"{len(r['alvos_integra'])} alvos p/ tese"
        )
    if len(linhas) == 2:
        linhas.append("Sem julgados novos nos assuntos monitorados nesta semana.")
    if bucket.get("processados"):
        linhas.append(f"\n🧠 Teses atualizadas por íntegras: {bucket['processados']}")
    try:
        whatsapp.notificar_humano("\n".join(linhas))
    except Exception:
        pass
