-- 0026 — atendimento telepresencial: sala, consentimento, áudio e transcrição.
--
-- O QUE FICA GUARDADO, E O QUE NÃO FICA
-- O vídeo existe apenas ao vivo, para o atendimento ser humano: ninguém
-- grava imagem, e não há arquivo de vídeo em lugar nenhum. O que se
-- conserva é a VOZ (um .m4a) e o TEXTO da conversa, anexados ao caso como
-- registro do atendimento.
--
-- A transcrição é registro, não fonte de cadastro. Os dados que vão para
-- contrato e procuração continuam vindo dos documentos, da conversa escrita
-- ou do lançamento direto — CPF ouvido em áudio erra, e um dígito errado
-- invalida o instrumento.
--
-- CONSENTIMENTO
-- Consulta inicial é coberta pelo sigilo profissional (EAOAB art. 34, VII),
-- e a LGPD se aplica pelo local do titular, não do servidor. Por isso o
-- aceite fica gravado com data, hora, IP e o texto exato que foi mostrado:
-- se amanhã se discutir o que o cliente autorizou, a resposta está aqui, e
-- não na memória de ninguém. Sem aceite, a sala abre — mas sem gravar.

create table if not exists public.atendimentos (
  id                uuid primary key default gen_random_uuid(),
  caso_id           uuid not null references public.casos(id) on delete cascade,
  cliente_id        uuid references public.clientes(id) on delete set null,

  -- sala
  sala_nome         text not null,
  sala_url          text not null,
  expira_em         timestamptz,

  -- consentimento do cliente (antes de entrar)
  consentimento_em      timestamptz,
  consentimento_ip      text,
  consentimento_texto   text,          -- o texto exato que ele leu
  consentimento_versao  text,

  -- execução
  status            text not null default 'AGENDADO',
                    -- AGENDADO | EM_ANDAMENTO | GRAVANDO | ENCERRADO |
                    -- TRANSCRITO | FALHOU
  iniciado_em       timestamptz,
  encerrado_em      timestamptz,
  duracao_segundos  integer,

  -- o que fica: áudio e texto
  gravacao_id       text,              -- id da gravação no provedor
  audio_path        text,              -- .m4a na pasta do caso
  transcricao       text,
  transcrito_em     timestamptz,
  erro              text,

  observacao        text,              -- nota do advogado sobre o atendimento
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now()
);

create index if not exists idx_atendimentos_caso
  on public.atendimentos(caso_id, criado_em desc);
create index if not exists idx_atendimentos_sala
  on public.atendimentos(sala_nome);
create index if not exists idx_atendimentos_gravacao
  on public.atendimentos(gravacao_id) where gravacao_id is not null;

alter table public.atendimentos enable row level security;

-- o escritório enxerga tudo
drop policy if exists atendimentos_escritorio on public.atendimentos;
create policy atendimentos_escritorio on public.atendimentos
  for all to authenticated
  using (public.meu_papel() = 'OPERADOR')
  with check (public.meu_papel() = 'OPERADOR');

-- o cliente enxerga apenas os atendimentos dos próprios casos, e só os
-- campos que o painel mostra (a transcrição não é exposta a ele por aqui:
-- o acesso do cliente passa pela API, que decide o que devolver)
drop policy if exists atendimentos_cliente on public.atendimentos;
create policy atendimentos_cliente on public.atendimentos
  for select to authenticated
  using (
    exists (
      select 1 from public.casos c
      join public.clientes cl on cl.id = c.cliente_id
      where c.id = atendimentos.caso_id
        and cl.auth_user_id = auth.uid()
    )
  );
