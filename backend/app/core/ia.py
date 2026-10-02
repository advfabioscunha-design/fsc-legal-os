"""
QUANTO TEMPO ESPERAR PELA IA, E QUANTAS VEZES INSISTIR.

Os dezesseis clientes do projeto eram construídos só com a chave, o que
deixa valer o padrão da biblioteca: DEZ MINUTOS de espera, com duas
novas tentativas por cima. Trinta minutos no pior caso, com a conexão
HTTP aberta o tempo todo.

Ninguém espera trinta minutos. Quem clica desiste em dois, recarrega a
página e clica de novo, e aí há duas revisões do mesmo contrato
rodando ao mesmo tempo, as duas cobradas, uma sobrescrevendo a outra.
O servidor, enquanto isso, segura trabalhadores presos numa espera que
já não interessa a ninguém.

OS NÚMEROS, E POR QUE ESTES

  TEMPO_LIMITE  180 segundos. O trabalho mais pesado do sistema é a
                revisão de um contrato de locação: o modelo inteiro, o
                guia técnico e a minuta de vinte mil caracteres entram
                no pedido, e saem até oito mil fichas de apontamentos.
                Isso leva de um a dois minutos. Três é folga para o dia
                ruim, e é curto o bastante para o operador ainda estar
                olhando a tela quando a resposta chegar.

  TENTATIVAS    1. A biblioteca repete sozinha quando a resposta é de
                sobrecarga ou de rede, e repetir uma vez resolve a
                maioria desses casos. Repetir duas apenas triplica a
                espera de quem já estava esperando demais, e cada
                tentativa é cobrada de novo.

O que NÃO se resolve com paciência: chave errada, conta sem saldo,
pedido malformado. Esses voltam na primeira tentativa, em menos de um
segundo, e insistir não ajudaria.
"""
from __future__ import annotations

TEMPO_LIMITE = 180.0
TENTATIVAS = 1


# ══════════════════════════════════════════════════════════════════
# O QUE DIZER QUANDO A IA RECUSA
#
# A API da Anthropic recusa por motivos bem diferentes, e todos chegam
# aqui como uma exceção em inglês com um JSON dentro. Para quem está no
# painel, todos viravam a mesma frase: "Deu erro aqui no servidor".
#
# Três deles não são defeito do sistema e têm conserto de um minuto no
# painel de cobrança: saldo acabado, TETO DE GASTO atingido e chave
# errada. Os outros são temporários e pedem só paciência.
#
# Confundir os cinco custa caro. O operador clica de novo cinco vezes,
# chama quem fez o sistema, e o problema estava num botão do console
# que ninguém sabia que existia.
# ══════════════════════════════════════════════════════════════════
import re as _re
from datetime import datetime as _dt

_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
          "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# "You will regain access on 2026-11-01 at 00:00 UTC."
_QUANDO_VOLTA = _re.compile(
    r"regain access on\s+(\d{4})-(\d{2})-(\d{2})", _re.IGNORECASE)


def _por_extenso(texto: str) -> str:
    """A data que vem no erro, escrita como gente lê."""
    m = _QUANDO_VOLTA.search(texto or "")
    if not m:
        return ""
    ano, mes, dia = (int(x) for x in m.groups())
    try:
        nome = _MESES[mes - 1]
    except IndexError:
        return ""
    return f"{'1º' if dia == 1 else dia} de {nome} de {ano}"


