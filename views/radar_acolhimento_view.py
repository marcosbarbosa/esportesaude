# ==============================================================================
# 📄 Arquivo: views/radar_acolhimento_view.py
# 🏷️ VERSÃO: 8.0 (PRO Elite - Ordenação Dinâmica Crescente/Decrescente)
# ⚙️ FUNÇÃO: Radar de Evasão proativo com filtros avançados e UI Premium.
# ==============================================================================

import streamlit as st
import pandas as pd
import urllib.parse
import datetime
from database import supabase
from fpdf import FPDF
from utils.texto import formatar_whatsapp_numero as limpar_whatsapp_link


# ==============================================================================
# 🛠️ FUNÇÕES DE APOIO E CÁLCULO
# ==============================================================================


def calcular_dias_uteis_ausente(ultima_data, data_final):
    """Conta estritamente os dias úteis entre a última presença e hoje."""
    if pd.isna(ultima_data) or not ultima_data:
        return 9999  # Código 9999 = Nunca compareceu

    dias_uteis = 0
    dia_atual = ultima_data + datetime.timedelta(days=1)

    while dia_atual <= data_final:
        if dia_atual.weekday() < 5:
            dias_uteis += 1
        dia_atual += datetime.timedelta(days=1)

    return dias_uteis


# ==============================================================================
# 🖨️ FUNÇÃO GERADORA DE PDF (Blindada)
# ==============================================================================
def gerar_pdf_atrasados(lista_alunos):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    pdf.set_font("Arial", size=16, style="B")
    pdf.cell(
        190,
        10,
        txt="Relatorio de Acolhimento e Prevensao de Evasao",
        ln=True,
        align="C",
    )

    pdf.set_font("Arial", size=10)
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    pdf.cell(
        190,
        10,
        txt=f"Instituto Muda Brasil - Gerado em: {data_hoje}",
        ln=True,
        align="C",
    )
    pdf.ln(5)

    pdf.set_font("Arial", size=10, style="B")
    pdf.cell(85, 10, "Nome do Aluno", border=1, align="C")
    pdf.cell(45, 10, "Turma", border=1, align="C")
    pdf.cell(25, 10, "Ausencias", border=1, align="C")
    pdf.cell(35, 10, "WhatsApp", border=1, align="C")
    pdf.ln()

    pdf.set_font("Arial", size=9)
    for aluno in lista_alunos:
        nome = str(aluno.get("nome", ""))[:35]
        turma = str(aluno.get("turma", "N/A"))[:20]

        if aluno["dias"] == 9999:
            dias_str = "S/ Registo"
        else:
            dias_str = f"{aluno['dias']} dias"

        whats = str(aluno.get("whatsapp", "S/ Numero"))

        pdf.cell(85, 10, nome, border=1)
        pdf.cell(45, 10, turma, border=1)
        pdf.cell(25, 10, dias_str, border=1, align="C")
        pdf.cell(35, 10, whats, border=1, align="C")
        pdf.ln()

    resultado_pdf = pdf.output(dest="S")
    if isinstance(resultado_pdf, str):
        return resultado_pdf.encode("latin1")
    return bytes(resultado_pdf)


