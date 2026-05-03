# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_inscricao.py
# 🏷️ VERSÃO: 1.0 (ONBOARDING LEGAL - LGPD & Imagem)
# 📅 DATA: 04/04/2026 | 🕒 HORA: 12:00
# ⚙️ FUNÇÃO: Termos de consentimento e aceite para novos alunos.
# 📏 LINHAS: ~80
# ==============================================================================
import streamlit as st


def renderizar_termos_legais():
    st.markdown("### 📝 Termos de Consentimento e Responsabilidade")
    st.info(
        "Para finalizar sua inscrição no projeto MoveRight, leia e aceite os termos abaixo."
    )

    # --- BLOCO 1: LGPD ---
    with st.expander("🔐 1. Proteção de Dados (LGPD)", expanded=True):
        st.markdown("""
        **CONSENTIMENTO PARA TRATAMENTO DE DADOS PESSOAIS:**
        Ao prosseguir, você autoriza o projeto **MUDA BRASILt** a coletar e tratar seus dados pessoais (nome, data de nascimento, contato e prontuário clínico) para as seguintes finalidades:
        * **Gestão Operacional:** Controle de frequência, organização de turmas e comunicações oficiais.
        * **Segurança:** Utilização do contato de emergência em caso de incidentes.
        * **Seguro:** Emissão de apólices de seguro contra acidentes pessoais (se aplicável).

        Seus dados serão armazenados de forma segura e não serão compartilhados com terceiros para fins comerciais. Você tem o direito de solicitar a retificação ou exclusão de seus dados a qualquer momento através da secretaria do projeto.
        """)
        aceite_lgpd = st.checkbox(
            "Li e aceito o tratamento dos meus dados conforme a LGPD.", key="chk_lgpd"
        )

    # --- BLOCO 2: USO DE IMAGEM ---
    with st.expander("📸 2. Autorização de Uso de Imagem e Voz", expanded=True):
        st.markdown("""
        **AUTORIZAÇÃO:**
        Eu autorizo o uso da minha imagem e voz, captadas em fotos e vídeos durante as atividades do projeto **MoveRight**, para fins exclusivos de:
        * Divulgação em redes sociais oficiais e site institucional.
        * Relatórios de prestação de contas para órgãos públicos e parceiros.
        * Materiais informativos e de divulgação do projeto.

        Esta autorização é concedida a título gratuito, abrangendo todo o território nacional e internacional, por prazo indeterminado, sem que nada haja a ser reclamado a título de direitos conexos à minha imagem.
        """)
        aceite_imagem = st.checkbox(
            "Autorizo o uso da minha imagem para divulgação do projeto.",
            key="chk_imagem",
        )

    # --- BLOCO 3: BOTÃO DE FINALIZAÇÃO ---
    st.markdown("---")
    if aceite_lgpd and aceite_imagem:
        if st.button(
            "🚀 FINALIZAR MINHA INSCRIÇÃO", type="primary", use_container_width=True
        ):
            st.success(
                "🎉 Parabéns! Sua inscrição foi processada com sucesso. Bem-vindo ao MoveRight!"
            )
            # Aqui entraria a função para salvar no banco de dados
            # salvar_aceite_aluno(id_aluno)
    else:
        st.warning(
            "⚠️ Você precisa marcar os dois campos de aceite acima para concluir a inscrição."
        )


# Função de ajuda caso queira usar como popup ou dentro de outro formulário
def mostrar_alerta_pendencia():
    st.error("🚨 ATENÇÃO: Este aluno possui pendências nos termos de LGPD ou Imagem!")
