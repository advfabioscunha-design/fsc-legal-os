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


# ── Compromisso com hora marcada ────────────────────────────────
#
# O `convite()` acima nasceu para prazo, que é dia inteiro. Audiência às
# 14h30 não é dia inteiro: quem recebe precisa ver o horário, e o
# calendário precisa saber o fuso — senão o Google mostra 17h30 para uma
# audiência de Porto Velho, porque assume UTC.
#
# O fuso vai declarado no próprio arquivo (VTIMEZONE) em vez de converter
# para UTC, porque horário de audiência é horário local: se o país mudar
# a regra do horário de verão, o compromisso continua às 14h30.

FUSO = "America/Sao_Paulo"

_VTIMEZONE = "\r\n".join([
    "BEGIN:VTIMEZONE",
    f"TZID:{FUSO}",
    "BEGIN:STANDARD",
    "DTSTART:19700101T000000",
    "TZOFFSETFROM:-0300",
    "TZOFFSETTO:-0300",
    "TZNAME:-03",
    "END:STANDARD",
    "END:VTIMEZONE",
])


def _vevent(uid: str, titulo: str, descricao: str, dia: date,
            hora_inicio: str | None = None, hora_fim: str | None = None,
            sequencia: int = 0, local: str | None = None,
            link: str | None = None, cancelar: bool = False,
            alarme_minutos: int = 60, organizador: str | None = None,
            convidados: list[tuple[str, str]] | None = None) -> list[str]:
    """As linhas de um VEVENT. Separado para servir ao convite e ao feed."""
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = dia.strftime("%Y%m%d")

    if hora_inicio:
        hi = str(hora_inicio)[:5].replace(":", "") + "00"
        if hora_fim:
            hf = str(hora_fim)[:5].replace(":", "") + "00"
            fim = f"DTEND;TZID={FUSO}:{d}T{hf}"
        else:
            # Sem hora de término, uma hora. Bloco de duração zero some
            # da grade de alguns calendários.
            h = int(str(hora_inicio)[:2])
            m = str(hora_inicio)[3:5]
            fim = f"DTEND;TZID={FUSO}:{d}T{min(h + 1, 23):02d}{m}00"
        tempo = [f"DTSTART;TZID={FUSO}:{d}T{hi}", fim]
        gatilho = f"TRIGGER:-PT{max(alarme_minutos, 0)}M"
    else:
        tempo = [f"DTSTART;VALUE=DATE:{d}",
                 f"DTEND;VALUE=DATE:{(dia + timedelta(days=1)).strftime('%Y%m%d')}"]
        gatilho = "TRIGGER:-PT12H"

    s = get_settings()
    linhas = [
        "BEGIN:VEVENT",
        f"UID:{uid}@{DOMINIO}",
        f"DTSTAMP:{agora}",
        f"SEQUENCE:{sequencia}",
        f"STATUS:{'CANCELLED' if cancelar else 'CONFIRMED'}",
        *tempo,
        _dobrar(f"SUMMARY:{_escapar(titulo)}"),
        _dobrar(f"DESCRIPTION:{_escapar(descricao)}"),
        f"ORGANIZER;CN=FSC Advocacia:mailto:{organizador or s.email_escritorio}",
        "TRANSP:OPAQUE" if hora_inicio else "TRANSP:TRANSPARENT",
    ]
    if local:
        linhas.append(_dobrar(f"LOCATION:{_escapar(local)}"))
    if link:
        linhas.append(_dobrar(f"URL:{link}"))
    for nome, email in (convidados or []):
        linhas.append(_dobrar(
            f"ATTENDEE;CN={_escapar(nome or email)};ROLE=REQ-PARTICIPANT;"
            f"PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{email}"))
    if not cancelar:
        linhas += ["BEGIN:VALARM", "ACTION:DISPLAY", gatilho,
                   _dobrar(f"DESCRIPTION:{_escapar(titulo)}"), "END:VALARM"]
    linhas.append("END:VEVENT")
    return linhas


def _envelope(corpo: list[str], metodo: str = "REQUEST",
              nome: str | None = None) -> bytes:
    linhas = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//FSC Advocacia//Legal OS//PT-BR",
        "CALSCALE:GREGORIAN", f"METHOD:{metodo}",
    ]
    if nome:
        linhas += [f"X-WR-CALNAME:{_escapar(nome)}", f"X-WR-TIMEZONE:{FUSO}"]
    linhas.append(_VTIMEZONE)
    linhas += corpo
    linhas.append("END:VCALENDAR")
    return ("\r\n".join(linhas) + "\r\n").encode("utf-8")


def compromisso(**kw) -> bytes:
    """Um .ics de um compromisso só, para anexar ao e-mail."""
    cancelar = kw.get("cancelar", False)
    return _envelope(_vevent(**kw), metodo="CANCEL" if cancelar else "REQUEST")


def feed(itens: list[dict], nome: str = "FSC Advocacia — Agenda") -> bytes:
    """A agenda inteira num arquivo, para o calendário assinar.

    Assinar é diferente de importar: o Google relê este endereço sozinho
    de tempos em tempos, então o que muda aqui aparece lá sem ninguém
    reenviar nada. É o que substitui a integração por OAuth com o Google
    Calendar, sem pedir ao escritório que entregue a conta Google inteira
    a um servidor.
    """
    corpo: list[str] = []
    for i in itens:
        try:
            dia = date.fromisoformat(str(i["data"])[:10])
        except Exception:
            continue
        corpo += _vevent(
            uid=i.get("uid_ics") or str(i.get("id")),
            titulo=i.get("titulo") or "Compromisso",
            descricao=i.get("descricao") or "",
            dia=dia,
            hora_inicio=i.get("hora_inicio"),
            hora_fim=i.get("hora_fim"),
            sequencia=int(i.get("sequencia_ics") or 0),
            local=i.get("local"),
            link=i.get("link"),
            cancelar=(i.get("status") == "CANCELADO"),
        )
    return _envelope(corpo, metodo="PUBLISH", nome=nome)
