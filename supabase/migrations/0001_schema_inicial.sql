-- ================================================================
-- FSC LEGAL OS v4.0 — SCHEMA INICIAL (Supabase/PostgreSQL)
-- Teses por GRUPO + Agente Especialista + Jornada do Cliente
-- ================================================================

-- ── ENUMs ────────────────────────────────────────────────────────
create type grupo_tese as enum (
  'BANCARIO', 'IMOBILIARIO', 'TRABALHISTA',
  'PREVIDENCIARIO', 'TRIBUTARIO', 'CONSUMIDOR', 'OUTROS'
);

-- Máquina de estados da JORNADA conduzida pelo Agente Especialista
create type estado_jornada as enum (
  'LEAD',               -- chegou via portal/whatsapp
  'QUALIFICACAO',       -- agente identifica grupo/tese e qualifica
  'PROPOSTA',           -- agente demonstra viabilidade e envia proposta
  'CONTRATO',           -- contrato enviado via ZapSign, aguardando assinatura
  'PAGAMENTO',          -- cobranca Asaas enviada, aguardando webhook
  'COLETA_DOCS',        -- coleta de documentos vitais da tese
  'COLETA_PROVAS',      -- depoimentos e provas complementares
  'ANALISE',            -- agente analista gera laudo de viabilidade
  'PETICAO',            -- redator gera peticao
  'REVISAO',            -- advogado revisa no CRM
  'APROVADO',           -- clicou APROVAR E PROTOCOLAR
  'PROTOCOLO_RPA',      -- na fila do robo
  'PROTOCOLADO',        -- numero de processo obtido
  'ESCALADO_HUMANO',    -- agente detectou dificuldade -> humano assume
  'AGENDADO',           -- cliente agendou com advogado especialista
  'INVIAVEL', 'CANCELADO', 'CONCLUIDO'
);

-- ── TESES (o cérebro mutável, agora agrupado) ───────────────────
create table teses (
  id              text primary key,                -- ex: BANCARIO_001
  grupo           grupo_tese not null,             -- AGRUPAMENTO: define o especialista
  subtipo         text,
  titulo          text not null,
  status          text not null default 'ATIVA',   -- ATIVA | SUPERADA
  tribunal_origem text,
  ratio_decidendi text not null,
  documentos_vitais jsonb not null default '[]',
  argumentos_chave  jsonb not null default '[]',
  diretriz_redacao  text,
  jurisprudencia    jsonb not null default '[]',
  calculo_base      jsonb,
  honorarios        jsonb,                         -- {modelo: MASSA|ALTA_COMPLEXIDADE, percentual: 0.5}
  overruled         boolean not null default false,
  tese_substituta   text references teses(id),
  motivo_overruling text,
  fonte_pdf         text,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now()
);
create index idx_teses_grupo on teses(grupo) where not overruled;

-- ── AGENTES ESPECIALISTAS (1 por grupo de teses) ────────────────
-- O system prompt é REGENERADO automaticamente quando as teses do
-- grupo mudam: o especialista sempre opera com o entendimento atual.
create table agentes_especialistas (
  grupo            grupo_tese primary key,
  nome             text not null,                  -- ex: "Dr. Agente Bancário"
  system_prompt    text not null,
  advogado_humano  text not null default 'Fábio Silva Cunha',  -- responsável p/ escalonamento
  whatsapp_humano  text,
  link_agenda      text,                           -- Cal.com/Calendly do advogado especialista
  ativo            boolean not null default true,
  atualizado_em    timestamptz not null default now()
);

-- ── CLIENTES ─────────────────────────────────────────────────────
create table clientes (
  id           uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique,                        -- Supabase Auth (portal)
  nome         text not null,
  cpf_cnpj     text,
  email        text,
  whatsapp     text,
  origem       text default 'PORTAL',              -- PORTAL | WHATSAPP | INDICACAO
  criado_em    timestamptz not null default now()
);

