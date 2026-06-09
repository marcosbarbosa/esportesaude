-- IMBRA — Migração: tabela de pacotes de Email BI
-- Execute no Supabase Dashboard → SQL Editor
-- URL: https://supabase.com/dashboard/project/<seu-projeto>/sql/new

CREATE TABLE IF NOT EXISTS email_bi_schedules (
  id               uuid         DEFAULT gen_random_uuid() PRIMARY KEY,
  nome             text         NOT NULL DEFAULT 'Pacote Principal',
  habilitado       boolean      NOT NULL DEFAULT false,
  frequencia       text         NOT NULL DEFAULT 'semanal',
  dia_semana       integer      NOT NULL DEFAULT 4,
  dia_mes          integer      NOT NULL DEFAULT 1,
  emails_destino   jsonb        NOT NULL DEFAULT '[]'::jsonb,
  modulos          jsonb        NOT NULL DEFAULT '{}'::jsonb,
  assunto_extra    text                  DEFAULT '',
  email_remetente  text                  DEFAULT '',
  email_senha_app  text                  DEFAULT '',
  base_url         text                  DEFAULT '',
  proximo_envio    date,
  ultimo_envio     timestamptz,
  total_envios     integer      NOT NULL DEFAULT 0,
  historico_envios jsonb        NOT NULL DEFAULT '[]'::jsonb,
  criado_em        timestamptz  NOT NULL DEFAULT now(),
  atualizado_em    timestamptz  NOT NULL DEFAULT now()
);
