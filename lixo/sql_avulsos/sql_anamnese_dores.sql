-- ==============================================================================
-- 🩻 SCRIPT SQL — Tabela de Anamnese de Dores (Mapa Corporal)
-- Sistema IMBRA / MudaBrasil
-- Executar no Supabase: SQL Editor → Cole e clique em "Run"
-- ==============================================================================

-- 1. CRIAÇÃO DA TABELA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anamnese_dores (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    aluno_id        UUID        NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    data_avaliacao  DATE        NOT NULL DEFAULT CURRENT_DATE,
    regioes         JSONB       NOT NULL DEFAULT '[]',
    intensidade     JSONB       NOT NULL DEFAULT '{}',
    observacoes     TEXT,
    criado_por      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Estrutura das colunas:
--   regioes    → array de IDs de região, ex: ["f_joelho_e", "c_lombar"]
--   intensidade → objeto região → nível (1=leve, 2=moderada, 3=intensa)
--                 ex: {"f_joelho_e": 2, "c_lombar": 3}

-- 2. ÍNDICES
-- ------------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_anamnese_dores_aluno_data
    ON anamnese_dores (aluno_id, data_avaliacao DESC);

-- 3. ROW LEVEL SECURITY
-- ------------------------------------------------------------------------------
ALTER TABLE anamnese_dores ENABLE ROW LEVEL SECURITY;

-- Política permissiva (ajuste conforme seu setup de RLS no Supabase)
-- Se o seu projeto já usa service_role key no backend Python, esta política
-- garante que as operações via SDK (server-side) sempre funcionem.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'anamnese_dores'
          AND policyname = 'allow_all_anamnese_dores'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY allow_all_anamnese_dores
                ON anamnese_dores
                FOR ALL
                USING (true)
                WITH CHECK (true)
        $policy$;
    END IF;
END $$;

-- 4. VERIFICAÇÃO (opcional — execute para confirmar que tudo está correto)
-- ------------------------------------------------------------------------------
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'anamnese_dores'
-- ORDER BY ordinal_position;
