"""
Contagem de prazos.

Duas advertências que valem mais que o código:

1. Dias úteis aqui excluem sábado, domingo e os feriados listados. A
   lista cobre os feriados nacionais fixos e os móveis derivados da
   Páscoa, mais o recesso forense (20/12 a 20/01, CPC art. 220). NÃO
   cobre feriado estadual, municipal, suspensão de expediente por
   portaria nem ponto facultativo do tribunal.

2. Por isso todo prazo calculado por aqui entra na plataforma marcado
   como ESTIMADO. A data de trabalho fica dois dias antes do prazo
   fatal justamente para que a conferência humana ainda caiba dentro
   da folga. O cálculo serve para ordenar a fila, não para substituir
   a certidão do tribunal.
"""
from __future__ import annotations

from datetime import date, timedelta


def pascoa(ano: int) -> date:
    """Algoritmo de Gauss/Butcher — domingo de Páscoa do ano."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados(ano: int) -> set[date]:
    p = pascoa(ano)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15),
             (11, 20), (12, 25)]
    moveis = [p - timedelta(days=48),   # carnaval (segunda)
              p - timedelta(days=47),   # carnaval (terça)
              p - timedelta(days=2),    # sexta-feira santa
              p + timedelta(days=60)]   # corpus christi
    return {date(ano, m, d) for m, d in fixos} | set(moveis)


def recesso(d: date) -> bool:
    """Recesso forense: 20/12 a 20/01 (CPC art. 220 — prazos suspensos)."""
    return (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 20)


def util(d: date) -> bool:
    return d.weekday() < 5 and d not in feriados(d.year) and not recesso(d)


def somar_uteis(inicio: date, dias: int) -> date:
    """Prazo em dias úteis contado a partir do dia seguinte à intimação
    (CPC art. 224: exclui o dia do começo, inclui o do vencimento)."""
    d, restam = inicio, dias
    while restam > 0:
        d += timedelta(days=1)
        if util(d):
            restam -= 1
    return d


def antecipar_uteis(d: date, dias: int = 2) -> date:
    """Recua `dias` úteis — é assim que nasce a data de trabalho do
    escritório, sempre antes do prazo fatal."""
    saida, restam = d, dias
    while restam > 0:
        saida -= timedelta(days=1)
        if util(saida):
            restam -= 1
    return saida


def dias_ate(d: date | str | None, hoje: date | None = None) -> int | None:
    if not d:
        return None
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return None
    return (d - (hoje or date.today())).days
