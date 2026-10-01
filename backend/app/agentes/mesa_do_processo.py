"""
A MESA DA PEÇA PROCESSUAL — o especialista do caso judicial.

É o mesmo que `mesa_do_advogado` faz pelo contrato do balcão, para o
outro lado da casa. A diferença não é de forma, é de consequência: um
contrato mal revisado volta do cliente; uma petição mal revisada é
protocolada, e o que foi protocolado não se desfaz.

O QUE MUDA EM RELAÇÃO À MESA DO CONTRATO

O dossiê é outro. No balcão, o material é a negociação, a coleta e as
duas revisões. Aqui é o processo: a última publicação, o prazo fatal,
a fase judicial, as peças anteriores, os documentos do kit e o que a
trava de peticionamento já apontou.

E há três coisas que o especialista daqui tem de olhar e o do contrato
não:

  O PRAZO FATAL. Atraso em contrato é cliente irritado; atraso aqui é
  preclusão. O prazo entra no material em primeiro lugar e ele avisa
  quando estiver perto.

  O MOMENTO PROCESSUAL. A peça certa na hora errada é peça perdida.
  Ele confere a peça contra o último andamento antes de opinar sobre
  o texto.

  OS PRECEDENTES INJETADOS. A peça tem jurisprudência real, posta pelo
  banco de precedentes, com número, relator e data copiados do
  registro. Ele NÃO inventa julgado, não completa citação e não "lembra"
  de acórdão nenhum: o que não veio do banco não existe.

O QUE ELE FAZ

Lê, aponta, sugere redação e corrige o texto quando o advogado manda.
Quando o ponto depende do cliente, pergunta a ele pela conversa do
caso e volta com a resposta.

O QUE ELE NÃO FAZ

Não protocola, não aprova, não muda a fase do caso e não mexe no texto
sem ordem. Protocolo é ato do advogado, com a trava documental que já
existe, e nada aqui passa por cima dela.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic

from ..core.config import get_settings
from ..core.db import get_db, registrar_evento
from ..core.ia import TEMPO_LIMITE, TENTATIVAS
from ..core.texto import humanizar

# As travas de aplicar texto são as mesmas do contrato, e é de propósito
# que sejam o mesmo código: duas implementações de "procurar e
# substituir com conferência" divergem no dia em que alguém melhora uma.
from .mesa_do_advogado import FERRAMENTA_ALTERAR, _aplicar

SYSTEM = """Você é advogado sênior da FC Advocacia, especialista na
matéria deste processo, e acompanhou o caso desde a triagem. Está
falando com o ADVOGADO responsável pela peça.

O QUE ESTÁ EM JOGO AQUI

Isto vai ser protocolado. Erro em contrato volta do cliente; erro aqui
vira preclusão, inépcia ou precedente contra. Trate cada resposta como
se a peça fosse protocolada em seguida, porque pode ser.

COMO RESPONDER

Direto, no máximo dois parágrafos curtos. Primeiro o fato, depois de
onde ele vem. O advogado tem pressa e vai agir pelo que você disser.

A LINHA ENTRE FATO E OPINIÃO

Sobre o que ACONTECEU no caso, você só repete o registro: o que a
publicação diz, qual o prazo, o que já foi protocolado, o que a trava
documental apontou. Sobre DIREITO você opina, e é para isso que ele
pergunta: aponte o risco, diga qual redação usaria e por quê, cite o
dispositivo. Quem assina é ele.

JURISPRUDÊNCIA: O QUE NÃO VEIO DO BANCO NÃO EXISTE

Os julgados da peça foram postos pelo banco de precedentes do
escritório, com número, relator e data copiados do registro. Você NÃO
cita acórdão de memória, não completa uma citação incompleta e não
sugere julgado que não esteja no material. Precisando de precedente
novo, diga ao advogado que é preciso rodar o banco de precedentes
para o tema.

O PRAZO E O MOMENTO

Se o prazo fatal estiver perto, diga isso antes de qualquer outra
coisa. E confira a peça contra o último andamento: peça certa na hora
errada é peça perdida, e isso se vê no andamento, não no texto.

QUANDO ELE MANDA ALTERAR

Aí você mexe no texto, com `alterar_texto`. Só quando ele pedir. As
regras são as mesmas de qualquer edição cuidadosa:

`procurar` tem de ser trecho LITERAL do texto na tela, caractere por
caractere. Errou uma vírgula, a alteração é recusada e nada acontece,
o que é melhor do que acertar o trecho errado.

