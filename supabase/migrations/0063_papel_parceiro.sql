-- ════════════════════════════════════════════════════════════════
-- O PAPEL PARCEIRO NO ENUM
-- ════════════════════════════════════════════════════════════════
--
-- `perfis.papel` não é texto livre: é o tipo `papel_usuario`, um enum
-- que nasceu com CLIENTE e OPERADOR, e ganhou ADMIN na migração 0027.
--
-- Eu escrevi o código do parceiro gravando papel = 'PARCEIRO' sem notar
-- isso. O upsert teria falhado no primeiro advogado que se cadastrasse —
-- e falhado de um jeito ruim: o registro em `parceiros` já estaria
-- criado, mas a pessoa continuaria sendo CLIENTE aos olhos do sistema,
-- caindo na área do cliente a cada login sem entender por quê.
--
-- Encontrado ao conferir as colunas de `perfis` antes de escrever a
-- tela. É o tipo de coisa que só aparece quando se lê o esquema em vez
-- de confiar na memória.
--
-- Por que uma migração separada: `alter type ... add value` não pode
-- rodar dentro de um bloco de transação junto com o uso do valor novo
-- em algumas versões do PostgreSQL. Isolada, ela é aplicada antes e o
-- resto do sistema já encontra o valor disponível.

alter type papel_usuario add value if not exists 'PARCEIRO';

comment on type papel_usuario is
  'CLIENTE — área do cliente. PARCEIRO — advogado de fora, vê só os '
  'casos em que há parceria viva dele. OPERADOR — equipe do escritório. '
  'ADMIN — equipe, e o único que concede ou retira acesso.';
