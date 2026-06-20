-- 0010 — Agenda e Agente Controlador (balanceamento de prazos)
create table if not exists membros_equipe (
  id             uuid primary key default gen_random_uuid(),
  nome           text not null,
  especialidades text[] default '{}',     -- tags: BANCARIO, TRIBUTARIO, ...
  lider          boolean not null default false,
  ativo          boolean not null default true,
  google_email   text,                     -- p/ futura sync Google Calendar
  criado_em      timestamptz not null default now()
);

create table if not exists prazos (
  id            uuid primary key default gen_random_uuid(),
  caso_id       uuid references casos(id),
  titulo        text not null,
  descricao     text,
  data          date not null,
  responsavel_id uuid references membros_equipe(id),
  especialidade text,
  status        text not null default 'ABERTO',   -- ABERTO | CONCLUIDO
  origem        text default 'MANUAL',            -- MANUAL | CONTROLADORIA
  criado_em     timestamptz not null default now()
);
create index if not exists idx_prazos_data on prazos (data);
create index if not exists idx_prazos_resp on prazos (responsavel_id);
