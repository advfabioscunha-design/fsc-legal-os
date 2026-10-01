-- O BANCO DE RELACIONAMENTO DO ESCRITÓRIO.
--
-- A base de clientes já existe: é a tabela `clientes`. O que faltava era
-- o que separa uma agenda de contatos de uma lista de disparo, que são
-- duas coisas bem diferentes em um escritório de advocacia.
--
-- CONSENTIMENTO, PORQUE É CLIENTE E NÃO LISTA COMPRADA
--
-- Parabéns de aniversário a quem é cliente é cortesia, e cabe no
-- legítimo interesse: a pessoa confiou um processo ao escritório e a
-- relação existe. Informativo periódico é outra coisa: é comunicação de
-- massa, e a LGPD e o Provimento 205/2021 da OAB tratam disso com mais
-- rigor. Por isso são DOIS campos, e não um:
--
--   aceita_felicitacoes  nasce ligado, com saída a qualquer momento
--   aceita_informativos  nasce DESLIGADO, só liga se a pessoa pedir
--
-- Quem pede para parar entra em `descadastrado_em`, e nenhum envio
-- automático passa por cima disso. Pedido de descadastro ignorado é o
-- tipo de coisa que vira reclamação na OAB e bloqueio do número na Meta
-- ao mesmo tempo.

alter table clientes add column if not exists aceita_felicitacoes boolean not null default true;
alter table clientes add column if not exists aceita_informativos boolean not null default false;
alter table clientes add column if not exists descadastrado_em    timestamptz;
alter table clientes add column if not exists descadastro_motivo  text;
-- De onde veio a autorização: "contrato de honorários", "pediu no
-- WhatsApp", "cadastro na plataforma". Sem isso, daqui a um ano
-- ninguém sabe dizer por que aquela pessoa está na lista.
alter table clientes add column if not exists origem_consentimento text;
alter table clientes add column if not exists consentimento_em     timestamptz;
-- Como o escritório conheceu a pessoa, para o relacionamento saber o
-- tom: cliente antigo, indicação, processo encerrado há anos.
alter table clientes add column if not exists relacionamento_nota text;

create index if not exists clientes_nascimento_idx
  on clientes (data_nascimento) where data_nascimento is not null;


-- O QUE JÁ FOI ENVIADO, PARA NÃO ENVIAR DUAS VEZES.
--
-- A rotina de aniversário roda todo dia às 9h. Se o servidor reiniciar,
-- se alguém apertar o botão à mão, ou se o job rodar duas vezes por
-- qualquer motivo, o cliente recebia DOIS "feliz aniversário" no mesmo
-- dia — e nada denuncia mais um robô do que isso.
--
-- A chave única é cliente + tipo + referência (o ano, para aniversário;
-- a data da campanha, para informativo). A segunda tentativa esbarra no
-- banco e não sai.

create table if not exists relacionamento_envios (
  id          uuid primary key default gen_random_uuid(),
  cliente_id  uuid not null references clientes(id),
  tipo        text not null,              -- ANIVERSARIO | DATA | INFORMATIVO
  referencia  text not null,              -- '2026' no aniversário; a data na campanha
  canal       text not null default 'WHATSAPP',
  texto       text,
  enviado_em  timestamptz not null default now(),
  erro        text,
  unique (cliente_id, tipo, referencia)
);

create index if not exists relacionamento_envios_cliente_idx
  on relacionamento_envios (cliente_id, enviado_em desc);

alter table relacionamento_envios enable row level security;
drop policy if exists relacionamento_envios_servico on relacionamento_envios;
create policy relacionamento_envios_servico on relacionamento_envios
  for all to service_role using (true) with check (true);
