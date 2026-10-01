"""O QUE VEM DO BANCO NEM SEMPRE TEM A FORMA QUE DEVERIA.

As colunas jsonb do sistema guardam o que os agentes devolvem: a
revisão, o laudo, o relatório, o histórico, a lista de apontamentos. O
esquema da ferramenta diz que `apontamentos` é uma lista de objetos, e
na maioria das vezes é. Mas o modelo é um modelo: de vez em quando ele
devolve a mesma informação como TEXTO, um JSON escrito dentro de uma
string, ou uma lista de frases em vez de uma lista de objetos.

O estrago disso é desproporcional ao tamanho do erro. `for a in
apontamentos` numa string percorre letra por letra, e `a.get(...)` numa
letra levanta `'str' object has no attribute 'get'`. Na tela, um `.map`
numa string derruba a página inteira com "Application error". O
documento estava certo; quem quebrou foi o formato do recado sobre ele.

Então nada neste sistema lê jsonb cru. Passa por aqui, e aqui a regra é
simples: devolver sempre a forma pedida, mesmo que vazia. Um pedido que
segue sem apontamento é um problema que o advogado resolve; um pedido
que não abre é um problema que só se resolve mexendo no banco.
"""
from __future__ import annotations

import json


def _decodificar(valor):
    """Tenta ler um JSON guardado como texto. Não sendo, devolve o texto."""
    if not isinstance(valor, str):
        return valor
    limpo = valor.strip()
    if not limpo or limpo[0] not in "[{\"":
        return valor
    try:
        return json.loads(limpo)
    except Exception:
        return valor


def como_dict(valor) -> dict:
    """Devolve sempre um dicionário.

    Vale para revisão, laudo, relatório, payload de evento: tudo que o
    código lê com `.get(...)`."""
    valor = _decodificar(valor)
    return valor if isinstance(valor, dict) else {}


def como_lista(valor) -> list:
    """Devolve sempre uma lista.

    Texto solto vira lista de um item, e não lista de letras, que é o
    que o `for` faria sozinho."""
    valor = _decodificar(valor)
    if isinstance(valor, list):
        return valor
    if valor is None or valor == "":
        return []
    if isinstance(valor, (str, int, float, bool)):
        return [valor]
    if isinstance(valor, dict):
        return [valor]
    return list(valor)


def lista_de_dicts(valor, campo: str = "texto") -> list[dict]:
    """Lista em que todo item é dicionário, para ser lido com `.get`.

    Item que veio como frase não se perde: entra no `campo` indicado, e
    o resto fica vazio. O apontamento do revisor escrito em prosa ainda
    é um apontamento, e sumir com ele seria pior do que exibi-lo sem a
    gravidade e a cláusula."""
    saida: list[dict] = []
    for item in como_lista(valor):
        item = _decodificar(item)
        if isinstance(item, dict):
            saida.append(item)
        elif isinstance(item, list):
            saida.extend(x for x in item if isinstance(x, dict))
        elif item not in (None, ""):
            saida.append({campo: str(item)})
    return saida


def texto_de(valor, separador: str = " ") -> str:
    """Um texto, venha o que vier. Para campo que o código imprime."""
    valor = _decodificar(valor)
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (list, tuple)):
        return separador.join(texto_de(x) for x in valor if x not in (None, ""))
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)
