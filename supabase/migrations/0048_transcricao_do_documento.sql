-- 0048 — o que está escrito no arquivo que o cliente mandou.
--
-- Até aqui o documento enviado era um arquivo guardado: alguém do
-- escritório precisava abrir, ler e digitar o que estava nele. Na
-- prática isso significava que uma foto do RG do fiador enviada às
-- 23h só virava informação no dia seguinte, e o relógio do prazo
-- ficava parado essa noite inteira por causa de um dado que já
-- estava na mão de todo mundo.
--
-- Agora o atendimento lê o arquivo assim que ele chega, transcreve o
-- que está legível e entrega a transcrição para quem sabe casar cada
-- dado com a pendência que o esperava.
--
-- A transcrição fica guardada, e não só usada, por dois motivos. O
-- primeiro é auditoria: quem abrir a pasta vê o que o sistema
-- entendeu do documento, e pode discordar. O segundo é custo: sem
-- guardar, qualquer reprocessamento leria o arquivo de novo.

alter table public.pedidos_documentos
  add column if not exists transcricao   text,
  add column if not exists transcrito_em timestamptz;

comment on column public.pedidos_documentos.transcricao is
  'O que está escrito no arquivo, lido na chegada. Serve para '
  'preencher o que faltava e para conferência humana depois.';

comment on column public.pedidos_documentos.transcrito_em is
  'Quando o arquivo foi lido. Nulo significa não lido: formato não '
  'suportado, arquivo grande demais ou falha na leitura. O arquivo '
  'continua guardado e o operador continua podendo abrir.';

create index if not exists idx_documentos_nao_lidos
  on public.pedidos_documentos(pedido_id)
  where transcrito_em is null;
