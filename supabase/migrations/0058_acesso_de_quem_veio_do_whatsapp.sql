-- O CONVITE DE ACESSO DE QUEM CHEGOU PELO WHATSAPP.
--
-- Quem escreve no WhatsApp vira cliente com número e sem e-mail. Quando
-- ele cria a senha, o sistema procurava o cadastro dele pelo e-mail, não
-- achava nada (porque não havia e-mail nenhum), e criava um cadastro
-- NOVO. O caso ficava pendurado no cadastro antigo, e o cliente entrava
-- na plataforma para ver o próprio caso e encontrava a tela vazia.
--
-- O código abaixo é a ponte. Ele sai uma vez, pelo WhatsApp, para aquele
-- número; quando o cliente cria a conta com ele, o cadastro que já
-- existe recebe o login e o e-mail, em vez de nascer outro ao lado.
--
-- Por que código e não só o número de telefone: o número vai no link, e
-- link se encaminha. Com o código, quem recebe o encaminhado não entra,
-- porque o código é usado uma vez e morre.

alter table clientes add column if not exists codigo_acesso       text;
alter table clientes add column if not exists codigo_acesso_em    timestamptz;
alter table clientes add column if not exists codigo_usado_em     timestamptz;

-- Dois cadastros com o mesmo código ligariam o login ao cadastro errado.
create unique index if not exists clientes_codigo_acesso_idx
  on clientes (codigo_acesso) where codigo_acesso is not null;

comment on column clientes.codigo_acesso is
  'Código de uso único enviado pelo WhatsApp para o cliente criar a senha '
  'e assumir este cadastro. Zerado quando usado.';
