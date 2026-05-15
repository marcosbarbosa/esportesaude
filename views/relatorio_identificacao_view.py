# ==============================================================================
# 📄 Arquivo: views/relatorio_identificacao_view.py
# 🏷️ VERSÃO: 1.0 (Módulo Cara-Crachá com Preview)
# ⚙️ FUNÇÃO: Relatório visual com foto, dados base e colunas dinâmicas.
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

def gerar_html_caracracha(df, campos_sel, opcoes_campos, orientacao, turma_sel):
    """Monta o código HTML puro para o Preview e para a conversão em PDF"""

    # 1. Configuração de Orientação da Página
    page_size = "A4 portrait" if "Retrato" in orientacao else "A4 landscape"

    # 2. Cabeçalhos da Tabela
    th_html = "<th style='width: 60px; text-align: center;'>FOTO</th><th>NOME DO ALUNO</th><th>TURMA</th>"
    for c in campos_sel:
        th_html += f"<th>{opcoes_campos[c].upper()}</th>"

    # 3. Construção das Linhas (Alunos)
    tr_html = ""
    for _, row in df.iterrows():
        foto_url = row.get("url_foto")

        # Fallback caso não tenha foto
        if pd.isna(foto_url) or not str(foto_url).strip():
            foto_img = "<div style='width: 45px; height: 45px; background-color: #E2E8F0; text-align: center; line-height: 45px; border-radius: 50%; font-size: 9px; color: #64748B; margin: 0 auto;'>Sem Foto</div>"
        else:
            foto_img = f"<img src='{foto_url}' style='width: 45px; height: 45px; border-radius: 50%; object-fit: cover;'>"

        nome = str(row.get("nome", "")).upper()
        turma = str(row.get("turma", ""))

        # Colunas Fixas
        tds = f"<td style='text-align:center;'>{foto_img}</td><td><b>{nome}</b></td><td>{turma}</td>"

        # Colunas Dinâmicas (Adicionadas pelo Operador)
        for c in campos_sel:
            val = str(row.get(c, ""))
            if val == "nan" or val == "None" or val == "": 
                val = "-"
            # Formatação especial para data de nascimento
            if c == "data_nascimento" and val != "-":
                try:
                    val = pd.to_datetime(val).strftime("%d/%m/%Y")
                except:
                    pass
            tds += f"<td>{val}</td>"

        tr_html += f"<tr>{tds}</tr>"

    data_hoje = datetime.date.today().strftime("%d/%m/%Y às %H:%M")

    # 4. Estrutura HTML/CSS Final
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: {page_size}; margin: 1cm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11px; color: #1E293B; }}
            h2 {{ text-align: center; color: #0F172A; margin-bottom: 5px; text-transform: uppercase; font-size: 18px; }}
            p {{ text-align: center; color: #64748B; margin-top: 0; margin-bottom: 20px; font-size: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #CBD5E1; padding: 8px; vertical-align: middle; }}
            th {{ background-color: #0F172A; color: white; font-weight: bold; font-size: 10px; }}
            tr:nth-child(even) {{ background-color: #F8FAFC; }}
            .footer {{ text-align: center; font-size: 8px; color: #94A3B8; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h2>Relatório de Identificação (Cara-Crachá)</h2>
        <p>Escopo Filtrado: <b>{turma_sel}</b> | Gerado em: {data_hoje}</p>
        <table>
            <thead><tr>{th_html}</tr></thead>
            <tbody>{tr_html}</tbody>
        </table>
        <div class="footer">Sistema Esporte e Saúde - Gestão Inteligente Moveright™</div>
    </body>
    </html>
    """
    return html

def renderizar_aba_caracracha():
    st.markdown("<h4 style='color: #0A2540; font-weight: 800;'>🪪 Relatório Cara-Crachá (Identificação)</h4>", unsafe_allow_html=True)
    st.caption("Crie um relatório visual com a foto dos alunos. Adicione os campos que precisar e faça um Preview antes de imprimir.")

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 3, 2], vertical_alignment="top")

        turmas = get_todas_turmas(ativas_apenas=True)
        lista_turmas = ["Todas as Turmas"] + turmas["nome"].tolist() if not turmas.empty else ["Todas as Turmas"]
        turma_sel = c1.selectbox("Filtrar Turma", lista_turmas, key="cc_turma")

        opcoes_campos = {
            "whatsapp": "WhatsApp / Celular",
            "data_nascimento": "Data de Nascimento",
            "cpf": "CPF",
            "rg": "RG",
            "endereco": "Endereço",
            "bairro": "Bairro",
            "contato_emergencia": "Contato de Emergência",
            "problemas_saude": "Problemas de Saúde",
            "medicamentos": "Medicamentos"
        }

        campos_selecionados = c2.multiselect(
            "Campos Extras (Foto, Nome e Turma já fixos)",
            options=list(opcoes_campos.keys()),
            format_func=lambda x: opcoes_campos[x],
            default=["whatsapp", "data_nascimento"],
            help="Se escolher muitos campos, mude a Orientação para Paisagem."
        )

        orientacao = c3.radio("Orientação da Folha", ["Retrato (Vertical)", "Paisagem (Wide/Horizontal)"], key="cc_ori")

    if st.button("👁️ GERAR PREVIEW DO RELATÓRIO", type="primary", use_container_width=True):
        with st.spinner("Procurando fotos e montando o relatório..."):
            df_alunos = buscar_alunos_geral("" if turma_sel == "Todas as Turmas" else turma_sel)

            if df_alunos.empty:
                st.warning("⚠️ Nenhum aluno encontrado para este filtro.")
                return

            # Ordenar por nome para facilitar a chamada
            df_alunos = df_alunos.sort_values(by="nome")

            html_final = gerar_html_caracracha(df_alunos, campos_selecionados, opcoes_campos, orientacao, turma_sel)
            st.session_state['html_caracracha'] = html_final
            st.session_state['turma_caracracha'] = turma_sel

    # --- SEÇÃO DE PREVIEW E IMPRESSÃO ---
    if 'html_caracracha' in st.session_state:
        st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px;'/>", unsafe_allow_html=True)

        col_prev, col_btn = st.columns([3, 1], vertical_alignment="bottom")
        col_prev.markdown("#### 👀 Preview do Relatório")

        if XHTML_DISPONIVEL:
            result = io.BytesIO()
            pisa.pisaDocument(io.StringIO(st.session_state['html_caracracha']), result)
            pdf_bytes = result.getvalue()

            col_btn.download_button(
                label="🖨️ BAIXAR PDF PARA IMPRIMIR",
                data=pdf_bytes,
                file_name=f"CaraCracha_{st.session_state['turma_caracracha']}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        else:
            col_btn.error("Biblioteca de PDF não disponível.")

        # Exibe o HTML dentro de um iFrame (Scrollável) no Streamlit
        st.components.v1.html(st.session_state['html_caracracha'], height=600, scrolling=True)