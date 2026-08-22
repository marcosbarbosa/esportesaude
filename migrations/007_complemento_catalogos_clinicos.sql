-- =============================================================================
-- IMBRA — Fase 1 (complemento): Catálogo Clínico Estruturado
--
-- Pré-requisito: migrations/006_catalogos_clinicos.sql já aplicada.
--
-- Esta migration é complementar, idempotente e não destrutiva:
--   - não faz DROP TABLE;
--   - não atualiza alunos nem campos legados;
--   - não altera problemas_saude, restricoes_fisicas ou tags_saude;
--   - não cria políticas RLS públicas;
--   - não executa seed.
--
-- Execute somente após revisão e backup aprovado no Supabase SQL Editor.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Catálogos: campos operacionais e de governança
-- -----------------------------------------------------------------------------

ALTER TABLE catalogo_condicoes_clinicas
    ADD COLUMN IF NOT EXISTS descricao_operacional TEXT,
    ADD COLUMN IF NOT EXISTS exige_revisao_periodica BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS intervalo_revisao_dias INTEGER,
    ADD COLUMN IF NOT EXISTS revisado_por TEXT,
    ADD COLUMN IF NOT EXISTS revisado_em TIMESTAMPTZ;

ALTER TABLE catalogo_restricoes_movimento
    ADD COLUMN IF NOT EXISTS categoria_movimento TEXT,
    ADD COLUMN IF NOT EXISTS descricao_simples_para_aluno TEXT,
    ADD COLUMN IF NOT EXISTS exige_validacao_clinica BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS nivel_padrao_sugerido TEXT,
    ADD COLUMN IF NOT EXISTS revisado_por TEXT,
    ADD COLUMN IF NOT EXISTS revisado_em TIMESTAMPTZ;

ALTER TABLE catalogo_adaptacoes
    ADD COLUMN IF NOT EXISTS categoria_adaptacao TEXT,
    ADD COLUMN IF NOT EXISTS descricao_operacional TEXT,
    ADD COLUMN IF NOT EXISTS descricao_simples_para_aluno TEXT,
    ADD COLUMN IF NOT EXISTS revisado_por TEXT,
    ADD COLUMN IF NOT EXISTS revisado_em TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_catalogo_condicoes_intervalo_revisao'
          AND conrelid = 'catalogo_condicoes_clinicas'::regclass
    ) THEN
        ALTER TABLE catalogo_condicoes_clinicas
            ADD CONSTRAINT ck_catalogo_condicoes_intervalo_revisao
            CHECK (intervalo_revisao_dias IS NULL OR intervalo_revisao_dias > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_catalogo_restricoes_nivel_padrao'
          AND conrelid = 'catalogo_restricoes_movimento'::regclass
    ) THEN
        ALTER TABLE catalogo_restricoes_movimento
            ADD CONSTRAINT ck_catalogo_restricoes_nivel_padrao
            CHECK (
                nivel_padrao_sugerido IS NULL OR
                nivel_padrao_sugerido IN (
                    'EVITAR', 'REDUZIR', 'ADAPTAR', 'MONITORAR', 'SEM_RESTRICAO'
                )
            );
    END IF;
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. Condição individual e restrição individual
-- -----------------------------------------------------------------------------

ALTER TABLE aluno_condicoes_clinicas
    ADD COLUMN IF NOT EXISTS data_informacao DATE,
    ADD COLUMN IF NOT EXISTS data_revisao_prevista DATE,
    ADD COLUMN IF NOT EXISTS responsavel_validacao TEXT;

