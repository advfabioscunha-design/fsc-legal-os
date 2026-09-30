"""
Conferência do CPF na Receita Federal.

O QUE EXISTE, E O QUE NÃO EXISTE
--------------------------------
A Receita não publica uma API aberta de consulta de CPF. O que existe
são duas coisas diferentes, e confundi-las é o erro comum:

  1. VALIDAÇÃO DOS DÍGITOS. Um CPF tem dois dígitos verificadores
     calculados a partir dos nove primeiros. Isso se confere sem
     consultar ninguém, e pega o erro que mais acontece: o dígito
     trocado ao digitar. Não prova que o CPF existe, nem de quem é.

  2. CONSULTA À BASE DA RECEITA. Devolve a situação cadastral e o nome
     do titular. Exige CPF mais data de nascimento, e passa por um
     contrato: a própria Receita pela Serpro, ou um intermediário. É
     paga, por consulta.

Este módulo faz a primeira sempre e a segunda quando houver credencial
configurada. Sem credencial, ele diz que não conferiu, e essa é a
diferença que importa: o sistema nunca afirma "conferido na Receita"
quando não consultou a Receita. Escrever isso na tela sem ter feito a
consulta seria mentir para o cliente e para o escritório.

A DATA DE NASCIMENTO
--------------------
A consulta não funciona sem ela. Por isso o cadastro passa a pedi-la:
não é dado a mais por capricho, é o que a Receita exige para responder.

COMO LIGAR
----------
No .env do servidor:

    RECEITA_PROVEDOR=infosimples        (ou serpro)
    RECEITA_TOKEN=...                   a credencial do provedor

Sem essas duas, tudo continua funcionando, só que sem a conferência.
"""
from __future__ import annotations

import re

import httpx

from ..core.config import get_settings
from ..core.cpf import cpf_valido

TEMPO_LIMITE = 12


def _so_digitos(v: str | None) -> str:
    return re.sub(r"\D", "", v or "")


def _nomes_batem(a: str, b: str) -> bool:
    """Compara nomes com a folga que a vida real exige.

    A Receita guarda o nome em maiúsculas e sem acento, e o cliente
    digita como quiser. Comparar caractere a caractere reprovaria
    "José da Silva" contra "JOSE DA SILVA", que é a mesma pessoa.

    Sobrenome de casada, nome social e abreviação fazem o resto do
    estrago, e por isso a comparação é por conjunto de palavras longas:
    se o primeiro nome e ao menos um sobrenome coincidem, passa. O que
    se quer pegar aqui é o CPF de outra pessoa, não a divergência de
    grafia."""
    def limpar(s: str) -> list[str]:
        import unicodedata
        s = unicodedata.normalize("NFD", s or "")
        s = "".join(c for c in s if unicodedata.category(c) != "Mn").upper()
        return [p for p in re.split(r"[^A-Z]+", s) if len(p) > 2]

    pa, pb = limpar(a), limpar(b)
    if not pa or not pb:
        return True                      # sem base de comparação, não acusa
    if pa[0] != pb[0]:
        return False                     # primeiro nome diferente já basta
    return bool(set(pa[1:]) & set(pb[1:])) or len(pa) == 1 or len(pb) == 1


def conferir(cpf: str, nascimento: str | None = None,
             nome: str | None = None) -> dict:
    """Devolve o que se sabe sobre aquele CPF.

    O resultado tem sempre `ok` e `conferido`. `ok` falso significa que
    há algo errado e o cliente precisa corrigir. `conferido` diz se a
    Receita foi de fato consultada: é ele que autoriza a tela a dizer
    "conferido na Receita"."""
    n = _so_digitos(cpf)

    if len(n) == 14:                     # CNPJ não passa por aqui
        return {"ok": True, "conferido": False, "tipo": "CNPJ",
                "aviso": "CNPJ não é conferido na base de CPF."}
    if len(n) != 11:
        return {"ok": False, "conferido": False,
                "erro": "CPF precisa ter 11 números."}
    if not cpf_valido(n):
        return {"ok": False, "conferido": False,
                "erro": "Este CPF não existe: os dígitos finais não fecham "
                        "com o número. Confira se não trocou algum algarismo."}

    s = get_settings()
    provedor = (s.receita_provedor or "").lower().strip()
    if not provedor or not s.receita_token:
        return {"ok": True, "conferido": False,
                "aviso": "Números conferidos. A situação na Receita não foi "
                         "consultada."}
    if not nascimento:
        return {"ok": True, "conferido": False,
                "precisa_nascimento": True,
                "aviso": "Para conferir na Receita, informe também a sua data "
                         "de nascimento."}

    try:
        dados = (_infosimples if provedor == "infosimples" else _serpro)(
            n, nascimento)
    except Exception as e:
        # Provedor fora do ar não pode travar um cadastro. O cliente
        # segue, e o escritório confere depois.
        print(f"[receita] consulta falhou: {e}")
        return {"ok": True, "conferido": False,
                "aviso": "Não consegui falar com a Receita agora. Os números "
                         "do CPF estão corretos."}

    if not dados.get("encontrado"):
        return {"ok": False, "conferido": True,
                "erro": "A Receita não reconheceu esse CPF com essa data de "
                        "nascimento. Confira os dois campos."}

    situacao = (dados.get("situacao") or "").upper()
    if situacao and "REGULAR" not in situacao:
        return {"ok": False, "conferido": True, "situacao": situacao,
                "nome_receita": dados.get("nome"),
                "erro": f"Na Receita este CPF consta como {situacao.lower()}. "
                        f"Regularize antes, porque o documento sai com esse "
                        f"dado e pode ser recusado em cartório ou banco."}

    if nome and dados.get("nome") and not _nomes_batem(nome, dados["nome"]):
        return {"ok": False, "conferido": True,
                "nome_receita": dados["nome"],
                "erro": "O nome que você informou não confere com o que consta "
                        "na Receita para este CPF. Verifique se digitou o seu "
                        "nome completo, como está no documento."}

    return {"ok": True, "conferido": True, "situacao": situacao or "REGULAR",
            "nome_receita": dados.get("nome")}


# ── Os provedores ───────────────────────────────────────────────
#
# Dois, porque a escolha entre eles é comercial e muda com o tempo. A
# forma do retorno é a mesma, e o resto do sistema não sabe qual está
# ligado.

def _infosimples(cpf: str, nascimento: str) -> dict:
    s = get_settings()
    r = httpx.post(
        "https://api.infosimples.com/api/v2/consultas/receita-federal/cpf",
        data={"token": s.receita_token, "cpf": cpf,
              "birthdate": _br(nascimento), "timeout": TEMPO_LIMITE},
        timeout=TEMPO_LIMITE + 5)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != 200 or not j.get("data"):
        return {"encontrado": False}
    d = j["data"][0]
    return {"encontrado": True, "nome": d.get("nome"),
            "situacao": d.get("situacao_cadastral") or d.get("situacao")}


def _serpro(cpf: str, nascimento: str) -> dict:
    s = get_settings()
    r = httpx.get(
        f"https://gateway.apiserpro.serpro.gov.br/consulta-cpf-df/v1/cpf/{cpf}",
        headers={"Authorization": f"Bearer {s.receita_token}"},
        timeout=TEMPO_LIMITE)
    if r.status_code == 404:
        return {"encontrado": False}
    r.raise_for_status()
    d = r.json()
    return {"encontrado": True, "nome": d.get("nome"),
            "situacao": (d.get("situacao") or {}).get("descricao")}


def _br(iso: str) -> str:
    """Nascimento no formato que os provedores aceitam, dd/mm/aaaa."""
    s = (iso or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
    return s
