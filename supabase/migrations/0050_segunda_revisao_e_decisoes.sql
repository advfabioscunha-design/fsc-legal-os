-- 0050 — a decisão que é do cliente, e a segunda revisão.
--
-- A primeira revisão encontra três tipos de coisa: o que o redator
-- corrige sozinho, o que é nulo e precisa mudar de qualquer jeito, e o
-- que o cliente pediu mas a lei não admite.
--
-- O terceiro tipo não se resolve dentro do escritório. Ninguém pode
-- escolher pelo cliente entre perder o que ele pediu e assinar algo
-- que pode cair depois. Então o pedido para, a pergunta sai pelos três
-- canais, e o que ele responder fica gravado aqui com data, hora e o
-- texto exato que ele leu. Se um dia a cláusula for questionada, a
-- diferença entre o escritório ter avisado e não ter avisado está
-- neste campo.
--
-- Respondida a decisão, o redator refaz o texto e vem a SEGUNDA
-- revisão. Ela existe porque o texto mudou depois da última leitura, e
-- documento alterado que ninguém releu é exatamente onde o erro entra.
-- Ela não relê o contrato inteiro: confere se o que voltou atende ao
-- que foi apontado e ao que o cliente decidiu.

alter table public.pedidos_contrato
  add column if not exists decisoes           jsonb default '[]'::jsonb,
  add column if not exists decisoes_pendentes jsonb default '[]'::jsonb,
  add column if not exists revisao_2          jsonb,
  add column if not exists revisado_2_em      timestamptz;

comment on column public.pedidos_contrato.decisoes is
  'O que o cliente escolheu em cada ponto que a lei não admitia: '
  'MANTER como pediu, com ciência do risco, ou ADEQUAR. Guarda o texto '
  'que ele leu e a hora em que respondeu.';

comment on column public.pedidos_contrato.decisoes_pendentes is
  'Os pontos ainda sem resposta. Enquanto houver um, o relógio fica '
  'parado: meia decisão não pode seguir para a conferência.';

comment on column public.pedidos_contrato.revisao_2 is
  'A conferência do que mudou depois do ajuste. Não é releitura do '
  'contrato: olha se os apontamentos foram atendidos e se o texto '
  'respeita a decisão do cliente.';

create index if not exists idx_pedidos_decisao_pendente
  on public.pedidos_contrato(fase)
  where fase = 'CIENCIA_ALTERACAO' and excluido_em is null;
