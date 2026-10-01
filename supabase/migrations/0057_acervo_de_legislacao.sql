-- O acervo de legislação conferida.
--
-- O especialista não cita artigo de cabeça. Ele consulta aqui, e o que
-- não estiver aqui ele marca como "confirmar o dispositivo" para o
-- advogado conferir antes de assinar.
--
-- Cada linha é um artigo, com a fonte de onde o texto veio e o nome de
-- quem conferiu. Sem conferência não entra: uma lei com acento quebrado
-- ou artigo faltando é pior do que acervo vazio, porque o agente passa a
-- confiar em texto errado.

create table if not exists legislacao (
  id            uuid primary key default gen_random_uuid(),
  lei           text not null,              -- 'Lei 8.245/1991'
  apelido       text,                       -- 'Lei do Inquilinato', 'CDC', 'CPC'
  artigo        text not null,              -- '46', '46-A' (só o número, sem "art.")
  texto         text not null,              -- o caput, incisos e parágrafos
  fonte         text,                       -- de onde veio (Planalto, DOU, etc.)
  conferido_por text,                       -- quem leu e bateu com o oficial
  conferido_em  timestamptz,
  criado_em     timestamptz not null default now(),
  unique (lei, artigo)
);

create index if not exists legislacao_lei_idx     on legislacao (lei);
create index if not exists legislacao_apelido_idx on legislacao (apelido);

-- busca por palavra no texto, para quando não se sabe o número do artigo
create index if not exists legislacao_texto_idx
  on legislacao using gin (to_tsvector('portuguese', texto));

alter table legislacao enable row level security;

-- leitura só pela API (service role); ninguém escreve pelo navegador
drop policy if exists legislacao_servico on legislacao;
create policy legislacao_servico on legislacao
  for all to service_role using (true) with check (true);
