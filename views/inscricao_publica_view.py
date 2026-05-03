# ==============================================================================
# 📄 Arquivo: views/inscricao_publica_view.py
# 🏷️ VERSÃO: 2.0 (PRO Elite - Dupla Personalidade: Admin/Público + Fix DB)
# ==============================================================================

import streamlit as st
import datetime
from database import supabase, get_todas_turmas


def tela_inscricao_publica_move_right():
    # Verifica se quem está acessando é um Administrador logado
    is_admin = st.session_state.get("usuario_logado", False)

    if not is_admin:
        st.markdown(
            """
            <style>#MainMenu, header, footer {visibility: hidden;} .block-container {padding-top: 2rem;}</style>
            <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #F8FAFC 0%, #E0F2FE 100%); border-radius: 15px; margin-bottom: 30px; border: 1px solid #BAE6FD;'>
                <h1 style='color: #0A2540; margin-bottom: 5px; font-weight: 900;'>📝 Ficha de Inscrição MoveRight</h1>
                <p style='color: #475569; font-weight: 600; font-size: 16px;'>Instituto Muda Brasil • Venha treinar e transformar sua vida conosco!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.form("ficha_publica_completa", clear_on_submit=True):
        st.markdown("#### 👤 1. Informações Pessoais")
        c1, c2 = st.columns(2)
        nome = c1.text_input(
            "Nome Completo:", placeholder="Como consta no documento oficial"
        )
        data_nasc = c2.date_input(
            "Data de Nascimento:",
            min_value=datetime.date(1920, 1, 1),
            max_value=datetime.date.today(),
        )

        c3, c4 = st.columns(2)
        cpf = c3.text_input("CPF:", placeholder="Apenas números")
        whatsapp = c4.text_input("WhatsApp (com DDD):", placeholder="Ex: 11988887777")

        # 🚀 Se for administrador, escolhe a Turma na hora!
        turma_selecionada = None
        if is_admin:
            st.markdown("#### 🏫 1.1 Alocação Direta (Apenas Administrador)")
            df_turmas = get_todas_turmas(ativas_apenas=True)
            lista_turmas = (
                df_turmas["nome"].tolist()
                if not df_turmas.empty
                else ["Sem turmas ativas"]
            )
            turma_selecionada = st.selectbox("Selecione a Turma Inicial:", lista_turmas)

        st.markdown("---")
        st.markdown("#### 🏥 2. Histórico de Saúde (Anamnese Clínica)")

        col_s1, col_s2 = st.columns(2)
        doenca = col_s1.text_area(
            "Possui alguma doença crônica? (Diabetes, Hipertensão, Artrose, etc)",
            height=100,
        )
        cirurgia = col_s2.text_area(
            "Já passou por alguma cirurgia recente ou antiga? Qual?", height=100
        )

        c_med, c_ale = st.columns(2)
        medicamentos = c_med.text_area(
            "Faz uso de algum medicamento diário/controlado?", height=80
        )
        alergias = c_ale.text_area(
            "Possui alguma alergia medicamentosa ou alimentar?", height=80
        )

        st.markdown("---")
        st.markdown("#### ⚖️ 3. Declaração de Responsabilidade")
        aceito = st.checkbox(
            "Declaro que as informações prestadas são verdadeiras e que estou apto fisicamente para participar das atividades do projeto, assumindo a responsabilidade pela minha saúde durante as aulas."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        lbl_botao = (
            "📥 CADASTRAR ALUNO DIRETAMENTE"
            if is_admin
            else "🚀 ENVIAR MINHA INSCRIÇÃO AGORA"
        )
        btn_enviar = st.form_submit_button(
            lbl_botao, type="primary", use_container_width=True
        )

        if btn_enviar:
            if not nome or not whatsapp or not aceito:
                st.error(
                    "❌ Por favor, preencha o Nome, WhatsApp e marque a caixa de aceite dos termos para continuar."
                )
            else:
                try:
                    if is_admin:
                        # 🚀 Salva direto na tabela ALUNOS (Pronto para Frequência)
                        payload_admin = {
                            "nome": nome.upper().strip(),
                            "data_nascimento": str(data_nasc),
                            "cpf": cpf,
                            "whatsapp": whatsapp,
                            "problemas_saude": f"Doenças: {doenca} | Cirurgias: {cirurgia} | Alergias: {alergias}",
                            "medicamentos": medicamentos,
                            "turma": turma_selecionada,
                            "status": "Ativo",
                        }
                        supabase.table("alunos").insert(payload_admin).execute()
                        st.success(
                            f"🎉 Matrícula de {nome.upper()} realizada com sucesso! O aluno já está disponível no módulo de Frequência."
                        )
                    else:
                        # 🚀 Salva em PRE CADASTROS (Público externo) - SEM a coluna 'criado_em'
                        payload_publico = {
                            "nome": nome.upper().strip(),
                            "data_nascimento": str(data_nasc),
                            "cpf": cpf,
                            "whatsapp": whatsapp,
                            "problemas_saude": f"Doenças: {doenca} | Cirurgias: {cirurgia} | Alergias: {alergias}",
                            "medicamentos": medicamentos,
                            "status": "Pendente",
                        }
                        supabase.table("pre_cadastros").insert(
                            payload_publico
                        ).execute()
                        st.success(
                            "🎉 Parabéns! Sua inscrição foi registrada com sucesso. Nossa coordenação entrará em contato muito em breve."
                        )
                        st.balloons()
                except Exception as e:
                    st.error(
                        f"Erro ao conectar com o banco de dados. Tente novamente mais tarde. (Erro: {e})"
                    )
