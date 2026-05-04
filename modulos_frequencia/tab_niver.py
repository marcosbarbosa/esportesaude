# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_niver.py
# 🏷️ VERSÃO: 12.0 (PRO Elite - Títulos Inteligentes e Logo Oficial)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Portal de Aniversários, Geração de Cartazes Word/PDF com Logos.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import base64
import io
import os
import requests
from PIL import Image, ImageOps
from database import buscar_alunos_geral
from utils.texto import formatar_whatsapp_link

try:
    from xhtml2pdf import pisa

    XHTML_DISPONIVEL = True
except ImportError:
    XHTML_DISPONIVEL = False

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_ALIGN_VERTICAL

    DOCX_DISPONIVEL = True
    _DOCX_ERR = None
except Exception as _e:
    DOCX_DISPONIVEL = False
    _DOCX_ERR = str(_e)


# ==============================================================================
# FUNÇÕES UTILITÁRIAS E TRATAMENTO DE IMAGEM
# ==============================================================================


def processar_imagem_para_redondo_b64(url, size=(120, 120)):
    if not url or pd.isna(url):
        return None
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            img = ImageOps.fit(img, size, centering=(0.5, 0.5))
            mask = Image.new("L", size, 0)
            from PIL import ImageDraw

            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            output = Image.new("RGBA", size, (255, 255, 255, 0))
            output.paste(img, (0, 0), mask)
            buffer = io.BytesIO()
            output.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        pass
    return None


def processar_imagem_para_redondo_word(url, size=(150, 150)):
    if not url or pd.isna(url):
        return None
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            img = ImageOps.fit(img, size, centering=(0.5, 0.5))
            mask = Image.new("L", size, 0)
            from PIL import ImageDraw

            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            output = Image.new("RGBA", size, (255, 255, 255, 0))
            output.paste(img, (0, 0), mask)
            background = Image.new("RGB", size, (255, 255, 255))
            background.paste(output, mask=output.split()[3])
            buffer = io.BytesIO()
            background.save(buffer, format="PNG")
            return buffer.getvalue()
    except Exception:
        pass
    return None


