-- 0019 — Envio de vários documentos de uma vez
-- Quando contrato, procuração e declaração vão no mesmo e-mail, todos
-- compartilham a MESMA referência (FSCDOC-xxxxxxxx). Por isso o índice do
-- token deixa de ser único.
drop index if exists idx_docassin_email_token;
create index if not exists idx_docassin_email_token
  on documentos_assinatura (email_token) where email_token is not null;

alter table documentos_assinatura add column if not exists lote_id uuid;
comment on column documentos_assinatura.lote_id is
  'Agrupa os documentos enviados juntos no mesmo e-mail';
