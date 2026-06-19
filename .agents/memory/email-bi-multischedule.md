---
name: Email BI multi-schedule
description: Status e arquitetura do sistema de e-mail BI com múltiplos pacotes de envio independentes.
---

# Status
Sistema **completamente implementado**. Nenhum código pendente.

**Why this matters:** O session plan (T001/T002/T003) foi criado antes de uma sessão de build anterior já ter implementado tudo. Não reescrever.

# Arquitetura
- `utils/email_relatorio_config.py` — funções multi-schedule: `get_schedules`, `salvar_schedule`, `excluir_schedule`, `marcar_envio_realizado_schedule`, `schedule_to_cfg`, `migrar_legado_para_schedule`, `calcular_proximo_envio`
- `database.py` → `get_emails_sistema()` — retorna [{nome, email}] dos usuários da tabela `usuarios`
- `main.py` → `_tela_email_bi()` — UI completa: lista de pacotes, editor inline, checkboxes de e-mails do sistema, textarea externos, histórico por pacote (📋 button)
- `main.py` linhas 492–539 — trigger de envio automático: loop por todos os schedules habilitados com data devida; fallback legado se nenhum schedule

# O único passo pendente (infraestrutura)
Criar a tabela `email_bi_schedules` no Supabase. O SQL está em `_SQL_MIGRACAO_EBI` (main.py ~linha 931) e é exibido automaticamente na tela Email BI quando a tabela não existe. O operador clica "Já executei — recarregar" após rodar no SQL Editor.

# Migração legada
Se existirem configs em `configuracoes_sistema` (chaves `ebi_*`), `migrar_legado_para_schedule()` cria automaticamente o primeiro pacote "Pacote Principal" na nova tabela (executa 1x por sessão, protegido por `_ebi_migr_done`).
