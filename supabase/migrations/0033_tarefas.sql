-- 0033 — o plano de trabalho do escritório.
--
-- Por que não reaproveitar `prazos`: prazo é um fato do processo — tem
-- data fatal, nasce de uma intimação e não se apaga. Tarefa é decisão
-- do escritório sobre QUANDO fazer o trabalho: muda de dia, muda de
-- responsável, é adiada, é concluída. Misturar os dois faria o
-- reagendamento de uma tarefa parecer alteração de prazo processual, e
-- essa é a última confusão que se quer num escritório.
--
-- A tarefa aponta para a origem (prazo, intimação, caso, pedido) e é
-- criada uma vez só por origem — o plano roda todo dia e toda sexta, e
-- sem essa chave a lista dobraria a cada rodada.

create table if not exists public.tarefas (
  id             uuid primary key default gen_random_uuid(),
  titulo         text not null,
  descricao      text,
  origem         text not null,          -- PRAZO|PUBLICACAO|TRIAGEM|CONTRATO|INTERNA
  prazo_id       uuid references public.prazos(id) on delete cascade,
  intimacao_id   uuid references public.intimacoes(id) on delete cascade,
  caso_id        uuid references public.casos(id) on delete cascade,
  pedido_id      uuid,                   -- pedidos_contrato

  data           date not null,          -- quando fazer
  prazo_fatal    date,                   -- o limite real, quando existe
  prioridade     text not null default 'MEDIA',   -- ALTA|MEDIA|BAIXA
  motivo         text,                   -- por que está nesta prioridade

  responsavel_id uuid references public.membros_equipe(id) on delete set null,
  status         text not null default 'ABERTA',  -- ABERTA|REAGENDADA|FEITA|CANCELADA
  adiamentos     integer not null default 0,
  historico      jsonb default '[]'::jsonb,
  criado_por     text default 'AGENTE',
  concluida_em   timestamptz,
  criado_em      timestamptz not null default now()
);

create index if not exists idx_tarefas_data on public.tarefas(data, prioridade);
create index if not exists idx_tarefas_status on public.tarefas(status);
create index if not exists idx_tarefas_resp on public.tarefas(responsavel_id);

-- Uma origem, uma tarefa viva.
create unique index if not exists idx_tarefas_prazo_viva
  on public.tarefas(prazo_id)
  where prazo_id is not null and status in ('ABERTA', 'REAGENDADA');

comment on column public.tarefas.adiamentos is
  'Quantas vezes a tarefa foi empurrada. Três adiamentos dizem algo que '
  'o card sozinho não diz — ou falta informação, ou falta gente.';

comment on column public.tarefas.motivo is
  'Por que esta tarefa está nesta prioridade, em uma frase. Prioridade '
  'sem justificativa ninguém confere, e a lista perde a autoridade.';
