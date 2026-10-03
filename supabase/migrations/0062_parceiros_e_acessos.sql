-- ════════════════════════════════════════════════════════════════
-- ADVOGADOS PARCEIROS — e o controle de acesso do administrador
-- ════════════════════════════════════════════════════════════════
--
-- O PROBLEMA QUE ISTO RESOLVE
--
-- Até aqui o sistema conhecia dois mundos. Quem é da EQUIPE vê tudo: a
-- API não filtra nada para OPERADOR e ADMIN. Quem é CLIENTE vê só o que
-- é dele, e isso é conferido dentro de cada rota.
--
-- O parceiro é um terceiro, e não cabia em nenhum dos dois. Ele é
-- advogado, trabalha nos casos, assina peça — mas só pode enxergar os
-- processos em que a parceria existe. Mostrar a ele a carteira inteira
-- do escritório seria quebra de sigilo, e dar a ele a tela do cliente
-- seria impedi-lo de trabalhar.
--
-- PARCEIRO NÃO É ADVOGADO ASSOCIADO
--
-- A distinção atravessa todo o desenho. O associado é do escritório:
-- tem papel OPERADOR ou ADMIN, vê a carteira toda, responde pela
-- operação. O parceiro é de fora: atua em causa específica, divide o
-- honorário daquela causa e não tem nada que ver com o resto.
--
-- Por isso parceiro NÃO entra em `membros_equipe`. Ele tem tabela
-- própria, papel próprio e telas próprias.

-- ── 1. QUEM É O PARCEIRO ────────────────────────────────────────
--
-- Os dados bancários moram aqui porque o repasse é feito a ele, e
-- perguntar a chave PIX na hora do acerto é o jeito certo de atrasar o
-- pagamento de alguém que já trabalhou.

create table if not exists public.parceiros (
  id             uuid primary key default gen_random_uuid(),
  auth_user_id   uuid unique,              -- o login dele (Supabase Auth)
  nome           text not null,
  cpf_cnpj       text,
  oab_numero     text,
  oab_uf         text,
  email          text,
  whatsapp       text,
  -- Para onde vai o dinheiro dele
  banco_nome     text,
  banco_codigo   text,
  agencia        text,
  conta          text,
  conta_tipo     text,
  pix_tipo       text,
  pix_chave      text,
  titular_confirmado boolean not null default false,
  -- ── O QUE ELE PODE FAZER ALÉM DO BÁSICO ──────────────────────
  --
  -- Nascem DESLIGADAS, as duas, e só o administrador liga. Não é
  -- desconfiança do parceiro: é que estas duas abrem portas que
  -- respondem pelo escritório, e abrir por padrão é decidir por quem
  -- deveria decidir.
  --
  -- `pode_usar_ia` — os agentes consomem a conta de IA do escritório, e
  -- a peça que sai leva o timbre e a OAB do responsável. Quem paga a
  -- conta e assina o documento é quem autoriza.
  --
  -- `pode_falar_com_cliente` — mensagem no canal do escritório chega ao
  -- cliente como se fosse do escritório. O parceiro conversa com a
  -- equipe desde o primeiro dia; falar em nome da casa é outra coisa.
  pode_usar_ia             boolean not null default false,
  pode_falar_com_cliente   boolean not null default false,
  permissoes_em            timestamptz,
  permissoes_por           text,

  -- Situação
  status         text not null default 'ATIVO',   -- ATIVO | SUSPENSO | ENCERRADO
  observacao     text,
  cadastro_completo_em timestamptz,
  criado_por     text,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now()
);

create unique index if not exists parceiros_oab_idx
  on public.parceiros (oab_numero, oab_uf)
  where oab_numero is not null and oab_uf is not null;
create index if not exists parceiros_email_idx on public.parceiros (lower(email));

comment on column public.parceiros.pode_usar_ia is
  'Desligado ao nascer. Só o administrador liga: os agentes gastam a '
  'conta de IA do escritório e a peça sai com o timbre dele.';
comment on column public.parceiros.pode_falar_com_cliente is
  'Desligado ao nascer. Só o administrador liga: mensagem nesse canal '
  'chega ao cliente como se viesse do escritório.';

comment on table public.parceiros is
  'Advogado de fora que atua em causa específica do escritório e divide '
  'o honorário dela. Não é membro da equipe: não vê a carteira, só os '
  'casos em que a parceria existe.';

