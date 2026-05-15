# ==============================================================================
# 📄 Arquivo: views/relatorio_view.py
# 🏷️ VERSÃO: 8.40 PRIMEMAX (A MURALHA - PDF Nativo, Excel e Sincronização Anti-Furo)
# 📏 LINHAS: ~900
# 👤 DESENVOLVEDOR: Parceiro de Programação Gemini & Marcos Barbosa
# ⚙️ FUNÇÃO: Relatórios, B.I., Auditoria Interativa (PDF) e Prestação Pedagógica
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io
import os
from views.relatorio_identificacao_view import renderizar_aba_caracracha

from database import (
    get_relatorio_periodo,
    buscar_alunos_geral,
    get_todas_turmas,
    get_alunos_por_turma,
    get_diarios_periodo,
    get_avaliacoes_aluno,
    get_midias_diario,
)

# 🚀 IMPORTAÇÃO DO MOTOR NATIVO DO WORD
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL

    DOCX_DISPONIVEL = True
except ImportError:
    DOCX_DISPONIVEL = False

# 🚀 IMPORTAÇÃO DO MOTOR NATIVO DE PDF
try:
    from xhtml2pdf import pisa

    XHTML_DISPONIVEL = True
except ImportError:
    XHTML_DISPONIVEL = False


# --- FUNÇÕES DE APOIO E IDENTIDADE ---
from utils.imagem import get_base64_image


def abrir_ficha_aluno(dados_aluno):
    """Callback executado apenas quando o botão 'Abrir Ficha' é clicado."""
    st.session_state.aluno_prontuario = dados_aluno
    st.session_state.menu_atual = "Portal do Aluno"


