# ==============================================================================
# 📄 ARQUIVO: views/inscricao_publica_view.py
# 🏷️ VERSÃO: 4.10 PRIMEMAX (Cadastro Full, Renda LGPD & Triagem de Documentos)
# 👤 COPYRIGHT: © 2026 MoveRight Gestão Inteligente • Instituto Muda Brasil
# 📏 LINHAS: ~250
# ⚙️ FUNÇÃO: Formulário Público de Captação e Triagem. Recebe os 28 campos
#            da Planilha Base, processa e comprime RG/Atestados via Pillow e
#            dispara E-mail de aceite LGPD via SMTP.
# ==============================================================================

import streamlit as st
import datetime
from database import supabase, upload_midia, get_todas_turmas
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image


# ==============================================================================
# 🚀 MOTOR DE DISPARO DE E-MAILS (LGPD)
# ==============================================================================
def disparar_email_lgpd(email_destino, nome_aluno, data_hora):
    if not email_destino:
        return False
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
    msg["From"] = remetente
    msg["To"] = email_destino
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo_email, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False


# ==============================================================================
# 🗜️ MOTOR DE PROCESSAMENTO E COMPRESSÃO DE IMAGENS
# ==============================================================================
def processar_documento(file_bytes, file_name, file_type):
    try:
        if "image" in file_type:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue(), f"doc_{file_name.split('.')[0]}.jpg", "image/jpeg"
        return file_bytes, file_name, file_type
    except Exception:
        return file_bytes, file_name, file_type


