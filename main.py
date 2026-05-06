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
def renderizar_seletor_tema():
    """
    Gera as ferramentas de topo (Acesso ao Drive e Seletor de Tema).
    Utiliza a memória (session_state) para lembrar a escolha e injeta CSS.
    """
    if "tema_operador" not in st.session_state:
        st.session_state.tema_operador = "Claro"

    # Injeção de CSS Dinâmico com base na escolha
    if st.session_state.tema_operador == "Escuro":
        css_tema = """
        <style>
            .stApp { background: #0E1117 !important; }
            .stSidebar { background-color: #1E293B !important; }

            /* Fundo dos painéis e bordas dos containers */
            div[data-testid="stVerticalBlockBorderWrapper"] { 
                background-color: #1E293B !important; 
                border-color: #334155 !important; 
            }

            /* Cor do texto global */
            p, span, h1, h2, h3, h4, h5, h6, label, .stMarkdown { color: #F8FAFC !important; }

            /* Menu Radiogroup Superior */
            div[role="radiogroup"] { 
                background: #1E293B !important; 
                border-color: #334155 !important; 
            }
            div[role="radiogroup"]::before { color: #3B82F6 !important; }
            div[role="radiogroup"] label p { color: #94A3B8 !important; }
            div[role="radiogroup"] label:hover { background: #334155 !important; }
            div[role="radiogroup"] label[data-checked="true"] { background: #3B82F6 !important; }
            div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }

            /* Inputs e Selects */
            div[data-baseweb="input"] > div {
                background: #0E1117 !important;
                border-color: #334155 !important;
                color: #F8FAFC !important;
            }

            /* 🚀 FIX: Correção de visibilidade dos Botões Secundários no Modo Escuro */
            button[kind="secondary"] {
                background: #1E293B !important; 
                border-color: #334155 !important; 
                color: #F8FAFC !important;
            }
            button[kind="secondary"]:hover {
                background: #334155 !important;
                border-color: #475569 !important;
                color: #60A5FA !important;
            }
            button[kind="secondary"] p { color: #F8FAFC !important; }

        </style>
        """
        st.markdown(css_tema, unsafe_allow_html=True)

    # Criamos colunas para posicionar o Botão do Drive e o Tema à direita
    col_vazia, col_drive, col_tema = st.columns(
        [5.5, 2.5, 2], vertical_alignment="center"
    )

    with col_drive:
        # 🚀 NOVO: Link Direto para o Google Drive
        st.link_button(
            "📂 Abrir Google Drive",
            "https://drive.google.com/drive/u/7/my-drive",
            use_container_width=True,
            help="Acesse a pasta da nuvem para gerir as fotografias.",
        )

    with col_tema:
        tema_escolhido = st.selectbox(
            "🌗 Preferência Visual:",
            ["Claro", "Escuro"],
            index=0 if st.session_state.tema_operador == "Claro" else 1,
            label_visibility="collapsed",
        )

    # Se o operador mudar o tema, recarrega a página
    if tema_escolhido != st.session_state.tema_operador:
        st.session_state.tema_operador = tema_escolhido
        st.rerun()


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
#MainMenu, header, footer { visibility: hidden; }
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

# ==============================================================================
# 🔐 PORTAL DE ACESSO — PRIME
# ==============================================================================
if not st.session_state.usuario_logado:
    st.markdown("<div style='min-height:5vh;'></div>", unsafe_allow_html=True)
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
    "BI Prime",
    "Relatórios",
    "Satisfação",
    "Ficha de Matrícula",
    "Conferência Facial",
]
if st.session_state.perfil == "SuperAdmin":
    menu.extend(
        ["Turmas", "Mensagens", "Mesclar Fichas", "Identidade Visual", "Backup"]
    )
menu.append("Sair")


