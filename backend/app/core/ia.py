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
