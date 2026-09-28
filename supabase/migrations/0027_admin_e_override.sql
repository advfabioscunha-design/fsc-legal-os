-- 0027 — papel de ADMIN, permissões finas e auditoria de override.
--
-- POR QUE ISSO VEM ANTES DO OVERRIDE
-- Até aqui `papel_usuario` só tinha CLIENTE e OPERADOR, e quem entra com o
-- código da equipe vira OPERADOR. Ou seja: o assessor e o advogado titular
-- têm hoje exatamente o mesmo poder. Um "override só para admin" sobre essa
-- base seria decorativo — não haveria a quem negar.
--
-- Então o papel ADMIN é criado primeiro, e a promoção é MANUAL: ninguém
-- vira admin por código de equipe, formulário ou convite. Só por comando
-- direto no banco, feito por quem tem a chave do projeto.
--
-- A coluna `permissoes` existe para o caso de o escritório querer dar o
-- override a alguém específico sem transformá-lo em admin de tudo — um
-- sócio, por exemplo. A verificação aceita as duas formas.

alter type papel_usuario add value if not exists 'ADMIN';

alter table public.perfis
  add column if not exists permissoes jsonb not null default '[]'::jsonb,
  add column if not exists nome text;

comment on column public.perfis.permissoes is
  'Permissões avulsas, ex.: ["override_peticao"]. Complementam o papel, '
  'não o substituem.';

-- helper: o usuário logado pode forçar peticionamento?
create or replace function public.pode_forcar_peticao()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce(
    (select papel = 'ADMIN'
         or permissoes ? 'override_peticao'
       from public.perfis where id = auth.uid()),
    false)
$$;


-- ── Auditoria do override ───────────────────────────────────────
-- Um override é a decisão de peticionar apesar de a trava ter apontado
-- problema. Se um dia se discutir aquela peça, a pergunta será "quem
-- mandou protocolar assim, e por quê". A resposta precisa estar gravada,
-- com a justificativa escrita de quem decidiu — não só "forçado pelo
-- usuário X".
create table if not exists public.overrides_peticionamento (
  id                uuid primary key default gen_random_uuid(),
  caso_id           uuid not null references public.casos(id) on delete cascade,
  usuario_id        uuid,
  usuario_email     text,
  usuario_papel     text,
  tipo_peticao      text not null,
  motivo_da_trava   text not null,      -- o que a validação tinha apontado
  justificativa     text,               -- por que o admin decidiu seguir
  regra             text,               -- A (inicial) ou B (demais peças)
  criado_em         timestamptz not null default now()
);

create index if not exists idx_overrides_caso
  on public.overrides_peticionamento(caso_id, criado_em desc);
create index if not exists idx_overrides_usuario
  on public.overrides_peticionamento(usuario_id, criado_em desc);

alter table public.overrides_peticionamento enable row level security;

-- todo o escritório enxerga os overrides: auditoria que só o autor vê
-- não é auditoria
drop policy if exists overrides_leitura on public.overrides_peticionamento;
create policy overrides_leitura on public.overrides_peticionamento
  for select to authenticated
  using (public.meu_papel() in ('OPERADOR', 'ADMIN'));

-- gravar, só quem pode forçar
drop policy if exists overrides_escrita on public.overrides_peticionamento;
create policy overrides_escrita on public.overrides_peticionamento
  for insert to authenticated
  with check (public.pode_forcar_peticao());


-- ── Registro das validações ─────────────────────────────────────
-- Guardar também o que foi APROVADO permite medir a trava depois: se ela
-- reprova demais, vira obstáculo e as pessoas passam a forçar por hábito.
create table if not exists public.validacoes_peticionamento (
  id               uuid primary key default gen_random_uuid(),
  caso_id          uuid not null references public.casos(id) on delete cascade,
  tipo_peticao     text not null,
  regra            text,
  aprovado         boolean not null,
  motivo           text,
  faltando         jsonb,
  usuario_email    text,
  criado_em        timestamptz not null default now()
);

create index if not exists idx_validacoes_caso
  on public.validacoes_peticionamento(caso_id, criado_em desc);

alter table public.validacoes_peticionamento enable row level security;
drop policy if exists validacoes_escritorio on public.validacoes_peticionamento;
create policy validacoes_escritorio on public.validacoes_peticionamento
  for all to authenticated
  using (public.meu_papel() in ('OPERADOR', 'ADMIN'))
  with check (public.meu_papel() in ('OPERADOR', 'ADMIN'));


-- ── Promoção do titular a ADMIN ─────────────────────────────────
-- Feita aqui, uma vez, pelo e-mail do responsável pelo escritório.
update public.perfis
   set papel = 'ADMIN'
 where email = 'adv.fabios.cunha@gmail.com';
