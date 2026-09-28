-- 0024 — banco de precedentes reais e petições da esteira.
--
-- POR QUE UMA TABELA PRÓPRIA DE PRECEDENTES
-- As ementas já existem na plataforma, mas guardadas dentro do jsonb
-- `teses.jurisprudencia` — ótimo para o especialista raciocinar, péssimo
-- para buscar "o que este tribunal já decidiu sobre ESTE tema". Aqui elas
-- ficam achatadas, uma por linha, com tribunal, número e data próprios, e
-- com busca textual.
--
-- É esta tabela que dá a garantia anti-alucinação: o agente de precedentes
-- só pode citar linhas que existem aqui, e cada linha carrega a origem
-- (PDF do acórdão ou API contratada). Ementa que não está no banco não
-- entra na petição — a tag é removida.

create table if not exists public.precedentes (
  id               uuid primary key default gen_random_uuid(),
  tribunal         text not null,              -- TJRO, TJSC, STJ…
  orgao_julgador   text,                       -- câmara/turma
  tipo             text,                       -- Apelação Cível, AgInt…
  numero           text,                       -- nº do processo/acórdão
  relator          text,
  data_julgamento  date,
  ementa           text not null,
  tema             text,                       -- matéria em uma linha
  grupo            text,                       -- BANCARIO, IMOBILIARIO…
  subtipo          text,
  fonte            text not null default 'BANCO_TESES',  -- BANCO_TESES | API | MANUAL
  fonte_ref        text,                       -- id da tese ou id externo
  url              text,
  criado_em        timestamptz not null default now()
);

-- evita a mesma ementa entrando duas vezes pelo mesmo tribunal
create unique index if not exists idx_precedentes_unico
  on public.precedentes(tribunal, numero) where numero is not null;
create index if not exists idx_precedentes_tribunal on public.precedentes(tribunal);
create index if not exists idx_precedentes_grupo on public.precedentes(grupo);
-- busca textual em português sobre tema + ementa
create index if not exists idx_precedentes_busca
  on public.precedentes
  using gin (to_tsvector('portuguese', coalesce(tema,'') || ' ' || ementa));

alter table public.precedentes enable row level security;
drop policy if exists precedentes_escritorio on public.precedentes;
create policy precedentes_escritorio on public.precedentes
  for all to authenticated
  using (public.meu_papel() = 'OPERADOR')
  with check (public.meu_papel() = 'OPERADOR');


-- ── Petições da esteira ─────────────────────────────────────────
-- markdown_base guarda a minuta COM as tags; markdown_final guarda a peça
-- depois dos precedentes injetados. Manter os dois permite rodar de novo
-- quando o banco crescer, sem perder o original.
create table if not exists public.peticoes (
  id               uuid primary key default gen_random_uuid(),
  caso_id          uuid not null references public.casos(id) on delete cascade,
  titulo           text,
  tribunal         text,                       -- onde será protocolada
  markdown_base    text not null,
  markdown_final   text,
  relatorio        jsonb,                      -- o que entrou e o que foi descartado
  origem           text not null default 'COLADA',  -- COLADA | REDIGIDA
  status           text not null default 'RASCUNHO', -- RASCUNHO | COM_PRECEDENTES | FINAL
  criado_em        timestamptz not null default now(),
  atualizado_em    timestamptz not null default now()
);

create index if not exists idx_peticoes_caso
  on public.peticoes(caso_id, criado_em desc);

alter table public.peticoes enable row level security;
drop policy if exists peticoes_escritorio on public.peticoes;
create policy peticoes_escritorio on public.peticoes
  for all to authenticated
  using (public.meu_papel() = 'OPERADOR')
  with check (public.meu_papel() = 'OPERADOR');
