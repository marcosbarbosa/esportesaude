-- ==============================================================================
-- 📐 SCRIPT DE NORMALIZAÇÃO — SISTEMA IMBRA / MudaBrasil
-- Versão: 2.0 — Baseada no schema REAL exportado do Supabase (maio/2026)
-- ==============================================================================
-- EXECUTE NO SUPABASE → SQL Editor
-- Execute UMA FASE DE CADA VEZ e verifique o resultado antes de avançar.
-- Todas as alterações destrutivas (DROP, NOT NULL) estão comentadas por segurança.
-- ==============================================================================
--
-- ═══════════════════════════════════════════════════════════════════════════════
-- DIAGNÓSTICO GERAL — O QUE JÁ EXISTE E O QUE FALTA
-- ═══════════════════════════════════════════════════════════════════════════════
--
--  COLUNA turma_id FK → turmas.id:
--    ✅ alunos.turma_id            — EXISTE (constraint alunos_turma_id_fkey)
--    ✅ diario_aulas.turma_id      — EXISTE (constraint diario_aulas_turma_id_fkey)
--    ❌ pesquisas_satisfacao.turma_id — NÃO EXISTE (só tem turma TEXT NOT NULL)
--
--  COLUNAS FK ausentes (sem constraint de integridade):
--    ⚠️  frequencia.aluno_id       — coluna existe mas SEM FK constraint
--    ⚠️  prontuarios_imbra.aluno_id — coluna existe mas SEM FK constraint
--
--  TABELA AUSENTE (script SQL criado mas nunca executado):
--    ❌ anamnese_dores              — NÃO EXISTE no banco (código a usa e falha)
--
--  TABELAS LEGADAS (existem no banco mas o código ATIVO não as usa):
--    🗄️  atendimentos              — código usa "frequencia" em vez desta
--    🗄️  anamnese_saude            — código usa "anamnese_dores" em vez desta
--    🗄️  avaliacoes_fisicas        — código usa "prontuario_avaliacoes" em vez desta
--    🗄️  prescricoes_profissionais — sem referência em nenhum arquivo de código
--    🗄️  prontuarios_imbra         — apenas backup_view.py; sem CRUD ativo
--
--  COLUNAS DUPLICADAS em alunos (dados históricos, sem prejuízo imediato):
--    ℹ️  telefone TEXT  +  whatsapp VARCHAR  — código usa "whatsapp"
--    ℹ️  foto_url TEXT  +  url_foto TEXT     — código usa "url_foto" (bi_individual
--                                              faz fallback para foto_url também)
--
--  BUG SILENCIOSO em aprovar_inscricao_aluno() → database.py linha 229:
--    ⚠️  pre_cadastros tem campo "celular" mas código lê "whatsapp" → retorna ""
--        Alunos aprovados da ficha pública chegam sem WhatsApp preenchido.
--        Correção: ver FASE 7 (ajuste de código, não de banco).
--
-- ==============================================================================




-- ==============================================================================
-- ██  FASE 0 — DIAGNÓSTICO DETALHADO  (apenas SELECTs, sem alterações)  ██████
-- Execute este bloco completo e analise cada resultado antes de avançar.
-- ==============================================================================


-- F0.1 — Confirmar quais colunas turma/turma_id existem em cada tabela
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name   IN ('alunos','diario_aulas','pesquisas_satisfacao')
  AND column_name  IN ('turma','turma_id')
ORDER BY table_name, column_name;

-- Resultado esperado do schema real:
--   alunos               | turma    | text | NULL | YES
--   alunos               | turma_id | uuid | NULL | YES   ← FK já existe
--   diario_aulas         | turma    | text | NULL | NO    ← NOT NULL
--   diario_aulas         | turma_id | uuid | NULL | YES   ← FK já existe
--   pesquisas_satisfacao | turma    | text | NULL | NO    ← NOT NULL, sem turma_id


-- F0.2 — Confirmar FKs registadas (deve mostrar alunos e diario_aulas, não pesquisas)
SELECT
    tc.table_name     AS tabela,
    kcu.column_name   AS coluna,
    ccu.table_name    AS referencia_tabela,
    ccu.column_name   AS referencia_coluna,
    rc.delete_rule    AS on_delete
FROM information_schema.table_constraints   tc
JOIN information_schema.key_column_usage    kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = rc.unique_constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('alunos','diario_aulas','pesquisas_satisfacao','frequencia','prontuarios_imbra')
ORDER BY tabela, coluna;