def explicar(erro) -> dict | None:
    """Traduz a recusa da IA. None quando o erro é de outra natureza.

    Devolve {motivo, detalhe, status, pode_tentar_de_novo}. `motivo` é
    curto e serve para o registro; `detalhe` é a frase que vai para a
    tela, e ela tem de dizer o que fazer, não só o que houve."""
    texto = str(erro or "")
    baixo = texto.lower()

    # 1. O TETO DE GASTO, que é o mais confuso de todos
    #
    # A conta tem saldo. O que acabou foi o LIMITE que o próprio
    # escritório definiu no console, e ele se renova sozinho no dia 1º.
    # Quem lê "usage limits" em inglês vai procurar defeito no sistema, e
    # o conserto é um campo no painel de cobrança.
    if "usage limit" in baixo or "regain access on" in baixo:
        quando = _por_extenso(texto)
        volta = (f" O acesso volta sozinho em {quando}." if quando
                 else " O acesso volta sozinho na virada do mês.")
        return {
            "motivo": "TETO_DE_GASTO",
            "status": 503,
            "pode_tentar_de_novo": False,
            "detalhe": (
                "A conta de IA do escritório atingiu o TETO DE GASTO que "
                "foi configurado, e por isso nenhum agente consegue "
                "trabalhar agora." + volta + " Para liberar antes, entre em "
                "console.anthropic.com, vá em Settings e depois Limits, e "
                "aumente o limite mensal de gasto. Não é falta de saldo: é "
                "um teto que a própria conta definiu. Nada se perdeu, e "
                "assim que o limite subir é só clicar de novo."),
        }

    # 2. Saldo acabado de verdade
    if "credit balance" in baixo or "insufficient" in baixo:
        return {
            "motivo": "SEM_SALDO",
            "status": 503,
            "pode_tentar_de_novo": False,
            "detalhe": (
                "A conta de IA do escritório está sem saldo, e por isso "
                "nenhum agente consegue trabalhar agora. Recarregue em "
                "console.anthropic.com, em Plans & Billing. Assim que o "
                "saldo entrar, é só clicar de novo: nada se perdeu."),
        }

    # 3. A chave
    if ("authentication" in baixo or "invalid x-api-key" in baixo
            or "invalid api key" in baixo or "permission_error" in baixo):
        return {
            "motivo": "CHAVE",
            "status": 503,
            "pode_tentar_de_novo": False,
            "detalhe": (
                "A chave de IA do escritório não está sendo aceita. Ou ela "
                "foi trocada no console e não foi atualizada no servidor, "
                "ou foi revogada. Confira em console.anthropic.com, em API "
                "Keys, e atualize a variável CLAUDE_API_KEY no servidor."),
        }

    # 4. Sobrecarga e excesso de chamadas: passam sozinhos
    if ("rate limit" in baixo or "429" in baixo or "overloaded" in baixo
            or "529" in baixo):
        return {
            "motivo": "SOBRECARGA",
            "status": 503,
            "pode_tentar_de_novo": True,
            "detalhe": (
                "A IA está recebendo mais pedidos do que consegue atender "
                "neste momento. Isso passa sozinho em alguns minutos. "
                "Espere um pouco e clique de novo: nada se perdeu."),
        }

    # 5. Demora
    if "timeout" in baixo or "timed out" in baixo:
        return {
            "motivo": "DEMORA",
            "status": 504,
            "pode_tentar_de_novo": True,
            "detalhe": (
                "A IA demorou mais do que o limite de espera e a chamada "
                "foi cortada. Costuma passar na segunda tentativa. Clique "
                "de novo: nada se perdeu."),
        }

    return None


def frase(erro, quando_nao_for_da_ia: str = "") -> str:
    """A frase para a tela, seja recusa da IA ou outra coisa."""
    diag = explicar(erro)
    if diag:
        return diag["detalhe"]
    return quando_nao_for_da_ia or f"{type(erro).__name__}: {str(erro)[:300]}"


# ══════════════════════════════════════════════════════════════════
# QUANDO A IA ESTÁ FORA, O SISTEMA PARA DE INSISTIR
#
# A esteira roda a cada quinze minutos e toca todos os pedidos em
# andamento. Com a conta bloqueada, cada rodada tentava redigir, revisar
# e ajustar CADA pedido, e cada tentativa falhava do mesmo jeito.
#
# O estrago não é só desperdício. O log enche de erro, o que esconde o
# erro de verdade quando ele aparecer; cada tentativa gasta uma conexão
# e o tempo do trabalhador; e, no caso de sobrecarga, insistir é
# exatamente o que faz a sobrecarga durar mais.
#
# Isto aqui lembra que a IA recusou e por quê, e manda o resto do
# sistema nem tentar até a hora de voltar. A memória é da instância: ela
# some quando o servidor reinicia, e isso está certo, porque reiniciar
# é também o que acontece depois de alguém arrumar a conta.
# ══════════════════════════════════════════════════════════════════
import time as _time
import threading as _threading

_tranca = _threading.Lock()
_fora: dict | None = None

