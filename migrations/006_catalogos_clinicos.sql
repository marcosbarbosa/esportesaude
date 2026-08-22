-- =============================================================================
-- IMBRA — Fase 1: Catálogo Clínico Estruturado
-- Execute no Supabase Dashboard → SQL Editor.
--
-- GARANTIAS DESTA MIGRATION
-- - Não altera nem remove problemas_saude, restricoes_fisicas ou tags_saude.
-- - Não migra nem interpreta textos clínicos legados.
-- - Não usa ON DELETE CASCADE em vínculos clínicos.
-- - Pode ser executada mais de uma vez sem recriar objetos existentes.
--
-- REVERSÃO
-- O rollback documentado está no final deste arquivo. Não o execute se já
-- existirem vínculos ou histórico de auditoria, pois a reversão deve ser uma
-- decisão administrativa consciente e nunca apagar dados clínicos em uso.
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- Catálogos administráveis
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS catalogo_condicoes_clinicas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo          TEXT NOT NULL,
    nome_padrao     TEXT NOT NULL,
    categoria       TEXT NOT NULL,
    grupo           TEXT NOT NULL DEFAULT 'Não especificado',
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_catalogo_condicoes_codigo UNIQUE (codigo),
    CONSTRAINT ck_catalogo_condicoes_codigo_nao_vazio
        CHECK (length(btrim(codigo)) > 0),
    CONSTRAINT ck_catalogo_condicoes_nome_nao_vazio
        CHECK (length(btrim(nome_padrao)) > 0),
    CONSTRAINT ck_catalogo_condicoes_categoria
        CHECK (
            categoria IN (
                'CARDIOVASCULAR',
                'MUSCULOESQUELETICA',
                'METABOLICA',
                'NEUROLOGICA',
                'RISCO_FUNCIONAL',
                'OUTRA'
            )
        )
);

CREATE TABLE IF NOT EXISTS catalogo_restricoes_movimento (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo          TEXT NOT NULL,
    nome_padrao     TEXT NOT NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_catalogo_restricoes_codigo UNIQUE (codigo),
    CONSTRAINT ck_catalogo_restricoes_codigo_nao_vazio
        CHECK (length(btrim(codigo)) > 0),
    CONSTRAINT ck_catalogo_restricoes_nome_nao_vazio
        CHECK (length(btrim(nome_padrao)) > 0)
);

CREATE TABLE IF NOT EXISTS catalogo_adaptacoes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo          TEXT NOT NULL,
    nome_padrao     TEXT NOT NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_catalogo_adaptacoes_codigo UNIQUE (codigo),
    CONSTRAINT ck_catalogo_adaptacoes_codigo_nao_vazio
        CHECK (length(btrim(codigo)) > 0),
    CONSTRAINT ck_catalogo_adaptacoes_nome_nao_vazio
        CHECK (length(btrim(nome_padrao)) > 0)
);

-- -----------------------------------------------------------------------------
-- Vínculos clínicos. Estes registros são novos e não fazem leitura, conversão
-- nem alteração de qualquer campo legado do aluno.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS aluno_condicoes_clinicas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id                UUID NOT NULL REFERENCES alunos(id) ON DELETE RESTRICT,
    condicao_id             UUID NOT NULL REFERENCES catalogo_condicoes_clinicas(id) ON DELETE RESTRICT,
    status                  TEXT NOT NULL DEFAULT 'NAO_INFORMADO',
    fonte_informacao        TEXT NOT NULL DEFAULT 'CADASTRO_MANUAL',
    data_registro           DATE,
    observacao_contextual   TEXT,
    status_revisao          TEXT NOT NULL DEFAULT 'PENDENTE',
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por              TEXT,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_aluno_condicoes_status
        CHECK (status IN ('ATIVA', 'HISTORICO', 'NAO_INFORMADO')),
    CONSTRAINT ck_aluno_condicoes_fonte
        CHECK (
            fonte_informacao IN (
                'CADASTRO_MANUAL',
                'DECLARACAO_ALUNO',
                'DOCUMENTO_MEDICO',
                'REGISTRO_LEGADO',
                'OUTRA'
            )
        ),
    CONSTRAINT ck_aluno_condicoes_revisao
        CHECK (
            status_revisao IN (
                'PENDENTE',
                'SUGERIDO',
                'CONFIRMADO',
                'REJEITADO',
                'OBSOLETO'
            )
        )
);

