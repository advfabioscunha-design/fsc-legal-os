-- 0005 — Situação operacional do caso (separa a esteira de Suspensos/Arquivados)
-- ATIVO = aparece na esteira | SUSPENSO = aguardando ação | ARQUIVADO = encerrado sem seguir
alter table casos add column if not exists situacao text not null default 'ATIVO';
alter table casos add column if not exists situacao_motivo text;
create index if not exists idx_casos_situacao on casos (situacao);
