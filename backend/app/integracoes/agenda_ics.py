"""
Convites de agenda (.ics) — o prazo entra no calendário de quem precisa.

Um arquivo iCalendar anexado ao e-mail é aceito pelo Gmail, Outlook,
Apple Calendar e Android sem integração nenhuma: o destinatário abre e o
compromisso já está no calendário dele, com alarme.

Duas decisões que estão no código e convém saber:

  · O evento é de DIA INTEIRO na data de TRABALHO (o prazo fatal menos
    dois dias úteis), e o corpo do convite diz qual é o prazo fatal.
    Marcar o dia do vencimento seria marcar o dia em que já é tarde.

  · O cliente só recebe convite do que depende dele — audiência, perícia,
    documento, comparecimento. Prazo de peça é obrigação do advogado, e
    despejar prazo processual na agenda do cliente gera aflição sem
    utilidade, além de sugerir que a responsabilidade é dele.

O UID é derivado do prazo, então reenviar o mesmo prazo ATUALIZA o
compromisso no calendário (SEQUENCE sobe) em vez de criar outro.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..core.config import get_settings

DOMINIO = "fscadvocaciadigital.com.br"


def _escapar(texto: str) -> str:
    return (texto.replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))


def _dobrar(linha: str) -> str:
    """RFC 5545: linha de no máximo 75 octetos, continuação com espaço."""
    if len(linha.encode()) <= 73:
        return linha
    partes, atual = [], ""
    for ch in linha:
        if len((atual + ch).encode()) > 73:
            partes.append(atual)
            atual = " " + ch
        else:
            atual += ch
    partes.append(atual)
    return "\r\n".join(partes)


def convite(uid: str, titulo: str, descricao: str, dia: date,
            sequencia: int = 0, alarme_dias: int = 1,
            local: str | None = None, cancelar: bool = False) -> bytes:
    s = get_settings()
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        f"PRODID:-//FSC Advocacia//Legal OS//PT-BR",
        "CALSCALE:GREGORIAN",
        f"METHOD:{'CANCEL' if cancelar else 'REQUEST'}",
        "BEGIN:VEVENT",
        f"UID:{uid}@{DOMINIO}",
        f"DTSTAMP:{agora}",
        f"SEQUENCE:{sequencia}",
        f"STATUS:{'CANCELLED' if cancelar else 'CONFIRMED'}",
        f"DTSTART;VALUE=DATE:{dia.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(dia + timedelta(days=1)).strftime('%Y%m%d')}",
        _dobrar(f"SUMMARY:{_escapar(titulo)}"),
        _dobrar(f"DESCRIPTION:{_escapar(descricao)}"),
        f"ORGANIZER;CN=FSC Advocacia:mailto:{s.email_escritorio}",
        "TRANSP:TRANSPARENT",
    ]
    if local:
        linhas.append(_dobrar(f"LOCATION:{_escapar(local)}"))
    if not cancelar:
        linhas += [
            "BEGIN:VALARM", "ACTION:DISPLAY",
            f"TRIGGER:-P{max(alarme_dias, 0)}D",
            _dobrar(f"DESCRIPTION:{_escapar(titulo)}"),
            "END:VALARM",
        ]
    linhas += ["END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(linhas) + "\r\n").encode("utf-8")


def enviar(destino: str, titulo: str, descricao: str, dia: date, uid: str,
           sequencia: int = 0, local: str | None = None,
           html_extra: str = "") -> str:
    """Manda o convite por e-mail. Devolve o Message-ID."""
    from . import avisos
    ics = convite(uid, titulo, descricao, dia, sequencia=sequencia, local=local)
    dia_br = dia.strftime("%d/%m/%Y")
    texto = f"{titulo}\n\nData no calendário: {dia_br}\n\n{descricao}"
    html = (
        f"<p style='font-family:Arial,sans-serif;font-size:14px'>"
        f"<b>{titulo}</b><br>Data no calendário: <b>{dia_br}</b></p>"
        f"<p style='font-family:Arial,sans-serif;font-size:14px;white-space:pre-line'>"
        f"{descricao}</p>{html_extra}"
        f"<p style='font-family:Arial,sans-serif;font-size:12px;color:#667'>"
        f"O anexo abaixo adiciona o compromisso ao seu calendário.</p>"
    )
    return avisos.enviar_email(
        destino, f"[Agenda] {titulo}", texto, html,
        anexos=[("compromisso.ics", ics, "text/calendar")],
    )
