-- 0017 — Via assinada devolvida por e-mail
-- Cada documento enviado ganha uma REFERÊNCIA curta (FSCDOC-xxxxxxxx) que
-- viaja no assunto do e-mail. Quando o cliente responde com o arquivo em
-- anexo, é por ela que a plataforma sabe a qual caso aquilo pertence.
alter table documentos_assinatura add column if not exists email_token text;
create unique index if not exists idx_docassin_email_token
  on documentos_assinatura (email_token) where email_token is not null;
comment on column documentos_assinatura.email_token is
  'Referência FSCDOC-xxxxxxxx usada no assunto do e-mail para casar a resposta do cliente';
