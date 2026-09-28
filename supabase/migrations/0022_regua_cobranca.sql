-- 0022 — "Aguardando documentos": dois relógios e a régua de cobrança.
--
-- Quando o escritório pede um documento, o caso deixa de depender de nós e
-- passa a depender do cliente. Até aqui isso era só um sinalizador
-- (aguardando_cliente) e o card continuava na esteira de produção, poluindo
-- a visão de quem redige. Agora vira etapa de verdade:
--
--   * o RELÓGIO DO ESCRITÓRIO (SLA) pausa, porque o atraso não é nosso;
--   * o RELÓGIO DO CLIENTE começa, e é ele que move a régua de cobrança;
--   * o card sai da produção e volta sozinho quando o documento chega.
--
-- sla_pausado_em / sla_parado_segundos guardam o tempo em que o caso ficou
-- parado por causa do cliente, para o SLA medir só o que é responsabilidade
-- do escritório.

alter table public.casos
  add column if not exists estado_anterior        text,
  add column if not exists aguardando_desde       timestamptz,
  add column if not exists sla_pausado_em         timestamptz,
  add column if not exists sla_parado_segundos    bigint not null default 0,
  add column if not exists cobranca_etapa         smallint not null default 0,
  add column if not exists cobranca_ultima_em     timestamptz,
  add column if not exists parado_sinalizado_em   timestamptz,
  -- prazo real do caso (prescrição, decadência, prazo processual). Só quando
  -- existe é que a cobrança pode falar em perda de direito — do contrário a
  -- mensagem seria inverídica com o cliente e expõe o escritório.
  add column if not exists prazo_fatal            date,
  add column if not exists prazo_descricao        text;

create index if not exists idx_casos_aguardando
  on public.casos(aguardando_desde) where aguardando_desde is not null;
create index if not exists idx_casos_prazo on public.casos(prazo_fatal);

-- Histórico da régua: o que foi mandado, quando e por qual canal. Sem isso
-- não há como provar depois que o cliente foi avisado.
create table if not exists public.cobrancas (
  id            uuid primary key default gen_random_uuid(),
  caso_id       uuid not null references public.casos(id) on delete cascade,
  solicitacao_id uuid,
  etapa         smallint not null,          -- 3, 7 ou 10 (dias)
  motivo        text,                       -- o documento pedido
  com_prazo     boolean not null default false,
  canais        text,                       -- PAINEL, EMAIL, WHATSAPP
  enviado_em    timestamptz not null default now()
);

create index if not exists idx_cobrancas_caso
  on public.cobrancas(caso_id, enviado_em desc);

alter table public.cobrancas enable row level security;

drop policy if exists cobrancas_escritorio on public.cobrancas;
create policy cobrancas_escritorio on public.cobrancas
  for all to authenticated
  using (public.meu_papel() = 'OPERADOR')
  with check (public.meu_papel() = 'OPERADOR');
