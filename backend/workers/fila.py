"""Fila de protocolos (Redis + RQ). Sem Redis, o worker faz polling na tabela."""
from redis import Redis
from rq import Queue

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.core.config import get_settings


def get_fila() -> Queue:
    return Queue("protocolos", connection=Redis.from_url(get_settings().redis_url))


def enfileirar_protocolo(caso_id: str, tribunal: str):
    from workers.rpa_eproc import executar_protocolo
    get_fila().enqueue(executar_protocolo, caso_id, tribunal,
                       job_timeout=900, retry=None)
