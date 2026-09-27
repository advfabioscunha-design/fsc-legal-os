-- ================================================================
-- 0015 — Qualificação completa do cliente + documentos para assinatura
--
-- Os modelos do escritório (contrato de honorários, procuração e
-- declaração de hipossuficiência) exigem a qualificação civil completa.
-- Esta migração cria esses campos e a tabela que controla o ciclo
-- GERADO → EM_REVISÃO → APROVADO → ENVIADO → ASSINADO.
-- ================================================================

-- ── 1. QUALIFICAÇÃO DO CLIENTE ──────────────────────────────────
alter table clientes add column if not exists nacionalidade  text default 'brasileiro(a)';
alter table clientes add column if not exists estado_civil   text;
alter table clientes add column if not exists profissao      text;
alter table clientes add column if not exists rg             text;
alter table clientes add column if not exists endereco_rua   text;
alter table clientes add column if not exists endereco_numero text;
alter table clientes add column if not exists endereco_complemento text;
alter table clientes add column if not exists endereco_bairro text;
alter table clientes add column if not exists endereco_cidade text;
alter table clientes add column if not exists endereco_uf    text;
alter table clientes add column if not exists endereco_cep   text;

comment on column clientes.endereco_cidade is
  'Usada como LOCAL de assinatura dos documentos e como FORO do contrato';

-- ── 2. DOCUMENTOS GERADOS PARA ASSINATURA ───────────────────────
create table if not exists documentos_assinatura (
  id            uuid primary key default gen_random_uuid(),
  caso_id       uuid not null references casos(id) on delete cascade,
  tipo          text not null,      -- CONTRATO | PROCURACAO | HIPOSSUFICIENCIA | OUTRO
  titulo        text not null,
  status        text not null default 'EM_REVISAO',
                -- EM_REVISAO | APROVADO | ENVIADO | ASSINADO | CANCELADO
  -- conteúdo gerado pelo agente (o que ele mudou no modelo)
  qualificacao  text,               -- parágrafo de qualificação do cliente
  objeto        jsonb,              -- objeto/cláusulas redigidas para o caso
  local_data    text,               -- "Porto Velho/RO, 27 de setembro de 2026"
  foro          text,               -- comarca eleita no contrato
  tipo_acao     text,               -- usado na procuração
  observacoes   text,               -- ajustes do advogado

  storage_path  text,               -- .docx gerado, no bucket de documentos
  -- assinatura digital
  zapsign_token text,
  link_assinatura text,
  enviado_em    timestamptz,
  assinado_em   timestamptz,
  assinado_url  text,               -- PDF assinado devolvido pelo assinador

  gerado_por    text default 'AGENTE',
  aprovado_por  text,
  aprovado_em   timestamptz,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index if not exists idx_docassin_caso on documentos_assinatura(caso_id, criado_em desc);
create index if not exists idx_docassin_status on documentos_assinatura(status);

-- ── 3. RLS: o cliente vê e assina os próprios documentos ────────
alter table documentos_assinatura enable row level security;

drop policy if exists docassin_visiveis on documentos_assinatura;
create policy docassin_visiveis on documentos_assinatura for select using (
  public.meu_papel() = 'OPERADOR'
  or (
    status in ('ENVIADO', 'ASSINADO')      -- rascunho em revisão não aparece
    and caso_id in (
      select c.id from casos c
      where c.cliente_id in (select cliente_id from perfis where id = auth.uid())
    )
  )
);

-- O backend grava com a service_role key (ignora RLS); a política acima
-- garante que o cliente nunca enxergue um documento ainda em revisão.