# ==============================================================================
# MOTOR 1: GERAÇÃO DO WORD
# ==============================================================================
def gerar_cartaz_word_core(df_mes, titulo, subtitulo="", mensagem_cartaz=""):
    if not DOCX_DISPONIVEL:
        raise RuntimeError(f"python-docx indisponível: {_DOCX_ERR}")
    doc = Document()

    # Margens do Documento
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    # 🚀 Injeção da Logo Oficial via identidade central
    from utils.identidade import get_config as _gcfg_niver
    _niver_cfg = _gcfg_niver()
    _niver_logo = _niver_cfg.get("logo_principal", "logo-imbra.png")
    if os.path.exists(_niver_logo):
        try:
            p_logo = doc.add_paragraph()
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_logo = p_logo.add_run()
            run_logo.add_picture(_niver_logo, width=Inches(1.5))
        except Exception:
            pass

    # Títulos e Subtítulos Inteligentes
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_h = p_header.add_run(f"{titulo}\n")
    run_h.bold = True
    run_h.font.size = Pt(22)
    run_h.font.color.rgb = RGBColor(30, 136, 229)

    if subtitulo:
        run_sub = p_header.add_run(f"{subtitulo}\n")
        run_sub.bold = True
        run_sub.font.size = Pt(16)
        run_sub.font.color.rgb = RGBColor(100, 116, 139)

    # Mensagem de Felicitações
    if mensagem_cartaz.strip():
        p_msg = doc.add_paragraph()
        p_msg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_m = p_msg.add_run(f'"{mensagem_cartaz.strip()}"\n')
        run_m.font.size = Pt(11)
        run_m.font.italic = True
        run_m.font.color.rgb = RGBColor(71, 85, 105)

    # Tabela com as Fotos dos Alunos (3 Colunas)
    table = doc.add_table(rows=0, cols=3)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    col_idx = 0
    for _, r in df_mes.iterrows():
        if col_idx == 0:
            row_cells = table.add_row().cells
        cell = row_cells[col_idx]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        img_bytes = processar_imagem_para_redondo_word(r.get("url_foto"))
        if img_bytes:
            run_img = p.add_run()
            run_img.add_picture(io.BytesIO(img_bytes), width=Inches(1.2))
            p.add_run("\n")
        else:
            run_no_img = p.add_run("[ SEM FOTO ]\n")
            run_no_img.font.color.rgb = RGBColor(148, 163, 184)
            run_no_img.font.size = Pt(8)

        run_nome = p.add_run(f"{r['nome'].upper()}\n")
        run_nome.bold = True
        run_nome.font.size = Pt(11)
        run_data = p.add_run(f"{r['dia']:02d}/{r['mes']:02d}\n")
        run_data.font.color.rgb = RGBColor(220, 38, 38)
        run_data.bold = True
        col_idx = (col_idx + 1) % 3

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ==============================================================================
# MOTOR 2: GERAÇÃO DO PDF
# ==============================================================================
def gerar_cartaz_pdf_core(df_mes, titulo, subtitulo="", mensagem_cartaz=""):
    if not XHTML_DISPONIVEL:
        return None

    # 🚀 Injeção da Logo em Base64 para HTML via identidade central
    from utils.identidade import get_config as _gcfg_npdf, get_logo_data_url as _gld_npdf
    _npdf_cfg = _gcfg_npdf()
    _npdf_logo_url = _gld_npdf(_npdf_cfg.get("logo_principal", "logo-imbra.png"))
    html_logo = (
        f'<div style="text-align: center; margin-bottom: 10px;"><img src="{_npdf_logo_url}" style="width: 140px; height: auto;"></div>'
        if _npdf_logo_url else ""
    )

    html_subtitulo = (
        f"<h2 style='color: #64748B; font-size: 18px; margin-top: -15px;'>{subtitulo}</h2>"
        if subtitulo
        else ""
    )
    html_mensagem = (
        f'<p style="color: #475569; font-style: italic; font-size: 14px; margin-bottom: 20px;">"{mensagem_cartaz.strip()}"</p>'
        if mensagem_cartaz.strip()
        else "<br>"
    )

    html = f"""
    <html><head><style>
        @page {{ size: A4; margin: 1.5cm; }}
        body {{ font-family: Helvetica, sans-serif; text-align: center; color: #0F172A; }}
        h1 {{ color: #1E88E5; font-size: 26px; margin-bottom: 5px; }}
        .card {{ width: 30%; display: inline-block; padding: 10px; text-align: center; margin-bottom: 15px; }}
        .foto {{ width: 90px; height: 90px; border-radius: 45px; border: 3px solid #1E88E5; }}
        .no-foto {{ width: 90px; height: 90px; border-radius: 45px; border: 2px dashed #94A3B8; background: #F8FAFC; display: inline-block; }}
        .nome {{ font-size: 12px; font-weight: bold; margin-top: 5px; text-transform: uppercase; }}
        .data {{ font-size: 14px; font-weight: bold; color: #DC2626; }}
    </style></head><body>
    {html_logo}
    <h1>{titulo}</h1>
    {html_subtitulo}
    {html_mensagem}
    <div style="width: 100%; text-align: center;">"""

    for _, r in df_mes.iterrows():
        b64_img = processar_imagem_para_redondo_b64(r.get("url_foto"))
        # Alternativa de "Espaço Reservado" se não houver foto (melhor que emojis que quebram no PDF)
        img_tag = (
            f'<img src="data:image/png;base64,{b64_img}" class="foto">'
            if b64_img
            else '<div class="no-foto"></div>'
        )
        html += f'<div class="card">{img_tag}<div class="nome">{r["nome"]}</div><div class="data">{r["dia"]:02d}/{r["mes"]:02d}</div></div>'
    html += "</div></body></html>"

    result = io.BytesIO()
    pisa.pisaDocument(io.StringIO(html), result)
    return result.getvalue()


