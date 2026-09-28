"""FSC LEGAL OS v4.0 — Backend FastAPI (api.seudominio.com.br)."""
import json
import re

import httpx
from fastapi import (FastAPI, Request, HTTPException, Header, UploadFile,
                     File, BackgroundTasks)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.config import get_settings
from .core.db import get_db
from .agentes import triagem, especialista, jurisprudencial, radar
from .agentes.orquestrador import mudar_estado, escalar_para_humano, TransicaoInvalida
from .integracoes import asaas, zapsign, whatsapp, avisos, email_entrada

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
        # Agente de Relacionamento: parabéns de aniversário (diário, 12:00 UTC ~ 09:00 BRT)
        try:
            from .agentes import relacionamento
            sched.add_job(
                relacionamento.parabenizar_aniversariantes,
                CronTrigger(hour=12, minute=0),
                id="aniversarios", replace_existing=True, max_instances=1,
            )
        except Exception as e:
            print(f"[aniversarios] job não agendado: {e}")
        # Lembretes: reenvia avisos que o cliente ainda não deu ciência
        try:
            sched.add_job(
                avisos.reenviar_pendentes,
                CronTrigger(minute=20),          # de hora em hora
                id="lembretes_ciencia", replace_existing=True, max_instances=1,
            )
        except Exception as e:
            print(f"[lembretes] job não agendado: {e}")
        # Caixa de entrada: recebe a via assinada devolvida por e-mail
        try:
            if s.imap_auto:
                from apscheduler.triggers.interval import IntervalTrigger
                sched.add_job(
                    email_entrada.ler_respostas,
                    IntervalTrigger(minutes=s.imap_minutos),
                    id="ler_respostas_email", replace_existing=True, max_instances=1,
                )
        except Exception as e:
            print(f"[caixa de entrada] job não agendado: {e}")
        # Régua de cobrança: casos parados esperando documento do cliente.
        # Roda de hora em hora, mas cada etapa (3, 7 e 10 dias) só dispara
        # uma vez por caso — quem controla é a contagem gravada no caso.
        try:
            from .agentes import pendencias
            sched.add_job(
                pendencias.rodar,
                CronTrigger(hour=9, minute=40),   # uma vez por dia, de manhã
                id="regua_cobranca", replace_existing=True, max_instances=1,
            )
        except Exception as e:
            print(f"[régua] job não agendado: {e}")
        # Controladoria: varre o DJEN pela OAB, recalcula as datas de
        # trabalho, vira as fases e manda os convites de agenda. Roda de
        # manhã cedo para que a fila do dia já esteja pronta às 8h BRT.
        try:
            from .agentes import controladoria
            sched.add_job(
                controladoria.rodar,
                CronTrigger(hour=10, minute=10),   # 07:10 BRT
                id="controladoria", replace_existing=True, max_instances=1,
            )
        except Exception as e:
            print(f"[controladoria] job não agendado: {e}")
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
    contato: str = ""           # legado: e-mail OU telefone
    relato: str
    cpf: str | None = None
    email: str | None = None    # cadastro completo
    whatsapp: str | None = None
    canal: str = "PORTAL"


@app.post("/api/v1/leads")
def novo_lead(body: NovoLead):
    from .core.cpf import cpf_valido
    if body.cpf and not cpf_valido(body.cpf):
        raise HTTPException(400, "CPF inválido — confira os números.")
    return triagem.criar_caso(
        body.nome, body.contato, body.relato, body.canal,
        cpf=body.cpf, email=body.email, whatsapp=body.whatsapp,
    )


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


# ── Serviço de Elaboração de Contrato ────────────────────────────
class ContratoInit(BaseModel):
    nome: str
    contato: str
    cpf: str | None = None
    canal: str = "PORTAL"


@app.post("/api/v1/contrato/iniciar")
def contrato_iniciar(body: ContratoInit):
    from .agentes import contrato
    return contrato.iniciar(body.nome, body.contato, body.canal, cpf=body.cpf)


@app.post("/api/v1/contrato/{caso_id}/mensagens")
def contrato_conversar(caso_id: str, body: Mensagem):
    from .agentes import contrato
    return contrato.atender(caso_id, body.conteudo, body.canal)


# ── CRM ──────────────────────────────────────────────────────────
@app.get("/api/v1/casos")
def listar_casos(estado: str | None = None, grupo: str | None = None, situacao: str = "ATIVO"):
    db = get_db()
    def montar(com_situacao: bool):
        q = db.table("casos").select("*, clientes(nome,whatsapp,email,origem)")
        if com_situacao and situacao and situacao != "TODOS":
            q = q.eq("situacao", situacao)
        if estado:
            q = q.eq("estado", estado)
        if grupo:
            q = q.eq("grupo", grupo)
        return q.order("atualizado_em", desc=True).limit(300).execute().data
    try:
        return montar(True)
    except Exception:
        return montar(False)  # coluna 'situacao' ainda não criada (migração pendente)


@app.get("/api/v1/casos/{caso_id}")
def detalhe_caso(caso_id: str):
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
    caso["mensagens"] = db.table("mensagens").select("*").eq("caso_id", caso_id) \
                          .order("criado_em").execute().data
    caso["documentos"] = db.table("documentos").select("*").eq("caso_id", caso_id) \
                           .order("criado_em", desc=True).execute().data
    try:
        caso["solicitacoes"] = db.table("solicitacoes").select("*") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        caso["solicitacoes"] = []
    try:
        caso["avisos"] = db.table("avisos").select("*") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).limit(50).execute().data
    except Exception:
        caso["avisos"] = []
    try:
        caso["documentos_assinatura"] = db.table("documentos_assinatura").select("*") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        caso["documentos_assinatura"] = []
    try:
        caso["prestacoes_contas"] = db.table("prestacoes_contas").select("*") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        caso["prestacoes_contas"] = []
    return caso


class EditarCliente(BaseModel):
    nome: str | None = None
    email: str | None = None
    cpf_cnpj: str | None = None
    whatsapp: str | None = None
    nacionalidade: str | None = None
    estado_civil: str | None = None
    profissao: str | None = None
    rg: str | None = None
    endereco_rua: str | None = None
    endereco_numero: str | None = None
    endereco_complemento: str | None = None
    endereco_bairro: str | None = None
    endereco_cidade: str | None = None
    endereco_uf: str | None = None
    endereco_cep: str | None = None


@app.patch("/api/v1/clientes/{cliente_id}")
def editar_cliente(cliente_id: str, body: EditarCliente):
    """CRM: completa ou corrige o cadastro do cliente (inclusive o e-mail,
    que é o que liga o acesso dele à plataforma)."""
    campos = {k: (v.strip() if isinstance(v, str) else v)
              for k, v in body.model_dump().items() if v is not None}
    if campos.get("email"):
        campos["email"] = campos["email"].lower()
        if "@" not in campos["email"]:
            raise HTTPException(400, "E-mail inválido.")
    if campos.get("whatsapp"):
        campos["whatsapp"] = "".join(c for c in campos["whatsapp"] if c.isdigit())
    if campos.get("cpf_cnpj"):
        from .core.cpf import cpf_valido
        so_num = "".join(c for c in campos["cpf_cnpj"] if c.isdigit())
        if len(so_num) == 11 and not cpf_valido(so_num):
            raise HTTPException(400, "CPF inválido — confira os números.")
        campos["cpf_cnpj"] = so_num
    db = get_db()
    antes = db.table("clientes").select("*").eq("id", cliente_id) \
              .maybe_single().execute().data or {}
    if campos:
        try:
            db.table("clientes").update(campos).eq("id", cliente_id).execute()
        except Exception as e:
            raise HTTPException(400, f"Não foi possível salvar: {e}")

    # trocou e-mail ou WhatsApp? a plataforma passa a falar no endereço novo
    troca = {}
    if _mudou_contato(antes, campos):
        try:
            troca = avisos.avisar_troca_de_contato(
                cliente_id, antes, {**antes, **campos}, quem="ESCRITORIO")
        except Exception as e:
            troca = {"erro": str(e)}
    return {"ok": True, **({"contato": troca} if troca else {})}


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


# ── Montagem de Processo do Escritório (operação interna) ─────────
_GRUPOS_VALIDOS = {"BANCARIO", "IMOBILIARIO", "TRABALHISTA",
                   "PREVIDENCIARIO", "TRIBUTARIO", "CONSUMIDOR", "OUTROS"}
_FASES_VALIDAS = {"QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO",
                  "COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO",
                  "PROTOCOLO_RPA", "PROTOCOLADO"}


class CasoEscritorio(BaseModel):
    nome: str
    contato: str | None = None      # email ou whatsapp
    cpf: str | None = None
    grupo: str | None = None        # grupo_tese
    fase: str = "PETICAO"           # estado em que o processo entra
    descricao: str | None = None
    honorarios: str | None = None
    numero_processo: str | None = None


@app.post("/api/v1/casos/escritorio")
def criar_caso_escritorio(body: CasoEscritorio):
    """Cadastra um processo do escritório (cliente atendido por fora) já na
    fase em que ele se encontra, para entrar direto na esteira de produção."""
    from .core.db import registrar_evento
    if not body.contato or not body.contato.strip():
        raise HTTPException(400, "Informe o contato do cliente (e-mail ou WhatsApp) para acionamento.")
    db = get_db()
    fase = body.fase if body.fase in _FASES_VALIDAS else "PETICAO"
    grupo = body.grupo if body.grupo in _GRUPOS_VALIDOS else None

    cli: dict = {"nome": body.nome, "origem": "ESCRITORIO"}
    if body.contato:
        if "@" in body.contato:
            cli["email"] = body.contato
        else:
            cli["whatsapp"] = "".join(ch for ch in body.contato if ch.isdigit())
    if body.cpf:
        cli["cpf_cnpj"] = body.cpf
    cliente = db.table("clientes").insert(cli).execute().data[0]

    caso_row: dict = {
        "cliente_id": cliente["id"],
        "estado": fase,
        "relato_inicial": body.descricao or "Processo cadastrado pelo escritório",
    }
    if grupo:
        caso_row["grupo"] = grupo
    if body.honorarios:
        caso_row["honorarios_valor"] = body.honorarios
    if body.numero_processo:
        caso_row["numero_processo"] = body.numero_processo
    caso = db.table("casos").insert(caso_row).execute().data[0]
    registrar_evento(caso["id"], "CASO_ESCRITORIO_CRIADO",
                     {"fase": fase, "origem": "ESCRITORIO"})
    return {"ok": True, "caso_id": caso["id"], "estado": fase}


@app.get("/api/v1/pendencias")
def pendencias():
    """Casos escalados para humano (caixa de Intervenção Urgente), com a
    contagem de mensagens do cliente ainda não respondidas."""
    db = get_db()
    casos = db.table("casos").select("*, clientes(nome,whatsapp,email,origem)") \
        .eq("estado", "ESCALADO_HUMANO").order("atualizado_em", desc=True) \
        .limit(100).execute().data
    for c in casos:
        msgs = db.table("mensagens").select("autor").eq("caso_id", c["id"]) \
            .order("criado_em").execute().data
        nao_resp = 0
        for m in reversed(msgs):
            if m["autor"] == "CLIENTE":
                nao_resp += 1
            else:
                break
        c["mensagens_nao_respondidas"] = nao_resp
    return casos


# ── Gestão do caso (detalhe, edição, anexos, situação) ───────────
from datetime import datetime, timezone as _tz


class MotivoBody(BaseModel):
    motivo: str | None = None


class NotaBody(BaseModel):
    texto: str


class DocLink(BaseModel):
    nome: str | None = None
    url: str
    tipo: str | None = "LINK"


class EditarCaso(BaseModel):
    relato_inicial: str | None = None
    grupo: str | None = None
    honorarios: str | None = None
    numero_processo: str | None = None
    titulo: str | None = None          # nome do caso, visível ao cliente


def _set_situacao(caso_id: str, situacao: str, motivo: str | None, evento: str):
    from .core.db import registrar_evento
    get_db().table("casos").update({
        "situacao": situacao, "situacao_motivo": motivo,
        "atualizado_em": datetime.now(_tz.utc).isoformat(),
    }).eq("id", caso_id).execute()
    registrar_evento(caso_id, evento, {"motivo": motivo})
    return {"ok": True, "situacao": situacao}


@app.post("/api/v1/casos/{caso_id}/suspender")
def suspender_caso(caso_id: str, body: MotivoBody):
    return _set_situacao(caso_id, "SUSPENSO", body.motivo, "CASO_SUSPENSO")


@app.post("/api/v1/casos/{caso_id}/arquivar")
def arquivar_caso(caso_id: str, body: MotivoBody):
    return _set_situacao(caso_id, "ARQUIVADO", body.motivo, "CASO_ARQUIVADO")


@app.post("/api/v1/casos/{caso_id}/ativar")
def ativar_caso(caso_id: str):
    return _set_situacao(caso_id, "ATIVO", None, "CASO_ATIVADO")


@app.delete("/api/v1/casos/{caso_id}")
def excluir_caso(caso_id: str):
    db = get_db()
    # 1) BACKUP completo na lixeira ANTES de apagar (retenção 6 meses)
    try:
        caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
        snap = {
            "caso": caso,
            "mensagens": db.table("mensagens").select("*").eq("caso_id", caso_id).execute().data,
            "documentos": db.table("documentos").select("*").eq("caso_id", caso_id).execute().data,
            "eventos": db.table("eventos").select("*").eq("caso_id", caso_id).execute().data,
        }
        rotulo = (caso.get("clientes") or {}).get("nome") or caso_id[:8]
        db.table("lixeira").insert({"caso_id": caso_id, "rotulo": rotulo, "dados": snap}).execute()
    except Exception:
        pass  # se a lixeira não existir ainda, não bloqueia a exclusão
    # 2) Apaga das tabelas operacionais
    for t in ("mensagens", "documentos", "eventos", "protocolos"):
        try:
            db.table(t).delete().eq("caso_id", caso_id).execute()
        except Exception:
            pass
    db.table("casos").delete().eq("id", caso_id).execute()
    return {"ok": True, "excluido": caso_id, "backup": "lixeira (6 meses)"}


@app.get("/api/v1/lixeira")
def listar_lixeira():
    return get_db().table("lixeira").select("id,caso_id,rotulo,excluido_em,expira_em") \
        .order("excluido_em", desc=True).limit(200).execute().data


@app.post("/api/v1/lixeira/{item_id}/restaurar")
def restaurar_lixeira(item_id: str):
    """Restaura um caso excluído a partir do backup da lixeira."""
    db = get_db()
    item = db.table("lixeira").select("*").eq("id", item_id).single().execute().data
    snap = item.get("dados") or {}
    caso = dict(snap.get("caso") or {})
    caso.pop("clientes", None)  # campo aninhado da query, não é coluna
    if not caso.get("id"):
        raise HTTPException(400, "Backup inválido.")
    db.table("casos").upsert(caso).execute()
    for m in snap.get("mensagens", []):
        m2 = {k: v for k, v in m.items() if k != "id"}
        try: db.table("mensagens").insert(m2).execute()
        except Exception: pass
    for d in snap.get("documentos", []):
        d2 = {k: v for k, v in d.items() if k != "id"}
        try: db.table("documentos").insert(d2).execute()
        except Exception: pass
    db.table("lixeira").delete().eq("id", item_id).execute()
    return {"ok": True, "restaurado": caso.get("id")}