-- ── 2. A PARCERIA: QUE CASO, QUE PERCENTUAL, POR QUANTO TEMPO ───
--
-- O percentual incide sobre o VALOR BRUTO dos honorários — contratuais
-- e sucumbenciais, com o mesmo percentual. Essa escolha fica gravada em
-- `base_calculo` em vez de ficar só no combinado verbal: acordo que se
-- calcula de um jeito quando o valor é pequeno e de outro quando é
-- grande é acordo que termina em desentendimento.
--
-- `encerrada_em` existe porque parceria acaba. Acabando, o acesso fecha
-- na hora — mas o registro fica, porque o percentual continua valendo
-- para o que foi recebido enquanto ela existia.

create table if not exists public.parcerias (
  id             uuid primary key default gen_random_uuid(),
  caso_id        uuid not null references public.casos(id) on delete cascade,
  parceiro_id    uuid not null references public.parceiros(id) on delete cascade,
  percentual     numeric(5,2) not null,     -- 0 a 100
  base_calculo   text not null default 'BRUTO',   -- BRUTO | LIQUIDO
  inclui_sucumbencia boolean not null default true,
  papel          text,                      -- correspondente, parceiro de tese, captador
  proposto_por   text,                      -- PARCEIRO | ESCRITORIO
  aprovada_em    timestamptz,               -- o escritório confirmou o percentual
  aprovada_por   text,
  observacao     text,
  iniciada_em    timestamptz not null default now(),
  encerrada_em   timestamptz,
  criado_em      timestamptz not null default now()
);

-- Um parceiro, um percentual vigente por caso. Dois registros vivos
-- para a mesma dupla significam dois percentuais, e aí ninguém sabe
-- qual vale na hora de pagar.
create unique index if not exists parcerias_viva_idx
  on public.parcerias (caso_id, parceiro_id)
  where encerrada_em is null;
create index if not exists parcerias_parceiro_idx on public.parcerias (parceiro_id);
create index if not exists parcerias_caso_idx on public.parcerias (caso_id);

comment on column public.parcerias.percentual is
  'Percentual do parceiro sobre o honorário BRUTO do caso (contratual '
  'e, quando inclui_sucumbencia, também o sucumbencial).';
comment on column public.parcerias.proposto_por is
  'Quem lançou o percentual. O parceiro pode propor ao cadastrar o caso; '
  'vale a partir da aprovação do escritório.';

-- ── 3. O ACERTO, CONGELADO ──────────────────────────────────────
--
-- Por que uma tabela só para isto: o percentual da parceria pode mudar
-- amanhã. O que já foi acertado não pode mudar junto. Aqui fica a
-- fotografia do cálculo — base, percentual aplicado e valor — do jeito
-- que estava no dia. Mesma lógica do histórico de honorários.

create table if not exists public.repasses_parceiro (
  id             uuid primary key default gen_random_uuid(),
  prestacao_id   uuid references public.prestacoes_contas(id) on delete cascade,
  caso_id        uuid not null references public.casos(id) on delete cascade,
  parceiro_id    uuid not null references public.parceiros(id),
  parceria_id    uuid references public.parcerias(id),
  base_contratual numeric(14,2) not null default 0,
  base_sucumbencia numeric(14,2) not null default 0,
  percentual     numeric(5,2) not null,
  valor_devido   numeric(14,2) not null default 0,
  pago_em        timestamptz,
  forma_pagamento text,
  comprovante_path text,
  observacao     text,
  criado_em      timestamptz not null default now()
);

create index if not exists repasses_parceiro_idx
  on public.repasses_parceiro (parceiro_id, criado_em desc);
create index if not exists repasses_caso_idx on public.repasses_parceiro (caso_id);

-- ── 4. O QUE O ADMINISTRADOR LIBERA OU BLOQUEIA ─────────────────
--
-- Só o administrador mexe aqui. São duas coisas diferentes na mesma
-- tabela, e o campo `efeito` diz qual:
--
--   LIBERAR  — dá a alguém um caso que ele não veria
--   BLOQUEAR — tira de alguém um caso que ele veria
--
-- O bloqueio existe para o caso sensível: o processo do próprio sócio,
-- a causa de um familiar, o cliente que pediu reserva. Hoje isso não
-- tem como ser feito — quem é da equipe vê tudo, e a única alternativa
-- seria tirar a pessoa da equipe.
--
-- O bloqueio vence a liberação, sempre. Em dúvida, o sistema esconde.