def format_nav(opt):
    mapa = {
        "Principal": "🏠 Início",
        "Frequência": "✅ Frequência",
        "Portal do Aluno": "🩺 Portal do Aluno",
        "Nova Matrícula": "📝 Nova Matrícula",
        "Radar de Acolhimento": "💙 Radar",
        "BI Prime": "📊 BI Prime",
        "Relatórios": "📋 Relatórios",
        "Satisfação": "⭐ Satisfação",
        "Ficha de Matrícula": "🖨️ Ficha",
        "Conferência Facial": "📸 Conf. Facial",
        "Turmas": "🏫 Turmas",
        "Mensagens": "💬 Mensagens",
        "Mesclar Fichas": "🔀 Mesclar",
        "Identidade Visual": "🎨 Identidade",
        "Backup": "🛠️ Admin",
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
    # ── Saudação compacta ──────────────────────────────────────────────────
    _hoje = datetime.date.today()
    _ds = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][
        _hoje.weekday()
    ]
    _meses_pt = [
        "jan",
        "fev",
        "mar",
        "abr",
        "mai",
        "jun",
        "jul",
        "ago",
        "set",
        "out",
        "nov",
        "dez",
    ]
    _nome_curto = (
        st.session_state.usuario_nome.split()[0]
        if st.session_state.usuario_nome
        else "Gestor"
    )
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:space-between;"
        f"margin-bottom:12px;'>"
        f"<div><h3 style='color:#0A2540;margin:0;font-size:1.25rem;font-weight:800;'>"
        f"Olá, {_nome_curto} 👋</h3>"
        f"<p style='color:#94A3B8;font-size:12px;margin:2px 0 0;'>"
        f"{_ds}, {_hoje.day} {_meses_pt[_hoje.month - 1]} {_hoje.year}</p></div>"
        f"<span style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;"
        f"padding:5px 12px;font-size:11px;font-weight:700;color:#1E40AF;'>"
        f"● {st.session_state.perfil}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Atalhos rápidos (1 clique) ─────────────────────────────────────────
    qa1, qa2, qa3, qa4 = st.columns(4, gap="small")
    with qa1:
        if st.button(
            "✅  Frequência",
            use_container_width=True,
            type="primary",
            help="Lançar presenças do dia",
        ):
            st.session_state.menu_atual = "Frequência"
            st.rerun()
    with qa2:
        if st.button(
            "🩺  Portal do Aluno",
            use_container_width=True,
            help="Prontuário e ficha clínica",
        ):
            st.session_state.menu_atual = "Portal do Aluno"
            st.rerun()
    with qa3:
        if st.button(
            "📊  BI & Análises", use_container_width=True, help="Dashboard analítico"
        ):
            st.session_state.menu_atual = "BI Prime"
            st.rerun()
    with qa4:
        if st.button(
            "📝  Nova Matrícula", use_container_width=True, help="Cadastrar novo aluno"
        ):
            st.session_state.menu_atual = "Nova Matrícula"
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

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
        except:
            return pd.DataFrame()

    c_ag, c_ni = st.columns([1, 2], gap="large")

    with c_ag:
        st.markdown(
            "<p style='font-weight:800; color:#0A2540; font-size:1.05rem; margin-bottom:12px;'>🗓️ Próximas Avaliações</p>",
            unsafe_allow_html=True,
        )
        agendamentos = get_agendamentos_pendentes(limite=8)
        if agendamentos:
            for a in agendamentos:
                with st.container(border=True):
                    st.markdown(f"🕒 **{a['horario']}** — {a['alunos']['nome']}")
        else:
            st.info("Agenda livre no momento.")

    with c_ni:
        col_t, col_pdf, col_word = st.columns(
            [0.5, 0.25, 0.25], vertical_alignment="center"
        )
        col_t.markdown(
            "<p style='font-weight:bold; color:#0A2540; font-size:1.1rem; margin:0;'>🎂 Aniversariantes</p>",
            unsafe_allow_html=True,
        )

        df_n_geral = load_niver_geral()
        if not df_n_geral.empty:
            meses_pt = {
                1: "Janeiro",
                2: "Fevereiro",
                3: "Março",
                4: "Abril",
                5: "Maio",
                6: "Junho",
                7: "Julho",
                8: "Agosto",
                9: "Setembro",
                10: "Outubro",
                11: "Novembro",
                12: "Dezembro",
            }
            meses_lista = list(meses_pt.values())

            st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
            meses_selecionados = st.multiselect(
                "Selecione os meses desejados:",
                meses_lista,
                default=[meses_pt[datetime.date.today().month]],
            )

            if meses_selecionados:
                meses_inv = {v: k for k, v in meses_pt.items()}
                meses_nums = [meses_inv[m] for m in meses_selecionados]
                df_n = df_n_geral[df_n_geral["mes"].isin(meses_nums)].sort_values(
                    ["mes", "dia"]
                )

                if len(meses_selecionados) == 1:
                    titulo_doc = f"ANIVERSARIANTES DE {meses_selecionados[0].upper()}"
                    subtitulo_doc = ""
                    nome_arq = meses_selecionados[0]
                else:
                    titulo_doc = "ANIVERSARIANTES"
                    subtitulo_doc = f"{meses_selecionados[0].upper()} À {meses_selecionados[-1].upper()}"
                    nome_arq = f"{meses_selecionados[0]}_A_{meses_selecionados[-1]}"

                with col_pdf:
                    if st.button(
                        "📕 PDF",
                        help="Gerar Cartaz Multi-Meses",
                        use_container_width=True,
                    ):
                        with st.spinner("A processar..."):
                            try:
                                from modulos_frequencia.tab_niver import (
                                    gerar_cartaz_pdf_core,
                                )

                                pdf_bytes = gerar_cartaz_pdf_core(
                                    df_n, titulo_doc, subtitulo_doc, ""
                                )
                                st.download_button(
                                    "📥 PDF",
                                    pdf_bytes,
                                    f"Aniversariantes_{nome_arq}.pdf",
                                    "application/pdf",
                                    use_container_width=True,
                                    type="primary",
                                )
                            except Exception as e:
                                st.error(f"Erro: {e}")

                with col_word:
                    _wk = f"word_niver_{nome_arq}"
                    if st.session_state.get(_wk):
                        st.download_button(
                            "📥 DOC",
                            st.session_state[_wk],
                            f"Aniversariantes_{nome_arq}.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            type="primary",
                        )
                    elif st.button(
                        "📘 DOCX", help="Gerar Word", use_container_width=True
                    ):
                        with st.spinner("A processar..."):
                            try:
                                from modulos_frequencia.tab_niver import (
                                    gerar_cartaz_word_core,
                                )

                                _wb = gerar_cartaz_word_core(
                                    df_n, titulo_doc, subtitulo_doc, ""
                                )
                                st.session_state[_wk] = _wb
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao gerar Word: {e}")

                st.markdown(
                    """
<style>
.avatar-niver-wrap { display:flex; align-items:center; justify-content:center; position: relative; }
.avatar-niver-circle { width:46px; height:46px; border-radius:50%; clip-path: circle(50% at 50% 50%); border:2.5px solid #0056b3; flex-shrink:0; transition: transform 0.28s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.28s ease; cursor:zoom-in; position:relative; z-index:2; background: linear-gradient(135deg,#0056b3,#00a8cc); overflow: hidden; }
.avatar-niver-circle:hover { transform: scale(2.6); box-shadow: 0 10px 30px rgba(0,0,0,0.40); z-index: 9999; position: relative; }
.avatar-niver-circle img { width:100%; height:100%; object-fit:cover; object-position: center top; display:block; }
.avatar-niver-circle.initials { display:flex; align-items:center; justify-content:center; color:#fff; font-weight:900; font-size:15px; letter-spacing:-0.5px; }
</style>""",
                    unsafe_allow_html=True,
                )

                hoje_dia = datetime.date.today().day
                hoje_mes = datetime.date.today().month

                for _, r in df_n.iterrows():
                    dia = int(r["dia"])
                    mes = int(r["mes"])
                    data_formatada = f"{dia:02d}/{mes:02d}"

                    if mes == hoje_mes and dia == hoje_dia:
                        icone, cor, status = "🎉", "#10B981", "HOJE"
                    elif (mes < hoje_mes) or (mes == hoje_mes and dia < hoje_dia):
                        icone, cor, status = "🎈", "#64748B", "Passou"
                    else:
                        icone, cor, status = "⏳", "#F59E0B", "Em breve"

                    msg = get_template_seguro_db("niver_hoje", r["nome"])
                    limpo = re.sub(r"\D", "", str(r.get("whatsapp", "")))
                    link_w = (
                        f"https://wa.me/55{limpo}?text={urllib.parse.quote(msg)}"
                        if len(limpo) >= 10
                        else None
                    )

                    foto_url = r.get("url_foto") or ""
                    iniciais = "".join(
                        p[0].upper() for p in str(r["nome"]).split()[:2] if p
                    )
                    if foto_url and str(foto_url).startswith("http"):
                        avatar_html = (
                            f'<div class="avatar-niver-wrap">'
                            f'<div class="avatar-niver-circle" '
                            f"onerror=\"this.className+=' initials';this.innerHTML='{iniciais}'\">"
                            f'<img src="{foto_url}" alt="{iniciais}" '
                            f"onerror=\"this.parentElement.classList.add('initials');"
                            f"this.parentElement.innerHTML='{iniciais}'\">"
                            f"</div>"
                            f"</div>"
                        )
                    else:
                        avatar_html = (
                            f'<div class="avatar-niver-wrap">'
                            f'<div class="avatar-niver-circle initials">{iniciais}</div>'
                            f"</div>"
                        )

                    with st.container(border=True):
                        c0, c1, c2, c3 = st.columns(
                            [0.45, 3.2, 0.8, 1.2], vertical_alignment="center"
                        )
                        with c0:
                            st.markdown(avatar_html, unsafe_allow_html=True)
                        c1.markdown(
                            f"**{r['nome']}**<br><span style='color:{cor};font-size:12px;font-weight:700;'>{icone} {data_formatada} &bull; {status}</span>",
                            unsafe_allow_html=True,
                        )
                        with c2:
                            if link_w:
                                st.markdown(
                                    f"""<a href="{link_w}" target="_blank" style="text-decoration: none;"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="28"></a>""",
                                    unsafe_allow_html=True,
                                )
                        with c3:
                            if st.button(
                                "🩺", key=f"hm_f_{r['id']}", use_container_width=True
                            ):
                                st.session_state.aluno_prontuario = r.to_dict()
                                st.session_state.origem_prontuario = "Principal"
                                st.session_state.menu_atual = "Portal do Aluno"
                                st.rerun()
            else:
                st.info("Selecione um ou mais meses.")
        else:
            st.info("Nenhum dado encontrado.")

