-- 0054 — esperar o cliente não consome o prazo do escritório.
--
-- São dois relógios no pedido, e só um deles parava.
--
-- O da FASE já parava: `avanca_em` nulo segura a esteira enquanto
-- falta informação indispensável. O da ENTREGA não parava, e era
-- justamente o que o cliente comprou: o escritório prometeu 24 horas,
-- o cliente levou oito para mandar o CPF do fiador, e o prazo seguiu
-- correndo contra quem estava parado esperando por ele. Na prática o
-- escritório entregava um serviço de 24 horas em 16, ou perdia o
-- prazo por culpa de uma espera que não era dele.
--
-- Quem contratou 24 horas de trabalho não contratou 24 horas de
-- calendário. As duas colunas abaixo guardam a diferença:
--
--   relogio_parado_em  o instante em que a espera começou. Nulo
--                      significa relógio andando.
--   horas_paradas      o total já acumulado de esperas encerradas.
--
-- O vencimento passa a ser pagamento + prazo + horas_paradas, e a
-- espera em curso entra na conta junto com as encerradas. Sem isso o
-- vencimento ficaria congelado no lugar errado durante toda a espera e
-- daria um salto no instante em que o cliente respondesse, que é
-- exatamente quando ninguém está olhando a agenda.
--
-- O marco da espera é gravado uma vez só, e não a cada salvamento:
-- remarcar zeraria o tempo parado de quem mandou metade da informação
-- e sumiu, que é o caso em que a contagem mais importa.

alter table public.pedidos_contrato
  add column if not exists relogio_parado_em timestamptz,
  add column if not exists horas_paradas     numeric(10,3) not null default 0;

comment on column public.pedidos_contrato.relogio_parado_em is
  'Quando o pedido parou para esperar informação do cliente. Nulo é '
  'relógio andando. Gravado uma vez só por espera.';

comment on column public.pedidos_contrato.horas_paradas is
  'Soma das esperas já encerradas, em horas. Entra no cálculo do '
  'vencimento da entrega para que a demora do cliente não consuma o '
  'prazo do escritório.';

-- A agenda mostra quando o compromisso está parado esperando alguém,
-- para o prazo que não anda não ser lido como prazo esquecido.
alter table public.agenda_itens
  add column if not exists aguardando_cliente boolean not null default false;

comment on column public.agenda_itens.aguardando_cliente is
  'Verdadeiro enquanto o prazo está suspenso à espera do cliente. O '
  'compromisso continua na agenda, e o vencimento anda junto com a '
  'espera em vez de vencer sozinho.';

create index if not exists idx_pedidos_relogio_parado
  on public.pedidos_contrato(relogio_parado_em)
  where relogio_parado_em is not null and excluido_em is null;
