# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_niver.py
# 🏷️ VERSÃO: 13.0 PRIMEMAX (Cartaz Ecológico — Layout Simétrico em 2 Colunas)
# 👤 COPYRIGHT: © 2026 MoveRight Gestão Inteligente • Instituto Muda Brasil
# 📏 LINHAS: ~260
# ⚙️ FUNÇÃO: Portal de Aniversários e Emissão de Cartazes Oficiais em Word/PDF.
#            Gera listas organizadas em duas colunas paralelas com injeção
#            simétrica de duas logos oficiais para máxima economia de papel.
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
from utils.identidade import (
    get_config as _get_id_cfg,
    get_logo_data_url as _get_logo_url,
)

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
# 🗜️ FUNÇÕES UTILITÁRIAS E TRATAMENTO DE IMAGEM
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
# 📘 MOTOR 1: GERAÇÃO DO WORD NATIVO (.DOCX)
# ==============================================================================
def gerar_cartaz_word_core(df_mes, titulo, subtitulo="", mensagem_cartaz=""):
    if not DOCX_DISPONIVEL:
        raise RuntimeError(f"python-docx indisponível: {_DOCX_ERR}")
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    _niver_cfg = _get_id_cfg()
    _niver_logo = _niver_cfg.get("logo_principal", "logo-imbra.png")
    if os.path.exists(_niver_logo):
        try:
            p_logo = doc.add_paragraph()
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_logo = p_logo.add_run()
            run_logo.add_picture(_niver_logo, width=Inches(1.5))
        except Exception:
            pass

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

    if mensagem_cartaz.strip():
        p_msg = doc.add_paragraph()
        p_msg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_m = p_msg.add_run(f'"{mensagem_cartaz.strip()}"\n')
        run_m.font.size = Pt(11)
        run_m.font.italic = True
        run_m.font.color.rgb = RGBColor(71, 85, 105)

    table = doc.add_table(rows=0, cols=3)
    table.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
        if "WD_TABLE_ALIGNMENT" in locals()
        else WD_ALIGN_PARAGRAPH.CENTER
    )
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
# 📕 MOTOR 2: GERAÇÃO DO CARTAZ ECO-PDF (LAYOUT GRIDO DE 2 COLUNAS)
# ==============================================================================
def gerar_cartaz_pdf_core(df_mes, titulo, subtitulo="", mensagem_cartaz=""):
    if not XHTML_DISPONIVEL:
        return None

    cfg = _get_id_cfg()
    logo_p_url = _get_logo_url(cfg.get("logo_principal", "logo-imbra.png"))
    logo_s_url = _get_logo_url(cfg.get("logo_secundaria", "logo-secretaria.png"))

    html_logo_p = (
        f'<img src="{logo_p_url}" style="height: 60px; width: auto;">'
        if logo_p_url
        else ""
    )
    html_logo_s = (
        f'<img src="{logo_s_url}" style="height: 60px; width: auto;">'
        if logo_s_url
        else ""
    )

    if not mensagem_cartaz.strip():
        mensagem_cartaz = (
            "Celebrando os aniversariantes! Muita saúde e vida ativa para todos!"
        )

    # ── CONSTRUÇÃO DO GRID DE DUAS COLUNAS LADO A LADO ──
    linhas_colunas_html = ""
    registros = df_mes.reset_index(drop=True)

    for i in range(0, len(registros), 2):
        # Configuração Dinâmica da Célula Esquerda (Aluno Ímpar)
        aluno_esq = registros.iloc[i]
        nome_esq = str(aluno_esq["nome"]).upper().strip()
        dia_esq = f"{int(aluno_esq['dia']):02d}/{int(aluno_esq['mes']):02d}"
        b64_img_esq = processar_imagem_para_redondo_b64(aluno_esq.get("url_foto"))

        foto_html_esq = (
            f'<img src="data:image/png;base64,{b64_img_esq}" class="foto-perfil">'
            if b64_img_esq
            else '<div class="no-foto"></div>'
        )

        celula_esquerda = f"""
            <td class="celula-aluno">
                <table style="width: 100%; border: none;">
                    <tr>
                        <td style="width: 75px; border: none; text-align: center;">{foto_html_esq}</td>
                        <td style="border: none; text-align: left; padding-left: 10px;">
                            <div class="nome-aluno">{nome_esq}</div>
                            <div class="data-aluno">🎂 {dia_esq}</div>
                        </td>
                    </tr>
                </table>
            </td>
        """

        # Configuração Dinâmica da Célula Direita (Aluno Par, se houver)
        if i + 1 < len(registros):
            aluno_dir = registros.iloc[i + 1]
            nome_dir = str(aluno_dir["nome"]).upper().strip()
            dia_dir = f"{int(aluno_dir['dia']):02d}/{int(aluno_dir['mes']):02d}"
            b64_img_dir = processar_imagem_para_redondo_b64(aluno_dir.get("url_foto"))

            foto_html_dir = (
                f'<img src="data:image/png;base64,{b64_img_dir}" class="foto-perfil">'
                if b64_img_dir
                else '<div class="no-foto"></div>'
            )

            celula_direita = f"""
                <td class="celula-aluno">
                    <table style="width: 100%; border: none;">
                        <tr>
                            <td style="width: 75px; border: none; text-align: center;">{foto_html_dir}</td>
                            <td style="border: none; text-align: left; padding-left: 10px;">
                                <div class="nome-aluno">{nome_dir}</div>
                                <div class="data-aluno">🎂 {dia_dir}</div>
                            </td>
                        </tr>
                    </table>
                </td>
            """
        else:
            celula_direita = '<td class="celula-vazia"></td>'

        linhas_colunas_html += f"<tr>{celula_esquerda}{celula_direita}</tr>"

    html_content = f"""
    <html><head><meta charset="UTF-8"><style>
        @page {{ size: A4 portrait; margin: 1.2cm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; color: #1E293B; text-align: center; }}
        .tb-header {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; border-bottom: 3px solid #1E88E5; padding-bottom: 12px; }}
        .tb-header td {{ border: none; vertical-align: middle; }}
        .header-center h1 {{ font-size: 24px; color: #1E88E5; margin: 0; font-weight: bold; }}
        .header-center h2 {{ font-size: 14px; color: #64748B; margin: 4px 0 0 0; font-weight: bold; }}
        .msg-box {{ background-color: #F0F9FF; border-left: 4px solid #1E88E5; padding: 12px; text-align: center; font-size: 12px; font-style: italic; color: #0369A1; margin-bottom: 25px; }}
        .grid-table {{ width: 100%; border-collapse: separate; border-spacing: 12px; }}
        .celula-aluno {{ width: 50%; background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 10px; vertical-align: middle; border-radius: 6px; }}
        .foto-perfil {{ width: 65px; height: 65px; border-radius: 32.5px; border: 2px solid #1E88E5; object-fit: cover; }}
        .no-foto {{ width: 65px; height: 65px; border-radius: 32.5px; border: 1px dashed #94A3B8; background: #F1F5F9; display: inline-block; }}
        .nome-aluno {{ font-size: 11px; font-weight: bold; color: #0F172A; line-height: 1.3; }}
        .data-aluno {{ font-size: 11px; font-weight: bold; color: #DC2626; margin-top: 2px; }}
        .celula-vazia {{ width: 50%; border: none; background: none; }}
        .footer-tag {{ text-align: center; font-size: 8px; color: #94A3B8; margin-top: 35px; border-top: 1px solid #E2E8F0; padding-top: 8px; }}
    </style></head><body>
        <table class="tb-header">
            <tr>
                <td style="width: 20%; text-align: left;">{html_logo_s}</td>
                <td style="width: 60%;" class="header-center">
                    <h1>{titulo}</h1>
                    {f"<h2>{subtitulo}</h2>" if subtitulo else ""}
                </td>
                <td style="width: 20%; text-align: right;">{html_logo_p}</td>
            </tr>
        </table>
        <div class="msg-box">"{mensagem_cartaz.strip()}"</div>
        <table class="grid-table">
            <tbody>{linhas_colunas_html}</tbody>
        </table>
        <div class="footer-tag">Moveright™ Sistema de Gestão Integrada • {cfg.get("nome_organizacao", "Instituto Muda Brasil")}</div>
    </body></html>
    """

    result = io.BytesIO()
    pisa.pisaDocument(io.StringIO(html_content), result)
    return result.getvalue()


# ==============================================================================
# 🧭 INTERFACE PRINCIPAL DO DASHBOARD (STREAMLIT RENDER)
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

    for _, r in df_mes.iterrows():
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
