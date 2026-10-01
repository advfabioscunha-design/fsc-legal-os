"""O VÍNCULO COM QUEM JÁ FOI CLIENTE.

Felicitação de aniversário e lembrança em data importante. É pouca
coisa, e é justamente por ser pouca que precisa ser bem feita: uma
mensagem repetida, ou mandada para quem pediu para parar, estraga mais
relação do que o silêncio teria estragado.

AS QUATRO TRAVAS, E POR QUE CADA UMA EXISTE

  NÃO ENVIA DUAS VEZES. A rotina roda todo dia às 9h, e o botão de rodar
  à mão existe. Sem registro do que já saiu, servidor reiniciado ou
  clique repetido mandavam dois "feliz aniversário" no mesmo dia, e
  nada denuncia mais uma máquina do que isso.

  RESPEITA QUEM PEDIU PARA PARAR. Pedido de descadastro ignorado vira
  reclamação na OAB e bloqueio do número na Meta, as duas coisas ao
  mesmo tempo.

  SEPARA CORTESIA DE COMUNICAÇÃO DE MASSA. Parabéns a quem é cliente
  cabe no legítimo interesse: a pessoa confiou um processo ao
  escritório. Informativo periódico é outra natureza, e por isso só sai
  para quem pediu, com o campo próprio ligado.

  NÃO FALA DE PROCESSO. Felicitação é felicitação. Misturar "e o seu
  processo está andando" numa mensagem de aniversário transforma
  cortesia em cobrança, e é o tipo de coisa que faz a pessoa associar o
  escritório a uma preocupação em vez de a um cuidado.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..core.db import get_db, registrar_evento

# Brasília. É o relógio que o escritório usa, e o aniversário é do dia de
# quem recebe, não do UTC: sem isto, quem faz aniversário dia 10 recebia
# o parabéns dia 9 à noite.
_FUSO = timezone(timedelta(hours=-3))

# O expediente. Felicitação é cortesia, e cortesia fora de hora vira
# incômodo: mensagem do escritório às 6h da manhã ou às 22h assusta em
# vez de agradar, e quem está com processo em curso pensa logo no pior.
HORA_ABRE, HORA_FECHA = 8, 18


def dentro_do_expediente() -> bool:
    agora = _hoje()
    # Sábado e domingo não. O escritório não trabalha, e mensagem
    # automática no fim de semana denuncia a máquina na hora.
    if agora.weekday() >= 5:
        return False
    return HORA_ABRE <= agora.hour < HORA_FECHA

# A mensagem de reserva. Só sai quando o modelo não responde, e é
# escrita de um jeito que não envergonhe: melhor uma frase correta e
# simples do que silêncio no aniversário de um cliente.
MSG_RESERVA = (
    "Feliz aniversário, {nome}! É uma honra ter você como cliente, e a FC "
    "Advocacia não deixaria esta data passar sem desejar um dia muito bom "
    "para você e para quem está perto.\n\nDr. Fábio Cunha e equipe")


def _regua() -> str:
    """A calibração de como o escritório felicita, do arquivo da skill."""
    from pathlib import Path
    try:
        return (Path(__file__).parent / "skills" /
                "felicitacao_do_escritorio.md").read_text(encoding="utf-8")
    except Exception:
        return ("Escreva uma felicitação de aniversário curta e calorosa em "
                "nome da FC Advocacia. Diga que é uma honra tê-lo como "
                "cliente e que o escritório não deixaria a data passar em "
                "branco. Nada sobre o processo, nada de oferta, nada de "
                "promessa de resultado.")


def _ja_disse_a_esta_pessoa(cliente_id: str) -> list[str]:
    """As mensagens que ESTA pessoa já recebeu, para não repetir nenhuma."""
    try:
        r = get_db().table("relacionamento_envios").select("texto") \
            .eq("cliente_id", cliente_id).eq("tipo", "ANIVERSARIO") \
            .order("enviado_em", desc=True).limit(8).execute().data or []
        return [str(x.get("texto") or "") for x in r if x.get("texto")]
    except Exception:
        return []


def escrever_felicitacao(cliente_id: str, nome: str) -> str:
    """A mensagem daquela pessoa, diferente de todas que ela já recebeu.

    O histórico dela vai no pedido com todas as letras. É o que impede o
    terceiro ano seguido de "desejamos saúde, paz e realizações": quem
    recebe a mesma frase duas vezes percebe o molde, e o que era carinho
    vira correspondência de banco."""
    primeiro = (nome or "").strip().split(" ")[0] or "tudo bem"
    anteriores = _ja_disse_a_esta_pessoa(cliente_id)

    try:
        import anthropic
        from ..core.config import get_settings
        from ..core.ia import TEMPO_LIMITE, TENTATIVAS
        s = get_settings()
        if not s.claude_api_key:
            return MSG_RESERVA.format(nome=primeiro)

        pedido = [f"Escreva a felicitação de aniversário para {primeiro}."]
        if anteriores:
            pedido.append(
                "ESTA PESSOA JÁ RECEBEU AS MENSAGENS ABAIXO. Nenhuma delas "
                "pode voltar, nem parecida. Mude a estrutura, não o "
                "sinônimo:\n\n"
                + "\n\n---\n\n".join(anteriores))
        else:
            pedido.append("É a primeira felicitação que esta pessoa recebe "
                          "do escritório.")

        r = anthropic.Anthropic(api_key=s.claude_api_key,
                                timeout=TEMPO_LIMITE,
                                max_retries=TENTATIVAS).messages.create(
            model=s.claude_model, max_tokens=400, system=_regua(),
            messages=[{"role": "user", "content": "\n\n".join(pedido)}])
        texto = "".join(b.text for b in r.content
                        if getattr(b, "type", "") == "text").strip()
    except Exception as e:
        print(f"[relacionamento] felicitação não escrita pelo agente: {e}")
        texto = ""

    from ..core.texto import humanizar
    texto = humanizar(texto).strip().strip('"')
    if len(texto) < 40:
        return MSG_RESERVA.format(nome=primeiro)

    # A ÚLTIMA CONFERÊNCIA, FEITA POR CÓDIGO
    #
    # O modelo foi instruído a não repetir, e quase sempre não repete.
    # "Quase sempre" não serve para uma mensagem que sai sozinha: aqui se
    # compara com o que ela já recebeu, e a repetição cai para a reserva.
    normal = " ".join(texto.lower().split())
    for velha in anteriores:
        if normal == " ".join(str(velha).lower().split()):
            return MSG_RESERVA.format(nome=primeiro)
    return texto


def _hoje() -> datetime:
    return datetime.now(_FUSO)


def _ja_foi(cliente_id: str, tipo: str, referencia: str) -> bool:
    try:
        r = get_db().table("relacionamento_envios").select("id") \
            .eq("cliente_id", cliente_id).eq("tipo", tipo) \
            .eq("referencia", referencia).limit(1).execute().data
        return bool(r)
    except Exception as e:
        # Tabela ausente ou banco fora: NÃO envia. Na dúvida entre
        # repetir e não mandar, não mandar é o erro barato.
        print(f"[relacionamento] não consegui conferir o histórico: {e}")
        return True


def _registrar(cliente_id: str, tipo: str, referencia: str,
               texto: str, erro: str = "") -> None:
    try:
        get_db().table("relacionamento_envios").insert({
            "cliente_id": cliente_id, "tipo": tipo, "referencia": referencia,
            "canal": "WHATSAPP", "texto": texto[:1000],
            "erro": erro[:300] or None,
        }).execute()
    except Exception as e:
        print(f"[relacionamento] envio não registrado: {e}")


def _pode_receber(c: dict, tipo: str) -> tuple[bool, str]:
    """Quem recebe, e o motivo de quem não recebe.

    O motivo volta para a tela do escritório: lista de 400 clientes com
    12 envios e sem explicação faz qualquer um achar que quebrou."""
    if c.get("descadastrado_em"):
        return False, "pediu para não receber"
    if not c.get("whatsapp"):
        return False, "sem WhatsApp no cadastro"
    if tipo == "ANIVERSARIO" and c.get("aceita_felicitacoes") is False:
        return False, "não aceita felicitações"
    if tipo == "INFORMATIVO" and not c.get("aceita_informativos"):
        return False, "não autorizou informativos"
    return True, ""


def aniversariantes_de_hoje() -> list[dict]:
    """Quem faz aniversário hoje, com o motivo de quem não vai receber.

    Serve à tela do escritório, que mostra a lista ANTES de qualquer
    disparo: ver quem vai receber é o que permite corrigir um cadastro
    errado antes de a mensagem sair, e não depois."""
    hoje = _hoje().strftime("%m-%d")
    ano = _hoje().strftime("%Y")
    try:
        clientes = get_db().table("clientes").select(
            "id,nome,whatsapp,data_nascimento,aceita_felicitacoes,"
            "aceita_informativos,descadastrado_em"
        ).not_.is_("data_nascimento", "null").execute().data or []
    except Exception as e:
        print(f"[relacionamento] base não lida: {e}")
        return []

    saida = []
    for c in clientes:
        dn = str(c.get("data_nascimento") or "")
        if len(dn) < 10 or dn[5:10] != hoje:
            continue
        pode, motivo = _pode_receber(c, "ANIVERSARIO")
        saida.append({
            "id": c["id"], "nome": c.get("nome") or "",
            "whatsapp": c.get("whatsapp") or "",
            "vai_receber": pode and not _ja_foi(c["id"], "ANIVERSARIO", ano),
            "motivo": motivo or ("já enviado hoje"
                                 if _ja_foi(c["id"], "ANIVERSARIO", ano)
                                 else ""),
        })
    return saida


def parabenizar_aniversariantes() -> dict:
    """A rotina das 9h. Idempotente: rodar de novo não manda de novo."""
    if not dentro_do_expediente():
        # Não é falha: é a rotina sabendo que não é hora. Quem faz
        # aniversário hoje continua na lista e recebe na próxima passada
        # dentro do expediente.
        return {"enviados": 0, "adiado": "fora do expediente",
                "agora": _hoje().strftime("%H:%M"),
                "janela": f"{HORA_ABRE}h às {HORA_FECHA}h de Brasília, dias úteis"}

    ano = _hoje().strftime("%Y")
    lista = aniversariantes_de_hoje()
    from ..integracoes.whatsapp import _enviar

    enviados, pulados = 0, []
    for a in lista:
        if not a["vai_receber"]:
            pulados.append({"nome": a["nome"], "motivo": a["motivo"]})
            continue
        texto = escrever_felicitacao(a["id"], a["nome"])
        # O registro vem ANTES do envio. Falhando o envio, fica a linha
        # com o erro e o cliente não recebe duas tentativas; falhando o
        # registro depois do envio, ele receberia de novo amanhã.
        _registrar(a["id"], "ANIVERSARIO", ano, texto)
        try:
            _enviar(a["whatsapp"], texto)
            enviados += 1
        except Exception as e:
            print(f"[relacionamento] parabéns não saiu para {a['nome']}: {e}")
            try:
                get_db().table("relacionamento_envios").update(
                    {"erro": str(e)[:300]}
                ).eq("cliente_id", a["id"]).eq("tipo", "ANIVERSARIO") \
                 .eq("referencia", ano).execute()
            except Exception:
                pass

    registrar_evento(None, "ANIVERSARIOS_ENVIADOS",
                     {"total": enviados, "pulados": len(pulados),
                      "data": _hoje().strftime("%Y-%m-%d")})
    return {"enviados": enviados, "pulados": pulados,
            "aniversariantes": len(lista)}


def descadastrar(cliente_id: str, motivo: str = "") -> dict:
    """O cliente pediu para não receber mais. Vale para tudo."""
    agora = datetime.now(timezone.utc).isoformat()
    get_db().table("clientes").update({
        "descadastrado_em": agora,
        "descadastro_motivo": (motivo or "pedido do cliente")[:300],
        "aceita_felicitacoes": False, "aceita_informativos": False,
        "atualizado_em": agora,
    }).eq("id", cliente_id).execute()
    registrar_evento(None, "RELACIONAMENTO_DESCADASTRO",
                     {"cliente_id": cliente_id, "motivo": motivo})
    return {"ok": True}


def religar(cliente_id: str, origem: str = "") -> dict:
    """O cliente voltou a aceitar. Guarda de onde veio a autorização."""
    agora = datetime.now(timezone.utc).isoformat()
    get_db().table("clientes").update({
        "descadastrado_em": None, "descadastro_motivo": None,
        "aceita_felicitacoes": True,
        "origem_consentimento": (origem or "pedido do cliente")[:200],
        "consentimento_em": agora, "atualizado_em": agora,
    }).eq("id", cliente_id).execute()
    return {"ok": True}