CREATE TABLE IF NOT EXISTS aluno_restricoes_fisicas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id                UUID NOT NULL REFERENCES alunos(id) ON DELETE RESTRICT,
    restricao_id            UUID NOT NULL REFERENCES catalogo_restricoes_movimento(id) ON DELETE RESTRICT,
    regiao_corporal         TEXT,
    lado                    TEXT,
    nivel_orientacao        TEXT NOT NULL DEFAULT 'MONITORAR',
    fonte_informacao        TEXT NOT NULL DEFAULT 'CADASTRO_MANUAL',
    status_revisao          TEXT NOT NULL DEFAULT 'PENDENTE',
    observacao_original     TEXT,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por              TEXT,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_aluno_restricoes_lado
        CHECK (lado IS NULL OR lado IN ('DIREITO', 'ESQUERDO', 'BILATERAL', 'NAO_INFORMADO')),
    CONSTRAINT ck_aluno_restricoes_orientacao
        CHECK (nivel_orientacao IN ('EVITAR', 'REDUZIR', 'ADAPTAR', 'MONITORAR', 'SEM_RESTRICAO')),
    CONSTRAINT ck_aluno_restricoes_fonte
        CHECK (
            fonte_informacao IN (
                'CADASTRO_MANUAL',
                'DECLARACAO_ALUNO',
                'DOCUMENTO_MEDICO',
                'REGISTRO_LEGADO',
                'OUTRA'
            )
        ),
    CONSTRAINT ck_aluno_restricoes_revisao
        CHECK (
            status_revisao IN (
                'PENDENTE',
                'SUGERIDO',
                'CONFIRMADO',
                'REJEITADO',
                'OBSOLETO'
            )
        )
);

-- -----------------------------------------------------------------------------
-- Auditoria. O operador é armazenado como identificador textual porque o modelo
-- atual de usuários pode variar entre instalações. O registro sobrevive a uma
-- eventual exclusão administrativa do aluno, sem apagar o histórico.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS historico_revisoes_clinicas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id            UUID REFERENCES alunos(id) ON DELETE SET NULL,
    entidade            TEXT NOT NULL,
    registro_id         UUID,
    acao                TEXT NOT NULL,
    valor_anterior      JSONB,
    valor_novo          JSONB,
    operador            TEXT NOT NULL DEFAULT 'Sistema',
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_historico_revisoes_entidade
        CHECK (
            entidade IN (
                'CATALOGO_CONDICAO',
                'CATALOGO_RESTRICAO',
                'CATALOGO_ADAPTACAO',
                'ALUNO_CONDICAO',
                'ALUNO_RESTRICAO'
            )
        ),
    CONSTRAINT ck_historico_revisoes_acao
        CHECK (acao IN ('CRIACAO', 'ATUALIZACAO', 'ATIVACAO', 'INATIVACAO', 'REVISAO'))
);

-- -----------------------------------------------------------------------------
-- Índices e prevenção de duplicidade para vínculos ativos.
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_catalogo_condicoes_ativos
    ON catalogo_condicoes_clinicas (ativo, categoria, grupo);

CREATE INDEX IF NOT EXISTS idx_catalogo_restricoes_ativos
    ON catalogo_restricoes_movimento (ativo);

CREATE INDEX IF NOT EXISTS idx_catalogo_adaptacoes_ativos
    ON catalogo_adaptacoes (ativo);

CREATE INDEX IF NOT EXISTS idx_aluno_condicoes_aluno
    ON aluno_condicoes_clinicas (aluno_id);