# Quanto tempo esperar antes de tentar de novo, por motivo. O teto de
# gasto tem data certa e vem no próprio erro; os outros são palpite
# conservador: curto o bastante para não atrasar a volta, longo o
# bastante para não virar martelo.
_ESPERA = {"SOBRECARGA": 5 * 60, "DEMORA": 2 * 60,
           "SEM_SALDO": 10 * 60, "CHAVE": 10 * 60, "TETO_DE_GASTO": 30 * 60}


def _ate_quando(diag: dict) -> float:
    """O instante em que vale a pena tentar de novo."""
    agora = _time.time()
    if diag["motivo"] == "TETO_DE_GASTO":
        m = _QUANDO_VOLTA.search(diag.get("origem", ""))
        if m:
            try:
                volta = _dt(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                # A data vem em UTC e o erro diz 00:00. Tentar meia hora
                # depois evita bater no segundo exato da virada.
                return max(volta.timestamp() + 1800, agora + 60)
            except ValueError:
                pass
    return agora + _ESPERA.get(diag["motivo"], 5 * 60)


def anotar_recusa(erro) -> dict | None:
    """Registra que a IA recusou. Devolve o diagnóstico, ou None."""
    diag = explicar(erro)
    if not diag:
        return None
    diag = dict(diag)
    diag["origem"] = str(erro)[:600]
    diag["ate"] = _ate_quando(diag)
    with _tranca:
        global _fora
        _fora = diag
    print(f"[ia] indisponível ({diag['motivo']}), "
          f"não tento de novo por enquanto")
    return diag


def indisponivel() -> dict | None:
    """O diagnóstico, se a IA ainda estiver fora. None quando vale tentar.

    Quem chama decide o que fazer: a esteira pula o pedido e tenta na
    próxima rodada; uma rota chamada por gente devolve a frase, porque
    quem clicou merece saber por que não aconteceu nada."""
    with _tranca:
        global _fora
        if not _fora:
            return None
        if _time.time() >= _fora.get("ate", 0):
            # Passou a hora: limpa e deixa tentar. Se continuar fora, a
            # próxima falha anota de novo.
            _fora = None
            return None
        return dict(_fora)


def liberou() -> None:
    """A IA respondeu. Esquece a recusa anterior."""
    with _tranca:
        global _fora
        if _fora:
            print("[ia] voltou a responder")
            _fora = None


def estado() -> dict:
    """Para a tela mostrar, e para quem quiser conferir sem tentar."""
    d = indisponivel()
    if not d:
        return {"disponivel": True}
    return {"disponivel": False, "motivo": d["motivo"],
            "detalhe": d["detalhe"],
            "pode_tentar_de_novo": d["pode_tentar_de_novo"],
            "voltar_a_tentar_em": max(0, int(d.get("ate", 0) - _time.time()))}


# ── O CLIENTE QUE SE LEMBRA DO QUE ACONTECEU ─────────────────────
#
# Anotar a recusa num lugar e esquecer de soltar o freio no outro é o
# jeito de deixar o sistema parado DEPOIS de alguém já ter arrumado a
# conta. Então quem registra o sucesso e a falha é o próprio caminho por
# onde toda chamada passa.
#
# O embrulho é fino de propósito: ele não muda nada da chamada, não
# tenta de novo, não engole erro. Só observa e repassa.
class _Mensagens:
    def __init__(self, interno):
        self._interno = interno

    def create(self, *a, **kw):
        try:
            r = self._interno.create(*a, **kw)
        except Exception as e:
            anotar_recusa(e)
            raise
        liberou()
        return r

    def __getattr__(self, nome):
        return getattr(self._interno, nome)


class _Cliente:
    def __init__(self, interno):
        self._interno = interno
        self.messages = _Mensagens(interno.messages)

    def __getattr__(self, nome):
        return getattr(self._interno, nome)


def cliente(chave: str):
    """O cliente da Anthropic do jeito que este sistema usa.

    Mesmo tempo de espera, mesmo número de tentativas e a observação do
    que aconteceu. Quem precisar do cliente cru ainda tem `_interno`."""
    import anthropic
    return _Cliente(anthropic.Anthropic(
        api_key=chave, timeout=TEMPO_LIMITE, max_retries=TENTATIVAS))
