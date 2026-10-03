-- ════════════════════════════════════════════════════════════════
-- O FINANCEIRO QUE FALTAVA
-- ════════════════════════════════════════════════════════════════
--
-- O QUE EXISTIA
--
-- `fin_lancamentos` tinha seis campos: tipo, categoria, descrição,
-- valor, data e "recorrente". Serve para anotar o que já aconteceu —
-- um caixa de papel, em forma de tabela.
--
-- O QUE NÃO DAVA PARA FAZER
--
-- Nada do que um escritório precisa saber sobre dinheiro:
--
--   · o que vence esta semana (não havia vencimento)
--   · o que já foi pago e o que está em aberto (não havia baixa)
--   · quanto aquele caso rendeu (não havia vínculo com o caso)
--   · quem deve e a quem se deve (não havia a pessoa)
--
-- Sem vencimento não existe "a receber"; sem baixa não existe "em
-- atraso". O escritório não tinha como responder se estava ganhando
-- dinheiro — e essa é a pergunta que um dono faz todo mês.
--
-- A ESCOLHA: AMPLIAR, NÃO SUBSTITUIR
--
-- Daria para criar uma tabela nova e deixar a antiga de lado. Mas os
-- lançamentos já feitos são o histórico real do escritório, e histórico
-- partido em duas tabelas é histórico que ninguém soma direito. As
-- colunas entram nulas; o que já existe continua valendo como estava.

alter table public.fin_lancamentos
  -- QUANDO VENCE, E SE JÁ FOI
  --
  -- As duas colunas que transformam uma anotação em controle. `data`
  -- continua sendo a competência (a que mês pertence); `vencimento` é
  -- quando o dinheiro entra ou sai; `pago_em` é quando aconteceu de
  -- verdade. Lançamento sem `pago_em` e com vencimento no passado é o
  -- que o sistema chama de atraso.
  add column if not exists vencimento      date,
  add column if not exists pago_em         timestamptz,
  add column if not exists forma_pagamento text,

  -- DE ONDE VEIO, PARA ONDE VAI
  add column if not exists caso_id         uuid references public.casos(id) on delete set null,
  add column if not exists cliente_id      uuid references public.clientes(id) on delete set null,
  add column if not exists parceiro_id     uuid references public.parceiros(id) on delete set null,
  add column if not exists pessoa          text,   -- quem paga, ou a quem se paga
  add column if not exists documento       text,   -- nota, recibo, contrato

  -- O PARCELAMENTO, SEM TABELA NOVA
  --
  -- Cada parcela é um lançamento com o seu próprio vencimento, ligado
  -- às irmãs por `grupo_parcelas`. Uma tabela de parcelas separada
  -- obrigaria toda consulta de caixa a juntar duas fontes — e caixa que
  -- depende de junção é caixa que alguém soma errado.
  add column if not exists parcela         integer,
  add column if not exists parcelas_total  integer,
  add column if not exists grupo_parcelas  uuid,

  add column if not exists observacao      text,
  add column if not exists origem          text,   -- MANUAL | PRESTACAO | REPASSE | BALCAO
  add column if not exists criado_por      text,
  add column if not exists atualizado_em   timestamptz;

comment on column public.fin_lancamentos.vencimento is
  'Quando o dinheiro entra ou sai. Sem isto não existe "a receber" nem '
  '"em atraso" — só uma lista do que já passou.';
comment on column public.fin_lancamentos.pago_em is
  'Nulo enquanto estiver em aberto. É a baixa, e é ela que separa o '
  'previsto do realizado.';
comment on column public.fin_lancamentos.origem is
  'MANUAL quando alguém lançou; PRESTACAO e REPASSE quando o sistema '
  'criou a partir do acerto de um caso. Serve para não contar duas '
  'vezes o mesmo dinheiro.';

-- O QUE VENCE, E O QUE VENCEU
--
-- Índice parcial sobre o que está em aberto: é a consulta que a tela
-- faz toda vez que alguém abre o financeiro, e ela não pode varrer o
-- histórico inteiro do escritório para achar as cinco contas da semana.
create index if not exists fin_lanc_em_aberto
  on public.fin_lancamentos (vencimento)
  where pago_em is null;

create index if not exists fin_lanc_caso on public.fin_lancamentos (caso_id)
  where caso_id is not null;
create index if not exists fin_lanc_parceiro on public.fin_lancamentos (parceiro_id)
  where parceiro_id is not null;
create index if not exists fin_lanc_grupo on public.fin_lancamentos (grupo_parcelas)
  where grupo_parcelas is not null;

-- ── O VÍNCULO DA PRESTAÇÃO COM O CASO ───────────────────────────
--
-- `prestacoes_contas` guarda o acerto com o CLIENTE. A parte do
-- parceiro vive em `repasses_parceiro` (migração 0062) e aponta para
-- ela. Falta só o caminho de volta: saber, a partir de um repasse, se
-- ele já virou lançamento no caixa — senão o escritório paga duas vezes
-- ou esquece de pagar.
alter table public.repasses_parceiro
  add column if not exists lancamento_id uuid references public.fin_lancamentos(id) on delete set null;

comment on column public.repasses_parceiro.lancamento_id is
  'O lançamento de saída criado quando o repasse foi provisionado. '
  'Existir aqui é o que impede o mesmo repasse de virar duas contas a '
  'pagar.';
