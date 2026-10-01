"""WhatsApp Cloud API — canal do cliente e alertas ao advogado."""
import httpx
from ..core.config import get_settings
from ..core.db import get_db

GRAPH = "https://graph.facebook.com/v21.0"


def _enviar(numero: str, texto: str):
    s = get_settings()
    if not (s.whatsapp_token and s.whatsapp_phone_id and numero):
        raise RuntimeError("WhatsApp não configurado")
    r = httpx.post(
        f"{GRAPH}/{s.whatsapp_phone_id}/messages",
        headers={"Authorization": f"Bearer {s.whatsapp_token}"},
        json={"messaging_product": "whatsapp", "to": numero,
              "type": "text", "text": {"body": texto[:4000]}},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ── ÁUDIO: baixar do cliente e enviar com a voz do Dr. Fábio ────
def _baixar_midia(media_id: str) -> str:
    """Baixa um áudio recebido (Graph API) e retorna o caminho local."""
    import tempfile
    s = get_settings()
    h = {"Authorization": f"Bearer {s.whatsapp_token}"}
    meta = httpx.get(f"{GRAPH}/{media_id}", headers=h, timeout=30).json()
    blob = httpx.get(meta["url"], headers=h, timeout=60).content
    caminho = tempfile.mktemp(suffix=".ogg")
    with open(caminho, "wb") as f:
        f.write(blob)
    return caminho


def _enviar_audio(numero: str, caminho_ogg: str):
    """Sobe o OGG/Opus e envia como mensagem de VOZ."""
    s = get_settings()
    h = {"Authorization": f"Bearer {s.whatsapp_token}"}
    with open(caminho_ogg, "rb") as f:
        up = httpx.post(
            f"{GRAPH}/{s.whatsapp_phone_id}/media", headers=h,
            data={"messaging_product": "whatsapp", "type": "audio/ogg"},
            files={"file": ("voz.ogg", f, "audio/ogg; codecs=opus")},
            timeout=60,
        )
    up.raise_for_status()
    r = httpx.post(
        f"{GRAPH}/{s.whatsapp_phone_id}/messages", headers=h,
        json={"messaging_product": "whatsapp", "to": numero,
              "type": "audio", "audio": {"id": up.json()["id"]}},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def responder_espelhando(numero: str, texto: str, cliente_mandou_audio: bool):
    """Espelha o canal do cliente: áudio → responde com a VOZ do
    Dr. Fábio Cunha (ElevenLabs); texto → responde texto.
    Se a síntese falhar, degrada para texto (nunca deixa sem resposta)."""
    import os as _os
    if cliente_mandou_audio:
        try:
            from .audio import sintetizar_voz_fabio, texto_para_fala
            ogg = sintetizar_voz_fabio(texto_para_fala(texto))
            _enviar_audio(numero, ogg)
            _os.unlink(ogg)
            return
        except Exception:
            pass
    _enviar(numero, texto)


def enviar_para_cliente(caso_id: str, texto: str):
    db = get_db()
    caso = db.table("casos").select("clientes(whatsapp)").eq("id", caso_id) \
             .single().execute().data
    numero = (caso.get("clientes") or {}).get("whatsapp")
    if numero:
        _enviar(numero, texto)
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "WHATSAPP",
            "autor": "AGENTE", "conteudo": texto
        }).execute()


def notificar_humano(texto: str):
    """Alerta o advogado (escalações, falha de protocolo etc.)."""
    s = get_settings()
    if s.humano_whatsapp:
        _enviar(s.humano_whatsapp, texto)


