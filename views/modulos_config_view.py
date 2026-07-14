# ==============================================================================
# 📄 views/modulos_config_view.py — Controle de Módulos e Funcionalidades
# SuperAdmin pode habilitar/desabilitar cada módulo para os usuários do sistema.
# ==============================================================================
import json
import streamlit as st
from database import set_config_valor, get_modulos_permissoes

# Definição declarativa de todos os módulos e funcionalidades controláveis.
# Adicionar novos módulos aqui — o restante do código é genérico.
MODULOS_DEFINICAO = [
    {
        "secao": "🗂️ Menus de Navegação",
        "itens": [
            {
                "chave": "mod_frequencia",
                "label": "✅ Frequência",
                "desc": (
                    "Menu de chamada diária, diário de aula, dossiê de turma, "
                    "emergência e controle de atestados médicos."
                ),
            },
            {
                "chave": "mod_portal_aluno",
                "label": "🩺 Portal do Aluno",
                "desc": (
                    "Ficha de matrícula, prontuário clínico, anamnese de dores, "
                    "medições corporais e histórico de saúde."
                ),
            },
            {
                "chave": "mod_relatorios",
                "label": "📊 Relatórios & BI",
                "desc": (
                    "Dashboards de presença, gráficos de evolução, "
                    "relatórios de período e exportações em PDF."
                ),
            },
        ],
    },
    {
        "secao": "🔧 Funcionalidades Específicas",
        "itens": [
            {
                "chave": "feat_dias_anamnese",
                "label": "📅 Aba 'Dias Regist./Anamnese'  (dentro de Frequência)",
                "desc": (
                    "Histórico de datas de aulas registradas, calendário de presença "
                    "e configuração do prazo de validade da anamnese clínica."
                ),
            },
        ],
    },
]


def tela_modulos_config():
    st.markdown(
        "<p style='font-weight:800;color:#0A2540;font-size:1rem;margin-bottom:2px;'>"
        "🔐 Controle de Módulos e Funcionalidades</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Habilite ou desabilite cada módulo para **todos os usuários** do sistema. "
        "O SuperAdmin sempre tem acesso completo, independente dessas configurações."
    )
    st.markdown("---")

    perms = get_modulos_permissoes()
    novos_valores: dict = {}

    for secao_def in MODULOS_DEFINICAO:
        st.markdown(
            f"<p style='font-weight:700;color:#1E40AF;font-size:0.9rem;"
            f"margin:12px 0 6px;'>{secao_def['secao']}</p>",
            unsafe_allow_html=True,
        )
        for item in secao_def["itens"]:
            chave = item["chave"]
            valor_atual = perms.get(chave, True)

            col_tog, col_info = st.columns([1.4, 4], gap="small",
                                           vertical_alignment="center")
            novo = col_tog.toggle(
                item["label"],
                value=valor_atual,
                key=f"mods_tog_{chave}",
            )
            col_info.caption(item["desc"])
            novos_valores[chave] = novo

        st.markdown("")

    st.markdown("---")
    col_btn, col_status = st.columns([1.5, 4], gap="small")
    if col_btn.button("💾 Salvar", type="primary", use_container_width=True,
                      key="mods_salvar"):
        ok, msg = set_config_valor(
            "config_modulos_permissoes", json.dumps(novos_valores)
        )
        get_modulos_permissoes.clear()
        if ok:
            col_status.success("✅ Configurações salvas! As alterações valem para todos imediatamente.")
            st.rerun()
        else:
            col_status.error(f"❌ Erro ao salvar: {msg}")

    st.caption(
        "💡 **Dica:** módulos desabilitados somem do menu de navegação e das abas. "
        "Habilite novamente aqui a qualquer momento para restaurar o acesso."
    )
