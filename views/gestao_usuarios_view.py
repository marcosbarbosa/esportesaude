import streamlit as st
from database import (
    listar_usuarios_sistema, atualizar_usuario_sistema, excluir_usuario_sistema,
    get_menu_permissoes_usuario, set_menu_permissoes_usuario, MENU_CATALOGO,
)

ADMIN_RESTRITO = "marcosbarbosa.am@gmail.com"


# ════════════════════════════════════════════════════════════════════════════
# BADGES
# ════════════════════════════════════════════════════════════════════════════

def _badge_ativo(ativo):
    if ativo is False:
        return (
            "<span style='background:#FEE2E2;color:#991B1B;"
            "padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>"
            "⛔ Inativo</span>"
        )
    return (
        "<span style='background:#D1FAE5;color:#065F46;"
        "padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>"
        "✅ Ativo</span>"
    )


def _badge_perfil(perfil):
    cores = {
        "SuperAdmin": ("#1D4ED8", "#DBEAFE"),
        "Admin":      ("#6D28D9", "#EDE9FE"),
        "Operador":   ("#0F766E", "#CCFBF1"),
    }
    c_txt, c_bg = cores.get(str(perfil), ("#374151", "#F3F4F6"))
    label = str(perfil or "—")
    return (
        f"<span style='background:{c_bg};color:{c_txt};"
        f"padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>"
        f"{label}</span>"
    )


# ════════════════════════════════════════════════════════════════════════════
# CATÁLOGO DE PERMISSÕES — hierarquia completa
# ════════════════════════════════════════════════════════════════════════════
#
# Estrutura de cada módulo pai:
#   emoji, titulo, cor_bg, cor_bd, cor_txt  → visual do expander
#   pai       → chave do módulo pai (checkbox "Acesso ao Menu")
#   descricao → texto de ajuda exibido no expander
#   secoes    → lista de seções internas, cada uma com:
#       titulo    → título da seção (banner colorido)
#       cor_bg / cor_bd / cor_txt → visual da seção
#       pai_cond  → (opcional) chave cujo valor True é pré-requisito
#       critica   → (opcional) True = borda/fundo vermelho de alerta
#       itens     → [(chave, label_curto, tooltip), ...]
#
# ATENÇÃO: chaves marcadas com 🔒 no mapeamento NÃO aparecem aqui —
# gestor_cfg_* permanecem restritas a SuperAdmin somente via código.
# ════════════════════════════════════════════════════════════════════════════