CREATE INDEX IF NOT EXISTS idx_aluno_restricoes_aluno
    ON aluno_restricoes_fisicas (aluno_id);

CREATE INDEX IF NOT EXISTS idx_historico_revisoes_clinicas_aluno
    ON historico_revisoes_clinicas (aluno_id, criado_em DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_aluno_condicao_ativa
    ON aluno_condicoes_clinicas (aluno_id, condicao_id)
    WHERE ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_aluno_restricao_ativa
    ON aluno_restricoes_fisicas (aluno_id, restricao_id, COALESCE(regiao_corporal, ''), COALESCE(lado, ''))
    WHERE ativo = TRUE;

-- -----------------------------------------------------------------------------
-- Atualização consistente de timestamps.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION atualizar_data_catalogo_clinico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_catalogo_condicoes_atualizado_em ON catalogo_condicoes_clinicas;
CREATE TRIGGER trg_catalogo_condicoes_atualizado_em
BEFORE UPDATE ON catalogo_condicoes_clinicas
FOR EACH ROW EXECUTE FUNCTION atualizar_data_catalogo_clinico();

DROP TRIGGER IF EXISTS trg_catalogo_restricoes_atualizado_em ON catalogo_restricoes_movimento;
CREATE TRIGGER trg_catalogo_restricoes_atualizado_em
BEFORE UPDATE ON catalogo_restricoes_movimento
FOR EACH ROW EXECUTE FUNCTION atualizar_data_catalogo_clinico();

DROP TRIGGER IF EXISTS trg_catalogo_adaptacoes_atualizado_em ON catalogo_adaptacoes;
CREATE TRIGGER trg_catalogo_adaptacoes_atualizado_em
BEFORE UPDATE ON catalogo_adaptacoes
FOR EACH ROW EXECUTE FUNCTION atualizar_data_catalogo_clinico();

DROP TRIGGER IF EXISTS trg_aluno_condicoes_atualizado_em ON aluno_condicoes_clinicas;
CREATE TRIGGER trg_aluno_condicoes_atualizado_em
BEFORE UPDATE ON aluno_condicoes_clinicas
FOR EACH ROW EXECUTE FUNCTION atualizar_data_catalogo_clinico();

DROP TRIGGER IF EXISTS trg_aluno_restricoes_atualizado_em ON aluno_restricoes_fisicas;
CREATE TRIGGER trg_aluno_restricoes_atualizado_em
BEFORE UPDATE ON aluno_restricoes_fisicas
FOR EACH ROW EXECUTE FUNCTION atualizar_data_catalogo_clinico();

ALTER TABLE catalogo_condicoes_clinicas DISABLE ROW LEVEL SECURITY;
ALTER TABLE catalogo_restricoes_movimento DISABLE ROW LEVEL SECURITY;
ALTER TABLE catalogo_adaptacoes DISABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_condicoes_clinicas DISABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_restricoes_fisicas DISABLE ROW LEVEL SECURITY;
ALTER TABLE historico_revisoes_clinicas DISABLE ROW LEVEL SECURITY;

COMMIT;

-- =============================================================================
-- ROLLBACK DOCUMENTADO — NÃO EXECUTAR AUTOMATICAMENTE
--
-- Antes de uma reversão, confirme que as tabelas de vínculo e auditoria estão
-- vazias. A migration não fornece um rollback que descarte dados clínicos.
--
-- BEGIN;
-- DROP TABLE IF EXISTS historico_revisoes_clinicas;
-- DROP TABLE IF EXISTS aluno_restricoes_fisicas;
-- DROP TABLE IF EXISTS aluno_condicoes_clinicas;
-- DROP TABLE IF EXISTS catalogo_adaptacoes;
-- DROP TABLE IF EXISTS catalogo_restricoes_movimento;
-- DROP TABLE IF EXISTS catalogo_condicoes_clinicas;
-- DROP FUNCTION IF EXISTS atualizar_data_catalogo_clinico();
-- COMMIT;
-- =============================================================================