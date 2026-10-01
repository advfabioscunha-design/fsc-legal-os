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

    # A AGENDA DO ESCRITÓRIO VEM ANTES DE TUDO
    #
    # Quando alguém daqui salvou este telefone junto com o caso, a
    # conversa já começa sabendo de quem é e sobre o que é. É a melhor
    # identificação que existe neste fluxo, porque quem a fez foi gente
    # do escritório olhando o cadastro, e não alguém digitando um nome
    # num WhatsApp.
    #
    # Na prática isso muda o primeiro minuto do atendimento: o cliente
    # escreve "e aí, como ficou?" e recebe resposta sobre o caso dele,
    # em vez de um pedido de CPF.
    try:
        from ..agentes import identificacao as _ident
        salvo = _ident.na_agenda(numero)
    except Exception as e:
        print(f"[whatsapp] agenda de contatos não consultada: {e}")
        salvo = None

    cli = None
    if salvo and salvo.get("cliente_id"):
        try:
            cli = db.table("clientes").select("id,nome") \
                .eq("id", salvo["cliente_id"]).limit(1).execute().data
            cli = cli[0] if cli else None
        except Exception:
            cli = None

    if not cli:
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
            # O MESMO AGENTE DO CHAT RESPONDE AQUI
            #
            # Antes isto só pegava pedido PARADO esperando informação.
            # Quem estava negociando preço, ou esperando o pagamento, ou
            # lendo a minuta, caía no especialista do processo judicial
            # ou abria um caso novo: perguntava sobre desconto e recebia
            # resposta de outro assunto.
            #
            # Agora qualquer pedido em conversa entra por aqui, e quem
            # responde é o atendimento e a negociação da plataforma. O
            # chat e o WhatsApp são a mesma conversa, vista de dois
            # lugares, e o cliente não deve notar diferença nenhuma
            # entre falar por um ou por outro.
            pedido = balcao.pedido_em_conversa_do_cliente(cli["id"])
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

        # O caso que o escritório salvou para este telefone ganha do
        # "mais recente": quem salvou sabia de qual deles o cliente
        # costuma falar, e o mais recente pode ser outro assunto.
        caso = None
        if salvo and salvo.get("caso_id"):
            caso = db.table("casos").select("id") \
                .eq("id", salvo["caso_id"]).limit(1).execute().data
        if not caso:
            caso = db.table("casos").select("id").eq("cliente_id", cli["id"]) \
                     .not_.in_("estado", ["CONCLUIDO", "CANCELADO", "INVIAVEL"]) \
                     .order("criado_em", desc=True).limit(1).execute().data
        if caso:
            from ..agentes.especialista import atender
            r = atender(caso[0]["id"], texto, canal="WHATSAPP")
            if r.get("resposta"):
                responder_espelhando(numero, r["resposta"], eh_audio)
            return {"ok": True, "caso": caso[0]["id"], "audio": eh_audio}

    # ANTES DE TRATAR COMO GENTE NOVA, VER SE JÁ É CLIENTE
    #
    # Cliente antigo escreve do telefone da esposa, troca de número, ou
    # nunca usou o WhatsApp e só conhece o escritório pelo processo que
    # corre há dois anos. O número não está no cadastro, e até aqui ele
    # caía na triagem como lead: o sistema abria um caso NOVO e o agente
    # respondia como se nunca o tivesse visto.
    #
    # A regra de sigilo está em `identificacao`: CPF, e-mail, número do
    # processo ou protocolo abrem o andamento; nome ou descrição do caso
    # só servem para pedir a confirmação. Nome num WhatsApp qualquer um
    # digita, e responder a isso é entregar o processo de um cliente a
    # um estranho.
    try:
        from ..agentes import identificacao
        quem = identificacao.identificar(texto)
    except Exception as e:
        print(f"[whatsapp] identificação não rodou: {e}")
        quem = {"situacao": "nao_achou"}

    if quem.get("situacao") == "liberado" and quem.get("casos"):
        resposta = _resposta_de_quem_ja_e_cliente(numero, quem)
        responder_espelhando(numero, resposta, eh_audio)
        return {"ok": True, "identificado": quem.get("por"),
                "casos": len(quem["casos"]), "audio": eh_audio}

    if quem.get("situacao") == "confirmar":
        responder_espelhando(numero, (
            "Encontrei um cadastro que pode ser o seu, mas antes de falar "
            "do processo preciso confirmar que é você mesmo. Me manda o seu "
            "CPF, ou o número do processo, ou o número de atendimento que o "
            "escritório te passou. Qualquer um dos três serve."), eh_audio)
        return {"ok": True, "aguardando": "confirmacao", "audio": eh_audio}

    # número novo → triagem cria caso e o especialista responde
    from ..agentes.triagem import criar_caso
    r = criar_caso(nome=f"Lead {numero[-4:]}", contato=numero,
                   relato=texto, canal="WHATSAPP")

    # O CONVITE PARA A PLATAFORMA SAI NA PRIMEIRA RESPOSTA
    #
    # É o único momento em que ele não interrompe nada: a pessoa acabou
    # de escrever, está com o telefone na mão e ainda não tem onde
    # acompanhar o que pediu. Mandado depois, no meio de uma dúvida
    # sobre prazo, vira propaganda.
    #
    # O convite só existe para quem ainda não tem login. Quem já tem
    # recebe nada: mandar "crie seu acesso" para quem já é cadastrado é
    # dizer que o escritório não sabe com quem está falando.
    resposta = r.get("primeira_resposta") or ""
    if resposta:
        try:
            resposta += _convite_de_acesso(numero, r.get("caso_id"))
        except Exception as e:
            print(f"[whatsapp] convite de acesso não entrou: {e}")
        responder_espelhando(numero, resposta, eh_audio)
    return {"ok": True, "novo_caso": r["caso_id"], "audio": eh_audio}


def _convite_de_acesso(numero: str, caso_id: str | None) -> str:
    """O trecho com o link da plataforma. Vazio quando não cabe."""
    from .acesso_pelo_whatsapp import frase_do_convite
    db = get_db()
    cli = db.table("clientes").select("id").eq("whatsapp", numero) \
            .maybe_single().execute().data
    if not cli:
        return ""
    protocolo = ""
    if caso_id:
        try:
            c = db.table("casos").select("numero_atendimento") \
                  .eq("id", caso_id).limit(1).execute().data
            protocolo = (c[0].get("numero_atendimento") or "") if c else ""
        except Exception:
            protocolo = ""
    return frase_do_convite(cli["id"], protocolo)


def _resposta_de_quem_ja_e_cliente(numero: str, quem: dict) -> str:
    """O andamento, depois de a pessoa ter se identificado.

    COM MAIS DE UM CASO, NÃO SE ADIVINHA

    Dois processos do mesmo cliente são dois assuntos, e responder sobre
    o errado é pior do que perguntar. Aqui já se pode listar os
    protocolos: a pessoa provou quem é."""
    from ..agentes import identificacao
    casos = quem.get("casos") or []

    if len(casos) == 1:
        return (identificacao.andamento(casos[0])
                + " Se quiser ver os documentos e o histórico completo, me "
                  "avisa que eu te mando o acesso à plataforma.")

    linhas = []
    for c in casos[:6]:
        marca = (c.get("numero_atendimento")
                 or c.get("numero_processo") or "sem número")
        titulo = c.get("titulo") or c.get("grupo") or "caso"
        linhas.append(f"· {marca} — {titulo}")
    return ("Você tem mais de um caso com o escritório. Me diz sobre qual "
            "deles você quer saber, pelo número do processo ou pelo número "
            "de atendimento:\n" + "\n".join(linhas))
