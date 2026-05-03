# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_lista.py
# 🏷️ VERSÃO: 2.0 (Admin Security Edition)
# 📅 DATA: 04/04/2026 | 🕒 HORA: 16:00
# ⚙️ FUNÇÃO: Lista com trava de exclusão integrada com database.py v3.1.
# ==============================================================================
import streamlit as st
import pandas as pd
from database import alternar_presenca, excluir_aluno_completo

def toggle_presence_btn(aluno_id, data_aula, atual_status, nome_aluno):
    if alternar_presenca(aluno_id, data_aula, not atual_status): 
        st.toast(f"✅ {nome_aluno} ATUALIZADO.")
    else: 
        st.toast("🚨 Erro ao guardar presença.")

def renderizar_aba_frequencia(df_alunos, data_aula, turma_selecionada, presencas_turma_geral, is_global_search, chave_unica):
    if df_alunos.empty: 
        return

    # 🔐 IDENTIFICAÇÃO DO USUÁRIO
    usuario_email = st.session_state.get('email_usuario', '').lower().strip()
    eh_admin = (usuario_email == "marcosbarbosa.am@gmail.com")

    css_botoes = ""

    for i in range(0, len(df_alunos), 3):
        if i > 0: 
            st.markdown('<div style="margin-top: -30px;"></div>', unsafe_allow_html=True)

        cols = st.columns(3)
        for j, (_, row) in enumerate(df_alunos.iloc[i : i + 3].iterrows()):
            with cols[j]:
                ja_presente = presencas_turma_geral.get(row["id"], False)
                border_color = "#dc3545" if ja_presente else "#dddddd"
                css_botoes += f"#b_{row['id']} div[data-testid='stButton'] button {{ border: 2px solid {border_color} !important; }}"

                with st.container(border=False):
                    # Ajuste da largura das colunas conforme permissão
                    layout_cols = [1.5, 5, 1.5, 1.5] if eh_admin else [1.5, 6.5, 1.5]
                    c_img, c_btn, c_ed, *c_del = st.columns(layout_cols, gap="small", vertical_alignment="center")

                    with c_img:
                        u_f = row.get("url_foto")
                        if pd.notna(u_v := u_f) and str(u_v).strip(): 
                            st.markdown(f'<img src="{u_v}" class="zoom-avatar">', unsafe_allow_html=True)
                        else: 
                            st.markdown('👤')

                    with c_btn:
                        st.markdown(f'<div id="b_{row["id"]}">', unsafe_allow_html=True)
                        if st.button(row['nome'][:22].upper(), key=f"f_{row['id']}", type="primary" if ja_presente else "secondary", use_container_width=True):
                            toggle_presence_btn(row["id"], data_aula, ja_presente, row["nome"])
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                    with c_ed:
                        if st.button("✏️", key=f"e_{row['id']}", use_container_width=True, help="Editar Aluno"):
                            st.session_state.aluno_prontuario = row
                            st.session_state.menu_atual = "Prontuário"
                            st.rerun()

                    # 🗑️ BLOCO DE EXCLUSÃO (EXCLUSIVO PARA O MARCOS)
                    if eh_admin and c_del:
                        with c_del[0]:
                            if st.button("🗑️", key=f"d_{row['id']}", use_container_width=True, help="EXCLUIR"):
                                sucesso, msg = excluir_aluno_completo(row['id'], usuario_email)
                                if sucesso:
                                    st.toast(msg, icon="✅")
                                    st.rerun()
                                else:
                                    st.error(msg)

    st.markdown(f"<style>{css_botoes}</style>", unsafe_allow_html=True)