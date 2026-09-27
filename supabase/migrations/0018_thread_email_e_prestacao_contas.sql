-- ================================================================
-- 0018 — Um único fio de e-mail por atendimento + prestação de contas
--
-- Todo e-mail do caso entra na MESMA conversa do cliente: o histórico
-- fica inteiro em um lugar só, do primeiro contato até o encerramento.
-- O fim da linha é a prestação de contas, que fecha o atendimento.
-- ================================================================

alter table casos add column if not exists email_thread_id text;
comment on column casos.email_thread_id is
  'Message-ID do primeiro e-mail do caso; os seguintes respondem a ele '
  'para que tudo fique na mesma conversa na caixa do cliente';

create table if not exists prestacoes_contas (
  id              uuid primary key default gen_random_uuid(),
  caso_id         uuid not null references casos(id) on delete cascade,
  -- valores (o que entrou, o que saiu, o que o cliente recebe)
  valor_recebido      numeric(14,2) not null default 0,
  honorarios_contratuais numeric(14,2) not null default 0,
  honorarios_sucumbenciais numeric(14,2) not null default 0,
  despesas            numeric(14,2) not null default 0,
  repasse_cliente     numeric(14,2) not null default 0,
  forma_repasse   text,
  observacoes     text,
  resultado       text,             -- como a causa terminou
  historico       jsonb,            -- linha do tempo congelada no encerramento
  enviada_em      timestamptz,
  ciencia_em      timestamptz,
  criado_em       timestamptz not null default now()
);
create index if not exists idx_prestacoes_caso on prestacoes_contas(caso_id);

alter table prestacoes_contas enable row level security;
drop policy if exists prestacoes_visiveis on prestacoes_contas;
create policy prestacoes_visiveis on prestacoes_contas for select using (
  public.meu_papel() = 'OPERADOR'
  or caso_id in (
    select c.id from casos c
    where c.cliente_id in (select cliente_id from perfis where id = auth.uid())
  )
);
