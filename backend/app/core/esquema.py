"""QUANDO O CÓDIGO ESTÁ NA FRENTE DO BANCO.

O código sobe pelo Docker e as migrações rodam à mão, no painel do
Supabase. Entre uma coisa e outra existe uma janela, às vezes de dias, em
que o programa pede uma coluna que ainda não existe.

O que o operador via nessa janela era "Deu erro aqui no servidor ao
executar esta ação" — a mesma frase para falta de migração, falta de
permissão e queda de rede. Três problemas diferentes, com três soluções
diferentes, e uma frase só para os três. Quem está olhando a tela não
tem como saber que basta rodar um SQL.

Este módulo traduz o erro do banco em uma frase que resolve: diz QUAL
migração falta e o que para de funcionar sem ela. É a diferença entre
abrir o log do servidor e abrir o painel do Supabase.
"""
from __future__ import annotations

import re

# Cada coluna e tabela nova, com a migração que a cria. Quem acrescentar
# uma migração nova acrescenta aqui também: é o que faz o aviso continuar
# apontando o arquivo certo em vez de virar um palpite.
DE_ONDE_VEM = {
    # 0055 — o humano assume a conversa
    "humano_em": "0055", "humano_quem": "0055",
    "cliente_digitando_em": "0055",
    # 0056 — a mesa da peça judicial
    "markdown_anterior": "0056", "editada_em": "0056",
    "editada_por": "0056",
    # 0057 — o acervo de legislação
    "legislacao": "0057",
    # 0058 — o acesso de quem veio do WhatsApp
    "codigo_acesso": "0058", "codigo_acesso_em": "0058",
    "codigo_usado_em": "0058",
    # 0059 — a agenda de contatos
    "contatos_whatsapp": "0059",
    # 0060 — o banco de relacionamento
    "aceita_felicitacoes": "0060", "aceita_informativos": "0060",
    "descadastrado_em": "0060", "descadastro_motivo": "0060",
    "origem_consentimento": "0060", "consentimento_em": "0060",
    "relacionamento_nota": "0060", "relacionamento_envios": "0060",
    # 0061 — o aceite dos termos na entrada
    "aceite_termos_em": "0061", "aceite_termos_versao": "0061",
    "aceite_privacidade_em": "0061", "aceite_privacidade_versao": "0061",
    "aceite_origem_ip": "0061",
    # 0062 — os advogados parceiros e o controle de acesso do admin
    "parceiros": "0062", "parcerias": "0062", "repasses_parceiro": "0062",
    "acessos_por_caso": "0062", "registro_de_acessos": "0062",
    "pode_usar_ia": "0062", "pode_falar_com_cliente": "0062",
}

O_QUE_PARA = {
    "0055": "o advogado assumir a conversa do cliente no balcão",
    "0056": "salvar a correção da petição na mesa da peça",
    "0057": "o especialista citar lei do acervo conferido",
    "0058": "o cliente que veio do WhatsApp criar o acesso à plataforma",
    "0059": "a agenda de contatos de WhatsApp no card do caso",
    "0060": "o cadastro de clientes e as felicitações de aniversário",
    "0061": "registrar o aceite dos termos quando o cliente cria o acesso",
    "0062": "os advogados parceiros, a divisão de honorários e o controle "
            "de acesso por caso",
    "0063": "o papel PARCEIRO no tipo papel_usuario — sem ele o cadastro "
            "do advogado parceiro não consegue gravar o papel",
}

# As mensagens que o PostgREST devolve quando o nome não existe.
#
# As aspas aparecem de três jeitos: simples, duplas e duplas ESCAPADAS,
# porque o erro vem dentro de um JSON que já foi para texto. Sem a barra
# invertida no padrão, `relation \"public.contatos_whatsapp\" does not
# exist` passava batido e o operador voltava a ver o erro genérico.
_ASPAS = r"[\\\"'`]*"
_SEM_COLUNA = re.compile(
    rf"column\s+{_ASPAS}([\w.]+){_ASPAS}\s+does not exist"
    rf"|could not find the {_ASPAS}([\w.]+){_ASPAS}\s+column"
    rf"|relation\s+{_ASPAS}([\w.]+){_ASPAS}\s+does not exist"
    rf"|could not find the table\s+{_ASPAS}([\w.]+){_ASPAS}",
    re.IGNORECASE)


def _nomes_citados(texto: str) -> list[str]:
    """Os pedaços do nome que o erro cita, do mais específico ao menos.

    O banco diz "clientes.aceita_felicitacoes" quando falta a COLUNA e
    "legislacao.artigo" quando falta a TABELA inteira. Olhar só o último
    pedaço acerta o primeiro caso e erra o segundo, e aí o aviso vira um
    genérico que não ajuda ninguém. Olham-se os dois."""
    m = _SEM_COLUNA.search(texto or "")
    if not m:
        return []
    bruto = next((g for g in m.groups() if g), "")
    partes = [p.strip().strip('"\'`') for p in bruto.split(".")]
    partes = [p for p in partes if p and p not in ("public", "")]
    # o último (a coluna) primeiro, depois a tabela
    return list(reversed(partes))


def falta_migracao(erro: Exception | str) -> str | None:
    """A frase que resolve, ou None quando o erro é outra coisa.

    Devolver None para erro que não é de esquema é tão importante quanto
    acertar o que é: avisar "rode a migração" para uma queda de rede
    manda a pessoa procurar no lugar errado."""
    texto = str(erro or "")
    nomes = _nomes_citados(texto)
    if not nomes:
        return None

    numero = next((DE_ONDE_VEM[n] for n in nomes if n in DE_ONDE_VEM), None)
    if not numero:
        return (f"O banco ainda não tem \"{nomes[0]}\". Falta aplicar uma "
                f"migração no Supabase.")

    para = O_QUE_PARA.get(numero, "este recurso")
    return (f"Falta aplicar a migração {numero} no banco. Sem ela, {para} "
            f"não funciona. Abra o SQL Editor do Supabase e rode o arquivo "
            f"supabase/migrations/{numero}_*.sql.")


def erro_amigavel(erro: Exception, quando: str = "") -> str:
    """A frase para a tela, seja falta de migração ou outra coisa."""
    aviso = falta_migracao(erro)
    if aviso:
        return aviso
    inicio = f"Não consegui {quando}. " if quando else ""
    return f"{inicio}{type(erro).__name__}: {str(erro)[:300]}"
