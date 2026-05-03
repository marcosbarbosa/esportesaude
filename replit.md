# IMBRA System — Plataforma de Gestão MudaBrasil / MoveRight

## Visão Geral

Sistema web completo de gestão para estúdio de fitness/saúde, construído em **Python + Streamlit + Supabase**. Gerencia presença de alunos, prontuários médicos, aniversariantes, relatórios institucionais e CRM.

**Workflow:** `IMBRA Chamada (main.py)` → `streamlit run main.py` na porta 8000

---

## Stack Técnico

- **Backend / UI:** Python 3.11, Streamlit
- **Banco de dados:** Supabase (PostgreSQL via `supabase-py`)
- **Relatórios:** xlsxwriter (Excel), xhtml2pdf (PDF), python-docx (Word)
- **Reconhecimento facial:** DeepFace + RetinaFace + OpenCV Headless (import lazy)
- **QR Code:** qrcode (fichas de matrícula)
- **Outros:** pandas, plotly, st_keyup

---

## Estrutura Principal

```
main.py                          # Roteador principal, login, menu, rodapé fixo
database.py                      # Todas as queries Supabase
identidade.json                  # Configuração de branding (editável via UI)
utils/
  identidade.py                  # Módulo central de identidade visual (logos, cabeçalho, rodapé)
views/
  ficha_aluno_view.py            # Geração de fichas PDF (HTML)
  relatorio_view.py              # Excel (frequência), PDF (auditoria), Word (relatório mensal)
  relatorio_satisfacao_view.py   # Relatório de satisfação (Word/HTML)
  identidade_view.py             # Ecrã de edição da identidade visual (SuperAdmin)
  bi_dashboard_view.py           # Dashboard BI Prime
  conferencia_facial_view.py     # Reconhecimento facial (DeepFace)
  prontuario_dashboard.py        # Portal do aluno / prontuário
  validador_view.py              # Validação pública de QR Code
  inscricao_publica_view.py      # Inscrição pública
  radar_acolhimento_view.py      # Radar de acolhimento / retenção
  turmas_view.py                 # Gestão de turmas (SuperAdmin)
  backup_view.py                 # Backup e manutenção (SuperAdmin)
modulos_frequencia/
  tab_lista.py                   # Lista de presença
  tab_niver.py                   # Cartaz de aniversariantes (Word/PDF)
  tab_diario.py                  # Diário de aulas
  tab_dossie.py                  # Dossiê do aluno
  tab_inscricao.py               # Inscrição via tablet
  tab_tablet.py                  # Modo tablet
  tab_emergencia.py              # Ficha de emergência
```

---

## Tabelas Supabase

| Tabela | Campos principais |
|---|---|
| `alunos` | id, nome, turma_id, status, url_foto, whatsapp, cpf, data_nascimento |
| `turmas` | id, nome, horario, professor |
| `frequencia` | aluno_id, data_aula, status (P/F/J) |
| `diario_aulas` | turma_id, data, url_foto_grupo, observacoes |
| `prontuarios_imbra` | aluno_id, dados médicos / histórico |
| `pesquisas_satisfacao` | aluno_id, turma, periodo, notas, comentario |

---

## Módulo de Identidade Visual

**Ficheiro de config:** `identidade.json` (lido/escrito por `utils/identidade.py`)

**Campos configuráveis:**
- `titulo_projeto`, `subtitulo_projeto`
- `nome_organizacao`, `cnpj`, `endereco`, `telefone`, `email_contato`
- `site`, `instagram`
- `logo_principal` (ex: `logo-imbra.png`), `logo_secundaria` (ex: `logo-secretaria.png`)

**Funções exportadas por `utils/identidade.py`:**
- `get_config()` / `salvar_config(data)`
- `get_logo_b64(filename)` / `get_logo_data_url(filename)`
- `render_cabecalho_html(cfg, extra)` / `render_rodape_html(cfg)`
- `render_cabecalho_docx(doc, cfg)` / `render_rodape_docx(doc, cfg)`
- `render_cabecalho_excel(ws, wb, cfg)` / `render_rodape_excel(ws, wb, cfg, linha)`

**Ficheiros actualizados para usar o módulo centralizado:**
- `views/ficha_aluno_view.py` — logos, título, CNPJ na ficha PDF e no texto LGPD
- `views/relatorio_view.py` — Excel (header/footer), PDF auditoria (header), Word mensal (header)
- `views/relatorio_satisfacao_view.py` — logo principal, título
- `modulos_frequencia/tab_niver.py` — logo Word + logo PDF
- `views/validador_view.py` — logos + título do projecto
- `main.py` — rodapé login + rodapé fixo inferior

**Ecrã de edição:** `views/identidade_view.py` → menu "🎨 Identidade" (visível apenas para SuperAdmin)

---

## Perfis de Acesso

| Perfil | Acesso |
|---|---|
| Admin | Todos os menus excepto SuperAdmin |
| SuperAdmin | Tudo + Turmas, Mensagens, Mesclar Fichas, **Identidade Visual**, Backup |
| Aluno | Portal do Aluno, Frequência |

---

## Logos

Ficheiros de imagem na raiz do projecto:
- `logo-imbra.png` — Logo Instituto Muda Brasil (logo principal)
- `logo-secretaria.png` — Logo parceiro/secretaria (logo secundária)
- `logo-movimentacao.png` — Logo auxiliar
- `whatsapp.png` — Ícone WhatsApp

---

## Notas de Desenvolvimento

- O import do DeepFace é **lazy** (dentro da função `detectar_presenca_facial`) para não bloquear o arranque.
- `gerar_excel_planilha_frequencia()` ainda recebe `caminho_logo_muda, caminho_logo_sec` como parâmetros por compatibilidade, mas usa `get_config()` internamente — os parâmetros são ignorados.
- O `identidade.json` persiste entre restarts do servidor; não é necessária uma tabela Supabase para as configurações de branding.
