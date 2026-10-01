-- 0056 — a peça processual ganha mesa de correção, como o contrato.
--
-- A peça era escrita uma vez e nunca mais editada por dentro do
-- sistema. `markdown_base` entrava no insert e ficava; `markdown_final`
-- só era escrito pela injeção de precedentes. Quem precisasse corrigir
-- uma vírgula copiava para o Word, corrigia lá e protocolava de lá, e
-- a partir daí o sistema guardava uma versão e o processo recebia
-- outra. Na hora de explicar o que foi protocolado, a resposta estava
-- no computador de alguém.
--
-- AS TRÊS COLUNAS
--
--   markdown_anterior  a versão de antes da última gravação. O mesmo
--                      que `pedidos_contrato.minuta_anterior` faz pelo
--                      contrato: autossalvamento sem histórico é uma
--                      forma elegante de perder trabalho, porque basta
--                      uma seleção acidental seguida de uma tecla.
--
--   editada_em         quando alguém mexeu à mão pela última vez. É o
--                      que distingue uma peça que passou pela leitura
--                      do advogado de uma que saiu do redator e nunca
--                      foi lida.
--
--   editada_por        quem mexeu. Peça protocolada é ato com nome, e
--                      a trilha precisa dizer de quem.
--
-- O QUE ESTA MIGRAÇÃO NÃO FAZ, DE PROPÓSITO
--
-- Não cria máquina de fases na peça. A fase é do caso, em
-- `casos.estado`, e já existe o par PETICAO ↔ REVISAO no orquestrador,
-- hoje sem uso. Criar um segundo relógio de fases na peça seria ter
-- dois lugares dizendo em que pé está a mesma coisa, e um dia eles
-- discordam.

alter table public.peticoes
  add column if not exists markdown_anterior text,
  add column if not exists editada_em        timestamptz,
  add column if not exists editada_por       text;

comment on column public.peticoes.markdown_anterior is
  'A versão de antes da última gravação. Existe para que o '
  'autossalvamento não possa apagar trabalho sem volta.';

comment on column public.peticoes.editada_em is
  'Quando a peça foi corrigida à mão pela última vez. Distingue a que '
  'passou pela leitura do advogado da que saiu do redator e nunca foi '
  'lida.';

comment on column public.peticoes.editada_por is
  'Quem corrigiu. Peça protocolada é ato com nome.';

-- A peça aberta na mesa é a mais recente do caso, e é essa consulta
-- que a tela faz a cada abertura.
create index if not exists idx_peticoes_editada
  on public.peticoes(caso_id, editada_em desc nulls last);
