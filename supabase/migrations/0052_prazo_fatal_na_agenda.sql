-- 0052 — o dia em que não dá mais, e a cadeia que fecha junto.
--
-- A agenda mostrava a data de fazer, que é a data de trabalho, e não a
-- data limite. São coisas diferentes, e a diferença é o que separa um
-- dia corrido de uma perda de prazo: quem olha o compromisso precisa
-- saber se ainda tem folga ou se hoje é o último dia.
--
-- A intimação ficava de fora da agenda. Ela é o começo do trabalho, e
-- vivia só na tela de intimações: o advogado olhava dois lugares para
-- saber o que o dia exigia. Pior, marcar resolvida lá não mexia na
-- agenda, e marcar realizado aqui não mexia lá. Duas telas discordando
-- sobre o mesmo ato é pior do que uma tela só, porque ensina a não
-- confiar em nenhuma das duas.
--
-- Com o `intimacao_id`, o "realizado" da agenda fecha a cadeia inteira:
-- o compromisso, o prazo que ele espelha, a tarefa que o originou e a
-- intimação que o motivou. E o que foi feito vira linha no histórico
-- do caso, que é de onde sai a prestação de contas. Trabalho que não
-- fica registrado não existe na hora de prestar contas, e foi feito do
-- mesmo jeito.

alter table public.agenda_itens
  add column if not exists prazo_fatal   date,
  add column if not exists intimacao_id  uuid
      references public.intimacoes(id) on delete set null,
  add column if not exists concluido_em  timestamptz,
  add column if not exists resultado     text;

comment on column public.agenda_itens.prazo_fatal is
  'O último dia possível para o ato. A coluna `data` é quando se '
  'pretende fazer; esta é quando deixa de ser possível.';

comment on column public.agenda_itens.intimacao_id is
  'A intimação que originou o compromisso. É por ela que o realizado '
  'da agenda fecha a intimação, sem ninguém precisar lembrar.';

comment on column public.agenda_itens.resultado is
  'O que houve, nas palavras de quem fez. Vai para o histórico do '
  'caso e para a prestação de contas.';

-- O que vence primeiro aparece primeiro, e o que não tem fatal não
-- atrapalha a ordenação.
create index if not exists idx_agenda_fatal
  on public.agenda_itens(prazo_fatal)
  where prazo_fatal is not null and status in ('ABERTO', 'CONFIRMADO');

create index if not exists idx_agenda_intimacao
  on public.agenda_itens(intimacao_id)
  where intimacao_id is not null;
