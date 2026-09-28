-- 0025 — dois ajustes no banco de precedentes, descobertos ao ligar o fluxo.
--
-- 1) O índice único era PARCIAL (where numero is not null). O PostgREST não
--    aceita índice parcial em ON CONFLICT, então o upsert falhava. Troca por
--    índice único total: NULLs continuam sendo distintos entre si, que é o
--    comportamento desejado para julgado sem número.
--
-- 2) Coluna `integral`. O banco atual guarda, em boa parte, TRECHOS curtos
--    extraídos dos acórdãos (46 a 144 caracteres), não a ementa completa.
--    Apresentar um trecho desses como "ementa transcrita" seria falso — e a
--    parte contrária confere. Com esta marca, a petição transcreve em bloco
--    de citação apenas o que é ementa de verdade; o resto entra como
--    referência ao julgado, dizendo o que ele decidiu, sem simular
--    transcrição.

drop index if exists idx_precedentes_unico;
create unique index if not exists idx_precedentes_unico
  on public.precedentes(tribunal, numero);

alter table public.precedentes
  add column if not exists integral boolean not null default false;

comment on column public.precedentes.integral is
  'true = ementa completa, pode ser transcrita em bloco de citação; '
  'false = trecho/referência, citado sem simular transcrição integral';
