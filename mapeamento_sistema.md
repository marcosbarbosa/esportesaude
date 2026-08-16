# 🗺️ Mapeamento Completo do Sistema — IMBRA Chamada
> Gerado por auditoria de código. Revisão humana necessária antes dos Passos 2 e 3.
> Última varredura: `views/`, `modulos_frequencia/`, `modulos_prontuario/`, `main.py`, `database.py`

---

## Legenda de Status das Chaves

| Símbolo | Significado |
|---|---|
| ✅ | Chave **já existe** na tela de Permissões de Menu |
| 🆕 | Chave **nova** — precisa ser adicionada |
| 🔒 | Restrito a **SuperAdmin** por código — atualmente sem checkbox |

---

## 1. 🏠 Principal (Dashboard Inicial)

**Arquivo:** `main.py` (linhas ~1750–2100)
**Chave pai:** `principal` ✅

### Filhos (abas/seções)
_Não há tabs — é uma única tela._

### Netos (ações críticas)
| Chave | Descrição |
|---|---|
| 🆕 `principal_snapshot_lote` | Botão "Processar em Lote" — regenera snapshot de KPIs |
| 🆕 `principal_agenda` | Bloco de agenda do dia (agendamentos médicos) |
| 🆕 `principal_risco` | Cards de alunos em risco crítico/moderado |
| 🆕 `principal_niver` | Card de aniversariantes do dia |

---

## 2. ✅ Frequência

**Arquivo:** `views/frequencia_view.py` + `modulos_frequencia/`
**Chave pai:** `frequencia` ✅

### Filhos (abas dentro da tela Frequência)

| Chave | Aba | Arquivo | Status |
|---|---|---|---|
| 🆕 `freq_chamada_tablet` | 📱 Chamada Tablet | `tab_tablet.py` | 🆕 |
| 🆕 `freq_diario` | 📝 Diário | `tab_diario.py` | 🆕 |
| 🆕 `freq_dossie` | 🖨️ Dossiê | `tab_dossie.py` | 🆕 |
| 🆕 `freq_emergencia_tab` | 🚨 Emergência | `tab_emergencia.py` | 🆕 |
| 🆕 `freq_lgpd` | 🔒 LGPD | `tab_lgpd.py` | 🆕 |
| 🆕 `freq_atestado` | 🏥 Atestado | `tab_atestado.py` | 🆕 |
| 🆕 `freq_niver` | 🎂 Aniversariantes | `tab_niver.py` | 🆕 |
| 🆕 `freq_admin` | 📅 Dias Regist./Anamnese | `tab_admin.py` | 🆕 _(só admins)_ |

### Netos (ações críticas)

| Chave | Descrição |
|---|---|
| ✅ `freq_conf_facial` | 📸 Conferência de Presença por Foto |
| 🆕 `freq_niver_pdf` | Gerar PDF de Parabéns (dentro da aba Aniversariantes) |
| 🆕 `freq_admin_validade_anamnese` | Salvar validade da anamnese (aba Admin) |
| 🆕 `freq_admin_excluir_aula` | Excluir dia letivo registrado (aba Admin) |

---

## 3. 🩺 Portal do Aluno

**Arquivo:** `views/prontuario_dashboard.py` + `views/prontuario_view.py` + `views/prontuario_ficha.py`
**Chave pai:** `portal_aluno` ✅

### Filhos — Abas do Dashboard

| Chave | Aba | Status |
|---|---|---|
| 🆕 `portal_tab_alunos` | 👥 Alunos (lista principal com busca) | 🆕 |
| 🆕 `portal_tab_patologias` | 🧬 Patologias / Anamnese Clínica | 🆕 |
| 🆕 `portal_tab_cracha` | 🪪 Cara-crachá | 🆕 |
| 🆕 `portal_tab_novo_aluno` | 📝 NOVO Aluno (cadastro completo) | 🆕 |
| 🆕 `portal_tab_triagem` | 🆕 TRIAGEM | 🆕 |
| 🆕 `portal_tab_agenda` | 🗓️ Agenda Médica | 🆕 |
| 🆕 `portal_tab_medidos` | 📊 Já Medidos | 🆕 |
| 🆕 `portal_tab_sem_medicoes` | ⚠️ Sem Medições | 🆕 |
| 🆕 `portal_tab_inativos` | 🗄️ Arquivo Morto (Inativos) | 🆕 |
| 🆕 `portal_tab_pa` | 🩸 Pressão Arterial (lançamento em lote) | 🆕 |

### Filhos — Prontuário Individual (`prontuario_view.py`)

