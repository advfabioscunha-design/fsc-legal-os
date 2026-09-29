-- 0040 — o número de protocolo que nunca chegou a existir.
--
-- A migração 0031 criou a coluna `numero`, a função que a preenche e o
-- gatilho que chama a função. No banco, só a coluna existia. Todos os
-- pedidos do balcão nasceram com numero nulo, e a tela mostrava um
-- espaço em branco onde deveria estar o protocolo.
--
-- Ninguém percebeu porque a tela do operador é aberta pelo card, e o
-- cliente só tinha um pedido. O problema aparece na hora errada: quando
-- o cliente liga e diz "é sobre o meu contrato", e não há número para
-- confirmar de qual dos pedidos ele está falando.
--
-- Esta migração refaz função e gatilho e numera o que já existe, na
-- ordem em que os pedidos foram criados, que é a ordem que o número
-- deveria ter tido desde o começo.

create or replace function public.gerar_numero_pedido()
returns trigger language plpgsql as $$
declare ano text; seq int;
begin
  if new.numero is null then
    ano := to_char(now(), 'YYYY');
    select coalesce(max(substring(numero from 12)::int), 0) + 1
      into seq
      from public.pedidos_contrato
     where numero like 'FSC-C-' || ano || '-%';
    new.numero := 'FSC-C-' || ano || '-' || lpad(seq::text, 4, '0');
  end if;
  return new;
end;
$$;

drop trigger if exists trg_numero_pedido on public.pedidos_contrato;
create trigger trg_numero_pedido
  before insert on public.pedidos_contrato
  for each row execute function public.gerar_numero_pedido();

-- Os que já existiam. Numerados por ano e por ordem de criação, para
-- que o protocolo continue dizendo a verdade sobre quando o pedido
-- entrou.
with s as (
  select id,
         'FSC-C-' || to_char(criado_em, 'YYYY') || '-' ||
         lpad((row_number() over (partition by to_char(criado_em, 'YYYY')
                                  order by criado_em))::text, 4, '0') as n
    from public.pedidos_contrato
   where numero is null
)
update public.pedidos_contrato p
   set numero = s.n
  from s
 where p.id = s.id;
