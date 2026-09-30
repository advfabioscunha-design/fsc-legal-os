-- 0046 — o relógio de cada fase.
--
-- O pedido parava em cada etapa esperando alguém clicar. Num escritório
-- pequeno isso significa que um contrato pago às nove da noite fica
-- parado até a manhã seguinte, não por falta de trabalho, mas por falta
-- de um clique.
--
-- Agora as três primeiras fases andam sozinhas, com janela: quatro
-- horas em elaboração, duas em revisão, duas em ajuste. Depois disso
-- para, e só o advogado move.
--
-- Para saber quando a janela vence é preciso saber quando a fase
-- começou, e não havia essa informação: `atualizado_em` muda a cada
-- mensagem, a cada documento anexado, a cada campo salvo. Usar essa
-- coluna faria o relógio reiniciar sempre que o cliente mandasse um
-- "obrigado" pelo chat.

alter table public.pedidos_contrato
  add column if not exists fase_em timestamptz;

comment on column public.pedidos_contrato.fase_em is
  'Quando o pedido entrou na fase atual. É daqui que se contam as '
  'janelas da esteira automática. Diferente de atualizado_em, que muda '
  'a cada toque no registro e por isso não serve de relógio.';

-- Os pedidos que já existem começam a contar de agora. Usar a data de
-- criação faria a esteira despachar de uma vez tudo o que está parado
-- há semanas, que é exatamente o susto que ninguém quer ao subir isto.
update public.pedidos_contrato
   set fase_em = now()
 where fase_em is null;

create index if not exists idx_pedidos_esteira
  on public.pedidos_contrato(fase, fase_em)
  where excluido_em is null;
