-- 0006 — Processo aguardando complemento do cliente (sai da produção até retorno)
alter table casos add column if not exists aguardando_cliente boolean not null default false;
alter table casos add column if not exists aguardando_desc text;
