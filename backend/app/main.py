"""FSC LEGAL OS v4.0 — Backend FastAPI (api.seudominio.com.br)."""
import httpx
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.config import get_settings
from .core.db import get_db
from .agentes import triagem, especialista, jurisprudencial, radar
from .agentes.orquestrador import mudar_estado, escalar_para_humano, TransicaoInvalida
from .integracoes import asaas, zapsign, whatsapp

app = FastAPI(title="FC Legal OS", version="4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir ao domínio do app em produção
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _agendar_radar():
    """Liga o Radar Jurimétrico semanal (DataJud) dentro do container da API.
    Desligar com RADAR_AUTO=false. Roda 1x/semana (padrão: segunda 06:00 UTC)."""
    s = get_settings()
    if not s.radar_auto:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        sched = BackgroundScheduler(timezone="UTC")
        sched.add_job(
            radar.radar_semanal,
            CronTrigger(day_of_week=s.radar_dia_semana, hour=s.radar_hora, minute=0),
            id="radar_semanal", replace_existing=True, max_instances=1,
        )
        sched.start()
        app.state.scheduler = sched
    except Exception as e:  # API sobe mesmo sem o scheduler
        print(f"[radar] scheduler não iniciado: {e}")


@app.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "ambiente": s.ambiente, "versao": "4.0"}


# ── Portal: novo lead e conversa ─────────────────────────────────
class NovoLead(BaseModel):
    nome: str
    contato: str
    relato: str
    cpf: str | None = None
    canal: str = "PORTAL"


@app.post("/api/v1/leads")
def novo_lead(body: NovoLead):
    from .core.cpf import cpf_valido
    if body.cpf and not cpf_valido(body.cpf):
        raise HTTPException(400, "CPF inválido — confira os números.")
    return triagem.criar_caso(body.nome, body.contato, body.relato, body.canal, cpf=body.cpf)


@app.get("/api/v1/validar-cpf")
def validar_cpf_endpoint(cpf: str):
    from .core.cpf import cpf_valido
    return {"cpf": cpf, "valido": cpf_valido(cpf)}


class Mensagem(BaseModel):
    conteudo: str
    canal: str = "PORTAL"


@app.post("/api/v1/casos/{caso_id}/mensagens")
def conversar(caso_id: str, body: Mensagem):
    return especialista.atender(caso_id, body.conteudo, body.canal)


# ── CRM ──────────────────────────────────────────────────────────
@app.get("/api/v1/casos")
def listar_casos(estado: str | None = None, grupo: str | None = None):
    q = get_db().table("casos").select("*, clientes(nome,whatsapp,email)")
    if estado:
        q = q.eq("estado", estado)
    if grupo:
        q = q.eq("grupo", grupo)
    return q.order("atualizado_em", desc=True).limit(200).execute().data


@app.get("/api/v1/casos/{caso_id}")
def detalhe_caso(caso_id: str):
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
    caso["mensagens"] = db.table("mensagens").select("*").eq("caso_id", caso_id) \
                          .order("criado_em").execute().data
    caso["documentos"] = db.table("documentos").select("*").eq("caso_id", caso_id).execute().data
    return caso


@app.post("/api/v1/casos/{caso_id}/aprovar-protocolar")
def aprovar_e_protocolar(caso_id: str, tribunal: str = "EPROC_TJSC"):
    """Botão APROVAR E PROTOCOLAR do CRM → fila do RPA."""
    try:
        mudar_estado(caso_id, "APROVADO", motivo="Aprovado pelo advogado no CRM")
        mudar_estado(caso_id, "PROTOCOLO_RPA", motivo=f"Enfileirado p/ {tribunal}")
    except TransicaoInvalida as e:
        raise HTTPException(409, str(e))

    get_db().table("protocolos").insert(
        {"caso_id": caso_id, "tribunal": tribunal}
    ).execute()
    try:
        from workers.fila import enfileirar_protocolo
        enfileirar_protocolo(caso_id, tribunal)
    except Exception:
        pass  # worker pega da tabela mesmo sem Redis
    return {"ok": True, "fila": tribunal}


