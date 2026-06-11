-- Migração 004: Adiciona colunas turma e url_foto à tabela pre_cadastros
-- Execute no SQL Editor do Supabase

ALTER TABLE pre_cadastros
  ADD COLUMN IF NOT EXISTS turma TEXT,
  ADD COLUMN IF NOT EXISTS url_foto TEXT;
