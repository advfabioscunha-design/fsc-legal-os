-- 0036 — a agenda do escritório.
--
-- Até aqui a tela de Agenda desenhava o mês a partir de `prazos`: só
-- mostrava o que nascia de intimação. Não havia onde marcar uma reunião,
-- uma audiência designada por telefone, um atendimento combinado no
-- chat, nem onde escrever "hoje o cartório não atende".
--
-- Quatro tabelas, porque são quatro coisas diferentes:
--
--   agenda_itens          o compromisso em si
--   agenda_convidados     quem foi chamado e se confirmou
--   agenda_dias_fechados  o dia encerrado (conferido) e/ou bloqueado
--   agenda_notas          o recado do dia, que não é compromisso
--
-- O nome não é `eventos` porque essa tabela já existe e é o registro de
-- auditoria do sistema — dois significados no mesmo nome é armadilha.

-- O membro da equipe só tinha `google_email`, criado pensando numa sync
-- com o Google que nunca veio. Notificar alguém pelo campo chamado
-- "google_email" é pedir para o próximo leitor errar: um e-mail de
-- trabalho é um e-mail de trabalho, seja ele do Google ou não.
alter table public.membros_equipe
  add column if not exists email text;
update public.membros_equipe
   set email = google_email
 where email is null and google_email is not null;

create table if not exists public.agenda_itens (
  id              uuid primary key default gen_random_uuid(),
  tipo            text not null default 'EVENTO',
      -- TAREFA | EVENTO | AUDIENCIA | PERICIA | ATENDIMENTO | REUNIAO | PRAZO
  titulo          text not null,
  descricao       text,

  data            date not null,
  hora_inicio     time,                  -- sem hora = o dia inteiro
  hora_fim        time,
  dia_inteiro     boolean not null default false,

  local           text,                  -- fórum, sala, endereço
  link            text,                  -- sala de atendimento (Daily), link do PJe

  caso_id         uuid references public.casos(id) on delete cascade,
  cliente_id      uuid references public.clientes(id) on delete set null,
  numero_processo text,
  prazo_id        uuid references public.prazos(id) on delete set null,
  tarefa_id       uuid references public.tarefas(id) on delete set null,
  anotacao_id     uuid references public.anotacoes(id) on delete set null,

  responsavel_id  uuid references public.membros_equipe(id) on delete set null,
  responsavel_avisado_em timestamptz,

  status          text not null default 'ABERTO',
      -- ABERTO | REALIZADO | CANCELADO | REAGENDADO
  adiamentos      integer not null default 0,
  historico       jsonb default '[]'::jsonb,

  -- UID estável do iCalendar: reenviar o mesmo item ATUALIZA o
  -- compromisso no calendário de quem recebeu, em vez de criar outro.
  uid_ics         text unique,
  sequencia_ics   integer not null default 0,

  criado_por      text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now()
);

create index if not exists idx_agenda_data on public.agenda_itens(data, hora_inicio);
create index if not exists idx_agenda_status on public.agenda_itens(status, data);
create index if not exists idx_agenda_caso on public.agenda_itens(caso_id);
create index if not exists idx_agenda_resp on public.agenda_itens(responsavel_id, data);

-- Um prazo vira no máximo um compromisso vivo. Sem isto, cada passagem
-- da controladoria criaria outro.
create unique index if not exists idx_agenda_prazo_vivo
  on public.agenda_itens(prazo_id)
  where prazo_id is not null and status in ('ABERTO', 'REAGENDADO');


create table if not exists public.agenda_convidados (
  id            uuid primary key default gen_random_uuid(),
  item_id       uuid not null references public.agenda_itens(id) on delete cascade,
  nome          text,
  email         text not null,
  papel         text not null default 'OUTRO',   -- CLIENTE|EQUIPE|PARTE|PERITO|OUTRO
  -- Token do link de confirmação. Aleatório e longo: quem tem o link
  -- confirma, e só isso — nunca dá acesso a nada além deste convite.
  token         text not null unique,
  convite_enviado_em timestamptz,
  resposta      text not null default 'PENDENTE',  -- PENDENTE|ACEITO|RECUSADO
  respondido_em timestamptz,
  ip_resposta   text,
  criado_em     timestamptz not null default now()
);

create index if not exists idx_convidados_item on public.agenda_convidados(item_id);
-- Mesma pessoa não é convidada duas vezes para o mesmo compromisso.
create unique index if not exists idx_convidados_unico
  on public.agenda_convidados(item_id, lower(email));


create table if not exists public.agenda_dias_fechados (
  data           date primary key,
  motivo         text,
  -- Fechar o dia tem dois sentidos, e o escritório usa os dois:
  --   conferido       o dia foi revisto, nada ficou para trás
  --   bloqueia_novos  não aceitar novo agendamento nesta data
  -- Fechar sem bloquear é o encerramento do expediente; bloquear sem
  -- fechar é feriado, viagem, audiência que toma o dia todo.
  bloqueia_novos boolean not null default false,
  fechado_por    text,
  criado_em      timestamptz not null default now()
);


create table if not exists public.agenda_notas (
  id         uuid primary key default gen_random_uuid(),
  data       date not null,
  texto      text not null,
  autor      text,
  criado_em  timestamptz not null default now()
);

create index if not exists idx_agenda_notas_data on public.agenda_notas(data);


comment on column public.agenda_itens.responsavel_avisado_em is
  'Quando o responsável foi notificado. Nulo com responsável preenchido '
  'significa que alguém foi designado e não sabe — é isso que a auditoria '
  'procura.';

comment on table public.agenda_notas is
  'O recado do dia: "cartório não atende", "perita remarcou por telefone", '
  '"cliente avisou que chega atrasado". Não é compromisso e não gera '
  'convite, mas é o que explica o dia para quem olhar depois.';
