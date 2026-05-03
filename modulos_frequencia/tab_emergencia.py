# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_emergencia.py
# 🏷️ VERSÃO: 2.5 (PRO Elite - UI Cards Híbridos + Dados Clínicos Restaurados)
# ⚙️ FUNÇÃO: Listagem rápida, acionamento de contatos e atalho para Ficha Digital.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import re
from utils.texto import formatar_whatsapp_link as limpar_whatsapp_emergencia

def renderizar_aba_emergencia(df_alunos_tab, turma_selecionada):
    if df_alunos_tab.empty:
        st.warning("Selecione uma turma para carregar os alunos.")
        return

    st.markdown("""
        <div style='background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px;'>
            <strong style='color: #991B1B;'>⚠️ USO RESTRITO DE EMERGÊNCIA:</strong><br>
            <span style='color: #B91C1C; font-size: 13px;'>Em caso de incidente grave, consulte os dados clínicos abaixo e clique em <strong>'🚨 Acionar'</strong> para abrir diretamente o WhatsApp ou a linha telefónica do responsável.</span>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================================================
    # 🎛️ CONTROLES PRESERVADOS (Filtro, Ordenação e Exportação)
    # ==========================================================================
    c_search, c_sort, c_export = st.columns([3, 1, 1], vertical_alignment="bottom")

    busca = c_search.text_input("🔍 Buscar Aluno:", placeholder="Digite o nome do aluno...")
    ordenacao = c_sort.selectbox("Ordenar:", ["A-Z", "Z-A"])

    if c_export.button("🖨️ Exportar PDF", use_container_width=True, type="primary"):
        st.info(f"A exportação em PDF dos contatos da turma {turma_selecionada} será anexada aqui.")

    st.markdown("<hr style='margin: 10px 0px 20px 0px; border-color: #E2E8F0;'>", unsafe_allow_html=True)

    # ==========================================================================
    # 🧠 LÓGICA DE FILTRAGEM
    # ==========================================================================
    df_exibir = df_alunos_tab.copy()

    if busca:
        df_exibir = df_exibir[df_exibir['nome'].str.contains(busca, case=False, na=False)]

    if ordenacao == "Z-A":
        df_exibir = df_exibir.sort_values("nome", ascending=False)
    else:
        df_exibir = df_exibir.sort_values("nome", ascending=True)

    if df_exibir.empty:
        st.warning("Nenhum aluno encontrado com este nome.")
        return

    # ==========================================================================
    # 🎨 ESTILOS CSS GLOBAIS (Restaurados para Efeito Zoom e Badges)
    # ==========================================================================
    st.markdown("""
    <style>
        .em-nome { font-size: 16px; font-weight: 900; color: #0F172A; margin: 0; line-height: 1.2; text-transform: uppercase; }
        .em-idade { font-size: 12.5px; color: #64748B; margin: 0 0 6px 0; font-weight: 600; }
        .em-badge-alergia { background-color: #FEF2F2; color: #DC2626; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800; display: inline-block; border: 1px solid #FCA5A5; margin-bottom: 3px; }
        .em-badge-saude { background-color: #FFFBEB; color: #D97706; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800; display: inline-block; border: 1px solid #FCD34D; margin-bottom: 3px; }
        .em-badge-vazio { background-color: #F8FAFC; color: #94A3B8; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; border: 1px dashed #CBD5E1; }
        .zoom-avatar-em { width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid #EF4444; box-shadow: 0px 2px 4px rgba(0,0,0,0.1); transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 10; flex-shrink: 0; }
        .zoom-avatar-em:hover { transform: scale(3.5); z-index: 99999 !important; box-shadow: 0px 10px 20px rgba(0,0,0,0.5); }
        .em-avatar-placeholder { width: 55px; height: 55px; border-radius: 50%; background-color: #F1F5F9; color: #94A3B8; display: flex; align-items: center; justify-content: center; font-size: 24px; border: 2px dashed #CBD5E1; flex-shrink: 0; }
    </style>
    """, unsafe_allow_html=True)

    # ==========================================================================
    # 🖼️ RENDERIZAÇÃO DOS CARDS (Híbrido Streamlit + HTML)
    # ==========================================================================
    for _, row in df_exibir.iterrows():
        with st.container(border=True):
            # Ajuste das larguras das colunas para comportar bem a informação clínica
            c_img, c_info, c_acao, c_ficha = st.columns([1.2, 4.5, 1.8, 1.5], vertical_alignment="center")

            # 1️⃣ Tratamento do Avatar
            foto = row.get("url_foto", "")
            if pd.notna(foto) and str(foto).strip() != "" and str(foto).strip().lower() not in ["none", "nan", "null"]:
                avatar_html = f'<img src="{foto}" class="zoom-avatar-em">'
            else:
                avatar_html = '<div class="em-avatar-placeholder">👤</div>'
            c_img.markdown(avatar_html, unsafe_allow_html=True)

            # 2️⃣ Tratamento dos Dados (Idade, Contato e Clínica)
            nome = str(row.get("nome", "Sem Nome")).strip()
            contato_str = str(row.get("contato_emergencia", "")).strip()

            # Cálculo de Idade
            idade_str = "Idade Ñ Informada"
            if pd.notna(row.get('data_nascimento')):
                try:
                    dt_nasc = pd.to_datetime(row['data_nascimento'])
                    hoje = datetime.date.today()
                    idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
                    idade_str = f"{idade} anos"
                except: pass

            # Verificação de Contato
            if pd.isna(contato_str) or contato_str == "" or contato_str.lower() in ["nan", "não informado", "none"]:
                contato_html = "<span style='color: #94A3B8;'>Sem Contato</span>"
            else:
                contato_html = f"<span style='color: #EF4444; font-weight: 800;'>📞 {contato_str}</span>"

            # 🚀 Badges Clínicos (O grande diferencial de Segurança)
            alergia_str = str(row.get('alergias', '')).strip()
            alergia_html = f"<div class='em-badge-alergia'>⚠️ Alergia: {alergia_str[:40]}</div><br>" if alergia_str and alergia_str.lower() not in ['nan', 'none', 'não', ''] else ""

            saude_str = str(row.get('problemas_saude', '')).strip()
            saude_html = f"<div class='em-badge-saude'>🏥 Saúde: {saude_str[:45]}</div><br>" if saude_str and saude_str.lower() not in ['nan', 'none', 'não', ''] else ""

            if not alergia_html and not saude_html:
                tags_html = "<div class='em-badge-vazio'>Nenhuma restrição clínica reportada.</div>"
            else:
                tags_html = f"{alergia_html}{saude_html}"

            # Construção Final do HTML da Info
            c_info.markdown(f"""
                <div style="line-height: 1.3;">
                    <p class="em-nome">{nome}</p>
                    <p class="em-idade">{idade_str} &nbsp;•&nbsp; {contato_html}</p>
                    {tags_html}
                </div>
            """, unsafe_allow_html=True)

            # 3️⃣ Botões de Acionamento (Híbridos Nativo Streamlit)
            with c_acao:
                if pd.isna(contato_str) or contato_str == "" or contato_str.lower() in ["nan", "não informado", "none"]:
                    st.button("🚨 Acionar", disabled=True, key=f"em_dis_{row['id']}", use_container_width=True)
                else:
                    link_w = limpar_whatsapp_emergencia(contato_str)
                    if link_w:
                        st.link_button("🚨 WhatsApp", link_w, use_container_width=True)
                    else:
                        numero_limpo_tel = re.sub(r"\D", "", contato_str)
                        st.link_button("🚨 Ligar Agora", f"tel:{numero_limpo_tel}", use_container_width=True)

            # 4️⃣ O Botão Ficha Digital 
            with c_ficha:
                if st.button("🩺 Ver Ficha", key=f"em_f_{row['id']}", use_container_width=True, type="primary"):
                    st.session_state.aluno_prontuario = row.to_dict()
                    st.session_state.origem_prontuario = "Frequência"
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.rerun()