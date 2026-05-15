# ==============================================================================
# 📄 Arquivo: views/relatorio_identificacao_view.py
# 🏷️ VERSÃO: 1.1 (Correções: filtro turma, PDF, datetime)
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import io
from database import buscar_alunos_geral, get_todas_turmas

try:
    from xhtml2pdf import pisa
    XHTML_DISPONIVEL = True
except ImportError:
    XHTML_DISPONIVEL = False


def _css_base(page_size):
    return f"""
        @page {{ size: {page_size}; margin: 1cm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11px; color: #1E293B; }}
        h2 {{ text-align: center; color: #0F172A; margin-bottom: 5px;
              text-transform: uppercase; font-size: 18px; }}
        p {{ text-align: center; color: #64748B; margin-top: 0;
             margin-bottom: 20px; font-size: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #CBD5E1; padding: 8px; vertical-align: middle; }}
        th {{ background-color: #0F172A; color: white; font-weight: bold; font-size: 10px; }}
        tr:nth-child(even) {{ background-color: #F8FAFC; }}
        .footer {{ text-align: center; font-size: 8px; color: #94A3B8; margin-top: 20px; }}
    """


def _formatar_valor(row, c):
    val = str(row.get(c, ""))
    if val in ("nan", "None", ""):
        return "-"
    if c == "data_nascimento":
        try:
            return pd.to_datetime(val).strftime("%d/%m/%Y")
        except Exception:
            pass
    return val


def gerar_html_preview(df, campos_sel, opcoes_campos, orientacao, turma_sel):
    """HTML para exibição no browser — inclui imagens externas."""
    page_size = "A4 portrait" if "Retrato" in orientacao else "A4 landscape"

    th_html = ("<th style='width:60px;text-align:center;'>FOTO</th>"
               "<th>NOME DO ALUNO</th><th>TURMA</th>")
    for c in campos_sel:
        th_html += f"<th>{opcoes_campos[c].upper()}</th>"

    tr_html = ""
    for _, row in df.iterrows():
        foto_url = row.get("url_foto") or ""
        if pd.isna(foto_url) or not str(foto_url).strip():
            foto_cell = ("<div style='width:45px;height:45px;background:#E2E8F0;"
                         "text-align:center;line-height:45px;border-radius:50%;"
                         "font-size:9px;color:#64748B;margin:0 auto;'>Sem Foto</div>")
        else:
            foto_cell = (f"<img src='{foto_url}' style='width:45px;height:45px;"
                         "border-radius:50%;object-fit:cover;'>")

        nome  = str(row.get("nome", "")).upper()
        turma = str(row.get("turma", ""))
        tds   = (f"<td style='text-align:center;'>{foto_cell}</td>"
                 f"<td><b>{nome}</b></td><td>{turma}</td>")
        for c in campos_sel:
            tds += f"<td>{_formatar_valor(row, c)}</td>"
        tr_html += f"<tr>{tds}</tr>"

    data_hora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    return f"""<html><head><meta charset="UTF-8">
    <style>{_css_base(page_size)}</style></head>
    <body>
        <h2>Relatório de Identificação (Cara-Crachá)</h2>
        <p>Escopo: <b>{turma_sel}</b> | Gerado em: {data_hora}</p>
        <table><thead><tr>{th_html}</tr></thead><tbody>{tr_html}</tbody></table>
        <div class="footer">Sistema Esporte e Saúde — Gestão Inteligente Moveright™</div>
    </body></html>"""


def gerar_html_pdf(df, campos_sel, opcoes_campos, orientacao, turma_sel):
    """HTML para xhtml2pdf — sem imagens externas (placeholder textual)."""
    page_size = "A4 portrait" if "Retrato" in orientacao else "A4 landscape"

    th_html = ("<th style='width:50px;text-align:center;'>FOTO</th>"
               "<th>NOME DO ALUNO</th><th>TURMA</th>")
    for c in campos_sel:
        th_html += f"<th>{opcoes_campos[c].upper()}</th>"

    tr_html = ""
    for _, row in df.iterrows():
        foto_url = row.get("url_foto") or ""
        tem_foto = bool(foto_url and not pd.isna(foto_url) and str(foto_url).strip())
        foto_cell = ("📷" if tem_foto else
                     "<span style='color:#94A3B8;font-size:8px;'>Sem Foto</span>")

        nome  = str(row.get("nome", "")).upper()
        turma = str(row.get("turma", ""))
        tds   = (f"<td style='text-align:center;'>{foto_cell}</td>"
                 f"<td><b>{nome}</b></td><td>{turma}</td>")
        for c in campos_sel:
            tds += f"<td>{_formatar_valor(row, c)}</td>"
        tr_html += f"<tr>{tds}</tr>"

    data_hora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    return f"""<html><head><meta charset="UTF-8">
    <style>{_css_base(page_size)}</style></head>
    <body>
        <h2>Relatório de Identificação (Cara-Crachá)</h2>
        <p>Escopo: <b>{turma_sel}</b> | Gerado em: {data_hora}</p>
        <table><thead><tr>{th_html}</tr></thead><tbody>{tr_html}</tbody></table>
        <div class="footer">Sistema Esporte e Saúde — Gestão Inteligente Moveright™</div>
    </body></html>"""


