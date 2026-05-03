# ==============================================================================
# 📄 Arquivo: views/templates_view.py
# 🏷️ VERSÃO: 1.0 (PRO Elite - Gestão de Copywriting CRM)
# ⚙️ FUNÇÃO: Permite à coordenação editar os textos dinâmicos do WhatsApp.
# ==============================================================================
import streamlit as st
from database import get_crm_templates, atualizar_crm_template

def tela_gestao_templates():
    st.title("💬 Gestão de Mensagens (WhatsApp)")
    st.write("Personalize os textos automáticos que o sistema utiliza para contactar os alunos.")
    st.info("💡 **Dica de Copywriting:** Use a tag `{nome}` no meio do texto. O sistema irá substituí-la automaticamente pelo primeiro nome do aluno na hora de enviar!")
    st.divider()

    df_templates = get_crm_templates()

    if df_templates.empty:
        st.warning("Nenhum template encontrado na base de dados.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚨 Retenção e Evasão")
        for _, t in df_templates[df_templates['gatilho'].str.contains('evasao|assiduo')].iterrows():
            with st.expander(f"📌 {t['titulo']}"):
                nova_msg = st.text_area("Texto da Mensagem:", value=t['mensagem'], height=120, key=f"txt_{t['gatilho']}")
                if st.button("💾 Guardar Texto", key=f"btn_{t['gatilho']}", type="primary", use_container_width=True):
                    sucesso, msg = atualizar_crm_template(t['gatilho'], nova_msg)
                    if sucesso:
                        st.success("Atualizado!")
                        st.rerun()
                    else:
                        st.error(msg)

    with col2:
        st.markdown("### 🎂 Parabenizações (Aniversários)")
        for _, t in df_templates[df_templates['gatilho'].str.contains('niver')].iterrows():
            with st.expander(f"🎉 {t['titulo']}"):
                nova_msg = st.text_area("Texto da Mensagem:", value=t['mensagem'], height=120, key=f"txt_{t['gatilho']}")
                if st.button("💾 Guardar Texto", key=f"btn_{t['gatilho']}", type="primary", use_container_width=True):
                    sucesso, msg = atualizar_crm_template(t['gatilho'], nova_msg)
                    if sucesso:
                        st.success("Atualizado!")
                        st.rerun()
                    else:
                        st.error(msg)