@app.patch("/api/v1/casos/{caso_id}")
def editar_caso(caso_id: str, body: EditarCaso):
    campos = {k: v for k, v in body.model_dump().items() if v is not None}
    if "honorarios" in campos:
        campos["honorarios_valor"] = campos.pop("honorarios")
    if campos:
        campos["atualizado_em"] = datetime.now(_tz.utc).isoformat()
        get_db().table("casos").update(campos).eq("id", caso_id).execute()
    return {"ok": True}


@app.post("/api/v1/casos/{caso_id}/nota")
def add_nota(caso_id: str, body: NotaBody):
    get_db().table("mensagens").insert({
        "caso_id": caso_id, "canal": "CRM", "autor": "HUMANO", "conteudo": body.texto,
    }).execute()
    return {"ok": True}


@app.post("/api/v1/casos/{caso_id}/documentos")
def add_documento_link(caso_id: str, body: DocLink):
    get_db().table("documentos").insert({
        "caso_id": caso_id, "tipo": body.tipo or "LINK",
        "storage_path": body.url, "observacao": body.nome, "status": "RECEBIDO",
    }).execute()
    return {"ok": True}


@app.post("/api/v1/casos/{caso_id}/documentos/upload")
async def upload_documento(caso_id: str, arquivo: UploadFile = File(...)):
    import re, uuid
    s = get_settings()
    db = get_db()
    conteudo = await arquivo.read()
    nome_orig = arquivo.filename or "arquivo"
    base = nome_orig.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    # storage não aceita espaços/acentos na chave -> troca por "_"
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base) or "arquivo"
    path = f"{caso_id}/{uuid.uuid4().hex}_{safe}"   # chave única e válida
    try:
        db.storage.from_(s.bucket_documentos).upload(
            path, conteudo,
            {"content-type": arquivo.content_type or "application/octet-stream", "upsert": "true"},
        )
    except Exception as e:
        raise HTTPException(500, f"Falha no upload de '{arquivo.filename}': {e}")
    db.table("documentos").insert({
        "caso_id": caso_id, "tipo": "UPLOAD", "storage_path": path,
        "observacao": arquivo.filename, "status": "RECEBIDO",
    }).execute()
    return {"ok": True, "path": path}


@app.get("/api/v1/documentos/{doc_id}/url")
def url_documento(doc_id: str):
    """Gera link temporário para abrir um documento salvo no storage privado."""
    s = get_settings()
    db = get_db()
    d = db.table("documentos").select("storage_path").eq("id", doc_id).single().execute().data
    sp = d.get("storage_path") or ""
    if sp.startswith("http"):
        return {"url": sp}
    try:
        res = db.storage.from_(s.bucket_documentos).create_signed_url(sp, 3600)
        url = res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
        return {"url": url}
    except Exception as e:
        raise HTTPException(500, f"Falha ao gerar link: {e}")


# ================================================================
#  DOCUMENTOS PARA ASSINATURA — gerar, revisar, aprovar, enviar
#
#  Caminho: CRM "Gerar documento" → agente monta o .docx a partir do
#  modelo oficial → fica EM_REVISAO → advogado ajusta e APROVA →
#  ENVIADO ao ZapSign → cliente assina por e-mail/WhatsApp/painel →
#  webhook devolve ASSINADO e arquiva o PDF na pasta do caso.
# ================================================================
TIPOS_DOCUMENTO = ["CONTRATO", "PROCURACAO", "HIPOSSUFICIENCIA", "OUTRO"]


class GerarDocumento(BaseModel):
    tipo: str
    titulo: str | None = None
    instrucao: str | None = None     # orientação do advogado para o agente


class PrestacaoBody(BaseModel):
    valor_recebido: float = 0
    honorarios_contratuais: float = 0
    honorarios_sucumbenciais: float = 0
    despesas: float = 0
    repasse_cliente: float | None = None
    forma_repasse: str | None = None
    resultado: str | None = None
    observacoes: str | None = None


@app.get("/api/v1/casos/{caso_id}/historico")
def historico_do_caso(caso_id: str):
    """Linha do tempo do atendimento, do primeiro contato até agora."""
    return avisos.montar_historico(caso_id)


@app.post("/api/v1/casos/{caso_id}/prestacao-contas")
def enviar_prestacao_contas(caso_id: str, body: PrestacaoBody):
    """Encerra o atendimento: envia ao cliente, no MESMO fio de e-mail,
    a prestação de contas com o demonstrativo financeiro e o histórico
    completo do que foi feito, do início ao fim."""
    try:
        return avisos.prestacao_de_contas(caso_id, body.model_dump())
    except Exception as e:
        raise HTTPException(500, f"Não foi possível enviar a prestação de contas: {e}")


@app.get("/api/v1/casos/{caso_id}/prestacoes-contas")
def listar_prestacoes(caso_id: str):
    try:
        return get_db().table("prestacoes_contas").select("*") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        return []


@app.post("/api/v1/email/ler-respostas")
def ler_respostas_email():
    """Lê a caixa do escritório agora e arquiva as vias assinadas que
    chegaram por e-mail (roda sozinha a cada 10 minutos)."""
    return email_entrada.ler_respostas()


@app.get("/api/v1/cep/{cep}")
def buscar_cep(cep: str):
    """Preenchimento automático de endereço pelo CEP (ViaCEP).

    Fica no backend, e não no navegador, por dois motivos: evita bloqueio de
    CORS/adblock no computador do usuário e permite que os agentes de
    atendimento também completem o endereço do cliente sozinhos.
    """
    import re as _re
    numeros = _re.sub(r"\D", "", cep or "")
    if len(numeros) != 8:
        raise HTTPException(400, "CEP deve ter 8 dígitos.")
    try:
        r = httpx.get(f"https://viacep.com.br/ws/{numeros}/json/", timeout=10)
        r.raise_for_status()
        d = r.json()
    except Exception:
        raise HTTPException(503, "Serviço de CEP indisponível no momento.")
    if d.get("erro"):
        raise HTTPException(404, "CEP não encontrado.")
    return {
        "cep": f"{numeros[:5]}-{numeros[5:]}",
        "endereco_rua": d.get("logradouro") or "",
        "endereco_bairro": d.get("bairro") or "",
        "endereco_cidade": d.get("localidade") or "",
        "endereco_uf": (d.get("uf") or "").upper(),
        "complemento_sugerido": d.get("complemento") or "",
    }


@app.get("/api/v1/documentos-assinatura/tipos")
def tipos_documento():
    """Opções do menu 'Gerar documento'."""
    from .agentes.documentos import NOMES
    return [{"tipo": t, "nome": NOMES.get(t, t)} for t in TIPOS_DOCUMENTO]


@app.post("/api/v1/casos/{caso_id}/documentos-assinatura")
def gerar_documento(caso_id: str, body: GerarDocumento):
    """Gera o documento a partir do modelo do escritório. Nasce EM_REVISAO."""
    from .agentes import documentos as redator
    try:
        return redator.gerar(caso_id, body.tipo, body.titulo, body.instrucao)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível gerar o documento: {e}")


@app.post("/api/v1/casos/{caso_id}/documentos-assinatura/anexar")
async def anexar_documento_avulso(
    caso_id: str,
    arquivo: UploadFile = File(...),
    titulo: str | None = None,
):
    """'Outros': o escritório anexa um documento pronto (PDF ou Word) para
    seguir junto dos demais no mesmo envio ao cliente."""
    import re as _re, uuid
    from .core.db import registrar_evento
    s = get_settings()
    db = get_db()

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo vazio.")
    if len(conteudo) > 25 * 1024 * 1024:
        raise HTTPException(400, "Arquivo acima de 25 MB.")

    base = (arquivo.filename or "documento").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe = _re.sub(r"[^A-Za-z0-9._-]", "_", base) or "documento"
    path = f"{caso_id}/gerados/{uuid.uuid4().hex}_{safe}"
    try:
        db.storage.from_(s.bucket_documentos).upload(
            path, conteudo,
            {"content-type": arquivo.content_type or "application/octet-stream",
             "upsert": "true"},
        )
    except Exception as e:
        raise HTTPException(500, f"Falha ao anexar: {e}")

    linha = {
        "caso_id": caso_id, "tipo": "OUTRO",
        "titulo": (titulo or base.rsplit(".", 1)[0])[:120],
        "status": "EM_REVISAO", "storage_path": path, "gerado_por": "HUMANO",
    }
    if base.lower().endswith(".pdf"):
        linha["pdf_path"] = path           # já é PDF: vai direto assim
    doc = db.table("documentos_assinatura").insert(linha).execute().data[0]
    registrar_evento(caso_id, "DOCUMENTO_ANEXADO",
                     {"documento_id": doc["id"], "arquivo": base})
    return {"ok": True, "documento": doc}


class LoteEnvio(BaseModel):
    documento_ids: list[str]


@app.post("/api/v1/casos/{caso_id}/documentos-assinatura/enviar-lote")
def enviar_lote_ao_cliente(caso_id: str, body: LoteEnvio):
    """Envia VÁRIOS documentos ao cliente em um único e-mail — contrato,
    procuração, declaração e o que mais for anexado seguem juntos, cada um
    em PDF. O cliente devolve tudo assinado de uma vez, respondendo o
    próprio e-mail ou pelo painel."""
    import uuid as _uuid
    from .core.db import registrar_evento
    from .agentes import documentos as redator
    db = get_db()
    if not body.documento_ids:
        raise HTTPException(400, "Selecione ao menos um documento.")

    docs = db.table("documentos_assinatura").select("*") \
             .in_("id", body.documento_ids).eq("caso_id", caso_id).execute().data or []
    docs = [d for d in docs if d["status"] != "ASSINADO"]
    if not docs:
        raise HTTPException(400, "Nenhum documento pendente entre os selecionados.")

    s = get_settings()
    anexos, falhas, titulos = [], [], []
    usados: dict[str, int] = {}
    for d in docs:
        try:
            nome, conteudo, mime = redator.preparar_anexo(d)
            # dois documentos com o mesmo nome se atropelam na pasta de
            # downloads do cliente — numeramos o repetido
            chave = nome.lower()
            if chave in usados:
                usados[chave] += 1
                raiz, _, ext = nome.rpartition(".")
                nome = f"{raiz} ({usados[chave]}).{ext}"
            else:
                usados[chave] = 1
            anexos.append((nome, conteudo, mime))
            titulos.append(d["titulo"])
        except Exception as e:
            falhas.append(f"{d['titulo']}: {e}")

    if not anexos:
        raise HTTPException(500, "Nenhum documento pôde ser preparado: "
                                 + "; ".join(falhas))
    # não deixamos sair um envio incompleto sem o escritório saber
    if falhas:
        raise HTTPException(
            409, "Estes documentos não puderam ser preparados: "
                 + "; ".join(falhas)
                 + ". Corrija ou desmarque para enviar os demais.")

    # uma referência só para o lote inteiro
    token = email_entrada.novo_token()
    lote = str(_uuid.uuid4())
    agora = datetime.now(_tz.utc).isoformat()
    for d in docs:
        db.table("documentos_assinatura").update({
            "status": "ENVIADO", "enviado_em": agora, "atualizado_em": agora,
            "email_token": token, "lote_id": lote,
            "aprovado_por": s.advogado, "aprovado_em": agora,
        }).eq("id", d["id"]).execute()

    lista = "\n".join(f"   {i}. {t}" for i, t in enumerate(titulos, 1))
    instrucao = (
        f"Preparamos os documentos do seu processo. Seguem {len(anexos)} "
        f"arquivos em PDF, anexos a este e-mail:\n\n{lista}\n\n"
        "Assine TODOS e devolva do jeito que for mais fácil para você:\n\n"
        "• PELO E-MAIL — RESPONDA esta mensagem com os documentos assinados "
        "em anexo (PDF, Word ou foto). Não apague o assunto: é por ele que "
        "identificamos o seu processo.\n\n"
        "• PELA PLATAFORMA — entre no seu painel, baixe cada documento, "
        "assine e use ENVIAR ASSINADO.\n\n"
        "Pode imprimir e assinar à caneta ou assinar digitalmente no celular. "
        "Assim que recebermos, seguimos com o seu processo."
    )
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "PORTAL", "autor": "HUMANO",
            "conteudo": f"📄 {len(anexos)} documentos disponíveis para assinatura."
                        f"\n\n{instrucao}",
        }).execute()
    except Exception:
        pass

    envio = {}
    try:
        envio = avisos.notificar(
            caso_id, "CONTRATO",
            f"{len(anexos)} documentos para assinatura", instrucao,
            anexos=anexos,
            assunto_extra=f" (ref. {email_entrada.referencia(token)})",
        )
    except Exception as e:
        envio = {"erros": [str(e)]}

    registrar_evento(caso_id, "DOCUMENTOS_ENVIADOS_LOTE",
                     {"quantidade": len(anexos), "titulos": titulos,
                      "lote_id": lote, "falhas": falhas})
    return {"ok": True, "enviados": titulos, "quantidade": len(anexos),
            "falhas": falhas, **envio}


@app.get("/api/v1/casos/{caso_id}/documentos-assinatura")
def listar_documentos_assinatura(caso_id: str):
    from .agentes import honorarios as hon
    db = get_db()
    try:
        docs = db.table("documentos_assinatura").select("*") \
            .eq("caso_id", caso_id).neq("status", "SUBSTITUIDO") \
            .order("criado_em", desc=True).execute().data or []
    except Exception:
        return []
    try:
        caso = db.table("casos").select("hon_atualizado_em") \
                 .eq("id", caso_id).single().execute().data or {}
        for d in docs:
            d["honorarios_desatualizado"] = hon.documento_desatualizado(d, caso)
    except Exception:
        pass
    return docs


# ── Honorários do caso ───────────────────────────────────────────
class HonorariosEntrada(BaseModel):
    hon_percentual: float | None = None
    hon_salarios_minimos: float | None = None
    hon_valor_fixo: float | None = None
    hon_entrada: float | None = None
    hon_parcelas: int | None = None
    hon_parcela_valor: float | None = None
    hon_vencimento: str | None = None
    hon_forma_pagamento: str | None = None
    hon_observacao: str | None = None
    justificativa: str | None = None
    origem: str | None = None


@app.get("/api/v1/casos/{caso_id}/honorarios")
def ver_honorarios(caso_id: str):
    from .agentes import honorarios as hon
    db = get_db()
    caso = db.table("casos").select("*").eq("id", caso_id).single().execute().data
    if not caso:
        raise HTTPException(404, "Caso não encontrado.")
    try:
        hist = db.table("honorarios_historico").select("*").eq("caso_id", caso_id) \
                 .order("criado_em", desc=True).limit(10).execute().data or []
    except Exception:
        hist = []
    return {"valores": {c: caso.get(c) for c in hon.CAMPOS},
            "atualizado_em": caso.get("hon_atualizado_em"),
            "origem": caso.get("hon_origem"),
            "resumo": hon.resumo_curto(caso),
            "clausula": hon.clausula_pagamento(caso),
            "historico": hist}


