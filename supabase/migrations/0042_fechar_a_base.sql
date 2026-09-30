-- 0042 — fechar a base.
--
-- O PROBLEMA
--
-- No Supabase, tabela sem RLS ligada é tabela aberta a quem tiver a
-- chave anônima. E a chave anônima é publicada de propósito: ela vai
-- dentro do JavaScript do site, porque é assim que o navegador do
-- cliente conversa com o banco. Qualquer visitante abre as ferramentas
-- do navegador e a tem em dez segundos. É por isso que ela se chama
-- anônima: ela não protege nada, quem protege é o RLS.
--
-- Vinte e uma das trinta e sete tabelas estavam sem RLS. Entre elas:
-- pedidos_contrato (nome, e-mail, valor e a conversa da negociação de
-- cada cliente), prazos, intimações, tarefas, anotações, membros da
-- equipe, mensagens de WhatsApp, e a folha e os lançamentos
-- financeiros do escritório.
--
-- POR QUE ISTO NÃO QUEBRA NADA
--
-- Ligar o RLS sem criar política nenhuma bloqueia todo mundo, exceto a
-- chave de serviço, que ignora RLS por definição. E a chave de serviço
-- é justamente a que o backend usa: ela vive só no servidor, dentro do
-- .env, e nunca sai de lá.
--
-- O site inteiro faz uma única consulta direta ao banco, em `perfis`,
-- que já tinha RLS com política própria. Todo o resto passa pela API.
-- Então o efeito prático desta migração é fechar a porta dos fundos e
-- deixar a da frente exatamente como estava.
--
-- O QUE ISTO NÃO RESOLVE
--
-- A API continua sem autenticação: 234 rotas abertas a quem souber o
-- endereço. Isso é outro trabalho, maior, e precisa ser feito. Esta
-- migração fecha o acesso direto ao banco, que é o caminho mais curto
-- e o que dá acesso a tudo de uma vez.

alter table public.agenda_convidados     enable row level security;
alter table public.agenda_dias_fechados  enable row level security;
alter table public.agenda_itens          enable row level security;
alter table public.agenda_notas          enable row level security;
alter table public.anotacoes             enable row level security;
alter table public.fin_folha             enable row level security;
alter table public.fin_lancamentos       enable row level security;
alter table public.intimacoes            enable row level security;
alter table public.lixeira               enable row level security;
alter table public.membros_equipe        enable row level security;
alter table public.monitoramentos        enable row level security;
alter table public.pedidos_ciencias      enable row level security;
alter table public.pedidos_contrato      enable row level security;
alter table public.pedidos_documentos    enable row level security;
alter table public.pedidos_mensagens     enable row level security;
alter table public.prazos                enable row level security;
alter table public.promocoes_equipe      enable row level security;
alter table public.radar_jurimetrico     enable row level security;
alter table public.solicitacoes_acesso   enable row level security;
alter table public.tarefas               enable row level security;
alter table public.wa_mensagens          enable row level security;

-- Sem política nenhuma abaixo, e isso é a decisão, não o esquecimento.
-- Política é permissão; a ausência delas é a negativa. Quando alguma
-- tela precisar ler direto do banco, a política nasce ali, restrita
-- àquela leitura, e não como uma porta larga criada por antecipação.
