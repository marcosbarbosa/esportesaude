import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import os
from database import supabase

try:
    from xhtml2pdf import pisa
    _XHTML_SAT = True
except ImportError:
    _XHTML_SAT = False

try:
    from docx import Document as _DocxDoc
    from docx.shared import Inches as _Inches, Pt as _Pt, RGBColor as _RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH as _WD_ALIGN
    _DOCX_SAT = True
except ImportError:
    _DOCX_SAT = False


from utils.imagem import get_base64_image


# =========================================================================
# 🖨️ MOTOR DE GERAÇÃO DE RELATÓRIO OFICIAL (MS WORD)
# =========================================================================
def gerar_documento_word(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp):
    total_resp = len(df)
    data_emissao = datetime.date.today().strftime("%d/%m/%Y")

    # Cálculos para as tabelas do relatório
    def calc_tabela(coluna):
        if coluna not in df.columns:
            return ""
        contagem = df[coluna].value_counts()
        linhas = ""
        for sentimento, votos in contagem.items():
            if sentimento != "Sem Classificação":
                pct = int((votos / total_resp) * 100) if total_resp > 0 else 0
                linhas += f"<tr><td style='padding: 8px; border-bottom: 1px solid #E2E8F0;'>{sentimento}</td><td style='padding: 8px; border-bottom: 1px solid #E2E8F0; text-align: center;'>{votos}</td><td style='padding: 8px; border-bottom: 1px solid #E2E8F0; text-align: center;'>{pct}%</td></tr>"
        return linhas

    linhas_q4 = calc_tabela("Sentimento_Q4")
    linhas_q3 = calc_tabela("Sentimento_Q3")
    linhas_q1 = calc_tabela("Sentimento_Q1")
    linhas_q2 = calc_tabela("Sentimento_Q2")

    # Comentários Reais
    df_comentarios = df[df["comentario"].notna() & (df["comentario"].str.strip() != "")]
    html_comentarios = ""
    for _, row in df_comentarios.head(15).iterrows():
        html_comentarios += f"<div style='margin-bottom: 10px; padding: 10px; background: #F8FAFC; border-left: 3px solid #0056b3; font-size: 10pt;'><strong>{row.get('turma', 'Turma')}</strong>: <i>\"{row['comentario']}\"</i></div>"

    if not html_comentarios:
        html_comentarios = "<p style='font-size: 10pt; color: #64748B;'>Nenhum comentário registrado no período.</p>"

    # 🖼️ Processar a Logo via módulo de identidade central
    from utils.identidade import get_config as _gcfg_sat, get_logo_data_url as _gld_sat
    _scfg = _gcfg_sat()
    logo_b64 = _gld_sat(_scfg.get("logo_principal", "logo-imbra.png"))
    if logo_b64:
        html_logo = f'<img src="{logo_b64}" width="120" style="max-width: 120px; height: auto;" alt="{_scfg.get("nome_organizacao","Instituto Muda Brasil")}">'
        style_logo = "width: 20%; text-align: right; padding: 10px; vertical-align: middle;"
    else:
        html_logo = "INSERIR LOGO<br>INSTITUTO"
        style_logo = "width: 20%; text-align: right; color: #94A3B8; font-size: 8pt; border: 1px dashed #94A3B8; padding: 10px; vertical-align: middle;"

    # Cabeçalho OBRIGATÓRIO para forçar o MS Word a formatar corretamente
    head_word = "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>"

    # Estrutura base em HTML
    html_content = f"""{head_word}
    <head>
        <meta charset='UTF-8'>
        <title>Relatório de Satisfação</title>
        <style>
            body {{ font-family: 'Arial', sans-serif; color: #2C3E50; line-height: 1.4; font-size: 11pt; }}
            h1 {{ font-size: 16pt; color: #0A2540; text-transform: uppercase; text-align: center; margin-bottom: 5px; }}
            h2 {{ font-size: 11pt; color: #475569; text-transform: uppercase; text-align: center; margin-top: 0; }}
            .section-title {{ font-size: 12pt; font-weight: bold; color: #0A2540; border-bottom: 1px solid #CBD5E1; padding-bottom: 5px; margin-top: 25px; margin-bottom: 15px; }}
            table.data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 10pt; }}
            table.data-table th {{ background: #0056b3; color: white; padding: 8px; text-align: left; font-weight: bold; }}
            .footer {{ margin-top: 40px; text-align: center; font-size: 8pt; color: #94A3B8; border-top: 1px solid #E2E8F0; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <table style="width: 100%; border-bottom: 3px solid #0056b3; margin-bottom: 20px;">
            <tr>
                <td style="width: 20%; text-align: left; color: #94A3B8; font-size: 8pt; border: 1px dashed #94A3B8; padding: 10px; vertical-align: middle;">INSERIR LOGO<br>SECRETARIA</td>
                <td style="width: 60%; text-align: center; vertical-align: middle;">
                    <h1>{_scfg.get("titulo_projeto","Esporte e Saúde na Comunidade")}</h1>
                    <h2>Relatório Oficial de Satisfação</h2>
                    <p style="font-size: 9pt; color: #64748B; margin-top: 5px;"><strong>Período:</strong> {periodo} de {ano} | <strong>Emissão:</strong> {data_emissao}</p>
                </td>
                <td style="{style_logo}">{html_logo}</td>
            </tr>
        </table>

        <table style="width: 100%; text-align: center; font-size: 10pt; margin-bottom: 20px; border-collapse: collapse;">
            <tr>
                <td style="border: 1px solid #E2E8F0; padding: 10px; background: #F8FAFC; width: 20%;">
                    <span style="font-size: 18pt; font-weight: bold; color: #0A2540;">{total_resp}</span><br>
                    <span style="font-size: 8pt; font-weight: bold; color: #64748B;">PESQUISAS</span>
                </td>
                <td style="border: 1px solid #E2E8F0; padding: 10px; background: #F8FAFC; width: 20%;">
                    <span style="font-size: 18pt; font-weight: bold; color: #10B981;">{tx_exc}%</span><br>
                    <span style="font-size: 8pt; font-weight: bold; color: #64748B;">EXCELÊNCIA (AULAS)</span>
                </td>
                <td style="border: 1px solid #E2E8F0; padding: 10px; background: #F8FAFC; width: 20%;">
                    <span style="font-size: 18pt; font-weight: bold; color: #0056b3;">{tx_dor}%</span><br>
                    <span style="font-size: 8pt; font-weight: bold; color: #64748B;">ALÍVIO DORES</span>
                </td>
                <td style="border: 1px solid #E2E8F0; padding: 10px; background: #F8FAFC; width: 20%;">
                    <span style="font-size: 18pt; font-weight: bold; color: #F59E0B;">{tx_ene}%</span><br>
                    <span style="font-size: 8pt; font-weight: bold; color: #64748B;">MAIS ENERGIA</span>
                </td>
                <td style="border: 1px solid #E2E8F0; padding: 10px; background: #F8FAFC; width: 20%;">
                    <span style="font-size: 18pt; font-weight: bold; color: #8B5CF6;">{tx_imp}%</span><br>
                    <span style="font-size: 8pt; font-weight: bold; color: #64748B;">IMPACTO NA VIDA</span>
                </td>
            </tr>
        </table>

        <div class='section-title'>1. Qualidade dos Encontros e Metodologia (Professores)</div>
        <table class="data-table">
            <tr><th>Classificação de Sentimento</th><th style='text-align:center; width:15%;'>Votos</th><th style='text-align:center; width:15%;'>Proporção</th></tr>
            {linhas_q4}
        </table>

        <div class='section-title'>2. Impacto na Qualidade de Vida (Dores Crônicas)</div>
        <table class="data-table">
            <tr><th>Classificação de Sentimento</th><th style='text-align:center; width:15%;'>Votos</th><th style='text-align:center; width:15%;'>Proporção</th></tr>
            {linhas_q2}
        </table>

        <div class='section-title'>3. Aumento de Disposição e Energia no Dia a Dia</div>
        <table class="data-table">
            <tr><th>Classificação de Sentimento</th><th style='text-align:center; width:15%;'>Votos</th><th style='text-align:center; width:15%;'>Proporção</th></tr>
            {linhas_q1}
        </table>

        <div class='section-title'>4. Efeito Transformador da Atividade na Vida do Aluno</div>
        <table class="data-table">
            <tr><th>Classificação de Sentimento</th><th style='text-align:center; width:15%;'>Votos</th><th style='text-align:center; width:15%;'>Proporção</th></tr>
            {linhas_q3}
        </table>

        <div class='section-title'>5. Principais Depoimentos e Feedback Comunitário</div>
        {html_comentarios}

        <br><br><br>
        <table style="width: 100%; text-align: center; margin-top: 50px;">
            <tr>
                <td style="width: 50%; vertical-align: top;">
                    <div style="border-top: 1px solid #0A2540; width: 80%; margin: 0 auto; padding-top: 5px;">
                        <strong>COORDENADOR DO PROJETO</strong><br><span style="font-size: 8pt; color: #64748B;">Instituto Muda Brasil</span>
                    </div>
                </td>
                <td style="width: 50%; vertical-align: top;">
                    <div style="border-top: 1px solid #0A2540; width: 80%; margin: 0 auto; padding-top: 5px;">
                        <strong>REPRESENTANTE PÚBLICO</strong><br><span style="font-size: 8pt; color: #64748B;">Secretaria de Esportes</span>
                    </div>
                </td>
            </tr>
        </table>

        <div class='footer'>
            Documento gerado oficialmente pelo Sistema Gestão Inteligente Moveright™<br>
            A auditoria dos dados de origem pode ser validada no painel digital.
        </div>
    </body>
    </html>
    """
    return html_content


