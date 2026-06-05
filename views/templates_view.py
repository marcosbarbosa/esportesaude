# ==============================================================================
# 📄 Arquivo: views/templates_view.py
# 🏷️ VERSÃO: 1.1 (PRO Elite - Gestão de Copywriting CRM)
# ==============================================================================
import math

import streamlit as st
from database import get_crm_templates, atualizar_crm_template

# Gatilhos de aniversário descontinuados (não editáveis no painel).
# "Aviso Prévio" (niver_futuro) foi removido: o sistema só usa "Dia Exato"
# (niver_hoje) e "Atrasado" (niver_passou).
GATILHOS_OCULTOS = {"niver_futuro"}


def _altura_textarea(texto: str, min_h: int = 120, max_h: int = 600,
                     por_linha: int = 24, larg_aprox: int = 60) -> int:
    """Calcula uma altura que exibe a mensagem inteira sem barra de rolagem.

    Cresce conforme o número de linhas (quebras explícitas + estimativa de
    quebras por largura), respeitando limites mínimo e máximo.
    """
    texto = texto or ""
    linhas = texto.split("\n")
    total = 0
    for ln in linhas:
        total += max(1, math.ceil(len(ln) / larg_aprox))
    altura = total * por_linha + 40
    return max(min_h, min(max_h, altura))


def _bloco_template(t):
    """Renderiza um expander com textarea auto-expansível + botão de salvar."""
    key_txt = f"txt_{t['gatilho']}"
    valor_atual = st.session_state.get(key_txt, t["mensagem"])
    with st.expander(f"🎉 {t['titulo']}"):
        nova_msg = st.text_area(
            "Texto da Mensagem:",
            value=t["mensagem"],
            height=_altura_textarea(valor_atual),
            key=key_txt,
        )
        if st.button(
            "💾 Guardar Texto",
            key=f"btn_{t['gatilho']}",
            type="primary",
            use_container_width=True,
        ):
            sucesso, msg = atualizar_crm_template(t["gatilho"], nova_msg)
            if sucesso:
                st.success("Atualizado!")
                st.rerun()
            else:
                st.error(msg)


def tela_gestao_templates():
    st.title("💬 Gestão de Mensagens (WhatsApp)")
    st.write(
        "Personalize os textos automáticos que o sistema utiliza para contactar os alunos."
    )
    st.info(
        "💡 **Dica de Copywriting:** Use a tag `{nome}` no meio do texto. O sistema irá substituí-la automaticamente pelo primeiro nome do aluno na hora de enviar!"
    )
    st.divider()

    df_templates = get_crm_templates()

    if df_templates.empty:
        st.warning("Nenhum template encontrado na base de dados.")
        return

    # Remove gatilhos descontinuados (ex.: Aviso Prévio).
    df_templates = df_templates[~df_templates["gatilho"].isin(GATILHOS_OCULTOS)]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚨 Retenção e Evasão")
        for _, t in df_templates[
            df_templates["gatilho"].str.contains("evasao|assiduo", regex=True)
        ].iterrows():
            _bloco_template(t)

    with col2:
        st.markdown("### 🎂 Parabenizações (Aniversários)")
        for _, t in df_templates[
            df_templates["gatilho"].str.contains("niver", regex=False)
        ].iterrows():
            _bloco_template(t)