def _gerar_pdf(html_pdf):
    result = io.BytesIO()
    try:
        status = pisa.pisaDocument(io.StringIO(html_pdf), result)
        if status.err:
            return None, f"Erro na geração do PDF (código {status.err})."
        return result.getvalue(), None
    except Exception as e:
        return None, str(e)


def renderizar_aba_caracracha():
    st.markdown(
        "<h4 style='color: #0A2540; font-weight: 800;'>🪪 Relatório Cara-Crachá (Identificação)</h4>",
        unsafe_allow_html=True,
    )
    st.caption("Relatório visual com foto dos alunos. Configure os campos, gere o preview e baixe o PDF.")

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 3, 2], vertical_alignment="top")

        turmas = get_todas_turmas(ativas_apenas=True)
        lista_turmas = (
            ["Todas as Turmas"] + turmas["nome"].tolist()
            if not turmas.empty else ["Todas as Turmas"]
        )
        turma_sel = c1.selectbox("Filtrar Turma", lista_turmas, key="cc_turma")

        opcoes_campos = {
            "whatsapp":           "WhatsApp / Celular",
            "data_nascimento":    "Data de Nascimento",
            "cpf":                "CPF",
            "rg":                 "RG",
            "endereco":           "Endereço",
            "bairro":             "Bairro",
            "contato_emergencia": "Contato de Emergência",
            "problemas_saude":    "Problemas de Saúde",
            "medicamentos":       "Medicamentos",
        }

        campos_selecionados = c2.multiselect(
            "Campos Extras (Foto, Nome e Turma já fixos)",
            options=list(opcoes_campos.keys()),
            format_func=lambda x: opcoes_campos[x],
            default=["whatsapp", "data_nascimento"],
            help="Se escolher muitos campos, mude a Orientação para Paisagem.",
        )

        orientacao = c3.radio(
            "Orientação da Folha",
            ["Retrato (Vertical)", "Paisagem (Wide/Horizontal)"],
            key="cc_ori",
        )

    if st.button("👁️ GERAR PREVIEW DO RELATÓRIO", type="primary", use_container_width=True):
        with st.spinner("Buscando alunos e montando o relatório..."):
            # Busca todos os alunos ativos e filtra por turma DEPOIS
            df_todos = buscar_alunos_geral(incluir_inativos=False)

            if df_todos.empty:
                st.warning("⚠️ Nenhum aluno encontrado.")
                return

            if turma_sel != "Todas as Turmas":
                df_alunos = df_todos[df_todos["turma"] == turma_sel].copy()
            else:
                df_alunos = df_todos.copy()

            if df_alunos.empty:
                st.warning(f"⚠️ Nenhum aluno encontrado para a turma: **{turma_sel}**.")
                return

            df_alunos = df_alunos.sort_values(by="nome")

            st.session_state["html_caracracha_preview"] = gerar_html_preview(
                df_alunos, campos_selecionados, opcoes_campos, orientacao, turma_sel
            )
            st.session_state["html_caracracha_pdf"] = gerar_html_pdf(
                df_alunos, campos_selecionados, opcoes_campos, orientacao, turma_sel
            )
            st.session_state["turma_caracracha"] = turma_sel
            st.session_state["total_caracracha"] = len(df_alunos)

    # --- SEÇÃO DE PREVIEW E IMPRESSÃO ---
    if "html_caracracha_preview" in st.session_state:
        st.markdown("<hr style='margin-top:10px;margin-bottom:20px;'/>", unsafe_allow_html=True)

        col_prev, col_btn = st.columns([3, 1], vertical_alignment="bottom")
        col_prev.markdown(
            f"#### 👀 Preview — {st.session_state.get('total_caracracha', '?')} aluno(s) "
            f"| {st.session_state.get('turma_caracracha', '')}"
        )

        if XHTML_DISPONIVEL:
            pdf_bytes, pdf_erro = _gerar_pdf(st.session_state["html_caracracha_pdf"])
            if pdf_bytes:
                col_btn.download_button(
                    label="🖨️ BAIXAR PDF",
                    data=pdf_bytes,
                    file_name=f"CaraCracha_{st.session_state['turma_caracracha']}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
            else:
                col_btn.error(f"Erro PDF: {pdf_erro}")
        else:
            col_btn.error("Biblioteca xhtml2pdf não instalada.")

        st.iframe(
            st.session_state["html_caracracha_preview"],
            height=620,
        )
