"""
QUEM JÁ É DA CASA NÃO SE APRESENTA DE NOVO.

O cliente que voltava para o segundo serviço começava do zero: digitava
outra vez o nome, o CPF, o endereço, e mandava de novo o documento de
identidade que já estava guardado na plataforma havia três meses. Do
lado dele isso não parece cuidado, parece que ninguém guardou nada, e a
pergunta que vem em seguida é justa: então para que eu mandei antes?

Este módulo faz duas coisas, e a segunda é a que economiza tempo de
verdade.

  `retrato`        junta o que o escritório já sabe sobre a pessoa,
                   cadastro e documentos, para a tela pedir confirmação
                   em vez de pedir digitação.
  `reaproveitar`   traz para o pedido novo os documentos que já estão
                   na pasta dela, com a marca de onde vieram.

O QUE ELE NÃO FAZ, E POR QUÊ

Não confirma sozinho. Endereço muda, estado civil muda, telefone muda,
e um contrato assinado com o endereço de dois anos atrás dá trabalho
na hora de citar alguém. O sistema preenche e pergunta; quem confirma
é o cliente.

Não copia documento vencido. Comprovante de residência e certidão têm
validade curta na prática, e reaproveitar um de um ano atrás seria
trocar um retrabalho por um defeito. A régua está em `VALIDADE_MESES`,
e o que passar dela aparece na tela como "pode estar desatualizado" em
vez de entrar calado.

Não atravessa cadastros. Só enxerga o que pertence aos `cliente_ids`
que quem chamou já provou serem da pessoa: o mesmo CPF pode ter mais
de um registro no banco por causa de cadastros antigos, e é por isso
que a lista vem de fora, do token, e não de uma busca por nome daqui.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..core.db import get_db, registrar_evento

# Quanto tempo um documento continua servindo sem ressalva. Não é
# prazo legal, é prudência: identidade não muda, comprovante de
# endereço muda toda hora, e quem decide no fim é quem lê a tela.
VALIDADE_MESES = 12

# Documentos que praticamente nunca mudam. Estes não ganham ressalva
# de validade, porque alertar sobre uma certidão de nascimento de dois
# anos atrás é ruído.
SEM_VALIDADE = ("identidade", "rg", "cnh", "cpf", "nascimento", "casamento",
                "contrato social", "cnpj", "procuração", "matrícula")


def _envelhecido(criado_em: str | None, nome: str) -> bool:
    if any(p in (nome or "").lower() for p in SEM_VALIDADE):
        return False
    if not criado_em:
        return True
    try:
        t = datetime.fromisoformat(str(criado_em).replace("Z", "+00:00"))
    except ValueError:
        return True
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t < datetime.now(timezone.utc) - timedelta(days=30 * VALIDADE_MESES)


def _cadastro(cli: dict) -> dict:
    """Os campos que o cliente teria de digitar de novo."""
    partes = [cli.get("endereco"), cli.get("numero"), cli.get("bairro"),
              cli.get("cidade"), cli.get("uf")]
    endereco = ", ".join(str(x).strip() for x in partes if str(x or "").strip())
    return {
        "nome": cli.get("nome"), "cpf_cnpj": cli.get("cpf_cnpj"),
        "email": cli.get("email"), "telefone": cli.get("whatsapp"),
        "nacionalidade": cli.get("nacionalidade"),
        "estado_civil": cli.get("estado_civil"),
        "profissao": cli.get("profissao"),
        "endereco": endereco or None,
        "cep": cli.get("cep"),
        "nascimento": cli.get("nascimento"),
    }


def documentos_guardados(cliente_ids: list[str],
                         pedido_atual: str | None = None) -> list[dict]:
    """Tudo o que essa pessoa já mandou, de qualquer serviço ou caso."""
    db = get_db()
    achados: list[dict] = []

    # 1. Os documentos dos pedidos do balcão.
    pedidos = db.table("pedidos_contrato").select("id,numero,tipo") \
        .in_("cliente_id", cliente_ids).is_("excluido_em", "null") \
        .limit(100).execute().data or []
    de_onde = {p["id"]: p for p in pedidos}
    ids = [p["id"] for p in pedidos if p["id"] != pedido_atual]
    if ids:
        for d in (db.table("pedidos_documentos")
                  .select("id,pedido_id,nome,tipo_mime,tamanho,url,rotulo,criado_em")
                  .in_("pedido_id", ids).order("criado_em", desc=True)
                  .limit(200).execute().data or []):
            origem = de_onde.get(d["pedido_id"]) or {}
            achados.append({
                "id": d["id"], "nome": d.get("nome"), "url": d.get("url"),
                "tipo_mime": d.get("tipo_mime"), "tamanho": d.get("tamanho"),
                "rotulo": d.get("rotulo"), "criado_em": d.get("criado_em"),
                "de": f"pedido {origem.get('numero') or ''}".strip(),
                "envelhecido": _envelhecido(d.get("criado_em"), d.get("nome") or ""),
            })

    # 2. Os documentos dos casos judiciais.
    casos = db.table("casos").select("id,numero_atendimento") \
        .in_("cliente_id", cliente_ids).limit(100).execute().data or []
    if casos:
        onde = {c["id"]: c for c in casos}
        for d in (db.table("documentos")
                  .select("id,caso_id,tipo,storage_path,criado_em")
                  .in_("caso_id", list(onde)).eq("status", "RECEBIDO")
                  .order("criado_em", desc=True).limit(200).execute().data or []):
            c = onde.get(d["caso_id"]) or {}
            nome = str(d.get("tipo") or "documento").replace("_", " ")
            achados.append({
                "id": d["id"], "nome": nome, "url": d.get("storage_path"),
                "tipo_mime": None, "tamanho": None, "rotulo": nome,
                "criado_em": d.get("criado_em"),
                "de": f"atendimento {c.get('numero_atendimento') or ''}".strip(),
                "envelhecido": _envelhecido(d.get("criado_em"), nome),
            })

    # O mesmo arquivo pode ter sido mandado duas vezes. Mostrar as duas
    # cópias faz o cliente conferir duas vezes a mesma coisa.
    vistos, unicos = set(), []
    for d in achados:
        chave = (d.get("url") or "") or (d.get("nome") or "")
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(d)
    return unicos[:40]


def retrato(cliente_ids: list[str], pedido_atual: str | None = None) -> dict:
    """O que o escritório já sabe, para a tela pedir confirmação."""
    if not cliente_ids:
        return {"conhecido": False}
    db = get_db()
    r = db.table("clientes").select("*").in_("id", cliente_ids) \
        .order("criado_em").limit(5).execute().data or []
    if not r:
        return {"conhecido": False}

    # Entre cadastros do mesmo CPF, vale o mais completo: o antigo
    # costuma ter só nome e telefone, e sobrescrever com ele seria
    # apagar o que a pessoa preencheu depois.
    melhor = max(r, key=lambda c: sum(1 for v in _cadastro(c).values() if v))
    cad = _cadastro(melhor)

    docs = documentos_guardados(cliente_ids, pedido_atual)
    antes = db.table("pedidos_contrato").select("id") \
        .in_("cliente_id", cliente_ids).is_("excluido_em", "null") \
        .limit(2).execute().data or []
    casos = db.table("casos").select("id").in_("cliente_id", cliente_ids) \
        .limit(2).execute().data or []

    ja_usou = len(antes) > (1 if pedido_atual else 0) or bool(casos)
    return {
        "conhecido": True,
        "ja_usou_antes": ja_usou,
        "cadastro": cad,
        "faltando": [k for k, v in cad.items() if not v],
        "documentos": docs,
    }


def reaproveitar(pedido_id: str, cliente_ids: list[str]) -> dict:
    """Traz para o pedido novo os documentos que já estão na pasta.

    Copia a linha, não o arquivo: o arquivo continua um só no
    armazenamento, e as duas linhas apontam para ele. Duplicar o
    binário custaria espaço e criaria a pergunta de qual das duas
    cópias é a boa quando uma for corrigida."""
    db = get_db()
    if not cliente_ids:
        return {"trazidos": 0}

    ja = {d.get("url") for d in (db.table("pedidos_documentos")
                                 .select("url").eq("pedido_id", pedido_id)
                                 .execute().data or [])}
    candidatos = [d for d in documentos_guardados(cliente_ids, pedido_id)
                  if d.get("url") and d["url"] not in ja and not d["envelhecido"]]

    trazidos = []
    for d in candidatos[:20]:
        try:
            linha = db.table("pedidos_documentos").insert({
                "pedido_id": pedido_id, "nome": d["nome"],
                "tipo_mime": d.get("tipo_mime"), "tamanho": d.get("tamanho"),
                "url": d["url"], "enviado_por": "CLIENTE",
                "rotulo": (f"Aproveitado do {d['de']}" if d.get("de")
                           else "Aproveitado da sua pasta")[:200],
            }).execute().data
            if linha:
                trazidos.append(d["nome"])
        except Exception as e:
            print(f"[cadastro] documento não reaproveitado: {e}")

    if trazidos:
        registrar_evento(None, "DOCUMENTOS_REAPROVEITADOS",
                         {"pedido_id": pedido_id, "arquivos": trazidos})
    return {"trazidos": len(trazidos), "arquivos": trazidos}
