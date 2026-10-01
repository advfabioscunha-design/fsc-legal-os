"""APOSENTADO. NÃO LIGUE ISTO DE VOLTA.

Este módulo era o "Módulo 1 — fundação omnichannel": um chatbot de
WhatsApp com prompt genérico, que respondia educadamente sem saber nada
do caso do cliente, criava um cadastro novo a cada número e não
conhecia pedido, prazo nem plataforma.

Ele ficou ligado em `/api/whatsapp/webhook` ao mesmo tempo que o
atendimento de verdade estava em `/webhooks/whatsapp`. Qual dos dois o
cliente encontrava dependia de qual endereço estivesse escrito no painel
da Meta, e apontar para o errado não dava erro nenhum: dava atendimento
ruim, em silêncio.

O atendimento do WhatsApp vive em `integracoes/whatsapp.py`, e é ele que
roteia para o balcão, para o especialista do caso ou para a triagem de
um lead novo, com o MESMO agente que responde no chat da plataforma.

Este arquivo fica como lápide, e não como código: quem procurar por
"omni" daqui a seis meses precisa achar o motivo, não um módulo pronto
para ser religado por engano.
"""

MOTIVO = (
    "whatsapp_omni foi aposentado. Use integracoes/whatsapp.py, que é o "
    "atendimento de verdade: conhece o pedido, o caso e o prazo, e usa o "
    "mesmo agente do chat da plataforma."
)


def __getattr__(nome: str):
    raise RuntimeError(f"{MOTIVO} (tentou usar: {nome})")