# ==============================================================================
# INTERFACE PRINCIPAL DO DASHBOARD
# ==============================================================================
def renderizar_aba_niver():
    df_alunos = buscar_alunos_geral("")
    if df_alunos.empty:
        st.warning("A base de alunos está vazia.")
        return

    df_alunos["data_nascimento"] = pd.to_datetime(
        df_alunos["data_nascimento"], errors="coerce"
    )
    df_validos = df_alunos.dropna(subset=["data_nascimento"]).copy()
    hoje = datetime.date.today()
    df_validos["dia"] = df_validos["data_nascimento"].dt.day
    df_validos["mes"] = df_validos["data_nascimento"].dt.month

    meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    c_mes, _, _ = st.columns([4, 1, 1], vertical_alignment="bottom")
    meses_selecionados = c_mes.multiselect(
        "Selecionar Mês(es):", list(meses.values()), default=[meses[hoje.month]]
    )

    if not meses_selecionados:
        st.warning("⚠️ Selecione pelo menos um mês para gerar o relatório.")
        return

    meses_inv = {v: k for k, v in meses.items()}
    meses_nums = [meses_inv[m] for m in meses_selecionados]
    df_mes = (
        df_validos[df_validos["mes"].isin(meses_nums)]
        .sort_values(by=["mes", "dia"])
        .copy()
    )

    # 🚀 LÓGICA MESTRA DE TÍTULO MULTI-MÊS
    if len(meses_selecionados) == 1:
        titulo_doc = f"ANIVERSARIANTES DE {meses_selecionados[0].upper()}"
        subtitulo_doc = ""
        nome_arq = meses_selecionados[0]
        nome_meses_tela = meses_selecionados[0]
    else:
        titulo_doc = "ANIVERSARIANTES"
        subtitulo_doc = (
            f"{meses_selecionados[0].upper()} A {meses_selecionados[-1].upper()}"
        )
        nome_arq = f"{meses_selecionados[0]}_A_{meses_selecionados[-1]}"
        nome_meses_tela = f"{meses_selecionados[0]} a {meses_selecionados[-1]}"

    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

    # 💌 Caixa de Mensagem
    c_msg, c_botoes = st.columns([3, 1], vertical_alignment="bottom")
    with c_msg:
        st.markdown(f"**💌 Mensagem Temática ({nome_meses_tela})**")
        st.selectbox(
            "Tom da mensagem:",
            ["🏃‍♀️ Energia & Movimento", "👨‍👩‍👧 Acolhedora", "✍️ Personalizada"],
            label_visibility="collapsed",
            key="tom_msg",
        )
        msg_base = f"Celebrando os aniversariantes de {nome_meses_tela}! Muita saúde e vida ativa para todos!"
        mensagem_digitada = st.text_area("Ajuste o texto:", value=msg_base, height=70)

    # 🖨️ Botões de Geração
    with c_botoes:
        if not df_mes.empty:
            if st.button("📕 GERAR PDF", use_container_width=True, type="primary"):
                st.session_state.pdf_niver = gerar_cartaz_pdf_core(
                    df_mes, titulo_doc, subtitulo_doc, mensagem_digitada
                )

            if "pdf_niver" in st.session_state:
                st.download_button(
                    "📥 BAIXAR PDF",
                    st.session_state.pdf_niver,
                    f"Cartaz_{nome_arq}.pdf",
                    "application/pdf",
                    use_container_width=True,
                )

    st.markdown(
        """<style>
        .zoom-niver { width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid #1E88E5; transition: transform 0.3s ease; cursor: zoom-in; }
        .zoom-niver:hover { transform: scale(3.5); z-index: 999; position: relative; }
        .badge-hoje { background: #10B981; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800; }
        .badge-passou { background: #F1F5F9; color: #64748B; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800; border: 1px solid #E2E8F0; }
        .badge-chegando { background: #FEF3C7; color: #D97706; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800; border: 1px solid #FDE68A; }
    </style>""",
        unsafe_allow_html=True,
    )

    # 📅 Exibição em Tela (Listagem Diária)
    for _, r in df_mes.iterrows():
        # Cálculo impecável de tempo real para o Badge
        aniv_data = datetime.date(hoje.year, int(r["mes"]), int(r["dia"]))
        delta = (aniv_data - hoje).days

        with st.container(border=True):
            c_av, c_info, c_status, c_whats, c_ficha = st.columns(
                [1, 3.5, 2, 0.8, 0.8], vertical_alignment="center"
            )
            with c_av:
                if pd.notna(r.get("url_foto")) and str(r.get("url_foto")).strip() != "":
                    st.markdown(
                        f'<img src="{r["url_foto"]}" class="zoom-niver">',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("👤", unsafe_allow_html=True)
            with c_info:
                st.markdown(f"**{r['nome'].upper()}**")
                st.markdown(
                    f"<span style='font-size:12px; color:#64748B;'>🎂 {r['dia']:02d}/{r['mes']:02d}</span>",
                    unsafe_allow_html=True,
                )
            with c_status:
                if delta == 0:
                    st.markdown(
                        '<span class="badge-hoje">🎈 É HOJE!</span>',
                        unsafe_allow_html=True,
                    )
                elif delta > 0:
                    st.markdown(
                        f'<span class="badge-chegando">⏳ Faltam {delta} dias</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span class="badge-passou">✔️ Já completou</span>',
                        unsafe_allow_html=True,
                    )
                _turma = str(r.get("turma") or "").strip()[:10]
                if _turma:
                    st.markdown(
                        f"<span style='font-size:12px; color:#000000; font-weight:600;'>📍 {_turma}</span>",
                        unsafe_allow_html=True,
                    )
            with c_whats:
                link_w = formatar_whatsapp_link(r.get("whatsapp"))
                if link_w:
                    st.markdown(
                        f'<a href="{link_w}?text=Parabéns!" target="_blank">💬</a>',
                        unsafe_allow_html=True,
                    )
            with c_ficha:
                if st.button("🩺", key=f"n_{r['id']}"):
                    st.session_state.aluno_prontuario = r.to_dict()
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.rerun()