_GRUPOS_PERM = [
    # ── 1. INÍCIO ────────────────────────────────────────────────────────
    {
        "emoji": "🏠", "titulo": "Início",
        "cor_bg": "#EFF6FF", "cor_bd": "#1D4ED8", "cor_txt": "#1E3A8A",
        "pai": "principal",
        "descricao": "Painel inicial com resumo geral do dia (KPIs, agenda, risco, aniversariantes).",
        "secoes": [
            {
                "titulo": "⚙️ Ações e Blocos do Painel",
                "cor_bg": "#F0F9FF", "cor_bd": "#38BDF8", "cor_txt": "#0369A1",
                "itens": [
                    ("principal_snapshot_lote",
                     "⚙️ Processar em Lote",
                     "Acesso ao botão 'Processar em Lote' que regenera o snapshot de KPIs."),
                    ("principal_agenda",
                     "🗓️ Agenda do Dia",
                     "Ver bloco de agendamentos médicos do dia no painel inicial."),
                    ("principal_risco",
                     "🚨 Cards de Risco",
                     "Ver cards de alunos em risco crítico e moderado."),
                    ("principal_niver",
                     "🎂 Aniversariantes",
                     "Ver card de aniversariantes do dia no painel inicial."),
                ],
            },
        ],
    },

    # ── 2. FREQUÊNCIA ─────────────────────────────────────────────────────
    {
        "emoji": "✅", "titulo": "Frequência",
        "cor_bg": "#F0FDF4", "cor_bd": "#16A34A", "cor_txt": "#14532D",
        "pai": "frequencia",
        "descricao": "Registro de presença nas aulas. Controle de abas e ferramentas da chamada.",
        "secoes": [
            {
                "titulo": "📑 Abas da Chamada",
                "cor_bg": "#F0FDF4", "cor_bd": "#4ADE80", "cor_txt": "#166534",
                "itens": [
                    ("freq_chamada_tablet",
                     "📱 Chamada Tablet",
                     "Aba de chamada via tablet (modo quiosque)."),
                    ("freq_diario",
                     "📝 Diário de Aulas",
                     "Aba do Diário — objetivos e observações do dia."),
                    ("freq_dossie",
                     "🖨️ Dossiê",
                     "Aba de emissão do dossiê do aluno direto da chamada."),
                    ("freq_emergencia_tab",
                     "🚨 Emergência",
                     "Aba do protocolo de emergência dentro da tela de frequência."),
                    ("freq_lgpd",
                     "🔒 LGPD",
                     "Aba LGPD para gestão de consentimentos de uso de imagem."),
                    ("freq_atestado",
                     "🏥 Atestado",
                     "Aba de registro e acompanhamento de atestados médicos."),
                    ("freq_niver",
                     "🎂 Aniversariantes",
                     "Aba de aniversariantes do dia na tela de chamada."),
                    ("freq_admin",
                     "📅 Admin (Dias/Anamnese)",
                     "Aba restrita: dias letivos registrados e anamnese em lote."),
                ],
            },
            {
                "titulo": "⚙️ Ferramentas e Ações",
                "cor_bg": "#ECFDF5", "cor_bd": "#6EE7B7", "cor_txt": "#065F46",
                "itens": [
                    ("freq_conf_facial",
                     "📸 Conf. Facial",
                     "Verificação de presença por reconhecimento fotográfico."),
                    ("freq_niver_pdf",
                     "🎁 PDF Parabéns",
                     "Gerar PDF de cartão de parabéns para aniversariantes."),
                    ("freq_admin_validade_anamnese",
                     "📋 Salvar Validade Anamnese",
                     "Salvar/atualizar a data de validade da anamnese individual."),
                    ("freq_admin_excluir_aula",
                     "🗑️ Excluir Dia Letivo",
                     "Excluir o registro de um dia de aula (ação irreversível)."),
                ],
            },
        ],
    },

    # ── 3. PORTAL DO ALUNO ────────────────────────────────────────────────
    {
        "emoji": "🩺", "titulo": "Portal do Aluno",
        "cor_bg": "#FFF7ED", "cor_bd": "#EA580C", "cor_txt": "#7C2D12",
        "pai": "portal_aluno",
        "descricao": "Cadastros, prontuários, medições e fichas dos alunos.",
        "secoes": [
            {
                "titulo": "📑 Abas do Dashboard",
                "cor_bg": "#FFF7ED", "cor_bd": "#FB923C", "cor_txt": "#9A3412",
                "itens": [
                    ("portal_tab_alunos",
                     "👥 Alunos",
                     "Lista principal de alunos ativos com busca e filtros."),
                    ("portal_tab_patologias",
                     "🧬 Patologias",
                     "Anamnese clínica e patologias em visão consolidada."),
                    ("portal_tab_cracha",
                     "🪪 Cara-crachá",
                     "Geração e impressão de crachás dos alunos."),
                    ("portal_tab_novo_aluno",
                     "📝 Novo Aluno",
                     "Formulário de cadastro de novo aluno."),
                    ("portal_tab_triagem",
                     "🔍 Triagem",
                     "Aba de triagem de novos ingressantes."),
                    ("portal_tab_agenda",
                     "🗓️ Agenda Médica",
                     "Gerenciamento de agendamentos médicos."),
                    ("portal_tab_medidos",
                     "📊 Já Medidos",
                     "Lista de alunos com medição registrada no período."),
                    ("portal_tab_sem_medicoes",
                     "⚠️ Sem Medições",
                     "Alunos sem nenhuma medição registrada."),
                    ("portal_tab_inativos",
                     "🗄️ Arquivo Morto",
                     "Aba de alunos inativos e arquivados."),
                    ("portal_tab_pa",
                     "🩸 PA em Lote",
                     "Lançamento de pressão arterial em lote pelo dashboard."),
                ],
            },
            {
                "titulo": "🩺 Prontuário Individual",
                "cor_bg": "#FEF3C7", "cor_bd": "#F59E0B", "cor_txt": "#78350F",
                "pai_cond": "portal_prontuario",
                "itens": [
                    ("portal_prontuario",
                     "🩺 Abrir Prontuário",
                     "Acessar e editar a ficha individual do aluno."),
                    ("portal_pront_perfil",
                     "👤 Perfil e Contato",
                     "Aba de dados pessoais, endereço e contatos."),
                    ("portal_pront_medicao",
                     "📝 Nova Medição",
                     "Registrar nova medição clínica (peso, pressão, etc.)."),
                    ("portal_pront_historico",
                     "📊 Histórico Clínico",
                     "Ver histórico completo de medições e evolução."),
                    ("portal_pront_docs",
                     "📂 Docs. Legais",
                     "Aba de documentação legal (RG, receituário, atestado)."),
                    ("portal_pront_social",
                     "🏘️ Perfil Social",
                     "Aba de perfil socioeconômico do aluno."),
                    ("portal_pront_dores",
                     "🩻 Mapa de Dores",
                     "Aba de registro do mapa de dores corporais."),
                    ("portal_pront_pa_ind",
                     "🩺 PA Individual",
                     "Histórico de pressão arterial individual."),
                ],
            },
            {
                "titulo": "📄 Exportação e Impressão",
                "cor_bg": "#FFFBEB", "cor_bd": "#FCD34D", "cor_txt": "#92400E",
                "itens": [
                    ("portal_ficha_impressao",
                     "🖨️ Central de Impressão",
                     "Central de impressão de fichas de matrícula."),
                    ("portal_exportar_pdf",
                     "📄 Exportar PDF Dossiê",
                     "Exportar dossiê clínico completo em PDF."),
                    ("portal_exportar_word",
                     "📝 Exportar Word",
                     "Exportar prontuário em formato Word (.docx)."),
                ],
            },
            {
                "titulo": "⚙️ Ações Administrativas",
                "cor_bg": "#F5F3FF", "cor_bd": "#8B5CF6", "cor_txt": "#4C1D95",
                "itens": [
                    ("portal_lgpd_toggle",
                     "✅ Autorizar/Revogar Imagem",
                     "Autorizar ou revogar uso de imagem do aluno (LGPD)."),
                    ("portal_atestado_arquivar",
                     "🏥 Arquivar Atestado",
                     "Arquivar atestado médico no histórico do aluno."),
                    ("portal_agendamento_criar",
                     "🗓️ Criar Agendamento",
                     "Criar ou editar agendamentos médicos do aluno."),
                    ("portal_validador",
                     "🔗 Validador Público",
                     "Gerar e visualizar link de validação de cadastro."),
                    ("portal_merge",
                     "🔀 Mesclar Fichas",
                     "Mesclar fichas de alunos duplicados (SuperAdmin/Admin)."),
                ],
            },
            {
                "titulo": "⚠️ Ações Críticas",
                "cor_bg": "#FEF2F2", "cor_bd": "#DC2626", "cor_txt": "#7F1D1D",
                "critica": True,
                "itens": [
                    ("portal_arquivar_aluno",
                     "🗄️ Arquivar Aluno",
                     "Inativar aluno com motivo de saída. Parcialmente reversível."),
                    ("portal_reativar_aluno",
                     "♻️ Reativar Aluno",
                     "Reativar um aluno inativo de volta à turma."),
                    ("portal_excluir_aluno",
                     "🗑️ Excluir Permanentemente",
                     "⚠️ IRREVERSÍVEL — Exclui o aluno e todos os dados do sistema."),
                ],
            },
        ],
    },

    # ── 4. RELATÓRIOS & BI ────────────────────────────────────────────────
    {
        "emoji": "📊", "titulo": "Relatórios & BI",
        "cor_bg": "#F5F3FF", "cor_bd": "#7C3AED", "cor_txt": "#4C1D95",
        "pai": "relatorios_bi",
        "descricao": "Relatórios gerenciais, prestação de contas e análise de dados.",
        "secoes": [
            {
                "titulo": "📂 Sub-Módulos",
                "cor_bg": "#F5F3FF", "cor_bd": "#A78BFA", "cor_txt": "#5B21B6",
                "itens": [
                    ("rel_relatorios",
                     "📋 Relatórios",
                     "Acesso à aba de relatórios (Prestação de Contas etc.)."),
                    ("rel_bi_dashboard",
                     "📊 BI Dashboard",
                     "Painel analítico com KPIs gerenciais."),
                    ("rel_bi_individual",
                     "👤 BI Individual",
                     "Relatório de evolução individual por aluno."),
                ],
            },
            {
                "titulo": "↳ Abas dentro de 📋 Relatórios",
                "cor_bg": "#FAF5FF", "cor_bd": "#C4B5FD", "cor_txt": "#6D28D9",
                "pai_cond": "rel_relatorios",
                "itens": [
                    ("rel_lista_freq",
                     "📋 Lista Freq. Oficial",
                     "Frequência por aluno e turma para um período."),
                    ("rel_plan_freq",
                     "📊 Plan. Frequência",
                     "Planilha de frequência com presenças, faltas e controle."),
                    ("rel_auditoria",
                     "🔎 Auditoria",
                     "Auditoria de cadastros e documentos pendentes."),
                    ("rel_prestacao_ped",
                     "🏆 Prestação Pedag.",
                     "Relatório pedagógico mensal com exportação Word."),
                    ("rel_avaliacoes",
                     "🧪 Avaliações",
                     "Alunos pendentes de avaliação física."),
                    ("rel_patologias",
                     "🧬 Patologias",
                     "Anamnese clínica e condições de saúde registradas."),
                    ("rel_pa_lote",
                     "🩺 Coleta PA em Lote",
                     "Registro de pressão arterial em lote por turma."),
                    ("rel_inativos",
                     "🗄️ Alunos Inativos",
                     "Relatório de alunos inativos e arquivados."),
                ],
            },
            {
                "titulo": "⚙️ Ações de Exportação",
                "cor_bg": "#EDE9FE", "cor_bd": "#DDD6FE", "cor_txt": "#4C1D95",
                "itens": [
                    ("rel_exportar_excel",
                     "📥 Exportar Excel/CSV",
                     "Baixar relatórios de frequência em Excel ou CSV."),
                    ("rel_exportar_word",
                     "📝 Gerar Word Pedagógico",
                     "Exportar prestação pedagógica em Word."),
                    ("rel_satisfacao",
                     "📊 Dados de Satisfação",
                     "Incluir dados de satisfação no relatório anual."),
                ],
            },
        ],
    },

    # ── 5. GESTOR ─────────────────────────────────────────────────────────
    {
        "emoji": "🎯", "titulo": "Gestor",
        "cor_bg": "#FFF1F2", "cor_bd": "#BE123C", "cor_txt": "#881337",
        "pai": "gestor",
        "descricao": "Ferramentas de monitoramento, satisfação e emergência.",
        "secoes": [
            {
                "titulo": "📑 Ferramentas do Gestor",
                "cor_bg": "#FFF1F2", "cor_bd": "#FDA4AF", "cor_txt": "#9F1239",
                "itens": [
                    ("gestor_radar",
                     "💙 Radar de Acolhimento",
                     "Monitoramento e alertas de acolhimento individual."),
                    ("gestor_satisfacao",
                     "⭐ Satisfação",
                     "Pesquisas de satisfação e impacto na saúde."),
                    ("gestor_emergencia",
                     "🚨 Emergência",
                     "Protocolo e contatos de emergência."),
                ],
            },
        ],
    },
]


