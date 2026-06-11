"""
VOZ DO AGENTE — transcrição (cliente fala) e síntese (agente responde
com a voz clonada do Dr. Fábio Cunha).

STT: OpenAI Whisper API (se OPENAI_API_KEY) ou faster-whisper local na VPS.
TTS: ElevenLabs com voice clone do Dr. Fábio (ELEVENLABS_VOICE_ID).
     Saída convertida para OGG/Opus (formato exigido pelo WhatsApp).

IMPORTANTE (transparência/OAB): recomenda-se que a 1ª mensagem da conversa
informe que o atendimento é feito pelo assistente digital do escritório,
supervisionado pelo Dr. Fábio Cunha. Controlado por AVISO_ASSISTENTE=true.
"""
import os
import subprocess
import tempfile
import httpx
from ..core.config import get_settings


# ── STT: áudio do cliente → texto ────────────────────────────────
def transcrever(caminho_audio: str) -> str:
    s = get_settings()
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if openai_key:  # Whisper API (rápido, ~US$0.006/min)
        with open(caminho_audio, "rb") as f:
            r = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {openai_key}"},
                data={"model": "whisper-1", "language": "pt"},
                files={"file": (os.path.basename(caminho_audio), f)},
                timeout=120,
            )
        r.raise_for_status()
        return r.json()["text"].strip()

    # Fallback: faster-whisper local (sem custo por uso; CPU da VPS)
    from faster_whisper import WhisperModel
    model = WhisperModel(os.getenv("WHISPER_MODELO", "small"),
                         device="cpu", compute_type="int8")
    segs, _ = model.transcribe(caminho_audio, language="pt")
    return " ".join(seg.text for seg in segs).strip()


# ── TTS: texto do agente → áudio com a voz do Dr. Fábio ─────────
def sintetizar_voz_fabio(texto: str) -> str:
    """Gera OGG/Opus com a voz clonada. Retorna o caminho do arquivo."""
    s = get_settings()
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
    if not (api_key and voice_id):
        raise RuntimeError("ElevenLabs não configurado (API key / voice id)")

    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key},
        json={
            "text": texto[:2500],
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.8,
                               "style": 0.25, "use_speaker_boost": True},
        },
        timeout=120,
    )
    r.raise_for_status()

    mp3 = tempfile.mktemp(suffix=".mp3")
    ogg = tempfile.mktemp(suffix=".ogg")
    with open(mp3, "wb") as f:
        f.write(r.content)

    # WhatsApp exige OGG/Opus para mensagem de voz
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3, "-c:a", "libopus",
         "-b:a", "24k", "-ar", "16000", "-ac", "1", ogg],
        check=True, capture_output=True,
    )
    os.unlink(mp3)
    return ogg


def texto_para_fala(texto: str) -> str:
    """Adapta texto escrito para soar natural falado (remove markdown,
    listas viram frases corridas, encurta)."""
    import re
    t = re.sub(r"[*_#`]", "", texto)
    t = re.sub(r"^\s*[-•\d]+[\.\)]?\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\n{2,}", ". ", t).replace("\n", " ")
    return t.strip()
