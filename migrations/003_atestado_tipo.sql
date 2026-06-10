-- migrations/003_atestado_tipo.sql
-- Adiciona coluna tipo_atestado à tabela atestados_temporarios
-- Execute no Supabase Dashboard → SQL Editor

ALTER TABLE atestados_temporarios
  ADD COLUMN IF NOT EXISTS tipo_atestado text NOT NULL DEFAULT 'outro';

-- Marca os registros existentes que são o único atestado do aluno
-- como aptidao_fisica (opcional — aplique com cuidado, só se quiser)
-- UPDATE atestados_temporarios SET tipo_atestado = 'aptidao_fisica'
-- WHERE tipo_atestado = 'outro';

CREATE INDEX IF NOT EXISTS idx_atestados_tipo
  ON atestados_temporarios (tipo_atestado);
