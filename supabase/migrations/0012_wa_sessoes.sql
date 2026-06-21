-- 0012 — Módulo 1: histórico/sessão de conversas do WhatsApp (omnichannel)
-- O "cliente/sessão" reaproveita a tabela 'clientes' (lookup por whatsapp).
-- Aqui guardamos o LOG da conversa por número, para dar contexto à IA.
create table if not exists wa_mensagens (
  id        bigint generated always as identity primary key,
  numero    text not null,
  autor     text not null,            -- CLIENTE | AGENTE
  conteudo  text not null,
  criado_em timestamptz not null default now()
);
create index if not exists idx_wa_msg_numero on wa_mensagens (numero, criado_em);