# ==============================================================================
# 🚀 ROTEAMENTO DE VISTAS
# ==============================================================================
elif st.session_state.menu_atual == "Frequência":
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
    st.info(
        "Preencha os dados da ficha com calma. Ao concluir, o aluno estará imediatamente disponível no sistema para marcação de presença."
    )
    tela_inscricao_publica_move_right()

elif st.session_state.menu_atual == "Portal do Aluno":
    if st.session_state.aluno_prontuario:
        from views.prontuario_ficha import renderizar_ficha

        renderizar_ficha()
    else:
        from views.prontuario_dashboard import renderizar_dashboard

        renderizar_dashboard()

elif st.session_state.menu_atual == "BI Prime":
    aba_bi = st.tabs(["📊 Dashboard Geral", "👤 Relatório Individual"])
    with aba_bi[0]:
        from views.bi_dashboard_view import render_bi_dashboard

        render_bi_dashboard()
    with aba_bi[1]:
        from views.bi_individual_view import render_bi_individual

        render_bi_individual()

elif st.session_state.menu_atual == "Relatórios":
    from views.relatorio_view import tela_relatorio

    tela_relatorio()

elif st.session_state.menu_atual == "Satisfação":
    from views.relatorio_satisfacao_view import tela_relatorio_prime_satisfacao

    tela_relatorio_prime_satisfacao()

elif st.session_state.menu_atual == "Ficha de Matrícula":
    try:
        from views.ficha_aluno_view import tela_impressao_ficha

        tela_impressao_ficha()
    except:
        st.error("⚠️ Crie o ficheiro `ficha_aluno_view.py` na pasta `views`.")

elif st.session_state.menu_atual == "Conferência Facial":
    from views.conferencia_facial_view import tela_conferencia_facial

    tela_conferencia_facial()

elif st.session_state.menu_atual == "Mesclar Fichas":
    from views.merge_alunos_view import tela_merge_alunos

    tela_merge_alunos()

elif st.session_state.menu_atual == "Identidade Visual":
    from views.identidade_view import tela_identidade_visual

    tela_identidade_visual()

elif st.session_state.menu_atual == "Turmas":
    from views.turmas_view import tela_gestao_turmas

    tela_gestao_turmas()

elif st.session_state.menu_atual == "Mensagens":
    from views.templates_view import tela_gestao_templates

    tela_gestao_templates()

elif st.session_state.menu_atual == "Backup":
    from views.backup_view import tela_backup
    from database import ferramenta_reparacao_turmas

    tela_backup()
    st.markdown("---")
    ferramenta_reparacao_turmas()

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
