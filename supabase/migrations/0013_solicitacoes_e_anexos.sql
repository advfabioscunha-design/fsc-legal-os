-- ================================================================
-- 0013 — Caixa de mensagens do cliente + envio de documentos
--
-- Caminho que este schema sustenta:
--   esteira precisa de um documento
--     -> operador cria SOLICITAÇÃO no CRM
--     -> solicitação aparece na caixa de mensagens do cliente
--     -> cliente anexa arquivo ou tira foto no próprio chat e clica ENVIAR
--     -> documento cai na pasta do caso (storage + tabela documentos)
--     -> solicitação vira ATENDIDA e o caso volta para a produção
-- ================================================================

-- ── SOLICITAÇÕES (o pedido que a esteira faz ao cliente) ────────
create table if not exists solicitacoes (
  id           uuid primary key default gen_random_uuid(),
  caso_id      uuid not null references casos(id) on delete cascade,
  descricao    text not null,                 -- o que o escritório precisa
  status       text not null default 'PENDENTE',  -- PENDENTE | ATENDIDA | CANCELADA
  criado_por   text not null default 'ESCRITORIO',
  criado_em    timestamptz not null default now(),
  atendida_em  timestamptz
);
create index if not exists idx_solicitacoes_caso
  on solicitacoes(caso_id, status);

-- ── DOCUMENTOS: de onde veio e a qual pedido responde ───────────
alter table documentos add column if not exists solicitacao_id uuid references solicitacoes(id);
alter table documentos add column if not exists enviado_por text not null default 'ESCRITORIO';
  -- CLIENTE | ESCRITORIO
comment on column documentos.enviado_por is
  'CLIENTE = anexado pelo próprio cliente na plataforma; ESCRITORIO = subido no CRM';

-- ── CLIENTES: contato completo (o e-mail passa a ser obrigatório
--    na prática, pois é a chave que liga o login do portal ao caso)
alter table clientes add column if not exists atualizado_em timestamptz not null default now();
create unique index if not exists idx_clientes_email_unico
  on clientes (lower(email)) where email is not null and email <> '';

-- ── RLS: o cliente enxerga e responde as próprias solicitações ──
alter table solicitacoes enable row level security;

drop policy if exists solicitacoes_visiveis on solicitacoes;
create policy solicitacoes_visiveis on solicitacoes for select using (
  public.meu_papel() = 'OPERADOR'
  or caso_id in (
    select c.id from casos c
    where c.cliente_id in (select cliente_id from perfis where id = auth.uid())
  )
);

drop policy if exists documentos_cliente_select on documentos;
create policy documentos_cliente_select on documentos for select using (
  public.meu_papel() = 'OPERADOR'
  or caso_id in (
    select c.id from casos c
    where c.cliente_id in (select cliente_id from perfis where id = auth.uid())
  )
);

-- O backend usa a service_role key (ignora RLS) para gravar; as políticas
-- acima protegem qualquer leitura feita direto pelo navegador do cliente.
