-- 0009 — Módulo Financeiro: lançamentos (entrada/saída) e folha de pagamento
create table if not exists fin_lancamentos (
  id         uuid primary key default gen_random_uuid(),
  tipo       text not null,                 -- ENTRADA | SAIDA
  categoria  text,
  descricao  text,
  valor      numeric(14,2) not null default 0,
  data       date not null default current_date,
  recorrente boolean not null default false, -- custo fixo mensal (entra na projeção anual)
  criado_em  timestamptz not null default now()
);
create index if not exists idx_fin_lanc_data on fin_lancamentos (data desc);

create table if not exists fin_folha (
  id        uuid primary key default gen_random_uuid(),
  nome      text not null,
  cargo     text,
  salario   numeric(14,2) not null default 0,
  ativo     boolean not null default true,
  criado_em timestamptz not null default now()
);
