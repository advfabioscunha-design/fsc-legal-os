-- 0023 — os estados novos da régua entram no enum da jornada.
--
-- casos.estado é do tipo estado_jornada. Sem estes três valores, o caso não
-- consegue sair da esteira de produção quando fica esperando o cliente.

alter type estado_jornada add value if not exists 'AGUARDANDO_DOCUMENTOS';
alter type estado_jornada add value if not exists 'PRONTO_PARA_ANALISE';
alter type estado_jornada add value if not exists 'LEAD_FRIO';
