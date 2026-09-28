-- 0028 — as quatro fases do caso e a controladoria de prazos.
--
-- O CAMINHO DO CASO, AGORA COM FRONTEIRAS CLARAS
--   CONTRATOS   quem chegou → proposta → assinatura → pagamento
--   PRODUÇÃO    documentos → análise → peça → revisão → protocolo
--   JUDICIAL    protocolado → tramitação → trânsito em julgado
--   RECEBIMENTO cumprimento, alvará, prestação de contas
--
-- Cada fronteira é um fato verificável, não uma opinião: o protocolo
-- empurra da produção para o judicial; a certidão de trânsito em julgado
-- empurra do judicial para o recebimento. Sem isso, "em andamento" virava
-- um depósito onde tudo cabia e nada era cobrado.

alter type estado_jornada add value if not exists 'JUDICIAL';
alter type estado_jornada add value if not exists 'TRANSITO_JULGADO';
alter type estado_jornada add value if not exists 'RECEBIMENTO';


-- ── Prazos: o que a controladoria precisa saber ─────────────────
-- prazo_fatal é a data real do processo; `data` é o dia em que o
-- escritório trabalha a peça — dois dias antes, por decisão do escritório.
-- Guardar os dois evita o erro clássico de confundir a folga com o prazo.
alter table public.prazos
  add column if not exists intimacao_id          uuid,
  add column if not exists prazo_fatal           date,
  add column if not exists tipo                  text,
  add column if not exists depende_do_cliente    boolean not null default false,
  add column if not exists convite_escritorio_em timestamptz,
  add column if not exists convite_cliente_em    timestamptz,
  add column if not exists atualizado_em         timestamptz not null default now();

comment on column public.prazos.prazo_fatal is
  'Data real do prazo no processo. A coluna `data` é o dia de trabalho, '
  'antecipado para dar folga antes do vencimento.';
comment on column public.prazos.depende_do_cliente is
  'true = audiência, perícia ou providência do cliente; só esses vão para '
  'a agenda dele. Prazo de peça é obrigação do advogado.';

-- Uma intimação gera um prazo, e só um.
--
-- O índice é TOTAL, sem cláusula WHERE, e isso não é detalhe: o
-- PostgREST recusa ON CONFLICT quando o índice é parcial, e o upsert do
-- prazo falhava calado no meio da importação — o processo entrava com
-- metade das publicações e nenhum prazo. Em Postgres, NULL não conflita
-- com NULL, então prazos manuais (sem intimação) continuam convivendo.
create unique index if not exists idx_prazos_intimacao
  on public.prazos(intimacao_id);
create index if not exists idx_prazos_fatal on public.prazos(prazo_fatal);


-- ── Casos: as datas que marcam cada virada de fase ──────────────
-- Guardadas como datas, e não como um campo "fase" solto, para que a
-- pergunta "há quanto tempo este caso está parado no judicial?" tenha
-- resposta sem garimpar a trilha de eventos.
alter table public.casos
  add column if not exists protocolado_em   timestamptz,
  add column if not exists judicial_em      timestamptz,
  add column if not exists transito_em      timestamptz,
  add column if not exists recebimento_em   timestamptz,
  add column if not exists orgao_julgador   text,
  add column if not exists classe_judicial  text,
  add column if not exists instancia        text,
  add column if not exists importado_de     text;   -- COMUNICA_CNJ | DATAJUD | MANUAL

create index if not exists idx_casos_numero_proc
  on public.casos(numero_processo) where numero_processo is not null;


-- ── Intimações: de onde veio e que prazo nasceu dela ────────────
alter table public.intimacoes
  add column if not exists origem          text default 'ESCAVADOR',
  add column if not exists tipo            text,     -- Intimação, Sentença, Pauta…
  add column if not exists orgao           text,
  add column if not exists link            text,
  add column if not exists prazo_dias      integer,  -- dias do prazo, quando conhecido
  add column if not exists prazo_estimado  boolean not null default false;

comment on column public.intimacoes.prazo_estimado is
  'true = o prazo foi calculado pelo padrão do tipo de ato, não lido do '
  'texto. A controladoria mostra esses prazos marcados para conferência: '
  'quem responde pelo prazo é o advogado, não o cálculo automático.';