def processar_webhook(payload: dict) -> dict:
    """Mensagem recebida no WhatsApp (texto OU áudio) → roteia para o
    caso ativo do número, ou cria novo lead via triagem. Áudios são
    transcritos; a resposta espelha o canal (áudio → voz do Dr. Fábio)."""
    try:
        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = msg["from"]
        eh_audio = msg.get("type") == "audio"
        if eh_audio:
            caminho = _baixar_midia(msg["audio"]["id"])
            from .audio import transcrever
            texto = transcrever(caminho)
            import os as _os
            _os.unlink(caminho)
        else:
            texto = msg.get("text", {}).get("body", "")
        if not texto:
            return {"ok": True, "ignorado": "mensagem vazia"}
    except (KeyError, IndexError):
        return {"ok": True, "ignorado": "sem mensagem"}

    db = get_db()
    cli = db.table("clientes").select("id,nome").eq("whatsapp", numero) \
            .maybe_single().execute().data

    if cli:
        # O BALCÃO VEM ANTES DO CASO
        #
        # Se este cliente tem um pedido de contrato parado esperando
        # informação, é quase certo que a mensagem é sobre ele: foi o
        # que o escritório cobrou por aqui há poucas horas. Mandar para
        # o especialista do processo faria a informação chegar no lugar
        # errado e o relógio do pedido continuar parado.
        #
        # Só vale com UM pedido parado. Com dois, não se adivinha, e a
        # conversa segue o caminho normal.
        try:
            from ..agentes import contratos_online as balcao
            pedido = balcao.pedido_travado_do_cliente(cli["id"])
            if pedido:
                r = balcao.resposta_do_cliente(pedido["id"], texto,
                                               canal="WHATSAPP")

                # UMA RESPOSTA SÓ, E A MELHOR DELAS
                #
                # O balcão já respondeu e já mandou pelo WhatsApp: chat e
                # WhatsApp são a mesma conversa, e tudo o que entra nela
                # sai nos dois. Mandar aqui a frase genérica de recibo
                # faria o cliente receber duas mensagens seguidas, a
                # segunda dizendo bem menos que a primeira.
                #
                # A frase de recibo continua existindo para o caso em que
                # o agente não conseguiu responder, e para quando o
                # humano assumiu a conversa: aí o cliente precisa saber
                # que a mensagem chegou, mesmo sem resposta ainda.
                if r.get("resposta"):
                    return {"ok": True, "pedido": pedido["id"],
                            "audio": eh_audio, "respondeu": "agente"}

                if r.get("com_humano"):
                    resposta = ("Recebi a sua mensagem. O escritório está "
                                "acompanhando e responde já.")
                elif r.get("preenchidos"):
                    resposta = ("Recebido, obrigado. Já estou complementando o "
                                "seu documento com essa informação.")
                elif r.get("ainda_falta"):
                    resposta = ("Recebi a sua mensagem e anotei no seu pedido. "
                                "Ainda falta alguma informação; o escritório "
                                "confere e retorna.")
                else:
                    resposta = ("Recebi a sua mensagem e anotei no seu pedido. "
                                "O escritório já está com ela.")
                responder_espelhando(numero, resposta, eh_audio)
                return {"ok": True, "pedido": pedido["id"], "audio": eh_audio}
        except Exception as e:
            print(f"[whatsapp] balcão não tratou, segue para o caso: {e}")

        caso = db.table("casos").select("id").eq("cliente_id", cli["id"]) \
                 .not_.in_("estado", ["CONCLUIDO", "CANCELADO", "INVIAVEL"]) \
                 .order("criado_em", desc=True).limit(1).execute().data
        if caso:
            from ..agentes.especialista import atender
            r = atender(caso[0]["id"], texto, canal="WHATSAPP")
            if r.get("resposta"):
                responder_espelhando(numero, r["resposta"], eh_audio)
            return {"ok": True, "caso": caso[0]["id"], "audio": eh_audio}

    # número novo → triagem cria caso e o especialista responde
    from ..agentes.triagem import criar_caso
    r = criar_caso(nome=f"Lead {numero[-4:]}", contato=numero,
                   relato=texto, canal="WHATSAPP")
    if r.get("primeira_resposta"):
        responder_espelhando(numero, r["primeira_resposta"], eh_audio)
    return {"ok": True, "novo_caso": r["caso_id"], "audio": eh_audio}