ALTER TABLE aluno_restricoes_fisicas
    ADD COLUMN IF NOT EXISTS condicao_aluno_id UUID,
    ADD COLUMN IF NOT EXISTS data_inicio DATE,
    ADD COLUMN IF NOT EXISTS data_validade DATE,
    ADD COLUMN IF NOT EXISTS responsavel_validacao TEXT,
    ADD COLUMN IF NOT EXISTS texto_original_legado TEXT,
    ADD COLUMN IF NOT EXISTS observacao_contextual TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_aluno_condicoes_id_aluno'
          AND conrelid = 'aluno_condicoes_clinicas'::regclass
    ) THEN
        ALTER TABLE aluno_condicoes_clinicas
            ADD CONSTRAINT uq_aluno_condicoes_id_aluno UNIQUE (id, aluno_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_aluno_restricoes_id_aluno'
          AND conrelid = 'aluno_restricoes_fisicas'::regclass
    ) THEN
        ALTER TABLE aluno_restricoes_fisicas
            ADD CONSTRAINT uq_aluno_restricoes_id_aluno UNIQUE (id, aluno_id);
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_aluno_restricoes_condicao_aluno'
          AND conrelid = 'aluno_restricoes_fisicas'::regclass
    ) THEN
        ALTER TABLE aluno_restricoes_fisicas
            ADD CONSTRAINT fk_aluno_restricoes_condicao_aluno
            FOREIGN KEY (condicao_aluno_id, aluno_id)
            REFERENCES aluno_condicoes_clinicas(id, aluno_id)
            ON DELETE RESTRICT;
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_aluno_restricoes_condicao_aluno_id
    ON aluno_restricoes_fisicas (condicao_aluno_id);

CREATE INDEX IF NOT EXISTS idx_aluno_restricoes_validade
    ON aluno_restricoes_fisicas (data_validade)
    WHERE ativo = TRUE;

-- -----------------------------------------------------------------------------
-- 3. Adaptações por aluno. Uma adaptação pode estar vinculada a uma restrição,
-- mas o vínculo é opcional para permitir orientação preventiva independente.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS aluno_adaptacoes_recomendadas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id                UUID NOT NULL,
    restricao_aluno_id      UUID,
    adaptacao_id            UUID NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'PENDENTE',
    observacao_operacional  TEXT,
    data_inicio             DATE,
    data_validade           DATE,
    revisado_por            TEXT,
    revisado_em             TIMESTAMPTZ,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por              TEXT,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_aluno_adaptacoes_aluno
        FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE RESTRICT,
    CONSTRAINT fk_aluno_adaptacoes_catalogo
        FOREIGN KEY (adaptacao_id) REFERENCES catalogo_adaptacoes(id) ON DELETE RESTRICT,
    CONSTRAINT ck_aluno_adaptacoes_status
        CHECK (status IN ('PENDENTE', 'VALIDADO', 'REJEITADO', 'EXPIRADO', 'REVOGADO'))
);

-- Garante a forma esperada se uma implantação anterior tiver criado a tabela
-- parcialmente. Não sobrescreve dados existentes.
ALTER TABLE aluno_adaptacoes_recomendadas
    ADD COLUMN IF NOT EXISTS restricao_aluno_id UUID,
    ADD COLUMN IF NOT EXISTS adaptacao_id UUID,
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PENDENTE',
    ADD COLUMN IF NOT EXISTS observacao_operacional TEXT,
    ADD COLUMN IF NOT EXISTS data_inicio DATE,
    ADD COLUMN IF NOT EXISTS data_validade DATE,
    ADD COLUMN IF NOT EXISTS revisado_por TEXT,
    ADD COLUMN IF NOT EXISTS revisado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_por TEXT,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_aluno_adaptacoes_aluno'
          AND conrelid = 'aluno_adaptacoes_recomendadas'::regclass
    ) THEN
        ALTER TABLE aluno_adaptacoes_recomendadas
            ADD CONSTRAINT fk_aluno_adaptacoes_aluno
            FOREIGN KEY (aluno_id)
            REFERENCES alunos(id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_aluno_adaptacoes_catalogo'
          AND conrelid = 'aluno_adaptacoes_recomendadas'::regclass
    ) THEN
        ALTER TABLE aluno_adaptacoes_recomendadas
            ADD CONSTRAINT fk_aluno_adaptacoes_catalogo
            FOREIGN KEY (adaptacao_id)
            REFERENCES catalogo_adaptacoes(id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_aluno_adaptacoes_status'
          AND conrelid = 'aluno_adaptacoes_recomendadas'::regclass
    ) THEN
        ALTER TABLE aluno_adaptacoes_recomendadas
            ADD CONSTRAINT ck_aluno_adaptacoes_status
            CHECK (status IN ('PENDENTE', 'VALIDADO', 'REJEITADO', 'EXPIRADO', 'REVOGADO'));
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_aluno_adaptacoes_restricao'
          AND conrelid = 'aluno_adaptacoes_recomendadas'::regclass
    ) THEN
        ALTER TABLE aluno_adaptacoes_recomendadas
            ADD CONSTRAINT fk_aluno_adaptacoes_restricao
            FOREIGN KEY (restricao_aluno_id, aluno_id)
            REFERENCES aluno_restricoes_fisicas(id, aluno_id)
            ON DELETE RESTRICT;
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_aluno_adaptacoes_aluno_id
    ON aluno_adaptacoes_recomendadas (aluno_id);