# ==============================================================================
# 🖥️ RENDERIZAÇÃO DA INTERFACE PRINCIPAL (UI)
# ==============================================================================
def tela_inscricao_publica_move_right(modo_admin=False):
    st.markdown(
        """
        <style>
            #MainMenu, header, footer {visibility: hidden;}
            .block-container {padding-top: 1rem; max-width: 900px;}
            .titulo-form {color: #0A2540; font-weight: 900; font-size: 28px; text-align: center; margin-bottom: 5px; text-transform: uppercase;}
            .subtitulo-form {color: #64748B; text-align: center; font-size: 15px; margin-bottom: 30px;}
            .caixa-lgpd {background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; font-size: 12px; color: #475569; margin-bottom: 15px; height: 150px; overflow-y: scroll;}
            .section-header {color: #1E88E5; font-size: 20px; font-weight: 800; border-bottom: 2px solid #E2E8F0; padding-bottom: 5px; margin-top: 25px; margin-bottom: 15px;}
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='titulo-form'>🏃‍♂️ Instituto Muda Brasil</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitulo-form'>Ficha Oficial de Inscrição e Triagem de Saúde</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        with st.form("form_inscricao_publica", clear_on_submit=False):
            # ---------------------------------------------------------
            # 1. DADOS PESSOAIS
            # ---------------------------------------------------------
            st.markdown(
                "<div class='section-header'>👤 1. Dados Pessoais</div>",
                unsafe_allow_html=True,
            )
            nome = st.text_input("Nome Completo *")

            c_email, c_cel = st.columns(2)
            email = c_email.text_input("E-mail * (Para envio do comprovativo LGPD)")
            celular = c_cel.text_input("Celular (WhatsApp) *")

            c_cpf, c_rg = st.columns(2)
            cpf = c_cpf.text_input("CPF *")
            rg = c_rg.text_input("RG")

            c_nasc, c_nat, c_sexo = st.columns(3)
            hoje = datetime.date.today()
            nascimento = c_nasc.date_input(
                "Data de Nascimento *",
                value=datetime.date(1960, 1, 1),
                min_value=datetime.date(1920, 1, 1),
                max_value=hoje,
                format="DD/MM/YYYY",
            )
            naturalidade = c_nat.text_input("Naturalidade (Cidade/Estado)")
            sexo = c_sexo.selectbox(
                "Sexo", ["Feminino", "Masculino", "Prefiro não informar"]
            )

            c_civil, c_conj = st.columns(2)
            estado_civil = c_civil.selectbox(
                "Estado Civil",
                [
                    "Solteiro(a)",
                    "Casado(a)",
                    "Divorciado(a)",
                    "Viúvo(a)",
                    "União Estável",
                ],
            )
            nome_conjuge = c_conj.text_input("Nome do cônjuge (se houver)")

            c_inst, c_peso, c_alt = st.columns(3)
            grau_instrucao = c_inst.selectbox(
                "Grau de Instrução",
                [
                    "Ensino Fundamental",
                    "Ensino Médio",
                    "Ensino Superior Incompleto",
                    "Ensino Superior Completo",
                    "Pós-graduação/Mestrado/Doutorado",
                ],
            )
            peso = c_peso.number_input("Peso (kg) *", min_value=0.0, step=0.1)
            altura = c_alt.number_input("Altura (m) *", min_value=0.0, step=0.01)

            # ---------------------------------------------------------
            # 2. ENDEREÇO
            # ---------------------------------------------------------
            st.markdown(
                "<div class='section-header'>🏠 2. Endereço</div>",
                unsafe_allow_html=True,
            )
            endereco = st.text_input("Endereço (Rua, Avenida, Número) *")

            c_comp, c_bairro, c_cep = st.columns(3)
            complemento = c_comp.text_input("Complemento (Apto, Bloco)")
            bairro = c_bairro.text_input("Bairro *")
            cep = c_cep.text_input("CEP")

            # ---------------------------------------------------------
            # 3. HISTÓRICO DE SAÚDE
            # ---------------------------------------------------------
            st.markdown(
                "<div class='section-header'>🩺 3. Triagem de Saúde</div>",
                unsafe_allow_html=True,
            )
            problemas = st.text_area("Liste os seus problemas de saúde:")
            medicamentos = st.text_area("Você faz uso contínuo de medicamentos? Quais?")
            alergia = st.text_input("Você é alérgico a algum medicamento? Quais?")
            restricoes = st.text_input(
                "Possui alguma restrição a prática de atividade física? Quais?"
            )

            outras_atividades = st.text_area(
                "Além das atividades do Imbra, pratica outras atividades físicas? (Quantas vezes na semana, quais atividades e por quanto tempo?)"
            )
            incomodos = st.text_input(
                "Sente algum incômodo durante ou após a prática de atividades físicas? Descreva:"
            )

            st.error(
                "🚨 **ATENÇÃO:** Para a segurança de todos, é estritamente obrigatório fornecer um contacto de emergência válido."
            )
            c_em_nome, c_em_tel = st.columns(2)
            emergencia_nome = c_em_nome.text_input("Nome do Contacto de Emergência *")
            emergencia_tel = c_em_tel.text_input("Telefone de Emergência *")

            # ---------------------------------------------------------
            # 4. PERFIL SOCIOECONÔMICO
            # ---------------------------------------------------------
            st.markdown(
                "<div class='section-header'>🤝 4. Perfil Socioeconômico e Voluntariado</div>",
                unsafe_allow_html=True,
            )
            c_mor, c_aposent = st.columns(2)
            residentes = c_mor.selectbox(
                "Quantos residentes na sua moradia (incluindo você)?",
                ["1 (Moro sozinho/a)", "2", "3", "4", "5 ou mais"],
            )
            aposentado = c_aposent.radio(
                "Você é aposentado(a)?", ["Sim", "Não"], horizontal=True
            )

            c_renda_f, c_renda_t = st.columns(2)
            fonte_renda = c_renda_f.text_input(
                "Principal fonte de renda (Ex: Aposentadoria, Pensão, Trabalho)"
            )
            renda_familiar = c_renda_t.selectbox(
                "Qual a renda da sua casa (contando todos os moradores)?",
                [
                    "Prefiro não informar",
                    "Até 1 salário mínimo",
                    "Até 2 salários mínimos",
                    "Até 3 salários mínimos",
                    "Até 4 salários mínimos",
                    "5 salários mínimos ou mais",
                ],
            )

            interesse_voluntario = st.radio(
                "Tem interesse em trabalho voluntário?", ["Sim", "Não"], horizontal=True
            )
            # Ações estruturadas (carregadas do banco)
            try:
                from database import get_acoes_voluntariado as _get_acoes_reg
                _acoes_reg = _get_acoes_reg()
            except Exception:
                _acoes_reg = []

            if _acoes_reg and interesse_voluntario == "Sim":
                _acoes_reg_opts = [f"{a.get('icone','🤝')} {a['nome']}" for a in _acoes_reg]
                _acoes_reg_sel  = st.multiselect(
                    "Em quais ações você gostaria de participar?",
                    options=_acoes_reg_opts,
                    help="Pode escolher mais de uma.",
                    key="reg_acoes_vol",
                )
                areas_voluntario = ", ".join(_acoes_reg_sel) if _acoes_reg_sel else ""
                if not _acoes_reg_sel:
                    areas_voluntario_extra = st.text_input(
                        "Outras áreas / observações (opcional):",
                        key="reg_acoes_vol_extra",
                    )
                    areas_voluntario = areas_voluntario_extra
                else:
                    areas_voluntario_extra = st.text_input(
                        "Observações adicionais (opcional):",
                        key="reg_acoes_vol_extra",
                    )
                    if areas_voluntario_extra:
                        areas_voluntario += f" | {areas_voluntario_extra}"
            else:
                areas_voluntario = st.text_input(
                    "Se sim, quais áreas você participaria? (Ex: Recepção, Artesanato, Ensinar algo)"
                )

            # ---------------------------------------------------------
            # 5. TURMA
            # ---------------------------------------------------------
            st.markdown(
                "<div class='section-header'>🗓️ 5. Preferência de Turma</div>",
                unsafe_allow_html=True,
            )

            turma_admin = None
            if modo_admin:
                try:
                    df_turmas = get_todas_turmas(ativas_apenas=True)
                    nomes_turmas = df_turmas["nome"].tolist() if not df_turmas.empty else []
                except Exception:
                    nomes_turmas = []
                if nomes_turmas:
                    turma_admin = st.selectbox(
                        "🎯 Alocar na Turma (obrigatório) *",
                        options=nomes_turmas,
                        help="Selecione a turma real onde o aluno será matriculado. Esta seleção ficará salva e pré-preenchida na triagem.",
                    )
                else:
                    st.warning("⚠️ Nenhuma turma ativa encontrada. Crie turmas no módulo de Gestão de Turmas.")

            st.info(
                "💡 As turmas têm limite de vagas. Escolha uma segunda opção para a Lista de Espera caso a primeira esteja lotada."
            )
            dias_pref = st.selectbox(
                "Quais dias prefere treinar? *",
                [
                    "Segundas, Quartas e Sextas",
                    "Terças e Quintas",
                    "Todos os dias (Seg a Sex)",
                ],
            )

            c_hora1, c_hora2 = st.columns(2)
            hora_pref = c_hora1.selectbox(
                "1ª Opção de Horário *",
                ["08:00 às 09:00", "09:00 às 10:00", "10:00 às 11:00"],
            )
            hora_pref_2 = c_hora2.selectbox(
                "2ª Opção de Horário",
                ["Nenhuma", "08:00 às 09:00", "09:00 às 10:00", "10:00 às 11:00"],
            )

            # ---------------------------------------------------------
            # 6. DOCUMENTAÇÃO E ASSINATURA
            # ---------------------------------------------------------
            st.markdown(
                "<div class='section-header'>📄 6. Documentação Médica e Legal</div>",
                unsafe_allow_html=True,
            )
            st.write("Anexe os documentos abaixo em formato Imagem ou PDF.")

            c_up_foto, c_up_rg, c_up_rec, c_up_atest = st.columns(4)
            with c_up_foto:
                foto_file = st.file_uploader(
                    "📸 Foto do Aluno", type=["jpg", "jpeg", "png"]
                )
            with c_up_rg:
                rg_file = st.file_uploader(
                    "1. Cópia do RG/CPF", type=["jpg", "jpeg", "png", "pdf"]
                )
            with c_up_rec:
                receita_file = st.file_uploader(
                    "2. Receituário Médico", type=["jpg", "jpeg", "png", "pdf"]
                )
            with c_up_atest:
                atestado_file = st.file_uploader(
                    "3. Atestado de Aptidão (anexe agora ou depois)",
                    type=["jpg", "jpeg", "png", "pdf"],
                )

            # Data de emissão + vencimento calculado — sempre visível
            _c_data_at, _c_venc_at = st.columns([2, 2])
            data_atestado = _c_data_at.date_input(
                "📅 Data de emissão do atestado *",
                value=datetime.date.today(),
                format="DD/MM/YYYY",
                key="pub_data_atestado",
                help="Data em que o médico assinou o atestado. O vencimento é calculado automaticamente (+ 1 ano).",
            )
            _venc_calc = data_atestado + datetime.timedelta(days=365)
            _c_venc_at.markdown(
                f"<div style='margin-top:26px;background:#F0FDF4;border-left:4px solid #22C55E;"
                f"padding:8px 14px;border-radius:6px;font-size:13px;'>"
                f"✅ <b>Válido até: {_venc_calc.strftime('%d/%m/%Y')}</b><br>"
                f"<span style='color:#6B7280;font-size:11px;'>emissão + 1 ano</span></div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                """
            <div class="caixa-lgpd">
                <strong>TERMO DE CONSENTIMENTO LIVRE (LGPD - LEI Nº 13.709/2018) E DIREITO DE IMAGEM</strong><br><br>
                1. Autorizo a coleta e tratamento dos meus dados de saúde para fins de segurança e adequação física.<br>
                2. Autorizo o uso da minha imagem e voz para fins de divulgação do projeto de forma gratuita.
            </div>
            """,
                unsafe_allow_html=True,
            )
            termo = st.checkbox(
                "Li e aceito os Termos da LGPD, Uso de Imagem e assumo a veracidade das informações médicas. *"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button(
                "🚀 Assinar Digitalmente e Enviar",
                type="primary",
                use_container_width=True,
            )

            if submit:
                if (
                    not nome
                    or not cpf
                    or not celular
                    or not endereco
                    or not emergencia_nome
                    or not emergencia_tel
                    or peso == 0
                    or altura == 0
                    or not email
                ):
                    st.error(
                        "⚠️ Por favor, preencha todos os campos obrigatórios (marcados com *)."
                    )
                elif not termo:
                    st.error("⚠️ O consentimento da LGPD é obrigatório pela lei.")
                else:
                    with st.spinner(
                        "A processar documentos e a registar assinatura digital..."
                    ):
                        url_rg, url_receita, url_atestado, url_foto = None, None, None, None
                        falhas_upload = []

                        if foto_file:
                            b_ft, n_ft, t_ft = processar_documento(
                                foto_file.getvalue(), foto_file.name, foto_file.type
                            )
                            url_foto = upload_midia(b_ft, n_ft, t_ft)

                        if rg_file:
                            b_rg, n_rg, t_rg = processar_documento(
                                rg_file.getvalue(), rg_file.name, rg_file.type
                            )
                            url_rg = upload_midia(b_rg, n_rg, t_rg)
                            if url_rg is None:
                                falhas_upload.append("Cópia do RG/CPF")

                        if receita_file:
                            b_rec, n_rec, t_rec = processar_documento(
                                receita_file.getvalue(),
                                receita_file.name,
                                receita_file.type,
                            )
                            url_receita = upload_midia(b_rec, n_rec, t_rec)
                            if url_receita is None:
                                falhas_upload.append("Receituário Médico")

                        if atestado_file:
                            b_at, n_at, t_at = processar_documento(
                                atestado_file.getvalue(),
                                atestado_file.name,
                                atestado_file.type,
                            )
                            url_atestado = upload_midia(b_at, n_at, t_at)
                            if url_atestado is None:
                                falhas_upload.append("Atestado de Aptidão")
                        else:
                            falhas_upload.append("Atestado de Aptidão (não anexado)")

                        contato_emergencia_final = (
                            f"{emergencia_nome.strip()} - {emergencia_tel.strip()}"
                        )

                        # 🚀 CARGA DE DADOS COMPLETA (ALINHADA À PLANILHA DO CLIENTE)
                        dados_inserir = {
                            "nome": nome,
                            "email": email,
                            "celular": celular,
                            "cpf": cpf,
                            "rg": rg,
                            "data_nascimento": str(nascimento),
                            "naturalidade": naturalidade,
                            "sexo": sexo,
                            "estado_civil": estado_civil,
                            "nome_conjuge": nome_conjuge,
                            "grau_instrucao": grau_instrucao,
                            "peso": peso,
                            "altura": altura,
                            "endereco": endereco,
                            "complemento": complemento,
                            "bairro": bairro,
                            "cep": cep,
                            "problemas_saude": problemas,
                            "medicamentos": medicamentos,
                            "alergia_medicamento": alergia,
                            "restricoes_fisicas": restricoes,
                            "pratica_outras_atividades": outras_atividades,
                            "incomodo_atividades": incomodos,
                            "residentes_moradia": residentes,
                            "aposentado": aposentado,
                            "fonte_renda": fonte_renda,
                            "renda_familiar": renda_familiar,
                            "interesse_voluntariado": interesse_voluntario,
                            "areas_voluntariado": areas_voluntario,
                            "contato_emergencia": contato_emergencia_final,
                            "dias_preferenciais": dias_pref,
                            "horario_preferencial": hora_pref,
                            "horario_preferencial_2": hora_pref_2,
                            "termo_imagem": termo,
                            "foto_url": url_foto,
                            "url_rg": url_rg,
                            "url_receituario": url_receita,
                            "url_atestado_medico": url_atestado,
                            "data_atestado": str(data_atestado) if data_atestado else None,
                            "data_vencimento_atestado": str(data_atestado + datetime.timedelta(days=365)) if data_atestado else None,
                            "status": "Pendente",
                        }
                        if modo_admin and turma_admin:
                            dados_inserir["turma"] = turma_admin

                        def _tentar_inserir(dados: dict) -> list:
                            """Insere na pre_cadastros removendo automaticamente colunas ausentes.
                            Retorna lista de colunas que foram descartadas (para aviso ao operador)."""
                            import re as _re
                            _ESSENCIAIS = {"nome", "cpf", "email", "celular", "status"}
                            _dados = dict(dados)
                            removidas = []
                            while True:
                                try:
                                    supabase.table("pre_cadastros").insert(_dados).execute()
                                    return removidas
                                except Exception as _e:
                                    _err = str(_e)
                                    if "PGRST204" in _err or (
                                        "column" in _err.lower() and
                                        ("not found" in _err.lower() or "schema" in _err.lower())
                                    ):
                                        _m = _re.search(r"'([a-z_]+)'\s+column", _err)
                                        if not _m:
                                            _m = _re.search(r"column\s+'([a-z_]+)'", _err)
                                        if not _m:
                                            _m = _re.search(r"find\s+the\s+'([a-z_]+)'", _err)
                                        _col = _m.group(1) if _m else None
                                        if _col and _col in _dados and _col not in _ESSENCIAIS:
                                            removidas.append(_col)
                                            del _dados[_col]
                                            continue
                                    raise

                        try:
                            _cols_removidas = _tentar_inserir(dados_inserir)
                            if _cols_removidas:
                                _sql_fix = "\n".join(
                                    f"ALTER TABLE pre_cadastros ADD COLUMN IF NOT EXISTS {c} TEXT;"
                                    for c in _cols_removidas
                                )
                                st.warning(
                                    f"⚠️ Inscrição salva, mas **{len(_cols_removidas)} campo(s) ignorado(s)** "
                                    f"por não existirem ainda na tabela: `{'`, `'.join(_cols_removidas)}`.\n\n"
                                    f"Peça ao administrador para rodar no Supabase SQL Editor:\n```sql\n{_sql_fix}\n```"
                                )

                            disparar_email_lgpd(
                                email,
                                nome.split()[0],
                                datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            )
                            if falhas_upload:
                                st.success(
                                    "✅ **Inscrição salva com sucesso!** Seus dados foram gravados — nada foi perdido."
                                )
                                st.warning(
                                    "⚠️ Os seguintes documentos ainda **não** foram enviados e precisarão ser "
                                    "entregues depois: "
                                    + ", ".join(falhas_upload)
                                    + "."
                                )
                            else:
                                st.success(
                                    "✅ **Inscrição validada e assinada!** Uma cópia do termo foi enviada para o seu e-mail."
                                )
                                st.balloons()
                        except Exception as e:
                            st.error(
                                f"Erro ao salvar: {e}. Verifique se todas as novas colunas foram criadas na tabela 'pre_cadastros' do Supabase."
                            )
