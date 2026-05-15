# ==============================================================================
# 📄 Arquivo: views/inscricao_publica_view.py
# 🏷️ VERSÃO: 3.0 (PRO ELITE - Cadastro Full + Dupla Personalidade Admin/Público)
# ⚙️ FUNÇÃO: Inscrição completa baseada na Planilha Excel (28 campos).
# ==============================================================================

import streamlit as st
import datetime
from database import supabase, upload_midia, get_todas_turmas
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image

# 🚀 MOTOR DE DISPARO DE E-MAILS (LGPD)
def disparar_email_lgpd(email_destino, nome_aluno, data_hora):
    if not email_destino: return False
    remetente = st.secrets.get("EMAIL_USER", "seu_email_aqui@gmail.com")
    senha = st.secrets.get("EMAIL_PASS", "sua_senha_de_app_aqui")
    assunto = "📜 Confirmação de Inscrição e Termo LGPD - Instituto Muda Brasil"

    corpo_email = f"""
    Olá, {nome_aluno}!
    Sua inscrição foi recebida com sucesso em {data_hora}.
    Este é o seu comprovativo de aceitação do Termo LGPD (Lei nº 13.709/2018).
    Seus dados estão protegidos. Aguarde o contacto da nossa coordenação.
    """
    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = email_destino
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_email, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

def processar_documento(file_bytes, file_name, file_type):
    try:
        if "image" in file_type:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            return buf.getvalue(), f"doc_{file_name.split('.')[0]}.jpg", "image/jpeg"
        return file_bytes, file_name, file_type
    except: return file_bytes, file_name, file_type

