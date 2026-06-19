-- =============================================================================
-- IMBRA / MudaBrasil — Otimizações DDL no Supabase
-- Execute no SQL Editor do Supabase: https://supabase.com/dashboard → SQL Editor
-- Execute um bloco por vez e verifique o resultado antes do próximo.
-- =============================================================================


-- =============================================================================
-- BLOCO 1 — ÍNDICES DE DESEMPENHO (seguro, não altera dados)
-- =============================================================================
-- Esses índices aceleram as queries mais frequentes do sistema.
-- Criar índice não afeta dados existentes e pode ser desfeito com DROP INDEX.

-- 1a. Frequência: buscas por aluno_id + data_aula (filtros de presença, KPIs)
CREATE INDEX IF NOT EXISTS idx_frequencia_aluno_data
    ON frequencia (aluno_id, data_aula DESC);

-- 1b. Frequência: filtro por data + status (relatórios de período)
CREATE INDEX IF NOT EXISTS idx_frequencia_data_status
    ON frequencia (data_aula DESC, status);

-- 1c. Registros de PA: última PA por aluno (order by data+hora desc)
CREATE INDEX IF NOT EXISTS idx_registros_pa_aluno_data
    ON registros_pa (aluno_id, data DESC, hora DESC);

-- 1d. Alunos: busca por turma + status (get_alunos_por_turma)
CREATE INDEX IF NOT EXISTS idx_alunos_turma_status
    ON alunos (turma, status);

-- Verificar índices criados:
-- SELECT indexname, tablename, indexdef FROM pg_indexes
-- WHERE schemaname = 'public' ORDER BY tablename, indexname;


-- =============================================================================
-- BLOCO 2 — REMOVER COLUNA DUPLICADA url_foto (mantém foto_url)
-- =============================================================================
-- ANTES de executar: confirme que o sistema usa foto_url como campo principal.
-- A coluna url_foto está preenchida em ~6 alunos e é duplicata de foto_url.
--
-- Passo 1: migrar dados de url_foto → foto_url onde foto_url está vazio
UPDATE alunos
SET foto_url = url_foto
WHERE (foto_url IS NULL OR foto_url = '')
  AND (url_foto IS NOT NULL AND url_foto <> '');

-- Passo 2: verificar que nenhum aluno perdeu a foto
SELECT COUNT(*) AS com_foto FROM alunos WHERE foto_url IS NOT NULL AND foto_url <> '';

-- Passo 3: remover a coluna duplicada
-- (só execute após confirmar o resultado acima)
ALTER TABLE alunos DROP COLUMN IF EXISTS url_foto;


-- =============================================================================
-- BLOCO 3 — REMOVER aluno_nome DE registros_pa (dado redundante)
-- =============================================================================
-- aluno_nome é redundante — o nome já existe em alunos.nome.
-- Antes: verifique que nenhuma view/relatório depende exclusivamente desta coluna.
--
-- Passo 1: verificar quantos registros têm aluno_nome preenchido
SELECT COUNT(*) AS total,
       COUNT(aluno_nome) AS com_nome
FROM registros_pa;

-- Passo 2: remover a coluna
-- (só execute se confirmar que o sistema não exibe aluno_nome diretamente)
ALTER TABLE registros_pa DROP COLUMN IF EXISTS aluno_nome;


-- =============================================================================
-- BLOCO 4 — COLUNA nome_fonetica EM alunos (opcional — busca fonética)
-- =============================================================================
-- Se ainda não existe, cria a coluna para habilitar busca server-side fonética.
-- Após criar, o sistema detecta automaticamente e ativa o filtro no banco.

ALTER TABLE alunos ADD COLUMN IF NOT EXISTS nome_fonetica TEXT;

-- Índice para ILIKE rápido na busca fonética
CREATE INDEX IF NOT EXISTS idx_alunos_nome_fonetica
    ON alunos (nome_fonetica text_pattern_ops);

-- Preencher com valor inicial (o sistema faz o backfill completo pela interface,
-- mas este SQL preenche a versão simples — apenas minúsculas sem acento)
UPDATE alunos
SET nome_fonetica = lower(
    translate(nome,
        'áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ',
        'aaaaaeeeeiiiioooooouuuucAAAAEEEEIIIIOOOOOUUUUC'
    )
)
WHERE nome_fonetica IS NULL;


-- =============================================================================
-- BLOCO 5 — LIMPEZA PONTUAL (executar uma vez se necessário)
-- =============================================================================
-- Remove logs de auditoria acumulados (já feito pelo agente em 19/06/2026,
-- mas útil se voltarem a acumular antes do fix de auto-limpeza ser ativado):

DELETE FROM configuracoes_sistema
WHERE chave LIKE 'matricula_doc_log_%'
  AND chave NOT IN (
      SELECT chave FROM configuracoes_sistema
      WHERE chave LIKE 'matricula_doc_log_%'
      ORDER BY chave DESC
      LIMIT 50
  );

-- Verificar resultado:
SELECT COUNT(*) AS logs_restantes
FROM configuracoes_sistema
WHERE chave LIKE 'matricula_doc_log_%';
