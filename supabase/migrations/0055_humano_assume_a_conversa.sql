-- 0055 — quando o humano entra, o agente sai; e volta sozinho.
--
-- O agente de atendimento responde o cliente em segundos, o que é bom
-- quase sempre e é péssimo na hora em que alguém do escritório decide
-- assumir a conversa. Os dois escrevendo ao mesmo tempo produzem o
-- efeito mais constrangedor que um atendimento pode ter: a pessoa
-- explica o caso com cuidado, e logo abaixo o agente responde outra
-- coisa, contradizendo ou repetindo. O cliente vê dois atendentes que
-- não se falam.
--
-- Bastava um botão de "assumir", e a experiência diz que ninguém
-- clica: quem está com pressa de responder, responde. Então o próprio
-- ato de escrever é que assume. Mandar uma mensagem como escritório
-- cala o agente.
--
-- E DEVOLVE SOZINHO, PORQUE NINGUÉM LEMBRA DE DEVOLVER
--
-- O silêncio do agente não pode ser permanente: quem assumiu sai para
-- uma audiência e esquece, e o cliente que escrever de madrugada fica
-- sem resposta até alguém lembrar. Cinco minutos sem o humano falar e
-- o agente retoma.
--
-- A conta é do servidor, com `humano_em`, e não de um relógio na tela:
-- a aba fechada, a página recarregada ou a troca de quem está
-- atendendo não podem mudar quem está no comando.
--
-- `cliente_digitando_em` existe para o outro lado da mesma necessidade:
-- quem acompanha precisa saber que o cliente está escrevendo agora,
-- para esperar a frase inteira antes de responder — ou para ver que
-- vale a pena assumir. É um carimbo que a tela do cliente renova
-- enquanto ele digita, e que vale por poucos segundos.

alter table public.pedidos_contrato
  add column if not exists humano_em            timestamptz,
  add column if not exists humano_quem          text,
  add column if not exists cliente_digitando_em timestamptz;

comment on column public.pedidos_contrato.humano_em is
  'Quando alguém do escritório falou com o cliente pela última vez. '
  'Enquanto estiver a menos de cinco minutos, o agente não responde: '
  'a conversa é de quem assumiu.';

comment on column public.pedidos_contrato.humano_quem is
  'Quem assumiu a conversa. Serve ao histórico e a quem abre o pedido '
  'depois e precisa saber com quem falar antes de escrever.';

comment on column public.pedidos_contrato.cliente_digitando_em is
  'Último sinal de que o cliente está escrevendo. Renovado pela tela '
  'dele enquanto digita; vale por poucos segundos.';

-- Os pedidos onde alguém do escritório está no comando agora. É a
-- consulta que a tela faz a cada poucos segundos, e ela não pode
-- varrer a tabela inteira.
create index if not exists idx_pedidos_humano_em
  on public.pedidos_contrato(humano_em desc)
  where humano_em is not null and excluido_em is null;