-- F0.3 — Estado atual do preenchimento de turma_id em alunos
SELECT
    COUNT(*)                                          AS total_alunos,
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL)      AS com_turma_id,
    COUNT(*) FILTER (WHERE turma_id IS NULL
                      AND turma IS NOT NULL
                      AND turma <> '')                AS sem_turma_id_mas_tem_nome,
    COUNT(*) FILTER (WHERE turma_id IS NULL
                      AND (turma IS NULL OR turma='')) AS sem_turma_nenhuma
FROM alunos;


-- F0.4 — Estado atual do preenchimento de turma_id em diario_aulas
SELECT
    COUNT(*)                                     AS total_diarios,
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL) AS com_turma_id,
    COUNT(*) FILTER (WHERE turma_id IS NULL)     AS sem_turma_id
FROM diario_aulas;


-- F0.5 — TURMAS FANTASMAS em alunos (nomes que não batem com nenhuma turma oficial)
-- Estes registos ficarão com turma_id = NULL após o backfill da Fase 2
SELECT
    a.turma             AS nome_fantasma,
    COUNT(a.id)         AS qtd_alunos,
    STRING_AGG(a.nome, ', ' ORDER BY a.nome) AS nomes_alunos
FROM alunos a
LEFT JOIN turmas t ON t.nome = a.turma
WHERE t.id IS NULL
  AND a.turma IS NOT NULL
  AND a.turma <> ''
GROUP BY a.turma
ORDER BY qtd_alunos DESC;

-- ⚠️  Se esta query retornar linhas: corrija via ferramenta_reparacao_turmas()
--     no app ANTES de executar a Fase 2. Cada linha é um grupo de alunos
--     cujo turma_id ficará NULL e portanto invisível na Conferência Facial.


-- F0.6 — TURMAS FANTASMAS em diario_aulas (histórico com nomes antigos)
SELECT
    d.turma             AS nome_fantasma,
    COUNT(d.id)         AS qtd_diarios,
    MIN(d.data_aula)    AS data_mais_antiga,
    MAX(d.data_aula)    AS data_mais_recente
FROM diario_aulas d
LEFT JOIN turmas t ON t.nome = d.turma
WHERE t.id IS NULL
  AND d.turma IS NOT NULL
  AND d.turma <> ''
GROUP BY d.turma
ORDER BY qtd_diarios DESC;


-- F0.7 — Turmas oficiais: quantos alunos cada uma possui
SELECT
    t.id,
    t.nome,
    t.horario,
    t.status,
    COUNT(a.id) FILTER (WHERE a.status <> 'Inativo') AS alunos_ativos,
    COUNT(a.id)                                       AS alunos_total,
    COUNT(a.id) FILTER (WHERE a.turma_id = t.id)     AS ja_com_turma_id
FROM turmas t
LEFT JOIN alunos a ON a.turma = t.nome
GROUP BY t.id, t.nome, t.horario, t.status
ORDER BY t.nome;


-- F0.8 — Verificar se anamnese_dores existe (script sql_anamnese_dores.sql precisa rodar)
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'anamnese_dores'
) AS tabela_anamnese_dores_existe;
-- Se retornar FALSE → execute a FASE 5 deste script para criá-la.


-- F0.9 — Verificar tabelas legadas que podem estar acumulando dados sem uso
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns c
     WHERE c.table_name = t.table_name
       AND c.table_schema = 'public')  AS qtd_colunas
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN (
      'atendimentos',
      'anamnese_saude',
      'avaliacoes_fisicas',
      'prescricoes_profissionais',
      'prontuarios_imbra'
  )
ORDER BY table_name;
-- Use os nomes retornados para verificar a contagem de registos:
-- SELECT COUNT(*) FROM atendimentos;
-- SELECT COUNT(*) FROM anamnese_saude;
-- etc.


-- ==============================================================================
-- ██  FASE 1 — ADICIONAR COLUNA AUSENTE: pesquisas_satisfacao.turma_id  ████████
-- alunos e diario_aulas já têm turma_id com FK. Só falta pesquisas_satisfacao.
-- ==============================================================================

-- F1.1 — Adicionar turma_id em pesquisas_satisfacao (nullable, sem FK ainda)
--         FK será adicionada na Fase 3, depois do backfill e verificação de órfãos
ALTER TABLE pesquisas_satisfacao
    ADD COLUMN IF NOT EXISTS turma_id UUID;

-- Confirmar:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name   = 'pesquisas_satisfacao'
  AND column_name  = 'turma_id';


