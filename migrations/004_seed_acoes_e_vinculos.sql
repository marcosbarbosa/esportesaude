-- ==============================================================================
-- IMBRA — Seed: Ações de Voluntariado + Vínculos com Alunos
-- Execute no Supabase Dashboard → SQL Editor
-- Idempotente: ON CONFLICT DO NOTHING (pode rodar mais de uma vez sem duplicar)
-- ==============================================================================


-- ── 0. Garantir que RLS está desabilitado ────────────────────────────────────
ALTER TABLE IF EXISTS acoes_voluntariado        DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS aluno_acoes_voluntariado  DISABLE ROW LEVEL SECURITY;


-- ── 1. Ações de Voluntariado (13 ações) ──────────────────────────────────────
INSERT INTO acoes_voluntariado (nome, descricao, area, icone, cor, ativa, ordem)
VALUES
    ('Trabalhos Manuais e Artesanato',
     'Tricô, bordado, costura, origami, pintura em tecido e outras atividades manuais.',
     'Arte e Cultura', '🧶', '#D97706', true, 10),

    ('Ensino e Educação',
     'Apoiar atividades pedagógicas, reforço escolar, alfabetização digital.',
     'Educação', '📚', '#2563EB', true, 20),

    ('Saúde e Bem-estar',
     'Orientações de saúde, aferição de pressão, apoio em atividades físicas leves.',
     'Saúde', '💚', '#059669', true, 30),

    ('Artes Plásticas',
     'Pintura, desenho, escultura, artesanato artístico e exposições.',
     'Arte e Cultura', '🎨', '#7C3AED', true, 40),

    ('Dançaterapia',
     'Dançaterapia, expressão corporal e atividades terapêuticas pelo movimento.',
     'Saúde', '💃', '#BE185D', true, 45),

    ('Organização e Administração',
     'Recepção, cadastros, organização de eventos e arquivos.',
     'Administração', '📋', '#0891B2', true, 50),

    ('Trabalho com Crianças',
     'Atividades lúdicas, recreação e suporte em eventos com crianças.',
     'Social', '👶', '#EC4899', true, 60),

    ('Trabalho com Idosos',
     'Companhia, conversas, apoio em atividades e visitas a idosos.',
     'Social', '🧓', '#EA580C', true, 70),

    ('Acolhimento e Conversas',
     'Escuta ativa, suporte emocional e integração de novos participantes.',
     'Social', '🤗', '#0D9488', true, 80),

    ('Eventos e Festas Sociais',
     'Organização e participação em comemorações e confraternizações.',
     'Eventos', '🎉', '#DC2626', true, 90),

    ('Decoração e Ambiente',
     'Decoração de espaços, arranjos, preparação de ambientes para eventos.',
     'Eventos', '🌸', '#DB2777', true, 100),

    ('Libras e Acessibilidade',
     'Interpretação em Libras, apoio à inclusão e acessibilidade.',
     'Inclusão', '🤟', '#6366F1', true, 110),

    ('Alimentação e Culinária',
     'Preparo de lanches, organização de alimentos e orientação nutricional.',
     'Saúde', '🍎', '#16A34A', true, 120)

ON CONFLICT (nome) DO NOTHING;


-- ==============================================================================
-- ── 2. Vínculos Aluno ↔ Ação (extraídos do PDF VOLU-Alunos_Ativos_20260729) ──
-- Usa subquery para resolver aluno_id e acao_id pelo nome (robusto a mudança de UUID)
-- ==============================================================================

