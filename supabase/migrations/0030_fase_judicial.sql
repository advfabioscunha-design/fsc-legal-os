-- 0030 — em que ponto do processo o caso está, dentro da fase judicial.
--
-- A tela Judicializado passa a ter doze colunas, seguindo o caminho
-- real: 1º grau, prazo em 1º grau, audiência, perícia, concluso,
-- julgado em 1º grau, 2º grau, prazo em 2º grau, acórdão, STJ, STF e
-- trânsito em julgado.
--
-- Isso NÃO vira estado do caso (`estado`/estado_jornada). São coisas
-- diferentes: `estado` diz em qual das quatro fases do escritório o
-- caso está — contratos, triagem, judicializado, execução — e é o que
-- a máquina de estados protege. `fase_judicial` diz onde o processo
-- está andando dentro do juízo, muda toda semana e é leitura de
-- publicação, que erra. Misturar os dois faria o classificador de
-- texto mexer na máquina de estados do escritório.

alter table public.casos
  add column if not exists fase_judicial        text,
  add column if not exists fase_judicial_base   text,
  add column if not exists fase_judicial_em     timestamptz,
  add column if not exists fase_judicial_motivo text,
  add column if not exists fase_judicial_fonte  text default 'AUTO';

comment on column public.casos.fase_judicial is
  'Coluna da tela Judicializado. Quando há prazo em aberto vale '
  'PRAZO_1G/PRAZO_2G, e fase_judicial_base guarda de onde o caso veio, '
  'para ele voltar sozinho quando o prazo for cumprido.';

comment on column public.casos.fase_judicial_fonte is
  'AUTO = lido das publicações. MANUAL = alguém corrigiu à mão, e a '
  'leitura automática para de mexer: quem olhou o processo sabe mais '
  'que a leitura de texto.';

comment on column public.casos.fase_judicial_motivo is
  'Por que o caso está nesta coluna, em uma frase. Fica à vista no '
  'card — classificação automática sem justificativa não se confere.';

create index if not exists idx_casos_fase_judicial
  on public.casos(fase_judicial) where fase_judicial is not null;
