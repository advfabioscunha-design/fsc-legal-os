-- 0041 — como alguém entra para a equipe.
--
-- Até aqui não havia caminho nenhum. Para um assessor começar a
-- trabalhar, era preciso criar o usuário na mão no painel do Supabase,
-- escrever a linha em membros_equipe e mudar o papel no banco. Três
-- passos manuais, fora da plataforma, feitos por quem tem a chave do
-- projeto, e nenhum deles fica registrado como decisão de alguém.
--
-- O convite resolve isso e traz uma coisa que a criação manual nunca
-- teve: rastro. Quem convidou, quando, para qual nível, quando a pessoa
-- aceitou, e de qual endereço. Se um dia se discutir o acesso de
-- alguém, a resposta está aqui.
--
-- SOBRE O NÍVEL
--
-- `perfis.papel` continua sendo o que o sistema pergunta para decidir
-- se alguém entra numa tela: CLIENTE, OPERADOR ou ADMIN. Ele não muda.
--
-- `nivel` é outra coisa: é a função da pessoa no escritório. Advogado,
-- assessor e estagiário são todos OPERADOR hoje, e por isso o sistema
-- não sabe distinguir um do outro. Guardar a função agora é o que vai
-- permitir, depois, dizer que estagiário não peticiona sem revisão,
-- sem ter de refazer o cadastro de ninguém.
--
-- ADMINISTRADOR NÃO SE CONVIDA
--
-- Um link de convite pode ser encaminhado por engano, vazar de uma
-- caixa de e-mail, ficar num print. Se esse link criar um
-- administrador, cria junto o poder de excluir pedido e de forçar
-- peticionamento. Então o convite nasce sempre em nível de trabalho, e
-- virar administrador é ato de quem já é, feito dentro da plataforma e
-- gravado com data, hora e autor.

-- ── O nível da pessoa ───────────────────────────────────────────
alter table public.perfis
  add column if not exists nivel text;

alter table public.membros_equipe
  add column if not exists nivel      text not null default 'ASSESSOR',
  add column if not exists perfil_id  uuid references public.perfis(id) on delete set null,
  add column if not exists convidado_por text,
  add column if not exists entrou_em  timestamptz;

comment on column public.membros_equipe.nivel is
  'ADMINISTRADOR | ADVOGADO | ASSESSOR | ESTAGIARIO. É a função no '
  'escritório, não a permissão técnica: essa continua em perfis.papel. '
  'Existe para que o sistema possa, depois, tratar estagiário e '
  'advogado de forma diferente sem refazer cadastro nenhum.';

comment on column public.membros_equipe.perfil_id is
  'A conta de acesso desta pessoa. Nulo enquanto o convite não for '
  'aceito: o membro já existe na agenda e pode receber tarefa antes '
  'mesmo de ter entrado na plataforma pela primeira vez.';

-- Quem já está na equipe veio de antes do nível existir. Líder vira
-- advogado, o resto vira assessor: é o palpite que erra menos, e a tela
-- deixa corrigir em um clique.
update public.membros_equipe
   set nivel = case when lider then 'ADVOGADO' else 'ASSESSOR' end
 where nivel is null or nivel = 'ASSESSOR';


-- ── O convite ───────────────────────────────────────────────────
--
-- O token é de uso único e tem prazo. Convite sem prazo é chave
-- perdida: fica num e-mail antigo e continua valendo dois anos depois,
-- quando a pessoa já saiu do escritório.
create table if not exists public.convites_equipe (
  id            uuid primary key default gen_random_uuid(),
  nome          text not null,
  email         text not null,
  nivel         text not null default 'ASSESSOR',
  especialidades text[] default '{}',
  telefone      text,

  token         text not null unique,
  expira_em     timestamptz not null,
  status        text not null default 'PENDENTE',
      -- PENDENTE | ACEITO | CANCELADO | EXPIRADO

  convidado_por text,
  criado_em     timestamptz not null default now(),
  enviado_em    timestamptz,
  reenviado_em  timestamptz,
  aceito_em     timestamptz,
  aceito_ip     text,
  membro_id     uuid references public.membros_equipe(id) on delete set null,
  perfil_id     uuid references public.perfis(id) on delete set null,
  observacao    text
);

create index if not exists idx_convites_status
  on public.convites_equipe(status, criado_em desc);
create unique index if not exists idx_convites_email_aberto
  on public.convites_equipe(lower(email))
  where status = 'PENDENTE';

comment on table public.convites_equipe is
  'Um convite por e-mail em aberto. O índice parcial garante isso: dois '
  'convites vivos para a mesma pessoa significam dois links válidos, e '
  'o segundo sempre parece o certo para quem recebe.';

comment on column public.convites_equipe.token is
  'Sorteado no servidor, de uso único. Vale como senha enquanto o '
  'convite estiver pendente, por isso o prazo curto.';

alter table public.convites_equipe enable row level security;
-- Sem policy de leitura: quem lê é a API com a chave de serviço. A
-- página de aceite consulta pelo token, por uma rota que devolve só o
-- nome e o nível, nunca a lista.


-- ── Promoção a administrador ────────────────────────────────────
create table if not exists public.promocoes_equipe (
  id          uuid primary key default gen_random_uuid(),
  perfil_id   uuid not null references public.perfis(id) on delete cascade,
  de_nivel    text,
  para_nivel  text not null,
  de_papel    text,
  para_papel  text not null,
  motivo      text,
  quem        text,
  criado_em   timestamptz not null default now()
);

create index if not exists idx_promocoes_perfil
  on public.promocoes_equipe(perfil_id, criado_em desc);

comment on table public.promocoes_equipe is
  'Toda mudança de nível ou de papel, com quem decidiu e por quê. '
  'Acesso que aparece sem explicação é o começo de toda discussão '
  'sobre quem podia fazer o quê.';
