-- 0039 — o rito do balcão na ordem em que as coisas realmente acontecem.
--
-- Três correções de ordem, e todas vêm do mesmo erro: o sistema pedia
-- ao cliente coisas que só fazem sentido depois que ele decidiu comprar.
--
-- 1. TIMBRE NA HORA CERTA
--    A escolha entre papel timbrado e folha branca aparecia na primeira
--    tela, junto com a lista de documentos. Ali a pessoa ainda não sabe
--    quanto custa nem se vai contratar, e a pergunta não significa
--    nada. Passa para depois do pagamento, quando o escritório já está
--    montando o documento dela. `com_timbre` continua existindo e
--    continua com default true; o que muda é `timbre_escolhido`, que
--    diz se a pessoa de fato escolheu ou se o valor é o padrão.
--
-- 2. O SERVIÇO QUE NÃO ESTÁ NA LISTA
--    O catálogo tem dez tipos. Quem precisa do décimo primeiro batia
--    numa parede: nenhum campo para dizer o que queria. Agora diz, em
--    texto livre, e o atendimento segue normalmente. O escritório lê e
--    decide se atende, e a lista dos pedidos que chegaram por aqui é a
--    melhor fonte que existe sobre qual deve ser o próximo tipo do
--    catálogo.
--
-- 3. O PDF ANTES DO CLIENTE
--    O advogado aprovava a minuta e ela ia direto para o cliente como
--    texto. Ninguém via a página montada. Agora a aprovação gera o PDF,
--    o advogado abre, confere o layout e só então libera. São dois
--    momentos distintos e cada um tem a sua marca de tempo.

alter table public.pedidos_contrato
  add column if not exists servico_livre     text,
  add column if not exists timbre_escolhido  boolean not null default false,
  add column if not exists pdf_gerado_em     timestamptz,
  add column if not exists visto_advogado_em timestamptz,
  add column if not exists visto_advogado_por text,
  add column if not exists excluido_em       timestamptz,
  add column if not exists excluido_por      text,
  add column if not exists excluido_motivo   text;

comment on column public.pedidos_contrato.servico_livre is
  'O que o cliente digitou quando não achou o serviço na lista. Com '
  'tipo OUTRO, é a única descrição que existe do pedido, e é por ela '
  'que o escritório decide se atende.';

comment on column public.pedidos_contrato.timbre_escolhido is
  'Se o cliente chegou a escolher. Falso significa que com_timbre está '
  'no padrão porque ninguém perguntou ainda.';

comment on column public.pedidos_contrato.visto_advogado_em is
  'Quando o advogado abriu o PDF e conferiu como a página ficou. A '
  'aprovação do texto e a conferência do layout são coisas diferentes: '
  'texto correto em página torta chega torto ao cliente.';

comment on column public.pedidos_contrato.excluido_em is
  'Exclusão é lógica, não física. Pedido apagado de verdade levaria '
  'junto a conversa, o comprovante de pagamento e a ciência registrada, '
  'que são justamente as provas de que o escritório precisa se o '
  'cliente reclamar depois.';

-- A esteira do operador nunca deve mostrar o que foi excluído, e essa
-- consulta roda a cada abertura da tela.
create index if not exists idx_pedidos_vivos
  on public.pedidos_contrato(fase)
  where excluido_em is null;


-- ── O recado do escritório e por onde ele saiu ──────────────────
--
-- A tabela de mensagens do pedido guardava só o texto. Quando o cliente
-- diz "ninguém me avisou", o que resolve a conversa é saber por quais
-- canais aquilo saiu e se o envio deu certo — não a mensagem em si.
alter table public.pedidos_mensagens
  add column if not exists canais       text[],
  add column if not exists email_em     timestamptz,
  add column if not exists whatsapp_em  timestamptz,
  add column if not exists falha        text;

comment on column public.pedidos_mensagens.canais is
  'PLATAFORMA, EMAIL, WHATSAPP. A plataforma é sempre garantida porque '
  'a mensagem é a própria linha desta tabela. Os outros dois dependem '
  'de o cliente ter e-mail e telefone cadastrados.';
