"""
PONTE CNJ — o pedaço de rede do escritório que fica no Brasil.

Por que isto existe
-------------------
O Comunica CNJ (comunicaapi.pje.jus.br) é servido por trás do CloudFront
com bloqueio geográfico: requisição de IP fora do Brasil recebe 403. O
servidor principal da plataforma está nos Estados Unidos, então ele não
consegue consultar o Diário sozinho.

Esta ponte roda numa máquina no Brasil (Oracle Cloud, região Brasil
Leste — São Paulo, camada Always Free) e faz uma coisa só: repassar a
consulta ao CNJ e devolver a resposta. Nada é guardado aqui.

O que ela deliberadamente NÃO é
-------------------------------
Não é um proxy genérico. Não existe parâmetro de URL de destino: o
destino está fixo no código. Um proxy aberto na internet vira, em
questão de dias, ferramenta de terceiros para atacar outros serviços —
e o endereço que aparece no ataque seria o do escritório.

Proteções:
  · destino único e fixo (comunicaapi.pje.jus.br), só leitura;
  · token obrigatório no cabeçalho X-Ponte-Token;
  · apenas os parâmetros de consulta conhecidos são repassados;
  · sem log do conteúdo das publicações — só data, status e tempo.
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

DESTINO = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
TOKEN = os.getenv("PONTE_TOKEN", "")

# Só estes parâmetros seguem adiante. Qualquer outro é descartado —
# assim a ponte não vira caminho para chamadas que não conhecemos.
PARAMETROS = {
    "numeroOab", "ufOab", "numeroProcesso", "siglaTribunal",
    "dataDisponibilizacaoInicio", "dataDisponibilizacaoFim",
    "itensPorPagina", "pagina", "meio", "nomeParte", "numeroComunicacao",
}

app = FastAPI(title="Ponte CNJ", docs_url=None, redoc_url=None)


@app.get("/health")
def health():
    return {"status": "ok", "destino": "comunicaapi.pje.jus.br"}


@app.get("/comunicacao")
def comunicacao(request: Request, x_ponte_token: str | None = Header(default=None)):
    if not TOKEN or x_ponte_token != TOKEN:
        raise HTTPException(401, "token inválido")

    params = {k: v for k, v in request.query_params.items() if k in PARAMETROS}
    if not params:
        raise HTTPException(400, "nenhum parâmetro de consulta reconhecido")

    inicio = time.time()
    try:
        r = httpx.get(DESTINO, params=params, timeout=90,
                      headers={"Accept": "application/json"})
    except httpx.HTTPError as e:
        print(f"[ponte] falha de rede: {e}")
        raise HTTPException(502, f"CNJ inacessível: {e}")

    print(f"[ponte] {r.status_code} em {time.time() - inicio:.1f}s "
          f"({params.get('numeroOab') or params.get('numeroProcesso') or '-'})")
    try:
        return JSONResponse(r.json(), status_code=r.status_code)
    except ValueError:
        # o CNJ às vezes devolve HTML de erro; repassa como texto
        return JSONResponse(
            {"status": "error", "message": r.text[:300]},
            status_code=r.status_code if r.status_code >= 400 else 502,
        )