Pegue o menor trecho que identifique o lugar sem ambiguidade; se ele
se repetir no documento, inclua o que estiver em volta até ficar único.

`substituir` é o texto final, pronto, sem marcação e sem comentário.

NUNCA apague ou altere uma citação de julgado para "encaixar" o
argumento. Mudar ementa, número ou relator de acórdão é falsidade, não
é redação.

QUANDO O PONTO É DO CLIENTE

Falta um documento, um dado, ou é preciso a ciência dele sobre uma
escolha. Aí você usa `falar_com_o_cliente`, escrevendo como ele vai
ler: sem jargão, dizendo o que está em jogo, o prazo que existe e o que
você precisa que ele responda. Não espere pela resposta: avise o
advogado que a pergunta saiu.

O QUE VOCÊ NÃO FAZ

Não protocola. Não aprova. Não muda a fase do caso. Não altera sem
ordem nem corrige de passagem o que não foi pedido.

Nada de travessão, asterisco ou marcação. Texto corrido."""


FERRAMENTA_CLIENTE = {
    "name": "falar_com_o_cliente",
    "description": ("Manda uma pergunta ao cliente pelos canais do caso e "
                    "registra no histórico. Use quando o advogado mandar "
                    "consultar o cliente, pedir um documento ou a ciência "
                    "dele sobre uma escolha."),
    "input_schema": {
        "type": "object",
        "properties": {
            "pergunta": {
                "type": "string",
                "description": ("A mensagem como o cliente vai ler: sem "
                                "jargão, com o que está em jogo, o prazo e "
                                "o que ele precisa responder."),
            },
            "assunto": {
                "type": "string",
                "description": "O ponto, em poucas palavras.",
            },
        },
        "required": ["pergunta", "assunto"],
    },
}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claude():
    return anthropic.Anthropic(api_key=get_settings().claude_api_key,
                               timeout=TEMPO_LIMITE,
                               max_retries=TENTATIVAS)


def _linha(rotulo: str, valor) -> str:
    return f"{rotulo}: {valor}" if valor not in (None, "", [], {}) else ""


def dossie(caso_id: str, peticao_id: str | None = None) -> str:
    """Tudo o que o escritório tem sobre este caso, em texto.

    Montado inteiro a cada pergunta. Guardar um resumo seria mais barato
    e responderia sobre o processo de ontem: num caso com prazo correndo,
    resposta velha é resposta errada."""
    db = get_db()
    r = db.table("casos").select("*, clientes(nome,cpf_cnpj,email,whatsapp)") \
        .eq("id", caso_id).limit(1).execute().data
    if not r:
        raise ValueError("Caso não encontrado.")
    c = r[0]
    cli = c.get("clientes") or {}

    partes: list[str] = []

    # O PRAZO VEM PRIMEIRO, SEMPRE
    #
    # Num dossiê longo, o que fica no fim não é lido. O prazo fatal é a
    # única informação que muda o que fazer com todo o resto: perto do
    # fim, a resposta certa deixa de ser "melhore a fundamentação" e
    # passa a ser "protocole o que está".
    partes += ["=== PRAZO ==="]
    partes += [x for x in [
        _linha("Prazo fatal do caso", c.get("prazo_fatal")),
        _linha("Do que se trata o prazo", c.get("prazo_descricao")),
        _linha("Hoje é", datetime.now(timezone.utc).date().isoformat()),
    ] if x]

    partes += ["", "=== O PROCESSO ==="]
    partes += [x for x in [
        _linha("Cliente", cli.get("nome")),
        _linha("CPF/CNPJ", cli.get("cpf_cnpj")),
        _linha("Título do caso", c.get("titulo")),
        _linha("Número de atendimento", c.get("numero_atendimento")),
        _linha("Área", c.get("grupo")),
        _linha("Subtipo", c.get("subtipo")),
        _linha("Número do processo", c.get("numero_processo")),
        _linha("Tribunal", c.get("tribunal")),
        _linha("Órgão julgador", c.get("orgao_julgador")),
        _linha("Classe judicial", c.get("classe_judicial")),
        _linha("Instância", c.get("instancia")),
        _linha("Fase na jornada do escritório", c.get("estado")),
        _linha("Fase judicial", c.get("fase_judicial")),
        _linha("Por que esta fase", c.get("fase_judicial_motivo")),
        _linha("Protocolado em", c.get("protocolado_em")),
        _linha("Valor da causa", c.get("valor_causa")),
    ] if x]

    if (c.get("relato_inicial") or "").strip():
        partes += ["", "=== O QUE O CLIENTE RELATOU NO INÍCIO ===",
                   c["relato_inicial"][:3000]]

    # As publicações: é delas que sai o momento processual.
    try:
        q = db.table("intimacoes").select(
            "conteudo,tipo,tribunal,orgao,data_movimento,prazo_em,status")
        achadas = q.eq("caso_id", caso_id).order("data_movimento", desc=True) \
            .limit(8).execute().data or []
        if not achadas and c.get("numero_processo"):
            # Muita publicação entra só com o número do processo, sem o
            # caso ligado. Sem este caminho, o especialista acharia que
            # o processo não tem andamento nenhum.
            achadas = db.table("intimacoes").select(
                "conteudo,tipo,tribunal,orgao,data_movimento,prazo_em,status") \
                .eq("numero_processo", c["numero_processo"]) \
                .order("data_movimento", desc=True).limit(8).execute().data or []
    except Exception:
        achadas = []
    if achadas:
        partes += ["", "=== ÚLTIMAS PUBLICAÇÕES, DA MAIS NOVA PARA A MAIS VELHA ==="]
        for i in achadas:
            partes.append(
                f"[{str(i.get('data_movimento') or '')[:10]}] "
                f"{i.get('tipo') or ''} {i.get('orgao') or ''} "
                f"(prazo em {i.get('prazo_em') or 'não calculado'}, "
                f"{i.get('status')})\n  "
                + " ".join(str(i.get("conteudo") or "").split())[:900])

    try:
        prazos = db.table("prazos").select("titulo,data,prazo_fatal,status,tipo") \
            .eq("caso_id", caso_id).order("data").limit(12).execute().data or []
    except Exception:
        prazos = []
    if prazos:
        partes += ["", "=== PRAZOS DO CASO ==="]
        partes += [f"- {p.get('titulo')} | trabalhar em {p.get('data')} | "
                   f"fatal {p.get('prazo_fatal')} | {p.get('status')}"
                   for p in prazos]

    try:
        docs = db.table("documentos").select("tipo,status,observacao,transcricao") \
            .eq("caso_id", caso_id).limit(40).execute().data or []
    except Exception:
        docs = []
    if docs:
        partes += ["", "=== DOCUMENTOS NA PASTA ==="]
        for d in docs:
            partes.append(f"- {d.get('tipo')} ({d.get('status')})"
                          + (f" — {d.get('observacao')}" if d.get("observacao") else ""))
            if (d.get("transcricao") or "").strip():
                partes.append(f"  transcrição: {d['transcricao'][:600]}")

    try:
        val = db.table("validacoes_peticionamento") \
            .select("tipo_peticao,regra,aprovado,motivo,faltando,criado_em") \
            .eq("caso_id", caso_id).order("criado_em", desc=True) \
            .limit(5).execute().data or []
    except Exception:
        val = []
    if val:
        partes += ["", "=== O QUE A TRAVA DE PETICIONAMENTO JÁ APONTOU ==="]
        partes += [f"- [{str(v.get('criado_em') or '')[:10]}] {v.get('tipo_peticao')} "
                   f"({v.get('regra')}): "
                   + ("aprovado" if v.get("aprovado") else "reprovado")
                   + f" — {v.get('motivo')}"
                   + (f" | faltando: {v.get('faltando')}" if v.get("faltando") else "")
                   for v in val]

    try:
        msgs = db.table("mensagens").select("autor,conteudo,criado_em,canal") \
            .eq("caso_id", caso_id).order("criado_em").limit(80).execute().data or []
    except Exception:
        msgs = []
    if msgs:
        partes += ["", "=== CONVERSA COM O CLIENTE ==="]
        quem = {"CLIENTE": "Cliente", "AGENTE": "Atendimento",
                "HUMANO": "Escritório"}
        partes += [f"[{(m.get('criado_em') or '')[:16]}] "
                   f"{quem.get(m.get('autor'), m.get('autor'))}: "
                   f"{(m.get('conteudo') or '')[:500]}" for m in msgs]

    # As peças: a atual por inteiro, as anteriores só pelo título, para
    # ele saber o que já foi dito ao juízo sem gastar o espaço todo.
    try:
        pecas = db.table("peticoes").select(
            "id,titulo,tribunal,status,origem,criado_em,markdown_final,markdown_base") \
            .eq("caso_id", caso_id).order("criado_em", desc=True) \
            .limit(10).execute().data or []
    except Exception:
        pecas = []
    anteriores = [p for p in pecas if p.get("id") != peticao_id]
    if anteriores:
        partes += ["", "=== PEÇAS ANTERIORES NESTE CASO ==="]
        partes += [f"- [{str(p.get('criado_em') or '')[:10]}] {p.get('titulo')} "
                   f"({p.get('tribunal') or ''}, {p.get('status')})"
                   for p in anteriores]

    atual = next((p for p in pecas if p.get("id") == peticao_id), None)
    if atual:
        corpo = (atual.get("markdown_final") or atual.get("markdown_base") or "")
        partes += ["", "=== A PEÇA COMO ESTÁ GRAVADA ===",
                   _linha("Título", atual.get("titulo")),
                   _linha("Tribunal", atual.get("tribunal")),
                   _linha("Jurisprudência injetada", atual.get("status")),
                   corpo[:30000]]

    return "\n".join([p for p in partes if p is not None])


def _consultar_cliente(caso_id: str, dados: dict, quem: str) -> dict:
    """Manda a pergunta ao cliente pelos canais do caso."""
    pergunta = (dados.get("pergunta") or "").strip()
    if len(pergunta) < 10:
        return {"enviada": False,
                "porque": "a pergunta ficou curta demais para o cliente "
                          "entender do que se trata"}
    db = get_db()
    try:
        db.table("mensagens").insert({
            "caso_id": caso_id, "canal": "PORTAL", "autor": "HUMANO",
            "conteudo": pergunta[:4000],
        }).execute()
    except Exception as e:
        print(f"[mesa-processo] mensagem não registrada: {e}")
        return {"enviada": False, "porque": str(e)[:200]}

    # Os canais externos são tentados depois do registro, e a falha
    # deles não desfaz a pergunta: ela existe no caso de qualquer jeito,
    # e o escritório pode cobrar por telefone se precisar.
    try:
        from ..integracoes import avisos
        avisos.notificar(caso_id, "MENSAGEM",
                         dados.get("assunto") or "Sobre o seu processo",
                         pergunta)
    except Exception as e:
        print(f"[mesa-processo] aviso externo não saiu: {e}")

    registrar_evento(caso_id, "PERGUNTA_AO_CLIENTE_NA_PECA",
                     {"quem": quem or "advogado",
                      "assunto": dados.get("assunto"),
                      "pergunta": pergunta[:500]})
    return {"enviada": True,
            "aviso": "A pergunta entrou na conversa do caso e saiu pelos "
                     "canais do cliente."}


def perguntar(peticao_id: str, pergunta: str, quem: str = "",
              texto_na_tela: str = "",
              anteriores: list[dict] | None = None) -> dict:
    """O advogado pergunta ao especialista do caso judicial."""
    pergunta = (pergunta or "").strip()
    if len(pergunta) < 3:
        raise ValueError("Escreva a pergunta.")

    db = get_db()
    r = db.table("peticoes").select("caso_id,markdown_final,markdown_base") \
        .eq("id", peticao_id).limit(1).execute().data
    if not r:
        raise ValueError("Peça não encontrada.")
    caso_id = r[0]["caso_id"]

    material = dossie(caso_id, peticao_id)
    base = texto_na_tela or r[0].get("markdown_final") \
        or r[0].get("markdown_base") or ""
    if (texto_na_tela or "").strip():
        material += ("\n\n=== O TEXTO QUE O ADVOGADO ESTÁ EDITANDO AGORA ===\n"
                     "É a versão da tela, com as alterações dele. Onde "
                     "divergir da peça gravada, vale esta.\n"
                     + texto_na_tela[:30000])

    mensagens: list[dict] = []
    for t in (anteriores or [])[-10:]:
        if t.get("pergunta"):
            mensagens.append({"role": "user", "content": t["pergunta"][:2000]})
        if t.get("resposta"):
            mensagens.append({"role": "assistant", "content": t["resposta"][:3000]})
    mensagens.append({"role": "user", "content":
                      f"MATERIAL DO CASO (é tudo o que existe registrado):\n"
                      f"{material}\n\n"
                      f"=== PERGUNTA DO ADVOGADO ===\n{pergunta}"})

    s = get_settings()
    cliente = _claude()
    feitas: list[dict] = []
    recusadas: list[dict] = []
    perguntas: list[dict] = []
    texto = ""

    for _ in range(2):
        rr = cliente.messages.create(
            model=s.claude_model, max_tokens=2500, system=SYSTEM,
            tools=[FERRAMENTA_ALTERAR, FERRAMENTA_CLIENTE],
            messages=mensagens)
        texto = "".join(b.text for b in rr.content if b.type == "text").strip()
        usos = [b for b in rr.content if getattr(b, "type", "") == "tool_use"]
        if not usos:
            break
        mensagens.append({"role": "assistant", "content": rr.content})
        saidas = []
        for u in usos:
            if u.name == "falar_com_o_cliente":
                dados = u.input or {}
                saida = _consultar_cliente(caso_id, dados, quem)
                if saida.get("enviada"):
                    perguntas.append({"assunto": dados.get("assunto", ""),
                                      "pergunta": dados.get("pergunta", "")})
            else:
                base, ok, nao = _aplicar(
                    base, (u.input or {}).get("alteracoes") or [])
                feitas += ok
                recusadas += nao
                saida = {"aplicadas": len(ok),
                         "recusadas": [{"procurar": x.get("procurar", "")[:120],
                                        "porque": x.get("porque")} for x in nao]}
            saidas.append({"type": "tool_result", "tool_use_id": u.id,
                           "content": json.dumps(saida, ensure_ascii=False)})
        mensagens.append({"role": "user", "content": saidas})

    texto = humanizar(texto) or ("Não consegui montar a resposta agora. "
                                 "Tente de novo em instantes.")
    if recusadas:
        texto += ("\n\nNão consegui aplicar "
                  + ("1 alteração" if len(recusadas) == 1
                     else f"{len(recusadas)} alterações")
                  + ": " + "; ".join(str(x.get("porque")) for x in recusadas)
                  + ". O trecho pode ter mudado depois que eu li.")

    registrar_evento(caso_id, "ADVOGADO_CONSULTOU_PECA", {
        "peticao": peticao_id, "quem": quem,
        "pergunta": pergunta[:500], "resposta": texto[:1000],
        "alteracoes": [{"motivo": a.get("motivo", "")} for a in feitas],
        "recusadas": len(recusadas), "ao_cliente": perguntas})

    saida = {"pergunta": pergunta, "resposta": texto, "em": _agora(),
             "ao_cliente": perguntas,
             "alteracoes": [{"motivo": a.get("motivo", "")} for a in feitas]}
    if feitas:
        saida["texto"] = base
    return saida


def consultas(peticao_id: str, limite: int = 50) -> list[dict]:
    """O histórico das tratativas desta peça, em ordem."""
    try:
        linhas = get_db().table("eventos") \
            .select("payload,criado_em").eq("tipo", "ADVOGADO_CONSULTOU_PECA") \
            .order("criado_em").limit(400).execute().data or []
    except Exception:
        return []
    saida = []
    for l in linhas:
        pay = l.get("payload") or {}
        if pay.get("peticao") != peticao_id:
            continue
        quem = (pay.get("quem") or "").strip()
        alt = pay.get("alteracoes")
        saida.append({
            "quem_rotulo": (f"{quem} (advogado)" if quem
                            and quem.lower() != "advogado" else "Advogado"),
            "pergunta": pay.get("pergunta"),
            "resposta": pay.get("resposta"),
            "alteracoes": alt if isinstance(alt, list) else [],
            "ao_cliente": pay.get("ao_cliente") or [],
            "em": l.get("criado_em")})
    return saida[-limite:]


def salvar_texto(peticao_id: str, texto: str, quem: str = "") -> dict:
    """Grava a correção do advogado, guardando a versão anterior.

    Escreve em `markdown_final`, e não em `markdown_base`: a base é a
    minuta com as marcações de jurisprudência, e é dela que a injeção de
    precedentes parte. Sobrescrevê-la faria a próxima rodada de
    precedentes partir de um texto já editado e duplicar julgado.

    O efeito colateral que isso cria está avisado na tela: rodar os
    precedentes de novo refaz o `markdown_final` a partir da base e
    desfaz o que foi corrigido à mão."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("A peça está vazia.")
    db = get_db()
    r = db.table("peticoes").select("markdown_final,markdown_base,caso_id") \
        .eq("id", peticao_id).limit(1).execute().data
    if not r:
        raise ValueError("Peça não encontrada.")
    anterior = r[0].get("markdown_final") or r[0].get("markdown_base") or ""

    campos = {"markdown_final": texto, "editada_em": _agora(),
              "editada_por": quem or "advogado", "atualizado_em": _agora()}
    if anterior and anterior != texto:
        campos["markdown_anterior"] = anterior
    db.table("peticoes").update(campos).eq("id", peticao_id).execute()
    return {"ok": True, "caracteres": len(texto)}
