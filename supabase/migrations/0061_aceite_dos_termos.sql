-- ACEITE DOS TERMOS DE USO E DA POLÍTICA DE PRIVACIDADE
--
-- A caixa marcada na tela não vale nada se não deixar rastro. O que dá
-- valor ao aceite é poder dizer, depois, QUANDO e QUAL VERSÃO a pessoa
-- aceitou — porque o documento muda, e aceite sem versão é aceite de
-- texto nenhum.
--
-- Por isso são três colunas e não uma caixa de "sim": o instante, a
-- versão do texto vigente naquele instante e o endereço de origem.
-- Guardar o IP junto com o registro é o que o Marco Civil espera de
-- quem precisa comprovar um ato praticado na internet.
--
-- Os dois documentos têm colunas separadas de propósito. Eles mudam em
-- datas diferentes, e quando a Política de Privacidade for atualizada é
-- só ela que precisa de novo aceite.

alter table public.clientes
  add column if not exists aceite_termos_em        timestamptz,
  add column if not exists aceite_termos_versao    text,
  add column if not exists aceite_privacidade_em   timestamptz,
  add column if not exists aceite_privacidade_versao text,
  add column if not exists aceite_origem_ip        text;

comment on column public.clientes.aceite_termos_em is
  'Instante em que o cliente aceitou os Termos de Uso, no primeiro acesso.';
comment on column public.clientes.aceite_termos_versao is
  'Versão (data) do texto dos Termos vigente no momento do aceite.';
comment on column public.clientes.aceite_privacidade_em is
  'Instante em que o cliente aceitou a Política de Privacidade.';
comment on column public.clientes.aceite_privacidade_versao is
  'Versão (data) da Política de Privacidade vigente no momento do aceite.';
comment on column public.clientes.aceite_origem_ip is
  'Endereço de origem do aceite, para comprovação do ato (Lei 12.965/2014).';

-- Quem ainda não aceitou é encontrado por aqui, para a revalidação
-- quando os textos mudarem.
create index if not exists clientes_sem_aceite
  on public.clientes (aceite_termos_em)
  where aceite_termos_em is null;
