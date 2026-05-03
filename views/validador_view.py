# ==============================================================================
# 📄 Arquivo: views/validador_view.py
# 🏷️ VERSÃO: 1.0 (PRO Elite - Validador Público LGPD)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Página pública para validação de QR Code das fichas de matrícula.
# ==============================================================================

import streamlit as st
from database import supabase
from utils.imagem import get_base64_image

def tela_validador_publico():
    st.markdown("<br>", unsafe_allow_html=True)

    col_logo1, col_texto, col_logo2 = st.columns([1, 2, 1], vertical_alignment="center")

    from utils.identidade import get_config as _gcfg_val, get_logo_data_url as _gld_val
    _vcfg = _gcfg_val()
    logo_sec = _gld_val(_vcfg.get("logo_secundaria", "logo-secretaria.png"))
    if logo_sec: col_logo1.markdown(f'<img src="{logo_sec}" width="100%" style="max-width: 120px;">', unsafe_allow_html=True)

    logo_inst = _gld_val(_vcfg.get("logo_principal", "logo-imbra.png"))
    if logo_inst: col_logo2.markdown(f'<img src="{logo_inst}" width="100%" style="max-width: 120px; float: right;">', unsafe_allow_html=True)

    with col_texto:
        st.markdown("<h2 style='text-align: center; color: #0A2540; font-weight: 900; margin-bottom: 0;'>AUDITORIA DIGITAL</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B;'>Validação de Documentos Oficiais</p>", unsafe_allow_html=True)

    st.markdown("<hr style='border-top: 2px solid #0056b3;'>", unsafe_allow_html=True)

    aluno_id = st.query_params.get("id")

    if not aluno_id:
        st.error("❌ Link de validação corrompido ou ID de protocolo não informado.")
        return

    with st.spinner("A consultar a base de dados central..."):
        try:
            res = supabase.from_("alunos").select("nome, turma, status, id").eq("id", str(aluno_id)).execute()

            if res.data:
                aluno = res.data[0]
                st.success("✅ DOCUMENTO OFICIAL VALIDADO COM SUCESSO")

                with st.container(border=True):
                    st.markdown(f"**Projeto Autorizado:** {_vcfg.get('titulo_projeto','ESPORTE E SAÚDE NA COMUNIDADE - FASE 2')}")
                    st.markdown(f"**Nome do Aluno:** {aluno['nome']}")
                    st.markdown(f"**Turma / Horário:** {aluno['turma']}")
                    st.markdown(f"**Status da Matrícula:** {aluno['status'].upper()}")
                    st.markdown(f"**ID de Protocolo Único:** `{aluno['id']}`")

                st.info("🔒 Em conformidade com a Lei Geral de Proteção de Dados (LGPD), informações sensíveis como CPF, morada e boletins de saúde foram ocultados desta visualização pública.")
            else:
                st.error("❌ ALERTA DE SEGURANÇA: Este documento não foi encontrado na base de dados oficial. Poderá tratar-se de uma falsificação.")
        except Exception as e:
            st.error("Erro técnico ao ligar com o servidor de validação.")