@app.put("/api/v1/casos/{caso_id}/honorarios")
def gravar_honorarios(caso_id: str, body: HonorariosEntrada):
    """Grava o combinado e acerta os documentos que ainda não saíram."""
    from .agentes import honorarios as hon
    valores = body.model_dump(exclude={"justificativa", "origem"})
    try:
        caso = hon.salvar(caso_id, valores,
                          autor=get_settings().advogado,
                          origem=(body.origem or "ESCRITORIO"),
                          justificativa=body.justificativa or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível gravar os honorários: {e}")
    return {"ok": True, "resumo": hon.resumo_curto(caso),
            "clausula": hon.clausula_pagamento(caso),
            "documentos": caso.get("_refeitos") or {}}


# ── Trava de peticionamento e override ───────────────────────────
def _perfil_do_token(authorization: str | None) -> dict:
    """Quem é o usuário e qual o papel dele.

    O papel NUNCA vem do corpo da requisição nem de um header: vem do
    token validado contra o Supabase e do que está gravado em `perfis`.
    O frontend esconder o botão é conveniência; a trava é aqui."""
    user = _usuario_do_token(authorization)
    try:
        perfil = get_db().table("perfis").select("papel,permissoes,email") \
                   .eq("id", user["id"]).maybe_single().execute().data or {}
    except Exception:
        perfil = {}
    return {
        "id": user["id"],
        "email": perfil.get("email") or user.get("email"),
        "papel": perfil.get("papel") or "CLIENTE",
        "permissoes": perfil.get("permissoes") or [],
    }


def _pode_forcar(perfil: dict) -> bool:
    return (perfil.get("papel") == "ADMIN"
            or "override_peticao" in (perfil.get("permissoes") or []))


@app.get("/api/v1/meu-perfil")
def meu_perfil(authorization: str | None = Header(default=None)):
    """O frontend usa isto para decidir se mostra o botão de forçar."""
    p = _perfil_do_token(authorization)
    return {**p, "pode_forcar_peticao": _pode_forcar(p)}


class ValidarPeticionamento(BaseModel):
    caso_id: str
    tipo_peticao: str
    override: bool = False
    justificativa: str | None = None


@app.post("/api/v1/validar-peticionamento")
def validar_peticionamento(body: ValidarPeticionamento,
                           authorization: str | None = Header(default=None)):
    """Confere se a peça pode ser protocolada.

    Sem override: Regra A (inicial → kit mínimo de documentos) ou Regra B
    (demais peças → compatibilidade com o último andamento).

    Com override: só ADMIN, ou quem tenha a permissão `override_peticao`,
    passa por cima da trava — e a decisão fica registrada com o motivo que
    foi ignorado e a justificativa de quem decidiu."""
    from .agentes import controller_peticao as trava
    perfil = _perfil_do_token(authorization)

    if perfil["papel"] == "CLIENTE":
        raise HTTPException(403, "Apenas a equipe do escritório pode peticionar.")

    # a validação roda sempre — inclusive no override, porque é o parecer
    # dela que fica registrado como o que foi ignorado
    try:
        parecer = trava.validar(body.caso_id, body.tipo_peticao, perfil["email"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível validar: {e}")

    if parecer["aprovado"]:
        return {**parecer, "override_usado": False,
                "pode_forcar": _pode_forcar(perfil)}

    if not body.override:
        # travado: devolve 200 com aprovado=false para a interface explicar
        return {**parecer, "override_usado": False,
                "pode_forcar": _pode_forcar(perfil)}

    if not _pode_forcar(perfil):
        raise HTTPException(
            403, "Somente o administrador pode liberar peticionamento com a "
                 "validação reprovada. Fale com o Dr. Fábio Cunha.")

    trava.registrar_override(
        body.caso_id, body.tipo_peticao, parecer.get("motivo", ""),
        body.justificativa or "", perfil, parecer.get("regra", ""))
    return {**parecer, "aprovado": True, "override_usado": True,
            "pode_forcar": True,
            "motivo": "Liberado por decisão do administrador. "
                      f"A validação havia apontado: {parecer.get('motivo', '')}"}


@app.get("/api/v1/casos/{caso_id}/overrides")
def listar_overrides(caso_id: str):
    try:
        return get_db().table("overrides_peticionamento").select("*") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        return []


# ── Atendimento telepresencial ───────────────────────────────────
class AbrirAtendimento(BaseModel):
    horas: int = 3


@app.post("/api/v1/casos/{caso_id}/atendimentos")
def abrir_atendimento(caso_id: str, body: AbrirAtendimento):
    """Abre a sala e devolve o acesso do advogado + o link do cliente."""
    from .agentes import atendimento
    from .integracoes.daily import DailyIndisponivel
    try:
        return atendimento.abrir(caso_id, max(1, min(body.horas, 6)))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except DailyIndisponivel as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível abrir o atendimento: {e}")


@app.get("/api/v1/casos/{caso_id}/atendimentos")
def listar_atendimentos(caso_id: str):
    try:
        return get_db().table("atendimentos").select(
            "id,status,sala_url,iniciado_em,encerrado_em,duracao_segundos,"
            "consentimento_em,audio_path,transcricao,transcrito_em,erro,criado_em"
        ).eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        return []


@app.get("/api/v1/atendimentos/{atendimento_id}/entrada")
def tela_de_entrada(atendimento_id: str):
    """O que o cliente vê antes de entrar: o texto do consentimento."""
    from .agentes import atendimento
    try:
        return atendimento.para_o_cliente(atendimento_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


class EntrarNaSala(BaseModel):
    nome: str | None = None
    aceita_gravacao: bool = False
    # verdadeiro só quando o termo foi aberto, rolado até o fim e aceito
    leu_termo: bool = False


@app.post("/api/v1/atendimentos/{atendimento_id}/entrar")
def entrar_na_sala(atendimento_id: str, body: EntrarNaSala, request: Request):
    """Registra a decisão sobre a gravação e devolve o token de entrada.

    Recusar não impede o atendimento — só desliga a gravação."""
    from .agentes import atendimento
    from .integracoes.daily import DailyIndisponivel
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() \
        or (request.client.host if request.client else None)
    try:
        return atendimento.entrar(atendimento_id, body.nome or "Cliente",
                                  bool(body.aceita_gravacao), ip,
                                  bool(body.leu_termo))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except DailyIndisponivel as e:
        raise HTTPException(503, str(e))


class AutorizarDurante(BaseModel):
    leu_termo: bool = False


@app.post("/api/v1/atendimentos/{atendimento_id}/autorizar-gravacao")
def autorizar_gravacao(atendimento_id: str, body: AutorizarDurante,
                       request: Request):
    """O cliente entrou sem autorizar e mudou de ideia durante a conversa.

    Mesma exigência de leitura do termo; muda só o momento."""
    from .agentes import atendimento
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() \
        or (request.client.host if request.client else None)
    try:
        return atendimento.autorizar_durante(atendimento_id, ip,
                                             bool(body.leu_termo))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível registrar: {e}")


@app.get("/api/v1/atendimentos/{atendimento_id}/pode-gravar")
def atendimento_pode_gravar(atendimento_id: str):
    from .agentes import atendimento
    return atendimento.pode_gravar(atendimento_id)


class EncerrarAtendimento(BaseModel):
    observacao: str | None = None


@app.post("/api/v1/atendimentos/{atendimento_id}/encerrar")
def encerrar_atendimento(atendimento_id: str, body: EncerrarAtendimento):
    from .agentes import atendimento
    try:
        return atendimento.encerrar(atendimento_id, body.observacao)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/v1/atendimentos/{atendimento_id}/transcrever")
def transcrever_atendimento(atendimento_id: str):
    """Refaz a transcrição na mão, quando a automática falhar."""
    from .agentes import atendimento
    try:
        return atendimento.transcrever(atendimento_id)
    except Exception as e:
        raise HTTPException(500, f"Não foi possível transcrever: {e}")


@app.post("/api/v1/atendimentos/webhook")
async def atendimento_webhook(request: Request, tarefas: BackgroundTasks):
    """Recebe do Daily o aviso de gravação pronta.

    Dois cuidados que o Daily impõe e que são fáceis de errar:

    1. ASSINATURA. O segredo é guardado em base64; a assinatura é o
       HMAC-SHA256 de `timestamp + "." + corpo`, com a chave decodificada,
       e vem em base64 no header X-Webhook-Signature. Sem conferir isso,
       qualquer um poderia postar aqui e injetar áudio no acervo.

    2. RESPONDER RÁPIDO. Baixar o áudio e transcrever leva minutos; se
       demorarmos, o Daily marca o endpoint como defeituoso e para de
       entregar. Então respondemos 200 na hora e processamos em segundo
       plano — inclusive no ping de verificação, que vem sem corpo útil.
    """
    import base64
    import hashlib
    import hmac as _hmac
    from .agentes import atendimento
    s = get_settings()
    corpo = await request.body()

    if s.daily_webhook_segredo:
        ts = request.headers.get("x-webhook-timestamp", "")
        assinatura = request.headers.get("x-webhook-signature", "")
        if ts and assinatura:
            try:
                chave = base64.b64decode(s.daily_webhook_segredo)
            except Exception:
                chave = s.daily_webhook_segredo.encode()
            esperado = base64.b64encode(_hmac.new(
                chave, f"{ts}.".encode() + corpo, hashlib.sha256).digest()).decode()
            if not _hmac.compare_digest(esperado, assinatura.strip()):
                raise HTTPException(401, "Assinatura do webhook inválida.")

    try:
        payload = json.loads(corpo or b"{}")
    except Exception:
        return {"ok": True, "ignorado": "sem payload"}

    tipo = (payload.get("type") or payload.get("event") or "").lower()
    if not tipo:
        return {"ok": True, "verificacao": True}   # ping de validação do Daily

    tarefas.add_task(atendimento.processar_webhook, payload)
    return {"ok": True, "recebido": tipo}


# ── Peticionamento: minuta com tags + injeção de precedentes ─────
class PeticaoEntrada(BaseModel):
    markdown: str | None = None
    titulo: str | None = None
    tribunal: str | None = None          # TJRO | TJSC — define a prioridade
    instrucao: str | None = None         # usada quando a plataforma redige


@app.post("/api/v1/casos/{caso_id}/peticoes")
def criar_peticao(caso_id: str, body: PeticaoEntrada):
    """Entra na esteira de peticionamento por dois caminhos: o advogado cola
    a minuta pronta (com as tags) ou pede que a plataforma redija."""
    from .core.db import registrar_evento
    from .agentes import redator_peticao
    db = get_db()
    if body.markdown and body.markdown.strip():
        base, origem = body.markdown, "COLADA"
    else:
        try:
            base = redator_peticao.redigir(caso_id, body.instrucao)
            origem = "REDIGIDA"
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"Não foi possível redigir a minuta: {e}")

    linha = db.table("peticoes").insert({
        "caso_id": caso_id, "titulo": body.titulo or "Petição inicial",
        "tribunal": (body.tribunal or "").upper() or None,
        "markdown_base": base, "origem": origem,
    }).execute().data[0]
    registrar_evento(caso_id, "PETICAO_CRIADA",
                     {"peticao_id": linha["id"], "origem": origem})
    from .agentes import precedentes
    return {"ok": True, "peticao": linha,
            "tags": precedentes.varrer_tags(base)}


@app.get("/api/v1/casos/{caso_id}/peticoes")
def listar_peticoes(caso_id: str):
    try:
        return get_db().table("peticoes").select("*").eq("caso_id", caso_id) \
            .order("criado_em", desc=True).execute().data
    except Exception:
        return []


@app.post("/api/v1/peticoes/{peticao_id}/precedentes")
def injetar_precedentes(peticao_id: str):
    """Troca cada tag por julgado real do banco. Tag sem julgado aderente é
    removida — a peça nunca sai com citação inventada."""
    from .agentes import precedentes
    try:
        return precedentes.injetar(peticao_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível injetar os precedentes: {e}")


@app.post("/api/v1/precedentes/sincronizar")
def sincronizar_precedentes():
    """Achata as ementas do banco de teses na tabela de busca por tema."""
    from .agentes import precedentes
    try:
        return precedentes.sincronizar_do_banco_de_teses()
    except Exception as e:
        raise HTTPException(500, f"Falha ao sincronizar: {e}")


@app.get("/api/v1/precedentes")
def listar_precedentes(tribunal: str | None = None, grupo: str | None = None,
                       tema: str | None = None, limite: int = 20):
    from .integracoes import jurisprudencia_api
    if tema:
        return jurisprudencia_api.buscar(tema, tribunal, grupo, limite)
    db = get_db()
    q = db.table("precedentes").select(
        "id,tribunal,tipo,numero,relator,data_julgamento,tema,grupo,fonte,url")
    if tribunal:
        q = q.eq("tribunal", tribunal.upper())
    if grupo:
        q = q.eq("grupo", grupo)
    try:
        return q.order("criado_em", desc=True).limit(limite).execute().data
    except Exception:
        return []


class PrazoFatal(BaseModel):
    prazo_fatal: str | None = None
    prazo_descricao: str | None = None


@app.put("/api/v1/casos/{caso_id}/prazo")
def gravar_prazo(caso_id: str, body: PrazoFatal):
    """Prazo real do caso (prescrição, decadência, prazo processual).

    É o que autoriza a cobrança do dia 7 a falar em risco ao direito. Sem
    prazo cadastrado, a cobrança usa urgência operacional — não afirma ao
    cliente algo que não está acontecendo."""
    from .core.db import registrar_evento
    try:
        get_db().table("casos").update({
            "prazo_fatal": body.prazo_fatal or None,
            "prazo_descricao": body.prazo_descricao or None,
            "atualizado_em": datetime.now(_tz.utc).isoformat(),
        }).eq("id", caso_id).execute()
    except Exception as e:
        raise HTTPException(500, f"Não foi possível gravar o prazo: {e}")
    registrar_evento(caso_id, "PRAZO_CADASTRADO",
                     {"prazo": body.prazo_fatal, "descricao": body.prazo_descricao})
    return {"ok": True}


@app.post("/api/v1/pendencias/rodar")
def rodar_regua():
    """Roda a régua de cobrança agora (o automático é diário, de manhã)."""
    from .agentes import pendencias
    try:
        return pendencias.rodar()
    except Exception as e:
        raise HTTPException(500, f"Não foi possível rodar a régua: {e}")


@app.post("/api/v1/documentos-assinatura/{doc_id}/revisar")
def revisar_documento(doc_id: str):
    """O agente confere o documento contra o cadastro e a conversa, e diz
    se pode ir para assinatura."""
    from .agentes import revisor
    try:
        return revisor.revisar(doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível revisar: {e}")


@app.post("/api/v1/documentos-assinatura/{doc_id}/atualizar")
def atualizar_documento(doc_id: str):
    """Refaz o documento por inteiro com os dados atuais."""
    from .agentes import revisor
    try:
        return revisor.atualizar_na_integra(doc_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível atualizar: {e}")


@app.post("/api/v1/casos/{caso_id}/honorarios/ler-conversa")
def ler_honorarios_da_conversa(caso_id: str):
    """O agente lê a conversa com o cliente e PROPÕE os valores combinados.
    Quem aplica é o escritório — valor de honorários não entra em contrato
    por conta própria."""
    from .agentes import honorarios as hon
    try:
        return hon.ler_da_conversa(caso_id)
    except Exception as e:
        raise HTTPException(500, f"Não foi possível ler a conversa: {e}")


@app.get("/api/v1/casos/{caso_id}/qualificacao")
def conferir_qualificacao(caso_id: str):
    """Diz o que falta no cadastro para os documentos poderem ser gerados."""
    from .agentes.documentos import campos_faltando, montar_qualificacao, comarca_do_cliente
    caso = get_db().table("casos").select("clientes(*)").eq("id", caso_id) \
             .single().execute().data
    cli = caso.get("clientes") or {}
    faltando = campos_faltando(cli)
    return {"completo": not faltando, "faltando": faltando,
            "qualificacao": montar_qualificacao(cli) if not faltando else None,
            "foro": comarca_do_cliente(cli)}


class AjusteDocumento(BaseModel):
    titulo: str | None = None
    qualificacao: str | None = None
    objeto: dict | None = None
    local_data: str | None = None
    foro: str | None = None
    tipo_acao: str | None = None
    observacoes: str | None = None


@app.patch("/api/v1/documentos-assinatura/{doc_id}")
def ajustar_documento(doc_id: str, body: AjusteDocumento):
    """Ajuste humano: refaz o .docx com o texto corrigido pelo advogado."""
    from .agentes import documentos as redator
    try:
        return redator.regravar(doc_id, body.model_dump())
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível ajustar: {e}")


@app.post("/api/v1/documentos-assinatura/{doc_id}/aprovar")
def aprovar_documento(doc_id: str, enviar: bool = False):
    """Advogado aprova. Com enviar=true já segue para assinatura."""
    from .core.db import registrar_evento
    db = get_db()
    d = db.table("documentos_assinatura").select("*").eq("id", doc_id) \
          .maybe_single().execute().data
    if not d:
        raise HTTPException(404, "Documento não encontrado.")
    if d["status"] in ("ENVIADO", "ASSINADO"):
        return {"ok": True, "info": f"Documento já está {d['status']}."}
    agora = datetime.now(_tz.utc).isoformat()
    db.table("documentos_assinatura").update({
        "status": "APROVADO", "aprovado_por": get_settings().advogado,
        "aprovado_em": agora, "atualizado_em": agora,
    }).eq("id", doc_id).execute()
    registrar_evento(d["caso_id"], "DOCUMENTO_APROVADO", {"documento_id": doc_id})
    if enviar:
        return enviar_documento_assinatura(doc_id)
    return {"ok": True, "status": "APROVADO"}


@app.post("/api/v1/documentos-assinatura/{doc_id}/enviar")
def enviar_documento_assinatura(doc_id: str):
    """Sobe o documento aprovado para o ZapSign e manda o link ao cliente
    por e-mail, WhatsApp e pelo chat da plataforma."""
    try:
        return zapsign.enviar_documento(doc_id)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(502, f"Falha ao enviar para assinatura: {e}")


class ParagrafosBody(BaseModel):
    paragrafos: list[dict]


@app.get("/api/v1/documentos-assinatura/{doc_id}/conteudo")
def conteudo_documento(doc_id: str):
    """Texto do documento em parágrafos, para o editor abrir em nova aba."""
    from .agentes import documentos as redator
    try:
        return redator.ler_paragrafos(doc_id)
    except Exception as e:
        raise HTTPException(500, f"Não foi possível abrir o documento: {e}")


@app.put("/api/v1/documentos-assinatura/{doc_id}/conteudo")
def salvar_conteudo_documento(doc_id: str, body: ParagrafosBody):
    """Salva os ajustes feitos pelo advogado, mantendo a formatação do modelo."""
    from .agentes import documentos as redator
    try:
        return redator.gravar_paragrafos(doc_id, body.paragrafos)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(500, f"Não foi possível salvar: {e}")


@app.post("/api/v1/documentos-assinatura/{doc_id}/enviar-cliente")
def enviar_documento_ao_cliente(doc_id: str):
    """Manda o documento para o cliente assinar À MÃO e devolver pela
    plataforma: ele baixa, assina, e reenvia pelo próprio chat.

    (A assinatura digital automática existe no código, mas está desligada
    por decisão do escritório — será ligada mais adiante.)"""
    from .core.db import registrar_evento
    db = get_db()
    d = db.table("documentos_assinatura").select("*").eq("id", doc_id) \
          .maybe_single().execute().data
    if not d:
        raise HTTPException(404, "Documento não encontrado.")
    if d["status"] == "ASSINADO":
        return {"ok": True, "info": "Documento já assinado."}

    # o cliente recebe em PDF sempre que possível: preserva a formatação e
    # não se altera sem rastro. Documento anexado em 'Outros' (que já pode
    # vir em PDF, Word ou foto) segue pelo mesmo caminho.
    from .agentes import documentos as redator
    try:
        preparado = redator.preparar_anexo(d)
    except Exception as e:
        # sem anexo o e-mail não cumpre a função: o cliente não teria o que
        # baixar, assinar e devolver. Melhor falhar aqui do que enviar vazio.
        raise HTTPException(500, f"Não foi possível preparar o documento: {e}")
    anexo = [preparado]
    pdf_ok = preparado[0].lower().endswith(".pdf")

    # referência que viaja no assunto e permite devolver por e-mail
    token = d.get("email_token") or email_entrada.novo_token()
    try:
        db.table("documentos_assinatura").update({"email_token": token}) \
          .eq("id", doc_id).execute()
    except Exception:
        token = None

    agora = datetime.now(_tz.utc).isoformat()
    db.table("documentos_assinatura").update({
        "status": "ENVIADO", "enviado_em": agora, "atualizado_em": agora,
        "aprovado_por": get_settings().advogado, "aprovado_em": agora,
    }).eq("id", doc_id).execute()

    instrucao = (
        f"Preparamos o seu {d['titulo']}. O documento vai em PDF, anexo a este "
        f"e-mail, e também está disponível no seu painel.\n\n"
        "Assine e devolva do jeito que for mais fácil para você:\n\n"
        "• PELO E-MAIL — basta RESPONDER esta mensagem com o documento "
        "assinado em anexo (pode ser PDF, Word ou foto). Não apague o assunto: "
        "é por ele que identificamos o seu processo.\n\n"
        "• PELA PLATAFORMA — entre no seu painel, toque em BAIXAR DOCUMENTO, "
        "assine e use ENVIAR ASSINADO.\n\n"
        "Pode imprimir e assinar à caneta ou assinar digitalmente no próprio "
        "celular. Assim que recebermos, seguimos com o seu processo."
    )
    # entra na conversa do cliente
    try:
        db.table("mensagens").insert({
            "caso_id": d["caso_id"], "canal": "PORTAL", "autor": "HUMANO",
            "conteudo": f"📄 {d['titulo']} disponível para assinatura.\n\n{instrucao}",
        }).execute()
    except Exception:
        pass
    # e sai por e-mail/WhatsApp com o link do painel
    envio = {}
    try:
        envio = avisos.notificar(
            d["caso_id"], "CONTRATO", f"{d['titulo']} para assinatura", instrucao,
            anexos=anexo,
            assunto_extra=f" (ref. {email_entrada.referencia(token)})" if token else "",
        )
    except Exception as e:
        envio = {"erros": [str(e)]}

    registrar_evento(d["caso_id"], "DOCUMENTO_ENVIADO_CLIENTE",
                     {"documento_id": doc_id, "tipo": d["tipo"], "pdf": pdf_ok})
    return {"ok": True, "status": "ENVIADO", "pdf": pdf_ok,
            "anexo": preparado[0], **envio}


@app.get("/api/v1/documentos-assinatura/{doc_id}/baixar")
def baixar_documento_assinatura(doc_id: str, formato: str = "docx"):
    from fastapi.responses import Response, RedirectResponse
    s = get_settings()
    db = get_db()
    d = db.table("documentos_assinatura").select("*").eq("id", doc_id) \
          .maybe_single().execute().data
    if not d:
        raise HTTPException(404, "Documento não encontrado.")
    if d.get("assinado_url"):                 # já assinado: devolve o que o cliente mandou
        alvo = d["assinado_url"]
        if str(alvo).startswith("http"):
            return RedirectResponse(alvo)
        try:
            conteudo = db.storage.from_(s.bucket_documentos).download(alvo)
        except Exception as e:
            raise HTTPException(500, f"Não foi possível baixar: {e}")
        return Response(
            content=conteudo, media_type="application/octet-stream",
            headers={"Content-Disposition":
                     _content_disposition(d["titulo"] + " (assinado)" + _sufixo(alvo))},
        )

    # PDF sob demanda (é o que o cliente recebe); .docx é a peça de trabalho
    if formato == "pdf":
        caminho = d.get("pdf_path")
        if not caminho:
            try:
                from .agentes import documentos as redator
                caminho = redator.gerar_pdf_do_documento(doc_id)["pdf_path"]
            except Exception as e:
                raise HTTPException(503, f"Não foi possível gerar o PDF: {e}")
        try:
            conteudo = db.storage.from_(s.bucket_documentos).download(caminho)
        except Exception as e:
            raise HTTPException(500, f"Não foi possível baixar: {e}")
        return Response(
            content=conteudo, media_type="application/pdf",
            headers={"Content-Disposition": _content_disposition(d["titulo"] + ".pdf")},
        )

    try:
        conteudo = db.storage.from_(s.bucket_documentos).download(d["storage_path"])
    except Exception as e:
        raise HTTPException(500, f"Não foi possível baixar: {e}")
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": _content_disposition(d["titulo"] + ".docx")},
    )


@app.delete("/api/v1/documentos-assinatura/{doc_id}")
def cancelar_documento_assinatura(doc_id: str):
    db = get_db()
    d = db.table("documentos_assinatura").select("status").eq("id", doc_id) \
          .maybe_single().execute().data
    if d and d["status"] == "ASSINADO":
        raise HTTPException(409, "Documento já assinado não pode ser excluído.")
    db.table("documentos_assinatura").delete().eq("id", doc_id).execute()
    return {"ok": True}


def _sufixo(caminho: str) -> str:
    """Extensão do arquivo (.pdf, .docx, .jpg...) a partir do caminho."""
    nome = str(caminho or "").split("/")[-1]
    return ("." + nome.rsplit(".", 1)[1]) if "." in nome else ""


def _content_disposition(nome: str) -> str:
    """Cabeçalho de download seguro: cabeçalhos HTTP só aceitam latin-1, e
    nomes com travessão, emoji ou acento quebram a resposta. Enviamos uma
    versão ASCII para compatibilidade e a versão UTF-8 (RFC 5987) para os
    navegadores modernos, que é a que o usuário vê."""
    import re, unicodedata
    from urllib.parse import quote
    limpo = re.sub(r'[\\/:*?"<>|]', "_", (nome or "arquivo")).strip() or "arquivo"
    ascii_nome = (unicodedata.normalize("NFKD", limpo)
                  .encode("ascii", "ignore").decode() or "arquivo")
    ascii_nome = re.sub(r"\s+", " ", ascii_nome).strip() or "arquivo"
    return (f'attachment; filename="{ascii_nome}"; '
            f"filename*=UTF-8''{quote(limpo)}")


def _nome_original(d: dict) -> str:
    """Nome de arquivo legível: prefere o que o cliente enviou; se não houver,
    limpa o prefixo aleatório da chave do storage."""
    import re
    nome = (d.get("observacao") or "").strip()
    if not nome or nome.startswith("http"):
        bruto = (d.get("storage_path") or "arquivo").split("/")[-1]
        nome = re.sub(r"^[0-9a-f]{32}_", "", bruto)   # remove o uuid do início
    return re.sub(r'[\\/:*?"<>|]', "_", nome) or "documento"


@app.get("/api/v1/documentos/{doc_id}/baixar")
def baixar_documento(doc_id: str):
    """Baixa o arquivo com o nome original, forçando o download (não abre
    no navegador). Vale para o que o cliente enviou e para o que o
    escritório subiu."""
    from fastapi.responses import Response, RedirectResponse
    import mimetypes
    s = get_settings()
    db = get_db()
    d = db.table("documentos").select("*").eq("id", doc_id).maybe_single().execute().data
    if not d:
        raise HTTPException(404, "Documento não encontrado.")
    sp = d.get("storage_path") or ""
    if sp.startswith("http"):                 # link de nuvem — só redireciona
        return RedirectResponse(sp)
    try:
        conteudo = db.storage.from_(s.bucket_documentos).download(sp)
    except Exception as e:
        raise HTTPException(500, f"Não foi possível baixar o arquivo: {e}")
    nome = _nome_original(d)
    tipo = mimetypes.guess_type(nome)[0] or "application/octet-stream"
    return Response(
        content=conteudo, media_type=tipo,
        headers={"Content-Disposition": _content_disposition(nome)},
    )


@app.delete("/api/v1/documentos/{doc_id}")
def excluir_documento(doc_id: str):
    """Remove o documento da pasta do cliente (storage) e do banco."""
    s = get_settings()
    db = get_db()
    d = db.table("documentos").select("storage_path").eq("id", doc_id).single().execute().data
    sp = (d or {}).get("storage_path") or ""
    if sp and not sp.startswith("http"):
        try:
            db.storage.from_(s.bucket_documentos).remove([sp])
        except Exception:
            pass
    db.table("documentos").delete().eq("id", doc_id).execute()
    return {"ok": True}


# ── SPRINT 1: Motor de Intimações e Processos (Escavador) ────────
class MonitorarBody(BaseModel):
    numero_processo: str | None = None
    oab: str | None = None
    tribunal: str | None = None
    caso_id: str | None = None


class StatusIntimacao(BaseModel):
    status: str


@app.post("/webhooks/escavador")
async def webhook_escavador(req: Request):
    """Recebe callbacks do Escavador. Insert rápido e idempotente, responde já."""
    from .integracoes import escavador
    try:
        payload = await req.json()
    except Exception:
        payload = {}
    return escavador.processar_webhook(payload)


@app.post("/api/v1/processos/monitorar")
def monitorar_processo(body: MonitorarBody):
    from .integracoes import escavador
    if not body.numero_processo and not body.oab:
        raise HTTPException(400, "Informe o número do processo ou a OAB.")
    return escavador.criar_monitoramento(body.numero_processo, body.oab, body.tribunal, body.caso_id)


@app.get("/api/v1/intimacoes")
def listar_intimacoes(status: str | None = None, tribunal: str | None = None,
                      q: str | None = None, limite: int = 200):
    qy = get_db().table("intimacoes").select("*")
    if status:
        qy = qy.eq("status", status)
    if tribunal:
        qy = qy.eq("tribunal", tribunal)
    if q:
        qy = qy.ilike("numero_processo", f"%{q}%")
    return qy.order("data_movimento", desc=True).limit(limite).execute().data


@app.patch("/api/v1/intimacoes/{intimacao_id}")
def atualizar_intimacao(intimacao_id: str, body: StatusIntimacao):
    if body.status not in ("A_RESOLVER", "RESOLVIDO", "PERDA_PRAZO"):
        raise HTTPException(400, "status inválido")
    get_db().table("intimacoes").update({"status": body.status, "lida": True}).eq("id", intimacao_id).execute()
    return {"ok": True}


@app.get("/api/v1/intimacoes/nao-lidas")
def intimacoes_nao_lidas():
    r = get_db().table("intimacoes").select("id").eq("lida", False).execute().data
    return {"total": len(r)}


@app.post("/api/v1/intimacoes/marcar-lidas")
def marcar_intimacoes_lidas():
    get_db().table("intimacoes").update({"lida": True}).eq("lida", False).execute()
    return {"ok": True}


@app.get("/api/v1/processos")
def listar_processos(tribunal: str | None = None, grupo: str | None = None,
                     estado: str | None = None, ano: str | None = None, limite: int = 200):
    rows = get_db().table("casos").select("*, clientes(nome,whatsapp,email)") \
        .order("atualizado_em", desc=True).limit(400).execute().data
    rows = [r for r in rows if r.get("numero_processo")]
    if tribunal:
        rows = [r for r in rows if r.get("tribunal") == tribunal]
    if grupo:
        rows = [r for r in rows if r.get("grupo") == grupo]
    if estado:
        rows = [r for r in rows if r.get("estado") == estado]
    if ano:
        rows = [r for r in rows if ano in (r.get("numero_processo") or "")]
    return rows[:limite]


@app.get("/api/v1/buscar")
def buscar_global(q: str):
    """Busca global da Top Bar: por nome, CPF/CNPJ ou número do processo."""
    db = get_db()
    termo = f"%{q}%"
    vistos: dict = {}
    try:
        for col in ("nome", "cpf_cnpj"):
            for c in db.table("clientes").select("id,nome,cpf_cnpj").ilike(col, termo).limit(15).execute().data:
                vistos[c["id"]] = c
    except Exception:
        pass
    casos = []
    if vistos:
        casos = db.table("casos").select("id,estado,grupo,numero_processo,cliente_id,clientes(nome,cpf_cnpj)") \
            .in_("cliente_id", list(vistos.keys())).limit(40).execute().data
    porproc = db.table("casos").select("id,estado,grupo,numero_processo,clientes(nome,cpf_cnpj)") \
        .ilike("numero_processo", termo).limit(20).execute().data
    # dedup por id de caso
    final = {c["id"]: c for c in (casos + porproc)}
    return {"casos": list(final.values())}


# ── SPRINT 2: Painel Administrativo e Financeiro ─────────────────
@app.get("/api/v1/admin/metricas")
def admin_metricas(periodo: str = "mes"):
    """KPIs do escritório a partir dos casos. periodo: dia|semana|mes|ano."""
    import re
    from datetime import datetime, timedelta, timezone as tz
    db = get_db()
    casos = db.table("casos").select(
        "estado,grupo,honorarios_valor,situacao,criado_em,pagamento_confirmado_em"
    ).limit(5000).execute().data

    agora = datetime.now(tz.utc)
    dias = {"dia": 1, "semana": 7, "mes": 30, "ano": 365}.get(periodo, 30)
    corte = agora - timedelta(days=dias)

    def _dt(s):
        try:
            return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        except Exception:
            return None

    no_periodo = [c for c in casos if (_dt(c.get("criado_em")) or agora) >= corte]

    por_nicho: dict = {}
    for c in no_periodo:
        g = c.get("grupo") or "OUTROS"
        por_nicho[g] = por_nicho.get(g, 0) + 1

    CONTRATACAO = {"LEAD", "QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO"}
    PRODUCAO = {"COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO", "APROVADO", "PROTOCOLO_RPA"}
    ATIVOS = {"PROTOCOLADO", "CONCLUIDO"}
    funil = {"contratacao": 0, "producao": 0, "ativos": 0}
    for c in casos:
        e = c.get("estado")
        if e in CONTRATACAO:
            funil["contratacao"] += 1
        elif e in PRODUCAO:
            funil["producao"] += 1
        elif e in ATIVOS:
            funil["ativos"] += 1

    def _valor(txt):
        t = str(txt or "")
        if "%" in t:
            return 0.0
        m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:[.,]\d{2})?)", t)
        if not m:
            return 0.0
        try:
            return float(m.group(1).replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    recebido = a_receber = 0.0
    vals = []
    for c in casos:
        v = _valor(c.get("honorarios_valor"))
        if v > 0:
            vals.append(v)
        if c.get("pagamento_confirmado_em"):
            recebido += v
        elif c.get("estado") in (CONTRATACAO | PRODUCAO | ATIVOS) - {"LEAD", "QUALIFICACAO", "PROPOSTA"}:
            a_receber += v
    ticket = round(sum(vals) / len(vals), 2) if vals else 0.0

    return {
        "periodo": periodo,
        "total_casos": len(no_periodo),
        "por_nicho": por_nicho,
        "funil": funil,
        "financeiro": {
            "recebido": round(recebido, 2), "a_receber": round(a_receber, 2),
            "ticket_medio": ticket, "qtd_valores": len(vals),
        },
    }


# ── Módulo de Custos (entradas/saídas + folha) ───────────────────
class Lancamento(BaseModel):
    tipo: str                      # ENTRADA | SAIDA
    categoria: str | None = None
    descricao: str | None = None
    valor: float = 0
    data: str | None = None
    recorrente: bool = False


class FolhaItem(BaseModel):
    nome: str
    cargo: str | None = None
    salario: float = 0


@app.get("/api/v1/financeiro/lancamentos")
def listar_lancamentos(limite: int = 300):
    return get_db().table("fin_lancamentos").select("*").order("data", desc=True).limit(limite).execute().data


@app.post("/api/v1/financeiro/lancamentos")
def criar_lancamento(body: Lancamento):
    if body.tipo not in ("ENTRADA", "SAIDA"):
        raise HTTPException(400, "tipo inválido (use ENTRADA ou SAIDA)")
    row = {"tipo": body.tipo, "categoria": body.categoria, "descricao": body.descricao,
           "valor": body.valor, "recorrente": body.recorrente}
    if body.data:
        row["data"] = body.data
    get_db().table("fin_lancamentos").insert(row).execute()
    return {"ok": True}


@app.delete("/api/v1/financeiro/lancamentos/{lanc_id}")
def excluir_lancamento(lanc_id: str):
    get_db().table("fin_lancamentos").delete().eq("id", lanc_id).execute()
    return {"ok": True}


@app.get("/api/v1/financeiro/folha")
def listar_folha():
    return get_db().table("fin_folha").select("*").eq("ativo", True).order("criado_em").execute().data


@app.post("/api/v1/financeiro/folha")
def criar_folha(body: FolhaItem):
    get_db().table("fin_folha").insert({"nome": body.nome, "cargo": body.cargo, "salario": body.salario}).execute()
    return {"ok": True}


@app.delete("/api/v1/financeiro/folha/{folha_id}")
def excluir_folha(folha_id: str):
    get_db().table("fin_folha").delete().eq("id", folha_id).execute()
    return {"ok": True}


@app.get("/api/v1/financeiro/resumo")
def financeiro_resumo(periodo: str = "mes"):
    from datetime import datetime, timedelta, date, timezone as tz
    db = get_db()
    lanc = db.table("fin_lancamentos").select("*").limit(5000).execute().data
    folha = db.table("fin_folha").select("salario").eq("ativo", True).execute().data
    dias = {"dia": 1, "semana": 7, "mes": 30, "ano": 365}.get(periodo, 30)
    corte = datetime.now(tz.utc).date() - timedelta(days=dias)

    def _d(s):
        try:
            return date.fromisoformat(str(s)[:10])
        except Exception:
            return None

    per = [l for l in lanc if (_d(l.get("data")) or corte) >= corte]
    entradas = sum(float(l.get("valor") or 0) for l in per if l.get("tipo") == "ENTRADA")
    saidas = sum(float(l.get("valor") or 0) for l in per if l.get("tipo") == "SAIDA")
    folha_mensal = sum(float(f.get("salario") or 0) for f in folha)
    recorrente_mensal = sum(float(l.get("valor") or 0) for l in lanc if l.get("tipo") == "SAIDA" and l.get("recorrente"))
    projecao_anual = (recorrente_mensal + folha_mensal) * 12
    return {
        "periodo": periodo, "entradas": round(entradas, 2), "saidas": round(saidas, 2),
        "saldo": round(entradas - saidas, 2), "folha_mensal": round(folha_mensal, 2),
        "projecao_anual_custos": round(projecao_anual, 2),
    }


# ── SPRINT 3: Agenda e Agente Controlador ────────────────────────
class Membro(BaseModel):
    nome: str
    especialidades: list[str] = []
    lider: bool = False
    google_email: str | None = None


class Prazo(BaseModel):
    titulo: str
    descricao: str | None = None
    data: str
    responsavel_id: str | None = None
    especialidade: str | None = None
    caso_id: str | None = None


class DistribuirPrazo(BaseModel):
    titulo: str
    descricao: str | None = None
    data: str
    especialidade: str | None = None
    caso_id: str | None = None


@app.get("/api/v1/membros")
def listar_membros():
    return get_db().table("membros_equipe").select("*").eq("ativo", True).order("nome").execute().data


@app.post("/api/v1/membros")
def criar_membro(body: Membro):
    get_db().table("membros_equipe").insert({
        "nome": body.nome, "especialidades": body.especialidades,
        "lider": body.lider, "google_email": body.google_email,
    }).execute()
    return {"ok": True}


@app.delete("/api/v1/membros/{membro_id}")
def excluir_membro(membro_id: str):
    get_db().table("membros_equipe").update({"ativo": False}).eq("id", membro_id).execute()
    return {"ok": True}


@app.get("/api/v1/prazos")
def listar_prazos(responsavel_id: str | None = None, inicio: str | None = None, fim: str | None = None):
    qy = get_db().table("prazos").select("*, membros_equipe(nome,lider)")
    if responsavel_id:
        qy = qy.eq("responsavel_id", responsavel_id)
    if inicio:
        qy = qy.gte("data", inicio)
    if fim:
        qy = qy.lte("data", fim)
    return qy.order("data").limit(1000).execute().data


@app.post("/api/v1/prazos")
def criar_prazo(body: Prazo):
    get_db().table("prazos").insert({
        "titulo": body.titulo, "descricao": body.descricao, "data": body.data,
        "responsavel_id": body.responsavel_id, "especialidade": body.especialidade,
        "caso_id": body.caso_id, "origem": "MANUAL",
    }).execute()
    return {"ok": True}


@app.patch("/api/v1/prazos/{prazo_id}")
def concluir_prazo(prazo_id: str, status: str = "CONCLUIDO"):
    get_db().table("prazos").update({"status": status}).eq("id", prazo_id).execute()
    return {"ok": True}


@app.delete("/api/v1/prazos/{prazo_id}")
def excluir_prazo(prazo_id: str):
    get_db().table("prazos").delete().eq("id", prazo_id).execute()
    return {"ok": True}


@app.post("/api/v1/prazos/distribuir")
def distribuir_prazo(body: DistribuirPrazo):
    """Agente Controlador: distribui o prazo ao membro APTO (por especialidade)
    com MENOR carga de prazos abertos na semana (balanceamento de carga)."""
    from datetime import datetime, timedelta, date, timezone as tz
    from .core.db import registrar_evento
    db = get_db()
    membros = db.table("membros_equipe").select("*").eq("ativo", True).execute().data
    if not membros:
        raise HTTPException(400, "Cadastre membros na equipe antes de distribuir.")
    aptos = [m for m in membros if not body.especialidade or body.especialidade in (m.get("especialidades") or [])]
    if not aptos:
        aptos = membros  # ninguém com a tag: considera todos

    hoje = datetime.now(tz.utc).date()
    ini = hoje - timedelta(days=hoje.weekday())
    fim = ini + timedelta(days=7)
    carga: dict = {}
    for p in db.table("prazos").select("responsavel_id,data,status").eq("status", "ABERTO").execute().data:
        try:
            dd = date.fromisoformat(str(p.get("data"))[:10])
        except Exception:
            dd = None
        if dd and ini <= dd < fim and p.get("responsavel_id"):
            carga[p["responsavel_id"]] = carga.get(p["responsavel_id"], 0) + 1

    escolhido = min(aptos, key=lambda m: carga.get(m["id"], 0))
    row = db.table("prazos").insert({
        "titulo": body.titulo, "descricao": body.descricao, "data": body.data,
        "responsavel_id": escolhido["id"], "especialidade": body.especialidade,
        "caso_id": body.caso_id, "origem": "CONTROLADORIA",
    }).execute().data[0]
    registrar_evento(body.caso_id, "PRAZO_DISTRIBUIDO",
                     {"responsavel": escolhido["nome"], "carga_semana": carga.get(escolhido["id"], 0)})
    # notificação ao responsável: ativa quando o WhatsApp/Cloud API estiver ligado
    return {"ok": True, "responsavel": escolhido["nome"], "prazo_id": row["id"],
            "carga_semana": carga.get(escolhido["id"], 0)}


# ── SPRINT 4: Assistente CEO (interno) e Relacionamento ──────────
class AssistenteMsg(BaseModel):
    conteudo: str
    historico: list[dict] = []


@app.post("/api/v1/assistente")
def assistente_ceo(body: AssistenteMsg):
    from .agentes import ceo
    return ceo.responder(body.historico, body.conteudo)


@app.post("/api/v1/relacionamento/aniversarios")
def disparar_aniversarios():
    """Disparo manual das felicitações de aniversário (o automático roda diário)."""
    from .agentes import relacionamento
    return relacionamento.parabenizar_aniversariantes()


# ── MÓDULO 1: Webhook do WhatsApp + Sessão (omnichannel) ─────────
@app.get("/api/whatsapp/webhook")
def whatsapp_verificar(request: Request):
    """Verificação inicial exigida pelo Meta (devolve o hub.challenge)."""
    from fastapi.responses import PlainTextResponse
    from .integracoes import whatsapp_omni
    p = request.query_params
    challenge = whatsapp_omni.verificar_webhook(
        p.get("hub.mode"), p.get("hub.verify_token"), p.get("hub.challenge")
    )
    if challenge is None:
        raise HTTPException(403, "Token de verificação inválido")
    return PlainTextResponse(str(challenge))


@app.post("/api/whatsapp/webhook")
async def whatsapp_receber(request: Request):
    """Recebe mensagens do cliente, gerencia o contexto e espelha a resposta."""
    from .integracoes import whatsapp_omni
    try:
        payload = await request.json()
    except Exception:
        return {"ok": True, "ignorado": "payload inválido"}
    return whatsapp_omni.processar_mensagem(payload)


@app.post("/api/v1/casos/{caso_id}/iniciar")
def iniciar_caso_escritorio(caso_id: str):
    """Botão do CRM: inicia o processo do escritório na esteira (situação ATIVA)
    e registra o disparo para os agentes da esteira darem sequência."""
    from .core.db import registrar_evento
    get_db().table("casos").update({
        "situacao": "ATIVO", "atualizado_em": datetime.now(_tz.utc).isoformat(),
    }).eq("id", caso_id).execute()
    registrar_evento(caso_id, "PROCESSO_INICIADO_ESTEIRA", {"por": "ESCRITORIO"})
    return {"ok": True}


# ── Acionamento do cliente + aprovação humana da etapa ───────────
ORDEM_ESTEIRA = ["LEAD", "QUALIFICACAO", "PROPOSTA", "CONTRATO", "PAGAMENTO",
                 "COLETA_DOCS", "COLETA_PROVAS", "ANALISE", "PETICAO", "REVISAO",
                 "APROVADO", "PROTOCOLO_RPA", "PROTOCOLADO"]


class AcionarBody(BaseModel):
    solicitacao: str


@app.post("/api/v1/casos/{caso_id}/acionar-cliente")
def acionar_cliente(caso_id: str, body: AcionarBody):
    """Operador digita o que precisa do cliente. A solicitação é registrada
    e cai na CAIXA DE MENSAGENS do cliente, dentro do cadastro dele, onde
    ele pode responder e anexar documentos pelo próprio chat."""
    from .core.db import registrar_evento
    db = get_db()

    # 1) registra a solicitação (é ela que o cliente vê e responde)
    solicitacao_id = None
    try:
        sol = db.table("solicitacoes").insert({
            "caso_id": caso_id, "descricao": body.solicitacao,
            "status": "PENDENTE", "criado_por": "ESCRITORIO",
        }).execute().data[0]
        solicitacao_id = sol["id"]
    except Exception:
        pass  # migração 0013 ainda não aplicada — segue pelo histórico

    # 2) a mensagem aparece na conversa do cliente na plataforma
    texto = f"[SOLICITAÇÃO AO CLIENTE] {body.solicitacao}"
    db.table("mensagens").insert({
        "caso_id": caso_id, "canal": "PORTAL", "autor": "HUMANO", "conteudo": texto,
    }).execute()
    registrar_evento(caso_id, "SOLICITACAO_CLIENTE",
                     {"texto": body.solicitacao, "solicitacao_id": solicitacao_id})
    # o caso entra em AGUARDANDO_DOCUMENTOS: sai da esteira de produção, o
    # relógio do escritório pausa e o do cliente começa a correr (régua)
    from .agentes import pendencias
    try:
        pendencias.marcar_aguardando(caso_id, body.solicitacao, solicitacao_id)
    except Exception:
        # versões antigas do banco: ao menos sinaliza a pendência
        try:
            db.table("casos").update({
                "aguardando_cliente": True, "aguardando_desc": body.solicitacao,
                "atualizado_em": datetime.now(_tz.utc).isoformat(),
            }).eq("id", caso_id).execute()
        except Exception:
            pass
    # 3) avisa o cliente por e-mail e WhatsApp (número escolhido pelo DDD)
    envio = {}
    try:
        envio = avisos.notificar(
            caso_id, "DOCUMENTO",
            "Precisamos de um documento seu",
            body.solicitacao,
            solicitacao_id=solicitacao_id,
        )
    except Exception as e:
        envio = {"erros": [str(e)]}
    return {"ok": True, "solicitacao_id": solicitacao_id, **envio}


class AvisoBody(BaseModel):
    titulo: str
    mensagem: str
    tipo: str = "GERAL"      # AUDIENCIA | MOVIMENTACAO | PRAZO | PAGAMENTO | GERAL


@app.post("/api/v1/casos/{caso_id}/avisar")
def avisar_cliente(caso_id: str, body: AvisoBody):
    """CRM: comunica o cliente sobre audiência, prazo ou qualquer
    movimentação. Sai por e-mail e WhatsApp (número escolhido pelo DDD)
    e fica aguardando a ciência dele no painel."""
    if not body.titulo.strip() or not body.mensagem.strip():
        raise HTTPException(400, "Informe o título e a mensagem do aviso.")
    return avisos.notificar(caso_id, body.tipo.upper(),
                            body.titulo.strip(), body.mensagem.strip())


@app.post("/api/v1/avisos/{aviso_id}/reenviar")
def reenviar_aviso(aviso_id: str):
    """CRM: reenvia um aviso específico que o cliente ainda não viu."""
    db = get_db()
    a = db.table("avisos").select("*").eq("id", aviso_id).maybe_single().execute().data
    if not a:
        raise HTTPException(404, "Aviso não encontrado.")
    if a.get("ciencia_em"):
        return {"ok": True, "info": "O cliente já deu ciência neste aviso."}
    r = avisos.notificar(a["caso_id"], a["tipo"], a["titulo"], a["mensagem"],
                         solicitacao_id=a.get("solicitacao_id"))
    db.table("avisos").update({
        "lembretes": (a.get("lembretes") or 0) + 1,
        "ultimo_lembrete": datetime.now(_tz.utc).isoformat(),
    }).eq("id", aviso_id).execute()
    return r


@app.post("/api/v1/avisos/reenviar-pendentes")
def reenviar_avisos_pendentes():
    """Dispara manualmente a rodada de lembretes (roda sozinha de hora em hora)."""
    return avisos.reenviar_pendentes()


# Como cada fase é explicada ao cliente no aviso automático
FASE_PARA_CLIENTE = {
    "QUALIFICACAO": ("Estamos analisando o seu caso",
                     "Recebemos as suas informações e nossa equipe já está analisando a viabilidade da sua causa."),
    "PROPOSTA": ("Sua proposta está pronta",
                 "Concluímos a análise e preparamos a proposta de atuação para o seu caso. Acesse para conferir."),
    "CONTRATO": ("Contrato disponível para assinatura",
                 "O contrato de honorários já está disponível para a sua assinatura."),
    "PAGAMENTO": ("Pagamento liberado",
                  "O contrato foi assinado e a etapa de pagamento está liberada."),
    "COLETA_DOCS": ("Hora de reunir os documentos",
                    "Entramos na fase de coleta de documentos. Assim que precisarmos de algo, avisamos por aqui — e você pode enviar pelo próprio chat, por anexo ou foto."),
    "COLETA_PROVAS": ("Coleta de provas complementares",
                      "Estamos reunindo as provas complementares do seu caso."),
    "ANALISE": ("Análise técnica do seu caso",
                "Seus documentos estão em análise técnica pela nossa equipe."),
    "PETICAO": ("Sua petição está sendo elaborada",
                "Iniciamos a redação da petição do seu caso."),
    "REVISAO": ("Petição em revisão final",
                "A petição foi concluída e está em revisão final pelo advogado responsável."),
    "APROVADO": ("Petição aprovada",
                 "A petição foi aprovada e segue para o protocolo no tribunal."),
    "PROTOCOLO_RPA": ("Protocolando no tribunal",
                      "Sua petição está sendo protocolada no tribunal."),
    "PROTOCOLADO": ("Processo protocolado",
                    "Sua ação foi protocolada. A partir de agora você acompanha cada movimentação por aqui."),
    "CONCLUIDO": ("Caso concluído",
                  "Seu caso foi concluído. Agradecemos pela confiança."),
}


def _avisar_fase(caso_id: str, fase: str) -> None:
    """Avisa o cliente (e-mail + WhatsApp) quando a fase muda."""
    dados = FASE_PARA_CLIENTE.get(fase)
    if not dados:
        return
    titulo, mensagem = dados
    try:
        avisos.notificar(caso_id, "MOVIMENTACAO", titulo, mensagem)
    except Exception:
        pass


@app.post("/api/v1/casos/{caso_id}/aprovar-etapa")
def aprovar_etapa(caso_id: str):
    """Aprovação humana após a conferência: avança o caso para a próxima etapa."""
    db = get_db()
    caso = db.table("casos").select("estado").eq("id", caso_id).single().execute().data
    atual = caso["estado"]
    if atual not in ORDEM_ESTEIRA:
        raise HTTPException(400, f"Estado '{atual}' não permite avanço manual.")
    i = ORDEM_ESTEIRA.index(atual)
    if i + 1 >= len(ORDEM_ESTEIRA):
        return {"ok": True, "info": "Caso já está na última etapa."}
    prox = ORDEM_ESTEIRA[i + 1]
    try:
        mudar_estado(caso_id, prox, motivo="Aprovação humana — avançar etapa")
    except TransicaoInvalida as e:
        raise HTTPException(409, str(e))
    _avisar_fase(caso_id, prox)
    return {"ok": True, "novo_estado": prox}


class MoverFase(BaseModel):
    fase: str


class AjusteBody(BaseModel):
    descricao: str


@app.post("/api/v1/casos/{caso_id}/retomar")
def retomar_producao(caso_id: str):
    """Cliente complementou o que faltava → volta para a produção."""
    from .core.db import registrar_evento
    from .agentes import pendencias
    try:
        r = pendencias.retomar(caso_id, "retomada manual")
    except Exception:
        r = {}
        try:
            get_db().table("casos").update({
                "aguardando_cliente": False, "aguardando_desc": None,
                "atualizado_em": datetime.now(_tz.utc).isoformat(),
            }).eq("id", caso_id).execute()
        except Exception:
            pass
    registrar_evento(caso_id, "CLIENTE_RETORNOU", {})
    return {"ok": True, **r}


@app.post("/api/v1/casos/{caso_id}/mover-fase")
def mover_fase(caso_id: str, body: MoverFase):
    """Override manual da fase (ex.: reinserir após ação humana no ponto certo)."""
    from .core.db import registrar_evento
    if body.fase not in ORDEM_ESTEIRA and body.fase not in ("CONCLUIDO", "AGENDADO"):
        raise HTTPException(400, f"Fase '{body.fase}' inválida.")
    get_db().table("casos").update({
        "estado": body.fase, "atualizado_em": datetime.now(_tz.utc).isoformat(),
    }).eq("id", caso_id).execute()
    registrar_evento(caso_id, "FASE_MOVIDA_MANUAL", {"fase": body.fase})
    _avisar_fase(caso_id, body.fase)
    return {"ok": True, "novo_estado": body.fase}


@app.post("/api/v1/casos/{caso_id}/solicitar-ajuste")
def solicitar_ajuste(caso_id: str, body: AjusteBody):
    """Fase/opção inexistente → registra para a pasta de ajuste e implementação."""
    from .core.db import registrar_evento
    registrar_evento(caso_id, "SOLICITACAO_AJUSTE", {"descricao": body.descricao})
    return {"ok": True}


def _br(iso) -> str:
    """Data/hora no formato brasileiro."""
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")) \
                       .strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(iso)[:16]


@app.get("/api/v1/casos/{caso_id}/download")
def baixar_dossie(caso_id: str):
    """Baixa o processo inteiro em um .zip:

      RELATORIO_DE_ATENDIMENTO.docx   — dossiê completo do caso
      documentos/enviados_pelo_cliente/…
      documentos/do_escritorio/…
      links_nuvem.txt                 — anexos que são link (Drive etc.)

    Tudo o que o cliente mandou pelo chat entra aqui junto com o resto.
    """
    import io, zipfile
    from fastapi.responses import Response
    from docx import Document
    from docx.shared import Pt
    s = get_settings()
    db = get_db()
    caso = db.table("casos").select("*, clientes(*)").eq("id", caso_id).single().execute().data
    msgs = db.table("mensagens").select("autor,conteudo,canal,criado_em") \
             .eq("caso_id", caso_id).order("criado_em").execute().data
    docs = db.table("documentos").select("*").eq("caso_id", caso_id) \
             .order("criado_em").execute().data
    try:
        sols = db.table("solicitacoes").select("*").eq("caso_id", caso_id) \
                 .order("criado_em").execute().data or []
    except Exception:
        sols = []
    try:
        avs = db.table("avisos").select("*").eq("caso_id", caso_id) \
                .order("criado_em").execute().data or []
    except Exception:
        avs = []
    cli = caso.get("clientes") or {}
    num = caso.get("numero_atendimento") or "—"

    # ── Relatório de atendimento (Word) ──────────────────────────
    doc = Document()
    doc.add_heading(f"Relatório de Atendimento — {num}", 0)
    if caso.get("titulo"):
        doc.add_paragraph(caso["titulo"])
    doc.add_paragraph(
        f"{s.advogado} — {s.oab}\n"
        f"Emitido em {datetime.now(_tz.utc).strftime('%d/%m/%Y %H:%M')} (UTC)"
    )

    doc.add_heading("1. Cliente", level=1)
    for rot, val in [
        ("Nome", cli.get("nome")), ("CPF/CNPJ", cli.get("cpf_cnpj")),
        ("E-mail", cli.get("email")), ("WhatsApp", cli.get("whatsapp")),
        ("Origem do cadastro", cli.get("origem")),
    ]:
        doc.add_paragraph(f"{rot}: {val or '—'}")

    doc.add_heading("2. Caso", level=1)
    for rot, val in [
        ("Nº de atendimento", num), ("Nome do caso", caso.get("titulo")),
        ("Fase atual", caso.get("estado")), ("Grupo", caso.get("grupo")),
        ("Situação", caso.get("situacao", "ATIVO")),
        ("Nº do processo", caso.get("numero_processo")),
        ("Honorários", caso.get("honorarios_valor")),
        ("Aberto em", _br(caso.get("criado_em"))),
        ("Última atualização", _br(caso.get("atualizado_em"))),
    ]:
        doc.add_paragraph(f"{rot}: {val or '—'}")
    if caso.get("aguardando_cliente"):
        doc.add_paragraph(f"⚠ Fora da produção, aguardando o cliente: "
                          f"{caso.get('aguardando_desc') or '—'}")

    doc.add_heading("3. Relato e informações coletadas", level=1)
    doc.add_paragraph(caso.get("relato_inicial") or "—")

    doc.add_heading("4. Documentos do caso", level=1)
    if docs:
        t = doc.add_table(rows=1, cols=4)
        t.style = "Light Grid Accent 1"
        for i, cab in enumerate(["Arquivo", "Origem", "Situação", "Recebido em"]):
            t.rows[0].cells[i].text = cab
        for d in docs:
            c = t.add_row().cells
            c[0].text = _nome_original(d)
            c[1].text = "Cliente" if d.get("enviado_por") == "CLIENTE" else "Escritório"
            c[2].text = d.get("status") or "—"
            c[3].text = _br(d.get("criado_em"))
    else:
        doc.add_paragraph("Nenhum documento anexado.")

    doc.add_heading("5. Pedidos feitos ao cliente", level=1)
    if sols:
        for x in sols:
            doc.add_paragraph(
                f"[{x.get('status')}] {x.get('descricao')}\n"
                f"    Pedido em {_br(x.get('criado_em'))}"
                + (f" · Atendido em {_br(x.get('atendida_em'))}" if x.get("atendida_em") else "")
            )
    else:
        doc.add_paragraph("Nenhum pedido registrado.")

    doc.add_heading("6. Comunicações e ciência do cliente", level=1)
    if avs:
        for a in avs:
            canais = []
            if a.get("enviado_email"):
                canais.append("e-mail")
            if a.get("enviado_whatsapp"):
                canais.append(f"WhatsApp {a.get('numero_origem') or ''}".strip())
            ciencia = (f"CIENTE em {_br(a.get('ciencia_em'))} ({a.get('ciencia_canal')})"
                       if a.get("ciencia_em") else "SEM CIÊNCIA")
            doc.add_paragraph(
                f"{_br(a.get('criado_em'))} — {a.get('titulo')}\n"
                f"    Enviado por: {', '.join(canais) or 'não enviado'} · {ciencia}"
                + (f" · {a.get('lembretes')} lembrete(s)" if a.get("lembretes") else "")
            )
            doc.add_paragraph(f"    {a.get('mensagem')}")
    else:
        doc.add_paragraph("Nenhuma comunicação registrada.")

    doc.add_heading("7. Histórico do atendimento", level=1)
    for m in msgs:
        p = doc.add_paragraph()
        r = p.add_run(f"[{_br(m.get('criado_em'))}] {m.get('autor')} "
                      f"({m.get('canal') or '—'})")
        r.bold = True
        r.font.size = Pt(9)
        doc.add_paragraph(m.get("conteudo") or "")

    buf = io.BytesIO()
    doc.save(buf)
    relatorio = buf.getvalue()

    # ── Zip: relatório + todos os documentos ─────────────────────
    zbuf = io.BytesIO()
    usados: dict[str, int] = {}
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("RELATORIO_DE_ATENDIMENTO.docx", relatorio)
        links, falhas = [], []
        for d in docs:
            sp = d.get("storage_path") or ""
            rotulo = _nome_original(d)
            if sp.startswith("http"):
                links.append(f"{rotulo}: {sp}")
                continue
            pasta = ("documentos/enviados_pelo_cliente"
                     if d.get("enviado_por") == "CLIENTE" else "documentos/do_escritorio")
            chave = f"{pasta}/{rotulo}"
            if chave in usados:                       # dois arquivos com o mesmo nome
                usados[chave] += 1
                raiz, _, ext = rotulo.rpartition(".")
                chave = (f"{pasta}/{raiz} ({usados[chave]}).{ext}" if raiz
                         else f"{pasta}/{rotulo} ({usados[chave]})")
            else:
                usados[chave] = 1
            try:
                z.writestr(chave, db.storage.from_(s.bucket_documentos).download(sp))
            except Exception as e:
                falhas.append(f"{rotulo}: {e}")
        if links:
            z.writestr("links_nuvem.txt", "\n".join(links))
        if falhas:
            z.writestr("_arquivos_nao_baixados.txt", "\n".join(falhas))

    nome_cli = (cli.get("nome") or "processo").replace(" ", "_")[:40]
    arquivo = f"{num}_{nome_cli}.zip" if num != "—" else f"processo_{nome_cli}.zip"
    return Response(
        content=zbuf.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": _content_disposition(arquivo)},
    )


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


# ================================================================
#  ÁREA DO CLIENTE — cadastro, caixa de mensagens e envio de docs
#
#  Caminho completo:
#    CRM "Acionar o cliente"  →  solicitacoes (PENDENTE)
#      →  caixa de mensagens do cliente (GET /cliente/caso/{id})
#      →  cliente anexa/fotografa e clica ENVIAR (POST .../documentos)
#      →  arquivo vai para a pasta do caso no storage + tabela documentos
#      →  solicitação vira ATENDIDA e o caso volta para a produção
# ================================================================

# Nome amigável do caso quando o escritório ainda não deu um título
NOME_POR_GRUPO = {
    "BANCARIO": "Direito Bancário",
    "IMOBILIARIO": "Distrato Imobiliário",
    "TRIBUTARIO": "Execução Fiscal",
    "CONSUMIDOR": "Recuperação de Consumo",
    "TRABALHISTA": "Causa Trabalhista",
    "PREVIDENCIARIO": "Causa Previdenciária",
}


def _mudou_contato(antes: dict, campos: dict) -> bool:
    """Diz se o e-mail ou o WhatsApp mudaram de fato nesta gravação."""
    for c in ("email", "whatsapp"):
        if c in campos and (campos.get(c) or "") != (antes.get(c) or ""):
            return True
    return False


def _nome_do_caso(grupo: str | None) -> str:
    return NOME_POR_GRUPO.get(grupo or "", "Atendimento jurídico")


def _clientes_do_token(authorization: str | None) -> tuple[dict, list[str]]:
    """Devolve (cadastro principal, ids de TODOS os cadastros do usuário).

    A base carrega cadastros duplicados do início da operação — o mesmo
    e-mail (às vezes o mesmo telefone gravado no campo e-mail) aparece em
    vários registros de `clientes`, cada um dono de casos diferentes.
    Por isso a posse de um caso é conferida contra a LISTA de cadastros
    daquele login, e não contra um único registro escolhido ao acaso:
    era isso que fazia o envio de documento responder "caso não
    encontrado". O principal é o cadastro com caso mais recente.
    """
    user = _usuario_do_token(authorization)
    email = (user.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(400, "Conta sem e-mail — não é possível localizar o cadastro.")
    db = get_db()

    # 1) vínculo forte: o cadastro já amarrado a este login. É ele que faz o
    #    acesso do cliente sobreviver a uma troca de e-mail feita no CRM.
    achados: list[dict] = []
    try:
        achados = db.table("clientes").select("*") \
                    .eq("auth_user_id", user["id"]).execute().data or []
    except Exception:
        achados = []

    # 2) vínculo por e-mail (primeiro acesso, ou cadastro criado pelo escritório)
    try:
        por_email = db.table("clientes").select("*").ilike("email", email) \
                      .execute().data or []
    except Exception:
        por_email = []
    for c in por_email:
        if c["id"] not in {x["id"] for x in achados}:
            achados.append(c)

    if not achados:
        nome = (user.get("user_metadata") or {}).get("nome") or email.split("@")[0]
        achados = [db.table("clientes").insert(
            {"nome": nome, "email": email, "origem": "PORTAL"}
        ).execute().data[0]]

    # amplia para os cadastros irmãos: mesmo CPF ou mesmo WhatsApp de algum
    # dos registros encontrados (é assim que os duplicados antigos se ligam)
    chaves_cpf = {c.get("cpf_cnpj") for c in achados if c.get("cpf_cnpj")}
    chaves_zap = {c.get("whatsapp") for c in achados if c.get("whatsapp")}
    for coluna, valores in (("cpf_cnpj", chaves_cpf), ("whatsapp", chaves_zap)):
        for v in valores:
            try:
                irmaos = db.table("clientes").select("*").eq(coluna, v).execute().data or []
            except Exception:
                irmaos = []
            for ir in irmaos:
                if ir["id"] not in {c["id"] for c in achados}:
                    achados.append(ir)

    ids = [c["id"] for c in achados]
    principal = achados[0]
    if len(achados) > 1:
        # o cadastro "vivo" é o que tem o caso mais recente
        try:
            ult = db.table("casos").select("cliente_id").in_("cliente_id", ids) \
                    .order("atualizado_em", desc=True).limit(1).execute().data
            if ult:
                dono = ult[0]["cliente_id"]
                principal = next((c for c in achados if c["id"] == dono), principal)
        except Exception:
            pass

    try:
        db.table("perfis").update({"cliente_id": principal["id"]}) \
          .eq("id", user["id"]).execute()
    except Exception:
        pass
    # amarra o cadastro ao login: a partir daqui, trocar o e-mail de contato
    # não tira o acesso do cliente à própria área
    if not principal.get("auth_user_id"):
        try:
            db.table("clientes").update({"auth_user_id": user["id"]}) \
              .eq("id", principal["id"]).execute()
            principal["auth_user_id"] = user["id"]
        except Exception:
            pass
    return principal, ids


def _cliente_do_token(authorization: str | None) -> dict:
    return _clientes_do_token(authorization)[0]


def _caso_do_cliente(caso_id: str, cliente_ids: list[str] | str) -> dict:
    """Confere se o caso pertence ao usuário logado (qualquer um dos
    cadastros dele). Aceita id único por compatibilidade."""
    if isinstance(cliente_ids, str):
        cliente_ids = [cliente_ids]
    caso = get_db().table("casos").select("*").eq("id", caso_id) \
             .maybe_single().execute().data
    if not caso:
        raise HTTPException(404, "Caso não encontrado.")
    if caso.get("cliente_id") not in cliente_ids:
        raise HTTPException(403, "Este caso não pertence ao seu cadastro.")
    return caso


@app.get("/api/v1/cliente/meus-casos")
def cliente_meus_casos(authorization: str | None = Header(default=None)):
    """Casos do cliente logado, cada um com o seu NÚMERO DE ATENDIMENTO.
    É por esse número que o cliente distingue um processo do outro quando
    tem mais de um em andamento."""
    _, ids = _clientes_do_token(authorization)
    db = get_db()
    casos = db.table("casos") \
        .select("id,estado,grupo,titulo,numero_atendimento,numero_processo,"
                "aguardando_cliente,aguardando_desc,criado_em,atualizado_em") \
        .in_("cliente_id", ids).order("criado_em").execute().data or []
    if not casos:
        return []

    idsc = [c["id"] for c in casos]
    # pendências por caso: avisos sem ciência e documentos ainda não enviados
    sem_ciencia: dict[str, int] = {}
    try:
        for a in (db.table("avisos").select("caso_id")
                    .in_("caso_id", idsc).is_("ciencia_em", "null")
                    .execute().data or []):
            sem_ciencia[a["caso_id"]] = sem_ciencia.get(a["caso_id"], 0) + 1
    except Exception:
        pass
    pend_doc: dict[str, int] = {}
    try:
        for x in (db.table("solicitacoes").select("caso_id")
                    .in_("caso_id", idsc).eq("status", "PENDENTE")
                    .execute().data or []):
            pend_doc[x["caso_id"]] = pend_doc.get(x["caso_id"], 0) + 1
    except Exception:
        pass

    for c in casos:
        c["avisos_sem_ciencia"] = sem_ciencia.get(c["id"], 0)
        c["documentos_pendentes"] = pend_doc.get(c["id"], 0)
        if not c.get("titulo"):
            c["titulo"] = _nome_do_caso(c.get("grupo"))
    # mais recentes primeiro na tela, mas a numeração seguiu a ordem de criação
    casos.sort(key=lambda c: c.get("atualizado_em") or c.get("criado_em") or "", reverse=True)
    return casos


@app.get("/api/v1/cliente/cadastro")
def cliente_cadastro(authorization: str | None = Header(default=None)):
    """Cadastro do cliente logado (nome, e-mail, CPF, WhatsApp)."""
    cli = _cliente_do_token(authorization)
    return {k: cli.get(k) for k in
            ("id", "nome", "email", "cpf_cnpj", "whatsapp", "origem", "criado_em")}


class CadastroCliente(BaseModel):
    nome: str | None = None
    email: str | None = None          # e-mail de contato (o login não muda)
    cpf_cnpj: str | None = None
    whatsapp: str | None = None
    nacionalidade: str | None = None
    estado_civil: str | None = None
    profissao: str | None = None
    rg: str | None = None
    endereco_rua: str | None = None
    endereco_numero: str | None = None
    endereco_complemento: str | None = None
    endereco_bairro: str | None = None
    endereco_cidade: str | None = None
    endereco_uf: str | None = None
    endereco_cep: str | None = None


@app.patch("/api/v1/cliente/cadastro")
def cliente_atualizar_cadastro(body: CadastroCliente,
                               authorization: str | None = Header(default=None)):
    """O próprio cliente atualiza o cadastro, inclusive o e-mail e o WhatsApp
    de contato. A partir da troca, os avisos passam a sair no endereço novo —
    e o que estava pendente é reenviado para lá.

    O LOGIN continua sendo o e-mail com que ele entrou: o vínculo do cadastro
    com a conta é feito pelo identificador do usuário, não pelo e-mail, então
    trocar o e-mail de contato não tira o acesso dele à própria área."""
    cli = _cliente_do_token(authorization)
    campos = {k: v for k, v in body.model_dump().items() if v}
    if campos.get("cpf_cnpj"):
        from .core.cpf import cpf_valido
        if not cpf_valido(campos["cpf_cnpj"]):
            raise HTTPException(400, "CPF inválido — confira os números.")
    if campos.get("whatsapp"):
        campos["whatsapp"] = "".join(c for c in campos["whatsapp"] if c.isdigit())
    if campos.get("email"):
        campos["email"] = campos["email"].strip().lower()
        if "@" not in campos["email"]:
            raise HTTPException(400, "E-mail inválido.")
    if campos:
        get_db().table("clientes").update(campos).eq("id", cli["id"]).execute()

    troca = {}
    if _mudou_contato(cli, campos):
        try:
            troca = avisos.avisar_troca_de_contato(
                cli["id"], cli, {**cli, **campos}, quem="CLIENTE")
        except Exception as e:
            troca = {"erro": str(e)}
    return {"ok": True, **({"contato": troca} if troca else {})}


@app.get("/api/v1/cliente/caso/{caso_id}")
def cliente_caso(caso_id: str, authorization: str | None = Header(default=None)):
    """Conversa + documentos + solicitações pendentes de UM caso do cliente.
    É a 'caixa de mensagens' dentro do cadastro dele."""
    cli, ids = _clientes_do_token(authorization)
    caso = _caso_do_cliente(caso_id, ids)
    db = get_db()
    mensagens = db.table("mensagens").select("id,autor,conteudo,canal,criado_em") \
                  .eq("caso_id", caso_id).order("criado_em").execute().data
    # notas internas do CRM não aparecem para o cliente
    mensagens = [m for m in mensagens if m.get("canal") != "CRM"]
    try:
        solicitacoes = db.table("solicitacoes").select("*").eq("caso_id", caso_id) \
                         .order("criado_em", desc=True).execute().data
    except Exception:
        solicitacoes = []
    try:
        documentos = db.table("documentos") \
            .select("id,observacao,tipo,status,enviado_por,criado_em") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).execute().data
    except Exception:
        documentos = []
    try:
        lista_avisos = db.table("avisos") \
            .select("id,tipo,titulo,mensagem,criado_em,ciencia_em,ciencia_canal") \
            .eq("caso_id", caso_id).order("criado_em", desc=True).limit(50).execute().data
    except Exception:
        lista_avisos = []
    try:
        assinaturas = db.table("documentos_assinatura") \
            .select("id,tipo,titulo,status,link_assinatura,enviado_em,assinado_em") \
            .eq("caso_id", caso_id).in_("status", ["ENVIADO", "ASSINADO"]) \
            .order("criado_em", desc=True).execute().data
    except Exception:
        assinaturas = []
    return {
        "assinaturas": assinaturas,
        "id": caso["id"], "estado": caso["estado"], "grupo": caso.get("grupo"),
        "titulo": caso.get("titulo") or _nome_do_caso(caso.get("grupo")),
        "numero_atendimento": caso.get("numero_atendimento"),
        "numero_processo": caso.get("numero_processo"),
        "aguardando_cliente": caso.get("aguardando_cliente"),
        "aguardando_desc": caso.get("aguardando_desc"),
        "mensagens": mensagens, "solicitacoes": solicitacoes,
        "documentos": documentos, "avisos": lista_avisos,
    }


def _documento_do_cliente(doc_id: str, cliente_ids: list[str]) -> dict:
    d = get_db().table("documentos_assinatura").select("*").eq("id", doc_id) \
          .maybe_single().execute().data
    if not d:
        raise HTTPException(404, "Documento não encontrado.")
    _caso_do_cliente(d["caso_id"], cliente_ids)
    return d


@app.get("/api/v1/cliente/documentos-assinatura/{doc_id}/baixar")
def cliente_baixar_documento(doc_id: str,
                             authorization: str | None = Header(default=None)):
    """O cliente baixa o documento que precisa assinar."""
    from fastapi.responses import Response
    _, ids = _clientes_do_token(authorization)
    d = _documento_do_cliente(doc_id, ids)
    s = get_settings()
    db = get_db()

    # o cliente sempre recebe PDF; se ainda não existir, gera na hora
    caminho, tipo, ext = d.get("pdf_path"), "application/pdf", ".pdf"
    if not caminho:
        try:
            from .agentes import documentos as redator
            caminho = redator.gerar_pdf_do_documento(doc_id)["pdf_path"]
        except Exception:
            caminho = d["storage_path"]          # servidor sem conversor: manda o .docx
            tipo = ("application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document")
            ext = ".docx"
    try:
        conteudo = db.storage.from_(s.bucket_documentos).download(caminho)
    except Exception as e:
        raise HTTPException(500, f"Não foi possível baixar: {e}")
    return Response(
        content=conteudo, media_type=tipo,
        headers={"Content-Disposition": _content_disposition(d["titulo"] + ext)},
    )


@app.post("/api/v1/cliente/documentos-assinatura/{doc_id}/assinado")
async def cliente_enviar_assinado(
    doc_id: str,
    arquivo: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """O cliente devolve o documento já assinado. Ele entra na pasta do caso,
    o documento passa a ASSINADO e o escritório é avisado."""
    import re as _re, uuid
    from .core.db import registrar_evento
    _, ids = _clientes_do_token(authorization)
    d = _documento_do_cliente(doc_id, ids)
    s = get_settings()
    db = get_db()

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo vazio.")
    if len(conteudo) > 25 * 1024 * 1024:
        raise HTTPException(400, "Arquivo acima de 25 MB.")

    base = (arquivo.filename or "assinado").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe = _re.sub(r"[^A-Za-z0-9._-]", "_", base) or "assinado"
    path = f"{d['caso_id']}/assinados/{uuid.uuid4().hex}_{safe}"
    try:
        db.storage.from_(s.bucket_documentos).upload(
            path, conteudo,
            {"content-type": arquivo.content_type or "application/octet-stream",
             "upsert": "true"},
        )
    except Exception as e:
        raise HTTPException(500, f"Falha ao receber o arquivo: {e}")

    agora = datetime.now(_tz.utc).isoformat()
    db.table("documentos_assinatura").update({
        "status": "ASSINADO", "assinado_em": agora,
        "assinado_url": path, "atualizado_em": agora,
    }).eq("id", doc_id).execute()

    # entra na pasta do caso junto dos demais documentos
    linha = {
        "caso_id": d["caso_id"], "tipo": f"ASSINADO_{d['tipo']}",
        "storage_path": path, "status": "RECEBIDO",
        "observacao": f"{d['titulo']} (assinado pelo cliente)",
    }
    try:
        linha["enviado_por"] = "CLIENTE"
        db.table("documentos").insert(linha).execute()
    except Exception:
        linha.pop("enviado_por", None)
        db.table("documentos").insert(linha).execute()

    try:
        db.table("mensagens").insert({
            "caso_id": d["caso_id"], "canal": "PORTAL", "autor": "CLIENTE",
            "conteudo": f"✍ Enviei o {d['titulo']} assinado.",
        }).execute()
        db.table("mensagens").insert({
            "caso_id": d["caso_id"], "canal": "PORTAL", "autor": "AGENTE",
            "conteudo": f"Recebemos o seu {d['titulo']} assinado. Muito obrigado! "
                        f"Já está arquivado no seu processo e seguimos com o próximo passo.",
        }).execute()
    except Exception:
        pass

    # se não restou pendência, o caso volta para a produção
    try:
        pend = db.table("documentos_assinatura").select("id") \
                 .eq("caso_id", d["caso_id"]).eq("status", "ENVIADO").execute().data or []
        if not pend:
            db.table("casos").update({
                "aguardando_cliente": False, "aguardando_desc": None,
                "atualizado_em": agora,
            }).eq("id", d["caso_id"]).execute()
    except Exception:
        pass

    registrar_evento(d["caso_id"], "DOCUMENTO_ASSINADO_RECEBIDO",
                     {"documento_id": doc_id, "tipo": d["tipo"]})
    return {"ok": True, "status": "ASSINADO", "arquivo": base}


@app.post("/api/v1/cliente/avisos/{aviso_id}/ciencia")
def cliente_dar_ciencia(aviso_id: str, authorization: str | None = Header(default=None)):
    """Botão 'Li e estou ciente' do painel. Registra data, hora e canal —
    é a prova de que a comunicação chegou ao cliente."""
    _, ids = _clientes_do_token(authorization)
    db = get_db()
    a = db.table("avisos").select("id,caso_id").eq("id", aviso_id) \
          .maybe_single().execute().data
    if not a:
        raise HTTPException(404, "Aviso não encontrado.")
    _caso_do_cliente(a["caso_id"], ids)          # confere a posse
    return avisos.dar_ciencia(aviso_id, canal="PAINEL")


@app.post("/api/v1/cliente/caso/{caso_id}/documentos")
async def cliente_enviar_documentos(
    caso_id: str,
    arquivos: list[UploadFile] = File(...),
    solicitacao_id: str | None = None,
    observacao: str | None = None,
    authorization: str | None = Header(default=None),
):
    """Botão ENVIAR do chat do cliente: recebe anexos ou fotos tiradas na
    hora, grava na pasta do caso, responde a solicitação e devolve o caso
    para a esteira — com os documentos já anexados."""
    import re, uuid
    from .core.db import registrar_evento
    cli, ids = _clientes_do_token(authorization)
    _caso_do_cliente(caso_id, ids)
    s = get_settings()
    db = get_db()

    if not arquivos:
        raise HTTPException(400, "Nenhum arquivo foi anexado.")

    salvos, falhas = [], []
    for arq in arquivos:
        conteudo = await arq.read()
        if not conteudo:
            continue
        if len(conteudo) > 25 * 1024 * 1024:
            falhas.append(f"{arq.filename}: arquivo acima de 25 MB")
            continue
        base = (arq.filename or "documento").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", base) or "documento"
        path = f"{caso_id}/{uuid.uuid4().hex}_{safe}"
        try:
            db.storage.from_(s.bucket_documentos).upload(
                path, conteudo,
                {"content-type": arq.content_type or "application/octet-stream",
                 "upsert": "true"},
            )
        except Exception as e:
            falhas.append(f"{base}: {e}")
            continue
        linha = {
            "caso_id": caso_id, "tipo": "ENVIO_CLIENTE", "storage_path": path,
            "observacao": observacao or arq.filename, "status": "RECEBIDO",
        }
        try:
            linha["enviado_por"] = "CLIENTE"
            if solicitacao_id:
                linha["solicitacao_id"] = solicitacao_id
            db.table("documentos").insert(linha).execute()
        except Exception:
            linha.pop("enviado_por", None)
            linha.pop("solicitacao_id", None)
            db.table("documentos").insert(linha).execute()
        salvos.append(base)

    if not salvos:
        raise HTTPException(500, "Não foi possível enviar: " + "; ".join(falhas))

    # a conversa registra o envio — o histórico segue único e contínuo
    lista = ", ".join(salvos)
    db.table("mensagens").insert({
        "caso_id": caso_id, "canal": "PORTAL", "autor": "CLIENTE",
        "conteudo": f"📎 Enviei {len(salvos)} documento(s): {lista}"
                    + (f"\n{observacao}" if observacao else ""),
    }).execute()

    # a solicitação é atendida
    if solicitacao_id:
        try:
            db.table("solicitacoes").update({
                "status": "ATENDIDA",
                "atendida_em": datetime.now(_tz.utc).isoformat(),
            }).eq("id", solicitacao_id).execute()
        except Exception:
            pass

    # se não restou pendência, o caso volta para a produção
    pendentes = 0
    try:
        pendentes = len(db.table("solicitacoes").select("id")
                        .eq("caso_id", caso_id).eq("status", "PENDENTE")
                        .execute().data or [])
    except Exception:
        pendentes = 0
    retomado = False
    if pendentes == 0:
        # é aqui que o card volta sozinho para a esteira: o tempo parado é
        # devolvido ao SLA, a régua de cobrança encerra e o estado vira
        # PRONTO_PARA_ANALISE
        from .agentes import pendencias
        try:
            pendencias.retomar(caso_id, "documento enviado pelo painel")
            retomado = True
        except Exception:
            try:
                db.table("casos").update({
                    "aguardando_cliente": False, "aguardando_desc": None,
                    "atualizado_em": datetime.now(_tz.utc).isoformat(),
                }).eq("id", caso_id).execute()
                retomado = True
            except Exception:
                pass

    registrar_evento(caso_id, "DOCUMENTOS_RECEBIDOS_DO_CLIENTE",
                     {"arquivos": salvos, "solicitacao_id": solicitacao_id,
                      "retomou_producao": retomado})
    return {"ok": True, "enviados": salvos, "falhas": falhas,
            "pendencias_restantes": pendentes, "retomou_producao": retomado}


class MensagemCliente(BaseModel):
    conteudo: str


@app.post("/api/v1/cliente/caso/{caso_id}/mensagens")
def cliente_mensagem(caso_id: str, body: MensagemCliente,
                     authorization: str | None = Header(default=None)):
    """Mensagem do cliente pela plataforma — mesma thread do caso, para o
    atendimento nunca recomeçar nem repetir perguntas já respondidas."""
    cli, ids = _clientes_do_token(authorization)
    _caso_do_cliente(caso_id, ids)
    return especialista.atender(caso_id, body.conteudo, "PORTAL")


# ══ Fases judiciais, importação de processos e controladoria ═════
class ImportarOAB(BaseModel):
    numero: str | None = None          # vazio = OAB do escritório (.env)
    uf: str | None = None
    dias: int = 60


class ImportarProcessos(BaseModel):
    processos: list[dict]
    fase: str = "JUDICIAL"


class MoverFase(BaseModel):
    destino: str                       # JUDICIAL | RECEBIMENTO
    motivo: str = ""


@app.post("/api/v1/processos/previa-oab")
def previa_oab(body: ImportarOAB):
    """Lê o Diário de Justiça Eletrônico Nacional (CNJ, gratuito) pela OAB
    e devolve os processos encontrados, dizendo quais já estão aqui."""
    from .agentes import importador
    from .integracoes.comunica_cnj import FonteOcupada
    try:
        return importador.previa_por_oab(body.numero, body.uf, dias=body.dias)
    except FonteOcupada as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/v1/processos/previa-numero")
def previa_numero(numero: str):
    from .agentes import importador
    from .integracoes.comunica_cnj import FonteOcupada
    if len(re.sub(r"\D", "", numero)) < 15:
        raise HTTPException(400, "Número de processo incompleto (CNJ tem 20 dígitos).")
    try:
        return importador.previa_por_numero(numero)
    except FonteOcupada as e:
        raise HTTPException(503, str(e))


class ComunicacoesLidas(BaseModel):
    comunicacoes: list[dict]


@app.post("/api/v1/processos/previa-do-navegador")
def previa_do_navegador(body: ComunicacoesLidas):
    """O navegador do escritório consulta o CNJ (que recusa o nosso
    servidor, por estar fora do Brasil) e manda o resultado para cá."""
    from .agentes import importador
    return importador.previa_de_comunicacoes(body.comunicacoes)


@app.post("/api/v1/controladoria/sincronizar")
def controladoria_sincronizar(body: ComunicacoesLidas):
    """Grava as publicações novas dos processos já cadastrados e cria os
    prazos; o que não é do acervo fica para conferência na tela."""
    from .agentes import importador
    return importador.sincronizar_conhecidos(body.comunicacoes)


@app.post("/api/v1/processos/importar")
def importar_processos(body: ImportarProcessos):
    from .agentes import importador
    if not body.processos:
        raise HTTPException(400, "Nenhum processo selecionado.")
    try:
        return importador.importar(body.processos, body.fase)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/v1/casos/{caso_id}/mover-fase")
def mover_fase(caso_id: str, body: MoverFase):
    from .agentes import controladoria
    try:
        return controladoria.mover_fase(caso_id, body.destino.upper(), body.motivo)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/v1/controladoria/rodar")
def controladoria_rodar():
    from .agentes import controladoria
    return controladoria.rodar()


@app.get("/api/v1/controladoria/fila")
def controladoria_fila(dias: int = 30):
    from .agentes import controladoria
    return controladoria.fila(dias=dias)


@app.get("/api/v1/painel/resumo")
def painel_resumo():
    """Os números da tela inicial e o que vence primeiro."""
    from .agentes import controladoria
    db = get_db()

    def _contar(estados: list[str]) -> int:
        total = 0
        for e in estados:
            r = db.table("casos").select("id", count="exact").eq("estado", e) \
                .eq("situacao", "ATIVO").limit(1).execute()
            total += r.count or 0
        return total

    try:
        fila = controladoria.fila(dias=7)
    except Exception:
        fila = []
    aguardando = db.table("casos").select("id", count="exact") \
        .eq("aguardando_cliente", True).eq("situacao", "ATIVO").limit(1).execute().count or 0
    novas = db.table("intimacoes").select("id", count="exact") \
        .eq("lida", False).limit(1).execute().count or 0
    return {
        "aguardando_cliente": aguardando,
        "contratos_abertos": _contar(["LEAD", "QUALIFICACAO", "PROPOSTA",
                                      "CONTRATO", "PAGAMENTO"]),
        "producao": _contar(["COLETA_DOCS", "AGUARDANDO_DOCUMENTOS",
                             "PRONTO_PARA_ANALISE", "COLETA_PROVAS", "ANALISE",
                             "PETICAO", "REVISAO", "PROTOCOLO_RPA"]),
        "judicial": _contar(["JUDICIAL", "PROTOCOLADO"]),
        "recebimento": _contar(["RECEBIMENTO"]),
        "prazos_7_dias": len(fila),
        "intimacoes_novas": novas,
        "prazos_proximos": [
            {"descricao": f["descricao"], "cliente": f["cliente"],
             "numero_processo": f["numero_processo"],
             "dias_restantes": f["dias_restantes"],
             "caso_id": f["caso_id"]} for f in fila[:8]
        ],
    }


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
