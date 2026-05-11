# ==============================================================================
# 📄 ARQUIVO: views/relatorio_satisfacao_view.py
# 🏷️ VERSÃO: 7.0 (ULTRA-PRIME - Faxina e Gestão de Respostas)
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import time
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

def gerar_documento_word(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp):
    total_resp = len(df)
    data_emissao = datetime.date.today().strftime("%d/%m/%Y")
    def calc_tabela(coluna):
        if coluna not in df.columns: return ""
        contagem = df[coluna].value_counts()
        linhas = ""
        for sentimento, votos in contagem.items():
            if sentimento != "Sem Classificação":
                pct = int((votos / total_resp) * 100) if total_resp > 0 else 0
                linhas += f"<tr><td style='padding: 8px; border-bottom: 1px solid #E2E8F0;'>{sentimento}</td><td style='padding: 8px; border-bottom: 1px solid #E2E8F0; text-align: center;'>{votos}</td><td style='padding: 8px; border-bottom: 1px solid #E2E8F0; text-align: center;'>{pct}%</td></tr>"
        return linhas

    linhas_q4, linhas_q3, linhas_q1, linhas_q2 = calc_tabela("Sentimento_Q4"), calc_tabela("Sentimento_Q3"), calc_tabela("Sentimento_Q1"), calc_tabela("Sentimento_Q2")
    df_comentarios = df[df["comentario"].notna() & (df["comentario"].str.strip() != "")] if "comentario" in df.columns else pd.DataFrame()
    html_comentarios = ""
    for _, row in df_comentarios.head(15).iterrows():
        html_comentarios += f"<div style='margin-bottom: 10px; padding: 10px; background: #F8FAFC; border-left: 3px solid #0056b3; font-size: 10pt;'><strong>{row.get('turma', 'Turma')}</strong>: <i>\"{row['comentario']}\"</i></div>"
    if not html_comentarios: html_comentarios = "<p style='font-size: 10pt; color: #64748B;'>Nenhum comentário registrado no período.</p>"

    from utils.identidade import get_config as _gcfg_sat, get_logo_data_url as _gld_sat
    _scfg = _gcfg_sat()
    logo_b64 = _gld_sat(_scfg.get("logo_principal", "logo-imbra.png"))
    if logo_b64:
        html_logo = f'<img src="{logo_b64}" width="120" style="max-width: 120px; height: auto;">'
        style_logo = "width: 20%; text-align: right; padding: 10px; vertical-align: middle;"
    else:
        html_logo, style_logo = "INSERIR LOGO", "width: 20%; text-align: right; color: #94A3B8; font-size: 8pt; border: 1px dashed #94A3B8; padding: 10px; vertical-align: middle;"

    html_content = f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head><style>body {{ font-family: 'Arial'; color: #2C3E50; font-size: 11pt; }} h1 {{ font-size: 16pt; color: #0A2540; text-align: center; }} h2 {{ font-size: 11pt; color: #475569; text-align: center; }} .section-title {{ font-size: 12pt; font-weight: bold; color: #0A2540; border-bottom: 1px solid #CBD5E1; margin-top: 25px; }} table.data-table {{ width: 100%; border-collapse: collapse; font-size: 10pt; }} table.data-table th {{ background: #0056b3; color: white; padding: 8px; }}</style></head>
    <body>
        <table style="width: 100%; border-bottom: 3px solid #0056b3; margin-bottom: 20px;"><tr><td style="width: 20%;">SECRETARIA</td><td style="width: 60%; text-align: center;"><h1>{_scfg.get("titulo_projeto","Esporte e Saúde")}</h1><h2>Relatório de Satisfação</h2><p>Período: {periodo} de {ano}</p></td><td style="{style_logo}">{html_logo}</td></tr></table>
        <div class='section-title'>1. Qualidade dos Encontros e Metodologia (Professores)</div><table class="data-table"><tr><th>Sentimento</th><th>Votos</th><th>%</th></tr>{linhas_q4}</table>
        <div class='section-title'>2. Impacto na Qualidade de Vida (Dores Crônicas)</div><table class="data-table"><tr><th>Sentimento</th><th>Votos</th><th>%</th></tr>{linhas_q2}</table>
        <div class='section-title'>3. Aumento de Disposição e Energia no Dia a Dia</div><table class="data-table"><tr><th>Sentimento</th><th>Votos</th><th>%</th></tr>{linhas_q1}</table>
        <div class='section-title'>4. Efeito Transformador da Atividade na Vida do Aluno</div><table class="data-table"><tr><th>Sentimento</th><th>Votos</th><th>%</th></tr>{linhas_q3}</table>
        <div class='section-title'>5. Comentários</div>{html_comentarios}
    </body></html>"""
    return html_content

def gerar_pdf_satisfacao_bytes(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp):
    if not _XHTML_SAT: return None
    html = gerar_documento_word(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp)
    resultado = io.BytesIO()
    pisa.pisaDocument(io.StringIO(html), resultado)
    return resultado.getvalue() if resultado.getvalue() else None

def gerar_docx_satisfacao_bytes(df, periodo, ano, tx_exc, tx_dor, tx_ene, tx_imp):
    if not _DOCX_SAT: return None
    doc = _DocxDoc()
    doc.add_paragraph("Relatório Oficial (Versão Simples)")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# =========================================================================
# 🗑️ MÓDULO DE EXCLUSÃO DE PESQUISA (FAXINA)
# =========================================================================
def deletar_pesquisa(id_pesquisa):
    try:
        supabase.table("pesquisas_satisfacao").delete().eq("id", id_pesquisa).execute()
        st.success("✅ Pesquisa removida com sucesso!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao excluir a pesquisa: {e}")

# =========================================================================
# 📊 TELA PRINCIPAL (DASHBOARD + FAXINA)
# =========================================================================
def tela_relatorio_prime_satisfacao():
    st.markdown("<style>.metric-card { background-color: #FFFFFF; border-radius: 12px; padding: 20px; border-top: 4px solid #0056b3; text-align: center; } .metric-value { font-size: 32px; font-weight: 900; color: #0A2540; line-height: 1; } .metric-label { font-size: 11px; font-weight: 800; color: #64748B; }</style>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #0A2540; font-weight: 800; margin-bottom: 0;'>⭐ Satisfação & Impacto na Saúde</h3>", unsafe_allow_html=True)

    try: host = st.context.headers.get("host", "esportesaude.riker.replit.dev")
    except: host = "esportesaude.riker.replit.dev"
    base_url = f"https://{host}/?rota=pesquisa"

    # LINKS CLICÁVEIS/COPIÁVEIS
    with st.expander("🔗 Links de Partilha da Pesquisa (Clique na caixa para copiar)", expanded=False):
        cl1, cl2, cl3, cl4 = st.columns(4)
        with cl1:
            st.markdown("**1º Trim. (Jan–Mar)**")
            st.code(f"{base_url}&t=1", language="markdown")
        with cl2:
            st.markdown("**2º Trim. (Abr–Jun)**")
            st.code(f"{base_url}&t=2", language="markdown")
        with cl3:
            st.markdown("**3º Trim. (Jul–Set)**")
            st.code(f"{base_url}&t=3", language="markdown")
        with cl4:
            st.markdown("**Link Aberto**")
            st.code(f"{base_url}", language="markdown")

    try:
        response = supabase.table("pesquisas_satisfacao").select("*").execute()
        dados = response.data
    except Exception as e:
        st.error(f"Erro ao buscar: {e}")
        return

    if not dados:
        st.info("📌 Aguardando pesquisas.")
        return

    df = pd.DataFrame(dados)
    if "data_resposta" in df.columns: df["data_resposta"] = pd.to_datetime(df["data_resposta"], errors="coerce")

    # AS DUAS ABAS: DASHBOARD E FAXINA
    tab_dashboard, tab_faxina = st.tabs(["📊 Dashboard de Satisfação", "🧹 Gerir Respostas (Faxina)"])

    with tab_dashboard:
        c1, c2 = st.columns([1, 4])
        with c1: ano_sel = st.selectbox("Ano:", sorted(df["data_resposta"].dt.year.dropna().unique().astype(int).tolist(), reverse=True))
        with c2: trimestre_sel = st.radio("Período:", ["Ano Completo", "1º Trimestre", "2º Trimestre", "3º Trimestre", "4º Trimestre"], horizontal=True)

        df_filtrado = df[df["data_resposta"].dt.year == ano_sel].copy()
        if "1º" in trimestre_sel: df_filtrado = df_filtrado[df_filtrado["data_resposta"].dt.month.isin([1,2,3])]
        elif "2º" in trimestre_sel: df_filtrado = df_filtrado[df_filtrado["data_resposta"].dt.month.isin([4,5,6])]

        if df_filtrado.empty: return st.warning("⚠️ Nenhuma pesquisa neste período.")

        def class_sent(t):
            t = str(t).upper()
            if any(x in t for x in ["😄", "ÓTIMO", "PASSOU"]): return "Positivo (Excelente)"
            if any(x in t for x in ["😐", "BOM", "POUCO"]): return "Neutro (Mediano)"
            if any(x in t for x in ["😞", "REGULAR", "AINDA DÓI", "SEM ENERGIA", "NÃO NOTEI"]): return "Atenção (Melhoria)"
            return "Sem Classificação"

        for q in ["q1_disposicao", "q2_dores", "q3_efeito_vida", "q4_avaliacao_geral"]:
            df_filtrado[f"Sentimento_{q[:2].upper()}"] = df_filtrado.get(q, pd.Series(["Sem Classificação"]*len(df_filtrado))).apply(class_sent)

        m1, m2, m3, m4, m5 = st.columns(5)
        tx_exc = int(((df_filtrado["Sentimento_Q4"] == "Positivo (Excelente)").sum() / len(df_filtrado)) * 100) if len(df_filtrado)>0 else 0
        tx_dor = int(((df_filtrado["Sentimento_Q2"] == "Positivo (Excelente)").sum() / len(df_filtrado)) * 100) if len(df_filtrado)>0 else 0
        tx_ene = int(((df_filtrado["Sentimento_Q1"] == "Positivo (Excelente)").sum() / len(df_filtrado)) * 100) if len(df_filtrado)>0 else 0
        tx_imp = int(((df_filtrado["Sentimento_Q3"] == "Positivo (Excelente)").sum() / len(df_filtrado)) * 100) if len(df_filtrado)>0 else 0

        m1.markdown(f"<div class='metric-card'><div class='metric-value'>{len(df_filtrado)}</div><div class='metric-label'>Pesquisas</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#10B981;'>{tx_exc}%</div><div class='metric-label'>Excelência</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#0056b3;'>{tx_dor}%</div><div class='metric-label'>Alívio Dores</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#F59E0B;'>{tx_ene}%</div><div class='metric-label'>Mais Energia</div></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#8B5CF6;'>{tx_imp}%</div><div class='metric-label'>Impacto Vida</div></div>", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        mapa = {"Positivo (Excelente)": "#10B981", "Neutro (Mediano)": "#F59E0B", "Atenção (Melhoria)": "#EF4444"}
        def plot_pie(df_p, col, tit):
            cnt = df_p[col].value_counts().reset_index()
            cnt.columns = ["Sentimento", "Votos"]
            cnt = cnt[cnt["Sentimento"] != "Sem Classificação"]
            if cnt.empty: return st.info("Sem dados")
            fig = px.pie(cnt, values="Votos", names="Sentimento", hole=0.55, title=tit, color="Sentimento", color_discrete_map=mapa)
            st.plotly_chart(fig, use_container_width=True)

        r1, r2 = st.columns(2)
        with r1: plot_pie(df_filtrado, "Sentimento_Q4", "1. Qualidade dos Professores")
        with r2: plot_pie(df_filtrado, "Sentimento_Q3", "2. Impacto na Saúde")
        r3, r4 = st.columns(2)
        with r3: plot_pie(df_filtrado, "Sentimento_Q1", "3. Disposição (Energia)")
        with r4: plot_pie(df_filtrado, "Sentimento_Q2", "4. Melhora nas Dores")

    # MÓDULO DE EXCLUSÃO NA ABA 2
    with tab_faxina:
        st.info("💡 Elimine pesquisas antigas de teste para não poluir o Dashboard oficial.")
        df_resp = df.sort_values(by="data_resposta", ascending=False)
        for _, row in df_resp.iterrows():
            dt_f = row['data_resposta'].strftime("%d/%m/%Y às %H:%M") if pd.notnull(row['data_resposta']) else "Desconhecida"
            with st.expander(f"📝 {dt_f} — {row.get('turma','Turma')} ({row.get('trimestre_referencia','N/A')})"):
                cx1, cx2 = st.columns([4,1])
                with cx1:
                    st.write(f"**Disposição:** {row.get('q1_disposicao','')}")
                    st.write(f"**Dores:** {row.get('q2_dores','')}")
                    st.write(f"**Efeito Vida:** {row.get('q3_efeito_vida','')}")
                    st.write(f"**Aulas:** {row.get('q4_avaliacao_geral','')}")
                    if "comentario" in row and pd.notna(row["comentario"]) and str(row["comentario"]).strip() != "":
                        st.write(f"**Comentário Antigo:** {row['comentario']}")
                with cx2:
                    if st.button("🗑️ Excluir", key=f"del_{row['id']}", type="primary"):
                        deletar_pesquisa(row["id"])