# ==============================================================================
# 📄 Arquivo: inscricao_view.py
# 📏 Módulo: Formulário Público de Captação e Triagem (LGPD + Segurança Senior)
# ⚙️ Atualização: Captação de Opção 1 e Opção 2 de horário para fila de espera.
# ==============================================================================
import streamlit as st
import datetime
from database import supabase, upload_midia
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image, ImageOps

# 🚀 MOTOR DE DISPARO DE E-MAILS (LGPD)
def disparar_email_lgpd(email_destino, nome_aluno, data_hora):
    if not email_destino: return False
    remetente = st.secrets.get("EMAIL_USER", "seu_email_aqui@gmail.com")
    senha = st.secrets.get("EMAIL_PASS", "sua_senha_de_app_aqui")
    assunto = "📜 Confirmação de Inscrição e Termo LGPD - Instituto Muda Brasil"

    corpo_email = f"""
    Olá, {nome_aluno}!

    A sua pré-inscrição no Instituto Muda Brasil foi recebida com sucesso no dia {data_hora}.

    Este e-mail serve como comprovativo oficial de que você ACEITOU o nosso Termo de Consentimento Livre, Informado e Inequívoco, em conformidade com a Lei Geral de Proteção de Dados Pessoais (LGPD - Lei nº 13.709/2018).

    O QUE VOCÊ AUTORIZOU:
    1. Coleta e tratamento dos seus dados pessoais e dados sensíveis (informações de saúde, físicas e atestados médicos) exclusivamente para fins de avaliação de aptidão física e segurança nas aulas do Instituto.
    2. Uso da sua imagem e voz para fins estritos de divulgação e publicidade institucional do projeto "Esporte e Saúde na Comunidade".

    As turmas possuem limite de 40 vagas. A coordenação avaliará as suas opções de horário e, caso as turmas estejam lotadas, você será direcionado para a Lista de Espera Oficial.

    Os seus dados estão protegidos nos nossos servidores. Aguarde o nosso contacto!

    Equipa Instituto Muda Brasil
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
    except Exception: return False 

def processar_documento(file_bytes, file_name, file_type):
    try:
        if "image" in file_type:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue(), f"doc_{file_name.split('.')[0]}.jpg", "image/jpeg"
        return file_bytes, file_name, file_type
    except Exception: return file_bytes, file_name, file_type

def tela_inscricao_publica():
    st.markdown("""
        <style>
            #MainMenu, header, footer {visibility: hidden;}
            .block-container {padding-top: 1rem; max-width: 800px;}
            .titulo-form {color: #1E88E5; font-weight: 900; font-size: 28px; text-align: center; margin-bottom: 5px;}
            .subtitulo-form {color: #64748B; text-align: center; font-size: 15px; margin-bottom: 30px;}
            .caixa-lgpd {background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; font-size: 12px; color: #475569; margin-bottom: 15px; height: 150px; overflow-y: scroll;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='titulo-form'>🏃‍♂️ Instituto Muda Brasil</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitulo-form'>Ficha de Inscrição e Triagem de Saúde</div>", unsafe_allow_html=True)

    with st.container(border=True):
        with st.form("form_inscricao_publica", clear_on_submit=False):
            st.markdown("### 👤 1. Dados Pessoais & Biometria")
            nome = st.text_input("Nome Completo *")
            c_cpf, c_rg = st.columns(2)
            cpf = c_cpf.text_input("CPF *")
            rg = c_rg.text_input("RG")

            c_nasc, c_peso, c_alt = st.columns(3)
            hoje = datetime.date.today()
            nascimento = c_nasc.date_input("Data de Nascimento *", value=datetime.date(1980, 1, 1), min_value=datetime.date(1920, 1, 1), max_value=hoje, format="DD/MM/YYYY")
            peso = c_peso.number_input("Peso (kg) *", min_value=0.0, step=0.1)
            altura = c_alt.number_input("Altura (m) *", min_value=0.0, step=0.01)

            c_email, c_cel = st.columns(2)
            email = c_email.text_input("E-mail * (Para envio do comprovativo LGPD)")
            celular = c_cel.text_input("Celular (WhatsApp) *")

            st.markdown("### 🗓️ 2. Preferência de Turma (Vagas Limitadas a 40)")
            st.info("💡 Como nossas turmas lotam rapidamente, selecione uma segunda opção de horário caso a sua primeira opção esteja sem vagas.")

            dias_pref = st.selectbox("Quais dias prefere treinar? *", ["Segundas, Quartas e Sextas", "Terças e Quintas", "Todos os dias (Seg a Sex)"])

            c_hora1, c_hora2 = st.columns(2)
            hora_pref = c_hora1.selectbox("1ª Opção de Horário *", ["08:00 às 09:00", "09:00 às 10:00", "10:00 às 11:00"])
            hora_pref_2 = c_hora2.selectbox("2ª Opção de Horário", ["Nenhuma", "08:00 às 09:00", "09:00 às 10:00", "10:00 às 11:00"])

            st.markdown("### 🏠 3. Endereço e Perfil")
            endereco = st.text_input("Endereço Completo (Rua, Número, Complemento) *")
            c_bairro, c_cep = st.columns(2)
            bairro = c_bairro.text_input("Bairro *")
            cep = c_cep.text_input("CEP")

            st.markdown("### 🩺 4. Histórico de Saúde e Segurança")
            problemas = st.text_area("Possui algum problema de saúde? Liste-os aqui:")
            medicamentos = st.text_area("Faz uso contínuo de medicamentos? Quais?")
            restricoes = st.text_input("Possui restrição para atividades físicas? Quais?")

            st.error("🚨 **ATENÇÃO:** Para a segurança de todos (especialmente alunos no grupo de risco ou +60 anos), é estritamente obrigatório fornecer um contacto de emergência válido.")
            c_em_nome, c_em_tel = st.columns(2)
            emergencia_nome = c_em_nome.text_input("Nome do Contacto de Emergência *")
            emergencia_tel = c_em_tel.text_input("Telefone de Emergência *")

            st.markdown("### 📄 5. Documentação Médica e Legal")
            st.write("Anexe os documentos abaixo em formato Imagem ou PDF.")

            c_up_rg, c_up_rec, c_up_atest = st.columns(3)
            with c_up_rg:
                rg_file = st.file_uploader("1. Cópia do RG/CPF", type=["jpg", "jpeg", "png", "pdf"])
            with c_up_rec:
                receita_file = st.file_uploader("2. Receituário Médico", type=["jpg", "jpeg", "png", "pdf"])
            with c_up_atest:
                atestado_file = st.file_uploader("3. Atestado de Aptidão *", type=["jpg", "jpeg", "png", "pdf"])

            st.markdown("""
            <div class="caixa-lgpd">
                <strong>TERMO DE CONSENTIMENTO LIVRE (LGPD - LEI Nº 13.709/2018) E DIREITO DE IMAGEM</strong><br><br>
                1. Autorizo a coleta e tratamento dos meus dados de saúde para fins de segurança e adequação física.<br>
                2. Autorizo o uso da minha imagem e voz para fins de divulgação do projeto de forma gratuita.
            </div>
            """, unsafe_allow_html=True)
            termo = st.checkbox("Li e aceito os Termos da LGPD, Uso de Imagem e assumo a veracidade das informações médicas. *")

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("🚀 Assinar Digitalmente e Enviar", type="primary", use_container_width=True)

            if submit:
                if not nome or not cpf or not celular or not endereco or not emergencia_nome or not emergencia_tel or peso == 0 or altura == 0 or not email:
                    st.error("⚠️ Por favor, preencha todos os campos obrigatórios (marcados com *).")
                elif not atestado_file:
                    st.error("⚠️ O Atestado Médico é obrigatório para concluir a inscrição.")
                elif not termo:
                    st.error("⚠️ O consentimento da LGPD é obrigatório pela lei.")
                else:
                    with st.spinner("A processar documentos e a registar assinatura digital..."):

                        url_rg, url_receita, url_atestado = None, None, None

                        if rg_file:
                            b_rg, n_rg, t_rg = processar_documento(rg_file.getvalue(), rg_file.name, rg_file.type)
                            url_rg = upload_midia(b_rg, n_rg, t_rg)

                        if receita_file:
                            b_rec, n_rec, t_rec = processar_documento(receita_file.getvalue(), receita_file.name, receita_file.type)
                            url_receita = upload_midia(b_rec, n_rec, t_rec)

                        if atestado_file:
                            b_at, n_at, t_at = processar_documento(atestado_file.getvalue(), atestado_file.name, atestado_file.type)
                            url_atestado = upload_midia(b_at, n_at, t_at)

                        contato_emergencia_final = f"{emergencia_nome.strip()} - {emergencia_tel.strip()}"

                        # 🚀 INJEÇÃO DO NOVO CAMPO: HORÁRIO PREFERENCIAL 2
                        dados_inserir = {
                            "nome": nome, "email": email, "celular": celular, "cpf": cpf, "rg": rg,
                            "data_nascimento": str(nascimento), "peso": peso, "altura": altura,
                            "dias_preferenciais": dias_pref, "horario_preferencial": hora_pref,
                            "horario_preferencial_2": hora_pref_2, # <--- AQUI
                            "endereco": endereco, "bairro": bairro, "cep": cep,
                            "problemas_saude": problemas, "medicamentos": medicamentos,
                            "restricoes_fisicas": restricoes, "contato_emergencia": contato_emergencia_final,
                            "termo_imagem": termo, 
                            "url_rg": url_rg,                        
                            "url_receituario": url_receita,          
                            "url_atestado_medico": url_atestado,     
                            "status": "Pendente"
                        }

                        try:
                            supabase.table("pre_cadastros").insert(dados_inserir).execute()
                            disparar_email_lgpd(email, nome.split()[0], datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                            st.success("✅ **Inscrição validada e assinada!** Uma cópia do termo foi enviada para o seu e-mail.")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")