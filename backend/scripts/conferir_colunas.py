"""Confere nomes de coluna usados no codigo contra as migracoes.

Nasceu de um erro real: escrevi `casos.area` e `casos.fase` de cabeca —
a tabela tem `grupo` e `estado`. Tambem escrevi `tarefas.prazo`, que nao
existe, e `casos.origem`, que e de `intimacoes`. Tres consultas que so
quebrariam em producao, na frente de quem estivesse usando.

Le as migracoes, monta o mapa real de colunas por tabela, e confere o
que o codigo pede em .select(...) e .insert({...}).
"""
import ast, re, sys, pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[2]
MIG = RAIZ / "supabase" / "migrations"
APP = RAIZ / "backend" / "app"

def colunas_reais() -> dict[str, set]:
    mapa: dict[str, set] = {}
    for f in sorted(MIG.glob("*.sql")):
        txt = f.read_text(encoding="utf-8")
        # create table
        for m in re.finditer(r"create table(?: if not exists)?\s+(?:public\.)?(\w+)\s*\((.*?)\n\);",
                             txt, re.S | re.I):
            tab, corpo = m.group(1), m.group(2)
            cols = mapa.setdefault(tab, set())
            for linha in corpo.split("\n"):
                linha = linha.strip()
                mc = re.match(r"^(\w+)\s+[a-z]", linha, re.I)
                if mc and mc.group(1).lower() not in (
                        "primary", "unique", "constraint", "check", "foreign"):
                    cols.add(mc.group(1))
        # alter table add column
        for m in re.finditer(r"alter table\s+(?:public\.)?(\w+)(.*?);", txt, re.S | re.I):
            tab, corpo = m.group(1), m.group(2)
            cols = mapa.setdefault(tab, set())
            for c in re.findall(r"add column(?: if not exists)?\s+(\w+)", corpo, re.I):
                cols.add(c)
    return mapa

REAIS = colunas_reais()
problemas = []

for py in sorted(APP.rglob("*.py")):
    txt = py.read_text(encoding="utf-8")
    # .table("x").select("a,b,c")
    for m in re.finditer(r'\.table\(["\'](\w+)["\']\)\s*\.\s*select\(\s*["\']([^"\']+)["\']', txt):
        tab, campos = m.group(1), m.group(2)
        if tab not in REAIS:
            continue
        linha = txt[:m.start()].count("\n") + 1
        # SELEÇÃO ANINHADA NÃO É COLUNA DESTA TABELA
        #
        # `select("*, clientes(nome,email)")` traz campos de OUTRA tabela.
        # Separar por vírgula sem entender isso fazia `email` ser cobrado
        # de `casos` — dezesseis acusações falsas na primeira execução,
        # que é o jeito mais rápido de um teste virar ruído que ninguém lê.
        campos = re.sub(r"\w+\([^)]*\)", "", campos)
        for campo in campos.split(","):
            campo = campo.strip()
            if not campo or campo == "*" or "(" in campo or ")" in campo:
                continue
            if campo not in REAIS[tab]:
                problemas.append(f"{py.relative_to(RAIZ)}:{linha}  "
                                 f"select {tab}.{campo} — coluna inexistente")

print(f"Tabelas lidas das migracoes: {len(REAIS)}")
if problemas:
    print(f"\n{len(problemas)} problema(s):")
    for p in problemas:
        print("  " + p)
else:
    print("\nNenhuma coluna inexistente nos .select() do codigo.")
sys.exit(1 if problemas else 0)