# =========================================================================
# 📕 PDF OFICIAL (xhtml2pdf) — gerado do mesmo HTML
# =========================================================================
def gerar_pdf_satisfacao_bytes(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp):
    """Converte o relatório HTML de satisfação em PDF real via xhtml2pdf."""
    if not _XHTML_SAT:
        return None
    html = gerar_documento_word(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp)
    resultado = io.BytesIO()
    pisa.pisaDocument(io.StringIO(html), resultado)
    return resultado.getvalue() if resultado.getvalue() else None


# =========================================================================
# 📘 WORD OFICIAL (python-docx nativo) — estrutura em tabelas
# =========================================================================
def gerar_docx_satisfacao_bytes(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp):
    """Gera um documento Word nativo (.docx) com python-docx."""
    if not _DOCX_SAT:
        return None

    from utils.identidade import get_config as _gcfg_w, get_logo_data_url as _gld_w
    import tempfile

    _cfg_w = _gcfg_w()
    logo_path = _cfg_w.get("logo_principal", "logo-imbra.png")

    total_resp = len(df)
    data_emissao = datetime.date.today().strftime("%d/%m/%Y")

    def _calc(coluna):
        if coluna not in df.columns:
            return []
        contagem = df[coluna].value_counts()
        return [
            (sent, votos, int((votos / total_resp) * 100) if total_resp > 0 else 0)
            for sent, votos in contagem.items()
            if sent != "Sem Classificação"
        ]

    doc = _DocxDoc()

    # ── Estilos globais ────────────────────────────────────────────────────
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = _Pt(11)

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    hdr_tbl = doc.add_table(rows=1, cols=3)
    hdr_tbl.style = "Table Grid"
    hdr_tbl.autofit = True

    # Col logo secretaria (placeholder)
    hdr_tbl.cell(0, 0).width = _Inches(1.4)
    p0 = hdr_tbl.cell(0, 0).paragraphs[0]
    run0 = p0.add_run("SECRETARIA\n(logo)")
    run0.font.size = _Pt(7)
    run0.font.color.rgb = _RGBColor(0x94, 0xA3, 0xB8)
    p0.alignment = _WD_ALIGN.CENTER

    # Col título central
    cell_c = hdr_tbl.cell(0, 1)
    pc = cell_c.paragraphs[0]
    r_title = pc.add_run(_cfg_w.get("titulo_projeto", "Esporte e Saúde na Comunidade").upper())
    r_title.bold = True
    r_title.font.size = _Pt(14)
    r_title.font.color.rgb = _RGBColor(0x0A, 0x25, 0x40)
    pc.alignment = _WD_ALIGN.CENTER
    p_sub = cell_c.add_paragraph("Relatório Oficial de Satisfação")
    p_sub.alignment = _WD_ALIGN.CENTER
    r_sub = p_sub.runs[0]
    r_sub.bold = True
    r_sub.font.size = _Pt(11)
    r_sub.font.color.rgb = _RGBColor(0x47, 0x55, 0x69)
    p_per = cell_c.add_paragraph(f"Período: {periodo} de {ano} | Emissão: {data_emissao}")
    p_per.alignment = _WD_ALIGN.CENTER
    p_per.runs[0].font.size = _Pt(9)

    # Col logo direita
    cell_logo = hdr_tbl.cell(0, 2)
    pl = cell_logo.paragraphs[0]
    pl.alignment = _WD_ALIGN.CENTER
    try:
        logo_data = _gld_w(logo_path)
        if logo_data and logo_data.startswith("data:"):
            b64_part = logo_data.split(",", 1)[1]
            img_bytes = __import__("base64").b64decode(b64_part)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name
            run_logo = pl.add_run()
            run_logo.add_picture(tmp_path, width=_Inches(1.0))
        else:
            pl.add_run("LOGO INSTITUTO").font.size = _Pt(7)
    except Exception:
        pl.add_run("LOGO INSTITUTO").font.size = _Pt(7)

    doc.add_paragraph()

    # ── Métricas em tabela de 5 colunas ───────────────────────────────────
    metricas = [
        ("PESQUISAS", str(total_resp), "0A2540"),
        ("EXCELÊNCIA (AULAS)", f"{tx_exc}%", "10B981"),
        ("ALÍVIO DORES", f"{tx_dor}%", "0056b3"),
        ("MAIS ENERGIA", f"{tx_ene}%", "F59E0B"),
        ("IMPACTO NA VIDA", f"{tx_imp}%", "8B5CF6"),
    ]
    met_tbl = doc.add_table(rows=2, cols=5)
    met_tbl.style = "Table Grid"
    for col_i, (label, valor, hex_cor) in enumerate(metricas):
        c_val = met_tbl.cell(0, col_i)
        p_v = c_val.paragraphs[0]
        r_v = p_v.add_run(valor)
        r_v.bold = True
        r_v.font.size = _Pt(16)
        r_v.font.color.rgb = _RGBColor(
            int(hex_cor[0:2], 16), int(hex_cor[2:4], 16), int(hex_cor[4:6], 16)
        )
        p_v.alignment = _WD_ALIGN.CENTER
        c_lbl = met_tbl.cell(1, col_i)
        p_l = c_lbl.paragraphs[0]
        r_l = p_l.add_run(label)
        r_l.bold = True
        r_l.font.size = _Pt(7)
        r_l.font.color.rgb = _RGBColor(0x64, 0x74, 0x8B)
        p_l.alignment = _WD_ALIGN.CENTER

    doc.add_paragraph()

    # ── Seções de perguntas ────────────────────────────────────────────────
    secoes = [
        ("1. Qualidade dos Encontros e Metodologia (Professores)", "Sentimento_Q4"),
        ("2. Impacto na Qualidade de Vida (Dores Crônicas)", "Sentimento_Q2"),
        ("3. Aumento de Disposição e Energia no Dia a Dia", "Sentimento_Q1"),
        ("4. Efeito Transformador da Atividade na Vida do Aluno", "Sentimento_Q3"),
    ]
    for titulo_sec, col in secoes:
        p_sec = doc.add_paragraph(titulo_sec)
        r_sec = p_sec.runs[0]
        r_sec.bold = True
        r_sec.font.size = _Pt(11)
        r_sec.font.color.rgb = _RGBColor(0x0A, 0x25, 0x40)

        linhas = _calc(col)
        if linhas:
            tbl = doc.add_table(rows=1 + len(linhas), cols=3)
            tbl.style = "Table Grid"
            for txt, header_col in zip(
                ["Classificação de Sentimento", "Votos", "Proporção"],
                range(3),
            ):
                cell_h = tbl.cell(0, header_col)
                ph = cell_h.paragraphs[0]
                rh = ph.add_run(txt)
                rh.bold = True
                rh.font.color.rgb = _RGBColor(0xFF, 0xFF, 0xFF)
                cell_h._tc.get_or_add_tcPr()
                from docx.oxml.ns import qn as _qn
                from docx.oxml import OxmlElement as _OE
                shading = _OE("w:shd")
                shading.set(_qn("w:fill"), "0056b3")
                shading.set(_qn("w:color"), "auto")
                shading.set(_qn("w:val"), "clear")
                cell_h._tc.tcPr.append(shading)

            for row_i, (sentimento, votos, pct) in enumerate(linhas, start=1):
                tbl.cell(row_i, 0).text = sentimento
                tbl.cell(row_i, 1).text = str(votos)
                tbl.cell(row_i, 2).text = f"{pct}%"
        else:
            doc.add_paragraph("Sem dados para este período.")
        doc.add_paragraph()

    # ── Comentários ────────────────────────────────────────────────────────
    p_com = doc.add_paragraph("5. Principais Depoimentos e Feedback Comunitário")
    p_com.runs[0].bold = True
    p_com.runs[0].font.size = _Pt(11)
    p_com.runs[0].font.color.rgb = _RGBColor(0x0A, 0x25, 0x40)

    df_coment = df[df["comentario"].notna() & (df["comentario"].str.strip() != "")]
    if df_coment.empty:
        doc.add_paragraph("Nenhum comentário registrado no período.")
    else:
        for _, row in df_coment.head(15).iterrows():
            p_q = doc.add_paragraph(style="List Bullet")
            r_t = p_q.add_run(f"{row.get('turma','Turma')}: ")
            r_t.bold = True
            p_q.add_run(f'"{row["comentario"]}"')

    doc.add_paragraph()

    # ── Assinaturas ────────────────────────────────────────────────────────
    sig_tbl = doc.add_table(rows=2, cols=3)
    sig_tbl.cell(0, 0).add_paragraph(
        "___________________________________"
    ).alignment = _WD_ALIGN.CENTER
    sig_tbl.cell(0, 2).add_paragraph(
        "___________________________________"
    ).alignment = _WD_ALIGN.CENTER
    ps1 = sig_tbl.cell(1, 0).paragraphs[0]
    ps1.add_run("COORDENADOR DO PROJETO\nInstituto Muda Brasil").bold = True
    ps1.alignment = _WD_ALIGN.CENTER
    ps2 = sig_tbl.cell(1, 2).paragraphs[0]
    ps2.add_run("REPRESENTANTE PÚBLICO\nSecretaria de Esportes").bold = True
    ps2.alignment = _WD_ALIGN.CENTER

    doc.add_paragraph()
    p_rod = doc.add_paragraph(
        "Documento gerado pelo Sistema Gestão Inteligente Moveright™\n"
        "A auditoria dos dados de origem pode ser validada no painel digital."
    )
    p_rod.runs[0].font.size = _Pt(8)
    p_rod.runs[0].font.color.rgb = _RGBColor(0x94, 0xA3, 0xB8)
    p_rod.alignment = _WD_ALIGN.CENTER

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# =========================================================================
# 📊 TELA PRINCIPAL DE BI
# =========================================================================
def tela_relatorio_prime_satisfacao():
    st.markdown(
        """
        <style>
            .metric-card { background-color: #FFFFFF; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #0056b3; text-align: center; height: 100%; }
            .metric-value { font-size: 32px; font-weight: 900; color: #0A2540; line-height: 1; margin-bottom: 5px; }
            .metric-label { font-size: 11px; font-weight: 800; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h3 style='color: #0A2540; font-weight: 800; margin-bottom: 0;'>⭐ Satisfação & Impacto na Saúde</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #64748B; margin-bottom: 16px;'>Gerencie os links da pesquisa, filtre por período e gere a prestação de contas oficial.</p>",
        unsafe_allow_html=True,
    )

    # ── Links de partilha da pesquisa ────────────────────────────────────────
    try:
        host = st.context.headers.get("host", "esportesaude.riker.replit.dev")
    except Exception:
        host = "esportesaude.riker.replit.dev"
    base_url = f"https://{host}/?rota=pesquisa"

    with st.expander("🔗 Links de Partilha da Pesquisa — clique para copiar", expanded=False):
        st.caption(
            "Passe o cursor sobre a caixa do trimestre desejado e clique no ícone "
            "de prancheta à direita para **copiar o link com 1 clique**."
        )
        cl1, cl2, cl3, cl4 = st.columns(4)
        with cl1:
            st.markdown("**1º Trim. (Jan–Mar)**")
            st.code(f"{base_url}&t=1", language="text")
        with cl2:
            st.markdown("**2º Trim. (Abr–Jun)**")
            st.code(f"{base_url}&t=2", language="text")
        with cl3:
            st.markdown("**3º Trim. (Jul–Set)**")
            st.code(f"{base_url}&t=3", language="text")
        with cl4:
            st.markdown("**Link Aberto (sempre ativo)**")
            st.code(f"{base_url}", language="text")
        st.markdown(
            f'<a href="{base_url}" target="_blank" style="font-size:12px;color:#0056b3;">'
            "🌐 Abrir formulário público →</a>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    try:
        response = supabase.table("pesquisas_satisfacao").select("*").execute()
        dados = response.data
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return

    if not dados:
        st.info(
            "📌 Aguardando os alunos responderem à primeira pesquisa para gerar os relatórios."
        )
        return

    df = pd.DataFrame(dados)
    if "data_resposta" in df.columns:
        df["data_resposta"] = pd.to_datetime(df["data_resposta"], errors="coerce")
    else:
        df["data_resposta"] = pd.to_datetime("today")

    with st.container(border=True):
        st.markdown(
            "<div style='font-size: 14px; font-weight: 700; color: #0056b3; margin-bottom: 10px;'>📅 FILTROS DE ANÁLISE</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 4], vertical_alignment="center")
        with c1:
            anos_disp = sorted(
                df["data_resposta"].dt.year.dropna().unique().astype(int).tolist(),
                reverse=True,
            )
            if not anos_disp:
                anos_disp = [datetime.date.today().year]
            ano_sel = st.selectbox(
                "Ano de Referência:", anos_disp, label_visibility="collapsed"
            )
        with c2:
            trimestre_sel = st.radio(
                "Período:",
                [
                    "Ano Completo",
                    "1º Trimestre",
                    "2º Trimestre",
                    "3º Trimestre",
                    "4º Trimestre",
                ],
                horizontal=True,
                label_visibility="collapsed",
            )

    df_filtrado = df[df["data_resposta"].dt.year == ano_sel].copy()
    if "1º" in trimestre_sel:
        df_filtrado = df_filtrado[df_filtrado["data_resposta"].dt.month.isin([1, 2, 3])]
    elif "2º" in trimestre_sel:
        df_filtrado = df_filtrado[df_filtrado["data_resposta"].dt.month.isin([4, 5, 6])]
    elif "3º" in trimestre_sel:
        df_filtrado = df_filtrado[df_filtrado["data_resposta"].dt.month.isin([7, 8, 9])]
    elif "4º" in trimestre_sel:
        df_filtrado = df_filtrado[
            df_filtrado["data_resposta"].dt.month.isin([10, 11, 12])
        ]

    if df_filtrado.empty:
        st.warning(
            f"⚠️ Nenhuma pesquisa foi submetida no período selecionado ({trimestre_sel} de {ano_sel})."
        )
        return

    # 🧠 CLASSIFICAÇÃO DE SENTIMENTOS
    def classificar_sentimento(texto):
        t = str(texto).upper()
        if any(
            x in t
            for x in ["😄", "NOTA 10", "ÓTIMO", "EXCELENTE", "PASSOU", "TRANSFORMOU"]
        ):
            return "Positivo (Excelente)"
        if any(x in t for x in ["😐", "BOM", "BONS", "MENOS", "POUCO", "AJUDOU"]):
            return "Neutro (Mediano)"
        if any(x in t for x in ["😞", "MELHORAR", "SINTO", "NOTEI", "ENERGIA"]):
            return "Atenção (Melhoria)"
        return "Sem Classificação"

    df_filtrado["Sentimento_Q1"] = df_filtrado.get(
        "q1_disposicao", pd.Series(["Sem Classificação"] * len(df_filtrado))
    ).apply(classificar_sentimento)
    df_filtrado["Sentimento_Q2"] = df_filtrado.get(
        "q2_dores", pd.Series(["Sem Classificação"] * len(df_filtrado))
    ).apply(classificar_sentimento)
    df_filtrado["Sentimento_Q3"] = df_filtrado.get(
        "q3_efeito_vida", pd.Series(["Sem Classificação"] * len(df_filtrado))
    ).apply(classificar_sentimento)
    df_filtrado["Sentimento_Q4"] = df_filtrado.get(
        "q4_avaliacao_geral", pd.Series(["Sem Classificação"] * len(df_filtrado))
    ).apply(classificar_sentimento)

    # 🚀 OS 5 KPIs
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{len(df_filtrado)}</div><div class='metric-label'>Pesquisas</div></div>",
            unsafe_allow_html=True,
        )
    with m2:
        pos_q4 = (df_filtrado["Sentimento_Q4"] == "Positivo (Excelente)").sum()
        tx_exc = int((pos_q4 / len(df_filtrado)) * 100) if len(df_filtrado) > 0 else 0
        st.markdown(
            f"<div class='metric-card'><div class='metric-value' style='color: #10B981;'>{tx_exc}%</div><div class='metric-label'>Excelência (Aulas)</div></div>",
            unsafe_allow_html=True,
        )
    with m3:
        pos_q2 = (df_filtrado["Sentimento_Q2"] == "Positivo (Excelente)").sum()
        tx_dor = int((pos_q2 / len(df_filtrado)) * 100) if len(df_filtrado) > 0 else 0
        st.markdown(
            f"<div class='metric-card'><div class='metric-value' style='color: #0056b3;'>{tx_dor}%</div><div class='metric-label'>Alívio de Dores</div></div>",
            unsafe_allow_html=True,
        )
    with m4:
        pos_q1 = (df_filtrado["Sentimento_Q1"] == "Positivo (Excelente)").sum()
        tx_ene = int((pos_q1 / len(df_filtrado)) * 100) if len(df_filtrado) > 0 else 0
        st.markdown(
            f"<div class='metric-card'><div class='metric-value' style='color: #F59E0B;'>{tx_ene}%</div><div class='metric-label'>Mais Energia</div></div>",
            unsafe_allow_html=True,
        )
    with m5:
        pos_q3 = (df_filtrado["Sentimento_Q3"] == "Positivo (Excelente)").sum()
        tx_imp = int((pos_q3 / len(df_filtrado)) * 100) if len(df_filtrado) > 0 else 0
        st.markdown(
            f"<div class='metric-card'><div class='metric-value' style='color: #8B5CF6;'>{tx_imp}%</div><div class='metric-label'>Impacto na Vida</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # 🖨️ EXPORTAÇÃO OFICIAL — PDF + WORD NATIVO
    # =========================================================================
    st.markdown(
        "<h5 style='color: #0A2540; font-weight: 800; font-size: 14px;'>🖨️ Emitir Prestação de Contas Oficial</h5>",
        unsafe_allow_html=True,
    )

    col_pdf, col_word = st.columns(2)

    with col_pdf:
        if not _XHTML_SAT:
            st.error("⚠️ xhtml2pdf não disponível.")
        else:
            pdf_bytes = gerar_pdf_satisfacao_bytes(
                df_filtrado, trimestre_sel, ano_sel, tx_exc, tx_dor, tx_ene, tx_imp
            )
            if pdf_bytes:
                st.download_button(
                    label="📕 BAIXAR RELATÓRIO (PDF Oficial)",
                    data=pdf_bytes,
                    file_name=f"Relatorio_Satisfacao_{trimestre_sel}_{ano_sel}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
            else:
                st.error("Erro ao gerar PDF.")

    with col_word:
        if not _DOCX_SAT:
            st.error("⚠️ python-docx não disponível.")
        else:
            docx_bytes = gerar_docx_satisfacao_bytes(
                df_filtrado, trimestre_sel, ano_sel, tx_exc, tx_dor, tx_ene, tx_imp
            )
            if docx_bytes:
                st.download_button(
                    label="📘 BAIXAR RELATÓRIO (Word Nativo .docx)",
                    data=docx_bytes,
                    file_name=f"Relatorio_Satisfacao_{trimestre_sel}_{ano_sel}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True,
                )
            else:
                st.error("Erro ao gerar Word.")

    st.markdown(
        "<hr style='border-top: 1px solid #E2E8F0; margin: 20px 0;'>",
        unsafe_allow_html=True,
    )

    # 📊 MATRIZ DOS GRÁFICOS
    mapa_cores = {
        "Positivo (Excelente)": "#10B981",
        "Neutro (Mediano)": "#F59E0B",
        "Atenção (Melhoria)": "#EF4444",
        "Sem Classificação": "#94A3B8",
    }

    def render_pie_chart(dataframe, coluna, titulo):
        st.markdown(
            f"<h6 style='text-align: center; color: #0A2540; font-weight: 800; margin-top: 15px;'>{titulo}</h6>",
            unsafe_allow_html=True,
        )
        contagem = dataframe[coluna].value_counts().reset_index()
        contagem.columns = ["Sentimento", "Votos"]
        contagem = contagem[contagem["Sentimento"] != "Sem Classificação"]
        if contagem.empty:
            return st.info("Sem dados.")
        fig = px.pie(
            contagem,
            values="Votos",
            names="Sentimento",
            hole=0.55,
            color="Sentimento",
            color_discrete_map=mapa_cores,
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont_size=12,
            textfont_weight="bold",
        )
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    r1c1, r1c2 = st.columns(2)
    with r1c1:
        render_pie_chart(
            df_filtrado, "Sentimento_Q4", "1. Qualidade dos Encontros (Professores)"
        )
    with r1c2:
        render_pie_chart(
            df_filtrado, "Sentimento_Q3", "2. Impacto na Qualidade de Vida (Saúde)"
        )

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        render_pie_chart(
            df_filtrado, "Sentimento_Q1", "3. Disposição no Dia a Dia (Energia)"
        )
    with r2c2:
        render_pie_chart(df_filtrado, "Sentimento_Q2", "4. Melhora nas Dores Crônicas")