-- ==============================================================================
-- ██  FASE 2 — BACKFILL: POPULAR turma_id A PARTIR DO NOME TEXT  ██████████████
-- Executa o JOIN entre o nome de texto e turmas.id.
-- Registos cujo nome não bater com nenhuma turma ficam com turma_id = NULL.
-- Execute F0.5 e F0.6 ANTES para minimizar os que ficarão NULL.
-- ==============================================================================

-- F2.1 — Backfill em alunos
UPDATE alunos a
SET    turma_id = t.id
FROM   turmas t
WHERE  t.nome    = a.turma
  AND  a.turma_id IS NULL;   -- idempotente: só atualiza os ainda vazios

-- Resultado:
SELECT
    COUNT(*)                                     AS total,
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL) AS com_turma_id,
    COUNT(*) FILTER (WHERE turma_id IS NULL)     AS ficaram_null
FROM alunos;


-- F2.2 — Backfill em diario_aulas
UPDATE diario_aulas d
SET    turma_id = t.id
FROM   turmas t
WHERE  t.nome    = d.turma
  AND  d.turma_id IS NULL;

-- Resultado:
SELECT
    COUNT(*)                                     AS total,
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL) AS com_turma_id,
    COUNT(*) FILTER (WHERE turma_id IS NULL)     AS ficaram_null
FROM diario_aulas;


-- F2.3 — Backfill em pesquisas_satisfacao
UPDATE pesquisas_satisfacao ps
SET    turma_id = t.id
FROM   turmas t
WHERE  t.nome    = ps.turma
  AND  ps.turma_id IS NULL;

-- Resultado:
SELECT
    COUNT(*)                                     AS total,
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL) AS com_turma_id,
    COUNT(*) FILTER (WHERE turma_id IS NULL)     AS ficaram_null
FROM pesquisas_satisfacao;


-- ==============================================================================
-- ██  FASE 3 — INTEGRIDADE: FK + ÍNDICES PARA pesquisas_satisfacao  ████████████
-- As FKs de alunos e diario_aulas já existem.
-- Esta fase adiciona a FK de pesquisas_satisfacao e os índices de performance.
-- Execute APENAS depois de verificar que o backfill (F2.3) está satisfatório.
-- ==============================================================================

-- F3.1 — Adicionar FK em pesquisas_satisfacao (SET NULL para não quebrar histórico)
--         "ON DELETE SET NULL" protege pesquisas antigas quando uma turma é excluída
ALTER TABLE pesquisas_satisfacao
    ADD CONSTRAINT pesquisas_satisfacao_turma_id_fkey
    FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE SET NULL;

-- F3.2 — Índice em alunos.turma_id (pode já existir — IF NOT EXISTS protege)
CREATE INDEX IF NOT EXISTS idx_alunos_turma_id
    ON alunos (turma_id);

-- F3.3 — Índice composto em diario_aulas (turma_id + data) para queries de período
CREATE INDEX IF NOT EXISTS idx_diario_aulas_turma_id_data
    ON diario_aulas (turma_id, data_aula DESC);

-- F3.4 — Índice em pesquisas_satisfacao
CREATE INDEX IF NOT EXISTS idx_pesquisas_satisfacao_turma_id
    ON pesquisas_satisfacao (turma_id);

-- F3.5 — Verificar todos os índices criados
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE tablename IN ('alunos','diario_aulas','pesquisas_satisfacao')
  AND indexname LIKE '%turma%'
ORDER BY tablename;


-- ==============================================================================
-- ██  FASE 4 — FKs AUSENTES: frequencia e prontuarios_imbra  ████████████████
-- Estas tabelas têm aluno_id sem constraint de integridade referencial.
-- Risco: é possível registar frequência para um aluno_id que não existe.
-- ==============================================================================

-- F4.1 — Verificar se já existem órfãos antes de adicionar a FK
--         (se retornar linhas, limpe-as antes — FK não é criada com dados inválidos)
SELECT f.id, f.aluno_id, f.data_aula, f.status
FROM frequencia f
LEFT JOIN alunos a ON a.id = f.aluno_id
WHERE a.id IS NULL
LIMIT 50;
-- Se retornar linhas → DELETE FROM frequencia WHERE aluno_id NOT IN (SELECT id FROM alunos);

SELECT p.id, p.aluno_id, p.data_avaliacao
FROM prontuarios_imbra p
LEFT JOIN alunos a ON a.id = p.aluno_id
WHERE a.id IS NULL
LIMIT 20;
-- Se retornar linhas → DELETE FROM prontuarios_imbra WHERE aluno_id NOT IN (SELECT id FROM alunos);


-- F4.2 — Adicionar FK em frequencia.aluno_id
--         ⚠️  SÓ execute depois de F4.1 confirmar zero órfãos
ALTER TABLE frequencia
    ADD CONSTRAINT frequencia_aluno_id_fkey
    FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE;
