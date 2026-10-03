"""Tenta vazar: parceiro, e visitante sem login, pedindo o que nao e deles."""
import re, sys
sys.path.insert(0, 'backend')
from app.core.seguranca import DO_PARCEIRO, SO_DO_ADMIN, _e_publico

par = [re.compile(p) for p in DO_PARCEIRO]
adm = [re.compile(p) for p in SO_DO_ADMIN]
falhas = 0

def alcanca_parceiro(metodo, caminho):
    return any(p.match(caminho) for p in par) or _e_publico(metodo, caminho)

ATAQUES = [
    ("GET","/api/v1/casos"), ("GET","/api/v1/casos/abc-123"),
    ("GET","/api/v1/clientes"), ("GET","/api/v1/contratos/pedidos"),
    ("GET","/api/v1/financeiro/lancamentos"), ("GET","/api/v1/equipe"),
    ("POST","/api/v1/admin/acessos"), ("POST","/api/v1/equipe/xyz/promover"),
    ("GET","/api/v1/intimacoes"), ("GET","/api/v1/casos/abc/documentos"),
    ("GET","/api/v1/prestacoes"), ("GET","/api/v1/cliente/meus-casos"),
    ("GET","/api/v1/parceiro/casos/../../casos"),
]
print("=== o parceiro NAO pode alcancar ===")
for m, c in ATAQUES:
    v = alcanca_parceiro(m, c)
    if v: falhas += 1
    print(f"  {'VAZOU' if v else 'bloqueado':10} {m:5} {c}")

print("\n=== visitante SEM LOGIN ===")
for m, c in [("GET","/api/v1/contratos/pedidos"), ("POST","/api/v1/contratos/pedidos"),
             ("GET","/api/v1/clientes"), ("GET","/api/v1/contratos/tipos")]:
    v = _e_publico(m, c)
    esperado = (m,c) in [("POST","/api/v1/contratos/pedidos"),("GET","/api/v1/contratos/tipos")]
    ok = (v == esperado)
    if not ok: falhas += 1
    print(f"  {'ok' if ok else 'ERRADO':10} {m:5} {c:42} publico={v}")

print("\n=== o parceiro PRECISA alcancar ===")
for c in ["/api/v1/parceiro/eu","/api/v1/parceiro/cadastro","/api/v1/parceiro/casos",
          "/api/v1/parceiro/caso/abc-123","/api/v1/parceiro/caso/abc/documentos",
          "/api/v1/parceiro/caso/abc/mensagens","/api/v1/parceiro/caso/abc/tarefas",
          "/api/v1/parceiro/casos/novo","/api/v1/parceiro/valores"]:
    v = any(p.match(c) for p in par)
    if not v: falhas += 1
    print(f"  {'ok' if v else 'FALTOU':10} {c}")

print(f"\n{'TUDO CERTO' if falhas == 0 else f'{falhas} PROBLEMA(S)'}")
sys.exit(1 if falhas else 0)
