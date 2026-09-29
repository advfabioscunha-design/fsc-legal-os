-- 0034 — pendências anotadas por quem cuida do caso.
--
-- Prazo nasce de intimação. Tarefa nasce do plano do agente. Pendência
-- nasce da cabeça de alguém: "ligar para a perita", "juntar o
-- comprovante que o cliente mandou no WhatsApp", "conferir se o alvará
-- saiu". Não vem de publicação nenhuma e, sem um lugar, fica no papel
-- da mesa.
--
-- A tabela se chama `anotacoes` e não `pendencias` porque já existe
-- `agentes/pendencias.py`, que é a régua de cobrança do cliente que não
-- mandou documento. Dois nomes iguais em domínios diferentes é
-- confusão garantida daqui a seis meses. Na tela, para o escritório,
-- continua sendo "Pendências".

create table if not exists public.anotacoes (
  id              uuid primary key default gen_random_uuid(),
  texto           text not null,
  data_resolver   date,                    -- sem data = lembrete, não entra no plano
  prioridade      text not null default 'MEDIA',
  caso_id         uuid references public.casos(id) on delete cascade,
  cliente_id      uuid references public.clientes(id) on delete set null,
  numero_processo text,
  responsavel_id  uuid references public.membros_equipe(id) on delete set null,
  status          text not null default 'ABERTA',   -- ABERTA|RESOLVIDA|CANCELADA
  resultado       text,                    -- o que foi feito, de fato
  adiamentos      integer not null default 0,
  historico       jsonb default '[]'::jsonb,
  criado_por      text,
  resolvido_em    timestamptz,
  criado_em       timestamptz not null default now()
);

create index if not exists idx_anotacoes_status on public.anotacoes(status, data_resolver);
create index if not exists idx_anotacoes_caso on public.anotacoes(caso_id);

comment on column public.anotacoes.resultado is
  'O que foi feito, não só que foi feito. "Liguei para a perita" e '
  '"perita confirmou a data para o dia 12" são coisas diferentes para '
  'quem abrir o caso daqui a três meses.';