CREATE INDEX IF NOT EXISTS idx_aluno_adaptacoes_restricao_aluno_id
    ON aluno_adaptacoes_recomendadas (restricao_aluno_id);

CREATE INDEX IF NOT EXISTS idx_aluno_adaptacoes_validade
    ON aluno_adaptacoes_recomendadas (data_validade)
    WHERE ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_aluno_adaptacao_ativa
    ON aluno_adaptacoes_recomendadas (
        aluno_id,
        adaptacao_id,
        COALESCE(restricao_aluno_id, '00000000-0000-0000-0000-000000000000'::UUID)
    )
    WHERE ativo = TRUE;

DROP TRIGGER IF EXISTS trg_aluno_adaptacoes_atualizado_em
    ON aluno_adaptacoes_recomendadas;
CREATE TRIGGER trg_aluno_adaptacoes_atualizado_em
BEFORE UPDATE ON aluno_adaptacoes_recomendadas
FOR EACH ROW EXECUTE FUNCTION atualizar_data_catalogo_clinico();

-- -----------------------------------------------------------------------------
-- 4. Estados e fontes de informação. Os valores legados permanecem permitidos
-- temporariamente para impedir falha em registros já existentes.
-- -----------------------------------------------------------------------------

ALTER TABLE aluno_condicoes_clinicas
    DROP CONSTRAINT IF EXISTS ck_aluno_condicoes_revisao,
    DROP CONSTRAINT IF EXISTS ck_aluno_condicoes_fonte;

ALTER TABLE aluno_restricoes_fisicas
    DROP CONSTRAINT IF EXISTS ck_aluno_restricoes_revisao,
    DROP CONSTRAINT IF EXISTS ck_aluno_restricoes_fonte;

ALTER TABLE aluno_condicoes_clinicas
    ADD CONSTRAINT ck_aluno_condicoes_revisao
    CHECK (
        status_revisao IN (
            'PENDENTE',
            'SUGERIDO_POR_MIGRACAO',
            'VALIDADO',
            'REJEITADO',
            'EXPIRADO',
            'REVOGADO',
            -- Valores aceitos apenas durante a transição da migration 006.
            'SUGERIDO',
            'CONFIRMADO',
            'OBSOLETO'
        )
    ) NOT VALID,
    ADD CONSTRAINT ck_aluno_condicoes_fonte
    CHECK (
        fonte_informacao IN (
            'AUTORRELATO',
            'ATESTADO_MEDICO',
            'LAUDO',
            'FAMILIAR_RESPONSAVEL',
            'OBSERVACAO_PROFISSIONAL',
            'REGISTRO_LEGADO',
            'OUTRA',
            -- Valores aceitos apenas durante a transição da migration 006.
            'CADASTRO_MANUAL',
            'DECLARACAO_ALUNO',
            'DOCUMENTO_MEDICO'
        )
    ) NOT VALID;

ALTER TABLE aluno_restricoes_fisicas
    ADD CONSTRAINT ck_aluno_restricoes_revisao
    CHECK (
        status_revisao IN (
            'PENDENTE',
            'SUGERIDO_POR_MIGRACAO',
            'VALIDADO',
            'REJEITADO',
            'EXPIRADO',
            'REVOGADO',
            -- Valores aceitos apenas durante a transição da migration 006.
            'SUGERIDO',
            'CONFIRMADO',
            'OBSOLETO'
        )
    ) NOT VALID,
    ADD CONSTRAINT ck_aluno_restricoes_fonte
    CHECK (
        fonte_informacao IN (
            'AUTORRELATO',
            'ATESTADO_MEDICO',
            'LAUDO',
            'FAMILIAR_RESPONSAVEL',
            'OBSERVACAO_PROFISSIONAL',
            'REGISTRO_LEGADO',
            'OUTRA',
            -- Valores aceitos apenas durante a transição da migration 006.
            'CADASTRO_MANUAL',
            'DECLARACAO_ALUNO',
            'DOCUMENTO_MEDICO'
        )
    ) NOT VALID;

