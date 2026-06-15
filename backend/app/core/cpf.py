"""Validação de CPF pelos dígitos verificadores (gratuita, offline).
Não consulta a Receita — apenas confere se o número é matematicamente
válido (rejeita CPF digitado errado ou inventado)."""
import re


def limpar(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def cpf_valido(cpf: str) -> bool:
    c = limpar(cpf)
    if len(c) != 11 or c == c[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(c[n]) * ((i + 1) - n) for n in range(i))
        dig = (soma * 10) % 11
        if dig == 10:
            dig = 0
        if dig != int(c[i]):
            return False
    return True
