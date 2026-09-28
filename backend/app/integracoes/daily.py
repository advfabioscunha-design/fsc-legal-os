"""
DAILY — sala de atendimento telepresencial.

Desenho combinado com o escritório:

  * VÍDEO ao vivo, para o atendimento ser humano — o advogado vê o cliente
    e o cliente vê o advogado.
  * GRAVAÇÃO só de áudio (`cloud-audio-only`, arquivo .m4a). Nenhum vídeo
    é gravado, em lugar nenhum. Imagem de cliente não vira arquivo.
  * SÓ O ADVOGADO PODE GRAVAR. A permissão vai no token dele, nunca na
    sala: o cliente não tem o direito, não é questão de esconder botão.
  * SALA DESCARTÁVEL. Cada atendimento cria a sua, com validade curta e
    nome que não revela nada do cliente.

Sobre entrar: o cliente recebe um link e um token. Clica, autoriza o
microfone e a câmera, e está na sala. Sem aplicativo, sem cadastro, sem
senha — que era o requisito.
"""
from __future__ import annotations

import secrets
import time

import httpx

from ..core.config import get_settings

BASE = "https://api.daily.co/v1"
# atendimento longo é raro; 3h é o teto da própria Daily para gravação
VALIDADE_PADRAO_S = 3 * 60 * 60


class DailyIndisponivel(RuntimeError):
    """A API do Daily não respondeu ou recusou a operação."""


def _headers() -> dict:
    s = get_settings()
    if not s.daily_api_key:
        raise DailyIndisponivel(
            "A chave da API do Daily não está configurada (DAILY_API_KEY).")
    return {"Authorization": f"Bearer {s.daily_api_key}",
            "Content-Type": "application/json"}


def _post(caminho: str, payload: dict) -> dict:
    try:
        r = httpx.post(f"{BASE}{caminho}", headers=_headers(),
                       json=payload, timeout=25)
    except DailyIndisponivel:
        raise
    except Exception as e:
        raise DailyIndisponivel(f"falha de rede ao falar com o Daily: {e}")
    if r.status_code >= 400:
        raise DailyIndisponivel(f"Daily respondeu {r.status_code}: {r.text[:300]}")
    return r.json()


# ── Sala ─────────────────────────────────────────────────────────
def criar_sala(validade_s: int = VALIDADE_PADRAO_S) -> dict:
    """Cria uma sala privada e descartável para um atendimento.

    O nome é aleatório de propósito: nome de sala aparece em URL, log e
    histórico de navegador, e não deve dizer quem é o cliente nem de que
    trata o caso.
    """
    nome = f"fsc-{secrets.token_hex(8)}"
    expira = int(time.time()) + validade_s
    sala = _post("/rooms", {
        "name": nome,
        "privacy": "private",          # só entra com token
        "properties": {
            "exp": expira,
            "eject_at_room_exp": True,
            # gravação de áudio: quem pode disparar é definido no token
            "enable_recording": "cloud-audio-only",
            "enable_chat": False,
            "enable_screenshare": True,   # útil para mostrar documento
            "enable_prejoin_ui": True,    # testa câmera e microfone antes
            "start_video_off": False,
            "start_audio_off": False,
            "max_participants": 4,        # advogado, cliente e folga
        },
    })
    return {"nome": sala["name"], "url": sala["url"], "expira_em": expira}


def excluir_sala(nome: str) -> bool:
    """Sala expirada não some sozinha do painel; apagamos ao encerrar."""
    try:
        r = httpx.delete(f"{BASE}/rooms/{nome}", headers=_headers(), timeout=20)
        return r.status_code < 400
    except Exception:
        return False


# ── Tokens de entrada ────────────────────────────────────────────
def token_advogado(sala: str, nome_exibicao: str, expira_em: int) -> str:
    """Token do advogado: dono da sala e ÚNICO que pode gravar."""
    d = _post("/meeting-tokens", {"properties": {
        "room_name": sala,
        "user_name": nome_exibicao,
        "is_owner": True,
        "enable_recording": "cloud-audio-only",
        "exp": expira_em,
    }})
    return d["token"]


def token_cliente(sala: str, nome_exibicao: str, expira_em: int) -> str:
    """Token do cliente: entra e conversa, mas não grava e não administra.

    `enable_recording` vai explicitamente como False — não basta omitir,
    porque a propriedade da sala poderia valer como padrão."""
    d = _post("/meeting-tokens", {"properties": {
        "room_name": sala,
        "user_name": nome_exibicao,
        "is_owner": False,
        "enable_recording": False,
        "exp": expira_em,
    }})
    return d["token"]


# ── Gravação ─────────────────────────────────────────────────────
def buscar_gravacao(gravacao_id: str) -> dict:
    try:
        r = httpx.get(f"{BASE}/recordings/{gravacao_id}",
                      headers=_headers(), timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise DailyIndisponivel(f"não foi possível ler a gravação: {e}")


def link_de_download(gravacao_id: str) -> str:
    """Link temporário para baixar o .m4a. Vale poucos minutos — é por isso
    que baixamos e guardamos no nosso storage em vez de referenciar."""
    try:
        r = httpx.get(f"{BASE}/recordings/{gravacao_id}/access-link",
                      headers=_headers(), timeout=25)
        r.raise_for_status()
        return r.json().get("download_link") or ""
    except Exception as e:
        raise DailyIndisponivel(f"não foi possível obter o link: {e}")


def excluir_gravacao(gravacao_id: str) -> bool:
    """Depois de guardar o áudio no nosso storage, a cópia na Daily sai.

    O arquivo de uma consulta coberta por sigilo não tem por que continuar
    em servidor de terceiro."""
    try:
        r = httpx.delete(f"{BASE}/recordings/{gravacao_id}",
                         headers=_headers(), timeout=20)
        return r.status_code < 400
    except Exception:
        return False