# ==============================================================================
# 📊 MOTOR EXCEL: PLANILHA, KPI, B.I. E RODAPÉ PADRÃO MOVERIGHT™
# ==============================================================================
def gerar_excel_planilha_frequencia(
    df_grid,
    turma_nome,
    periodo_str,
    caminho_logo_muda,
    caminho_logo_sec,
    total_alunos,
    total_presencas_geral,
    total_aulas,
):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_grid.to_excel(
            writer, sheet_name="Prestação de Contas", startrow=12, index=False
        )
        workbook = writer.book
        worksheet = writer.sheets["Prestação de Contas"]

        # --- ESTILOS ---
        f_tit = workbook.add_format(
            {"bold": True, "font_size": 13, "align": "left", "valign": "vcenter"}
        )
        f_sub = workbook.add_format(
            {
                "font_size": 10,
                "align": "left",
                "valign": "vcenter",
                "font_color": "#555555",
            }
        )
        f_dst = workbook.add_format(
            {
                "bold": True,
                "font_size": 10,
                "align": "left",
                "valign": "vcenter",
                "font_color": "#0056b3",
            }
        )
        f_cab_c = workbook.add_format(
            {
                "bold": True,
                "bottom": 1,
                "bg_color": "#F8FAFC",
                "align": "center",
                "valign": "vcenter",
            }
        )
        f_cab_e = workbook.add_format(
            {
                "bold": True,
                "bottom": 1,
                "bg_color": "#F8FAFC",
                "align": "left",
                "valign": "vcenter",
            }
        )
        f_dat_c = workbook.add_format({"align": "center", "valign": "vcenter"})
        f_tot_c = workbook.add_format(
            {
                "bold": True,
                "bottom": 2,
                "bg_color": "#E2E8F0",
                "align": "center",
                "valign": "vcenter",
            }
        )
        f_tot_e = workbook.add_format(
            {
                "bold": True,
                "bottom": 2,
                "bg_color": "#E2E8F0",
                "align": "left",
                "valign": "vcenter",
            }
        )
        f_rodape = workbook.add_format(
            {"font_size": 8, "font_color": "#64748B", "align": "left"}
        )
        f_rodape_bold = workbook.add_format(
            {"font_size": 8, "font_color": "#0A2540", "bold": True, "align": "left"}
        )

        from utils.identidade import (
            get_config as _gcfg_xls,
            get_logo_data_url as _gld_xls,
        )

        _xcfg = _gcfg_xls()
        import os as _os_xls

        _lp = _xcfg.get("logo_principal", "logo-imbra.png")
        _ls = _xcfg.get("logo_secundaria", "logo-secretaria.png")
        try:
            if _os_xls.path.exists(_lp):
                worksheet.insert_image("A1", _lp, {"x_scale": 0.16, "y_scale": 0.16})
        except:
            pass
        try:
            if _os_xls.path.exists(_ls):
                worksheet.insert_image("C1", _ls, {"x_scale": 0.35, "y_scale": 0.35})
        except:
            pass

        worksheet.merge_range(
            "A6:E6",
            f"{_xcfg.get('titulo_projeto', 'PROJETO ESPORTE E SAÚDE NA COMUNIDADE')} - PLANILHA DE FREQUÊNCIA",
            f_tit,
        )
        worksheet.merge_range("A7:E7", f"Período: {periodo_str}", f_sub)
        worksheet.merge_range("A8:E8", f"Escopo: {turma_nome}", f_sub)
        worksheet.merge_range(
            "A9:E9", f"Total de Aulas Realizadas no Período: {total_aulas}", f_dst
        )
        worksheet.merge_range(
            "A10:E10", f"Total de Presenças no Período: {total_presencas_geral}", f_dst
        )
        worksheet.merge_range(
            "A11:E11", f"Total de Alunos no Período: {total_alunos}", f_dst
        )

        for col_num, value in enumerate(df_grid.columns.values):
            fmt = f_cab_e if value in ["Aluno", "Turma"] else f_cab_c
            worksheet.write(12, col_num, value, fmt)
            val_topo = df_grid.iloc[0, col_num]
            fmt_t = f_tot_e if value in ["Aluno", "Turma"] else f_tot_c
            worksheet.write(13, col_num, val_topo, fmt_t)

            for row_num in range(1, len(df_grid)):
                val = df_grid.iloc[row_num, col_num]
                if value in ["Aluno", "Turma"]:
                    worksheet.write(13 + row_num, col_num, val)
                else:
                    worksheet.write(13 + row_num, col_num, val, f_dat_c)

        worksheet.set_column(0, 0, 8)
        worksheet.set_column(1, 1, 35)
        worksheet.set_column(2, 2, 18)
        if len(df_grid.columns) > 3:
            worksheet.set_column(3, len(df_grid.columns) - 1, 7.5)

        linha_rodape = 13 + len(df_grid) + 2
        worksheet.write(
            linha_rodape,
            0,
            "Sistema Esporte e Saúde - Gestão Inteligente Moveright™",
            f_rodape_bold,
        )
        worksheet.write(
            linha_rodape + 1,
            0,
            f"{_xcfg.get('nome_organizacao', 'Instituto Muda Brasil')} | CNPJ: {_xcfg.get('cnpj', '08.817.519/0001-79')}",
            f_rodape,
        )
        worksheet.write(
            linha_rodape + 2,
            0,
            f"Site: {_xcfg.get('site', 'imbra.org.br')} | Instagram: {_xcfg.get('instagram', '@institutomudabrasil')}",
            f_rodape,
        )
        worksheet.write(
            linha_rodape + 3, 0, f"Endereço: {_xcfg.get('endereco', '')}", f_rodape
        )
        if _xcfg.get("telefone"):
            worksheet.write(linha_rodape + 4, 0, f"Tel: {_xcfg['telefone']}", f_rodape)

        # ======================================================================
        # ABA B.I.: DASHBOARD MILIMÉTRICO
        # ======================================================================
        ws_bi = workbook.add_worksheet("Dashboard B.I.")
        df_al = df_grid.iloc[1:]
        tp = df_al["Total P"].sum() if "Total P" in df_al.columns else 0
        tf = df_al["Total F"].sum() if "Total F" in df_al.columns else 0
        r_cnt = len(df_al[df_al.get("Total F", 0) > df_al.get("Total P", 0)])

        ws_bi.write("A1", "Métrica", f_cab_e)
        ws_bi.write("B1", "Quantidade", f_cab_c)
        ws_bi.write("A2", "Presenças")
        ws_bi.write("B2", tp, f_dat_c)
        ws_bi.write("A3", "Faltas")
        ws_bi.write("B3", tf, f_dat_c)
        ws_bi.write("A5", "Regulares")
        ws_bi.write("B5", total_alunos - r_cnt, f_dat_c)
        ws_bi.write("A6", "Em Risco")
        ws_bi.write("B6", r_cnt, f_dat_c)

        taxa = tp / (tp + tf) if (tp + tf) > 0 else 0
        fmt_st = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "bg_color": "#D1FAE5" if taxa >= 0.65 else "#FEE2E2",
            }
        )
        ws_bi.merge_range(
            "A9:B9",
            f"{'🟢 SAUDÁVEL' if taxa >= 0.65 else '🔴 ALERTA'} ({taxa:.1%})",
            fmt_st,
        )

        dias_bi = [
            c
            for c in df_grid.columns
            if c
            not in [
                "Ordem",
                "Aluno",
                "Turma",
                "Total P",
                "Total F",
                "Total J",
                "% Presença",
            ]
        ]
        ws_bi.write(10, 0, "Data Aula", f_cab_e)
        ws_bi.write(10, 1, "Presentes", f_cab_c)
        for i, d in enumerate(dias_bi):
            ws_bi.write(11 + i, 0, d)
            ws_bi.write(11 + i, 1, df_grid.iloc[0][d], f_dat_c)

        c1 = workbook.add_chart({"type": "pie"})
        c1.add_series(
            {
                "categories": ["Dashboard B.I.", 1, 0, 2, 0],
                "values": ["Dashboard B.I.", 1, 1, 2, 1],
                "points": [
                    {"fill": {"color": "#10B981"}},
                    {"fill": {"color": "#EF4444"}},
                ],
            }
        )
        c1.set_title({"name": "Assiduidade Global"})
        ws_bi.insert_chart("D1", c1, {"x_scale": 0.6, "y_scale": 0.6})

        c2 = workbook.add_chart({"type": "pie"})
        c2.add_series(
            {
                "categories": ["Dashboard B.I.", 4, 0, 5, 0],
                "values": ["Dashboard B.I.", 4, 1, 5, 1],
                "points": [
                    {"fill": {"color": "#3B82F6"}},
                    {"fill": {"color": "#F59E0B"}},
                ],
            }
        )
        c2.set_title({"name": "Raio-X Turma"})
        ws_bi.insert_chart("H1", c2, {"x_scale": 0.6, "y_scale": 0.6})

        if dias_bi:
            c3 = workbook.add_chart({"type": "line"})
            c3.add_series(
                {
                    "categories": ["Dashboard B.I.", 11, 0, 11 + len(dias_bi) - 1, 0],
                    "values": ["Dashboard B.I.", 11, 1, 11 + len(dias_bi) - 1, 1],
                    "marker": {"type": "circle"},
                    "trendline": {
                        "type": "linear",
                        "line": {"color": "#EF4444", "dash_type": "long_dash"},
                    },
                    "data_labels": {"value": True},
                }
            )
            c3.set_title({"name": "Curva Diária de Frequência (Evolução)"})
            ws_bi.insert_chart("C13", c3, {"x_scale": 1.6, "y_scale": 1.1})

        ws_bi.set_column(0, 0, 25)
    return output.getvalue()


