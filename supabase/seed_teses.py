"""
Importa o teses_banco.json (v3.1 local) para a tabela `teses` do Supabase
e cria os Agentes Especialistas de cada grupo encontrado.

Uso:  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python seed_teses.py caminho/teses_banco.json
"""
import json
import sys
import os
from supabase import create_client

MAPA_GRUPO = {
    "bancario": "BANCARIO", "imobiliario": "IMOBILIARIO",
    "trabalhista": "TRABALHISTA", "previdenciario": "PREVIDENCIARIO",
    "tributario": "TRIBUTARIO", "consumidor": "CONSUMIDOR",
}


def main(caminho_json: str):
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    banco = json.load(open(caminho_json, encoding="utf-8"))

    grupos = set()
    for t in banco["teses"]:
        grupo = MAPA_GRUPO.get(t.get("area", "").lower().strip(), "OUTROS")
        grupos.add(grupo)
        db.table("teses").upsert({
            "id": t["id"], "grupo": grupo,
            "subtipo": t.get("subtipo"), "titulo": t["titulo"],
            "status": t.get("status", "ATIVA"),
            "tribunal_origem": t.get("tribunal_origem"),
            "ratio_decidendi": t.get("ratio_decidendi", ""),
            "documentos_vitais": t.get("documentos_vitais", []),
            "argumentos_chave": t.get("argumentos_chave", []),
            "diretriz_redacao": t.get("diretriz_redacao"),
            "jurisprudencia": t.get("jurisprudencia", []),
            "calculo_base": t.get("calculo_base"),
            "honorarios": t.get("honorarios"),
            "overruled": t.get("overruled", False),
            "tese_substituta": t.get("tese_substituta"),
            "fonte_pdf": t.get("fonte_pdf"),
        }).execute()
        print(f"  tese {t['id']} → grupo {grupo}")

    for g in grupos:
        db.table("agentes_especialistas").upsert({
            "grupo": g,
            "nome": f"Especialista {g.title()}",
            "system_prompt": "GERADO_DINAMICAMENTE",  # especialista.py gera em runtime
        }).execute()
        print(f"  agente especialista criado: {g}")

    # ── Sincroniza EXCLUSÕES (diretriz: excluir tese superada e renovar) ──
    # Teses excluídas localmente (teses_arquivadas.json) saem da nuvem
    # também, com cópia na tabela teses_arquivadas.
    arq_path = os.path.join(os.path.dirname(caminho_json), "teses_arquivadas.json")
    if os.path.exists(arq_path):
        arquivadas = json.load(open(arq_path, encoding="utf-8")).get("teses", [])
        for t in arquivadas:
            db.table("teses_arquivadas").upsert({
                "id": t["id"], "tese": t,
                "motivo_exclusao": t.get("_motivo_exclusao"),
                "substituida_por": t.get("_substituida_por"),
            }).execute()
            db.table("teses").delete().eq("id", t["id"]).execute()
            print(f"  tese {t['id']} excluída da nuvem (arquivada)")

    print(f"\nConcluído: {len(banco['teses'])} teses, {len(grupos)} especialistas.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../../teses_banco.json")
