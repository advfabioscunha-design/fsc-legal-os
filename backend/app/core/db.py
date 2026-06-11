"""Cliente Supabase único (service role — uso exclusivo do backend)."""
from functools import lru_cache
from supabase import create_client, Client
from .config import get_settings


@lru_cache
def get_db() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_key)


def registrar_evento(caso_id: str | None, tipo: str, payload: dict | None = None):
    """Trilha de auditoria universal."""
    get_db().table("eventos").insert(
        {"caso_id": caso_id, "tipo": tipo, "payload": payload or {}}
    ).execute()
