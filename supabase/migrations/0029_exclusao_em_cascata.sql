-- 0029 — apagar um caso apaga o que pende dele.
--
-- Metade das tabelas filhas estava com ON DELETE NO ACTION, então o
-- banco recusava apagar o caso enquanto restasse uma intimação, um
-- prazo, um protocolo. O código tentava limpar só quatro delas, e as
-- que ficaram de fora travavam tudo — de forma silenciosa, porque a
-- tela fechava o painel sem olhar a resposta.
--
-- Isso apareceu quando começamos a importar processos do CNJ: caso
-- importado nasce com intimações e prazos, e nenhum deles podia ser
-- excluído. Antes disso o defeito existia, apenas não era exercitado.
--
-- Duas defesas, e as duas ficam: o código continua apagando as filhas
-- explicitamente (é ele quem monta o backup da lixeira, e backup é a
-- razão de existir dessa ordem), e o banco passa a garantir o resto.

alter table public.prazos
  drop constraint if exists prazos_caso_id_fkey,
  add constraint prazos_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.intimacoes
  drop constraint if exists intimacoes_caso_id_fkey,
  add constraint intimacoes_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.mensagens
  drop constraint if exists mensagens_caso_id_fkey,
  add constraint mensagens_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.documentos
  drop constraint if exists documentos_caso_id_fkey,
  add constraint documentos_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.eventos
  drop constraint if exists eventos_caso_id_fkey,
  add constraint eventos_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.protocolos
  drop constraint if exists protocolos_caso_id_fkey,
  add constraint protocolos_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.escalacoes
  drop constraint if exists escalacoes_caso_id_fkey,
  add constraint escalacoes_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;

alter table public.monitoramentos
  drop constraint if exists monitoramentos_caso_id_fkey,
  add constraint monitoramentos_caso_id_fkey
    foreign key (caso_id) references public.casos(id) on delete cascade;
