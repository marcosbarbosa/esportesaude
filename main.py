# ==============================================================================
# 📄 Arquivo: main.py novo modulo
# 🏷️ VERSÃO: 14.5 (PRO Elite - Fix CSS Dark Mode e Integração Google Drive)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Roteador Central, Segurança, Dashboard Principal e Temas.
# ==============================================================================

import streamlit as st

st.set_page_config(
    page_title="Esporte e Saúde - Gestão",
    layout="wide",
    page_icon="🏃‍♂️",
    initial_sidebar_state="collapsed",
)

import datetime
import time
import pandas as pd
import re
import random
import urllib.parse
import math

from database import (
    get_agendamentos_pendentes,
    autenticar_usuario,
    cadastrar_usuario_sistema,
    recuperar_senha_usuario,
    get_template_seguro_db,
    ADMIN_MASTER,
    supabase,
)


# ==============================================================================
# 🎨 SELETOR DINÂMICO DE TEMA E FERRAMENTAS GLOBAIS
# ==============================================================================
def injetar_css_tema():
    """Injeta CSS do tema ativo com .stApp como prefixo para superar especificidade do CSS base."""
    if "tema_operador" not in st.session_state:
        st.session_state.tema_operador = "Claro"

    if st.session_state.tema_operador == "Escuro":
        st.markdown("""
<style>
/* ════════════════════════════════════════════════════════════════
   TEMA ESCURO v3 — prefixo .stApp garante especificidade máxima
════════════════════════════════════════════════════════════════ */

/* ── Fundos ─────────────────────────────────────────────────── */
.stApp                                        { background: #0E1117 !important; }
.stApp .stSidebar                             { background: #1E293B !important; }
.stApp div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1E293B !important;
    border-color: #334155 !important;
}

/* ── Texto global ─────────────────────────────────────────────── */
.stApp p, .stApp span, .stApp li,
.stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp h5, .stApp h6,
.stApp label,
.stApp div[data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
.stApp small, .stApp .stCaption p             { color: #94A3B8 !important; }

/* ── Nav radiogroup ───────────────────────────────────────────── */
.stApp div[role="radiogroup"]                 { background: #1E293B !important; border-color: #334155 !important; }
.stApp div[role="radiogroup"]::before         { color: #3B82F6 !important; }
.stApp div[role="radiogroup"] label p         { color: #94A3B8 !important; }
.stApp div[role="radiogroup"] label:hover     { background: #334155 !important; }
.stApp div[role="radiogroup"] label[data-checked="true"]   { background: #3B82F6 !important; }
.stApp div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }

/* ── Inputs / Selects / Textareas ─────────────────────────────── */
.stApp div[data-baseweb="input"] > div,
.stApp div[data-baseweb="select"] > div,
.stApp div[data-baseweb="textarea"] > div {
    background: #1E293B !important;
    border-color: #334155 !important;
}
.stApp div[data-baseweb="input"] input,
.stApp div[data-baseweb="textarea"] textarea,
.stApp div[data-baseweb="select"] input,
.stApp div[data-baseweb="select"] [data-testid="stSelectboxValue"],
.stApp div[data-baseweb="select"] [data-testid="stSelectboxLabel"] { color: #F8FAFC !important; }

/* ── BOTÕES PRIMARY ───────────────────────────────────────────── */
.stApp button[kind="primary"],
.stApp button[kind="primaryFormSubmit"],
.stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(135deg,#0056b3 0%,#0072e5 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
}
.stApp button[kind="primary"] p,
.stApp button[kind="primary"] span,
.stApp button[kind="primaryFormSubmit"] p,
.stApp button[kind="primaryFormSubmit"] span,
.stApp button[data-testid="stBaseButton-primary"] p,
.stApp button[data-testid="stBaseButton-primaryFormSubmit"] p { color: #FFFFFF !important; }

/* ── BOTÕES SECONDARY ─────────────────────────────────────────── */
.stApp button[kind="secondary"],
.stApp button[kind="secondaryFormSubmit"],
.stApp button[data-testid="stBaseButton-secondary"],
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: #1E293B !important;
    border: 1.5px solid #475569 !important;
    color: #F8FAFC !important;
}
.stApp button[kind="secondary"]:hover,
.stApp button[kind="secondaryFormSubmit"]:hover,
.stApp button[data-testid="stBaseButton-secondary"]:hover,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background: #334155 !important;
    border-color: #64748B !important;
    color: #93C5FD !important;
}
.stApp button[kind="secondary"] p,
.stApp button[kind="secondary"] span,
.stApp button[kind="secondaryFormSubmit"] p,
.stApp button[kind="secondaryFormSubmit"] span,
.stApp button[data-testid="stBaseButton-secondary"] p,
.stApp button[data-testid="stBaseButton-secondary"] span,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] p,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] span { color: #F8FAFC !important; }
.stApp button[kind="secondary"]:hover p,
.stApp button[kind="secondary"]:hover span,
.stApp button[data-testid="stBaseButton-secondary"]:hover p,
.stApp button[data-testid="stBaseButton-secondary"]:hover span { color: #93C5FD !important; }

/* ── BOTÕES TERTIARY ──────────────────────────────────────────── */
.stApp button[kind="tertiary"],
.stApp button[data-testid="stBaseButton-tertiary"] {
    background: transparent !important;
    border: none !important;
    color: #93C5FD !important;
}
.stApp button[kind="tertiary"] p,
.stApp button[kind="tertiary"] span,
.stApp button[data-testid="stBaseButton-tertiary"] p,
.stApp button[data-testid="stBaseButton-tertiary"] span { color: #93C5FD !important; }

/* ── BOTÕES ICON ──────────────────────────────────────────────── */
.stApp button[kind="icon"],
.stApp button[data-testid="stBaseButton-icon"] {
    background: #1E293B !important;
    border-color: #334155 !important;
    color: #F8FAFC !important;
}
.stApp button[kind="icon"] p,
.stApp button[data-testid="stBaseButton-icon"] p { color: #F8FAFC !important; }

/* ── LINK BUTTONS ─────────────────────────────────────────────── */
.stApp a[data-testid="stLinkButton"],
.stApp .stLinkButton a {
    background: #1E293B !important;
    border: 1.5px solid #475569 !important;
    color: #F8FAFC !important;
}
.stApp a[data-testid="stLinkButton"]:hover,
.stApp .stLinkButton a:hover { background: #334155 !important; color: #93C5FD !important; }
.stApp a[data-testid="stLinkButton"] p,
.stApp a[data-testid="stLinkButton"] span,
.stApp .stLinkButton a p,
.stApp .stLinkButton a span { color: #F8FAFC !important; }

/* ── SORT HEADER (cabeçalhos clicáveis do grid) ───────────────── */
.stApp .sort-header button {
    background: transparent !important;
    border: none !important;
    color: #CBD5E1 !important;
    font-weight: 700 !important;
}
.stApp .sort-header button:hover { color: #60A5FA !important; }
.stApp .sort-header button p,
.stApp .sort-header button span { color: inherit !important; }

/* ── TABS ─────────────────────────────────────────────────────── */
.stApp button[data-baseweb="tab"]                           { color: #94A3B8 !important; }
.stApp button[data-baseweb="tab"][aria-selected="true"]     { color: #60A5FA !important; border-color: #60A5FA !important; }

/* ── EXPANDERS ────────────────────────────────────────────────── */
.stApp details summary                        { color: #F8FAFC !important; }
.stApp details[data-testid="stExpander"]      { border-color: #334155 !important; }

/* ── MÉTRICAS ─────────────────────────────────────────────────── */
.stApp div[data-testid="stMetricValue"]       { color: #F8FAFC !important; }
.stApp div[data-testid="stMetricLabel"] p     { color: #94A3B8 !important; }
.stApp div[data-testid="stMetricDelta"]       { color: #94A3B8 !important; }

/* ── ALERTAS / INFO / WARNING ─────────────────────────────────── */
.stApp div[data-testid="stAlert"] p           { color: inherit !important; }
</style>
""", unsafe_allow_html=True)

    else:
        # Tema Claro — especificidade .stApp garante contraste sobre qualquer override
        st.markdown("""
<style>
/* ════════════════════════════════════════════════════════════════
   TEMA CLARO v3 — contraste total em todos os tipos de botão
════════════════════════════════════════════════════════════════ */

/* ── BOTÕES SECONDARY ─────────────────────────────────────────── */
.stApp button[kind="secondary"],
.stApp button[kind="secondaryFormSubmit"],
.stApp button[data-testid="stBaseButton-secondary"],
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: #F8FAFC !important;
    border: 1.5px solid #E2E8F0 !important;
    color: #1E293B !important;
}
.stApp button[kind="secondary"]:hover,
.stApp button[kind="secondaryFormSubmit"]:hover,
.stApp button[data-testid="stBaseButton-secondary"]:hover,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background: #EEF2FF !important;
    border-color: #C7D2FE !important;
    color: #0056b3 !important;
}
.stApp button[kind="secondary"] p,
.stApp button[kind="secondary"] span,
.stApp button[kind="secondaryFormSubmit"] p,
.stApp button[kind="secondaryFormSubmit"] span,
.stApp button[data-testid="stBaseButton-secondary"] p,
.stApp button[data-testid="stBaseButton-secondary"] span,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] p,
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] span { color: #1E293B !important; }
.stApp button[kind="secondary"]:hover p,
.stApp button[data-testid="stBaseButton-secondary"]:hover p { color: #0056b3 !important; }

/* ── BOTÕES TERTIARY ──────────────────────────────────────────── */
.stApp button[kind="tertiary"],
.stApp button[data-testid="stBaseButton-tertiary"] { color: #0056b3 !important; }
.stApp button[kind="tertiary"] p,
.stApp button[data-testid="stBaseButton-tertiary"] p { color: #0056b3 !important; }

/* ── LINK BUTTONS ─────────────────────────────────────────────── */
.stApp a[data-testid="stLinkButton"],
.stApp .stLinkButton a {
    background: #F8FAFC !important;
    border: 1.5px solid #E2E8F0 !important;
    color: #1E293B !important;
}
.stApp a[data-testid="stLinkButton"]:hover,
.stApp .stLinkButton a:hover {
    background: #EEF2FF !important;
    border-color: #C7D2FE !important;
    color: #0056b3 !important;
}
.stApp a[data-testid="stLinkButton"] p,
.stApp a[data-testid="stLinkButton"] span,
.stApp .stLinkButton a p,
.stApp .stLinkButton a span { color: #1E293B !important; }

/* ── SORT HEADER (cabeçalhos clicáveis do grid) ───────────────── */
.stApp .sort-header button {
    background: transparent !important;
    border: none !important;
    color: #0F172A !important;
    font-weight: 700 !important;
}
.stApp .sort-header button:hover { color: #1D4ED8 !important; }
.stApp .sort-header button p,
.stApp .sort-header button span { color: inherit !important; }
</style>
""", unsafe_allow_html=True)


