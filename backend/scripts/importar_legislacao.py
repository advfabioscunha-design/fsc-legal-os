"""Carrega uma lei no acervo conferido, artigo por artigo.

Para que serve
--------------
O especialista não cita artigo de cabeça: ele consulta a tabela
`legislacao`. Este script é o jeito de pôr lei lá dentro.

Como usar
---------
    python scripts/importar_legislacao.py ARQUIVO \\
        --lei "Lei 8.245/1991" --apelido "Lei do Inquilinato" \\
        --fonte "planalto.gov.br, baixado em 01/10/2026" \\
        --conferido-por "Fábio Silva Cunha"

ARQUIVO pode ser .txt, .md ou .docx. Sai um relatório na tela com o
número de artigos encontrados e o primeiro e o último — confira esses
dois contra o texto oficial antes de confiar no acervo.

Rode com `--ensaio` primeiro: ele mostra o que faria sem gravar nada.

O cuidado com o acento
----------------------
O Planalto serve as leis em ISO-8859-1 sem declarar. Página salva pelo
navegador costuma vir certa; texto puxado por ferramenta que assume
UTF-8 vem com losango no lugar de cada acento, e isso não tem conserto
depois. Este script detecta o estrago e se recusa a gravar: acervo vazio
é melhor do que acervo errado, porque do errado o agente passa a
confiar.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_db  # noqa: E402

# "Art. 46.", "Art. 46-A.", "Art 1º", "Artigo 5º"
_ARTIGO = re.compile(
    r"^\s*Art(?:\.|igo)?\s*(\d{1,4}(?:\s*[-–]\s*[A-Z])?)\s*[.ºo°\-–)]*\s*",
    re.IGNORECASE)

# o que não é lei e costuma vir pregado no texto baixado
_LIXO = re.compile(
    r"^\s*(Presidência da República|Casa Civil|Subchefia para Assuntos"
    r"|Brasília, \d|Mensagem de veto|Vide |Texto compilado"
    r"|Este texto não substitui)", re.IGNORECASE)


def ler(caminho: Path) -> str:
    if caminho.suffix.lower() == ".docx":
        from docx import Document
        return "\n".join(p.text for p in Document(str(caminho)).paragraphs)
    # tenta UTF-8 e, falhando, o latin-1 do Planalto
    bruto = caminho.read_bytes()
    for cod in ("utf-8", "cp1252", "iso-8859-1"):
        try:
            return bruto.decode(cod)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="replace")


def partir(texto: str) -> list[dict]:
    """Quebra o texto em artigos. Cada artigo leva seus incisos,
    parágrafos e alíneas, porque é assim que ele se lê."""
    linhas = [l.rstrip() for l in texto.splitlines()]
    artigos: list[dict] = []
    atual: dict | None = None
    for l in linhas:
        if _LIXO.match(l):
            continue
        m = _ARTIGO.match(l)
        if m:
            if atual:
                artigos.append(atual)
            numero = re.sub(r"\s*[-–]\s*", "-", m.group(1)).upper()
            atual = {"artigo": numero, "linhas": [l.strip()]}
        elif atual is not None and l.strip():
            atual["linhas"].append(l.strip())
    if atual:
        artigos.append(atual)

    saida = []
    vistos = set()
    for a in artigos:
        if a["artigo"] in vistos:      # texto compilado repete o artigo
            continue                    # revogado/alterado: fica o primeiro
        vistos.add(a["artigo"])
        saida.append({"artigo": a["artigo"],
                      "texto": "\n".join(a["linhas"]).strip()})
    return saida


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("arquivo")
    p.add_argument("--lei", required=True, help='Ex.: "Lei 8.245/1991"')
    p.add_argument("--apelido", default="", help='Ex.: "Lei do Inquilinato"')
    p.add_argument("--fonte", default="", help="De onde veio o texto")
    p.add_argument("--conferido-por", default="", dest="conferido_por")
    p.add_argument("--ensaio", action="store_true",
                   help="Mostra o que faria, sem gravar")
    a = p.parse_args()

    caminho = Path(a.arquivo)
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        return 1

    texto = ler(caminho)

    quebrados = texto.count("�")
    if quebrados:
        print(f"RECUSADO: {quebrados} caractere(s) ilegível(is) no arquivo.")
        print("O acento foi destruído na codificação e não volta. Baixe a lei")
        print("de novo salvando a página pelo navegador (Ctrl+S) ou peça o PDF")
        print("oficial, e rode outra vez.")
        return 2

    artigos = partir(texto)
    if not artigos:
        print("Nenhum artigo reconhecido. O arquivo tem o texto da lei?")
        return 3

    print(f"{a.lei}: {len(artigos)} artigo(s) reconhecido(s).")
    print(f"  primeiro → art. {artigos[0]['artigo']}: "
          f"{artigos[0]['texto'][:160]}")
    print(f"  último   → art. {artigos[-1]['artigo']}: "
          f"{artigos[-1]['texto'][:160]}")
    print("\nCONFIRA esses dois contra o texto oficial. Se o último não for o")
    print("último artigo da lei, o arquivo veio truncado e o acervo ficaria")
    print("incompleto sem ninguém perceber.\n")

    if a.ensaio:
        print("Ensaio: nada foi gravado.")
        return 0

    agora = datetime.now(timezone.utc).isoformat()
    linhas = [{"lei": a.lei, "apelido": a.apelido or None,
               "artigo": x["artigo"], "texto": x["texto"],
               "fonte": a.fonte or None,
               "conferido_por": a.conferido_por or None,
               "conferido_em": agora if a.conferido_por else None}
              for x in artigos]

    db = get_db()
    gravados = 0
    for i in range(0, len(linhas), 200):
        lote = linhas[i:i + 200]
        db.table("legislacao").upsert(lote, on_conflict="lei,artigo").execute()
        gravados += len(lote)
        print(f"  gravados {gravados}/{len(linhas)}")

    print(f"\nPronto. {gravados} artigo(s) de {a.lei} no acervo.")
    if not a.conferido_por:
        print("Sem --conferido-por: o especialista vai citar sem o selo de")
        print("conferência. Rode de novo com o nome de quem conferiu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
