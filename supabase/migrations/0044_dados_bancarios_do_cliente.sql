-- 0044 — para onde o dinheiro do cliente vai.
--
-- Quando uma ação termina com valor a receber, alguém precisa dizer
-- para qual conta transferir. Hoje isso acontece por WhatsApp, no dia
-- do alvará, com o cliente mandando print do aplicativo do banco e o
-- escritório digitando à mão na prestação de contas. É o momento de
-- maior pressa do processo inteiro, que é exatamente quando se erra um
-- dígito.
--
-- Guardar antes resolve duas coisas: o dado chega conferido e com
-- calma, e a prestação de contas sai preenchida sozinha.
--
-- SÓ EM NOME DO CLIENTE
--
-- A conta informada tem de ser do próprio cliente. Transferir valor de
-- alvará para conta de terceiro é o caminho mais curto para uma
-- acusação de apropriação, e não há conveniência que pague esse risco.
-- A trava está na tela e no texto que o cliente lê, e o campo
-- `titular_confirmado` guarda a declaração dele de que a conta é sua.
--
-- ONDE ESSE DADO APARECE, E ONDE NÃO APARECE
--
-- Aparece num lugar só: no documento de prestação de contas, junto do
-- valor transferido. Não vai para contrato, não vai para procuração,
-- não vai para petição, não aparece na tela do caso. Dado bancário que
-- circula por todo lado acaba num documento que vai para o processo, e
-- processo é público.

alter table public.clientes
  add column if not exists banco_nome     text,
  add column if not exists banco_codigo   text,
  add column if not exists agencia        text,
  add column if not exists conta          text,
  add column if not exists conta_tipo     text,          -- CORRENTE | POUPANCA
  add column if not exists pix_tipo       text,          -- CPF | CNPJ | EMAIL | TELEFONE | ALEATORIA
  add column if not exists pix_chave      text,
  add column if not exists titular_confirmado boolean not null default false,
  add column if not exists dados_bancarios_em timestamptz;

comment on column public.clientes.titular_confirmado is
  'O cliente declarou que a conta informada é dele. Sem isso, a '
  'prestação de contas não usa os dados: o escritório pergunta na hora, '
  'como fazia antes.';

comment on column public.clientes.pix_chave is
  'Chave PIX do próprio cliente. Junto com a conta, e não no lugar '
  'dela: PIX falha, cai fora do horário, tem limite. Ter os dois '
  'caminhos evita que a transferência pare por causa do meio.';

comment on column public.clientes.dados_bancarios_em is
  'Quando o cliente informou ou atualizou. A prestação de contas cita '
  'esta data: dado bancário de dois anos atrás merece uma confirmação '
  'antes de a transferência sair.';
