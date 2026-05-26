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
    def _v(campo, fallback="Não informado"):
        v = aluno.get(campo)
        return str(v).strip() if v and str(v).strip() not in ("", "None", "nan") else fallback

    nome        = _v('nome', 'NÃO INFORMADO').upper()
    cpf         = _v('cpf')
    rg          = _v('rg')
    nascimento  = _v('data_nascimento')
    telefone    = _v('whatsapp')
    email       = _v('email', 'Não informado').lower()
    endereco    = _v('endereco')
    bairro      = _v('bairro', '')
    end_full    = f"{endereco}{', ' + bairro if bairro and bairro != 'Não informado' else ''}"
    turma       = _v('turma', 'Não definida')
    contato_eme = _v('contato_emergencia')
    problemas   = _v('problemas_saude', 'Nenhum informado')
    medicament  = _v('medicamentos', 'Nenhum informado')
    restricoes  = _v('restricoes_fisicas', 'Nenhuma informada')
    termo_img   = bool(aluno.get('termo_imagem'))

    data_hoje   = datetime.date.today().strftime("%d/%m/%Y")
    id_aluno    = aluno.get('id', '0000')

    logo_b64 = get_base64_image("logo-imbra.png")
    html_logo = (f'<img src="{logo_b64}" style="max-width:110px;max-height:70px;width:auto;height:auto;" alt="Instituto Muda Brasil">'
                 if logo_b64 else '<span style="font-size:7pt;color:#64748b;">LOGO INSTITUTO</span>')

    logo_sec_b64 = get_base64_image("logo-secretaria.png")
    html_logo_sec = (f'<img src="{logo_sec_b64}" style="max-width:110px;max-height:70px;width:auto;height:auto;" alt="Secretaria">'
                     if logo_sec_b64 else '<span style="font-size:7pt;color:#64748b;">LOGO PARCEIRO</span>')

    texto_qr = f"MOVERIGHT|{id_aluno}|{nome}|{cpf}|{data_hoje}"
    qr_b64   = gerar_qr_code_b64(texto_qr)
    html_qr  = (f'<img src="{qr_b64}" style="width:52px;height:52px;">'
                if qr_b64 else '<div class="qr-ph">QR</div>')

    # checkboxes: ☑ se já autorizado no sistema, ☐ para assinar na impressão
    chk_lgpd = '&#9744;'            # sempre vazio — requer assinatura física
    chk_img  = '&#9745;' if termo_img else '&#9744;'
    img_obs  = (' <span class="chk-sim">Autorizado digitalmente</span>' if termo_img
                else ' <span class="chk-nao">Pendente de autorização</span>')

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Ficha de Matrícula — {nome}</title>
<style>
  @page {{ size: A4 portrait; margin: 1cm 1.2cm; }}
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; color: #1e293b;
          line-height: 1.35; font-size: 8.8pt; background: #fff; }}
  .wrap {{ width: 100%; max-width: 190mm; margin: auto; }}

  /* ── CABEÇALHO ── */
  header {{ display: flex; align-items: center; justify-content: space-between;
            border-bottom: 2.5px solid #0056b3; padding-bottom: 8px; margin-bottom: 10px; }}
  .hd-logo {{ width: 115px; text-align: center; }}
  .hd-title {{ flex: 1; text-align: center; padding: 0 8px; }}
  .hd-title h1 {{ margin: 0; font-size: 12pt; color: #0a2540; text-transform: uppercase;
                  font-weight: 900; line-height: 1.2; }}
  .hd-title h2 {{ margin: 3px 0 0; font-size: 9.5pt; font-weight: 700; color: #0056b3; }}
  .hd-meta {{ font-size: 7.5pt; margin-top: 4px; color: #64748b; }}

  /* ── SEÇÕES ── */
  .sec {{ margin-bottom: 8px; }}
  .sec-hd {{ background: #0056b3; color: #fff; padding: 3px 8px;
             font-weight: 700; font-size: 8pt; text-transform: uppercase;
             letter-spacing: .4px; margin-bottom: 6px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; }}
  .grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px 12px; }}
  .fi {{ border-bottom: 1px solid #e2e8f0; padding: 2px 0 3px; }}
  .fi.span2 {{ grid-column: span 2; }}
  .fi.span3 {{ grid-column: span 3; }}
  .lb {{ font-weight: 700; font-size: 7.2pt; color: #64748b;
         display: block; text-transform: uppercase; margin-bottom: 1px; }}
  .vl {{ font-size: 8.8pt; color: #0f172a; font-weight: 600; text-transform: uppercase; }}
  .vl-low {{ font-size: 8.8pt; color: #0f172a; font-weight: 600; }}

  /* ── SAÚDE ── */
  .saude-box {{ background: #fff7ed; border: 1px solid #fed7aa;
                border-radius: 4px; padding: 6px 10px; }}

  /* ── TERMOS ── */
  .termos-wrap {{ display: flex; gap: 8px; margin-top: 8px; }}
  .termo-bloco {{ flex: 1; border: 1.5px solid #cbd5e1; border-radius: 5px;
                  padding: 8px 10px; background: #f8fafc; }}
  .termo-bloco.destaque {{ border-color: #93c5fd; background: #eff6ff; }}
  .termo-num {{ font-size: 7.5pt; font-weight: 900; color: #0056b3;
                text-transform: uppercase; letter-spacing: .3px; margin-bottom: 5px;
                border-bottom: 1px solid #dbeafe; padding-bottom: 3px; }}
  .termo-num.imagem {{ color: #7c3aed; border-bottom-color: #ddd6fe; }}
  .termo-check {{ display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; }}
  .chk-box {{ font-size: 15pt; line-height: 1; margin-top: -1px; flex-shrink: 0; color: #0f172a; }}
  .termo-txt {{ font-size: 7.8pt; color: #334155; text-align: justify; line-height: 1.45; }}
  .termo-txt strong {{ color: #0f172a; }}
  .chk-sim {{ color: #059669; font-size: 6.8pt; font-weight: 700; background: #d1fae5;
              padding: 1px 5px; border-radius: 3px; }}
  .chk-nao {{ color: #92400e; font-size: 6.8pt; font-weight: 700; background: #fef3c7;
              padding: 1px 5px; border-radius: 3px; }}
  .termo-badge {{ margin-top: 5px; font-size: 7pt; font-style: italic; color: #64748b; }}

  /* ── ASSINATURA ── */
  .assinatura {{ display: flex; justify-content: space-between; align-items: flex-end;
                 margin-top: 12px; gap: 16px; }}
  .sig-bloco {{ flex: 1; text-align: center; }}
  .sig-line {{ border-top: 1px solid #0a2540; margin-bottom: 4px; margin-top: 28px; }}
  .sig-label {{ font-size: 7.2pt; font-weight: 700; color: #0a2540; text-transform: uppercase; }}
  .sig-data {{ font-size: 7pt; color: #64748b; margin-top: 2px; }}

  /* ── RODAPÉ ── */
  .rodape {{ display: flex; justify-content: space-between; align-items: flex-end;
             border-top: 1px solid #e2e8f0; padding-top: 6px; margin-top: 10px;
             font-size: 7pt; color: #94a3b8; }}
  .qr-ph {{ width: 52px; height: 52px; border: 1px solid #cbd5e1;
             display: flex; align-items: center; justify-content: center;
             font-size: 5pt; text-align: center; background: #f8fafc; }}

  /* ── IMPRESSÃO ── */
  .btn-print {{ position: fixed; top: 16px; right: 16px; background: #0056b3; color: #fff;
                border: none; padding: 10px 20px; border-radius: 7px; font-size: 13px;
                font-weight: 700; cursor: pointer; z-index: 9999;
                box-shadow: 0 3px 12px rgba(0,86,179,.35); }}
  .btn-print:hover {{ background: #004494; }}
  @media print {{ .btn-print {{ display: none !important; }} }}
</style>
</head>
<body>
<button class="btn-print" onclick="window.print()">🖨️ IMPRIMIR / SALVAR PDF</button>

<div class="wrap">

  <!-- CABEÇALHO -->
  <header>
    <div class="hd-logo">{html_logo_sec}</div>
    <div class="hd-title">
      <h1>Esporte e Saúde na Comunidade — Fase 2</h1>
      <h2>Ficha de Matrícula e Termos de Adesão</h2>
      <div class="hd-meta"><strong>Protocolo:</strong> #{id_aluno} &nbsp;|&nbsp; <strong>Emissão:</strong> {data_hoje}</div>
    </div>
    <div class="hd-logo">{html_logo}</div>
  </header>

  <!-- DADOS CADASTRAIS -->
  <div class="sec">
    <div class="sec-hd">1. Dados Cadastrais</div>
    <div class="grid2">
      <div class="fi span2">
        <span class="lb">Nome Completo</span>
        <span class="vl">{nome}</span>
      </div>
      <div class="fi">
        <span class="lb">CPF</span>
        <span class="vl">{cpf}</span>
      </div>
      <div class="fi">
        <span class="lb">RG</span>
        <span class="vl">{rg}</span>
      </div>
      <div class="fi">
        <span class="lb">Data de Nascimento</span>
        <span class="vl">{nascimento}</span>
      </div>
      <div class="fi">
        <span class="lb">Turma / Modalidade</span>
        <span class="vl">{turma}</span>
      </div>
      <div class="fi span2">
        <span class="lb">Endereço Residencial</span>
        <span class="vl">{end_full}</span>
      </div>
      <div class="fi">
        <span class="lb">Telefone / WhatsApp</span>
        <span class="vl">{telefone}</span>
      </div>
      <div class="fi">
        <span class="lb">E-mail de Contato</span>
        <span class="vl-low">{email}</span>
      </div>
      <div class="fi span2">
        <span class="lb">Contato de Emergência</span>
        <span class="vl">{contato_eme}</span>
      </div>
    </div>
  </div>

  <!-- SAÚDE -->
  <div class="sec">
    <div class="sec-hd">2. Informações de Saúde e Segurança</div>
    <div class="saude-box">
      <div class="grid3">
        <div class="fi">
          <span class="lb" style="color:#92400e;">Problemas / Condições de Saúde</span>
          <span class="vl" style="color:#78350f;">{problemas}</span>
        </div>
        <div class="fi">
          <span class="lb" style="color:#92400e;">Medicamentos de Uso Contínuo</span>
          <span class="vl" style="color:#78350f;">{medicament}</span>
        </div>
        <div class="fi">
          <span class="lb" style="color:#92400e;">Restrições / Lesões Físicas</span>
          <span class="vl" style="color:#78350f;">{restricoes}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- TERMOS LADO A LADO -->
  <div class="sec">
    <div class="sec-hd">3. Termos de Consentimento — Assinale e Assine</div>
    <div class="termos-wrap">

      <!-- TERMO 1: LGPD / INSCRIÇÃO -->
      <div class="termo-bloco">
        <div class="termo-num">Termo 1 — Adesão e Proteção de Dados (LGPD)</div>
        <div class="termo-check">
          <span class="chk-box">{chk_lgpd}</span>
          <p class="termo-txt">
            Eu, <strong>{nome}</strong>, declaro que as informações de saúde prestadas são
            verdadeiras e condizem com meu atestado de aptidão física, e que estou
            ciente das normas e do regulamento do projeto
            <strong>Esporte e Saúde na Comunidade — Fase 2</strong>.
            Autorizo o tratamento dos meus dados pessoais
            (nome, CPF, RG, dados de saúde e frequência) para fins exclusivos de
            gestão acadêmica, prestação de contas oficial e registros de frequência,
            em conformidade com a
            <strong>Lei Geral de Proteção de Dados — LGPD (Lei nº 13.709/2018)</strong>.
          </p>
        </div>
        <div class="termo-badge">
          Lei 13.709/2018 — LGPD &nbsp;|&nbsp; Art. 7º, inciso V (execução de contrato/serviço público)
        </div>
      </div>

      <!-- TERMO 2: IMAGEM -->
      <div class="termo-bloco destaque">
        <div class="termo-num imagem">Termo 2 — Autorização de Uso de Imagem e Voz <span style="font-weight:400;font-size:6.8pt;">(opcional)</span></div>
        <div class="termo-check">
          <span class="chk-box">{chk_img}</span>
          <p class="termo-txt">
            Autorizo, <strong>a título gratuito e por prazo indeterminado</strong>,
            o uso da minha imagem e voz captadas em fotos e vídeos durante as
            atividades do projeto, para fins <strong>exclusivos</strong> de:
            prestação de contas oficial, relatórios técnicos e divulgação
            institucional (redes sociais, site e materiais do Instituto Muda Brasil).
            <br><strong>A não autorização não impede minha participação no projeto.</strong>
            Esta autorização poderá ser revogada a qualquer momento mediante
            comunicação formal ao coordenador do projeto.{img_obs}
          </p>
        </div>
        <div class="termo-badge">
          Lei 9.610/1998 — Direitos Autorais &nbsp;|&nbsp; Art. 5º CC — Direito de Imagem
        </div>
      </div>

    </div>
  </div>

  <!-- ASSINATURA -->
  <div class="assinatura">
    <div class="sig-bloco" style="flex:2;">
      <div class="sig-line"></div>
      <div class="sig-label">Assinatura do Aluno / Responsável Legal</div>
      <div class="sig-data">Data: _______ / _______ / 202_____</div>
    </div>
    <div class="sig-bloco">
      <div class="sig-line"></div>
      <div class="sig-label">Assinatura do Coordenador</div>
      <div class="sig-data">Data: _______ / _______ / 202_____</div>
    </div>
  </div>

  <!-- RODAPÉ -->
  <div class="rodape">
    <div>
      <strong>Sistema MoveRight Elite™ — Gestão Inteligente de Saúde e Esporte</strong><br>
      Instituto Muda Brasil &nbsp;|&nbsp; CNPJ: 08.817.519/0001-79 &nbsp;|&nbsp; imbra.org.br
    </div>
    <div style="text-align:right; display:flex; align-items:center; gap:8px;">
      <span>Autenticidade digital:<br>escaneie o QR Code.</span>
      {html_qr}
    </div>
  </div>

</div>
</body>
</html>"""
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