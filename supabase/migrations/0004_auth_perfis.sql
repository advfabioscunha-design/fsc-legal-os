-- ================================================================
-- v4.3 — Autenticação por perfis (cliente x operador)
-- Liga os usuários do Supabase Auth a um PAPEL e, no caso do
-- cliente, ao seu registro em `clientes`. Operador tem acesso ao
-- CRM; cliente só inicia contratação e acompanha o próprio processo.
-- ================================================================

do $$ begin
  create type papel_usuario as enum ('CLIENTE', 'OPERADOR');
exception when duplicate_object then null; end $$;

create table if not exists perfis (
  id          uuid primary key references auth.users(id) on delete cascade,
  papel       papel_usuario not null default 'CLIENTE',
  nome        text,
  email       text,
  cliente_id  uuid references clientes(id),
  criado_em   timestamptz not null default now()
);
alter table perfis enable row level security;

-- cada usuário enxerga/edita apenas o próprio perfil
drop policy if exists perfil_self_select on perfis;
create policy perfil_self_select on perfis for select using (auth.uid() = id);
drop policy if exists perfil_self_update on perfis;
create policy perfil_self_update on perfis for update using (auth.uid() = id);

-- cria o perfil automaticamente no cadastro (sempre CLIENTE por padrão;
-- operador é promovido manualmente — ver nota ao final)
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.perfis (id, papel, nome, email)
  values (new.id, 'CLIENTE',
          coalesce(new.raw_user_meta_data->>'nome', ''), new.email)
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- helper: papel do usuário logado
create or replace function public.meu_papel()
returns papel_usuario language sql stable security definer set search_path = public as $$
  select papel from public.perfis where id = auth.uid()
$$;

-- ── RLS para o cliente ver os PRÓPRIOS casos e mensagens ────────
alter table casos     enable row level security;
alter table mensagens enable row level security;

drop policy if exists casos_cliente_select on casos;
create policy casos_cliente_select on casos for select using (
  public.meu_papel() = 'OPERADOR'
  or cliente_id in (select cliente_id from perfis where id = auth.uid())
);

drop policy if exists mensagens_cliente_select on mensagens;
create policy mensagens_cliente_select on mensagens for select using (
  public.meu_papel() = 'OPERADOR'
  or caso_id in (
    select c.id from casos c
    where c.cliente_id in (select cliente_id from perfis where id = auth.uid())
  )
);

-- ================================================================
-- PROMOVER UM OPERADOR (rodar manualmente após o cadastro dele):
--   update perfis set papel = 'OPERADOR'
--   where email = 'operador@fscadvocaciadigital.com.br';
-- ================================================================