| Chave | Aba | Status |
|---|---|---|
| ✅ `portal_prontuario` | 🩺 Abrir Prontuário/Ficha individual | ✅ |
| 🆕 `portal_pront_perfil` | 👤 Perfil e Contato | 🆕 |
| 🆕 `portal_pront_medicao` | 📝 Nova Medição | 🆕 |
| 🆕 `portal_pront_historico` | 📊 Histórico Clínico | 🆕 |
| 🆕 `portal_pront_docs` | 📂 Documentação Legal (RG, Receituário, Atestado) | 🆕 |

### Filhos — Ficha Ampliada (`prontuario_ficha.py`) — abas extras

| Chave | Aba | Status |
|---|---|---|
| 🆕 `portal_pront_social` | 🏘️ Perfil Social | 🆕 |
| 🆕 `portal_pront_dores` | 🩻 Mapa de Dores | 🆕 |
| 🆕 `portal_pront_pa_ind` | 🩺 Pressão Arterial Individual | 🆕 |

### Netos — Ações Críticas no Prontuário

| Chave | Ação | Observação |
|---|---|---|
| ✅ `portal_ficha_impressao` | 🖨️ Central de Impressão de Fichas | ✅ |
| 🆕 `portal_exportar_pdf` | 📄 Exportar PDF Dossiê Clínico | `gerador_pdf.py` |
| 🆕 `portal_exportar_word` | 📝 Exportar Word Prontuário | `gerador_word.py` |
| 🆕 `portal_arquivar_aluno` | 🗄️ Arquivar Aluno (inativar + motivo de saída) | Ação irreversível parcial |
| 🆕 `portal_reativar_aluno` | ♻️ Reativar Aluno | |
| 🆕 `portal_excluir_aluno` | 🗑️ Excluir Aluno permanentemente | ⚠️ Irreversível |
| 🆕 `portal_lgpd_toggle` | ✅/🚫 Autorizar/Revogar Uso de Imagem (LGPD) | |
| 🆕 `portal_atestado_arquivar` | ➕ Arquivar Atestado no histórico | |
| 🆕 `portal_agendamento_criar` | 🗓️ Criar/Editar Agendamento Médico | |
| 🆕 `portal_merge` | 🔀 Mesclar Fichas duplicadas | `merge_alunos_view.py` |
| 🆕 `portal_validador` | 🔍 Validador Público (deeplink) | `validador_view.py` |

---

## 4. 📊 Relatórios & BI

**Arquivos:** `views/relatorio_view.py`, `views/bi_dashboard_view.py`, `views/bi_individual_view.py`
**Chave pai:** `relatorios_bi` ✅

### Filhos — Sub-módulos

| Chave | Módulo | Status |
|---|---|---|
| ✅ `rel_relatorios` | 📋 Relatórios (acesso à aba principal) | ✅ |
| ✅ `rel_bi_dashboard` | 📊 BI Dashboard (KPIs gerenciais) | ✅ |
| ✅ `rel_bi_individual` | 👤 BI Individual (evolução por aluno) | ✅ |

### Netos — Abas dentro de 📋 Relatórios

| Chave | Aba | Status |
|---|---|---|
| ✅ `rel_lista_freq` | 📋 Lista Frequência Oficial | ✅ |
| ✅ `rel_plan_freq` | 📊 Planilha de Frequência | ✅ |
| ✅ `rel_auditoria` | 🔎 Auditoria de Cadastros | ✅ |
| ✅ `rel_prestacao_ped` | 🏆 Prestação Pedagógica (Word) | ✅ |
| ✅ `rel_avaliacoes` | 🧪 Avaliações Pendentes | ✅ |
| ✅ `rel_patologias` | 🧬 Patologias / Anamnese | ✅ |
| ✅ `rel_pa_lote` | 🩺 Coleta PA em Lote | ✅ |
| 🆕 `rel_inativos` | 🗄️ Alunos Inativos | 🆕 _(existe na view, falta na permissão)_ |

### Netos — Ações dentro de Relatórios

| Chave | Ação | Observação |
|---|---|---|
| 🆕 `rel_exportar_excel` | 📥 Exportar Excel/CSV (Frequência) | Dentro de `rel_lista_freq` e `rel_plan_freq` |
| 🆕 `rel_exportar_word` | 📝 Gerar Word Prestação Pedagógica | Dentro de `rel_prestacao_ped` |
| 🆕 `rel_satisfacao` | 📊 Incluir dados de Satisfação no relatório anual | Dentro de `rel_plan_freq` |

---

## 5. 🎯 Gestor

**Arquivos:** `views/radar_acolhimento_view.py`, `views/relatorio_satisfacao_view.py`, `modulos_frequencia/tab_emergencia.py`
**Chave pai:** `gestor` ✅

### Filhos — Abas do Gestor