-- ADRIANA BEATRIZ PERIN → Trabalhos Manuais e Artesanato
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%ADRIANA BEATRIZ PERIN%' AND a.status != 'Inativo'
  AND ac.nome = 'Trabalhos Manuais e Artesanato'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- ANA CAROLINA SANTOS MAZZA → Ensino e Educação
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%ANA CAROLINA SANTOS MAZZA%' AND a.status != 'Inativo'
  AND ac.nome = 'Ensino e Educação'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- CARMELITA LIMA DE OLIVEIRA → TODAS as ações ("disponível pra várias")
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%CARMELITA LIMA DE OLIVEIRA%' AND a.status != 'Inativo'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- CRISTINA CESAR PENTEADO → Trabalhos Manuais + Acolhimento e Conversas
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%CRISTINA CESAR PENTEADO%' AND a.status != 'Inativo'
  AND ac.nome IN ('Trabalhos Manuais e Artesanato', 'Acolhimento e Conversas')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- DARCI RAMIL SFORCINI → Eventos e Festas Sociais
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%DARCI RAMIL SFORCINI%' AND a.status != 'Inativo'
  AND ac.nome = 'Eventos e Festas Sociais'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- IRANDIR MENDES RIBEIRO → Libras e Acessibilidade
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%IRANDIR MENDES RIBEIRO%' AND a.status != 'Inativo'
  AND ac.nome = 'Libras e Acessibilidade'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- JERUSIA PERES → Trabalhos Manuais + Organização e Administração
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%JERUSIA PERES%' AND a.status != 'Inativo'
  AND ac.nome IN ('Trabalhos Manuais e Artesanato', 'Organização e Administração')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- JOSE ANTONIO MIGUEL RODRIGUES → Saúde e Bem-estar
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%JOSE ANTONIO MIGUEL%' AND a.status != 'Inativo'
  AND ac.nome = 'Saúde e Bem-estar'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- JOSÉ MARCOS FERNANDES → Artes Plásticas + Ensino + Organização
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MARCOS FERNANDES%' AND a.status != 'Inativo'
  AND ac.nome IN ('Artes Plásticas', 'Ensino e Educação', 'Organização e Administração')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- LEILA GEORGE NASSAN FOLGOSI → Trabalho com Crianças
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%LEILA GEORGE NASSAN%' AND a.status != 'Inativo'
  AND ac.nome = 'Trabalho com Crianças'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MAGDA MAIA MORAES → Dançaterapia
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MAGDA MAIA MORAES%' AND a.status != 'Inativo'
  AND ac.nome = 'Dançaterapia'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MARCIA REGINA DE SOUZA (ZWLLER) → Trabalho com Crianças
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MARCIA REGINA DE SOUZA%' AND a.status != 'Inativo'
  AND ac.nome = 'Trabalho com Crianças'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MARIA DE LOURDES PINHA LEITÃO → Acolhimento + Ensino + Trabalho com Crianças
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MARIA DE LOURDES PINHA%' AND a.status != 'Inativo'
  AND ac.nome IN ('Acolhimento e Conversas', 'Ensino e Educação', 'Trabalho com Crianças')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MARIA DO CARMO SOUZA FERREIRA → Ensino e Educação
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MARIA DO CARMO SOUZA%' AND a.status != 'Inativo'
  AND ac.nome = 'Ensino e Educação'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MARIA DO ROSÁRIO SOUSA → Ensino e Educação + Artes Plásticas
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MARIA DO ROSÁRIO SOUSA%' AND a.status != 'Inativo'
  AND ac.nome IN ('Ensino e Educação', 'Artes Plásticas')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MARIANGELA NAPONIELLO → Decoração e Ambiente + Organização e Administração
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MARIANGELA NAPONIELLO%' AND a.status != 'Inativo'
  AND ac.nome IN ('Decoração e Ambiente', 'Organização e Administração')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MEIRILANDE DO NASCIMENTO → Saúde e Bem-estar
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MEIRILANDE DO NASCIMENTO%' AND a.status != 'Inativo'
  AND ac.nome = 'Saúde e Bem-estar'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- MÁRCIA DA SILVA COIMBRA → Trabalhos Manuais + Artes Plásticas
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%MÁRCIA DA SILVA COIMBR%' AND a.status != 'Inativo'
  AND ac.nome IN ('Trabalhos Manuais e Artesanato', 'Artes Plásticas')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- SONIA MARIA FERNANDES NUNES → Ensino e Educação
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%SONIA MARIA FERNANDES NUNES%' AND a.status != 'Inativo'
  AND ac.nome = 'Ensino e Educação'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- SÍLVIA CRISTINA DOS SANTOS → Saúde e Bem-estar
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%SÍLVIA CRISTINA DOS SANTOS%' AND a.status != 'Inativo'
  AND ac.nome = 'Saúde e Bem-estar'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- THAIZA LEITÃO GONÇALVES → Trabalho com Crianças + Trabalho com Idosos
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%THAIZA LEITÃO GONÇALVES%' AND a.status != 'Inativo'
  AND ac.nome IN ('Trabalho com Crianças', 'Trabalho com Idosos')
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- THEREZA CHRISTINA PULICI → TODAS as ações ("Todas")
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%THEREZA CHRISTINA PULICI%' AND a.status != 'Inativo'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;

-- THEREZINHA NAZARÉ CURY → Acolhimento e Conversas
INSERT INTO aluno_acoes_voluntariado (aluno_id, acao_id, data_inscricao)
SELECT a.id::text, ac.id, CURRENT_DATE
FROM alunos a, acoes_voluntariado ac
WHERE a.nome ILIKE '%THEREZINHA NAZARÉ CURY%' AND a.status != 'Inativo'
  AND ac.nome = 'Acolhimento e Conversas'
ON CONFLICT (aluno_id, acao_id) DO NOTHING;


-- ==============================================================================
-- ── 3. Verificação ───────────────────────────────────────────────────────────
-- Execute para conferir o resultado:
-- ==============================================================================
/*
SELECT
    a.nome AS aluno,
    ac.icone || ' ' || ac.nome AS acao,
    v.data_inscricao
FROM aluno_acoes_voluntariado v
JOIN alunos a              ON a.id::text = v.aluno_id
JOIN acoes_voluntariado ac ON ac.id      = v.acao_id
ORDER BY a.nome, ac.ordem;
*/
