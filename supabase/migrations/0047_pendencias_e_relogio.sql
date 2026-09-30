-- 0047 — o que falta, e o relógio que espera por isso.
--
-- A coleta era tudo ou nada: faltando qualquer informação, o pedido não
-- avançava e o cliente ficava parado. Só que nem toda falta é igual.
--
--   INDISPENSÁVEL   sem isso o documento não se conclui. Nome e CPF de
--                   quem assina, endereço do imóvel, valor do aluguel.
--   COMPLEMENTAR    melhora e não impede. Profissão, telefone, e o
--                   estado civil em contrato que não depende dele.
--
-- Agora o trabalho começa de qualquer jeito: a maior parte do contrato
-- não depende do dado que falta, e escrever o que já dá para escrever
-- adianta o prazo de todo mundo. O que falta vira pendência, e é ela
-- que decide o que se diz ao cliente e se o relógio anda.
--
-- ── POR QUE UMA COLUNA NOVA PARA O RELÓGIO ─────────────────────
--
-- A esteira calculava a virada somando a janela a `fase_em`. Isso
-- funciona enquanto ninguém espera por nada. Com pendência, a conta
-- passa a ter pausa, e pausa não se representa somando horas a uma
-- data: seria preciso guardar também quanto tempo ficou parado, e
-- quando parou, e quando voltou.
--
-- `avanca_em` diz a única coisa que a esteira precisa saber: o momento
-- em que aquele pedido pode andar. Nulo significa parado. A conta de
-- quanto falta fica em um lugar só, na hora de soltar.

alter table public.pedidos_contrato
  add column if not exists pendencias jsonb default '[]'::jsonb,
  add column if not exists avanca_em  timestamptz;

comment on column public.pedidos_contrato.pendencias is
  'O que falta, cada item com rótulo e a marca de obrigatório. É o que '
  'a tela do cliente mostra e o que decide se a entrega pode acontecer.';

comment on column public.pedidos_contrato.avanca_em is
  'Quando a esteira pode mover este pedido para a fase seguinte. Nulo '
  'é relógio parado: ou há pendência indispensável em aberto, ou o '
  'pedido chegou à conferência final, que é onde a automação termina.';

-- Quem já está em alguma das fases automáticas ganha o relógio a
-- partir de agora. Sem isto, a esteira ignoraria os pedidos antigos
-- para sempre, porque `avanca_em` nulo é parado.
update public.pedidos_contrato
   set avanca_em = now() + interval '4 hours'
 where avanca_em is null
   and fase = 'REDACAO'
   and excluido_em is null;

update public.pedidos_contrato
   set avanca_em = now() + interval '2 hours'
 where avanca_em is null
   and fase in ('REVISAO_IA', 'AJUSTE')
   and excluido_em is null;

create index if not exists idx_pedidos_avanco
  on public.pedidos_contrato(avanca_em)
  where avanca_em is not null and excluido_em is null;


-- A observação que o cliente deixa ao aprovar. Não é pedido de
-- alteração: sem um lugar para ela, todo comentário virava pedido de
-- mudança, o documento voltava para ajuste e os dois lados perdiam um
-- dia por causa de uma frase.
alter table public.pedidos_contrato
  add column if not exists observacao_cliente text;
