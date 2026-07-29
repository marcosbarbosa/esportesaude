-- IMBRA — Migração: Sistema de Ações Voluntariadas
-- Execute no Supabase Dashboard → SQL Editor (UMA VEZ)

-- 1. Tabela de definições de ações voluntariadas
CREATE TABLE IF NOT EXISTS acoes_voluntariado (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT NOT NULL,
    descricao   TEXT,
    area        TEXT NOT NULL DEFAULT 'Geral',
    icone       TEXT NOT NULL DEFAULT '🤝',
    cor         TEXT NOT NULL DEFAULT '#059669',
    ativa       BOOLEAN NOT NULL DEFAULT true,
    ordem       INT NOT NULL DEFAULT 99,
    criado_em   TIMESTAMPTZ DEFAULT now()
);

-- 2. Tabela de vínculos aluno ↔ ação (many-to-many)
CREATE TABLE IF NOT EXISTS aluno_acoes_voluntariado (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id        TEXT NOT NULL,
    acao_id         UUID NOT NULL REFERENCES acoes_voluntariado(id) ON DELETE CASCADE,
    data_inscricao  DATE DEFAULT CURRENT_DATE,
    obs             TEXT,
    criado_em       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(aluno_id, acao_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_aluno_acoes_aluno_id
    ON aluno_acoes_voluntariado (aluno_id);

CREATE INDEX IF NOT EXISTS idx_aluno_acoes_acao_id
    ON aluno_acoes_voluntariado (acao_id);