def _toggle_tema_ui(key_suffix=""):
    """Widget compacto de toggle de tema — reutilizável no login e no app."""
    tema_escolhido = st.selectbox(
        "🌗",
        ["☀️ Claro", "🌙 Escuro"],
        index=0 if st.session_state.tema_operador == "Claro" else 1,
        label_visibility="collapsed",
        key=f"tema_sel_{key_suffix}",
    )
    novo = "Claro" if tema_escolhido.startswith("☀️") else "Escuro"
    if novo != st.session_state.tema_operador:
        st.session_state.tema_operador = novo
        st.rerun()


def renderizar_seletor_tema():
    """Renderiza Drive + Seletor de Tema no topo do app (apenas logado)."""
    col_vazia, col_drive, col_tema = st.columns(
        [5.5, 2.5, 2], vertical_alignment="center"
    )
    with col_drive:
        st.link_button(
            "📂 Abrir Google Drive",
            "https://drive.google.com/drive/u/7/my-drive",
            use_container_width=True,
            help="Acesse a pasta da nuvem para gerir as fotografias.",
        )
    with col_tema:
        _toggle_tema_ui(key_suffix="app")


# ==============================================================================
# 🚪 ROTEADOR PÚBLICO COM "BOTÃO DE VOLTAR" E VALIDADOR DE QR CODE
# ==============================================================================
rota = st.query_params.get("rota")
if rota in ["inscricao", "pesquisa", "validar"]:
    st.markdown(
        "<style>#MainMenu, header, footer {visibility: hidden;} .block-container {padding-top: 1rem !important;}</style>",
        unsafe_allow_html=True,
    )

    if rota != "validar":
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("⬅️ Voltar ao Início", use_container_width=True):
                st.query_params.clear()
                st.rerun()
        st.markdown(
            "<hr style='margin-top: 0; margin-bottom: 20px; border-top: 2px solid #E2E8F0;'>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if rota == "inscricao":
        from views.inscricao_publica_view import tela_inscricao_publica_move_right

        tela_inscricao_publica_move_right()
    elif rota == "pesquisa":
        from views.pesquisa_satisfacao_view import tela_pesquisa_satisfacao_move_right

        tela_pesquisa_satisfacao_move_right()
    elif rota == "validar":
        from views.validador_view import tela_validador_publico

        tela_validador_publico()
    st.stop()


# ==============================================================================
# 📦 FUNÇÕES CACHED (nível de módulo — nunca dentro de condicionais)
# ==============================================================================
@st.cache_data(ttl=3600)
def load_niver_geral():
    try:
        from database import buscar_alunos_geral
        df = buscar_alunos_geral("")
        df["dt"] = pd.to_datetime(df["data_nascimento"], errors="coerce")
        df = df.dropna(subset=["dt"]).copy()
        df["dia"] = df["dt"].dt.day
        df["mes"] = df["dt"].dt.month
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def load_frequencia_ultima_presenca():
    """Retorna DataFrame com colunas [id, ultima_presenca] — máx data_aula PRESENTE por aluno."""
    try:
        res = (
            supabase.from_("frequencia")
            .select("aluno_id, data_aula, status")
            .eq("status", "PRESENTE")
            .limit(50000)
            .execute()
        )
        if not res.data:
            return pd.DataFrame(columns=["id", "ultima_presenca"])
        df_f = pd.DataFrame(res.data)
        df_f["data_aula"] = pd.to_datetime(df_f["data_aula"], errors="coerce")
        ultima = df_f.groupby("aluno_id")["data_aula"].max().reset_index()
        ultima.columns = ["id", "ultima_presenca"]
        return ultima
    except Exception:
        return pd.DataFrame(columns=["id", "ultima_presenca"])


# ==============================================================================
# 🛡️ MÓDULO DE SEGURANÇA E SESSÃO (8 HORAS)
# ==============================================================================
def gerar_captcha():
    st.session_state.captcha_n1 = random.randint(1, 10)
    st.session_state.captcha_n2 = random.randint(1, 10)
    st.session_state.captcha_result = (
        st.session_state.captcha_n1 + st.session_state.captcha_n2
    )


def inicializar_sessao():
    chaves = {
        "usuario_logado": False,
        "usuario_nome": "",
        "usuario_email": "",
        "perfil": "Visitante",
        "menu_atual": "Principal",
        "auth_tab": "in",
        "aluno_prontuario": None,
        "ultimo_acesso": time.time(),
        "admin_liberado": False,
    }
    for k, v in chaves.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if "captcha_result" not in st.session_state:
        gerar_captcha()


inicializar_sessao()

if st.session_state.usuario_logado:
    if time.time() - st.session_state.ultimo_acesso > 28800:
        st.session_state.clear()
        st.session_state.alerta_expiracao = "⚠️ A sua sessão expirou por medida de segurança após um longo período de inatividade. Por favor, acesse novamente."
        st.rerun()

    st.session_state.ultimo_acesso = time.time()

# ==============================================================================
# 🎨 CSS PRIME — MINIMALISTA & EXCELÊNCIA (TEMA CLARO BASE)
# ==============================================================================
st.markdown(
    """
<style>
/* ── BASE ──────────────────────────────────────────────────────────────────── */
#MainMenu, footer { visibility: hidden; }
[data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.block-container {
    padding-top: 1rem !important;
    max-width: 1300px;
    padding-bottom: 74px !important;
}
.stApp {
    background: linear-gradient(160deg,#EEF2FF 0%,#E8EEF8 45%,#F0F4FF 100%) !important;
}

/* ── CARD DO LOGIN ──────────────────────────────────────────────────────────── */
div[data-testid="column"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border-radius: 20px !important;
    box-shadow: 0 28px 56px rgba(10,37,64,.13), 0 6px 16px rgba(10,37,64,.07) !important;
    border: 1px solid rgba(226,232,240,.8) !important;
    border-top: none !important;
    padding: 0 !important;
    overflow: hidden !important;
}
div[data-testid="column"] > div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}

/* ── INPUTS ─────────────────────────────────────────────────────────────────── */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    border-radius: 10px !important;
    border: 1.5px solid #E2E8F0 !important;
    background: #F8FAFC !important;
    transition: all .2s ease !important;
}
div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
    border-color: #0056b3 !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3px rgba(0,86,179,.08) !important;
}
div[data-baseweb="input"] input { font-size: 14px !important; padding: 10px 14px !important; }

/* ── BOTÕES PRIMARY ─────────────────────────────────────────────────────────── */
button[kind="primaryFormSubmit"], button[kind="primary"] {
    background: linear-gradient(135deg,#0056b3 0%,#0072e5 100%) !important;
    color: white !important; border: none !important;
    padding: 18px 15px !important; font-weight: 700 !important;
    font-size: 14px !important; border-radius: 10px !important;
    text-transform: uppercase; letter-spacing: 1.2px;
    width: 100% !important; transition: all .25s ease !important;
    box-shadow: 0 4px 14px rgba(0,86,179,.28) !important;
    margin-top: 6px !important;
}
button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover {
    background: linear-gradient(135deg,#004494 0%,#0056b3 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 22px rgba(0,86,179,.34) !important;
}

/* ── BOTÕES SECONDARY ───────────────────────────────────────────────────────── */
button[kind="secondary"] {
    background: #F8FAFC !important; border: 1.5px solid #E2E8F0 !important;
    color: #475569 !important; border-radius: 10px !important;
    font-weight: 600 !important; font-size: 13px !important;
    transition: all .2s ease !important;
}
button[kind="secondary"]:hover {
    background: #EEF2FF !important; border-color: #C7D2FE !important;
    color: #0056b3 !important;
}

/* ── CAPTCHA ────────────────────────────────────────────────────────────────── */
.captcha-box {
    display: flex; align-items: center; justify-content: center;
    background: #F0F7FF; border: 1.5px solid #BFDBFE;
    border-radius: 10px; height: 44px;
    color: #1E3A8A; font-weight: 800; font-size: 14px; letter-spacing: .5px;
}

/* ── LINKS PÚBLICOS ─────────────────────────────────────────────────────────── */
.pub-pill {
    display: flex; align-items: center; justify-content: center;
    gap: 5px; padding: 9px 12px;
    background: #F8FAFC; border: 1px solid #E2E8F0;
    color: #475569; border-radius: 8px; font-size: 12px; font-weight: 600;
    text-decoration: none; transition: all .2s ease;
}
.pub-pill:hover { background: #EEF2FF; color: #0056b3; border-color: #C7D2FE; }

/* ── RODAPÉ FIXO ────────────────────────────────────────────────────────────── */
.rodape-prime {
    position: fixed; bottom: 0; left: 0; width: 100%;
    background: rgba(10,37,64,.97); backdrop-filter: blur(8px);
    color: rgba(255,255,255,.65); text-align: center;
    padding: 9px 20px; z-index: 999; font-size: 11.5px;
    border-top: 1px solid rgba(255,255,255,.07);
}
.rodape-prime strong { color: #fff; }
.rodape-prime a { color: #94A3B8; text-decoration: none; margin: 0 6px; transition: .2s; }
.rodape-prime a:hover { color: #60A5FA; }

/* ── BARRA NAV (RADIO PILLS) ────────────────────────────────────────────────── */
div[role="radiogroup"] {
    background: #FFFFFF !important; padding: 7px 16px !important;
    border-radius: 14px !important; gap: 3px !important; align-items: center !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.05) !important; border: 1px solid #E2E8F0 !important;
    margin-bottom: 16px !important; margin-top: 0 !important;
    justify-content: flex-end !important;
}
div[role="radiogroup"]::before {
    content: "🏃 IMBRA"; color: #0056b3; font-size: 16px; font-weight: 900;
    margin-right: auto; letter-spacing: -.5px;
}
div[role="radiogroup"] label {
    background: transparent !important; border: none !important;
    border-radius: 8px !important; padding: 5px 10px !important;
    transition: all .18s ease !important; margin: 0 !important;
}
div[role="radiogroup"] label p {
    color: #64748B !important; font-weight: 600 !important;
    font-size: 12px !important; margin: 0 !important;
}
div[role="radiogroup"] label:hover { background: #F1F5F9 !important; }
div[role="radiogroup"] label[data-checked="true"] {
    background: #0056b3 !important;
    box-shadow: 0 2px 8px rgba(0,86,179,.22) !important;
}
div[role="radiogroup"] label[data-checked="true"] p {
    color: #FFFFFF !important; font-weight: 700 !important;
}

/* ── ATALHOS DO DASHBOARD ───────────────────────────────────────────────────── */
.stButton button, .stLinkButton a {
    border-radius: 12px !important; font-weight: 700 !important;
    font-size: 13px !important; letter-spacing: .2px;
}
</style>
""",
    unsafe_allow_html=True,
)

# CSS do tema injeta SEMPRE (antes do check de login)
injetar_css_tema()

# ==============================================================================
# 🔐 PORTAL DE ACESSO — PRIME
# ==============================================================================
if not st.session_state.usuario_logado:
    # Toggle de tema no canto superior direito do login
    _cl, _ct = st.columns([6, 1])
    with _ct:
        _toggle_tema_ui(key_suffix="login")

    st.markdown("<div style='min-height:3vh;'></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1.05, 1])

    with col_c:
        if "alerta_expiracao" in st.session_state:
            st.warning(st.session_state.pop("alerta_expiracao"))

        with st.container(border=True):
            # ── HEADER ESCURO COM LOGO ──────────────────────────────────────
            from utils.identidade import (
                get_config as _gc_l,
                get_logo_data_url as _gld_l,
            )

            _cfg_l = _gc_l()
            _logo_b64 = _gld_l(_cfg_l.get("logo_principal", "logo-imbra.png"))
            _logo_html = (
                f'<img src="{_logo_b64}" style="height:52px;object-fit:contain;'
                f'filter:brightness(0) invert(1);margin-bottom:8px;">'
                if _logo_b64
                else '<div style="font-size:38px;margin-bottom:8px;">🏃‍♂️</div>'
            )
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#0A2540 0%,#1a3a5c 100%);
                              padding:26px 32px 22px;text-align:center;margin:-1px -1px 0;">
                    {_logo_html}
                    <h2 style="color:#FFFFFF;margin:0;font-size:13px;font-weight:800;
                               letter-spacing:.2px;line-height:1.3;white-space:nowrap;">
                        {_cfg_l.get("titulo_projeto", "ESPORTE E SAÚDE NA COMUNIDADE")}
                    </h2>
                    <p style="color:rgba(255,255,255,.72);font-size:12px;margin:6px 0 2px;
                              font-weight:500;letter-spacing:.1px;">
                        Entre com suas credenciais institucionais
                    </p>
                    <p style="color:rgba(255,255,255,.38);font-size:10px;margin:2px 0 0;
                              text-transform:uppercase;letter-spacing:2.5px;">
                        Gestão Inteligente MoveRight®
                    </p>
                </div>""",
                unsafe_allow_html=True,
            )

            # ── CORPO DO CARD ───────────────────────────────────────────────
            st.markdown("<div style='padding:22px 28px 20px;'>", unsafe_allow_html=True)

            if st.session_state.auth_tab == "in":
                with st.form("login_form"):
                    email = st.text_input(
                        "E-MAIL",
                        placeholder="exemplo@mudabrasil.org",
                        key="l_email",
                    )
                    senha = st.text_input(
                        "SENHA",
                        type="password",
                        placeholder="••••••••",
                        key="l_pwd",
                    )
                    col_cap, col_resp = st.columns([1.25, 1])
                    with col_cap:
                        st.markdown(
                            f"<div class='captcha-box'>🛡️ "
                            f"{st.session_state.captcha_n1} + "
                            f"{st.session_state.captcha_n2} = ?</div>",
                            unsafe_allow_html=True,
                        )
                    with col_resp:
                        resp = st.text_input(
                            "Resultado",
                            label_visibility="collapsed",
                            placeholder="Resposta",
                            key="l_cap",
                        )
                    btn_login = st.form_submit_button(
                        "ENTRAR  →", type="primary", use_container_width=True
                    )

                if btn_login:
                    if resp.strip() == str(st.session_state.captcha_result):
                        ok, user = autenticar_usuario(email, senha)
                        if ok:
                            st.session_state.usuario_logado = True
                            st.session_state.usuario_nome = user.get("nome")
                            st.session_state.usuario_email = email
                            st.session_state.email_usuario = email
                            st.session_state.perfil = (
                                "SuperAdmin"
                                if email.lower() == ADMIN_MASTER.lower()
                                else "Admin"
                            )
                            st.rerun()
                        else:
                            st.error("❌ Credenciais inválidas.")
                            gerar_captcha()
                    else:
                        st.error("❌ Verificação incorreta.")
                        gerar_captcha()
                        time.sleep(1)
                        st.rerun()

                st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
                cb1, cb2 = st.columns(2)
                with cb1:
                    if st.button(
                        "👤 Novo Operador", use_container_width=True, type="secondary"
                    ):
                        st.session_state.auth_tab = "up"
                        st.rerun()
                with cb2:
                    if st.button(
                        "🔑 Recuperar Senha", use_container_width=True, type="secondary"
                    ):
                        st.session_state.auth_tab = "forgot"
                        st.rerun()

                st.markdown(
                    "<p style='text-align:center;color:#94A3B8;font-size:11px;"
                    "margin:10px 0 2px;'>🔒 Acesso seguro — dados protegidos</p>"
                    "<hr style='border:none;border-top:1px solid #F1F5F9;margin:10px 0;'>",
                    unsafe_allow_html=True,
                )
                cp, cq = st.columns(2)
                with cp:
                    st.markdown(
                        '<a href="/?rota=inscricao" target="_self" class="pub-pill">'
                        "➕ Novo Aluno</a>",
                        unsafe_allow_html=True,
                    )
                with cq:
                    st.markdown(
                        '<a href="/?rota=pesquisa" target="_self" class="pub-pill">'
                        "⭐ Avaliar Projeto</a>",
                        unsafe_allow_html=True,
                    )

            elif st.session_state.auth_tab == "up":
                if st.button("← Voltar", type="secondary"):
                    st.session_state.auth_tab = "in"
                    st.rerun()
                st.info("Apenas coordenadores podem criar contas de acesso.", icon="ℹ️")
                with st.form("reg_form"):
                    n = st.text_input("Nome Completo")
                    e = st.text_input("E-mail Institucional")
                    p = st.text_input("Criar Senha", type="password")
                    if st.form_submit_button(
                        "CRIAR CONTA", type="primary", use_container_width=True
                    ):
                        sucesso, msg = cadastrar_usuario_sistema(n, e, p)
                        if sucesso:
                            st.success(msg)
                            time.sleep(1)
                            st.session_state.auth_tab = "in"
                            st.rerun()
                        else:
                            st.error(msg)

            elif st.session_state.auth_tab == "forgot":
                if st.button("← Voltar", type="secondary"):
                    st.session_state.auth_tab = "in"
                    st.rerun()
                st.markdown(
                    "<p style='color:#0056b3;font-weight:700;margin:6px 0 2px;'>"
                    "🔑 Recuperar Acesso</p>"
                    "<p style='color:#64748B;font-size:12px;margin:0 0 10px;'>"
                    "Enviaremos instruções para o e-mail registado.</p>",
                    unsafe_allow_html=True,
                )
                with st.form("forgot_form"):
                    email_rec = st.text_input(
                        "E-mail de acesso",
                        placeholder="exemplo@mudabrasil.org",
                        key="r_email",
                    )
                    if st.form_submit_button(
                        "ENVIAR INSTRUÇÕES", type="primary", use_container_width=True
                    ):
                        sucesso, msg = recuperar_senha_usuario(email_rec.strip())
                        if sucesso:
                            st.success(f"✅ {msg}")
                            time.sleep(3)
                            st.session_state.auth_tab = "in"
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            st.markdown("</div>", unsafe_allow_html=True)

    # ── Rodapé do Login ─────────────────────────────────────────────────────
    from utils.identidade import get_config as _gcfg_login

    _lcfg = _gcfg_login()
    _links = []
    if _lcfg.get("site"):
        _links.append(
            f'<a href="https://{_lcfg["site"]}" target="_blank">🌐 {_lcfg["site"]}</a>'
        )
    if _lcfg.get("instagram"):
        _links.append(
            f'<a href="https://instagram.com/{_lcfg["instagram"].lstrip("@")}"'
            f' target="_blank">📸 {_lcfg["instagram"]}</a>'
        )
    if _lcfg.get("cnpj"):
        _links.append(f"CNPJ: {_lcfg['cnpj']}")
    st.markdown(
        f'<div class="rodape-prime">'
        f"<strong>{_lcfg.get('nome_organizacao', 'Instituto Muda Brasil')}</strong>"
        f"&nbsp;·&nbsp;{' &nbsp;|&nbsp; '.join(_links)}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ==============================================================================
# 🧭 NAVEGAÇÃO INTERNA E DASHBOARD
# ==============================================================================

# Executa as ferramentas de topo (Seletor de Tema e Botão do Drive) acima do menu principal
renderizar_seletor_tema()

menu = [
    "Principal",
    "Frequência",
    "Portal do Aluno",
    "Nova Matrícula",
    "Radar de Acolhimento",
    "Relatórios & BI",
    "Satisfação",
]
if st.session_state.perfil == "SuperAdmin":
    menu.extend(["Config"])
menu.append("Sair")


def format_nav(opt):
    mapa = {
        "Principal": "🏠 Início",
        "Frequência": "✅ Frequência",
        "Portal do Aluno": "🩺 Portal do Aluno",
        "Nova Matrícula": "📝 Nova Matrícula",
        "Radar de Acolhimento": "💙 Radar",
        "Relatórios & BI": "📊 Relatórios & BI",
        "Satisfação": "⭐ Satisfação",
        "Config": "⚙️ Config",
        "Sair": "🔓 Sair",
    }
    return mapa.get(opt, opt)


st.radio(
    "Nav",
    menu,
    format_func=format_nav,
    horizontal=True,
    key="nav",
    on_change=lambda: st.session_state.update({"menu_atual": st.session_state.nav}),
    label_visibility="collapsed",
)
if st.session_state.nav == "Sair":
    st.session_state.clear()
    st.rerun()

# --- DASHBOARD PRINCIPAL ---
if st.session_state.menu_atual == "Principal":
    # ── CSS Global do Dashboard ─────────────────────────────────────────────
    st.markdown("""
<style>
.hg-avatar-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}
.hg-avatar {
  display: block;
  width: 42px !important;
  height: 42px !important;
  min-width: 42px;
  min-height: 42px;
  max-width: 42px;
  max-height: 42px;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  object-fit: cover;
  object-position: center center;
  flex-shrink: 0;
  box-shadow: 0 0 0 2.5px #3B82F6, 0 2px 8px rgba(59,130,246,0.25);
  transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.25s ease;
  cursor: zoom-in;
}
.hg-avatar:hover {
  transform: scale(3.5);
  box-shadow: 0 0 0 2.5px #3B82F6, 0 12px 36px rgba(0,0,0,0.5);
  z-index: 9999;
  position: relative;
}
.hg-initials {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  min-width: 42px;
  min-height: 42px;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(135deg, #3B82F6, #06B6D4);
  color: #fff;
  font-weight: 900;
  font-size: 14px;
  box-shadow: 0 0 0 2.5px #3B82F6, 0 2px 8px rgba(59,130,246,0.2);
}
.hg-niver-hoje  { color: #10B981; font-weight: 800; }
.hg-niver-breve { color: #F59E0B; font-weight: 700; }
.hg-niver-passou{ color: #94A3B8; }
</style>""", unsafe_allow_html=True)

    # ── Cabeçalho: Saudação + Data + Relógio SP ─────────────────────────────
    _hoje = datetime.date.today()
    _ds = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
           "Sexta-feira", "Sábado", "Domingo"][_hoje.weekday()]
    _meses_pt_full = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                      "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    _meses_abrev   = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    _nome_curto = (
        st.session_state.usuario_nome.split()[0]
        if st.session_state.usuario_nome else "Gestor"
    )

    _col_greet, _col_clock = st.columns([3, 1], gap="small", vertical_alignment="center")

    with _col_greet:
        st.markdown(
            f"<div style='margin-bottom:4px;'>"
            f"<h3 style='color:#0A2540;margin:0;font-size:1.2rem;font-weight:800;line-height:1.3;'>"
            f"Olá, {_nome_curto} 👋</h3>"
            f"<p style='color:#475569;font-size:13px;font-weight:600;margin:2px 0 0;'>"
            f"📅 {_ds}, {_hoje.day:02d} de {_meses_pt_full[_hoje.month-1]} de {_hoje.year}"
            f"&nbsp;&nbsp;"
            f"<span style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:6px;"
            f"padding:2px 8px;font-size:11px;font-weight:700;color:#1E40AF;'>"
            f"● {st.session_state.perfil}</span>"
            f"</p></div>",
            unsafe_allow_html=True,
        )

    with _col_clock:
        import streamlit.components.v1 as _stc
        _stc.html(
            """
<div style='text-align:right; padding:4px 0; font-family:sans-serif;'>
  <div id="ck"
       style='font-size:1.65rem; font-weight:900; color:#1E40AF;
              font-family:monospace; letter-spacing:2px; line-height:1;'>
    --:--:--
  </div>
  <div style='font-size:10px; color:#94A3B8; font-weight:600; margin-top:2px;'>
    🕒 Horário de São Paulo
  </div>
</div>
<script>
(function(){
  function tick(){
    var el = document.getElementById('ck');
    if(!el){ setTimeout(tick,150); return; }
    el.textContent = new Date().toLocaleTimeString('pt-BR',
      {timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit',second:'2-digit'});
  }
  tick();
  setInterval(tick, 1000);
})();
</script>""",
            height=58,
            scrolling=False,
        )

    st.markdown("<hr style='margin:8px 0 10px;border-color:#E2E8F0;'/>", unsafe_allow_html=True)

    # ── Layout principal: Grid (esq) + Avaliações (dir) ─────────────────────
    _col_grid, _col_agenda = st.columns([3, 1], gap="large")

    # ════════════════════════════════════════════════
    # COLUNA DIREITA — Próximas Avaliações (sempre visível)
    # ════════════════════════════════════════════════
    with _col_agenda:
        st.markdown(
            "<p style='font-weight:800;color:#0A2540;font-size:0.95rem;margin:0 0 8px;'>"
            "🗓️ Próximas Avaliações</p>",
            unsafe_allow_html=True,
        )
        _agendamentos = get_agendamentos_pendentes(limite=8)
        if _agendamentos:
            for _ag in _agendamentos:
                _nm = ((_ag.get("alunos") or {}).get("nome") or _ag.get("nome_aluno") or "—")
                _hr = _ag.get("horario") or _ag.get("data_hora") or "—"
                _dt = str(_ag.get("data") or "")
                _dt_fmt = ""
                if _dt and len(_dt) >= 10:
                    try:
                        _dp = datetime.date.fromisoformat(_dt[:10])
                        _dt_fmt = f"{_dp.day:02d}/{_dp.month:02d}"
                    except Exception:
                        _dt_fmt = _dt[:5]
                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size:12px;line-height:1.4;'>"
                        f"<span style='font-weight:700;color:#1E40AF;'>🕒 {_hr}"
                        f"{(' · ' + _dt_fmt) if _dt_fmt else ''}</span><br>"
                        f"<span style='color:#0F172A;'>{_nm}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("Agenda livre ✅", icon=None)

    # ════════════════════════════════════════════════
    # COLUNA ESQUERDA — Grid de Alunos
    # ════════════════════════════════════════════════
    with _col_grid:
        from database import buscar_alunos_geral
        _hg_c_titulo, _hg_c_busca, _hg_c_turma = st.columns(
            [1.4, 2.5, 1.8], vertical_alignment="bottom", gap="small"
        )
        _hg_c_titulo.markdown(
            "<p style='font-weight:800;color:#0A2540;font-size:1.05rem;margin:0;'>👥 Alunos Ativos</p>",
            unsafe_allow_html=True,
        )
        _hg_busca = _hg_c_busca.text_input(
            "Buscar:", placeholder="🔍 Nome ou turma…",
            label_visibility="collapsed", key="hg_busca"
        )

        # Carregar dados
        _df_alunos = buscar_alunos_geral("")
        _df_ultima  = load_frequencia_ultima_presenca()

        if not _df_alunos.empty:
            # Merge com última presença
            if not _df_ultima.empty:
                _df_hg = _df_alunos.merge(_df_ultima, on="id", how="left")
            else:
                _df_hg = _df_alunos.copy()
                _df_hg["ultima_presenca"] = pd.NaT

            _df_hg["ultima_presenca"] = pd.to_datetime(_df_hg["ultima_presenca"], errors="coerce")

            # Birthday
            _df_hg["_dt_nasc"] = pd.to_datetime(_df_hg["data_nascimento"], errors="coerce")
            _df_hg["_dia_n"]   = _df_hg["_dt_nasc"].dt.day
            _df_hg["_mes_n"]   = _df_hg["_dt_nasc"].dt.month

            # Filtro de turma
            _turmas_disp = sorted(
                [t for t in _df_hg["turma"].dropna().unique().tolist() if str(t).strip()],
                key=str
            )
            _hg_turma = _hg_c_turma.selectbox(
                "Turma:", ["Todas"] + _turmas_disp,
                label_visibility="collapsed", key="hg_turma"
            )

            # Aplicar filtros
            _df_grid = _df_hg.copy()
            if _hg_busca and len(_hg_busca.strip()) >= 3:
                _b = _hg_busca.strip().lower()
                _df_grid = _df_grid[
                    _df_grid["nome"].str.lower().str.contains(_b, na=False) |
                    _df_grid["turma"].str.lower().str.contains(_b, na=False)
                ]
            if _hg_turma != "Todas":
                _df_grid = _df_grid[_df_grid["turma"] == _hg_turma]

            # Ordenação dinâmica
            if "hg_sort_col" not in st.session_state:
                st.session_state.hg_sort_col = "nome"
                st.session_state.hg_sort_asc = True
            _sc = st.session_state.get("hg_sort_col", "nome")
            _sa = st.session_state.get("hg_sort_asc", True)
            if _sc == "aniversario":
                _df_grid = _df_grid.sort_values(
                    ["_mes_n", "_dia_n"], ascending=_sa, na_position="last"
                )
            elif _sc in _df_grid.columns:
                _df_grid = _df_grid.sort_values(_sc, ascending=_sa, na_position="last")
            else:
                _df_grid = _df_grid.sort_values("nome")
            _df_grid = _df_grid.reset_index(drop=True)

            # Paginação com botões ◀ ▶
            _hg_ppp   = 20
            _hg_total = max(1, math.ceil(len(_df_grid) / _hg_ppp))
            if "hg_pg" not in st.session_state:
                st.session_state.hg_pg = 1
            # Reset para pág 1 quando filtro muda
            if st.session_state.get("hg_busca_prev") != _hg_busca or \
               st.session_state.get("hg_turma_prev") != _hg_turma:
                st.session_state.hg_pg = 1
                st.session_state.hg_busca_prev = _hg_busca
                st.session_state.hg_turma_prev = _hg_turma
            st.session_state.hg_pg = max(1, min(st.session_state.hg_pg, _hg_total))
            _hg_pg  = st.session_state.hg_pg
            _hg_ini = (_hg_pg - 1) * _hg_ppp
            _df_pag = _df_grid.iloc[_hg_ini: _hg_ini + _hg_ppp]

            # Barra de info + navegação
            _pc1, _pc2, _pc3, _pc4 = st.columns([3, 0.6, 0.6, 1], gap="small",
                                                  vertical_alignment="center")
            _pc1.caption(f"{len(_df_grid)} aluno(s) · pág {_hg_pg}/{_hg_total}")
            if _pc2.button("◀", key="hg_prev", disabled=(_hg_pg <= 1),
                           use_container_width=True):
                st.session_state.hg_pg -= 1
                st.rerun()
            if _pc3.button("▶", key="hg_next", disabled=(_hg_pg >= _hg_total),
                           use_container_width=True):
                st.session_state.hg_pg += 1
                st.rerun()

            # ── Cabeçalho das colunas (clicável para ordenar) ──────────
            _h0, _h1, _h2, _h3, _h4, _h5 = st.columns(
                [0.5, 3.2, 1.6, 1.5, 1.8, 0.9], gap="small"
            )
            _h0.markdown(" ", unsafe_allow_html=True)
            _h5.markdown(" ", unsafe_allow_html=True)

            def _sort_btn(col_widget, label, sort_key):
                _ativo = (st.session_state.get("hg_sort_col") == sort_key)
                _seta  = (" ▲" if st.session_state.get("hg_sort_asc", True) else " ▼") if _ativo else ""
                if col_widget.button(
                    f"{label}{_seta}",
                    key=f"hdr_{sort_key}",
                    use_container_width=True,
                    help=f"Ordenar por {label}",
                ):
                    if st.session_state.get("hg_sort_col") == sort_key:
                        st.session_state.hg_sort_asc = not st.session_state.get("hg_sort_asc", True)
                    else:
                        st.session_state.hg_sort_col = sort_key
                        st.session_state.hg_sort_asc = True
                    st.session_state.hg_pg = 1
                    st.rerun()

            _sort_btn(_h1, "Nome",           "nome")
            _sort_btn(_h2, "Turma",          "turma")
            _sort_btn(_h3, "🎂 Aniversário", "aniversario")
            _sort_btn(_h4, "⏱ Última Pres.", "ultima_presenca")

            # ── Linhas do Grid ─────────────────────────────────────────
            _hoje_hg   = datetime.date.today()
            _hoje_dia  = _hoje_hg.day
            _hoje_mes  = _hoje_hg.month
            _meses_abr = ["","jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]

            for _, _r in _df_pag.iterrows():
                with st.container(border=True):
                    _ca, _cb, _cc, _cd, _ce, _cf = st.columns(
                        [0.5, 3.2, 1.6, 1.5, 1.8, 0.9], gap="small",
                        vertical_alignment="center"
                    )

                    # Foto
                    _foto = str(_r.get("url_foto") or "").strip()
                    _inic = "".join(p[0].upper() for p in str(_r["nome"]).split()[:2] if p)
                    if _foto.startswith("http"):
                        _av_html = (
                            f'<div class="hg-avatar-wrap">'
                            f'<img class="hg-avatar" src="{_foto}" alt="{_inic}" '
                            f"onerror=\"this.outerHTML='<div class=hg-initials>{_inic}</div>'\">"
                            f'</div>'
                        )
                    else:
                        _av_html = f'<div class="hg-avatar-wrap"><div class="hg-initials">{_inic}</div></div>'
                    with _ca:
                        st.markdown(_av_html, unsafe_allow_html=True)

                    # Nome
                    _cb.markdown(
                        f"<span style='font-size:13.5px;font-weight:700;color:#0F172A;'>"
                        f"{_r['nome']}</span>",
                        unsafe_allow_html=True,
                    )

                    # Turma
                    _turma_v = str(_r.get("turma") or "—").strip() or "—"
                    _cc.markdown(
                        f"<span style='font-size:12px;color:#475569;'>{_turma_v}</span>",
                        unsafe_allow_html=True,
                    )

                    # Aniversário
                    _dia_n = _r.get("_dia_n")
                    _mes_n = _r.get("_mes_n")
                    if pd.notna(_dia_n) and pd.notna(_mes_n):
                        _dia_n, _mes_n = int(_dia_n), int(_mes_n)
                        _nasc_str = f"{_dia_n:02d}/{_meses_abr[_mes_n]}"
                        if _mes_n == _hoje_mes and _dia_n == _hoje_dia:
                            _niver_html = f"<span class='hg-niver-hoje'>🎉 {_nasc_str} HOJE!</span>"
                        elif (_mes_n > _hoje_mes) or (_mes_n == _hoje_mes and _dia_n > _hoje_dia):
                            _niver_html = f"<span class='hg-niver-breve'>⏳ {_nasc_str}</span>"
                        else:
                            _niver_html = f"<span class='hg-niver-passou'>🎈 {_nasc_str}</span>"
                    else:
                        _niver_html = "<span style='color:#CBD5E1;'>—</span>"
                    _cd.markdown(
                        f"<span style='font-size:12px;'>{_niver_html}</span>",
                        unsafe_allow_html=True,
                    )

                    # Última Presença
                    _up = _r.get("ultima_presenca")
                    _dias_sem = ["seg","ter","qua","qui","sex","sáb","dom"]
                    if pd.notna(_up):
                        _up_dt   = pd.Timestamp(_up).date()
                        _up_dias = (_hoje_hg - _up_dt).days
                        _up_cor  = "#10B981" if _up_dias <= 7 else ("#F59E0B" if _up_dias <= 30 else "#EF4444")
                        _up_txt  = _up_dt.strftime("%d/%m/%y")
                        _up_dsem = _dias_sem[_up_dt.weekday()]
                        _up_html = (
                            f"<span style='font-size:12px;font-weight:700;color:{_up_cor};'>"
                            f"{_up_txt}</span>"
                            f"<span style='font-size:10px;color:#94A3B8;margin-left:4px;'>"
                            f"{_up_dsem} · {_up_dias}d</span>"
                        )
                    else:
                        _up_html = "<span style='font-size:12px;color:#CBD5E1;'>Sem registro</span>"
                    _ce.markdown(_up_html, unsafe_allow_html=True)

                    # Botão Ficha
                    with _cf:
                        if st.button(
                            "🩺", key=f"hg_{_r['id']}",
                            use_container_width=True, help="Abrir Prontuário"
                        ):
                            from database import buscar_aluno_por_id
                            _aluno_fresh = buscar_aluno_por_id(_r["id"]) or _r.to_dict()
                            st.session_state.aluno_prontuario = _aluno_fresh
                            st.session_state.origem_prontuario = "Principal"
                            st.session_state.menu_atual = "Portal do Aluno"
                            st.rerun()
        else:
            st.info("Nenhum aluno ativo encontrado.")

# ==============================================================================
# 🚀 ROTEAMENTO DE VISTAS
# ==============================================================================
elif st.session_state.menu_atual == "Frequência":
    _c_freq_titulo, _c_freq_btn = st.columns([6, 1], vertical_alignment="center")
    with _c_freq_btn:
        if st.button("📸 Conf. Facial", use_container_width=True, help="Conferência de Presença por Foto"):
            st.session_state.menu_atual = "Conferência Facial"
            st.rerun()
    from views.frequencia_view import tela_frequencia
    tela_frequencia()

elif st.session_state.menu_atual == "Radar de Acolhimento":
    from views.radar_acolhimento_view import tela_radar_acolhimento

    tela_radar_acolhimento()

elif st.session_state.menu_atual == "Nova Matrícula":
    if "rota" in st.query_params:
        st.query_params.clear()
    from views.inscricao_publica_view import tela_inscricao_publica_move_right

    st.markdown("### 📝 Cadastro Oficial de Novo Aluno")

    try:
        _host_nm = st.context.headers.get("host", "")
        _link_inscricao = f"https://{_host_nm}/?rota=inscricao"
    except Exception:
        _link_inscricao = "/?rota=inscricao"

    with st.container(border=True):
        _c_lnk, _c_info = st.columns([3, 2], vertical_alignment="center")
        with _c_lnk:
            st.markdown("**🔗 Link de Auto-Inscrição do Aluno**")
            st.caption("Envie ao novo aluno para que ele preencha o formulário por conta própria.")
        with _c_info:
            st.code(_link_inscricao, language=None)

    st.info(
        "Preencha os dados da ficha com calma. Ao concluir, o aluno estará imediatamente disponível no sistema para marcação de presença."
    )
    tela_inscricao_publica_move_right()

elif st.session_state.menu_atual == "Portal do Aluno":
    _col_portal, _col_ficha_portal = st.columns([6, 1], vertical_alignment="center")
    with _col_ficha_portal:
        if st.button("🖨️ Ficha", use_container_width=True, help="Central de impressão de fichas de matrícula"):
            st.session_state.menu_atual = "Ficha de Matrícula"
            st.rerun()
    if st.session_state.aluno_prontuario:
        from views.prontuario_ficha import renderizar_ficha
        renderizar_ficha()
    else:
        from views.prontuario_dashboard import renderizar_dashboard
        renderizar_dashboard()

elif st.session_state.menu_atual in ("Relatórios & BI", "BI Prime", "Relatórios"):
    _col_rel, _col_ficha_rel = st.columns([6, 1], vertical_alignment="center")
    with _col_ficha_rel:
        if st.button("🖨️ Ficha", use_container_width=True, key="ficha_btn_rel", help="Central de impressão de fichas de matrícula"):
            st.session_state.menu_atual = "Ficha de Matrícula"
            st.rerun()
    _aba_rel = st.tabs(["📋 Relatórios", "📊 BI Dashboard", "👤 BI Individual"])
    with _aba_rel[0]:
        from views.relatorio_view import tela_relatorio
        tela_relatorio()
    with _aba_rel[1]:
        from views.bi_dashboard_view import render_bi_dashboard
        render_bi_dashboard()
    with _aba_rel[2]:
        from views.bi_individual_view import render_bi_individual
        render_bi_individual()

elif st.session_state.menu_atual == "Satisfação":
    from views.relatorio_satisfacao_view import tela_relatorio_prime_satisfacao

    tela_relatorio_prime_satisfacao()

elif st.session_state.menu_atual == "Ficha de Matrícula":
    try:
        from views.ficha_aluno_view import tela_impressao_ficha

        tela_impressao_ficha()
    except:
        st.error("⚠️ Crie o ficheiro `ficha_aluno_view.py` na pasta `views`.")

elif st.session_state.menu_atual in (
    "Config", "Conferência Facial",
    "Turmas", "Mensagens", "Identidade Visual", "Backup", "Mesclar Fichas",
):
    if st.session_state.menu_atual == "Conferência Facial":
        _idx_cfg = None
    else:
        _idx_cfg = {
            "Config": 0, "Turmas": 0, "Mensagens": 1,
            "Identidade Visual": 2, "Backup": 3, "Mesclar Fichas": 4,
        }.get(st.session_state.menu_atual, 0)

    if st.session_state.menu_atual == "Conferência Facial":
        from views.conferencia_facial_view import tela_conferencia_facial
        tela_conferencia_facial()
    else:
        _aba_cfg = st.tabs(
            ["🏫 Turmas", "💬 Mensagens", "🎂 Aniversários", "🎨 Identidade Visual", "🛠️ Admin", "🔀 Mesclar Fichas"]
        )
        with _aba_cfg[0]:
            from views.turmas_view import tela_gestao_turmas
            tela_gestao_turmas()
        with _aba_cfg[1]:
            from views.templates_view import tela_gestao_templates
            tela_gestao_templates()
        with _aba_cfg[2]:
            from views.config_niver_view import tela_config_niver
            tela_config_niver()
        with _aba_cfg[3]:
            from views.identidade_view import tela_identidade_visual
            tela_identidade_visual()
        with _aba_cfg[4]:
            from views.backup_view import tela_backup
            from database import ferramenta_reparacao_turmas
            tela_backup()
            st.markdown("---")
            ferramenta_reparacao_turmas()
        with _aba_cfg[5]:
            from views.merge_alunos_view import tela_merge_alunos
            tela_merge_alunos()

# ── Rodapé Fixo ─────────────────────────────────────────────────────────────
from utils.identidade import get_config as _gcfg_rodape

_rcfg = _gcfg_rodape()
_rlinks = []
if _rcfg.get("site"):
    _rlinks.append(
        f'<a href="https://{_rcfg["site"]}" target="_blank">🌐 {_rcfg["site"]}</a>'
    )
if _rcfg.get("instagram"):
    _rlinks.append(
        f'<a href="https://instagram.com/{_rcfg["instagram"].lstrip("@")}"'
        f' target="_blank">📸 {_rcfg["instagram"]}</a>'
    )
st.markdown(
    f'<div class="rodape-prime">'
    f"<strong>{_rcfg.get('nome_organizacao', 'Instituto Muda Brasil')}</strong>"
    f"&nbsp;·&nbsp; MoveRight Elite"
    f"{'&nbsp;&nbsp;' + '&nbsp;|&nbsp;'.join(_rlinks) if _rlinks else ''}"
    f"</div>",
    unsafe_allow_html=True,
)
