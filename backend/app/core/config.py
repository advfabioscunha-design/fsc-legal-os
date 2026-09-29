"""Configuração central do backend — tudo via variáveis de ambiente."""
import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    # Identidade
    advogado: str = os.getenv("ADVOGADO_NOME", "Fábio Silva Cunha")
    oab: str = os.getenv("OAB", "OAB/RO 10.849")
    email_escritorio: str = os.getenv("EMAIL_ESCRITORIO",
                                      "adv.fabios.cunha@gmail.com")
    ambiente: str = os.getenv("AMBIENTE", "dev")  # dev | staging | prod

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
    bucket_documentos: str = os.getenv("BUCKET_DOCUMENTOS", "documentos")

    # Claude
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    claude_model_rapido: str = os.getenv("CLAUDE_MODEL_RAPIDO", "claude-haiku-4-5-20251001")

    # Integrações
    asaas_api_key: str = os.getenv("ASAAS_API_KEY", "")
    asaas_base_url: str = os.getenv("ASAAS_BASE_URL", "https://api.asaas.com/v3")
    zapsign_api_token: str = os.getenv("ZAPSIGN_API_TOKEN", "")
    zapsign_base_url: str = os.getenv("ZAPSIGN_BASE_URL", "https://api.zapsign.com.br/api/v1")
    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_phone_id: str = os.getenv("WHATSAPP_PHONE_ID", "")
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "fc-legal-os")

    # ── Dois números do escritório, roteados pelo DDD do cliente ──
    # Cliente com DDD 69 recebe do número de Rondônia; DDD 48 recebe do
    # número de Santa Catarina; qualquer outro DDD (ou sem telefone)
    # recebe sempre do 48, que é o padrão do escritório.
    whatsapp_phone_id_69: str = os.getenv("WHATSAPP_PHONE_ID_69", "")
    whatsapp_phone_id_48: str = os.getenv("WHATSAPP_PHONE_ID_48", "")
    whatsapp_numero_69: str = os.getenv("WHATSAPP_NUMERO_69", "5569993225383")
    whatsapp_numero_48: str = os.getenv("WHATSAPP_NUMERO_48", "5548988357992")
    whatsapp_ddd_padrao: str = os.getenv("WHATSAPP_DDD_PADRAO", "48")

    # ── E-mail transacional (Gmail com senha de app) ──────────────
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_porta: int = int(os.getenv("SMTP_PORTA", "587"))
    smtp_usuario: str = os.getenv("SMTP_USUARIO", "")
    smtp_senha: str = os.getenv("SMTP_SENHA", "")          # senha de app do Google
    smtp_remetente: str = os.getenv("SMTP_REMETENTE", "FC Advocacia")
    # Leitura da caixa de entrada: é assim que a via assinada devolvida por
    # e-mail entra na pasta do cliente, sem ninguém precisar salvar à mão.
    imap_host: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    imap_porta: int = int(os.getenv("IMAP_PORTA", "993"))
    imap_pasta: str = os.getenv("IMAP_PASTA", "INBOX")
    imap_auto: bool = os.getenv("IMAP_AUTO", "true").lower() == "true"
    imap_minutos: int = int(os.getenv("IMAP_MINUTOS", "10"))

    # Endereço do painel do cliente (usado nos links dos avisos)
    app_url: str = os.getenv("APP_URL", "https://app.fscadvocaciadigital.com.br")
    # Endereço da própria API. O convidado confirma presença clicando num
    # link que cai aqui, sem passar pelo painel — ele não tem login.
    api_url: str = os.getenv("API_URL", "https://api.fscadvocaciadigital.com.br")

    # Assinatura do calendário. O Google Calendar (e o Outlook, e o
    # iPhone) assinam um endereço que devolve iCalendar e o relem sozinhos
    # de tempos em tempos. Quem tem o endereço vê a agenda inteira, então
    # o token é longo e só sai daqui; trocá-lo derruba as assinaturas
    # antigas, que é justamente o que se quer quando ele vaza.
    agenda_feed_token: str = os.getenv("AGENDA_FEED_TOKEN", "")

    # Lembrete automático quando o cliente não dá ciência
    aviso_lembrete_horas: int = int(os.getenv("AVISO_LEMBRETE_HORAS", "24"))
    aviso_lembretes_max: int = int(os.getenv("AVISO_LEMBRETES_MAX", "3"))
    # Escavador — monitoramento de processos e intimações
    escavador_api_token: str = os.getenv("ESCAVADOR_API_TOKEN", "")
    escavador_base_url: str = os.getenv("ESCAVADOR_BASE_URL", "https://api.escavador.com")
    # ── Pesquisa de jurisprudência (ementas para a petição) ──────
    # O DataJud do CNJ não devolve ementa; para o agente de precedentes
    # citar julgado real é preciso um provedor de pesquisa contratado.
    # Vazio = usa só o banco interno do escritório (acórdãos em PDF).
    jurisprudencia_provedor: str = os.getenv("JURISPRUDENCIA_PROVEDOR", "")
    jusbrasil_api_token: str = os.getenv("JUSBRASIL_API_TOKEN", "")
    jurisprudencias_api_token: str = os.getenv("JURISPRUDENCIAS_API_TOKEN", "")

    # ── Ponte CNJ (saída de rede no Brasil) ──────────────────────
    # O Comunica CNJ recusa requisição de IP fora do Brasil (403 no
    # CloudFront) e este servidor está nos Estados Unidos. Com a ponte
    # configurada — uma máquina pequena em São Paulo, ver
    # infra/ponte-cnj — a varredura do Diário volta a rodar sozinha.
    # Sem ela, a consulta continua saindo do navegador do escritório.
    comunica_ponte_url: str = os.getenv("COMUNICA_PONTE_URL", "")
    comunica_ponte_token: str = os.getenv("COMUNICA_PONTE_TOKEN", "")

    # ── Atendimento telepresencial (Daily) ───────────────────────
    # Vídeo ao vivo, gravação só de áudio. O segredo do webhook impede que
    # qualquer um poste "gravação pronta" e injete áudio no acervo.
    daily_api_key: str = os.getenv("DAILY_API_KEY", "")
    daily_webhook_segredo: str = os.getenv("DAILY_WEBHOOK_SEGREDO", "")
    escavador_webhook_token: str = os.getenv("ESCAVADOR_WEBHOOK_TOKEN", "fc-legal-os")

    # Fila / RPA
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rpa_headless: bool = os.getenv("RPA_HEADLESS", "true").lower() == "true"

    # DataJud CNJ — Radar Jurimétrico (chave pública oficial; troca rara)
    # `or` e não o segundo argumento do getenv: a variável existe no
    # .env do servidor, porém VAZIA, e o getenv devolve a string vazia
    # em vez do padrão. O resultado era um cabeçalho "APIKey " sem
    # chave, que o httpx recusa — e o radar semanal parou sem avisar.
    datajud_api_key: str = os.getenv("DATAJUD_API_KEY") or (
        "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
    )
    # Os tribunais onde o escritório atua (ver core/tribunais.py).
    # O radar e a consulta por número usam esta lista.
    datajud_tribunais: list[str] = [
        a.strip()
        for a in (os.getenv("DATAJUD_TRIBUNAIS")
                  or "tjro,tjsc,tjrs,tjpr,tjmt,tjba,tjsp,trt12,trt14,trf1,trf4"
                  ).split(",")
        if a.strip()
    ]
    # Agendamento semanal do radar (scheduler embutido no container da API)
    radar_auto: bool = os.getenv("RADAR_AUTO", "true").lower() == "true"
    radar_dia_semana: str = os.getenv("RADAR_DIA_SEMANA", "mon")  # mon..sun
    radar_hora: int = int(os.getenv("RADAR_HORA", "6"))           # 0-23 (UTC)

    # Código de acesso para cadastro de OPERADORES (equipe)
    equipe_codigo: str = os.getenv("EQUIPE_CODIGO", "")

    # Escalonamento humano
    humano_whatsapp: str = os.getenv("HUMANO_WHATSAPP", "")
    link_agenda_padrao: str = os.getenv("LINK_AGENDA", "")

    # Limiares do agente
    horas_sem_resposta_para_escalar: int = int(os.getenv("HORAS_ESCALAR_DEMORA", "48"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
