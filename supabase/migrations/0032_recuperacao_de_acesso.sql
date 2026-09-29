-- 0032 — recuperação de acesso à conta do cliente.
--
-- Duas coisas diferentes, que costumam ser tratadas como uma só:
--
--   ESQUECI A SENHA        o e-mail continua acessível. Resolve sozinho:
--                          link com token de uso único e validade curta.
--                          Não precisa de tabela nenhuma.
--
--   PERDI O E-MAIL         o único canal verificado se perdeu. NÃO existe
--                          jeito automático seguro: qualquer regra que
--                          troque o e-mail com dado que circula por aí
--                          (CPF, nome da mãe, data de nascimento) entrega
--                          a conta a quem tiver esses dados — e num
--                          escritório de advocacia a conta guarda
--                          contrato, procuração e documento pessoal.
--
-- Esta tabela é do segundo caso: o pedido entra numa fila, alguém liga
-- para o número cadastrado, confirma quem é, e só então libera.

create table if not exists public.solicitacoes_acesso (
  id                uuid primary key default gen_random_uuid(),
  cliente_id        uuid references public.clientes(id) on delete cascade,
  cpf_informado     text,                  -- guardado só o suficiente para conferir
  nascimento_bate   boolean,               -- conferência feita no servidor
  email_atual       text,
  email_novo        text not null,
  status            text not null default 'PENDENTE',  -- PENDENTE|APROVADA|RECUSADA
  conferido_por     text,
  conferido_em      timestamptz,
  observacao        text,
  ip                text,
  criado_em         timestamptz not null default now()
);

create index if not exists idx_sol_acesso_status
  on public.solicitacoes_acesso(status, criado_em desc);

comment on table public.solicitacoes_acesso is
  'Pedidos de troca do e-mail de acesso. Nunca são aplicados '
  'automaticamente: o escritório confirma a identidade por telefone ou '
  'WhatsApp no número já cadastrado antes de aprovar.';

comment on column public.solicitacoes_acesso.nascimento_bate is
  'A data de nascimento informada confere com o cadastro. Não é prova de '
  'identidade — é filtro para tentativa preguiçosa não consumir o tempo '
  'de quem vai ligar.';