-- ON DELETE CASCADE: se o aluno for excluído, a frequência some junto (OK para este sistema)

-- F4.3 — Adicionar FK em prontuarios_imbra.aluno_id
ALTER TABLE prontuarios_imbra
    ADD CONSTRAINT prontuarios_imbra_aluno_id_fkey
    FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE;


-- ==============================================================================
-- ██  FASE 5 — CRIAR TABELA anamnese_dores (SE AINDA NÃO EXISTIR)  ████████████
-- O arquivo sql_anamnese_dores.sql foi criado mas provavelmente não foi executado.
-- O código database.py usa esta tabela — sem ela, funções de mapa corporal falham.
-- ==============================================================================

-- (Conteúdo do sql_anamnese_dores.sql, adaptado com IF NOT EXISTS)

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

CREATE INDEX IF NOT EXISTS idx_anamnese_dores_aluno_data
    ON anamnese_dores (aluno_id, data_avaliacao DESC);

ALTER TABLE anamnese_dores ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'anamnese_dores'
          AND policyname = 'allow_all_anamnese_dores'
    ) THEN
        EXECUTE $policy$
            CREATE POLICY allow_all_anamnese_dores
                ON anamnese_dores FOR ALL
                USING (true) WITH CHECK (true)
        $policy$;
    END IF;
END $$;

-- Confirmar:
SELECT table_name, (SELECT COUNT(*) FROM anamnese_dores) AS registros
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'anamnese_dores';


-- ==============================================================================
-- ██  FASE 6 — VISTAS AUXILIARES (VIEWS) PARA SIMPLIFICAR O CÓDIGO  ████████████
-- Permite que o Python use SELECT * FROM vw_alunos_com_turma e já receba
-- os dados da turma resolvidos — sem JOIN manual em cada função.
-- ==============================================================================

CREATE OR REPLACE VIEW vw_alunos_com_turma AS
SELECT
    a.id,
    a.nome,
    a.status,
    a.data_nascimento,
    a.peso,
    a.altura,
    a.whatsapp,
    a.email,
    a.cpf,
    a.rg,
    a.endereco,
    a.bairro,
    a.cep,
    a.contato_emergencia,
    a.problemas_saude,
    a.medicamentos,
    a.restricoes_fisicas,
    a.url_foto,
    a.url_rg,
    a.url_receituario,
    a.url_atestado_medico,
    a.cor_alerta_atual,
    a.nota_risco_atual,
    a.created_at,
    -- Campos socioeconômicos
    a.grau_instrucao,
    a.principal_fonte_renda,
    a.faixa_renda,
    a.naturalidade,
    a.sexo,
    a.estado_civil,
    a.aposentado,
    a.nome_conjuge,
    a.qtd_moradores,
    a.trabalho_voluntario_interesse,
    a.trabalho_voluntario_areas,
    a.anamnese_incomodo_atividade,
    -- Turma (novo modelo normalizado)
    a.turma_id,
    t.nome         AS turma,          -- mantém o mesmo nome de campo para compatibilidade
    t.horario      AS turma_horario,
    t.dias_semana  AS turma_dias_semana,
    t.status       AS turma_status
FROM alunos a
LEFT JOIN turmas t ON t.id = a.turma_id;

-- Nota: a view retorna "turma" como o nome resolvido da turma (não o campo TEXT antigo).
-- Quando o código Python for migrado, usará esta view e a coluna TEXT pode ser removida.


CREATE OR REPLACE VIEW vw_diario_com_turma AS
SELECT
    d.id,
    d.data_aula,
    d.objetivo_geral,
    d.exercicios_executados,
    d.url_foto_grupo,
    d.foco_clinico_social,
    d.relatos_melhora,
    d.turma_id,
    t.nome         AS turma,          -- compatibilidade com código atual
    t.horario      AS turma_horario
FROM diario_aulas d
LEFT JOIN turmas t ON t.id = d.turma_id;


-- ==============================================================================
-- ██  RESUMO DE VERIFICAÇÃO FINAL  ████████████████████████████████████████████
-- Execute este bloco após completar as Fases 1 a 5 para ter o quadro completo.
-- ==============================================================================

-- VF.1 — Taxa de preenchimento de turma_id por tabela
SELECT
    'alunos' AS tabela,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL) AS com_turma_id,
    COUNT(*) FILTER (WHERE turma_id IS NULL)     AS sem_turma_id,
    ROUND(COUNT(*) FILTER (WHERE turma_id IS NOT NULL)
          * 100.0 / NULLIF(COUNT(*), 0), 1)      AS pct_ok