@app.post("/api/v1/casos/{caso_id}/escalar")
def escalar_manual(caso_id: str, motivo: str = "PEDIDO_CLIENTE", detalhe: str = ""):
    return escalar_para_humano(caso_id, motivo, detalhe)


@app.post("/api/v1/cerebro/processar")
def cerebro_processar():
    """Processa os acórdãos do bucket jurisprudencia/<GRUPO>[/<SUBNICHO>]/,
    cria/reforça teses e move os PDFs para _processados (automático)."""
    return jurisprudencial.processar_bucket()


@app.post("/api/v1/cerebro/radar-semanal")
def cerebro_radar_semanal(processar_pdfs: bool = True):
    """Radar Jurimétrico DataJud/CNJ: varre TJRO/TRT14 por grupo, agrega a
    jurimetria da semana, atualiza teses pelas íntegras e notifica o advogado.
    Disparado pelo scheduler semanal ou manualmente pelo CRM."""
    return radar.radar_semanal(processar_pdfs=processar_pdfs)


@app.get("/api/v1/radar")
def listar_radar(grupo: str | None = None, limite: int = 12):
    q = get_db().table("radar_jurimetrico").select("*")
    if grupo:
        q = q.eq("grupo", grupo)
    return q.order("semana_ref", desc=True).limit(limite).execute().data


# ── Área do cliente (autenticada via Supabase) ──────────────────
def _usuario_do_token(authorization: str | None) -> dict:
    """Valida o access_token do Supabase chamando /auth/v1/user
    (não precisa do JWT secret) e retorna o usuário {id, email}."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Token ausente")
    token = authorization.split(" ", 1)[1]
    s = get_settings()
    try:
        r = httpx.get(
            f"{s.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": s.supabase_service_key},
            timeout=15,
        )
    except httpx.HTTPError:
        raise HTTPException(503, "Auth indisponível")
    if r.status_code != 200:
        raise HTTPException(401, "Token inválido")
    return r.json()


class RegistroEquipe(BaseModel):
    codigo: str


@app.post("/api/v1/equipe/registrar")
def equipe_registrar(body: RegistroEquipe, authorization: str | None = Header(default=None)):
    """Promove o usuário logado a OPERADOR se o código de acesso da equipe
    conferir. Permite cadastrar vários funcionários com segurança."""
    user = _usuario_do_token(authorization)
    s = get_settings()
    if not s.equipe_codigo or body.codigo.strip() != s.equipe_codigo:
        raise HTTPException(403, "Código de acesso inválido")
    get_db().table("perfis").upsert({
        "id": user["id"], "papel": "OPERADOR", "email": user.get("email"),
    }, on_conflict="id").execute()
    return {"ok": True, "papel": "OPERADOR"}


@app.get("/api/v1/cliente/meus-casos")
def cliente_meus_casos(authorization: str | None = Header(default=None)):
    """Casos do cliente logado — vinculados pelo e-mail do cadastro."""
    user = _usuario_do_token(authorization)
    email = user.get("email")
    if not email:
        return []
    db = get_db()
    cli = db.table("clientes").select("id").eq("email", email).maybe_single().execute().data
    if not cli:
        return []
    return db.table("casos").select("id,estado,grupo,subtipo") \
             .eq("cliente_id", cli["id"]).order("criado_em", desc=True).execute().data


@app.get("/api/v1/teses")
def listar_teses(grupo: str | None = None):
    q = get_db().table("teses").select("*").eq("overruled", False)
    if grupo:
        q = q.eq("grupo", grupo)
    return q.execute().data


# ── Webhooks (eventos confirmam, nunca o agente) ────────────────
@app.post("/webhooks/asaas")
async def webhook_asaas(req: Request):
    return asaas.processar_webhook(await req.json())


@app.post("/webhooks/zapsign")
async def webhook_zapsign(req: Request):
    return zapsign.processar_webhook(await req.json())


@app.post("/webhooks/whatsapp")
async def webhook_whatsapp(req: Request):
    return whatsapp.processar_webhook(await req.json())


@app.get("/webhooks/whatsapp")
def verificar_whatsapp(request: Request):
    """Verificação do webhook exigida pela Meta."""
    p = request.query_params
    if p.get("hub.verify_token") == "fsc-legal-os":
        return int(p.get("hub.challenge", 0))
    raise HTTPException(403)