# ════════════════════════════════════════════════════════════════════════════
# HELPER: renderiza uma seção interna do expander
# ════════════════════════════════════════════════════════════════════════════

def _render_secao_perm(secao, novas_perms, perm_atual, uid, pai_ativo):
    """Renderiza um bloco de checkboxes para uma seção dentro de um módulo.

    Args:
        secao      : dict com titulo, itens, pai_cond, critica e cores
        novas_perms: dict mutável onde os novos valores são gravados
        perm_atual : dict com permissões atuais vindas do banco
        uid        : id do usuário sendo configurado
        pai_ativo  : bool — o módulo pai está habilitado?
    """
    pai_cond = secao.get("pai_cond")
    if pai_cond:
        sec_ativo = pai_ativo and novas_perms.get(pai_cond, True)
    else:
        sec_ativo = pai_ativo

    critica = secao.get("critica", False)
    cor_bg  = secao.get("cor_bg", "#F8FAFC")
    cor_bd  = secao.get("cor_bd", "#94A3B8")
    cor_txt = secao.get("cor_txt", "#1E293B")

    # Banner da seção
    alerta = (
        " <span style='font-size:10px;color:#DC2626;font-weight:700;'>"
        "⚠️ Permissões de alto risco</span>"
        if critica else ""
    )
    dica_off = (
        f" <span style='color:#94A3B8;font-size:10px;'>"
        f"(habilite '{pai_cond}' acima para editar)</span>"
        if (pai_cond and not sec_ativo) else ""
    )
    st.markdown(
        f"<div style='background:{cor_bg};border-left:3px solid {cor_bd};"
        f"border-radius:4px;padding:4px 10px;margin:6px 0 4px 0;'>"
        f"<span style='color:{cor_txt};font-weight:600;font-size:12px;'>"
        f"{secao['titulo']}</span>{alerta}{dica_off}</div>",
        unsafe_allow_html=True,
    )

    # Checkboxes em linhas de 4
    itens = secao["itens"]
    for row_start in range(0, len(itens), 4):
        row = itens[row_start: row_start + 4]
        cols = st.columns(4)
        for i, (chave, label, tip) in enumerate(row):
            val_atual = perm_atual.get(chave, True)
            tip_final = (
                tip if sec_ativo
                else "⚠️ Habilite o módulo pai para configurar esta opção."
            )
            val_novo = cols[i].checkbox(
                label,
                value=val_atual,
                key=f"perm_{uid}_{chave}",
                disabled=not sec_ativo,
                help=tip_final,
            )
            novas_perms[chave] = val_novo and sec_ativo


