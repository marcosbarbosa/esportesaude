# ==============================================================================
# 📄 Arquivo: views/turmas_view.py
# 🏷️ VERSÃO: 1.0 (CRUD de Entidade Forte)
# ⚙️ FUNÇÃO: Gestão dinâmica do catálogo de turmas.
# ==============================================================================
import streamlit as st
import pandas as pd
from database import get_todas_turmas, adicionar_turma, atualizar_turma, excluir_turma

def tela_gestao_turmas():
    st.title("🏫 Gestão de Turmas")
    st.write("Catálogo oficial de turmas. Cadastre, edite os horários ou inative turmas antigas.")
    st.divider()

    df_turmas = get_todas_turmas()

    # --- SESSÃO DE CADASTRO ---
    with st.expander("➕ Cadastrar Nova Turma", expanded=False):
        c1, c2, c3 = st.columns([2, 1, 1])
        n_nome = c1.text_input("Nome Completo da Turma:", placeholder="Ex: S-11H - Seg/Qua/Sex (11H às 12H)")
        n_dias = c2.selectbox("Dias da Semana:", ["Seg/Qua/Sex", "Ter/Qui", "Sáb/Dom", "Outros"])
        n_hora = c3.time_input("Horário de Início:")

        if st.button("💾 Salvar Turma", type="primary"):
            if len(n_nome) < 5:
                st.warning("Preencha um nome descritivo para a turma.")
            else:
                sucesso, msg = adicionar_turma(n_nome, n_hora.strftime("%H:%M"), n_dias)
                if sucesso:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- GRID DE TURMAS ---
    if df_turmas.empty:
        st.info("Nenhuma turma cadastrada no banco de dados.")
        return

    st.markdown("### 📋 Turmas Cadastradas")

    # CSS para alinhar botões do grid
    st.markdown("""
        <style>
            .stButton button { width: 100%; padding: 4px; }
        </style>
    """, unsafe_allow_html=True)

    # Cabeçalho do Grid
    h1, h2, h3, h4 = st.columns([3, 1.5, 1, 2])
    h1.markdown("**Nome da Turma**")
    h2.markdown("**Dias e Horário**")
    h3.markdown("**Status**")
    h4.markdown("**Ações**")
    st.markdown("<hr style='margin: 4px 0px 12px 0px;'>", unsafe_allow_html=True)

    for _, t in df_turmas.iterrows():
        c1, c2, c3, c4 = st.columns([3, 1.5, 1, 2], vertical_alignment="center")

        c1.write(t['nome'])
        c2.write(f"{t['dias_semana']} às {t['horario']}")

        cor_status = "green" if t['status'] == "Ativa" else "red"
        c3.markdown(f"<span style='color: {cor_status}; font-weight:bold;'>{t['status']}</span>", unsafe_allow_html=True)

        with c4:
            b1, b2 = st.columns(2)
            if b1.button("✏️ Editar", key=f"ed_t_{t['id']}"):
                st.session_state[f"edit_turma_{t['id']}"] = True
            if b2.button("🗑️ Excluir", key=f"del_t_{t['id']}", type="secondary"):
                sucesso, msg = excluir_turma(t['id'])
                if sucesso:
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)

        # Modo de Edição Aberto
        if st.session_state.get(f"edit_turma_{t['id']}", False):
            with st.container(border=True):
                st.markdown(f"**Editando:** {t['nome']}")
                e1, e2, e3 = st.columns([2, 1, 1])
                e_nome = e1.text_input("Novo Nome:", value=t['nome'], key=f"e_n_{t['id']}")
                e_stat = e2.selectbox("Status:", ["Ativa", "Inativa"], index=0 if t['status']=="Ativa" else 1, key=f"e_s_{t['id']}")

                # Botões de salvar edição
                eb1, eb2 = st.columns(2)
                if eb1.button("Salvar Modificações", type="primary", key=f"sv_e_{t['id']}"):
                    sucesso, msg = atualizar_turma(t['id'], e_nome, t['horario'], t['dias_semana'], e_stat)
                    if sucesso:
                        st.session_state[f"edit_turma_{t['id']}"] = False
                        st.toast(msg, icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)

                if eb2.button("Cancelar", key=f"cn_e_{t['id']}"):
                    st.session_state[f"edit_turma_{t['id']}"] = False
                    st.rerun()

        st.markdown("<hr style='margin: 4px 0px; border-color:#F1F5F9;'>", unsafe_allow_html=True)