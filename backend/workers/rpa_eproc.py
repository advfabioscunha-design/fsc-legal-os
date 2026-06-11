"""
RPA EPROC — protocolo autônomo headless (Playwright) na nuvem.

Fluxo: pega petição + docs no Supabase Storage → loga no Eproc →
peticionamento inicial → preenche metadados → upload dos PDFs →
assina (certificado em nuvem via API PSC, ou A1 no servidor) →
captura nº do processo → atualiza CRM → notifica cliente.

Os seletores do Eproc variam por tribunal/versão — calibrar na
primeira execução real em staging (RPA_HEADLESS=false para assistir).
"""
import os
import sys, pathlib
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.core.db import get_db, registrar_evento

TRIBUNAIS = {
    "EPROC_TJSC": {"url": "https://eproc1g.tjsc.jus.br/eproc/"},
    "PJE_TJRO":   {"url": "https://pjepg.tjro.jus.br/"},
    "PJE_TRT14":  {"url": "https://pje.trt14.jus.br/primeirograu/login.seam"},
}
MAX_TENTATIVAS = 3


def _log(protocolo_id: str, etapa: str, detalhe: str = ""):
    db = get_db()
    atual = db.table("protocolos").select("log").eq("id", protocolo_id).single().execute().data
    log = atual["log"] + [{"ts": datetime.now(timezone.utc).isoformat(),
                           "etapa": etapa, "detalhe": detalhe}]
    db.table("protocolos").update(
        {"log": log, "atualizado_em": datetime.now(timezone.utc).isoformat()}
    ).eq("id", protocolo_id).execute()


def executar_protocolo(caso_id: str, tribunal: str) -> dict:
    from playwright.sync_api import sync_playwright

    s = get_settings()
    db = get_db()
    prot = db.table("protocolos").select("*").eq("caso_id", caso_id) \
             .eq("status", "NA_FILA").order("criado_em", desc=True) \
             .limit(1).execute().data
    if not prot:
        return {"erro": "protocolo não encontrado na fila"}
    prot = prot[0]
    pid = prot["id"]

    db.table("protocolos").update(
        {"status": "EXECUTANDO", "tentativas": prot["tentativas"] + 1}
    ).eq("id", pid).execute()
    _log(pid, "INICIO", tribunal)

    try:
        caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data

        # 1. baixa a petição do Storage
        pdf_path = "/tmp/peticao.pdf"
        blob = db.storage.from_(s.bucket_documentos).download(caso["peticao_storage_path"])
        with open(pdf_path, "wb") as f:
            f.write(blob)
        _log(pid, "PETICAO_BAIXADA", caso["peticao_storage_path"])

        # 2. navegação headless
        cfg = TRIBUNAIS[tribunal]
        login = os.getenv(f"{tribunal}_LOGIN", "")
        senha = os.getenv(f"{tribunal}_SENHA", "")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=s.rpa_headless)
            page = browser.new_page()
            page.goto(cfg["url"], timeout=60_000)
            _log(pid, "TRIBUNAL_ACESSADO", cfg["url"])

            # — login (seletores Eproc 1º grau; calibrar em staging) —
            page.fill("#txtUsuario", login)
            page.fill("#pwdSenha", senha)
            page.click("#sbmEntrar")
            page.wait_for_load_state("networkidle")
            _log(pid, "LOGIN_OK")

            # — peticionamento inicial: menu → formulário → uploads —
            # [CALIBRAR]: cada Eproc estadual tem variações de menu.
            # A 1ª execução em staging grava screenshots de cada passo.
            page.screenshot(path=f"/tmp/protocolo_{pid}.png")
            _log(pid, "AGUARDANDO_CALIBRACAO",
                 "Seletores do peticionamento a calibrar na 1ª execução em staging")

            # — assinatura —
            # Plano A: API do certificado em nuvem (BirdID/PSC) assina o PDF
            #          ANTES do upload (módulo integracoes/assinatura_nuvem).
            # Plano B: certificado A1 no servidor (decifrado só em runtime).
            browser.close()

        db.table("protocolos").update({"status": "FALHA"}).eq("id", pid).execute()
        registrar_evento(caso_id, "PROTOCOLO_PENDENTE_CALIBRACAO", {"protocolo": pid})
        _notificar(f"🔧 RPA {tribunal}: executou até a calibração de seletores. "
                   f"Caso {caso_id[:8]} aguarda 1ª execução assistida.")
        return {"status": "PENDENTE_CALIBRACAO"}

    except Exception as e:
        _log(pid, "ERRO", str(e)[:500])
        db.table("protocolos").update({"status": "FALHA"}).eq("id", pid).execute()
        if prot["tentativas"] + 1 >= MAX_TENTATIVAS:
            from app.agentes.orquestrador import escalar_para_humano
            escalar_para_humano(caso_id, "DIFICULDADE",
                                f"RPA falhou {MAX_TENTATIVAS}x no {tribunal}: {e}",
                                oferecer_agenda=False)
        _notificar(f"❌ RPA {tribunal} falhou no caso {caso_id[:8]}: {str(e)[:200]}")
        return {"status": "FALHA", "erro": str(e)}


def _notificar(msg: str):
    try:
        from app.integracoes.whatsapp import notificar_humano
        notificar_humano(msg)
    except Exception:
        pass


def confirmar_sucesso(caso_id: str, numero_processo: str):
    """Chamado quando o robô captura o número do processo."""
    from app.agentes.orquestrador import mudar_estado
    from app.integracoes.whatsapp import enviar_para_cliente
    db = get_db()
    db.table("casos").update({"numero_processo": numero_processo}).eq("id", caso_id).execute()
    db.table("protocolos").update({"status": "SUCESSO", "numero_processo": numero_processo}) \
      .eq("caso_id", caso_id).execute()
    mudar_estado(caso_id, "PROTOCOLADO", motivo=f"Processo {numero_processo}")
    try:
        enviar_para_cliente(caso_id,
            f"Ótima notícia! 🎉 Sua ação foi protocolada na Justiça.\n"
            f"Número do processo: {numero_processo}\n"
            f"Vou te manter informado de cada movimentação.")
    except Exception:
        pass
