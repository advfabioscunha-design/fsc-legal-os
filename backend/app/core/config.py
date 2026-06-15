"""Configuração central do backend — tudo via variáveis de ambiente."""
import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    # Identidade
    advogado: str = os.getenv("ADVOGADO_NOME", "Fábio Silva Cunha")
    oab: str = os.getenv("OAB", "OAB/RO 10.849")
    email_escritorio: str = os.getenv("EMAIL_ESCRITORIO",
                                      "contato@fscadvocaciadigital.com.br")
    ambiente: str = os.getenv("AMBIENTE", "dev")  # dev | staging | prod

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
    bucket_documentos: str = os.getenv("BUCKET_DOCUMENTOS", "documentos")

    # Claude
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-5")
    claude_model_rapido: str = os.getenv("CLAUDE_MODEL_RAPIDO", "claude-haiku-4-5-20251001")

    # Integrações
    asaas_api_key: str = os.getenv("ASAAS_API_KEY", "")
    asaas_base_url: str = os.getenv("ASAAS_BASE_URL", "https://api.asaas.com/v3")
    zapsign_api_token: str = os.getenv("ZAPSIGN_API_TOKEN", "")
    zapsign_base_url: str = os.getenv("ZAPSIGN_BASE_URL", "https://api.zapsign.com.br/api/v1")
    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_phone_id: str = os.getenv("WHATSAPP_PHONE_ID", "")

    # Fila / RPA
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rpa_headless: bool = os.getenv("RPA_HEADLESS", "true").lower() == "true"

    # DataJud CNJ — Radar Jurimétrico (chave pública oficial; troca rara)
    datajud_api_key: str = os.getenv(
        "DATAJUD_API_KEY",
        "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
    )
    datajud_tribunais: list[str] = [
        a.strip()
        for a in os.getenv("DATAJUD_TRIBUNAIS", "tjro,trt14").split(",")
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
