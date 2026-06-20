"""
AGENTE DE RELACIONAMENTO — felicitações de aniversário aos clientes.

CRON diário: lê a data de nascimento dos clientes e dispara, via WhatsApp
(API do Meta), uma mensagem humanizada em nome da FC Advocacia.
Ativa automaticamente quando o WhatsApp Cloud API estiver configurado.
"""
from datetime import datetime, timezone
from ..core.db import get_db, registrar_evento

MSG = (
    "🎉 Feliz aniversário, {nome}! "
    "Toda a equipe da FC Advocacia deseja a você um dia muito especial, cheio de "
    "saúde, paz e realizações. É uma honra cuidar dos seus direitos. Conte sempre "
    "conosco! 🙏\n— Dr. Fábio Cunha e equipe FC Advocacia"
)


def parabenizar_aniversariantes() -> dict:
    db = get_db()
    hoje = datetime.now(timezone.utc).strftime("%m-%d")
    try:
        clientes = db.table("clientes").select("id,nome,whatsapp,data_nascimento").execute().data
    except Exception:
        return {"enviados": 0, "erro": "coluna data_nascimento ainda não criada"}

    from ..integracoes.whatsapp import _enviar
    enviados = 0
    for c in clientes:
        dn = str(c.get("data_nascimento") or "")
        numero = c.get("whatsapp")
        if len(dn) >= 10 and numero and dn[5:10] == hoje:
            primeiro = (c.get("nome") or "").split(" ")[0] or "tudo bem"
            try:
                _enviar(numero, MSG.format(nome=primeiro))
                enviados += 1
            except Exception:
                pass  # WhatsApp não configurado ainda → ignora silenciosamente
    registrar_evento(None, "ANIVERSARIOS_ENVIADOS", {"total": enviados, "data": hoje})
    return {"enviados": enviados}
