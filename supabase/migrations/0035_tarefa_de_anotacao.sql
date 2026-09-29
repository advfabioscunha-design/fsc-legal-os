-- 0035 — a tarefa precisa saber de qual pendência nasceu.
--
-- A 0034 criou `anotacoes` mas esqueceu o outro lado: `tarefas` não
-- tinha onde guardar a origem, e o plano do dia morria com PGRST204 ao
-- tentar gravar `anotacao_id`. Sem esta coluna também não há como
-- deduplicar — o plano recriaria a mesma pendência todo dia.

alter table public.tarefas
  add column if not exists anotacao_id uuid
    references public.anotacoes(id) on delete cascade;

-- Uma anotação, uma tarefa viva.
create unique index if not exists idx_tarefas_anotacao_viva
  on public.tarefas(anotacao_id)
  where anotacao_id is not null and status in ('ABERTA', 'REAGENDADA');

-- Mesma regra para publicação e para pedido do balcão: até hoje só o
-- prazo tinha índice, e as outras origens podiam duplicar sem o banco
-- reclamar. Antes do índice, cancelar as cópias já criadas — guarda a
-- mais antiga, que é a que pode ter histórico, e marca as outras como
-- canceladas pelo sistema em vez de apagar.
with copias as (
  select id, row_number() over (
           partition by intimacao_id order by criado_em, id) as n
    from public.tarefas
   where intimacao_id is not null and status in ('ABERTA', 'REAGENDADA')
)
update public.tarefas t
   set status = 'CANCELADA',
       motivo = coalesce(t.motivo || ' · ', '') || 'cópia removida na 0035'
  from copias c
 where c.id = t.id and c.n > 1;

with copias as (
  select id, row_number() over (
           partition by pedido_id order by criado_em, id) as n
    from public.tarefas
   where pedido_id is not null and status in ('ABERTA', 'REAGENDADA')
)
update public.tarefas t
   set status = 'CANCELADA',
       motivo = coalesce(t.motivo || ' · ', '') || 'cópia removida na 0035'
  from copias c
 where c.id = t.id and c.n > 1;

create unique index if not exists idx_tarefas_intimacao_viva
  on public.tarefas(intimacao_id)
  where intimacao_id is not null and status in ('ABERTA', 'REAGENDADA');

create unique index if not exists idx_tarefas_pedido_viva
  on public.tarefas(pedido_id)
  where pedido_id is not null and status in ('ABERTA', 'REAGENDADA');

comment on column public.tarefas.anotacao_id is
  'Pendência anotada à mão que virou tarefa. Fechar a tarefa não fecha a '
  'anotação: quem resolve a pendência escreve o que foi feito, e isso vai '
  'para o histórico do card.';
