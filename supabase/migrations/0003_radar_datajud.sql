-- ================================================================
-- v4.2 — Radar Jurimétrico automático (DataJud CNJ)
-- Monitoramento semanal de processos julgados nos tribunais de
-- atuação (TJRO, TRT14...), por GRUPO de tese. O DataJud entrega
-- METADADOS (não a íntegra do acórdão): número, classe, assuntos,
-- órgão julgador, movimentos e datas. Usamos isso como INTELIGÊNCIA
-- ESTRATÉGICA (jurimetria) que reforça os Agentes Especialistas e
-- aponta quais processos buscar a íntegra para virar tese.
-- ================================================================

-- Snapshot semanal por grupo: o que o radar encontrou e a leitura
-- estratégica gerada pela IA a partir dos metadados agregados.
create table if not exists radar_jurimetrico (
  id              uuid primary key default gen_random_uuid(),
  grupo           grupo_tese not null,
  semana_ref      date not null,                 -- segunda-feira da semana analisada
  tribunais       jsonb not null default '[]',   -- aliases consultados (tjro, trt14...)
  total_julgados  int  not null default 0,
  procedentes     int  not null default 0,
  improcedentes   int  not null default 0,
  taxa_exito      numeric,                        -- procedentes / julgados
  orgaos_destaque jsonb not null default '[]',   -- [{orgao, qtd}]
  assuntos_alta   jsonb not null default '[]',   -- [{assunto, qtd}]
  leitura_ia      text,                           -- síntese estratégica (Claude)
  alvos_integra   jsonb not null default '[]',   -- processos p/ buscar a íntegra → vira tese
  criado_em       timestamptz not null default now(),
  unique (grupo, semana_ref)
);
create index if not exists idx_radar_grupo on radar_jurimetrico(grupo, semana_ref desc);

-- Deduplicação: processos já vistos pelo radar (não recontar/realertar).
create table if not exists datajud_monitorados (
  numero_processo text primary key,
  grupo           grupo_tese not null,
  tribunal        text not null,
  orgao_julgador  text,
  classe          text,
  assuntos        jsonb not null default '[]',
  resultado       text,                           -- PROCEDENTE | IMPROCEDENTE | OUTRO
  data_julgamento date,
  virou_tese      boolean not null default false,
  visto_em        timestamptz not null default now()
);
create index if not exists idx_djmon_grupo on datajud_monitorados(grupo, visto_em desc);

alter table radar_jurimetrico   enable row level security;
alter table datajud_monitorados enable row level security;