# ==============================================================================
# 🖥️ TELA PRINCIPAL (FRONT-END)
# ==============================================================================
def tela_radar_acolhimento():
    # 1. 🚀 INICIALIZAÇÃO DE ESTADO (Agora com a memória da Ordem)
    if "dias_busca_radar" not in st.session_state:
        st.session_state.dias_busca_radar = 7
    if "ocultar_novatos" not in st.session_state:
        st.session_state.ocultar_novatos = True
    if "ordem_evasao" not in st.session_state:
        st.session_state.ordem_evasao = "🚨 Maior Evasão (Decrescente)"

    st.markdown("### 💙 Radar de Acolhimento e Prevenção de Evasão")
    st.write(
        "Lista automática de alunos ordenados pelos mais faltosos. O cálculo ignora sábados e domingos."
    )

    # ==========================================================================
    # 🎛️ BARRA DE FILTRO (NOVA ESTRUTURA COM SELECTBOX)
    # ==========================================================================
    with st.container(border=True):
        st.markdown("**⚙️ Configurações de Busca**")

        ocultar = st.checkbox(
            "🎒 Ocultar alunos que NUNCA vieram (Focar apenas em Evasão Real)",
            value=st.session_state.ocultar_novatos,
        )

        st.write("")

        # 2. 🚀 REDESENHO DAS COLUNAS: Inserimos um espaço para a ordem
        c_dias, c_ordem, c_btn = st.columns(
            [1.5, 1.5, 1.5], vertical_alignment="bottom"
        )

        with c_dias:
            novos_dias = st.number_input(
                "Avisar a partir de (Dias):",
                min_value=1,
                value=st.session_state.dias_busca_radar,
                step=1,
            )

        with c_ordem:
            # Opções de ordenação amigáveis
            opcoes_ordem = [
                "🚨 Maior Evasão (Decrescente)",
                "📉 Menor Evasão (Crescente)",
            ]

            # Garante que a caixa seleciona o que já estava na memória
            index_atual = (
                opcoes_ordem.index(st.session_state.ordem_evasao)
                if st.session_state.ordem_evasao in opcoes_ordem
                else 0
            )

            nova_ordem = st.selectbox(
                "Ordem da Lista:", opcoes_ordem, index=index_atual
            )

        with c_btn:
            if st.button(
                "🔍 ATUALIZAR LISTA", type="primary", use_container_width=True
            ):
                # 3. 🚀 SALVA TODAS AS PREFERÊNCIAS NA MEMÓRIA
                st.session_state.dias_busca_radar = novos_dias
                st.session_state.ocultar_novatos = ocultar
                st.session_state.ordem_evasao = nova_ordem
                st.rerun()

    # ==========================================================================
    # 💾 MOTOR DE BANCO DE DADOS
    # ==========================================================================
    try:
        res_alunos = (
            supabase.table("alunos")
            .select("id, nome, whatsapp, turma, url_foto")
            .eq("status", "Ativo")
            .execute()
        )
        df_alunos = pd.DataFrame(res_alunos.data)

        if df_alunos.empty:
            st.info("Nenhum aluno ativo encontrado para análise.")
            return

        res_freq = (
            supabase.table("frequencia")
            .select("aluno_id, data_aula")
            .eq("status", "PRESENTE")
            .execute()
        )
        df_freq = pd.DataFrame(res_freq.data)

        mapa_ultimas_datas = {}
        if not df_freq.empty:
            df_freq["data_aula"] = pd.to_datetime(df_freq["data_aula"]).dt.date
            mapa_ultimas_datas = (
                df_freq.groupby("aluno_id")["data_aula"].max().to_dict()
            )

        hoje = datetime.date.today()
        lista_final_evasao = []

        for _, aluno in df_alunos.iterrows():
            aluno_id = str(aluno["id"])
            ultima_presenca = mapa_ultimas_datas.get(aluno_id, None)
            dias_calculados = calcular_dias_uteis_ausente(ultima_presenca, hoje)

            if st.session_state.ocultar_novatos and dias_calculados == 9999:
                continue

            if dias_calculados >= st.session_state.dias_busca_radar:
                foto = aluno.get("url_foto")
                if pd.isna(foto) or not foto:
                    foto = None

                whats = aluno.get("whatsapp")
                if pd.isna(whats) or not whats:
                    whats = None

                turma_val = aluno.get("turma")
                if pd.isna(turma_val) or not turma_val:
                    turma_val = "N/A"

                lista_final_evasao.append(
                    {
                        "id": aluno_id,
                        "nome": str(aluno["nome"]),
                        "turma": turma_val,
                        "whatsapp": whats,
                        "url_foto": foto,
                        "dias": dias_calculados,
                        "data_ultima": ultima_presenca,
                    }
                )

        # ==========================================================================
        # 4. 🚀 A LÓGICA MÁGICA DE ORDENAÇÃO DINÂMICA
        # ==========================================================================
        # Se a opção escolhida tiver a palavra "Decrescente", o reverse é True. Se não, é False.
        ordem_reversa = (
            True if "Decrescente" in st.session_state.ordem_evasao else False
        )
        lista_final_evasao.sort(key=lambda x: x["dias"], reverse=ordem_reversa)

        # ==========================================================================
        # 🎨 RENDERIZAÇÃO DA TELA (LISTA FINAL E TAGS)
        # ==========================================================================
        if len(lista_final_evasao) == 0:
            st.success("✅ Tudo em ordem! Nenhum aluno atingiu os critérios de filtro.")
        else:
            c_titulo, c_pdf = st.columns([3, 1], vertical_alignment="bottom")
            with c_titulo:
                st.markdown(f"#### 🚨 Alunos identificados pelo Radar:")
            with c_pdf:
                pdf_bytes = gerar_pdf_atrasados(lista_final_evasao)
                st.download_button(
                    label="📄 Baixar Relatório PDF",
                    data=pdf_bytes,
                    file_name=f"Radar_Evasao_{datetime.date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.markdown("---")

            for item in lista_final_evasao:
                nome_curto = str(item["nome"]).split()[0].capitalize()
                numero = limpar_whatsapp_link(item["whatsapp"])

                if item["dias"] == 9999:
                    alerta_visual = (
                        "⚠️ Nenhuma presença registada (Faltoso desde a matrícula)"
                    )
                    tag_html = "<span style='background: #FEF08A; color: #854D0E; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; border: 1px solid #EAB308; margin-left: 8px;'>🆕 NUNCA COMPARECEU</span>"
                else:
                    data_str = item["data_ultima"].strftime("%d/%m/%Y")
                    alerta_visual = f"⚠️ {item['dias']} dias úteis ausente (Última presença: {data_str})"
                    tag_html = "<span style='background: #FECACA; color: #991B1B; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; border: 1px solid #F87171; margin-left: 8px;'>🚨 EVASÃO</span>"

                msg = f"Olá, {nome_curto}! Tudo bem? Sentimos sua falta nas aulas do Instituto Muda Brasil! 💙 Está tudo bem com você? Queríamos saber se está precisando de algo e quando pretende voltar. Sua presença é muito importante para nós! Um grande abraço!"
                link_wa = (
                    f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"
                    if numero
                    else None
                )

                with st.container(border=True):
                    col_foto, col_texto, col_botao = st.columns(
                        [1, 4, 1.5], vertical_alignment="center"
                    )

                    with col_foto:
                        if item.get("url_foto"):
                            st.image(item["url_foto"], use_container_width=True)
                        else:
                            st.markdown(
                                "<h1 style='text-align: center; color: #ccc; margin: 0;'>👤</h1>",
                                unsafe_allow_html=True,
                            )

                    with col_texto:
                        st.markdown(
                            f"**{item['nome'].upper()}** {tag_html}",
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"**Turma:** {item['turma']}  \n<span style='color: #EF4444;'>{alerta_visual}</span>",
                            unsafe_allow_html=True,
                        )

                    with col_botao:
                        if link_wa:
                            st.link_button(
                                "💬 ACOLHER",
                                link_wa,
                                type="primary",
                                use_container_width=True,
                            )
                        else:
                            st.button(
                                "Sem WhatsApp",
                                disabled=True,
                                use_container_width=True,
                                key=f"btn_off_{item['id']}",
                            )

    except Exception as e:
        st.error(f"Erro ao processar radar: {e}")