# ════════════════════════════════════════════════════════════════════════════
# TELA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

def tela_gestao_usuarios():
    email_session = (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or st.session_state.get("email")
        or ""
    ).strip().lower()

    if email_session != ADMIN_RESTRITO.lower():
        st.warning(
            "🔒 Esta área é restrita ao administrador principal do sistema. "
            f"Somente **{ADMIN_RESTRITO}** tem acesso."
        )
        return

    st.markdown("""
        <div style='background:#F0FDF4;border-left:4px solid #16A34A;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#14532D;'>👥 Gestão de Operadores</strong><br>
            <span style='color:#15803D;font-size:13px;'>
                Edite nome, e-mail ou senha dos operadores que fazem login no sistema.
                Inative acessos temporariamente ou exclua permanentemente.
                Apenas o administrador principal tem acesso a esta tela.
            </span>
        </div>
    """, unsafe_allow_html=True)

    edit_id = st.session_state.get("_usr_edit_id")

    usuarios, erro_bd = listar_usuarios_sistema()

    if erro_bd:
        st.error(
            f"❌ Erro ao acessar a tabela `usuarios` no banco de dados:\n\n`{erro_bd}`\n\n"
            "Verifique se a tabela existe e se as colunas estão criadas."
        )
        return

    if usuarios and "ativo" not in usuarios[0]:
        st.warning(
            "⚠️ A coluna `ativo` ainda não existe na tabela `usuarios`. "
            "Execute o SQL abaixo no **Supabase → SQL Editor** para habilitar inativar/reativar:"
        )
        st.code(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo boolean NOT NULL DEFAULT true;",
            language="sql",
        )
        st.markdown("---")

    if usuarios and "perfil" not in usuarios[0]:
        st.info(
            "ℹ️ A coluna `perfil` não existe ainda. Execute no **Supabase → SQL Editor**:\n\n"
            "`ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perfil TEXT DEFAULT 'Operador';`"
        )
        st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # EDITOR DE USUÁRIO
    # ══════════════════════════════════════════════════════════════════════
    if edit_id:
        u = next((x for x in usuarios if x["id"] == edit_id), None)
        if u is None:
            st.error("Operador não encontrado.")
            st.session_state.pop("_usr_edit_id", None)
            st.rerun()

        st.markdown(f"### ✏️ Editando operador: **{u.get('nome', '—')}**")

        with st.form("form_editar_usuario"):
            c1, c2 = st.columns(2)
            novo_nome  = c1.text_input("Nome completo", value=u.get("nome", ""))
            novo_email = c2.text_input("E-mail de login", value=u.get("email", ""))
            nova_senha = st.text_input(
                "Nova senha (deixe em branco para não alterar)",
                value="", type="password",
                help="Mínimo 6 caracteres.",
            )

            ativo_atual = u.get("ativo", True)
            if ativo_atual is None:
                ativo_atual = True
            novo_ativo = st.toggle(
                "Conta ativa", value=bool(ativo_atual),
                help="Desative para bloquear o acesso sem excluir o cadastro.",
            )

            perfil_opcoes = ["Operador", "Admin", "SuperAdmin"]
            perfil_atual = u.get("perfil") or "Operador"
            if perfil_atual not in perfil_opcoes:
                perfil_opcoes.append(perfil_atual)
            novo_perfil = st.selectbox(
                "Perfil de acesso",
                options=perfil_opcoes,
                index=perfil_opcoes.index(perfil_atual),
            )

            st.markdown("---")
            cs1, cs2 = st.columns(2)
            btn_salvar   = cs1.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
            btn_cancelar = cs2.form_submit_button("❌ Cancelar", use_container_width=True)

        if btn_cancelar:
            st.session_state.pop("_usr_edit_id", None)
            st.rerun()

        if btn_salvar:
            if not novo_nome.strip():
                st.error("O nome não pode ficar em branco.")
            elif not novo_email.strip():
                st.error("O e-mail não pode ficar em branco.")
            else:
                payload = {
                    "nome":   novo_nome.strip(),
                    "email":  novo_email.strip().lower(),
                    "ativo":  novo_ativo,
                    "perfil": novo_perfil,
                }
                if nova_senha.strip():
                    if len(nova_senha.strip()) < 6:
                        st.error("A senha precisa ter no mínimo 6 caracteres.")
                        st.stop()
                    payload["senha"] = nova_senha.strip()
                ok, msg = atualizar_usuario_sistema(edit_id, payload)
                if ok:
                    st.success(msg)
                    st.session_state.pop("_usr_edit_id", None)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        return

    # ══════════════════════════════════════════════════════════════════════
    # LISTAGEM EM GRID
    # ══════════════════════════════════════════════════════════════════════
    if not usuarios:
        st.info(
            "Nenhum operador cadastrado ainda. "
            "Crie o primeiro operador pelo formulário de cadastro do sistema."
        )
        return

    st.caption(f"{len(usuarios)} operador(es) cadastrado(s)")

    col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2.5, 2.5, 1.2, 1.2, 1.8])
    col_h1.markdown("**Nome**")
    col_h2.markdown("**E-mail**")
    col_h3.markdown("**Perfil**")
    col_h4.markdown("**Status**")
    col_h5.markdown("**Ações**")
    st.markdown("<hr style='margin:4px 0 8px 0;'>", unsafe_allow_html=True)

    for u in usuarios:
        uid   = u["id"]
        ativo = u.get("ativo", True)
        if ativo is None:
            ativo = True
        is_me = u.get("email", "").strip().lower() == email_session

        c1, c2, c3, c4, c5 = st.columns([2.5, 2.5, 1.2, 1.2, 1.8])
        c1.markdown(f"{'**[Você]** ' if is_me else ''}{u.get('nome', '—')}")
        c2.markdown(f"<small>{u.get('email', '—')}</small>", unsafe_allow_html=True)
        c3.markdown(_badge_perfil(u.get("perfil")), unsafe_allow_html=True)
        c4.markdown(_badge_ativo(ativo), unsafe_allow_html=True)

        with c5:
            ba, bb, bc = st.columns(3)

            if ba.button("✏️", key=f"usr_ed_{uid}", help="Editar dados e senha"):
                st.session_state["_usr_edit_id"] = uid
                st.rerun()

            lbl_tog = "⛔" if ativo else "✅"
            tip_tog = "Inativar acesso" if ativo else "Reativar acesso"
            if bb.button(lbl_tog, key=f"usr_tog_{uid}", help=tip_tog, disabled=is_me):
                ok, msg = atualizar_usuario_sistema(uid, {"ativo": not ativo})
                if ok:
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

            if bc.button("🗑️", key=f"usr_del_{uid}", help="Excluir permanentemente", disabled=is_me):
                st.session_state[f"_usr_conf_del_{uid}"] = True
                st.rerun()

        if st.session_state.get(f"_usr_conf_del_{uid}"):
            st.warning(
                f"⚠️ Excluir **{u.get('nome', '—')}** ({u.get('email', '—')}) permanentemente? "
                "Esta ação não pode ser desfeita."
            )
            cd1, cd2, _ = st.columns([1.5, 1.5, 4])
            if cd1.button("✅ Confirmar exclusão", key=f"usr_del_ok_{uid}", type="primary"):
                ok, msg = excluir_usuario_sistema(uid, email_session)
                if ok:
                    st.session_state.pop(f"_usr_conf_del_{uid}", None)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            if cd2.button("Cancelar", key=f"usr_del_no_{uid}"):
                st.session_state.pop(f"_usr_conf_del_{uid}", None)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # PERMISSÕES DE MENU
    # ══════════════════════════════════════════════════════════════════════
    st.markdown(
        "<hr style='margin:28px 0 18px 0;border-color:#CBD5E1;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style='background:#EFF6FF;border-left:4px solid #1D4ED8;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#1E3A8A;'>🔐 Permissões de Menu</strong><br>
            <span style='color:#1D4ED8;font-size:13px;'>
                Controle quais seções do sistema cada operador pode acessar.
                <b>SuperAdmin</b> sempre tem acesso completo e não aparece aqui.
                Desmarcar um menu o torna invisível para o operador.
                As sub-opções só tomam efeito quando o módulo pai estiver <em>ativo</em>.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filtra usuários que não são o próprio SuperAdmin
    usuarios_filtraveis = [
        u for u in usuarios
        if u.get("email", "").strip().lower() != ADMIN_RESTRITO.lower()
    ]

    if not usuarios_filtraveis:
        st.info("Nenhum operador disponível para configurar permissões.")
        return

    # ── Seletor de operador ───────────────────────────────────────────────
    _nomes_perm = {
        f"{u.get('nome', '—')} ({u.get('email', '—')})": u
        for u in usuarios_filtraveis
    }
    _sel_label = st.selectbox(
        "👤 Selecionar operador:",
        options=list(_nomes_perm.keys()),
        key="perm_usr_sel",
    )
    _usr_perm  = _nomes_perm[_sel_label]
    _uid_perm  = _usr_perm["id"]
    _perm_atual = get_menu_permissoes_usuario(_uid_perm)

    st.markdown(
        f"<small style='color:#64748B;'>Configurando permissões para: "
        f"<strong>{_usr_perm.get('nome','—')}</strong> — "
        f"perfil <em>{_usr_perm.get('perfil','—')}</em> — "
        f"{sum(1 for v in _perm_atual.values() if v is True)} itens liberados atualmente</small>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='color:#475569;font-size:12px;margin:10px 0 4px 0;'>"
        "🔑 <b>Acesso ao Menu</b> controla se o módulo inteiro aparece para o operador. "
        "As sub-opções ficam desabilitadas quando o módulo pai estiver <em>desmarcado</em>. "
        "Passe o cursor sobre qualquer item para ver a descrição detalhada."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Dict que acumulará os novos valores da UI ─────────────────────────
    _novas_perms: dict = {}

    # ── Renderiza um expander por módulo pai ──────────────────────────────
    for _g in _GRUPOS_PERM:
        _chave_pai  = _g["pai"]
        _val_pai_db = _perm_atual.get(_chave_pai, True)

        # Conta quantos filhos deste grupo estão desativados
        _todas_chaves_grupo = [_chave_pai] + [
            chave
            for sec in _g.get("secoes", [])
            for (chave, _, _) in sec.get("itens", [])
        ]
        _n_off = sum(
            1 for k in _todas_chaves_grupo
            if _perm_atual.get(k, True) is False
        )
        _resumo = (
            f" — ⚠️ {_n_off} item(s) desativado(s)"
            if _n_off > 0 else ""
        )

        _exp_label = (
            f"{_g['emoji']} **{_g['titulo']}**"
            f"{'  *(acesso bloqueado)*' if not _val_pai_db else ''}"
            f"{_resumo}"
        )

        with st.expander(_exp_label, expanded=(_n_off > 0 or not _val_pai_db)):

            # Descrição do módulo
            st.markdown(
                f"<div style='background:{_g['cor_bg']};border-left:4px solid {_g['cor_bd']};"
                f"border-radius:6px;padding:6px 12px;margin-bottom:10px;'>"
                f"<span style='color:{_g['cor_txt']};font-size:12px;'>"
                f"{_g['descricao']}</span></div>",
                unsafe_allow_html=True,
            )

            # Checkbox do módulo pai (acesso geral)
            _val_pai_novo = st.checkbox(
                f"🔓 Acesso ao módulo **{_g['titulo']}**",
                value=_val_pai_db,
                key=f"perm_{_uid_perm}_{_chave_pai}",
                help=f"Habilitar/desabilitar o módulo '{_g['titulo']}' inteiro para este operador.",
            )
            _novas_perms[_chave_pai] = _val_pai_novo

            if not _val_pai_novo:
                st.caption(
                    f"⚠️ Com o módulo desabilitado, todas as {len(_todas_chaves_grupo) - 1} "
                    f"sub-opções abaixo ficam automaticamente inativas."
                )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # Seções internas
            for _sec in _g.get("secoes", []):
                _render_secao_perm(
                    secao=_sec,
                    novas_perms=_novas_perms,
                    perm_atual=_perm_atual,
                    uid=_uid_perm,
                    pai_ativo=_val_pai_novo,
                )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Botão de salvamento — merge seguro ────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    _btn_salvar_perm = st.button(
        "💾 Salvar Permissões",
        type="primary",
        key=f"perm_salvar_{_uid_perm}",
        use_container_width=False,
    )

    if _btn_salvar_perm:
        # Merge seguro: começa com o que já está no banco (preserva chaves
        # não exibidas na UI), sobrescreve apenas as chaves gerenciadas aqui.
        _merged = dict(_perm_atual)
        _merged.update(_novas_perms)

        _ok_perm, _msg_perm = set_menu_permissoes_usuario(_uid_perm, _merged)
        if _ok_perm:
            _n_ativos   = sum(1 for v in _novas_perms.values() if v is True)
            _n_inativos = sum(1 for v in _novas_perms.values() if v is False)
            st.success(
                f"✅ Permissões de **{_usr_perm.get('nome','—')}** salvas! "
                f"({_n_ativos} itens ativos · {_n_inativos} bloqueados)"
            )
            # Invalida cache de permissões se for o próprio usuário logado
            if st.session_state.get("usuario_id") == _uid_perm:
                st.session_state.pop("_menu_perms_cache", None)
                st.session_state.pop("_menu_perms_version", None)
        else:
            st.error(f"❌ {_msg_perm}")
