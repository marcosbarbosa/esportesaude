-- IMBRA — Migração: campo data_vencimento nos atestados temporários
-- Execute no Supabase Dashboard → SQL Editor

ALTER TABLE atestados_temporarios
  ADD COLUMN IF NOT EXISTS data_vencimento date;

-- Índice para acelerar alertas de vencimento
CREATE INDEX IF NOT EXISTS idx_atestados_vencimento
  ON atestados_temporarios (data_vencimento)
  WHERE data_vencimento IS NOT NULL;
