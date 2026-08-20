-- ==============================================================================
-- IMBRA — Modelo CRM: elogio de assiduidade
-- Execute no Supabase Dashboard → SQL Editor
-- Idempotente: preserva qualquer texto já personalizado pelo administrador.
-- ==============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_templates_gatilho
    ON crm_templates (gatilho);

INSERT INTO crm_templates (gatilho, titulo, mensagem, atualizado_em)
SELECT
    'assiduo_top',
    'Elogio de Assiduidade',
    'Olá, {nome}! Parabéns pela sua assiduidade e dedicação nas aulas! Sua presença faz a diferença. Continue assim! 🌟',
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM crm_templates
    WHERE gatilho = 'assiduo_top'
);