-- ── CASOS (a esteira; cada caso pertence a um especialista) ─────
create table casos (
  id               uuid primary key default gen_random_uuid(),
  cliente_id       uuid not null references clientes(id),
  grupo            grupo_tese,                     -- definido na qualificação
  tese_id          text references teses(id),
  estado           estado_jornada not null default 'LEAD',
  relato_inicial   text,
  score_viabilidade int,
  laudo            jsonb,                          -- laudo completo do analista
  valor_causa      numeric(14,2),
  honorarios_modelo text,                          -- MASSA | ALTA_COMPLEXIDADE
  honorarios_valor  text,
  proposta_enviada_em   timestamptz,
  contrato_zapsign_id   text,
  contrato_assinado_em  timestamptz,
  cobranca_asaas_id     text,
  pagamento_confirmado_em timestamptz,
  peticao_storage_path  text,                      -- PDF no Supabase Storage
  tribunal         text,
  numero_processo  text,
  escalado_motivo  text,
  criado_em        timestamptz not null default now(),
  atualizado_em    timestamptz not null default now()
);
create index idx_casos_estado on casos(estado);
create index idx_casos_grupo  on casos(grupo);

-- ── MENSAGENS (conversa do especialista com o cliente) ──────────
create table mensagens (
  id         bigint generated always as identity primary key,
  caso_id    uuid not null references casos(id),
  canal      text not null default 'PORTAL',       -- PORTAL | WHATSAPP
  autor      text not null,                        -- CLIENTE | AGENTE | HUMANO
  conteudo   text not null,
  criado_em  timestamptz not null default now()
);
create index idx_mensagens_caso on mensagens(caso_id, criado_em);

-- ── DOCUMENTOS (coleta guiada pelos documentos_vitais da tese) ──
create table documentos (
  id           uuid primary key default gen_random_uuid(),
  caso_id      uuid not null references casos(id),
  tipo         text not null,                      -- ex: contrato_bancario_original
  storage_path text not null,                      -- bucket privado 'documentos'
  status       text not null default 'RECEBIDO',   -- SOLICITADO | RECEBIDO | VALIDADO | REJEITADO
  observacao   text,
  criado_em    timestamptz not null default now()
);

-- ── ESCALAÇÕES (agente -> humano) ────────────────────────────────
create table escalacoes (
  id          uuid primary key default gen_random_uuid(),
  caso_id     uuid not null references casos(id),
  motivo      text not null,        -- DIFICULDADE | DEMORA_DOCS | PEDIDO_CLIENTE | JURIDICO_COMPLEXO
  detalhe     text,
  resolvida   boolean not null default false,
  agendamento timestamptz,          -- se o cliente agendou com o advogado
  criado_em   timestamptz not null default now()
);

-- ── PROTOCOLOS (fila e auditoria do RPA) ─────────────────────────
create table protocolos (
  id          uuid primary key default gen_random_uuid(),
  caso_id     uuid not null references casos(id),
  tribunal    text not null,                       -- EPROC_TJSC | PJE_TJRO | PJE_TRT14
  status      text not null default 'NA_FILA',    -- NA_FILA | EXECUTANDO | SUCESSO | FALHA
  tentativas  int not null default 0,
  log         jsonb not null default '[]',
  numero_processo text,
  criado_em   timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

-- ── EVENTOS (trilha de auditoria de TUDO) ────────────────────────
create table eventos (
  id        bigint generated always as identity primary key,
  caso_id   uuid references casos(id),
  tipo      text not null,    -- ESTADO_MUDOU | WEBHOOK_ASAAS | WEBHOOK_ZAPSIGN | ESCALACAO | ...
  payload   jsonb,
  criado_em timestamptz not null default now()
);

-- ── RLS (LGPD: cliente só enxerga o que é dele) ──────────────────
alter table clientes   enable row level security;
alter table casos      enable row level security;
alter table mensagens  enable row level security;
alter table documentos enable row level security;

create policy cliente_ve_proprio_cadastro on clientes
  for select using (auth.uid() = auth_user_id);
create policy cliente_ve_proprios_casos on casos
  for select using (cliente_id in (select id from clientes where auth_user_id = auth.uid()));
create policy cliente_ve_proprias_mensagens on mensagens
  for select using (caso_id in (select c.id from casos c
    join clientes cl on cl.id = c.cliente_id where cl.auth_user_id = auth.uid()));
create policy cliente_ve_proprios_documentos on documentos
  for select using (caso_id in (select c.id from casos c
    join clientes cl on cl.id = c.cliente_id where cl.auth_user_id = auth.uid()));
-- Backend usa service_role key (bypassa RLS). CRM usa role 'advogado' via JWT claim.
