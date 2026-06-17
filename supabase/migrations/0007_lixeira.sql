-- 0007 — Lixeira: backup completo antes de excluir (retenção de 6 meses)
create table if not exists lixeira (
  id          uuid primary key default gen_random_uuid(),
  caso_id     uuid,
  rotulo      text,
  dados       jsonb not null,                 -- snapshot do caso + mensagens + documentos + eventos
  excluido_em timestamptz not null default now(),
  expira_em   timestamptz not null default (now() + interval '6 months')
);
create index if not exists idx_lixeira_excluido_em on lixeira (excluido_em desc);
