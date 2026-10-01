-- 0053 — o prazo que se conta em horas, e não em dias.
--
-- O contrato do balcão tem entrega em 24 horas, ou em 6 quando o
-- cliente paga a urgência. Isso não cabe no campo de data: quem
-- contratou às 14h de terça com 24 horas tem até as 14h de quarta, e
-- não até o fim de quarta. A diferença é um dia inteiro de trabalho
-- que o escritório acha que tem e não tem.
--
-- Prazo processual continua em `prazo_fatal`, que é data, porque é
-- assim que a lei o conta. Prazo de serviço vai em `prazo_fatal_em`,
-- com hora, porque é assim que foi vendido.
--
-- O `pedido_id` existe por causa de uma particularidade: este prazo
-- MUDA no meio do caminho. Urgência contratada depois do pedido aberto
-- encurta a entrega, e o vencimento pode cair para o dia anterior ao
-- que estava marcado. Com a ligação, o compromisso é recalculado da
-- mesma conta que o balcão usa, em vez de corrigido na mão: duas
-- contas do mesmo prazo acabam divergindo, e a que diverge é sempre a
-- que ninguém está olhando.

alter table public.agenda_itens
  add column if not exists prazo_fatal_em timestamptz,
  add column if not exists pedido_id      uuid;

comment on column public.agenda_itens.prazo_fatal_em is
  'O vencimento com hora, para os prazos contados em horas, como a '
  'entrega do balcão. Quando existe, manda sobre `prazo_fatal`.';

comment on column public.agenda_itens.pedido_id is
  'O pedido do balcão que este compromisso espelha. É por ele que a '
  'urgência contratada no meio do caminho move o compromisso sozinha.';

create index if not exists idx_agenda_pedido
  on public.agenda_itens(pedido_id)
  where pedido_id is not null;

create index if not exists idx_agenda_fatal_hora
  on public.agenda_itens(prazo_fatal_em)
  where prazo_fatal_em is not null and status in ('ABERTO', 'CONFIRMADO');
