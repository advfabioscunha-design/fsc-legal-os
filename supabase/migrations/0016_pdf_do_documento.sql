-- 0016 — PDF do documento enviado ao cliente
-- O .docx continua sendo a peça de trabalho do escritório (editável);
-- o cliente recebe o PDF, que preserva a formatação e não pode ser
-- alterado sem deixar rastro.
alter table documentos_assinatura add column if not exists pdf_path text;
comment on column documentos_assinatura.pdf_path is
  'PDF gerado do .docx no momento do envio ao cliente (LibreOffice)';
