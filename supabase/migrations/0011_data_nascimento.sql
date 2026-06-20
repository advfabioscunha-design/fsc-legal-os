-- 0011 — Data de nascimento do cliente (Agente de Relacionamento / aniversários)
alter table clientes add column if not exists data_nascimento date;
