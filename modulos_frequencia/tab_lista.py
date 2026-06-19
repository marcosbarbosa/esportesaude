# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_lista.py
# 🏷️ VERSÃO: 2.0 (Admin Security Edition)
# 📅 DATA: 04/04/2026 | 🕒 HORA: 16:00
# ⚙️ FUNÇÃO: Lista com trava de exclusão integrada com database.py v3.1.
# ==============================================================================
import streamlit as st
import pandas as pd
from database import alternar_presenca, excluir_aluno_completo

_CSS_LISTA = """
<style>
.freq-avatar {
    display: block;
    width: 42px !important; height: 42px !important;
    min-width: 42px; min-height: 42px;
    max-width: 42px; max-height: 42px;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    object-fit: cover;
    object-position: center center;
    flex-shrink: 0;
    box-shadow: 0 0 0 2.5px #3B82F6, 0 2px 8px rgba(59,130,246,0.25);
    transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.25s ease;
    cursor: zoom-in;
    position: relative;
    z-index: 50;
}
.freq-avatar:hover {
    transform: scale(3.5);
    box-shadow: 0 0 0 2.5px #3B82F6, 0 12px 36px rgba(0,0,0,0.5);
    z-index: 99999 !important;
    position: relative;
}
.freq-initials {
    display: flex; align-items: center; justify-content: center;
    width: 42px; height: 42px;
    min-width: 42px; min-height: 42px;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    background: linear-gradient(135deg, #3B82F6, #06B6D4);
    color: #fff;
    font-weight: 900;
    font-size: 16px;
    box-shadow: 0 0 0 2px #BFDBFE;
    flex-shrink: 0;
}
</style>
"""

def toggle_presence_btn(aluno_id, data_aula, atual_status, nome_aluno):
    if alternar_presenca(aluno_id, data_aula, not atual_status): 
        st.toast(f"✅ {nome_aluno} ATUALIZADO.")
    else: 
        st.toast("🚨 Erro ao guardar presença.")

def renderizar_aba_frequencia(df_alunos, data_aula, turma_selecionada, presencas_turma_geral, is_global_search, chave_unica):
    if df_alunos.empty: 
        return

    st.markdown(_CSS_LISTA, unsafe_allow_html=True)

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
                    layout_cols = [1, 5, 1.2, 1.2] if eh_admin else [1, 6.5, 1.2]
                    c_img, c_btn, c_ed, *c_del = st.columns(layout_cols, gap="small", vertical_alignment="center")

                    with c_img:
                        u_f = str(row.get("foto_url") or "").strip()
                        inic = "".join(p[0].upper() for p in str(row["nome"]).split()[:2] if p)
                        if u_f.startswith("http"):
                            st.markdown(
                                f'<img src="{u_f}" class="freq-avatar" '
                                f'onerror="this.outerHTML=\'<div class=freq-initials>{inic}</div>\'">',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(f'<div class="freq-initials">{inic}</div>', unsafe_allow_html=True)

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