| Chave | Aba | Status |
|---|---|---|
| ✅ `gestor_radar` | 💙 Radar de Acolhimento | ✅ |
| ✅ `gestor_satisfacao` | ⭐ Satisfação | ✅ |
| ✅ `gestor_emergencia` | 🚨 Emergência (Protocolo) | ✅ |
| 🔒 `_config` | ⚙️ Config (SuperAdmin) | 🔒 Sem checkbox — só SuperAdmin |

### Netos — Abas dentro de ⚙️ Config (SuperAdmin)
> Atualmente acessíveis apenas a SuperAdmin sem granularidade de permissão.

| Chave | Aba | Arquivo | Status |
|---|---|---|---|
| 🔒 `gestor_cfg_turmas` | 🏫 Turmas | `turmas_view.py` | 🔒 |
| 🔒 `gestor_cfg_mensagens` | 💬 Mensagens/Templates | `templates_view.py` | 🔒 |
| 🔒 `gestor_cfg_niver` | 🔔 Auto Niver | `config_niver_view.py` | 🔒 |
| 🔒 `gestor_cfg_identidade` | 🎨 Identidade Visual | `identidade_view.py` | 🔒 |
| 🔒 `gestor_cfg_backup` | 🗄️ Backup Admin | `backup_view.py` | 🔒 |
| 🔒 `gestor_cfg_merge` | 🔀 Mesclar Fichas | `merge_alunos_view.py` | 🔒 |
| 🔒 `gestor_cfg_calendario` | 📅 Calendário Institucional | `main.py` interno | 🔒 |
| 🔒 `gestor_cfg_email` | 📧 Email BI (agendamentos) | `main.py` interno | 🔒 |
| 🔒 `gestor_cfg_usuarios` | 👥 Usuários/Operadores | `gestao_usuarios_view.py` | 🔒 |
| 🔒 `gestor_cfg_lgpd` | 🔒 Log LGPD | `main.py` interno | 🔒 |
| 🔒 `gestor_cfg_tags` | 🏷️ Tags de Saúde | `tags_clinicas_config_view.py` | 🔒 |
| 🔒 `gestor_cfg_voluntariado` | 🤝 Voluntariado | `voluntariado_config_view.py` | 🔒 |
| 🔒 `gestor_cfg_datas` | 🎊 Datas Comemorativas | `datas_comemorativas_view.py` | 🔒 |

---

## 6. Módulos Auxiliares / Acesso Público

> Estes módulos existem no código mas atualmente não têm chave de permissão controlada.

| Módulo | Arquivo | Observação |
|---|---|---|
| 🔗 Inscrição Pública | `views/inscricao_publica_view.py` | Acesso por link público (sem login) |
| 🔗 Formulário de Inscrição (interno) | `views/inscricao_view.py` | Rota interna para novos alunos |
| 🔗 Validador Público | `views/validador_view.py` | Deeplink de validação de cadastro |
| 🔗 Pesquisa de Satisfação (pública) | `views/pesquisa_satisfacao_view.py` | Rota pública `/pesquisa` |

---

## Resumo Executivo — Lacunas Identificadas

### Chaves existentes: **19**
`principal`, `frequencia`, `freq_conf_facial`, `portal_aluno`, `portal_prontuario`, `portal_ficha_impressao`, `relatorios_bi`, `rel_relatorios`, `rel_bi_dashboard`, `rel_bi_individual`, `rel_lista_freq`, `rel_plan_freq`, `rel_auditoria`, `rel_prestacao_ped`, `rel_avaliacoes`, `rel_patologias`, `rel_pa_lote`, `gestor`, `gestor_radar`, `gestor_satisfacao`, `gestor_emergencia`

### Chaves novas propostas: **41**
Ver tabelas acima (marcadas com 🆕).

### Chaves SuperAdmin (sem checkbox): **13**
Ver seção Gestor → Config (marcadas com 🔒). **Recomendação:** manter como SuperAdmin, sem expor ao RBAC de operadores.

---

## Prioridade de Implementação (sugestão)

| Prioridade | Grupo | Justificativa |
|---|---|---|
| 🔴 Alta | `rel_inativos` | Existe na view mas falta na permissão — alunos veem dados que não deveriam |
| 🔴 Alta | `portal_excluir_aluno` | Ação irreversível sem controle de permissão |
| 🟡 Média | Abas de Frequência (`freq_diario`, `freq_dossie`, etc.) | Controle granular do que o operador vê na chamada |
| 🟡 Média | Abas do Dashboard Portal (`portal_tab_*`) | Ocultar abas sensíveis (Triagem, Arquivo Morto) |
| 🟢 Baixa | Ações de prontuário (`portal_exportar_pdf`, etc.) | Úteis mas de baixo risco de vazamento |
| 🟢 Baixa | Config SuperAdmin (`gestor_cfg_*`) | Manter como está (sem checkbox) é seguro |
