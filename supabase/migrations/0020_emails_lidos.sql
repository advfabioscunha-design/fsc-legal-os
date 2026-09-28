-- 0020 — memória das mensagens já processadas pela caixa de entrada.
-- Antes o controle era o flag "não lida" do IMAP: se o advogado abrisse o
-- e-mail primeiro, a via assinada era perdida. Agora a rotina varre também
-- o que já foi lido e usa o Message-ID para não repetir.

create table if not exists public.emails_lidos (
  message_id   text primary key,
  caso_id      uuid references public.casos(id) on delete set null,
  resumo       text,
  criado_em    timestamptz not null default now()
);

create index if not exists idx_emails_lidos_caso on public.emails_lidos(caso_id);
create index if not exists idx_emails_lidos_data on public.emails_lidos(criado_em desc);

alter table public.emails_lidos enable row level security;

drop policy if exists emails_lidos_escritorio on public.emails_lidos;
create policy emails_lidos_escritorio on public.emails_lidos
  for all to authenticated
  using (public.meu_papel() = 'OPERADOR')
  with check (public.meu_papel() = 'OPERADOR');