-- -----------------------------------------------------------------------------
-- 5. Auditoria complementar
-- -----------------------------------------------------------------------------

ALTER TABLE historico_revisoes_clinicas
    DROP CONSTRAINT IF EXISTS ck_historico_revisoes_entidade,
    DROP CONSTRAINT IF EXISTS ck_historico_revisoes_acao;

ALTER TABLE historico_revisoes_clinicas
    ADD CONSTRAINT ck_historico_revisoes_entidade
    CHECK (
        entidade IN (
            'CATALOGO_CONDICAO',
            'CATALOGO_RESTRICAO',
            'CATALOGO_ADAPTACAO',
            'ALUNO_CONDICAO',
            'ALUNO_RESTRICAO',
            'ALUNO_ADAPTACAO'
        )
    ) NOT VALID,
    ADD CONSTRAINT ck_historico_revisoes_acao
    CHECK (
        acao IN (
            'CRIACAO',
            'ATUALIZACAO',
            'ATIVACAO',
            'INATIVACAO',
            'REVISAO',
            'EXPIRACAO',
            'REVOGACAO'
        )
    ) NOT VALID;

-- -----------------------------------------------------------------------------
-- 6. RLS: manter habilitado. Nenhuma policy pública é criada aqui.
--
-- Como o IMBRA usa backend Streamlit e um modelo próprio de perfis, a política
-- de acesso deve ser desenhada antes de qualquer tela consumir estas tabelas.
-- Sem policy permissiva, o acesso direto via anon client permanece bloqueado.
-- -----------------------------------------------------------------------------

ALTER TABLE catalogo_condicoes_clinicas ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogo_restricoes_movimento ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogo_adaptacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_condicoes_clinicas ENABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_restricoes_fisicas ENABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_adaptacoes_recomendadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_revisoes_clinicas ENABLE ROW LEVEL SECURITY;

COMMIT;

-- =============================================================================
-- CONSULTAS DE CONFERÊNCIA — execute separadamente, fora da transaction acima.
-- =============================================================================

-- Pré-execução: confirme schema, RLS e policies existentes.
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN (
--     'catalogo_condicoes_clinicas',
--     'catalogo_restricoes_movimento',
--     'catalogo_adaptacoes',
--     'aluno_condicoes_clinicas',
--     'aluno_restricoes_fisicas',
--     'historico_revisoes_clinicas'
--   )
-- ORDER BY tablename;
--
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
--   AND tablename LIKE '%clinica%'
-- ORDER BY tablename, policyname;
--
-- Pós-execução: confira as novas colunas e os índices.
-- SELECT table_name, column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name IN (
--     'catalogo_condicoes_clinicas',
--     'catalogo_restricoes_movimento',
--     'catalogo_adaptacoes',
--     'aluno_condicoes_clinicas',
--     'aluno_restricoes_fisicas',
--     'aluno_adaptacoes_recomendadas',
--     'historico_revisoes_clinicas'
--   )
-- ORDER BY table_name, ordinal_position;
--
-- SELECT tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
--   AND tablename IN ('aluno_restricoes_fisicas', 'aluno_adaptacoes_recomendadas')
-- ORDER BY tablename, indexname;

-- =============================================================================
-- ROLLBACK NÃO DESTRUTIVO
--
-- Não há rollback automático. Após uso real, colunas e vínculos clínicos não
-- devem ser removidos. Para suspender a funcionalidade, não exponha as tabelas
-- em UI e mantenha RLS sem policy permissiva. Qualquer remoção física exige
-- backup validado, confirmação humana e análise de dependências.
-- =============================================================================