# ==============================================================================
# 🖨️ MOTOR PDF NATIVO: AUDITORIA OFICIAL (NADA DE HTML)
# ==============================================================================
def gerar_pdf_auditoria_core(falhas, contagem_falhas, turma_aud):
    """Gera um PDF nativo e robusto usando xhtml2pdf."""
    if not XHTML_DISPONIVEL:
        return None

    # Base64 para as imagens não quebrarem no PDF
    from utils.identidade import get_config as _gcfg_pdf, get_logo_data_url as _gld_pdf

    _pcfg = _gcfg_pdf()
    logo_imbra = _gld_pdf(_pcfg.get("logo_principal", "logo-imbra.png"))
    logo_sec = _gld_pdf(_pcfg.get("logo_secundaria", "logo-secretaria.png"))

    html_logo_imbra = (
        f'<img src="{logo_imbra}" style="width: 100px; height: auto;">'
        if logo_imbra
        else "<b>IMBRA</b>"
    )
    html_logo_sec = (
        f'<img src="{logo_sec}" style="width: 140px; height: auto;">'
        if logo_sec
        else "<b>SECRETARIA SP</b>"
    )

    data_hoje = datetime.date.today().strftime("%d/%m/%Y")

    html_metrics = "".join(
        [
            f"<li><b>{k}:</b> {v} registro(s) pendente(s)</li>"
            for k, v in contagem_falhas.items()
            if v > 0
        ]
    )
    html_linhas = "".join(
        [
            f"<tr><td>{f['Aluno']}</td><td>{f['Turma']}</td><td>{f['Pendências']}</td></tr>"
            for f in falhas
        ]
    )

    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 portrait; margin: 1.2cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; color: #1E293B; font-size: 11px; line-height: 1.4; }}
            h1 {{ color: #0F172A; font-size: 18px; margin-bottom: 5px; text-align: center; }}
            h2 {{ color: #1D4ED8; font-size: 14px; text-align: center; margin-top: 0; }}
            h3 {{ color: #0F172A; font-size: 13px; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 5px; margin-top: 20px; }}
            .tb-header {{ width: 100%; border: none; margin-bottom: 20px; }}
            .tb-header td {{ border: none; padding: 0; }}
            .resumo-box {{ background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; margin-bottom: 20px; border-radius: 5px; }}
            .resumo-box ul {{ margin: 0; padding-left: 20px; }}
            table.tabela-dados {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            table.tabela-dados th, table.tabela-dados td {{ border: 1px solid #CBD5E1; padding: 8px; text-align: left; }}
            table.tabela-dados th {{ background-color: #0F172A; color: #FFFFFF; font-weight: bold; font-size: 12px; }}
            .footer {{ text-align: center; font-size: 9px; color: #64748B; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <table class="tb-header">
            <tr>
                <td style="width: 25%; text-align: left; vertical-align: middle;">{html_logo_sec}</td>
                <td style="width: 50%; text-align: center; vertical-align: middle;">
                    <h1>{_pcfg.get("nome_organizacao", "INSTITUTO MUDA BRASIL").upper()}</h1>
                    <h2>{_pcfg.get("titulo_projeto", "PROJETO ESPORTE E SAÚDE NA COMUNIDADE")}</h2>
                </td>
                <td style="width: 25%; text-align: right; vertical-align: middle;">{html_logo_imbra}</td>
            </tr>
        </table>

        <h3>Relatório Oficial de Auditoria de Cadastros e Documentos</h3>
        <p><strong>Data da Emissão:</strong> {data_hoje} &nbsp;|&nbsp; <strong>Escopo Filtrado:</strong> {turma_aud}</p>

        <div class="resumo-box">
            <strong>Resumo Global de Totalizadores de Irregularidades:</strong><br>
            <ul>{html_metrics}</ul>
        </div>

        <table class="tabela-dados">
            <tr>
                <th style="width: 35%;">Nome do Aluno</th>
                <th style="width: 20%;">Turma de Origem</th>
                <th style="width: 45%;">Pendências Identificadas (Ação Necessária)</th>
            </tr>
            {html_linhas}
        </table>

        <div class="footer">Sistema Esporte e Saúde - Gestão Inteligente Moveright™ - Documento Oficial de Auditoria</div>
    </body>
    </html>
    """

    result = io.BytesIO()
    pisa.pisaDocument(io.StringIO(html_content), result)
    return result.getvalue()


# ==============================================================================
# 🏆 MOTOR WORD NATIVO: PRESTAÇÃO PEDAGÓGICA (PYTHON-DOCX)
# ==============================================================================
def gerar_word_prestacao_contas(
    turma, mes_nome, ano, engajamento, diarios, clinico, is_global=False
):
    if not DOCX_DISPONIVEL:
        return None
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # CABEÇALHO COM LOGOS LOCAIS
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(1.6)
    table.columns[1].width = Inches(3.4)
    table.columns[2].width = Inches(1.2)

    c_sec, c_txt, c_imb = table.rows[0].cells
    c_sec.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    c_txt.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    c_imb.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    p_sec = c_sec.paragraphs[0]
    p_sec.alignment = WD_ALIGN_PARAGRAPH.LEFT
    from utils.identidade import get_config as _gcfg_word

    _wcfg = _gcfg_word()
    _wlogo_s = _wcfg.get("logo_secundaria", "logo-secretaria.png")
    _wlogo_p = _wcfg.get("logo_principal", "logo-imbra.png")
    if os.path.exists(_wlogo_s):
        p_sec.add_run().add_picture(_wlogo_s, width=Inches(1.6))

    p_txt = c_txt.paragraphs[0]
    p_txt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t1 = p_txt.add_run(
        f"{_wcfg.get('nome_organizacao', 'INSTITUTO MUDA BRASIL').upper()}\n"
    )
    run_t1.bold = True
    run_t1.font.size = Pt(14)
    run_t1.font.color.rgb = RGBColor(10, 37, 64)
    run_t2 = p_txt.add_run(
        f"PROJETO: {_wcfg.get('titulo_projeto', 'ESPORTE E SAÚDE NA COMUNIDADE - FASE 2')}"
    )
    run_t2.bold = True
    run_t2.font.size = Pt(10)
    run_t2.font.color.rgb = RGBColor(100, 116, 139)

    p_imb = c_imb.paragraphs[0]
    p_imb.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if os.path.exists(_wlogo_p):
        p_imb.add_run().add_picture(_wlogo_p, width=Inches(1.2))

    doc.add_paragraph("_" * 68).alignment = WD_ALIGN_PARAGRAPH.CENTER

    # TÍTULO E ESCOPO
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.space_before = Pt(12)
    rt = p_title.add_run("RELATÓRIO MENSAL DE ATIVIDADES CLÍNICAS E PEDAGÓGICAS\n")
    rt.bold = True
    rt.font.size = Pt(13)
    rt.font.color.rgb = RGBColor(10, 37, 64)

    escopo = "Todas as Turmas do Polo" if is_global else turma
    rsub = p_title.add_run(
        f"Mês de Referência: {mes_nome.upper()} / {ano}  |  Escopo: {escopo}"
    )
    rsub.font.size = Pt(10)
    rsub.font.color.rgb = RGBColor(100, 116, 139)

    # ENGAJAMENTO
    p_e = doc.add_paragraph()
    p_e.space_before = Pt(15)
    re = p_e.add_run("1. MÉTRICAS DE ENGAJAMENTO")
    re.bold = True
    re.font.size = Pt(12)
    re.font.color.rgb = RGBColor(10, 37, 64)

    t_eng = doc.add_table(rows=2, cols=3)
    t_eng.style = "Table Grid"
    t_eng.alignment = WD_TABLE_ALIGNMENT.CENTER
    h1, h2, h3 = t_eng.rows[0].cells
    h1.text, h2.text, h3.text = "Alunos Ativos", "Aulas Lecionadas", "Assiduidade Média"
    v1, v2, v3 = t_eng.rows[1].cells
    v1.text = str(engajamento["total_alunos"])
    v2.text = str(engajamento["total_aulas"])
    v3.text = f"{engajamento['assiduidade']:.1f}%"
    for row in t_eng.rows:
        for cell in row.cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # DIÁRIO DE BORDO
    p_d = doc.add_paragraph()
    p_d.space_before = Pt(15)
    rd = p_d.add_run("2. RESUMO PEDAGÓGICO (Diário de Bordo)")
    rd.bold = True
    rd.font.size = Pt(12)
    rd.font.color.rgb = RGBColor(10, 37, 64)

    if diarios:
        for d in diarios[:20]:
            try:
                dt_obj = pd.to_datetime(str(d["data_aula"])).date()
                data_fmt = dt_obj.strftime("%d/%m/%Y")
            except:
                data_fmt = str(d["data_aula"])
            prefixo_turma = f"[{d.get('turma', '')[:5]}] " if is_global else ""
            p_aula = doc.add_paragraph()
            p_aula.style = "List Bullet"
            r_bold = p_aula.add_run(f"Aula de {data_fmt} {prefixo_turma}: ")
            r_bold.bold = True
            p_aula.add_run(f"{d.get('objetivo_geral', 'Sem objetivo definido.')}")
    else:
        doc.add_paragraph(
            "Nenhum registo de aula preenchido no sistema durante este período."
        )

    # BIOINDICADORES
    p_c = doc.add_paragraph()
    p_c.space_before = Pt(15)
    rc = p_c.add_run("3. IMPACTO CLÍNICO E SAÚDE")
    rc.bold = True
    rc.font.size = Pt(12)
    rc.font.color.rgb = RGBColor(10, 37, 64)

    doc.add_paragraph(
        f"Durante o mês de {mes_nome}, foram realizadas reavaliações clínicas. Com base nos dados consolidados, a média geral foi:"
    )
    b1 = doc.add_paragraph(style="List Bullet")
    b1.add_run("Esforço Médio Global (Borg): ")
    b1.add_run(f"{clinico['borg']}").bold = True
    b2 = doc.add_paragraph(style="List Bullet")
    b2.add_run("Nível de Dor Médio Reportado: ")
    b2.add_run(f"{clinico['dor']:.1f} / 10").bold = True
    b3 = doc.add_paragraph(style="List Bullet")
    b3.add_run("Padrão de Saúde Intestinal (Bristol): ")
    b3.add_run(f"{clinico['bristol']}").bold = True
    b4 = doc.add_paragraph(style="List Bullet")
    b4.add_run("Nível de Hidratação (Urina): ")
    b4.add_run(f"{clinico['urina']}").bold = True

    # ASSINATURA OFICIAL CORRIGIDA
    doc.add_paragraph("\n")
    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs1 = p_sig.add_run("SISTEMA\nESPORTE E SAÚDE\n\n")
    rs1.bold = True
    rs1.font.size = Pt(11)
    rs1.font.color.rgb = RGBColor(10, 37, 64)
    rs2 = p_sig.add_run("Coordenador")
    rs2.font.size = Pt(10)
    rs2.font.color.rgb = RGBColor(10, 37, 64)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ==============================================================================
# RENDERIZAÇÃO DA INTERFACE PRINCIPAL (ST)
# ==============================================================================
def tela_relatorio():
    st.markdown(
        "<div style='background:linear-gradient(135deg,#F8FAFC,#E0F2FE);padding:25px;border-radius:12px;border-left:6px solid #1E88E5;'><h2>📄 Central de Relatórios e Auditoria</h2><p>Planilhas de Frequência, B.I. Analítico e Prestação de Contas Oficial.</p></div>",
        unsafe_allow_html=True,
    )

    tab_f, tab_id, tab_a, tab_w = st.tabs(
        [
            "📊 Planilha de Frequência",
            "🪪 Relatório Cara-Crachá",
            "🔎 Auditoria de Cadastros",
            "🏆 Prestação de Conta Pedagógica",
        ]
    )

    # ==============================================================================
    # --- ABA 1: FREQUÊNCIA (MOTOR ANTI-FURO IMPLEMENTADO) ---
    # ==============================================================================
    with tab_f:
        c1, c2, c3 = st.columns([1, 1, 2], vertical_alignment="bottom")
        d_i = c1.date_input(
            "Data de Início", datetime.date.today().replace(day=1), format="DD/MM/YYYY"
        )
        d_f = c2.date_input("Data de Fim", datetime.date.today(), format="DD/MM/YYYY")

        turmas = get_todas_turmas(ativas_apenas=True)
        t_sel = c3.selectbox(
            "Filtrar Turma",
            ["Todas as Turmas"] + turmas["nome"].tolist()
            if not turmas.empty
            else ["Todas as Turmas"],
        )

        if st.button(
            "🔍 Processar Dados de Prestação de Contas",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner(
                "Analisando tendências, cruzando diários e resolvendo lacunas (Anti-Furo)..."
            ):
                # O motor inteligente do database.py agora faz o trabalho sujo!
                df_matriz = get_relatorio_periodo(
                    d_i, d_f, "" if t_sel == "Todas as Turmas" else t_sel
                )

                if df_matriz.empty:
                    st.warning(
                        "⚠️ Não foram encontradas aulas no Diário para este período."
                    )
                    return

                # Renomear colunas para manter a compatibilidade com a exportação Excel
                if "Nome" in df_matriz.columns:
                    df_matriz.rename(columns={"Nome": "Aluno"}, inplace=True)

                # Inserir a coluna "Ordem"
                df_matriz.insert(0, "Ordem", range(1, 1 + len(df_matriz)))

                # Encontrar quais são as colunas de data reais
                cols_data_reais = [
                    c
                    for c in df_matriz.columns
                    if c
                    not in [
                        "Ordem",
                        "Aluno",
                        "Turma",
                        "Total P",
                        "Total F",
                        "Total J",
                        "% Presença",
                    ]
                ]
                n_aulas = len(cols_data_reais)

                # Variáveis Globais de Soma
                tp_geral = int(df_matriz["Total P"].sum())
                tf_geral = int(df_matriz["Total F"].sum())
                tj_geral = int(df_matriz.get("Total J", pd.Series(dtype=int)).sum())

                # Criar a linha de Totalizador no final
                tot_d = {
                    "Ordem": "-",
                    "Aluno": "TOTAL DE PRESENÇAS DIÁRIAS",
                    "Turma": "-",
                }

                for c in df_matriz.columns:
                    if c not in tot_d:
                        if c in cols_data_reais:
                            tot_d[c] = (df_matriz[c] == "P").sum()
                        elif c == "Total P":
                            tot_d[c] = tp_geral
                        elif c == "Total F":
                            tot_d[c] = tf_geral
                        elif c == "Total J":
                            tot_d[c] = tj_geral
                        else:
                            tot_d[c] = "-"

                df_final = pd.concat(
                    [pd.DataFrame([tot_d]), df_matriz], ignore_index=True
                )
                periodo_formatado = (
                    f"{d_i.strftime('%d/%m/%Y')} a {d_f.strftime('%d/%m/%Y')}"
                )

                # Gerar arquivo Excel seguro
                excel = gerar_excel_planilha_frequencia(
                    df_final,
                    t_sel,
                    periodo_formatado,
                    "logo-imbra.png",
                    "logo-secretaria.png",
                    len(df_matriz),
                    tp_geral,
                    n_aulas,
                )

                st.success(
                    f"✅ Sucesso! {n_aulas} aulas úteis cruzadas de {periodo_formatado}."
                )

                st.download_button(
                    "📥 BAIXAR PLANILHA DE FREQUÊNCIA (EXCEL)",
                    excel,
                    f"Relatorio_AntiFuro_{t_sel}_{d_i.strftime('%d_%m_%Y')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                )

                # --- RENDERIZAÇÃO VISUAL: DASHBOARD E TABELA ---
                st.markdown("### 📊 Dashboard Analítico")
                ck1, ck2, ck3 = st.columns(3)
                ck1.metric("Aulas Realizadas", n_aulas)
                ck2.metric("Total Presenças", tp_geral)
                ck3.metric("Total Faltas / Justif.", f"{tf_geral} / {tj_geral}")

                cg1, cg2 = st.columns(2)
                cg1.plotly_chart(
                    px.pie(
                        names=["Presenças", "Faltas", "Justificadas"],
                        values=[tp_geral, tf_geral, tj_geral],
                        title="Assiduidade Global",
                        color_discrete_sequence=["#10B981", "#EF4444", "#F59E0B"],
                    ),
                    use_container_width=True,
                )

                r_st = len(df_matriz[df_matriz["Total F"] > df_matriz["Total P"]])
                cg2.plotly_chart(
                    px.pie(
                        names=["Regulares", "Em Risco"],
                        values=[len(df_matriz) - r_st, r_st],
                        title="Saúde da Turma",
                        color_discrete_sequence=["#3B82F6", "#F59E0B"],
                    ),
                    use_container_width=True,
                )

                st.markdown("#### 📅 Planilha de Frequência Detalhada")

                # Colorir os P, F e J visualmente no Streamlit
                def colorir_status(val):
                    if val == "P":
                        return "color: #10B981; font-weight: bold; background-color: #D1FAE5;"
                    if val == "F":
                        return "color: #EF4444; font-weight: bold; background-color: #FEE2E2;"
                    if val == "J":
                        return "color: #F59E0B; font-weight: bold; background-color: #FEF3C7;"
                    return ""

                df_st = df_final.style.applymap(colorir_status).set_properties(
                    subset=[c for c in df_final.columns if c not in ["Aluno", "Turma"]],
                    **{"text-align": "center"},
                )
                st.dataframe(df_st, use_container_width=True, hide_index=True)
    # ==============================================================================
    # --- ABA 1.5: RELATÓRIO CARA-CRACHÁ ---
    # ==============================================================================
    with tab_id:
        renderizar_aba_caracracha()

    # ==============================================================================
    # --- ABA 2: AUDITORIA COM PDF NATIVO E GRID INTERATIVO ---
    # ==============================================================================
    with tab_a:
        st.markdown("### 🔎 Auditoria de Cadastros e Documentos")
        st.write(
            "Identifique pendências documentais e clique no botão para acessar e corrigir a ficha do aluno instantaneamente."
        )

        df_aud = buscar_alunos_geral("")
        if not df_aud.empty:
            with st.container(border=True):
                c_aud1, _ = st.columns(2)
                turma_aud = c_aud1.selectbox(
                    "Turma para Auditoria",
                    ["Todas"]
                    + sorted(
                        [
                            t
                            for t in df_aud["turma"].unique().tolist()
                            if isinstance(t, str)
                        ]
                    ),
                )
                if turma_aud != "Todas":
                    df_aud = df_aud[df_aud["turma"] == turma_aud]

            if st.button(
                "🚀 INICIAR VERIFICAÇÃO DE INTEGRIDADE", use_container_width=True
            ):
                checks = {
                    "url_foto": "📸 Foto",
                    "url_documento": "🪪 Documento Oficial",
                    "cpf": "🆔 CPF",
                    "rg": "📄 RG",
                    "data_nascimento": "🎂 Nasc.",
                    "url_atestado": "⚕️ Atestado Médico",
                }
                falhas = []
                contagem_falhas = {label: 0 for label in checks.values()}

                for _, r in df_aud.iterrows():
                    missing = []
                    for col, label in checks.items():
                        if (
                            pd.isna(r.get(col))
                            or str(r.get(col)).strip() == ""
                            or str(r.get(col)).strip().upper() == "NÃO INFORMADO"
                        ):
                            missing.append(label)
                            contagem_falhas[label] += 1
                    if missing:
                        falhas.append(
                            {
                                "Aluno": r["nome"],
                                "Turma": r["turma"],
                                "Pendências": ", ".join(missing),
                                "id_aluno": str(r.get("id", "")).split(".")[0],
                                "dict_aluno": r.to_dict(),
                            }
                        )

                if falhas:
                    st.error(
                        f"⚠️ Identificadas irregularidades em {len(falhas)} alunos da turma {turma_aud}."
                    )
                    st.markdown("#### 📊 Totalizadores de Pendências")
                    cols_metric = st.columns(len(checks))
                    for idx, (label, count) in enumerate(contagem_falhas.items()):
                        cols_metric[idx].metric(label.split(" ", 1)[-1], count)

                    # 🚀 REPOSICIONAMENTO E EXPORTAÇÃO PARA PDF REAL
                    st.markdown("#### 🖨️ Opções de Exportação Oficial")
                    c_dw1, c_dw2 = st.columns(2)

                    # Exportação Excel
                    df_export = pd.DataFrame(falhas)[["Aluno", "Turma", "Pendências"]]
                    output_aud = io.BytesIO()
                    with pd.ExcelWriter(output_aud, engine="xlsxwriter") as writer:
                        pd.DataFrame(
                            list(contagem_falhas.items()),
                            columns=["Documento/Campo", "Quantidade em Falta"],
                        ).to_excel(writer, index=False, sheet_name="Resumo_Auditoria")
                        writer.sheets["Resumo_Auditoria"].set_column(0, 0, 30)
                        writer.sheets["Resumo_Auditoria"].set_column(1, 1, 20)
                        df_export.to_excel(
                            writer, index=False, sheet_name="Detalhamento"
                        )
                        writer.sheets["Detalhamento"].set_column(0, 0, 35)
                        writer.sheets["Detalhamento"].set_column(1, 1, 20)
                        writer.sheets["Detalhamento"].set_column(2, 2, 50)

                    c_dw1.download_button(
                        "📥 Exportar Lista Completa (Excel)",
                        output_aud.getvalue(),
                        f"Auditoria_{datetime.date.today().strftime('%d_%m_%Y')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                    # 🚀 Exportação PDF Real
                    pdf_auditoria = gerar_pdf_auditoria_core(
                        falhas, contagem_falhas, turma_aud
                    )
                    if pdf_auditoria:
                        c_dw2.download_button(
                            "📕 Imprimir Resumo (PDF Oficial)",
                            pdf_auditoria,
                            f"Auditoria_Oficial_{datetime.date.today().strftime('%d_%m_%Y')}.pdf",
                            "application/pdf",
                            use_container_width=True,
                        )
                    else:
                        c_dw2.error(
                            "⚠️ Biblioteca PDF (xhtml2pdf) não encontrada no servidor."
                        )

                    # Grid Interativo com Botões de Ação
                    st.markdown("<hr/>", unsafe_allow_html=True)
                    st.markdown("#### 📋 Detalhamento e Ação Rápida")
                    st.markdown(
                        "<div style='background-color: #F8FAFC; padding: 10px; border-radius: 8px; margin-bottom: 10px;'>",
                        unsafe_allow_html=True,
                    )
                    ch1, ch2, ch3, ch4 = st.columns(
                        [2.5, 2, 4.5, 2], vertical_alignment="center"
                    )
                    ch1.markdown("**Nome do Aluno**")
                    ch2.markdown("**Turma**")
                    ch3.markdown("**Falta Preencher**")
                    ch4.markdown("**Ação**")
                    st.markdown("</div>", unsafe_allow_html=True)

                    for f in falhas:
                        with st.container():
                            c1, c2, c3, c4 = st.columns(
                                [2.5, 2, 4.5, 2], vertical_alignment="center"
                            )
                            c1.write(f["Aluno"])
                            c2.write(f["Turma"])
                            c3.write(f["Pendências"])
                            with c4:
                                st.button(
                                    "🩺 Abrir Ficha",
                                    key=f"aud_{f['id_aluno']}",
                                    on_click=abrir_ficha_aluno,
                                    args=(f["dict_aluno"],),
                                    use_container_width=True,
                                )
                            st.markdown(
                                "<hr style='margin: 0px 0px 10px 0px; border-color: #E2E8F0;'/>",
                                unsafe_allow_html=True,
                            )
                else:
                    st.success(
                        "🎉 Todos os alunos desta turma possuem documentos e cadastros 100% completos!"
                    )

    # ==============================================================================
    # --- ABA 3: PRESTAÇÃO PEDAGÓGICA (MOTOR NATIVO .DOCX) ---
    # ==============================================================================
    with tab_w:
        st.markdown("### 🏆 Prestação de Conta Pedagógica")
        st.info(
            "Geração do documento oficial consolidando métricas bioindicadoras e de engajamento baseadas nos dados preenchidos no Diário de Bordo."
        )
        if not DOCX_DISPONIVEL:
            st.error(
                "⚠️ Biblioteca 'python-docx' não instalada no servidor. O relatório nativo não pode ser gerado."
            )
            return

        cw1, cw2, cw3 = st.columns(3)
        meses_dict = {
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
        hoje_mes = datetime.date.today().month
        m_w_nome = cw1.selectbox(
            "Mês de Referência",
            list(meses_dict.values()),
            index=hoje_mes - 1 if hoje_mes - 1 < 12 else 0,
        )
        m_w_num = [k for k, v in meses_dict.items() if v == m_w_nome][0]
        a_w = cw2.selectbox("Ano de Referência", [2025, 2026, 2027], index=1)
        t_w_sel = cw3.selectbox(
            "Escopo do Relatório",
            ["Global Polo"] + turmas["nome"].tolist()
            if not turmas.empty
            else ["Global Polo"],
        )

        if st.button(
            "🚀 GERAR ARQUIVO WORD (.docx)", type="primary", use_container_width=True
        ):
            with st.spinner(
                "Compilando prontuários e diários com Motor Nativo Word..."
            ):
                data_ini_w = datetime.date(a_w, m_w_num, 1)
                if m_w_num == 12:
                    data_fim_w = datetime.date(a_w, 12, 31)
                else:
                    data_fim_w = datetime.date(
                        a_w, m_w_num + 1, 1
                    ) - datetime.timedelta(days=1)

                turma_query = "" if t_w_sel == "Global Polo" else t_w_sel
                if t_w_sel == "Global Polo":
                    df_alunos_w = buscar_alunos_geral()
                    if not df_alunos_w.empty:
                        df_alunos_w = df_alunos_w[df_alunos_w["status"] != "Inativo"]
                else:
                    df_alunos_w = get_alunos_por_turma(t_w_sel)

                total_alunos_w = len(df_alunos_w) if not df_alunos_w.empty else 0
                df_freq_w = get_relatorio_periodo(data_ini_w, data_fim_w, turma_query)

                # A nova função já nos dá as aulas úteis perfeitamente no DataFrame
                if not df_freq_w.empty:
                    cols_data = [
                        c
                        for c in df_freq_w.columns
                        if c
                        not in [
                            "Nome",
                            "Turma",
                            "Total P",
                            "Total F",
                            "Total J",
                            "% Presença",
                        ]
                    ]
                    total_aulas_w = len(cols_data)
                else:
                    total_aulas_w = 0

                if not df_freq_w.empty and total_aulas_w > 0:
                    presencas_totais_w = df_freq_w["Total P"].sum()
                    possiveis = total_alunos_w * total_aulas_w
                    assiduidade_w = (
                        (presencas_totais_w / possiveis * 100) if possiveis > 0 else 0.0
                    )
                else:
                    assiduidade_w = 0.0

                eng_w = {
                    "total_alunos": total_alunos_w,
                    "total_aulas": total_aulas_w,
                    "assiduidade": assiduidade_w,
                }
                diarios_w = get_diarios_periodo(data_ini_w, data_fim_w, turma_query)
                if isinstance(diarios_w, pd.DataFrame):
                    diarios_w = diarios_w.to_dict("records")

                total_avals, soma_dor = 0, 0
                borg_list, bristol_list, urina_list = [], [], []

                if not df_alunos_w.empty:
                    for _, aluno in df_alunos_w.iterrows():
                        avals = get_avaliacoes_aluno(aluno["id"])
                        avals_lista = (
                            avals.to_dict("records")
                            if isinstance(avals, pd.DataFrame)
                            else (avals or [])
                        )
                        for av in avals_lista:
                            try:
                                dt_av = pd.to_datetime(av["data_avaliacao"]).date()
                                if data_ini_w <= dt_av <= data_fim_w:
                                    total_avals += 1
                                    soma_dor += float(
                                        av.get("nivel_dor", av.get("dor_nivel", 0))
                                    )
                                    if av.get("borg"):
                                        borg_list.append(av.get("borg"))
                                    if av.get("bristol"):
                                        bristol_list.append(av.get("bristol"))
                                    if av.get("urina"):
                                        urina_list.append(av.get("urina"))
                            except:
                                pass

                def get_moda(lista, default="Dados Insuficientes"):
                    return max(set(lista), key=lista.count) if lista else default

                clin_w = {
                    "total_avaliacoes": total_avals,
                    "dor": (soma_dor / total_avals) if total_avals > 0 else 0.0,
                    "borg": get_moda(borg_list),
                    "bristol": get_moda(bristol_list),
                    "urina": get_moda(urina_list),
                }

                doc_word = gerar_word_prestacao_contas(
                    t_w_sel, m_w_nome, a_w, eng_w, diarios_w, clin_w
                )
                if doc_word:
                    st.success("✅ Relatório Clínico/Pedagógico compilado com sucesso!")
                    st.download_button(
                        "📥 BAIXAR RELATÓRIO EXECUTIVO (.docx)",
                        doc_word,
                        f"Prestacao_Contas_{m_w_nome}_{a_w}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

    st.markdown(
        "<br><p style='text-align:center; color:#94a3b8; font-size:10px;'>Moveright™ Gestão Inteligente - Projeto Esporte e Saúde Community Phase 2 - v8.40 PRIMEMAX</p>",
        unsafe_allow_html=True,
    )
