# ==============================================================================
# 📄 Arquivo: views/ficha_aluno_view.py
# 🏷️ VERSÃO: 11.9 (PRO Elite - Compliance LGPD com Cessão de Imagem)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Busca inteligente de alunos e geração de Ficha de Matrícula Oficial.
# ==============================================================================

import streamlit as st
import datetime
import base64
import unicodedata
import io
from database import buscar_alunos_geral

try:
    from st_keyup import st_keyup
    HAS_KEYUP = True
except ImportError:
    HAS_KEYUP = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

def normalizar_fonetica(texto):
    if not texto or not isinstance(texto, str): return ""
    t = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()
    t = t.replace("ct", "t").replace("ph", "f").replace("th", "t").replace("y", "i").replace("ll", "l").replace("nn", "n")
    return t.strip()

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{b64_string}"
    except Exception:
        return None

def gerar_qr_code_b64(texto_auditoria):
    if not HAS_QRCODE: return None
    try:
        qr = qrcode.QRCode(version=1, box_size=4, border=0)
        qr.add_data(texto_auditoria)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0A2540", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64_string = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{b64_string}"
    except Exception:
        return None

def gerar_html_ficha(aluno):
    nome = aluno.get('nome', 'NÃO INFORMADO')
    cpf = aluno.get('cpf', 'NÃO INFORMADO')
    rg = aluno.get('rg', 'NÃO INFORMADO')
    nascimento = aluno.get('data_nascimento', 'NÃO INFORMADO')
    telefone = aluno.get('whatsapp', 'NÃO INFORMADO')

    email_raw = aluno.get('email', 'NÃO INFORMADO')
    email = email_raw.lower() if isinstance(email_raw, str) and email_raw.strip() != "" and email_raw != 'NÃO INFORMADO' else 'NÃO INFORMADO'

    endereco = aluno.get('endereco', 'NÃO INFORMADO')
    turma = aluno.get('turma', 'Turma Padrão')
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    id_aluno = aluno.get('id', '0000')

    logo_b64 = get_base64_image("logo-imbra.png")
    if logo_b64: html_logo = f'<img src="{logo_b64}" style="max-width: 120px; max-height: 80px; width: auto; height: auto;" alt="Instituto Muda Brasil">'
    else: html_logo = "INSERIR LOGO<br>INSTITUTO"

    logo_sec_b64 = get_base64_image("logo-secretaria.png")
    if logo_sec_b64: html_logo_sec = f'<img src="{logo_sec_b64}" style="max-width: 120px; max-height: 80px; width: auto; height: auto;" alt="Logo Secretaria">'
    else: html_logo_sec = "INSERIR LOGO<br>SECRETARIA"

    texto_qr = f"AUDITORIA MOVERIGHT\nAluno: {nome}\nCPF: {cpf}\nEmissao: {data_hoje}\nProtocolo: {id_aluno}"
    qr_b64 = gerar_qr_code_b64(texto_qr)
    html_qr_code = f'<img src="{qr_b64}" style="width: 60px; height: 60px;">' if qr_b64 else '<div class="qr-placeholder">QR CODE<br>AUDITORIA</div>'

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Ficha de Matrícula - {nome}</title>
        <style>
            @page {{ size: A4; margin: 1.2cm; }}
            * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; color: #2c3e50; line-height: 1.4; font-size: 10pt; background: #fff; }}
            .page-container {{ width: 100%; max-width: 210mm; margin: auto; padding: 10px; }}
            header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #ff6b35; padding-bottom: 15px; margin-bottom: 20px; }}
            .logo-placeholder {{ width: 130px; height: 80px; background: transparent; display: flex; align-items: center; justify-content: center; font-size: 8pt; text-align: center; color: #64748b; }}
            .header-title {{ text-align: center; flex-grow: 1; padding: 0 10px; }}
            .header-title h1 {{ margin: 0; font-size: 16pt; color: #0a2540; text-transform: uppercase; font-weight: 900; }}
            .header-title h2 {{ margin: 5px 0 0 0; font-size: 11pt; font-weight: bold; color: #475569; }}
            .section {{ margin-bottom: 15px; }}
            .section-title {{ background: #f8fafc; padding: 6px 12px; font-weight: bold; text-transform: uppercase; font-size: 9pt; border-left: 4px solid #0056b3; margin-bottom: 10px; color: #0a2540; }}
            .data-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }}
            .data-item {{ border-bottom: 1px solid #f1f5f9; padding: 4px 0; }}
            .label {{ font-weight: bold; font-size: 8pt; color: #64748b; display: block; text-transform: uppercase; }}
            .value {{ font-size: 10pt; color: #0f172a; text-transform: uppercase; font-weight: 600; }}
            .value-lower {{ font-size: 10pt; color: #0f172a; font-weight: 600; }}
            .health-alert {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 12px; }}
            .legal-term {{ font-size: 8.5pt; text-align: justify; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; font-style: italic; margin: 20px 0; color: #475569; }}
            .signature-area {{ margin-top: 50px; display: flex; justify-content: center; width: 100%; }}
            .sig-box {{ width: 60%; text-align: center; }}
            .sig-line {{ border-top: 1px solid #0a2540; margin-bottom: 8px; }}
            .sig-label {{ font-size: 8pt; font-weight: bold; color: #0a2540; }}
            .footer-info {{ margin-top: 30px; display: flex; justify-content: space-between; align-items: flex-end; font-size: 7.5pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 10px; }}
            .qr-placeholder {{ width: 60px; height: 60px; border: 1px solid #cbd5e1; display: flex; align-items: center; justify-content: center; font-size: 6pt; text-align: center; background: #f8fafc; }}
            @media print {{ body {{ background: white; }} .page-container {{ border: none; width: 100%; padding: 0; }} .no-print {{ display: none !important; }} }}

            .btn-imprimir {{ position: fixed; top: 20px; right: 20px; background: #0056b3; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 15px rgba(0,86,179,0.3); transition: 0.3s; z-index: 1000; display: flex; align-items: center; gap: 8px; }}
            .btn-imprimir:hover {{ background: #004494; transform: translateY(-2px); }}
        </style>
    </head>
    <body>
        <button class="btn-imprimir no-print" onclick="window.print()">🖨️ IMPRIMIR FICHA A4</button>

        <div class="page-container">
            <header>
                <div class="logo-placeholder">{html_logo_sec}</div>
                <div class="header-title">
                    <h1>ESPORTE E SAÚDE NA COMUNIDADE - FASE 2</h1>
                    <h2>FICHA DE MATRÍCULA E TERMO DE ADESÃO</h2>
                    <div style="font-size: 8.5pt; margin-top: 8px; color: #64748b;">
                        <strong>ID Protocolo:</strong> #{id_aluno} &nbsp;|&nbsp; 
                        <strong>Emissão:</strong> {data_hoje}
                    </div>
                </div>
                <div class="logo-placeholder">{html_logo}</div>
            </header>

            <div class="section">
                <div class="section-title">Informações Cadastrais do Aluno</div>
                <div class="data-grid">
                    <div class="data-item" style="grid-column: span 2;">
                        <span class="label">Nome Completo</span>
                        <span class="value">{nome}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">CPF</span>
                        <span class="value">{cpf}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">RG</span>
                        <span class="value">{rg}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">Data de Nascimento</span>
                        <span class="value">{nascimento}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">Turma / Modalidade de Inscrição</span>
                        <span class="value">{turma}</span>
                    </div>
                    <div class="data-item" style="grid-column: span 2;">
                        <span class="label">Endereço Residencial</span>
                        <span class="value">{endereco}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">Telefone / WhatsApp</span>
                        <span class="value">{telefone}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">E-mail de Contato</span>
                        <span class="value-lower">{email}</span>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Saúde e Segurança de Risco</div>
                <div class="health-alert">
                    <div class="data-grid">
                        <div class="data-item">
                            <span class="label" style="color: #991b1b;">Liberação Médica para Atividades</span>
                            <span class="value" style="color: #7f1d1d;">Sim, Apto para atividades físicas</span>
                        </div>
                        <div class="data-item">
                            <span class="label" style="color: #991b1b;">Uso de Medicamentos Contínuos</span>
                            <span class="value" style="color: #7f1d1d;">Não Informado / Conforme Atestado</span>
                        </div>
                        <div class="data-item" style="grid-column: span 2;">
                            <span class="label" style="color: #991b1b;">Alergias ou Lesões Prévias Graves</span>
                            <span class="value" style="color: #7f1d1d;">Nenhuma restrição grave informada via sistema</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="legal-term">
                Eu, <strong>{nome}</strong>, declaro estar ciente e concordo com minha inscrição no Instituto Muda Brasil para o projeto ESPORTE E SAÚDE NA COMUNIDADE - FASE 2. Declaro que as informações de saúde acima são verídicas e condizem com meu atestado físico. Autorizo expressamente o tratamento de meus dados pessoais, <strong>bem como o uso gratuito da minha imagem e voz captadas durante as atividades</strong>, para fins de gestão acadêmica, prestação de contas oficial, divulgação institucional e registros de frequência, em total conformidade com a Lei Geral de Proteção de Dados (Lei 13.709/2018 - LGPD) e a legislação vigente sobre direitos de imagem.
            </div>

            <div class="signature-area">
                <div class="sig-box">
                    <div class="sig-line"></div>
                    <div class="sig-label">ASSINATURA DO ALUNO (OU RESPONSÁVEL LEGAL)</div>
                    <div style="font-size: 7.5pt; color: #64748b; margin-top: 4px;">Assinado fisicamente no dia: ___/___/202___</div>
                </div>
            </div>

            <div class="footer-info">
                <div>
                    <strong>Sistema Esporte e Saúde - Gestão Inteligente Moveright™</strong><br>
                    Instituto Muda Brasil | CNPJ: 08.817.519/0001-79 | mdbrasil.org
                </div>
                <div style="text-align: right; display: flex; align-items: center; gap: 10px;">
                    <span>Auditoria Digital:<br>Documento validado via QR Code.</span>
                    {html_qr_code}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def tela_impressao_ficha():
    st.markdown("### 🖨️ Ficha Oficial de Matrícula (Prestação de Contas)")
    st.write("Digite o nome do aluno abaixo. A lista atualiza automaticamente conforme digita.")

    df_alunos = buscar_alunos_geral("")
    if df_alunos.empty:
        st.warning("Nenhum aluno encontrado na base de dados.")
        return

    with st.container(border=True):
        st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0056b3; margin-bottom: 10px;'>🔍 BUSCAR ALUNO</div>", unsafe_allow_html=True)
        if HAS_KEYUP:
            termo_busca = st_keyup("Buscar", label_visibility="collapsed", placeholder="🔍 Digite pelo menos 3 letras (Busca Automática)...")
        else:
            termo_busca = st.text_input("Buscar", label_visibility="collapsed", placeholder="🔍 Digite pelo menos 3 letras e prima ENTER...")

    if termo_busca and len(termo_busca) >= 3:
        termo_norm = normalizar_fonetica(termo_busca)
        df_alunos['nome_norm'] = df_alunos['nome'].apply(normalizar_fonetica)
        df_view = df_alunos[df_alunos['nome_norm'].str.contains(termo_norm, case=False, na=False)].sort_values("nome")

        if df_view.empty:
            st.warning("⚠️ Nenhum aluno encontrado com este nome.")
        else:
            st.markdown(f"**{len(df_view)} aluno(s) encontrado(s):**")
            for idx, row in df_view.iterrows():
                with st.container(border=True):
                    c_info, c_acao = st.columns([4, 1], vertical_alignment="center")
                    with c_info:
                        st.markdown(f"**👤 {row['nome']}**")
                        st.caption(f"CPF: {row.get('cpf', 'N/A')} | Turma: {row.get('turma', 'N/A')}")
                    with c_acao:
                        if st.button("🖨️ Gerar Ficha", key=f"btn_ficha_{row['id']}", use_container_width=True):
                            st.session_state["aluno_ficha_selecionado"] = row.to_dict()

    if st.session_state.get("aluno_ficha_selecionado"):
        aluno_dados = st.session_state["aluno_ficha_selecionado"]
        st.markdown("<hr style='border-top: 2px dashed #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)

        c_status, c_btn = st.columns([2, 1], vertical_alignment="center")
        c_status.success(f"✅ Ficha gerada para: **{aluno_dados['nome']}**")

        html_gerado = gerar_html_ficha(aluno_dados)
        with c_btn:
            st.download_button(
                label="📄 BAIXAR FICHA (PDF/IMPRESSÃO)",
                data=html_gerado,
                file_name=f"Ficha_Matricula_{aluno_dados.get('id', '00')}.html",
                mime="text/html",
                type="primary",
                use_container_width=True
            )

        st.info("💡 **Dica:** O ficheiro HTML será descarregado. Abra-o no navegador e prima **Ctrl+P** (Salvar como PDF). As margens já estão bloqueadas para A4 perfeito.")
        with st.expander("👀 Ver Pré-visualização do Documento", expanded=True):
            st.components.v1.html(html_gerado, height=900, scrolling=True)