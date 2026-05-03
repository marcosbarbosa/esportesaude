# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_dossie.py
# 🏷️ VERSÃO: 2.2 (Correção Crítica de Indentação)
# 📅 DATA: 03/04/2026 | 🕒 HORA: 18:45
# ⚙️ FUNÇÃO: Geração de documentos PDF/Word e Dashboard clínico individual.
# 📏 LINHAS: ~65
# ==============================================================================
import streamlit as st
import pandas as pd
from database import (
    get_estatisticas_frequencia_aluno,
    get_historico_aulas_aluno,
    get_avaliacoes_aluno,
)


def renderizar_aba_dossie(df_alunos_tab, data_aula, turma_selecionada, chave_unica):
    # 🚀 O Rádio possui a key para o CSS e a indentação está absolutamente correta
    tipo_dossie = st.radio(
        "Selecione o tipo:",
        ["🏫 Dossiê da Seleção", "👤 Dashboard do Aluno"],
        horizontal=True,
        label_visibility="collapsed",
        key="radio_dossie",
    )

    if tipo_dossie == "🏫 Dossiê da Seleção":
        with st.container(border=True):
            st.markdown("### 🖨️ Emissão do Dossiê Oficial da Turma")
            t_s = (
                turma_selecionada.replace(":", "h")
                .replace("(", "")
                .replace(")", "")
                .replace(" ", "_")
                .replace("🌍_", "")
            )
            n_base = f"Dossie_{t_s}_{data_aula.strftime('%d-%m-%Y')}"
            cw, cp = st.columns(2)

            with cw:
                if st.button("⚙️ Processar Word", use_container_width=True):
                    from gerador_word import criar_documento_dossie

                    st.session_state[f"dw_{chave_unica}"] = criar_documento_dossie(
                        data_aula, turma_selecionada
                    )
                if f"dw_{chave_unica}" in st.session_state:
                    st.download_button(
                        "📥 Baixar Word",
                        data=st.session_state[f"dw_{chave_unica}"],
                        file_name=f"{n_base}.docx",
                        use_container_width=True,
                        type="primary",
                    )
            with cp:
                if st.button("👁️ Processar PDF", use_container_width=True):
                    from gerador_pdf import criar_documento_pdf

                    st.session_state[f"dp_{chave_unica}"] = criar_documento_pdf(
                        data_aula, turma_selecionada
                    )
                if f"dp_{chave_unica}" in st.session_state:
                    st.download_button(
                        "📥 Baixar PDF",
                        data=st.session_state[f"dp_{chave_unica}"],
                        file_name=f"{n_base}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
    else:
        with st.container(border=True):
            st.markdown("### 👤 Dashboard Clínico do Aluno")
            if not df_alunos_tab.empty:
                aluno_sel = st.selectbox(
                    "Selecione o Aluno:", df_alunos_tab["nome"].tolist()
                )
                aluno_data = df_alunos_tab[df_alunos_tab["nome"] == aluno_sel].iloc[0]
                c_f, c_i = st.columns([1, 4])
                with c_f:
                    if pd.notna(aluno_data.get("url_foto")):
                        st.image(aluno_data.get("url_foto"), width=120)
                    else:
                        st.markdown(
                            '<div style="font-size:80px;">👤</div>',
                            unsafe_allow_html=True,
                        )
                with c_i:
                    st.markdown(f"### {aluno_data['nome']}")
                    st.markdown(f"**Turma:** {aluno_data['turma']}")
                st.divider()

                estats = get_estatisticas_frequencia_aluno(aluno_data["id"])
                c1, c2, c3 = st.columns(3)
                c1.metric("Aulas", estats.get("total", 0))
                c2.metric("Presenças", estats.get("presentes", 0))
                c3.metric("Taxa Global", f"{estats.get('percentual', 0.0):.1f}%")
                st.markdown("---")

                historico = get_historico_aulas_aluno(aluno_data["id"])
                if historico:
                    for h in historico:
                        with st.expander(f"📅 Aula do dia {h.get('data_aula')}"):
                            st.markdown(f"**🎯 Objetivo:** {h.get('objetivo_geral')}")

                _id = aluno_data["id"]
                _nome = aluno_data["nome"]
                _pdf_key = f"da_{_id}"
                _word_key = f"da_word_{_id}"

                btn_pdf, btn_word = st.columns(2)
                with btn_pdf:
                    if st.session_state.get(_pdf_key):
                        st.download_button(
                            "📥 PDF",
                            data=st.session_state[_pdf_key],
                            file_name=f"Dossie_{_nome}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                        )
                    elif st.button(
                        f"🖨️ PDF — {_nome}",
                        use_container_width=True,
                        type="primary",
                    ):
                        from gerador_pdf import criar_documento_aluno_pdf
                        avals = get_avaliacoes_aluno(_id)
                        st.session_state[_pdf_key] = criar_documento_aluno_pdf(
                            aluno_data, avals, historico, estats
                        )
                        st.rerun()

                with btn_word:
                    if st.session_state.get(_word_key):
                        st.download_button(
                            "📥 Word",
                            data=st.session_state[_word_key],
                            file_name=f"Dossie_{_nome}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
                    elif st.button(
                        f"📘 Word — {_nome}",
                        use_container_width=True,
                    ):
                        from gerador_word import criar_documento_aluno_word
                        avals = get_avaliacoes_aluno(_id)
                        try:
                            wb = criar_documento_aluno_word(aluno_data, avals, historico, estats)
                            if wb:
                                st.session_state[_word_key] = wb
                                st.rerun()
                        except Exception as _e:
                            st.error(f"Erro Word: {_e}")
            else:
                st.warning("Não há alunos nesta turma.")
