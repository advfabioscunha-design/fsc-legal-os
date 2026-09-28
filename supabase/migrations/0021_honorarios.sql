-- 0021 — honorários do caso em campos próprios.
--
-- Até aqui os honorários eram um texto livre no caso e números fixos dentro
-- do modelo de contrato ("30%", "10 salários mínimos"). Isso obrigava a
-- editar o documento à mão a cada renegociação, e o que ficou combinado na
-- conversa com o cliente não conversava com o que ia para o contrato.
--
-- Agora o combinado vira dado: cada forma de cobrança tem o seu campo, a
-- cláusula de pagamento é montada a partir deles, e toda alteração fica
-- registrada em honorarios_historico — quem mudou, quando, de quanto para
-- quanto e com base em quê.

alter table public.casos
  add column if not exists hon_percentual        numeric(5,2),   -- % sobre o proveito econômico
  add column if not exists hon_salarios_minimos  numeric(6,2),   -- nº de salários mínimos
  add column if not exists hon_valor_fixo        numeric(12,2),  -- valor fixo em reais
  add column if not exists hon_entrada           numeric(12,2),  -- entrada paga na assinatura
  add column if not exists hon_parcelas          integer,        -- nº de parcelas do valor fixo
  add column if not exists hon_parcela_valor     numeric(12,2),  -- valor de cada parcela
  add column if not exists hon_vencimento        text,           -- ex.: "todo dia 10"
  add column if not exists hon_forma_pagamento   text,           -- PIX, boleto, dedução do alvará…
  add column if not exists hon_observacao        text,           -- condição combinada fora do padrão
  add column if not exists hon_atualizado_em     timestamptz,
  add column if not exists hon_atualizado_por    text,
  add column if not exists hon_origem            text;           -- CONVERSA | ESCRITORIO

-- Documento gerado antes da última mudança de valores fica marcado, para
-- ninguém mandar ao cliente um contrato com honorários vencidos.
alter table public.documentos_assinatura
  add column if not exists honorarios_versao timestamptz;

create table if not exists public.honorarios_historico (
  id            uuid primary key default gen_random_uuid(),
  caso_id       uuid not null references public.casos(id) on delete cascade,
  anterior      jsonb,
  novo          jsonb not null,
  origem        text,          -- CONVERSA | ESCRITORIO
  justificativa text,          -- trecho da conversa que embasou a mudança
  autor         text,
  criado_em     timestamptz not null default now()
);

create index if not exists idx_hon_hist_caso
  on public.honorarios_historico(caso_id, criado_em desc);

alter table public.honorarios_historico enable row level security;

drop policy if exists hon_hist_escritorio on public.honorarios_historico;
create policy hon_hist_escritorio on public.honorarios_historico
  for all to authenticated
  using (public.meu_papel() = 'OPERADOR')
  with check (public.meu_papel() = 'OPERADOR');