def tela_inscricao_publica_move_right():
    is_admin = st.session_state.get("usuario_logado", False)

    if not is_admin:
        st.markdown("""
            <style>#MainMenu, header, footer {visibility: hidden;} .block-container {padding-top: 2rem;}</style>
            <div style='text-align: center; padding: 25px; background: linear-gradient(135deg, #F8FAFC 0%, #E0F2FE 100%); border-radius: 15px; margin-bottom: 25px; border: 1px solid #BAE6FD;'>
                <h1 style='color: #0A2540; margin-bottom: 5px; font-weight: 900; text-transform: uppercase;'>📝 Ficha de Inscrição MoveRight</h1>
                <p style='color: #475569; font-weight: 600;'>Instituto Muda Brasil • Venha treinar e transformar sua vida conosco!</p>
            </div>
        """, unsafe_allow_html=True)

    with st.form("form_inscricao_full", clear_on_submit=False):

        # ── 1. DADOS PESSOAIS ──
        st.markdown("### 👤 1. Dados Pessoais")
        nome = st.text_input("Nome Completo *").upper()

        c_email, c_cel = st.columns(2)
        email = c_email.text_input("E-mail *")
        whatsapp = c_cel.text_input("WhatsApp (com DDD) *")

        c_cpf, c_rg = st.columns(2)
        cpf = c_cpf.text_input("CPF *")
        rg = c_rg.text_input("RG")

        c_nasc, c_nat, c_sexo = st.columns(3)
        nascimento = c_nasc.date_input("Data de Nascimento *", value=datetime.date(1960, 1, 1), min_value=datetime.date(1920, 1, 1))
        naturalidade = c_nat.text_input("Naturalidade")
        sexo = c_sexo.selectbox("Sexo", ["Feminino", "Masculino", "Outro"])

        c_civil, c_inst = st.columns(2)
        estado_civil = c_civil.selectbox("Estado Civil", ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"])
        instrucao = c_inst.selectbox("Grau de Instrução", ["Ensino Fundamental", "Ensino Médio", "Ensino Superior", "Pós-graduação"])

        c_peso, c_alt = st.columns(2)
        peso = c_peso.number_input("Peso (kg)", min_value=0.0, step=0.1)
        altura = c_alt.number_input("Altura (m)", min_value=0.0, step=0.01)

        # ── 2. ENDEREÇO ──
        st.markdown("### 🏠 2. Endereço")
        endereco = st.text_input("Rua/Logradouro e Número *")
        c_bairro, c_cep = st.columns(2)
        bairro = c_bairro.text_input("Bairro *")
        cep = c_cep.text_input("CEP")

        # ── 3. SAÚDE ──
        st.markdown("### 🩺 3. Histórico de Saúde")
        problemas = st.text_area("Problemas de saúde / Doenças:")
        medicamentos = st.text_area("Medicamentos de uso contínuo:")
        alergias = st.text_input("Possui alguma alergia?")
        emergencia = st.text_input("Contacto de Emergência (Nome e Tel) *")

        # ── 4. SOCIOECONÔMICO ──
        st.markdown("### 🤝 4. Perfil Socioeconômico")
        c_mor, c_apo = st.columns(2)
        residentes = c_mor.selectbox("Residentes na moradia", ["1", "2", "3", "4", "5 ou mais"])
        aposentado = c_apo.radio("Aposentado?", ["Sim", "Não"], horizontal=True)
        renda = st.selectbox("Renda Familiar", ["Até 1 Salário", "1 a 2 Salários", "2 a 4 Salários", "Acima de 4 Salários"])

        # ── 5. TURMA E DOCUMENTOS ──
        st.markdown("### 🗓️ 5. Turma e Documentação")

        if is_admin:
            turmas_list = [t['nome'] for t in get_todas_turmas()]
            turma_final = st.selectbox("Vincular diretamente à Turma:", turmas_list)
        else:
            st.info("Escolha sua preferência. A vaga depende de disponibilidade.")
            turma_final = st.selectbox("Preferência de Horário:", ["08:00 às 09:00", "09:00 às 10:00", "10:00 às 11:00"])

            atestado_file = st.file_uploader("Anexar Atestado Médico (Obrigatório) *", type=["jpg", "png", "pdf"])
            termo = st.checkbox("Aceito os termos da LGPD e Uso de Imagem. *")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_txt = "🚀 MATRICULAR ALUNO" if is_admin else "🚀 ENVIAR MINHA INSCRIÇÃO"
        submit = st.form_submit_button(btn_txt, type="primary", use_container_width=True)

        if submit:
            if not nome or not cpf or not whatsapp or not emergencia:
                st.error("⚠️ Preencha os campos obrigatórios (*).")
            elif not is_admin and (not atestado_file or not termo):
                st.error("⚠️ Anexe o atestado e aceite o termo LGPD.")
            else:
                with st.spinner("A processar cadastro..."):
                    try:
                        url_atestado = None
                        if not is_admin and atestado_file:
                            b_at, n_at, t_at = processar_documento(atestado_file.getvalue(), atestado_file.name, atestado_file.type)
                            url_atestado = upload_midia(b_at, n_at, t_at)

                        # Mapeamento para o Banco de Dados
                        payload = {
                            "nome": nome,
                            "data_nascimento": str(nascimento),
                            "cpf": cpf,
                            "whatsapp": whatsapp,
                            "email": email,
                            "sexo": sexo,
                            "endereco": endereco,
                            "bairro": bairro,
                            "problemas_saude": problemas,
                            "medicamentos": medicamentos,
                            "contato_emergencia": emergencia,
                            "status": "Ativo" if is_admin else "Pendente",
                            "turma": turma_final if is_admin else None,
                            "horario_preferencial": None if is_admin else turma_final,
                            "url_atestado_medico": url_atestado
                            # Adicione aqui os demais campos socioeconómicos se já criou as colunas no Supabase
                        }

                        tabela = "alunos" if is_admin else "pre_cadastros"
                        supabase.table(tabela).insert(payload).execute()

                        if not is_admin: disparar_email_lgpd(email, nome, datetime.datetime.now().strftime("%d/%m/%Y"))

                        st.success(f"✅ Sucesso! Cadastro realizado em: {tabela}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro no banco: {e}")

# Lembrete: Execute esta função dentro do seu main.py onde a rota for 'inscricao'.