FROM alunos
UNION ALL
SELECT 'diario_aulas',
    COUNT(*),
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL),
    COUNT(*) FILTER (WHERE turma_id IS NULL),
    ROUND(COUNT(*) FILTER (WHERE turma_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*),0), 1)
FROM diario_aulas
UNION ALL
SELECT 'pesquisas_satisfacao',
    COUNT(*),
    COUNT(*) FILTER (WHERE turma_id IS NOT NULL),
    COUNT(*) FILTER (WHERE turma_id IS NULL),
    ROUND(COUNT(*) FILTER (WHERE turma_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*),0), 1)
FROM pesquisas_satisfacao;

-- Metas: alunos e diario_aulas → 100% (ou próximo).
-- pesquisas_satisfacao pode ter NULL para pesquisas de turmas já extintas.


-- VF.2 — Confirmar todas as FKs presentes nas tabelas críticas
SELECT
    tc.table_name     AS tabela,
    kcu.column_name   AS coluna_fk,
    ccu.table_name    AS ref_tabela,
    ccu.column_name   AS ref_coluna,
    rc.delete_rule    AS on_delete
FROM information_schema.table_constraints   tc
JOIN information_schema.key_column_usage    kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = rc.unique_constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN (
      'alunos','diario_aulas','pesquisas_satisfacao',
      'frequencia','prontuarios_imbra','anamnese_dores'
  )
ORDER BY tabela, coluna_fk;


-- ==============================================================================
-- ██  FASE 7 — LIMPEZA FUTURA (COMENTADA — NÃO EXECUTAR AGORA)  ███████████████
-- Execute APENAS depois que o código Python estiver 100% migrado para turma_id.
-- Antes: atualize database.py e todas as views para não usar mais turma TEXT.
-- ==============================================================================

-- 7.A — Remover coluna turma TEXT de alunos (IRREVERSÍVEL)
-- ALTER TABLE alunos DROP COLUMN IF EXISTS turma;

-- 7.B — Remover coluna turma TEXT de diario_aulas (IRREVERSÍVEL)
-- ALTER TABLE diario_aulas DROP COLUMN IF EXISTS turma;

-- 7.C — Remover coluna turma TEXT de pesquisas_satisfacao (IRREVERSÍVEL)
-- ALTER TABLE pesquisas_satisfacao DROP COLUMN IF EXISTS turma;

-- 7.D — Remover colunas duplicadas legadas de alunos (IRREVERSÍVEL)
--        Confirme ANTES que nenhuma parte do código as usa como fonte primária.
-- ALTER TABLE alunos DROP COLUMN IF EXISTS telefone;   -- código usa "whatsapp"
-- ALTER TABLE alunos DROP COLUMN IF EXISTS foto_url;   -- código usa "url_foto"
--        (bi_individual_view.py tem fallback para foto_url — ajustar primeiro)

-- 7.E — Ao remover coluna turma TEXT de diario_aulas:
--        Retirar o NOT NULL da migration já que turma_id assumirá o papel.
--        A remoção do NOT NULL na coluna TEXT acontece automaticamente com DROP COLUMN.


-- ==============================================================================
-- ██  INFORMATIVO — BUGS IDENTIFICADOS NO CÓDIGO (SEM SQL, PARA REFERÊNCIA)  ██
-- ==============================================================================
--
-- BUG-01 ⚠️  aprovar_inscricao_aluno() — database.py linha 229
--   pre_cadastros.celular existe mas o código lê .get("whatsapp", "") → sempre ""
--   Alunos vindos da ficha pública chegam SEM WhatsApp no sistema.
--   CORREÇÃO: mudar para .get("celular", "") ou mapear o campo correto.
--
-- BUG-02 ℹ️  aprovar_inscricao_aluno() — database.py linhas 240-242
--   Código lê url_foto, url_rg, url_receituario de pre_cadastros.
--   Schema real de pre_cadastros NÃO tem essas colunas (retorna None silenciosamente).
--   Impacto baixo (campos ficam NULL), mas nunca serão preenchidos na aprovação.
--
-- BUG-03 ⚠️  anamnese_dores — tabela ausente
--   database.py tem funções que usam anamnese_dores mas a tabela não existe.
--   Execute a FASE 5 deste script para criá-la.
--
-- BUG-04 ℹ️  backup_view.py lista "midias" como tabela — não existe no schema real
--   O nome correto é "diario_midias". Backup provavelmente falha silenciosamente.
--
-- ==============================================================================
