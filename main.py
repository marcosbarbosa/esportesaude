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
    load_frequencia_ultima_presenca,
    load_atestados_vencimento,
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

    # Esconde o indicador "Running..." (status widget) do Streamlit em todas as telas
    st.markdown(
        "<style>[data-testid='stStatusWidget']{display:none !important;}</style>",
        unsafe_allow_html=True,
    )

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
    """Renderiza Drive + Prestação de Contas + Seletor de Tema no topo do app."""
    col_vazia, col_drive, col_prest, col_tema = st.columns(
        [3.0, 2.5, 2.5, 2], vertical_alignment="center"
    )
    with col_drive:
        st.link_button(
            "📂 Abrir Google Drive",
            "https://drive.google.com/drive/u/7/my-drive",
            use_container_width=True,
            help="Acesse a pasta da nuvem para gerir as fotografias.",
        )
    with col_prest:
        st.link_button(
            "📁 Prestação de Contas",
            "https://drive.google.com/drive/folders/1TWP0Q3nwKpsDKmjWUrFC6uKBuvfmGpFC",
            use_container_width=True,
            help="Abra a pasta de Prestação de Contas para salvar os PDFs gerados.",
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
@st.cache_data(ttl=3600, show_spinner=False)
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


def _ebi_base_url():
    """URL pública do app (https://host) para montar links acionáveis no e-mail."""
    try:
        h = st.context.headers.get("host", "")
        if h:
            return f"https://{h}"
    except Exception:
        pass
    return ""


# ── Deep-link interno: links acionáveis vindos do Email BI ────────────────────
# (?ir=freq&d=YYYY-MM-DD  → tela de Frequência | ?ir=ficha&id=<id> → ficha do aluno)
_ir_dl = st.query_params.get("ir")
if _ir_dl in ("freq", "ficha", "triagem") and "_pending_deeplink" not in st.session_state:
    st.session_state["_pending_deeplink"] = {
        "ir": _ir_dl,
        "d": st.query_params.get("d", ""),
        "id": st.query_params.get("id", ""),
    }
    try:
        st.query_params.clear()
    except Exception:
        pass

if st.session_state.usuario_logado:
    if time.time() - st.session_state.ultimo_acesso > 28800:
        st.session_state.clear()
        st.session_state.alerta_expiracao = "⚠️ A sua sessão expirou por medida de segurança após um longo período de inatividade. Por favor, acesse novamente."
        st.rerun()

    st.session_state.ultimo_acesso = time.time()

    # ── Aplica deep-link interno após autenticação ─────────────────────────
    _dl = st.session_state.pop("_pending_deeplink", None)
    if _dl:
        if _dl.get("ir") == "freq":
            st.session_state.menu_atual = "Frequência"
            _d_dl = _dl.get("d", "")
            if _d_dl:
                try:
                    st.session_state["_freq_data_alvo"] = datetime.date.fromisoformat(_d_dl[:10])
                except Exception:
                    pass
            st.rerun()
        elif _dl.get("ir") == "ficha" and _dl.get("id"):
            try:
                from database import buscar_aluno_por_id
                _al_dl = buscar_aluno_por_id(_dl["id"])
            except Exception:
                _al_dl = None
            if _al_dl:
                st.session_state.aluno_prontuario = _al_dl
                st.session_state.origem_prontuario = "Principal"
                st.session_state.menu_atual = "Portal do Aluno"
            else:
                st.session_state["_deeplink_erro"] = "⚠️ Aluno do link não encontrado."
            st.rerun()
        elif _dl.get("ir") == "triagem":
            st.session_state.aluno_prontuario = None
            st.session_state.menu_atual = "Portal do Aluno"
            st.session_state["_abrir_triagem"] = True
            st.rerun()

    if st.session_state.get("_deeplink_erro"):
        st.warning(st.session_state.pop("_deeplink_erro"))

    # ── Email BI: verificação de envio agendado (1x por sessão) ────────────
    if not st.session_state.get("_ebi_checado"):
        st.session_state["_ebi_checado"] = True
        try:
            from utils.email_relatorio_config import (
                get_schedules, schedule_to_cfg, marcar_envio_realizado_schedule,
                get_config_ebi, verificar_e_marcar_envio_realizado,
            )
            from utils.email_relatorio import enviar_relatorio_bi
            from utils.identidade import get_config as _gid_ebi
            _nome_org_ebi = _gid_ebi().get("nome_organizacao", "Instituto Muda Brasil")
            _hoje_ebi = datetime.date.today()
            _schedules = get_schedules()
            if _schedules:
                # Multi-schedule: itera por todos os pacotes habilitados
                for _sched in _schedules:
                    if not _sched.get("habilitado"):
                        continue
                    if not _sched.get("emails_destino"):
                        continue
                    _prox_s = _sched.get("proximo_envio", "")
                    _devido_s = not _prox_s
                    if not _devido_s:
                        try:
                            _devido_s = datetime.date.fromisoformat(str(_prox_s)[:10]) <= _hoje_ebi
                        except Exception:
                            _devido_s = True
                    if _devido_s:
                        _cfg_s = schedule_to_cfg(_sched)
                        _ok_s, _ = enviar_relatorio_bi(_cfg_s, _nome_org_ebi, _ebi_base_url())
                        if _ok_s:
                            marcar_envio_realizado_schedule(_sched["id"], _cfg_s)
            else:
                # Fallback legado (configuracoes_sistema) enquanto não há schedules
                _ebi_cfg = get_config_ebi()
                _prox = _ebi_cfg.get("proximo_envio", "")
                _devido = not _prox
                if not _devido:
                    try:
                        _devido = datetime.date.fromisoformat(str(_prox)[:10]) <= _hoje_ebi
                    except Exception:
                        _devido = True
                if _devido and _ebi_cfg.get("habilitado") and _ebi_cfg.get("emails_destino"):
                    _ok_ebi, _ = enviar_relatorio_bi(_ebi_cfg, _nome_org_ebi, _ebi_base_url())
                    if _ok_ebi:
                        verificar_e_marcar_envio_realizado(_ebi_cfg)
        except Exception:
            pass

# ==============================================================================
# 🎨 CSS PRIME — MINIMALISTA & EXCELÊNCIA (TEMA CLARO BASE)
# ==============================================================================
st.markdown(
    """
<style>
/* ── BASE ──────────────────────────────────────────────────────────────────── */
#MainMenu, footer { visibility: hidden; }
[data-testid="stStatusWidget"]  { display: none !important; }
[data-testid="stHeader"]        { display: none !important; }
[data-testid="stToolbar"]       { display: none !important; }
[data-testid="stAppToolbar"]    { display: none !important; }
[data-testid="stDecoration"]    { display: none !important; }
.stAppToolbar                   { display: none !important; }
.stToolbar                      { display: none !important; }
#stDecoration                   { display: none !important; }
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
# 📅 CALENDÁRIO INSTITUCIONAL — Tela de gestão de Dias Sem Aula
# ==============================================================================

_SQL_MIGRACAO_EBI = """
CREATE TABLE IF NOT EXISTS email_bi_schedules (
  id               uuid         DEFAULT gen_random_uuid() PRIMARY KEY,
  nome             text         NOT NULL DEFAULT 'Pacote Principal',
  habilitado       boolean      NOT NULL DEFAULT false,
  frequencia       text         NOT NULL DEFAULT 'semanal',
  dia_semana       integer      NOT NULL DEFAULT 4,
  dia_mes          integer      NOT NULL DEFAULT 1,
  emails_destino   jsonb        NOT NULL DEFAULT '[]'::jsonb,
  modulos          jsonb        NOT NULL DEFAULT '{}'::jsonb,
  assunto_extra    text                  DEFAULT '',
  email_remetente  text                  DEFAULT '',
  email_senha_app  text                  DEFAULT '',
  base_url         text                  DEFAULT '',
  proximo_envio    date,
  ultimo_envio     timestamptz,
  total_envios     integer      NOT NULL DEFAULT 0,
  historico_envios jsonb        NOT NULL DEFAULT '[]'::jsonb,
  criado_em        timestamptz  NOT NULL DEFAULT now(),
  atualizado_em    timestamptz  NOT NULL DEFAULT now()
);

-- Desativa RLS (sistema interno — acesso via chave de serviço)
ALTER TABLE email_bi_schedules DISABLE ROW LEVEL SECURITY;
""".strip()


def _tela_email_bi():
    import pandas as _pd_ebi
    from utils.email_relatorio_config import (
        calcular_proximo_envio,
        get_schedules, salvar_schedule, excluir_schedule,
        migrar_legado_para_schedule, schedule_to_cfg,
        marcar_envio_realizado_schedule, _ler_schedules,
    )
    from utils.email_relatorio import enviar_relatorio_bi
    from database import get_emails_sistema

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    st.markdown("""
        <div style='background:#EFF6FF;border-left:4px solid #1D4ED8;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#1E3A8A;'>📧 Email BI — Relatório Gerencial Automático</strong><br>
            <span style='color:#1D4ED8;font-size:13px;'>
                Configure <strong>pacotes independentes</strong> de envio por e-mail.
                Cada pacote tem seus próprios destinatários, módulos e agendamento —
                com histórico completo de envios.
            </span>
        </div>
    """, unsafe_allow_html=True)

    # ── Verificar tabela ───────────────────────────────────────────────────
    schedules = get_schedules()
    if schedules is None:
        st.error("⚠️ Tabela `email_bi_schedules` não encontrada no banco de dados.")
        st.markdown(
            "Execute o SQL abaixo no **Supabase Dashboard → SQL Editor** "
            "e depois clique em **Confirmar**:"
        )
        st.code(_SQL_MIGRACAO_EBI, language="sql")
        if st.button("✅ Já executei — recarregar", key="ebi_migr_ok", type="primary"):
            _ler_schedules.clear()
            st.rerun()
        return

    # ── Auto-migração legada (1x por sessão) ──────────────────────────────
    if not schedules and not st.session_state.get("_ebi_migr_done"):
        if migrar_legado_para_schedule():
            _ler_schedules.clear()
            schedules = get_schedules() or []
        st.session_state["_ebi_migr_done"] = True

    emails_sistema = get_emails_sistema()

    # ── STATE MACHINE: lista ↔ editor ─────────────────────────────────────
    edit_id = st.session_state.get("ebi_edit_id")  # None | "new" | uuid

    # ══════════════════════════════════════════════════════════════════════
    # EDITOR
    # ══════════════════════════════════════════════════════════════════════
    if edit_id is not None:
        dados = {}
        if edit_id != "new":
            dados = next((s for s in schedules if s["id"] == edit_id), {})

        mod_def = dados.get("modulos") or {}
        if isinstance(mod_def, str):
            import json as _jj
            try:
                mod_def = _jj.loads(mod_def)
            except Exception:
                mod_def = {}

        emails_ja = dados.get("emails_destino") or []
        emails_sis_set = {u["email"] for u in emails_sistema}
        emails_externos_ja = [e for e in emails_ja if e not in emails_sis_set]

        titulo_ed = (
            f"📝 Editando: **{dados.get('nome', '—')}**"
            if edit_id != "new" else "📝 Novo Pacote de Envio"
        )
        st.markdown(f"### {titulo_ed}")

        with st.form(key=f"ebi_form_{edit_id}"):
            cn, ctog = st.columns([3, 2])
            nome_pct = cn.text_input(
                "Nome do pacote",
                value=dados.get("nome", "Pacote de Envio"),
                key=f"ebi_fn_{edit_id}",
            )
            habilitado = ctog.toggle(
                "Ativar envio automático",
                value=bool(dados.get("habilitado", False)),
                key=f"ebi_fh_{edit_id}",
                help="Quando ativo, o envio dispara automaticamente ao abrir o sistema na data agendada.",
            )

            # ── Agendamento ──────────────────────────────────────────────
            st.markdown("#### ⚙️ Agendamento")
            cfreq1, cfreq2 = st.columns(2)
            freq_opts = {"semanal": "Semanal", "quinzenal": "Quinzenal", "mensal": "Mensal"}
            freq_keys = list(freq_opts.keys())
            freq_atual = dados.get("frequencia", "semanal")
            frequencia = cfreq1.selectbox(
                "Frequência",
                options=freq_keys,
                index=freq_keys.index(freq_atual) if freq_atual in freq_keys else 0,
                format_func=lambda k: freq_opts[k],
                key=f"ebi_ff_{edit_id}",
            )
            dias_sem_nms = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            dsv = int(dados.get("dia_semana") or 4)
            dmv = int(dados.get("dia_mes") or 1)
            if frequencia in ("semanal", "quinzenal"):
                dia_semana_sel = cfreq2.selectbox(
                    "Dia da semana",
                    options=list(range(7)),
                    index=dsv if 0 <= dsv <= 6 else 4,
                    format_func=lambda i: dias_sem_nms[i],
                    key=f"ebi_fds_{edit_id}",
                )
                dia_mes_sel = dmv
            else:
                dia_semana_sel = dsv
                dia_mes_sel = cfreq2.number_input(
                    "Dia do mês (1–28)", min_value=1, max_value=28,
                    value=dmv, step=1, key=f"ebi_fdm_{edit_id}",
                )

            # ── Destinatários ────────────────────────────────────────────
            st.markdown("#### 📬 Destinatários e Remetente")
            if emails_sistema:
                st.markdown("**E-mails cadastrados no sistema** *(marque os que devem receber este pacote):*")
                cols_em = st.columns(2)
                emails_sis_sel = []
                for idx_u, u in enumerate(emails_sistema):
                    col_u = cols_em[idx_u % 2]
                    lbl_u = f"{u['nome']} — {u['email']}"
                    chk_key = f"ebi_u_{edit_id}_{u['email'].replace('@','_at_').replace('.','_')}"
                    if col_u.checkbox(lbl_u, value=(u["email"] in emails_ja), key=chk_key):
                        emails_sis_sel.append(u["email"])
            else:
                emails_sis_sel = []
                st.caption("Nenhum usuário cadastrado no sistema ainda.")

            st.markdown("**E-mails adicionais** *(externos, um por linha):*")
            externos_txt = st.text_area(
                "",
                value="\n".join(emails_externos_ja),
                placeholder="emailexterno@exemplo.com\noutro@exemplo.com",
                height=75,
                label_visibility="collapsed",
                key=f"ebi_fext_{edit_id}",
            )

            # ── Remetente ────────────────────────────────────────────────
            cre1, cre2 = st.columns(2)
            remetente = cre1.text_input(
                "Gmail remetente",
                value=dados.get("email_remetente", ""),
                placeholder="seuemail@gmail.com",
                key=f"ebi_frem_{edit_id}",
            )
            senha_app = cre2.text_input(
                "Senha de app do Gmail",
                value=dados.get("email_senha_app", ""),
                type="password",
                key=f"ebi_fsen_{edit_id}",
                help="Gere em myaccount.google.com → Segurança → Senhas de app.",
            )
            base_url_cfg = st.text_input(
                "🔗 URL pública do sistema",
                value=dados.get("base_url", ""),
                placeholder="https://seusistema.onrender.com",
                key=f"ebi_furl_{edit_id}",
                help="Endereço público — usado nos botões de ação dentro do e-mail.",
            )

            # ── Módulos ──────────────────────────────────────────────────
            st.markdown("#### 🧩 Módulos do Relatório")
            cm1, cm2 = st.columns(2)
            mod_exec   = cm1.checkbox("📊 Painel Executivo (KPIs)",       value=bool(mod_def.get("executivo", True)),         key=f"ebi_me_{edit_id}")
            mod_ev     = cm1.checkbox("⚠️ Risco de Evasão",               value=bool(mod_def.get("evasao", True)),            key=f"ebi_mev_{edit_id}")
            mod_aud    = cm1.checkbox("📋 Auditoria de Cadastros",         value=bool(mod_def.get("auditoria", True)),         key=f"ebi_ma_{edit_id}")
            mod_nov    = cm1.checkbox("📥 Novos Cadastros (Aprovação)",    value=bool(mod_def.get("novos_cadastros", True)),   key=f"ebi_mn_{edit_id}")
            mod_freq   = cm2.checkbox("🏆 Frequência por Turma",           value=bool(mod_def.get("frequencia_turma", True)),  key=f"ebi_mft_{edit_id}")
            mod_dias   = cm2.checkbox("📅 Dias sem Registro",              value=bool(mod_def.get("dias_sem_registro", True)), key=f"ebi_mds_{edit_id}")
            mod_aniv   = cm2.checkbox("🎂 Aniversariantes da Semana",      value=bool(mod_def.get("aniversariantes", True)),   key=f"ebi_man_{edit_id}")
            mod_pres   = cm2.checkbox("📈 Presenças no Ano (por mês)",     value=bool(mod_def.get("presencas_mes", True)),     key=f"ebi_mpm_{edit_id}")
            mod_ates   = cm2.checkbox("🏥 Atestados a Vencer (30 dias)",  value=bool(mod_def.get("atestados_vencendo", False)), key=f"ebi_mat_{edit_id}")

            assunto_extra = st.text_input(
                "Texto extra no assunto (opcional)",
                value=dados.get("assunto_extra", ""),
                placeholder="Ex.: Unidade Centro",
                key=f"ebi_fass_{edit_id}",
            )

            st.markdown("---")
            cs1, cs2, cs3 = st.columns(3)
            btn_salvar   = cs1.form_submit_button("💾 Salvar Pacote",           type="primary", use_container_width=True)
            btn_teste    = cs2.form_submit_button("📨 Enviar Agora (Teste)",    use_container_width=True)
            btn_cancelar = cs3.form_submit_button("❌ Cancelar",                use_container_width=True)

        # ── Ações ────────────────────────────────────────────────────────
        if btn_cancelar:
            st.session_state.pop("ebi_edit_id", None)
            st.rerun()

        if btn_salvar or btn_teste:
            externos_lista = [
                e.strip()
                for linha in externos_txt.replace(",", "\n").splitlines()
                for e in [linha] if e.strip()
            ]
            todos_emails = list(dict.fromkeys(emails_sis_sel + externos_lista))
            cfg_calc = {"habilitado": habilitado, "frequencia": frequencia,
                        "dia_semana": int(dia_semana_sel), "dia_mes": int(dia_mes_sel)}
            proximo = calcular_proximo_envio(cfg_calc)
            payload = {
                "nome":            nome_pct.strip() or "Pacote de Envio",
                "habilitado":      habilitado,
                "frequencia":      frequencia,
                "dia_semana":      int(dia_semana_sel),
                "dia_mes":         int(dia_mes_sel),
                "emails_destino":  todos_emails,
                "modulos": {
                    "executivo":         mod_exec,
                    "evasao":            mod_ev,
                    "auditoria":         mod_aud,
                    "novos_cadastros":   mod_nov,
                    "frequencia_turma":  mod_freq,
                    "dias_sem_registro": mod_dias,
                    "aniversariantes":    mod_aniv,
                    "presencas_mes":      mod_pres,
                    "atestados_vencendo": mod_ates,
                },
                "assunto_extra":   assunto_extra.strip(),
                "email_remetente": remetente.strip(),
                "email_senha_app": senha_app.strip(),
                "base_url":        base_url_cfg.strip().rstrip("/"),
                "proximo_envio":   str(proximo),
            }
            if btn_salvar:
                sid = salvar_schedule(payload, edit_id if edit_id != "new" else None)
                if sid:
                    st.success(f"✅ Pacote **{payload['nome']}** salvo. Próximo envio: {proximo.strftime('%d/%m/%Y')}.")
                    st.session_state.pop("ebi_edit_id", None)
                    st.rerun()

            if btn_teste:
                if not todos_emails:
                    st.error("❌ Selecione ao menos um destinatário antes de testar.")
                else:
                    from utils.identidade import get_config as _gid_t
                    nome_org_t = _gid_t().get("nome_organizacao", "Instituto Muda Brasil")
                    cfg_t = schedule_to_cfg({**payload, "emails_destino": todos_emails})
                    with st.spinner("Gerando e enviando relatório de teste…"):
                        ok_t, msg_t = enviar_relatorio_bi(cfg_t, nome_org_t, _ebi_base_url())
                    if ok_t:
                        st.success(f"✅ {msg_t}")
                    else:
                        st.error(f"❌ {msg_t}")
        return

    # ══════════════════════════════════════════════════════════════════════
    # LISTAGEM DE PACOTES
    # ══════════════════════════════════════════════════════════════════════
    col_novo, _ = st.columns([2, 5])
    if col_novo.button("➕ Novo Pacote de Envio", type="primary", use_container_width=True, key="ebi_novo"):
        st.session_state["ebi_edit_id"] = "new"
        st.rerun()

    if not schedules:
        st.info("Nenhum pacote configurado ainda. Clique em **'➕ Novo Pacote'** para começar.")
        return

    st.markdown("---")
    _DIAS_NMS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    _FREQ_LBL = {"semanal": "Semanal", "quinzenal": "Quinzenal", "mensal": "Mensal"}

    for _s in schedules:
        _ativo   = bool(_s.get("habilitado", False))
        _icon    = "🟢" if _ativo else "⚪"
        _freq_l  = _FREQ_LBL.get(_s.get("frequencia", "semanal"), "—")
        _ds      = _s.get("dia_semana")
        _dm      = _s.get("dia_mes")
        if _s.get("frequencia", "semanal") in ("semanal", "quinzenal") and _ds is not None:
            _dia_l = _DIAS_NMS[int(_ds)] if 0 <= int(_ds) <= 6 else "—"
        else:
            _dia_l = f"dia {_dm}"
        _prox_l  = _s.get("proximo_envio") or "—"
        _total_l = _s.get("total_envios") or 0
        _ult_l   = (_s.get("ultimo_envio") or "")[:16].replace("T", " ") or "—"
        _n_em    = len(_s.get("emails_destino") or [])
        _sid     = _s["id"]

        with st.container(border=True):
            cL, cM1, cM2, cM3, cR = st.columns([3.5, 1.5, 1.5, 1.5, 2.5])
            cL.markdown(f"**{_s['nome']}** &nbsp; {_icon} {'Ativo' if _ativo else 'Inativo'}")
            cL.caption(f"✉️ {_n_em} destinatário(s) · {_freq_l} ({_dia_l})")
            cM1.metric("Próximo envio", _prox_l if _prox_l != "—" else "—")
            cM2.metric("Enviados", f"{_total_l}×")
            cM3.metric("Último", _ult_l[:10] if _ult_l != "—" else "—")

            ba, bt, bh, be = cR.columns(4)
            if ba.button("✏️", key=f"ebi_ed_{_sid}", help="Editar pacote"):
                st.session_state["ebi_edit_id"] = _sid
                st.rerun()
            if bt.button("📨", key=f"ebi_tst_{_sid}", help="Enviar agora (teste)"):
                st.session_state[f"ebi_test_{_sid}"] = True
                st.rerun()
            if bh.button("📋", key=f"ebi_hist_{_sid}", help="Ver histórico de envios"):
                _hk = f"ebi_show_hist_{_sid}"
                st.session_state[_hk] = not st.session_state.get(_hk, False)
                st.rerun()
            if be.button("🗑️", key=f"ebi_del_{_sid}", help="Excluir pacote"):
                st.session_state[f"ebi_conf_del_{_sid}"] = True
                st.rerun()

            # ── Confirmar exclusão ────────────────────────────────────────
            if st.session_state.get(f"ebi_conf_del_{_sid}"):
                st.warning(f"⚠️ Excluir **'{_s['nome']}'**? Esta ação não pode ser desfeita.")
                cd1, cd2 = st.columns(2)
                if cd1.button("✅ Confirmar exclusão", key=f"ebi_del_ok_{_sid}", type="primary"):
                    excluir_schedule(_sid)
                    st.session_state.pop(f"ebi_conf_del_{_sid}", None)
                    st.rerun()
                if cd2.button("Cancelar", key=f"ebi_del_cancel_{_sid}"):
                    st.session_state.pop(f"ebi_conf_del_{_sid}", None)
                    st.rerun()

            # ── Histórico ────────────────────────────────────────────────
            if st.session_state.get(f"ebi_show_hist_{_sid}"):
                _hist = _s.get("historico_envios") or []
                if isinstance(_hist, str):
                    import json as _jh
                    try:
                        _hist = _jh.loads(_hist)
                    except Exception:
                        _hist = []
                if not _hist:
                    st.caption("Nenhum envio registrado ainda.")
                else:
                    st.markdown(f"**📋 Histórico — {len(_hist)} envio(s) registrado(s):**")
                    _linhas_h = [
                        [str(i + 1), dt[:16].replace("T", " ")]
                        for i, dt in enumerate(reversed(_hist[-20:]))
                    ]
                    st.dataframe(
                        _pd_ebi.DataFrame(_linhas_h, columns=["#", "Data / Hora"]),
                        use_container_width=True, hide_index=True,
                    )

            # ── Envio de teste inline ─────────────────────────────────────
            if st.session_state.get(f"ebi_test_{_sid}"):
                st.session_state.pop(f"ebi_test_{_sid}")
                from utils.identidade import get_config as _gid_l
                _nome_l = _gid_l().get("nome_organizacao", "Instituto Muda Brasil")
                _cfg_l  = schedule_to_cfg(_s)
                with st.spinner(f"Enviando teste '{_s['nome']}'…"):
                    _ok_l, _msg_l = enviar_relatorio_bi(_cfg_l, _nome_l, _ebi_base_url())
                if _ok_l:
                    st.success(f"✅ {_msg_l}")
                else:
                    st.error(f"❌ {_msg_l}")


def _tela_calendario_institucional():
    from database import (
        get_dias_sem_aula_periodo_df,
        registrar_dia_sem_aula,
        remover_dia_sem_aula,
    )

    st.markdown("""
        <div style='background:#F0FDF4;border-left:4px solid #16A34A;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#14532D;'>📅 Calendário Institucional — Dias Sem Aula</strong><br>
            <span style='color:#15803D;font-size:13px;'>
                Registre dias em que não houve aula por motivo institucional
                (reuniões internas, recessos, feriados locais, etc.).<br>
                Esses dias são automaticamente excluídos do alerta de
                <em>frequência pendente</em> nos relatórios.
            </span>
        </div>
    """, unsafe_allow_html=True)

    hoje_cal = datetime.date.today()

    # ── Formulário de cadastro ─────────────────────────────────────────────
    st.markdown("### ➕ Registrar dia sem aula")
    ca, cb, cc = st.columns([2, 4, 2])
    novo_dia_cal   = ca.date_input("Data:", value=hoje_cal, format="DD/MM/YYYY", key="cal_data_novo")
    motivo_cal_txt = cb.text_input("Motivo:", placeholder="Ex: Reunião pedagógica, Feriado municipal…", key="cal_motivo")
    btn_reg_cal    = cc.button("✅ Registrar", type="primary", use_container_width=True, key="cal_btn_reg")

    if btn_reg_cal:
        ok = registrar_dia_sem_aula(
            str(novo_dia_cal),
            motivo_cal_txt,
            criado_por=st.session_state.get("usuario_logado", "sistema"),
        )
        if ok:
            st.success(f"✅ {novo_dia_cal.strftime('%d/%m/%Y')} registrado como Sem Aula.")
            st.session_state.pop("cal_lista_carregada", None)
            st.rerun()
        else:
            st.error("❌ Falha ao registrar. Verifique se a tabela `dias_sem_aula` foi criada no Supabase.")
            with st.expander("ℹ️ SQL para criar a tabela (execute 1 vez no Supabase)", expanded=True):
                st.code("""
CREATE TABLE IF NOT EXISTS dias_sem_aula (
    id         uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    data       date NOT NULL UNIQUE,
    motivo     text DEFAULT '',
    criado_em  timestamptz DEFAULT now(),
    criado_por text DEFAULT ''
);
ALTER TABLE dias_sem_aula ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON dias_sem_aula
    FOR ALL USING (true) WITH CHECK (true);
                """, language="sql")

    st.markdown("---")

    # ── Filtro de período para listar ──────────────────────────────────────
    st.markdown("### 📋 Registros existentes")
    fl1, fl2, fl3 = st.columns([2, 2, 2])
    cal_ini = fl1.date_input(
        "De:", value=hoje_cal - datetime.timedelta(days=180),
        format="DD/MM/YYYY", key="cal_lista_ini"
    )
    cal_fim = fl2.date_input(
        "Até:", value=hoje_cal + datetime.timedelta(days=90),
        format="DD/MM/YYYY", key="cal_lista_fim"
    )
    btn_listar = fl3.button("🔍 Buscar", use_container_width=True, key="cal_btn_listar")

    if btn_listar:
        st.session_state["cal_lista_carregada"] = True

    if st.session_state.get("cal_lista_carregada"):
        df_cal = get_dias_sem_aula_periodo_df(str(cal_ini), str(cal_fim))
        if df_cal.empty:
            st.info("Nenhum dia sem aula registrado no período selecionado.")
        else:
            st.markdown(f"**{len(df_cal)} dia(s) encontrado(s):**")
            for _, row_cal in df_cal.iterrows():
                try:
                    d_obj   = datetime.date.fromisoformat(str(row_cal["data"]))
                    weekday = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][d_obj.weekday()]
                    d_disp  = f"{d_obj.strftime('%d/%m/%Y')} ({weekday})"
                except Exception:
                    d_disp = str(row_cal["data"])
                motivo_d = str(row_cal.get("motivo", "") or "—")
                criado_d = str(row_cal.get("criado_por", "") or "sistema")
                col_d, col_m, col_x = st.columns([3, 5, 1])
                col_d.markdown(f"📌 **{d_disp}**")
                col_m.markdown(
                    f"<small style='color:#64748B;'>{motivo_d} · <em>por {criado_d}</em></small>",
                    unsafe_allow_html=True,
                )
                if col_x.button("🗑️", key=f"cal_del_{row_cal['data']}", help="Remover este dia"):
                    remover_dia_sem_aula(str(row_cal["data"]))
                    st.session_state.pop("cal_lista_carregada", None)
                    st.rerun()
    else:
        st.caption("Ajuste o período e clique em **Buscar** para ver os registros.")


# ==============================================================================
# 🧭 NAVEGAÇÃO INTERNA E DASHBOARD
# ==============================================================================

# Executa as ferramentas de topo (Seletor de Tema e Botão do Drive) acima do menu principal
renderizar_seletor_tema()

menu = [
    "Principal",
    "Frequência",
    "Portal do Aluno",
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

    # ── Dialog: Agendar Nova Avaliação ───────────────────────────────────────
    @st.dialog("✏️ Gerenciar Agendamento")
    def _dialog_gerenciar_ag(ag_id, nome, data_atual, hora_atual):
        import datetime as _dt3
        from database import (
            concluir_ou_cancelar_agendamento as _cca,
            atualizar_agendamento as _uag,
        )

        st.markdown(
            f"<div style='font-size:13px;color:#0A2540;font-weight:700;"
            f"margin-bottom:12px;'>👤 {nome}</div>",
            unsafe_allow_html=True,
        )

        # ── Editar data / hora ──────────────────────────────────────────
        try:
            _data_pre = _dt3.date.fromisoformat(str(data_atual)[:10])
        except Exception:
            _data_pre = _dt3.date.today() + _dt3.timedelta(days=1)
        try:
            _h, _m = str(hora_atual)[:5].split(":")
            _hora_pre = _dt3.time(int(_h), int(_m))
        except Exception:
            _hora_pre = _dt3.time(11, 0)

        _eg1, _eg2 = st.columns(2)
        _nova_data = _eg1.date_input(
            "📅 Data:", value=_data_pre,
            min_value=_dt3.date.today(),
            key="gag_data", format="DD/MM/YYYY",
        )
        _nova_hora = _eg2.time_input(
            "🕐 Horário:", value=_hora_pre,
            key="gag_hora", step=1800,
        )

        if st.button("💾 Salvar Alteração", type="primary", use_container_width=True):
            _ok_u, _msg_u = _uag(ag_id, str(_nova_data), str(_nova_hora)[:5])
            if _ok_u:
                get_agendamentos_pendentes.clear()
                st.rerun()
            else:
                st.error(f"Erro: {_msg_u}")

        st.divider()

        # ── Exclusão com confirmação inline ────────────────────────────
        _key_conf = f"gag_conf_{ag_id}"
        if not st.session_state.get(_key_conf):
            if st.button("🗑️ Excluir Agendamento", use_container_width=True):
                st.session_state[_key_conf] = True
                st.rerun()
        else:
            st.warning(f"Confirma excluir o agendamento de **{nome}**?")
            _cd1, _cd2 = st.columns(2)
            if _cd1.button("✅ Sim, excluir", type="primary", use_container_width=True):
                _ok_x, _msg_x = _cca(ag_id, "Cancelado")
                if _ok_x:
                    st.session_state.pop(_key_conf, None)
                    get_agendamentos_pendentes.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {_msg_x}")
            if _cd2.button("↩️ Não, voltar", use_container_width=True):
                st.session_state.pop(_key_conf, None)
                st.rerun()

    @st.dialog("📅 Agendar Nova Avaliação")
    def _dialog_nova_aval():
        import datetime as _dt2
        from database import buscar_alunos_geral as _bag, criar_agendamento as _cag
        from utils.busca_aluno import busca_aluno_widget as _baw, filtrar_alunos_df as _faf
        st.caption("Busque o aluno, confirme a data e o horário.")
        _busca_d = _baw("dag_busca", placeholder="🔍 Digite pelo menos 3 letras do nome...")
        _aluno_d = None
        if _busca_d and len(_busca_d.strip()) >= 3:
            _df_d = _faf(_bag(""), _busca_d, cols=["nome", "turma"])
            if _df_d.empty:
                st.warning("Nenhum aluno encontrado.")
            else:
                _map_d = {
                    f"{r['nome']}  ({str(r.get('turma',''))[:18]})": r.to_dict()
                    for _, r in _df_d.head(10).iterrows()
                }
                _k_d = st.selectbox("Selecionar:", list(_map_d.keys()), key="dag_sel",
                                    label_visibility="collapsed")
                _aluno_d = _map_d[_k_d]
        # Data — próximo dia útil como padrão
        _hoje_d = _dt2.date.today()
        _prox_d = _hoje_d + _dt2.timedelta(days=1)
        while _prox_d.weekday() >= 5:
            _prox_d += _dt2.timedelta(days=1)
        _c1d, _c2d = st.columns(2)
        _data_d = _c1d.date_input("📅 Data:", value=_prox_d, min_value=_hoje_d,
                                   key="dag_data", format="DD/MM/YYYY")
        _hora_d = _c2d.time_input("🕐 Horário:", value=_dt2.time(11, 0), key="dag_hora",
                                   step=1800)
        st.divider()
        if st.button("✅ Confirmar Agendamento", type="primary",
                     use_container_width=True, disabled=(_aluno_d is None)):
            _ok_d, _msg_d = _cag(
                _aluno_d["id"], str(_data_d), str(_hora_d)[:5], "Avaliação"
            )
            if _ok_d:
                get_agendamentos_pendentes.clear()
                st.rerun()
            else:
                st.error(f"Erro: {_msg_d}")

    # ── Layout principal: Grid (esq) + Avaliações (dir) ─────────────────────
    _col_grid, _col_agenda = st.columns([3, 1], gap="large")

    # ════════════════════════════════════════════════
    # COLUNA DIREITA — Próximas Avaliações (sempre visível)
    # ════════════════════════════════════════════════
    with _col_agenda:
        # CSS: reduz fonte do nome nos cards de agendamento em 35%
        st.markdown("""<style>
        div[data-testid="column"] + div[data-testid="column"] button p,
        div[data-testid="column"] + div[data-testid="column"] button span {
            font-size: 9px !important;
            line-height: 1.3 !important;
        }
        div[data-testid="column"] + div[data-testid="column"]
          div[data-testid="stVerticalBlockBorderWrapper"] button {
            padding: 3px 6px !important;
            min-height: unset !important;
        }
        </style>""", unsafe_allow_html=True)

        _ag_hd_col, _ag_add_col = st.columns([3, 1], vertical_alignment="center")
        _ag_hd_col.markdown(
            "<p style='font-weight:800;color:#0A2540;font-size:0.95rem;margin:0 0 6px;'>"
            "🗓️ Próximas Avaliações</p>",
            unsafe_allow_html=True,
        )
        with _ag_add_col:
            if st.button("➕", key="hg_nova_aval", help="Agendar Nova Avaliação",
                         use_container_width=True):
                _dialog_nova_aval()

        _agendamentos = get_agendamentos_pendentes(limite=8)
        if _agendamentos:
            for _ag in _agendamentos:
                _aluno_data = _ag.get("alunos") or {}
                _nm  = (_aluno_data.get("nome") or _ag.get("nome_aluno") or "—")
                _aid = _aluno_data.get("id") or _ag.get("aluno_id")
                _hr  = (_ag.get("horario") or "—")
                _dt  = str(_ag.get("data_agendamento") or _ag.get("data") or "")
                _dt_fmt = ""
                if _dt and len(_dt) >= 10:
                    try:
                        _dp = datetime.date.fromisoformat(_dt[:10])
                        _dias_sem = ["seg","ter","qua","qui","sex","sáb","dom"]
                        _dia_sem = _dias_sem[_dp.weekday()]
                        _dt_fmt = f"{_dia_sem} {_dp.day:02d}/{_dp.month:02d}"
                    except Exception:
                        _dt_fmt = _dt[:5]
                _nm_curto = (_nm[:16] + "…") if len(_nm) > 16 else _nm
                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size:11px;color:#64748B;margin-bottom:2px;'>"
                        f"🕒 <b>{_hr}</b>{(' · ' + _dt_fmt) if _dt_fmt else ''}</div>",
                        unsafe_allow_html=True,
                    )
                    _ag_id_str = _ag.get("id", "")
                    _c_nm, _c_del = st.columns([4, 1], vertical_alignment="center")
                    if _aid:
                        if _c_nm.button(
                            _nm_curto,
                            key=f"hg_ag_{_ag_id_str}",
                            use_container_width=True,
                            help=f"Abrir prontuário: {_nm} → Nova Medição",
                        ):
                            from database import buscar_aluno_por_id
                            _al = buscar_aluno_por_id(_aid) or _aluno_data
                            st.session_state.aluno_prontuario = _al
                            st.session_state.origem_prontuario = "Principal"
                            st.session_state.prontuario_aba = "Nova Medição"
                            st.session_state.menu_atual = "Portal do Aluno"
                            st.rerun()
                    else:
                        _c_nm.markdown(
                            f"<div style='font-size:8px;font-weight:600;"
                            f"color:#0F172A;'>{_nm_curto}</div>",
                            unsafe_allow_html=True,
                        )
                    if _ag_id_str and _c_del.button(
                        "✏️", key=f"hg_ag_del_{_ag_id_str}",
                        help="Editar ou excluir este agendamento",
                    ):
                        _dialog_gerenciar_ag(_ag_id_str, _nm, _dt, _hr)
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
        from utils.busca_aluno import busca_aluno_widget as _baw_hg, filtrar_alunos_df as _faf_hg
        _hg_busca = _baw_hg(
            "hg_busca",
            container=_hg_c_busca,
            placeholder="🔍 Nome ou turma…",
        )

        # Carregar dados
        _df_alunos  = buscar_alunos_geral("")
        _df_ultima  = load_frequencia_ultima_presenca()
        _df_atestad = load_atestados_vencimento()

        # Templates WhatsApp — carregados uma vez, fora do loop.
        # Cada gatilho da tabela crm_templates (painel Configurações > Mensagens)
        # é mapeado com exatidão: niver_hoje (Dia Exato) / niver_passou (Atrasado) /
        # evasao_nunca / evasao_60 / evasao_80 / assiduo_top.
        # "Aviso Prévio" (niver_futuro) foi descontinuado: futuros não recebem parabéns.
        try:
            from utils.niver_automatico import montar_link_whatsapp, personalizar_mensagem, montar_mensagem_niver, get_parabenizados_dict
            from database import get_crm_templates
            _df_tpl = get_crm_templates()
            # Dicionário {gatilho: mensagem} — fonte única e auditada
            _tpl_map: dict = {}
            if not _df_tpl.empty and "gatilho" in _df_tpl.columns:
                for _, _tr in _df_tpl.iterrows():
                    _tpl_map[str(_tr.get("gatilho", ""))] = str(_tr.get("mensagem", ""))
            _parab_dict = get_parabenizados_dict()
            _wapp_ok = True
        except Exception:
            _tpl_map = {}
            _parab_dict = {}
            _wapp_ok = False

        if not _df_alunos.empty:
            # Merge com última presença
            if not _df_ultima.empty:
                _df_hg = _df_alunos.merge(_df_ultima, on="id", how="left")
            else:
                _df_hg = _df_alunos.copy()
                _df_hg["ultima_presenca"] = pd.NaT

            # Merge com vencimento de atestado
            if not _df_atestad.empty:
                _df_hg = _df_hg.merge(_df_atestad, on="id", how="left")
            else:
                _df_hg["data_vencimento_atestado"] = pd.NaT

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
            _df_grid = _faf_hg(_df_grid, _hg_busca, cols=["nome", "turma"], min_len=3)
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
            _h0, _h1, _h2, _h3, _h4, _h5, _h6 = st.columns(
                [0.5, 2.8, 1.4, 1.3, 1.6, 1.5, 0.9], gap="small"
            )
            _h0.markdown(" ", unsafe_allow_html=True)
            _h6.markdown(" ", unsafe_allow_html=True)

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

            _sort_btn(_h1, "Nome",              "nome")
            _sort_btn(_h2, "Turma",             "turma")
            _sort_btn(_h3, "🎂 Aniversário",    "aniversario")
            _sort_btn(_h4, "⏱ Última Pres.",    "ultima_presenca")
            _sort_btn(_h5, "🏥 Venc. Atestado", "data_vencimento_atestado")

            # Pré-carregar IDs avaliados (1 query, sem N+1 no loop)
            try:
                from database import get_ids_alunos_avaliados
                _ids_avaliados_hg = get_ids_alunos_avaliados()
            except Exception:
                _ids_avaliados_hg = set()

            # ── Linhas do Grid ─────────────────────────────────────────
            _hoje_hg   = datetime.date.today()
            _hoje_dia  = _hoje_hg.day
            _hoje_mes  = _hoje_hg.month
            _meses_abr = ["","jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]

            for _, _r in _df_pag.iterrows():
                with st.container(border=True):
                    _ca, _cb, _cc, _cd, _ce, _cg, _cf = st.columns(
                        [0.5, 2.8, 1.4, 1.3, 1.6, 1.5, 0.9], gap="small",
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
                    _sem_img = not _r.get("termo_imagem")
                    _badge_img = (
                        "<abbr title='Não autoriza uso de imagem e voz (LGPD)' "
                        "style='text-decoration:none;cursor:help;"
                        "background:#FEE2E2;color:#DC2626;"
                        "border:1px solid #FECACA;"
                        "border-radius:3px;padding:1px 5px;"
                        "font-size:10px;font-weight:800;"
                        "margin-right:5px;white-space:nowrap;'>📷✕</abbr>"
                    ) if _sem_img else ""
                    _atestado_bloq = bool(_r.get("atestado_bloqueado"))
                    _badge_atestado = (
                        "<abbr title='Atestado médico pendente — Participação bloqueada' "
                        "style='text-decoration:none;cursor:help;"
                        "background:#FFF7ED;color:#C2410C;"
                        "border:1px solid #FED7AA;"
                        "border-radius:3px;padding:1px 5px;"
                        "font-size:10px;font-weight:800;"
                        "margin-right:5px;white-space:nowrap;'>🏥⚠</abbr>"
                    ) if _atestado_bloq else ""
                    _nunca_av = str(_r.get("id", "")) not in _ids_avaliados_hg
                    _badge_sem_av = (
                        "<abbr title='Nunca avaliado — sem nenhuma avaliação registrada' "
                        "style='text-decoration:none;cursor:help;"
                        "background:#EFF6FF;color:#1D4ED8;"
                        "border:1px solid #BFDBFE;"
                        "border-radius:3px;padding:1px 5px;"
                        "font-size:10px;font-weight:800;"
                        "margin-right:5px;white-space:nowrap;'>📋✕</abbr>"
                    ) if _nunca_av else ""
                    _aval_pend = bool(_r.get("avaliacao_pendente"))
                    _badge_aval_pend = (
                        "<abbr title='Bloqueado — aguardando reavaliação' "
                        "style='text-decoration:none;cursor:help;"
                        "background:#FEF3C7;color:#92400E;"
                        "border:1px solid #FCD34D;"
                        "border-radius:3px;padding:1px 5px;"
                        "font-size:10px;font-weight:800;"
                        "margin-right:5px;white-space:nowrap;'>⚡🚫</abbr>"
                    ) if _aval_pend else ""
                    _cb.markdown(
                        f"<span style='font-size:13.5px;font-weight:700;color:#0F172A;'>"
                        f"{_badge_img}{_badge_atestado}{_badge_sem_av}{_badge_aval_pend}{_r['nome']}</span>",
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
                        # Link WhatsApp de parabéns — aparece apenas no mês do aniversário
                        if _wapp_ok and _mes_n == _hoje_mes:
                            _ja_parab_hg = str(_r.get("id", "")) in _parab_dict
                            if _ja_parab_hg:
                                _ts_hg = _parab_dict.get(str(_r.get("id", "")), "")
                                _ts_hg = _ts_hg.split("|")[0][:10].replace("T", " ") if _ts_hg else ""
                                _niver_html += (
                                    f"<br><span style='font-size:10px;color:#065F46;"
                                    f"font-weight:800;background:#D1FAE5;padding:1px 5px;"
                                    f"border-radius:4px;'>✅ Parabenizado</span>"
                                    + (f"<br><span style='font-size:9px;color:#94A3B8;'>{_ts_hg}</span>" if _ts_hg else "")
                                )
                            else:
                                _wap_n = str(_r.get("whatsapp") or "").strip()
                                # Texto idêntico ao painel admin conforme status:
                                # Dia Exato (niver_hoje) ou Atrasado (niver_passou).
                                # Aniversários futuros não recebem parabéns antecipado.
                                if _mes_n == _hoje_mes and _dia_n == _hoje_dia:
                                    _niver_status = "hoje"
                                elif _dia_n < _hoje_dia:
                                    _niver_status = "passou"
                                else:
                                    _niver_status = None
                                if _wap_n and _niver_status:
                                    _msg_n = montar_mensagem_niver(_niver_status, str(_r.get("nome", "")))
                                    _link_n = montar_link_whatsapp(_wap_n, _msg_n)
                                    if _link_n:
                                        _niver_html += (
                                            f"<br><a href='{_link_n}' target='_blank' "
                                            f"style='font-size:10px;color:#25D366;text-decoration:none;"
                                            f"font-weight:600;'>📱 Parabéns</a>"
                                        )
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
                        # Link WhatsApp de retenção/evasão — aparece quando ausente > 14 dias
                        if _wapp_ok and _up_dias > 14:
                            _wap_e = str(_r.get("whatsapp") or "").strip()
                            if _wap_e:
                                # Gatilho correto conforme grau de ausência:
                                # 14-30 dias → evasao_60 | >30 dias → evasao_80
                                _ev_key = "evasao_60" if _up_dias <= 30 else "evasao_80"
                                _tpl_e = _tpl_map.get(_ev_key, "Olá {nome}, sentimos sua falta!")
                                _msg_e = personalizar_mensagem(_tpl_e, str(_r.get("nome", "")))
                                _link_e = montar_link_whatsapp(_wap_e, _msg_e)
                                if _link_e:
                                    _cor_icone = "#F59E0B" if _up_dias <= 30 else "#EF4444"
                                    _up_html += (
                                        f"<br><a href='{_link_e}' target='_blank' "
                                        f"style='font-size:10px;color:{_cor_icone};text-decoration:none;"
                                        f"font-weight:600;'>📱 Contato</a>"
                                    )
                    else:
                        _up_html = "<span style='font-size:12px;color:#CBD5E1;'>Sem registro</span>"
                        # Sem histórico = aluno nunca veio → gatilho evasao_nunca
                        if _wapp_ok:
                            _wap_e = str(_r.get("whatsapp") or "").strip()
                            if _wap_e:
                                _tpl_e = _tpl_map.get("evasao_nunca", "Olá {nome}, ainda não te vimos por aqui!")
                                _msg_e = personalizar_mensagem(_tpl_e, str(_r.get("nome", "")))
                                _link_e = montar_link_whatsapp(_wap_e, _msg_e)
                                if _link_e:
                                    _up_html += (
                                        f"<br><a href='{_link_e}' target='_blank' "
                                        f"style='font-size:10px;color:#EF4444;text-decoration:none;"
                                        f"font-weight:600;'>📱 Contato</a>"
                                    )
                    _ce.markdown(_up_html, unsafe_allow_html=True)

                    # Vencimento Atestado
                    _dv = _r.get("data_vencimento_atestado")
                    if pd.notna(_dv):
                        _dv_dt   = pd.Timestamp(_dv).date()
                        _dv_dias = (_dv_dt - _hoje_hg).days
                        if _dv_dias < 0:
                            _dv_cor   = "#DC2626"
                            _dv_bg    = "#FEE2E2"
                            _dv_icon  = "🔴"
                            _dv_label = f"Vencido {abs(_dv_dias)}d"
                        elif _dv_dias <= 30:
                            _dv_cor   = "#D97706"
                            _dv_bg    = "#FEF3C7"
                            _dv_icon  = "🟡"
                            _dv_label = f"{_dv_dias}d"
                        else:
                            _dv_cor   = "#059669"
                            _dv_bg    = "#D1FAE5"
                            _dv_icon  = "🟢"
                            _dv_label = f"{_dv_dias}d"
                        _dv_html = (
                            f"<span style='font-size:11px;font-weight:700;color:{_dv_cor};"
                            f"background:{_dv_bg};border-radius:4px;padding:2px 5px;"
                            f"display:inline-block;'>"
                            f"{_dv_icon} {_dv_dt.strftime('%d/%m/%y')}</span>"
                            f"<br><span style='font-size:10px;color:#94A3B8;'>{_dv_label}</span>"
                        )
                    else:
                        _dv_html = "<span style='font-size:11px;color:#CBD5E1;'>— sem atestado</span>"
                    _cg.markdown(_dv_html, unsafe_allow_html=True)

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
    st.session_state.menu_atual = "Portal do Aluno"
    st.rerun()

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
            ["🏫 Turmas", "💬 Mensagens", "🎂 Aniversários", "🎨 Identidade Visual", "🛠️ Admin", "🔀 Mesclar Fichas", "📅 Calendário", "📧 Email BI", "👥 Usuários", "🔒 LGPD"]
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
        with _aba_cfg[6]:
            _tela_calendario_institucional()
        with _aba_cfg[7]:
            _tela_email_bi()
        with _aba_cfg[8]:
            from views.gestao_usuarios_view import tela_gestao_usuarios
            tela_gestao_usuarios()
        with _aba_cfg[9]:
            from database import get_logs_lgpd
            st.markdown(
                "<p style='font-weight:800;color:#0A2540;font-size:1rem;margin-bottom:4px;'>"
                "🔒 Histórico de Alterações — Autorização de Imagem (LGPD)</p>",
                unsafe_allow_html=True,
            )
            st.caption("Cada alteração do campo 'Uso de Imagem e Voz' registra automaticamente data/hora, operador e novo status.")
            _logs_lgpd = get_logs_lgpd()
            if not _logs_lgpd:
                st.info("Nenhuma alteração registrada ainda.")
            else:
                if st.button("🔄 Atualizar", key="lgpd_log_refresh"):
                    get_logs_lgpd.clear()
                    st.rerun()
                for _lg in _logs_lgpd:
                    _ts_fmt = str(_lg.get("timestamp", ""))[:16].replace("T", " ")
                    _status_color = "#065F46" if _lg.get("status") == "Autorizado" else "#7F1D1D"
                    _status_bg = "#D1FAE5" if _lg.get("status") == "Autorizado" else "#FEE2E2"
                    _status_icon = "✅" if _lg.get("status") == "Autorizado" else "🚫"
                    st.markdown(
                        f"<div style='padding:8px 12px;border-radius:6px;margin-bottom:6px;"
                        f"background:#F8FAFC;border:1px solid #E2E8F0;display:flex;align-items:center;gap:12px;'>"
                        f"<span style='font-size:12px;color:#64748B;min-width:120px;'>🕒 {_ts_fmt}</span>"
                        f"<span style='font-size:13px;font-weight:700;color:#0F172A;flex:1;'>"
                        f"{_lg.get('aluno_nome', '—').upper()}</span>"
                        f"<span style='padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;"
                        f"background:{_status_bg};color:{_status_color};'>"
                        f"{_status_icon} {_lg.get('status', '—')}</span>"
                        f"<span style='font-size:11px;color:#94A3B8;min-width:100px;text-align:right;'>"
                        f"op: {_lg.get('operador', '—')}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

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
