-- A AGENDA DE CONTATOS DO WHATSAPP.
--
-- O escritório salva o número do cliente junto com o caso dele. Quando
-- esse número escreve, o atendimento já sabe de quem é e sobre o que é,
-- e não precisa pedir CPF a quem o próprio escritório cadastrou.
--
-- POR QUE UMA TABELA, E NÃO O CAMPO `whatsapp` DO CLIENTE
--
-- O campo do cadastro responde "qual é o telefone deste cliente". Esta
-- tabela responde a pergunta inversa, que é a que o atendimento faz:
-- "de quem é este telefone, e sobre qual caso ele costuma falar".
--
-- São perguntas diferentes e os dados também: um cliente usa dois
-- telefones, um telefone atende por dois clientes da mesma família, e o
-- cliente com três processos fala quase sempre de um só. Nada disso cabe
-- num campo único do cadastro sem apagar informação.
--
-- O `caso_id` é o caso PADRÃO, não uma trava: o cliente continua podendo
-- perguntar de outro, e o agente continua podendo listar os demais.

create table if not exists contatos_whatsapp (
  numero      text primary key,                 -- só dígitos, com 55 na frente
  cliente_id  uuid references clientes(id),
  caso_id     uuid references casos(id),
  nome        text,                             -- como o escritório chama a pessoa
  observacao  text,                             -- o que quem salvou quis deixar dito
  criado_por  text,
  criado_em   timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

create index if not exists contatos_whatsapp_cliente_idx
  on contatos_whatsapp (cliente_id);
create index if not exists contatos_whatsapp_caso_idx
  on contatos_whatsapp (caso_id);

alter table contatos_whatsapp enable row level security;

drop policy if exists contatos_whatsapp_servico on contatos_whatsapp;
create policy contatos_whatsapp_servico on contatos_whatsapp
  for all to service_role using (true) with check (true);
