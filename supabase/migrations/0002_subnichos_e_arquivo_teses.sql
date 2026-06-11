-- ================================================================
-- v4.1 — Subnichos nos casos + arquivo de teses excluídas
-- (já aplicado em produção em 10/06/2026; mantido para staging/replays)
-- ================================================================

-- O CRM filtra a esteira por subnicho (espelha a organização de pastas:
-- FILA_DE_BANCO, RMC_RCC, FRAUDES_BANCARIAS, VENDA_CASADA_SEGURO_PRESTAMISTA,
-- DEFESA_BUSCA_APREENSAO_VEICULO, ...)
alter table casos add column if not exists subtipo text;
create index if not exists idx_casos_subtipo on casos(subtipo);

-- Diretriz do escritório: tese superada é EXCLUÍDA do banco ativo e
-- arquivada aqui (recuperável; o banco vivo só carrega o entendimento atual).
create table if not exists teses_arquivadas (
  id text primary key,
  tese jsonb not null,
  motivo_exclusao text,
  substituida_por text,
  excluida_em timestamptz not null default now()
);
alter table teses_arquivadas enable row level security;
