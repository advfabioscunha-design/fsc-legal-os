"""
ATENDIMENTO TELEPRESENCIAL — o fluxo do encontro.

    advogado abre → cliente recebe o link → aceita a gravação → conversam
    → advogado grava → encerra → o áudio cai na pasta do caso → transcreve
    → a transcrição entra no histórico do atendimento

Duas regras que atravessam o módulo:

1. SEM ACEITE, SEM GRAVAÇÃO. A sala abre do mesmo jeito — o cliente que
   não quer ser gravado continua sendo atendido —, mas o botão de gravar
   fica travado do lado do servidor, não só na tela.

2. O ÁUDIO NÃO FICA COM TERCEIRO. Assim que o arquivo é guardado na pasta
   do caso, a cópia na Daily é apagada. Consulta coberta por sigilo não
   tem por que morar em servidor de fornecedor.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone as _tz

import httpx

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..integracoes import daily

VERSAO_CONSENTIMENTO = "2026-09-v2"

# O texto abaixo é o que o cliente lê antes de entrar. Ele foi reescrito
# para descrever as proteções que de fato existem, em vez de abrir com um
# aviso de transferência internacional que assustava sem informar.
#
# O que este texto NÃO afirma: que os dados ficam "no escritório" ou "no
# Brasil". Não ficam — a infraestrutura está nos Estados Unidos, e um
# consentimento que descreve errado onde o dado é tratado é consentimento
# viciado (LGPD, arts. 9º e 33), com o ônus recaindo sobre o advogado.
#
# A localização também não aparece aqui, por decisão do escritório: um
# aviso de transferência internacional no meio do termo de gravação
# assusta sem informar. Ela está na POLÍTICA DE PRIVACIDADE (/privacidade),
# que é o documento próprio para isso e para onde o contrato remete. A
# informação não pode simplesmente deixar de existir: sem ela em lugar
# algum, o consentimento não alcança a transferência.
TEXTO_CONSENTIMENTO = (
    "Este atendimento é feito por vídeo, ao vivo. Para que o escritório "
    "tenha registro fiel do que foi conversado, **somente o áudio** é "
    "gravado — a sua imagem não é gravada nem armazenada em momento algum.\n\n"

    "COMO O SEU ATENDIMENTO É PROTEGIDO\n"
    "• A gravação e a transcrição ficam em **banco de dados exclusivo deste "
    "escritório**, com armazenamento criptografado e acesso por chave de "
    "segurança — não são compartilhadas com nenhum outro escritório, "
    "empresa ou plataforma de terceiros.\n"
    "• O acesso é **individual e identificado**: cada integrante da equipe "
    "entra com a própria credencial, e todo acesso fica registrado.\n"
    "• A sua área de cliente é isolada por controle técnico: **você enxerga "
    "apenas o seu processo**, e nenhum outro cliente enxerga o seu.\n"
    "• A conexão é criptografada de ponta a ponta do seu navegador até o "
    "sistema.\n"
    "• Assim que a gravação é arquivada no seu processo, a **cópia no "
    "serviço de videochamada é apagada** — o áudio não fica com o "
    "fornecedor.\n"
    "• Tudo está coberto pelo **sigilo profissional do advogado** (art. 34, "
    "VII, da Lei 8.906/94), que é dever legal e não mera política interna.\n\n"

    "Você pode recusar: o atendimento acontece do mesmo jeito, apenas sem "
    "gravação. E pode pedir a exclusão do áudio a qualquer momento."
)


def _agora():
    return datetime.now(_tz.utc)


def _iso(d):
    return d.isoformat()


# ── Abrir o atendimento ──────────────────────────────────────────
def abrir(caso_id: str, horas: int = 3) -> dict:
    """Cria a sala e devolve o acesso do advogado. O link do cliente é
    gerado só quando ele aceitar (ou recusar) a gravação."""
    db = get_db()
    caso = db.table("casos").select(
        "id,numero_atendimento,titulo,cliente_id,clientes(nome)"
    ).eq("id", caso_id).single().execute().data
    if not caso:
        raise ValueError("Caso não encontrado.")

    sala = daily.criar_sala(validade_s=horas * 3600)
    s = get_settings()
    token = daily.token_advogado(sala["nome"], s.advogado, sala["expira_em"],
                                 com_gravacao=sala.get("gravacao_disponivel", True))

    linha = db.table("atendimentos").insert({
        "caso_id": caso_id,
        "cliente_id": caso.get("cliente_id"),
        "sala_nome": sala["nome"], "sala_url": sala["url"],
        "expira_em": _iso(datetime.fromtimestamp(sala["expira_em"], _tz.utc)),
        "status": "AGENDADO",
    }).execute().data[0]

    registrar_evento(caso_id, "ATENDIMENTO_ABERTO",
                     {"atendimento_id": linha["id"], "sala": sala["nome"],
                      "gravacao_disponivel": sala.get("gravacao_disponivel")})
    # o cliente é avisado pelos canais que já existem — painel e e-mail
    link = f"{s.app_url}/atendimento/{linha['id']}"
    try:
        from ..integracoes import avisos
        avisos.notificar(
            caso_id, "ATENDIMENTO", "Seu atendimento por vídeo está pronto",
            "O escritório abriu uma sala para falar com você por vídeo.\n\n"
            f"É só clicar e entrar, direto pelo navegador — sem instalar nada "
            f"e sem criar conta:\n{link}\n\n"
            "Antes de entrar você escolhe se autoriza a gravação do áudio. "
            "O link vale por algumas horas.",
        )
    except Exception:
        pass
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "PORTAL", "autor": "HUMANO",
            "conteudo": "📹 Seu atendimento por vídeo está pronto. "
                        f"Clique para entrar: {link}",
        }).execute()
    except Exception:
        pass

    aviso = "" if sala.get("gravacao_disponivel", True) else (
        "A sala está no ar, mas a GRAVAÇÃO está indisponível: o plano atual "
        "do Daily não permite gravar. Cadastre um cartão no painel do Daily "
        "(contas novas ganham US$ 15 de crédito) e a gravação passa a "
        "funcionar sozinha no próximo atendimento.")
    return {"ok": True, "atendimento": linha, "url": sala["url"],
            "token": token,
            "gravacao_disponivel": sala.get("gravacao_disponivel", True),
            "aviso": aviso,
            "link_cliente": link}


def para_o_cliente(atendimento_id: str) -> dict:
    """O que o painel do cliente precisa para montar a tela de entrada."""
    db = get_db()
    a = db.table("atendimentos").select(
        "id,caso_id,sala_url,status,expira_em,consentimento_em"
    ).eq("id", atendimento_id).single().execute().data
    if not a:
        raise ValueError("Atendimento não encontrado.")
    expirado = False
    if a.get("expira_em"):
        try:
            expirado = datetime.fromisoformat(
                str(a["expira_em"]).replace("Z", "+00:00")) < _agora()
        except Exception:
            expirado = False
    return {"ok": True, "atendimento_id": a["id"], "status": a["status"],
            "expirado": expirado,
            "ja_consentiu": bool(a.get("consentimento_em")),
            "texto_consentimento": TEXTO_CONSENTIMENTO,
            "versao_consentimento": VERSAO_CONSENTIMENTO}


def entrar(atendimento_id: str, nome: str, aceita_gravacao: bool,
           ip: str | None = None) -> dict:
    """Registra a decisão do cliente e devolve o token de entrada.

    Recusar não impede o atendimento. O que muda é que a sala segue sem
    gravação — e isso fica registrado, com hora e IP."""
    db = get_db()
    a = db.table("atendimentos").select("*").eq("id", atendimento_id) \
          .single().execute().data
    if not a:
        raise ValueError("Atendimento não encontrado.")

    agora = _agora()
    if a.get("expira_em"):
        try:
            if datetime.fromisoformat(
                    str(a["expira_em"]).replace("Z", "+00:00")) < agora:
                raise ValueError("Este link de atendimento expirou. "
                                 "Peça um novo ao escritório.")
        except ValueError:
            raise
        except Exception:
            pass

    mudanca = {"status": "EM_ANDAMENTO", "atualizado_em": _iso(agora)}
    if not a.get("iniciado_em"):
        mudanca["iniciado_em"] = _iso(agora)
    if aceita_gravacao:
        mudanca.update({
            "consentimento_em": _iso(agora),
            "consentimento_ip": (ip or "")[:60] or None,
            "consentimento_texto": TEXTO_CONSENTIMENTO,
            "consentimento_versao": VERSAO_CONSENTIMENTO,
        })
    db.table("atendimentos").update(mudanca).eq("id", atendimento_id).execute()

    expira = int(time.time()) + 4 * 3600
    token = daily.token_cliente(a["sala_nome"], (nome or "Cliente")[:60], expira)
    registrar_evento(a["caso_id"], "ATENDIMENTO_CLIENTE_ENTROU",
                     {"atendimento_id": atendimento_id,
                      "consentiu_gravacao": bool(aceita_gravacao)})
    return {"ok": True, "url": a["sala_url"], "token": token,
            "pode_gravar": bool(aceita_gravacao)}


def pode_gravar(atendimento_id: str) -> dict:
    """A trava do lado do servidor: o CRM consulta antes de mostrar o botão,
    e o encerramento confere de novo."""
    db = get_db()
    a = db.table("atendimentos").select("consentimento_em") \
          .eq("id", atendimento_id).single().execute().data or {}
    ok = bool(a.get("consentimento_em"))
    return {"pode_gravar": ok,
            "motivo": "" if ok else
                      "O cliente ainda não autorizou a gravação do áudio."}


def encerrar(atendimento_id: str, observacao: str | None = None) -> dict:
    db = get_db()
    a = db.table("atendimentos").select("*").eq("id", atendimento_id) \
          .single().execute().data
    if not a:
        raise ValueError("Atendimento não encontrado.")
    agora = _agora()
    dur = None
    if a.get("iniciado_em"):
        try:
            ini = datetime.fromisoformat(
                str(a["iniciado_em"]).replace("Z", "+00:00"))
            dur = int((agora - ini).total_seconds())
        except Exception:
            dur = None
    db.table("atendimentos").update({
        "status": "ENCERRADO", "encerrado_em": _iso(agora),
        "duracao_segundos": dur, "observacao": observacao or a.get("observacao"),
        "atualizado_em": _iso(agora),
    }).eq("id", atendimento_id).execute()
    daily.excluir_sala(a["sala_nome"])     # a sala não sobrevive ao encontro
    registrar_evento(a["caso_id"], "ATENDIMENTO_ENCERRADO",
                     {"atendimento_id": atendimento_id, "duracao_s": dur})
    return {"ok": True, "duracao_segundos": dur}


# ── Quando a gravação fica pronta ────────────────────────────────
def guardar_gravacao(gravacao_id: str, sala: str | None = None) -> dict:
    """Baixa o .m4a, guarda na pasta do caso, apaga a cópia da Daily e
    manda transcrever. Chamado pelo webhook e reutilizável na mão."""
    s = get_settings()
    db = get_db()

    consulta = db.table("atendimentos").select("*")
    a = (consulta.eq("gravacao_id", gravacao_id).limit(1).execute().data or [None])[0]
    if not a and sala:
        a = (db.table("atendimentos").select("*").eq("sala_nome", sala)
             .order("criado_em", desc=True).limit(1).execute().data or [None])[0]
    if not a:
        return {"ok": False, "motivo": "gravação não corresponde a nenhum atendimento"}

    if a.get("audio_path"):
        return {"ok": True, "info": "áudio já guardado", "audio_path": a["audio_path"]}

    # sem consentimento registrado, o áudio não entra no acervo
    if not a.get("consentimento_em"):
        daily.excluir_gravacao(gravacao_id)
        db.table("atendimentos").update({
            "erro": "gravação descartada: não havia consentimento registrado",
            "atualizado_em": _iso(_agora()),
        }).eq("id", a["id"]).execute()
        registrar_evento(a["caso_id"], "GRAVACAO_DESCARTADA_SEM_CONSENTIMENTO",
                         {"atendimento_id": a["id"]})
        return {"ok": False, "motivo": "sem consentimento — gravação descartada"}

    try:
        link = daily.link_de_download(gravacao_id)
        if not link:
            raise RuntimeError("link de download vazio")
        with httpx.stream("GET", link, timeout=180, follow_redirects=True) as r:
            r.raise_for_status()
            conteudo = b"".join(r.iter_bytes())
    except Exception as e:
        db.table("atendimentos").update({
            "status": "FALHOU", "erro": f"download do áudio: {str(e)[:200]}",
            "atualizado_em": _iso(_agora()),
        }).eq("id", a["id"]).execute()
        return {"ok": False, "motivo": str(e)[:200]}

    path = f"{a['caso_id']}/atendimentos/{uuid.uuid4().hex}.m4a"
    db.storage.from_(s.bucket_documentos).upload(
        path, conteudo, {"content-type": "audio/mp4", "upsert": "true"})

    db.table("atendimentos").update({
        "gravacao_id": gravacao_id, "audio_path": path,
        "atualizado_em": _iso(_agora()),
    }).eq("id", a["id"]).execute()

    # o áudio agora é nosso; a cópia do fornecedor sai
    daily.excluir_gravacao(gravacao_id)

    try:
        db.table("documentos").insert({
            "caso_id": a["caso_id"], "tipo": "AUDIO_ATENDIMENTO",
            "storage_path": path, "status": "RECEBIDO",
            "observacao": "Áudio do atendimento telepresencial",
        }).execute()
    except Exception:
        pass

    registrar_evento(a["caso_id"], "AUDIO_ATENDIMENTO_GUARDADO",
                     {"atendimento_id": a["id"], "bytes": len(conteudo)})
    resultado = transcrever(a["id"])
    return {"ok": True, "audio_path": path, "transcricao": resultado}


def transcrever(atendimento_id: str) -> dict:
    """Transcreve o áudio guardado e anexa ao histórico do caso.

    A transcrição é REGISTRO do atendimento. Não alimenta cadastro: os
    dados de contrato e procuração vêm dos documentos, da conversa escrita
    ou do lançamento direto."""
    import os
    import tempfile

    from ..integracoes import audio as voz
    s = get_settings()
    db = get_db()
    a = db.table("atendimentos").select("*").eq("id", atendimento_id) \
          .single().execute().data
    if not a or not a.get("audio_path"):
        return {"ok": False, "motivo": "não há áudio guardado neste atendimento"}

    try:
        dados = db.storage.from_(s.bucket_documentos).download(a["audio_path"])
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            f.write(dados)
            caminho = f.name
        texto = (voz.transcrever(caminho) or "").strip()
        os.unlink(caminho)
    except Exception as e:
        db.table("atendimentos").update({
            "erro": f"transcrição: {str(e)[:200]}",
            "atualizado_em": _iso(_agora()),
        }).eq("id", atendimento_id).execute()
        return {"ok": False, "motivo": str(e)[:200]}

    if not texto:
        return {"ok": False, "motivo": "a transcrição voltou vazia"}

    db.table("atendimentos").update({
        "transcricao": texto, "transcrito_em": _iso(_agora()),
        "status": "TRANSCRITO", "erro": None,
        "atualizado_em": _iso(_agora()),
    }).eq("id", atendimento_id).execute()

    try:
        db.table("mensagens").insert({
            "caso_id": a["caso_id"], "canal": "CRM", "autor": "HUMANO",
            "conteudo": "🎙 Atendimento por vídeo transcrito. "
                        f"{len(texto.split())} palavras registradas no caso.",
        }).execute()
    except Exception:
        pass

    registrar_evento(a["caso_id"], "ATENDIMENTO_TRANSCRITO",
                     {"atendimento_id": atendimento_id, "caracteres": len(texto)})
    return {"ok": True, "caracteres": len(texto)}


# ── Webhook ──────────────────────────────────────────────────────
def processar_webhook(payload: dict) -> dict:
    """Trata os eventos do Daily. O que nos interessa é a gravação pronta."""
    tipo = (payload.get("type") or payload.get("event") or "").lower()
    dados = payload.get("payload") or payload.get("data") or payload
    gravacao = (dados.get("recording_id") or dados.get("id") or "")
    sala = dados.get("room_name") or dados.get("room")

    if "recording" in tipo and ("ready" in tipo or "finished" in tipo):
        if not gravacao:
            return {"ok": False, "motivo": "evento sem id de gravação"}
        return guardar_gravacao(gravacao, sala)

    return {"ok": True, "ignorado": tipo or "evento desconhecido"}