create table if not exists public.acessos_por_caso (
  id             uuid primary key default gen_random_uuid(),
  caso_id        uuid not null references public.casos(id) on delete cascade,
  perfil_id      uuid,                      -- membro da equipe (perfis.id)
  parceiro_id    uuid references public.parceiros(id) on delete cascade,
  efeito         text not null,             -- LIBERAR | BLOQUEAR
  motivo         text,
  concedido_por  text not null,
  criado_em      timestamptz not null default now(),
  revogado_em    timestamptz,
  revogado_por   text,
  -- Ou é de um membro da equipe, ou é de um parceiro. Nunca dos dois,
  -- nunca de nenhum: regra no banco e não só na tela, porque linha sem
  -- dono é regra de acesso que ninguém sabe a quem se aplica.
  constraint acesso_tem_um_dono check (
    (perfil_id is not null and parceiro_id is null) or
    (perfil_id is null and parceiro_id is not null))
);

create index if not exists acessos_caso_idx on public.acessos_por_caso (caso_id)
  where revogado_em is null;
create index if not exists acessos_perfil_idx on public.acessos_por_caso (perfil_id)
  where revogado_em is null;
create index if not exists acessos_parceiro_idx on public.acessos_por_caso (parceiro_id)
  where revogado_em is null;

-- ── 5. REGISTRO DE QUEM MEXEU NO ACESSO ─────────────────────────
--
-- Conceder e retirar acesso é ato de quem responde pelo escritório.
-- Sem registro, uma semana depois ninguém lembra quem liberou o quê —
-- e numa auditoria da OAB isso é exatamente o que se pergunta.

create table if not exists public.registro_de_acessos (
  id             uuid primary key default gen_random_uuid(),
  quando         timestamptz not null default now(),
  quem_fez       text not null,
  acao           text not null,   -- PROMOVEU_ADMIN | REBAIXOU | LIBEROU_CASO |
                                  -- BLOQUEOU_CASO | SUSPENDEU_PARCEIRO | ...
  alvo_tipo      text,            -- PERFIL | PARCEIRO | CASO
  alvo_id        text,
  alvo_nome      text,
  detalhe        jsonb
);

create index if not exists registro_acessos_quando on public.registro_de_acessos (quando desc);

-- ── 6. O PAPEL NOVO ─────────────────────────────────────────────
--
-- `perfis.papel` passa a aceitar PARCEIRO, ao lado de CLIENTE, OPERADOR
-- e ADMIN. É esse campo que o porteiro lê para decidir qual mundo a
-- pessoa enxerga.

comment on column public.perfis.papel is
  'CLIENTE (área do cliente) · PARCEIRO (só os casos em que há parceria) '
  '· OPERADOR (equipe) · ADMIN (equipe, e único que concede acesso).';

-- ── 7. RLS ──────────────────────────────────────────────────────
--
-- Mesma postura das demais: tudo passa pela API com a chave de serviço,
-- e o navegador não fala direto com estas tabelas.

alter table public.parceiros          enable row level security;
alter table public.parcerias          enable row level security;
alter table public.repasses_parceiro  enable row level security;
alter table public.acessos_por_caso   enable row level security;
alter table public.registro_de_acessos enable row level security;

drop policy if exists parceiros_servico on public.parceiros;
create policy parceiros_servico on public.parceiros
  for all to service_role using (true) with check (true);

drop policy if exists parcerias_servico on public.parcerias;
create policy parcerias_servico on public.parcerias
  for all to service_role using (true) with check (true);

drop policy if exists repasses_parceiro_servico on public.repasses_parceiro;
create policy repasses_parceiro_servico on public.repasses_parceiro
  for all to service_role using (true) with check (true);

drop policy if exists acessos_por_caso_servico on public.acessos_por_caso;
create policy acessos_por_caso_servico on public.acessos_por_caso
  for all to service_role using (true) with check (true);

drop policy if exists registro_de_acessos_servico on public.registro_de_acessos;
create policy registro_de_acessos_servico on public.registro_de_acessos
  for all to service_role using (true) with check (true);
