# ==============================================================================
# 📄 Arquivo: views/prontuario_dashboard.py
# 🏷️ VERSÃO: 4.4 (PRIME ELITE - UI Standardization & Cadastro Rápido Inline)
# ⚙️ FUNÇÃO: Portal do Aluno (Painel de Gestão no Topo e Action Grid na Base)
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import time
import math
import io

try:
    from st_keyup import st_keyup
    HAS_KEYUP = True
except ImportError:
    HAS_KEYUP = False

from database import (
    buscar_alunos_geral,
    get_agendamentos_pendentes,
    concluir_ou_cancelar_agendamento,
    excluir_aluno_completo,
    get_estatisticas_frequencia_aluno,
    get_historico_aulas_aluno,
    get_avaliacoes_aluno,
    criar_agendamento,
    cadastrar_novo_aluno,
    get_todas_turmas,
    alterar_status_aluno,
    get_ultima_pa_todos,
    supabase,
)
from utils.texto import normalizar_fonetica
from utils.busca_aluno import filtrar_alunos_df, busca_com_sugestoes


# ==============================================================================
# 🛠️ HELPERS — PA compacta + PDF da lista
# ==============================================================================

_PA_ABBR = {
    "normal":   "Norm",
    "elevada":  "Elev",
    "estagio1": "Estg1",
    "estagio2": "Estg2",
    "crise":    "Crise",
}
_PA_COR = {
    "normal":   "#1565C0",
    "elevada":  "#F57F17",
    "estagio1": "#E64A19",
    "estagio2": "#B71C1C",
    "crise":    "#7F0000",
}


def _pa_compact_html(sis, dia, pul, cls_k: str) -> str:
    """Retorna HTML compacto para exibição de PA na coluna do grid."""
    if not sis or not dia or int(sis) <= 0:
        return "<span style='color:#CBD5E1;font-size:12px;'>—</span>"
    abbr = _PA_ABBR.get(cls_k, "")
    cor  = _PA_COR.get(cls_k, "#475569")
    pul_txt = f" ❤{int(pul)}" if pul else ""
    return (
        f"<div style='font-size:12px;font-weight:700;color:{cor};line-height:1.3;'>"
        f"{sis}/{dia}{pul_txt}<br>"
        f"<span style='font-size:10px;'>{abbr}</span>"
        f"</div>"
    )


def _pa_compact_txt(sis, dia, pul, cls_k: str) -> str:
    """Retorna texto plano compacto para PDF e sort."""
    if not sis or not dia or int(sis) <= 0:
        return "—"
    abbr = _PA_ABBR.get(cls_k, "")
    pul_txt = f" b{int(pul)}" if pul else ""
    return f"{sis}/{dia}{pul_txt} {abbr}".strip()


def _gerar_pdf_lista(df: pd.DataFrame, label_periodo: str) -> bytes:
    """Gera PDF tabular da lista de alunos respeitando a ordenação atual."""
    from fpdf import FPDF

    def _s(text: str) -> str:
        """Sanitiza texto para Latin-1: substitui chars problemáticos e descarta o resto."""
        return (
            str(text)
            .replace("\u2014", "-")    # em dash —
            .replace("\u2013", "-")    # en dash –
            .replace("\u2764", "")     # ❤
            .replace("\u00b7", ".")    # · middle dot
            .replace("\u2019", "'")   # ' right single quote
            .replace("\u201c", '"')    # " left double quote
            .replace("\u201d", '"')    # " right double quote
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )

    _label_pdf = _s(label_periodo)
    _total_pdf = len(df)

    class _PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 7, _s("IMBRA - Lista de Alunos"), align="C",
                      new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 8)
            self.cell(
                0, 5,
                _s(f"Periodo: {_label_pdf}  |  Gerado em: "
                   f"{datetime.date.today().strftime('%d/%m/%Y')}  |  "
                   f"Total: {_total_pdf} aluno(s)"),
                align="C", new_x="LMARGIN", new_y="NEXT",
            )
            self.ln(2)

        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 7)
            self.cell(0, 8, _s(f"Pag. {self.page_no()}"), align="C")

    pdf = _PDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=14)

    hdrs   = ["#", "Nome", "Turma", "Nasc.", "Aulas", "Pres.", "Taxa%", "Ult. PA"]
    widths = [8,   65,    32,     22,      13,      13,      16,      60]

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(30, 77, 216)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(widths, hdrs):
        pdf.cell(w, 6, _s(h), border=0, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)

    for i, (_, a) in enumerate(df.iterrows()):
        if i % 2 == 0:
            pdf.set_fill_color(239, 246, 255)
        else:
            pdf.set_fill_color(255, 255, 255)

        _dn = a.get("data_nascimento")
        try:
            dn_fmt = pd.to_datetime(_dn).strftime("%d/%m/%Y") if pd.notna(_dn) and _dn else "-"
        except Exception:
            dn_fmt = "-"

        _aulas = int(a.get("total_aulas", 0))
        taxa_txt = f"{float(a.get('taxa_presenca', 0)):.1f}%" if _aulas > 0 else "-"
        pa_txt   = str(a.get("_pa_txt", "") or "-")[:28]

        vals = [
            str(i + 1),
            str(a.get("nome", ""))[:36],
            str(a.get("turma", ""))[:18],
            dn_fmt,
            str(int(a.get("total_aulas", 0))),
            str(int(a.get("total_presencas", 0))),
            taxa_txt,
            pa_txt,
        ]
        for w, v in zip(widths, vals):
            pdf.cell(w, 5, _s(v), border=0, fill=True)
        pdf.ln()

    return bytes(pdf.output())


# ==============================================================================
# 🛠️ MOTORES DE DADOS (ALTA PERFORMANCE)
# ==============================================================================


@st.cache_data(ttl=300, show_spinner=False)
def obter_todos_alunos_cache():
    return buscar_alunos_geral("")


@st.cache_data(ttl=300, show_spinner=False)
def carregar_dados_crm_avaliacoes_senior():
    """Motor de processamento em lote. Separa Ativos do Arquivo Morto."""
    try:
        # Usando .from_() para proteção do Supabase
        res_al = supabase.from_("alunos").select("*").execute()
        df_al = pd.DataFrame(res_al.data)
        if df_al.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Garante que a coluna status existe no DF
        if 'status' not in df_al.columns:
            df_al['status'] = 'Ativo'

        # SEPARAÇÃO: Arquivo Morto vs Ativos
        df_inativos = df_al[df_al['status'] == 'Inativo'].copy()
        df_ativos = df_al[df_al['status'] != 'Inativo'].copy()

        if df_ativos.empty:
             return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), df_inativos

        res_av = (
            supabase.from_("prontuario_avaliacoes")
            .select("aluno_id, data_avaliacao")
            .execute()
        )
        df_av = pd.DataFrame(res_av.data)

        _todos_freq = []
        _off_freq = 0
        for _ in range(500):
            _r_freq = (
                supabase.from_("frequencia")
                .select("aluno_id, status, data_aula")
                .order("id")
                .range(_off_freq, _off_freq + 999)
                .execute()
            )
            if _r_freq.data:
                _todos_freq.extend(_r_freq.data)
            if not _r_freq.data or len(_r_freq.data) < 1000:
                break
            _off_freq += 1000
        df_f_bruto = pd.DataFrame(_todos_freq) if _todos_freq else pd.DataFrame(columns=["aluno_id", "status", "data_aula"])
        if not df_f_bruto.empty and "data_aula" in df_f_bruto.columns:
            df_f_bruto["data_aula"] = pd.to_datetime(df_f_bruto["data_aula"], errors="coerce")
        # guarda cópia limpa com datas para uso nos filtros de período
        df_freq_datado = df_f_bruto.copy() if not df_f_bruto.empty else pd.DataFrame(columns=["aluno_id","status","data_aula"])

        if not df_av.empty:
            df_av["data_avaliacao"] = pd.to_datetime(
                df_av["data_avaliacao"], errors="coerce"
            )
            df_av_latest = (
                df_av.groupby("aluno_id")["data_avaliacao"].max().reset_index()
            )
            df_merged = pd.merge(
                df_ativos, df_av_latest, left_on="id", right_on="aluno_id", how="left"
            )
        else:
            df_merged = df_ativos.copy()
            df_merged["data_avaliacao"] = pd.NaT

        if not df_f_bruto.empty:
            df_stats = (
                df_f_bruto.groupby("aluno_id")
                .agg(
                    total_aulas=("status", "count"),
                    total_presencas=("status", lambda x: (x == "PRESENTE").sum()),
                )
                .reset_index()
            )
            df_merged = pd.merge(
                df_merged, df_stats, left_on="id", right_on="aluno_id", how="left"
            )
        else:
            df_merged["total_aulas"] = 0
            df_merged["total_presencas"] = 0

        df_merged["total_presencas"] = (
            df_merged["total_presencas"].fillna(0).astype(int)
        )
        df_merged["total_aulas"] = df_merged["total_aulas"].fillna(0).astype(int)
        df_merged["taxa_presenca"] = (
            df_merged["total_presencas"] / df_merged["total_aulas"] * 100
        ).fillna(0.0)

        hoje = pd.Timestamp(datetime.date.today())
        df_merged["dias_passados"] = (hoje - df_merged["data_avaliacao"]).dt.days

        df_medidos = (
            df_merged[df_merged["data_avaliacao"].notna()]
            .sort_values("dias_passados", ascending=False)
            .copy()
        )
        df_nao_medidos = (
            df_merged[df_merged["data_avaliacao"].isna()].sort_values("nome").copy()
        )
        df_todos_crm = df_merged.sort_values("nome").copy()

        return df_medidos, df_nao_medidos, df_todos_crm, df_inativos, df_freq_datado
    except Exception as e:
        st.error(f"Falha Crítica no Motor de Dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ==============================================================================
# 🖥️ RENDERIZAÇÃO DA INTERFACE
# ==============================================================================
def renderizar_dashboard():
    # Injeção de CSS para o Action Grid + Micro Avatar + Hover Zoom
    st.markdown(
        """
    <style>
        .header-portal { background: linear-gradient(135deg, #F8FAFC 0%, #E0F2FE 100%); padding: 25px; border-radius: 12px; border-left: 6px solid #1E88E5; margin-bottom: 15px; }
        .header-portal h1 { color: #0A2540; font-size: 28px; margin: 0 0 5px 0; font-weight: 900; }
        .header-portal p { color: #64748B; font-size: 15px; margin: 0; font-weight: 500; }

        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] { overflow: visible !important; }

        .linha-divisoria { height: 1px; background-color: #E2E8F0; margin: 4px 0px 8px 0px; }
        .btn-compact button { min-height: 36px !important; padding: 4px 8px !important; font-size: 13px !important; }
        .grid-header { display:flex; background-color:#F8FAFC; padding:12px; border-radius:6px; font-weight:800; color:#475569; font-size:12px; border: 1px solid #E2E8F0; margin-bottom: 5px; text-transform: uppercase; }
        .grid-row { display:flex; align-items:center; padding: 8px 0; border-bottom: 1px solid #F1F5F9; }

        .zoom-avatar-dash {
            width: 36px; height: 36px; border-radius: 50%; object-fit: cover;
            border: 2px solid #1E88E5; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 10;
            flex-shrink: 0;
        }
        .zoom-avatar-dash:hover {
            transform: scale(4.0); z-index: 99999 !important; box-shadow: 0px 10px 20px rgba(0,0,0,0.5);
        }
        .avatar-placeholder {
            width: 36px; height: 36px; border-radius: 50%; background-color: #F1F5F9;
            color: #94A3B8; display: flex; align-items: center; justify-content: center;
            font-size: 18px; border: 1px dashed #CBD5E1; flex-shrink: 0;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Limpa caches locais se uma matrícula acabou de ocorrer (sinalizado por triagem_view).
    if st.session_state.pop("_force_reload_crm", False):
        obter_todos_alunos_cache.clear()
        carregar_dados_crm_avaliacoes_senior.clear()

    df_medidos, df_nao_medidos, df_todos_crm, df_inativos, df_freq_datado = carregar_dados_crm_avaliacoes_senior()

    if df_todos_crm.empty and df_inativos.empty:
        st.warning("A base de dados de alunos está vazia.")
        # Não damos return aqui para permitir o cadastro do primeiro aluno via busca.

    # ==========================================================================
    # 1. PAINEL DE CONTROLE (HERO SECTION & TABS) - MOVIDO PARA O TOPO
    # ==========================================================================
    st.markdown("""
        <div class="header-portal">
            <h1>🩺 Portal do Aluno & Gestão Clínica</h1>
            <p>Central de Admissões, Prontuários, Arquivo Morto e Agenda da Semana.</p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.pop("_abrir_triagem", False):
        st.info(
            "📥 Você chegou pelo relatório para **aprovar novos cadastros**. "
            "Abra a aba **🆕 TRIAGEM** abaixo para conferir documentos e aprovar.",
            icon="👉",
        )

    # ── Filtra abas do Portal conforme permissões do operador ───────────────
    def _portal_lib(chave: str) -> bool:
        if st.session_state.get("perfil") == "SuperAdmin":
            return True
        _p = st.session_state.get("_menu_perms_cache") or {}
        return _p.get(chave, True)

    _DASH_ABAS_CFG = [
        ("portal_tab_alunos",       "👥 Alunos"),
        ("portal_tab_patologias",   "🧬 Patologias"),
        ("portal_tab_cracha",       "🪪 Cara-crachá"),
        ("portal_tab_novo_aluno",   "📝 NOVO Aluno"),
        ("portal_tab_triagem",      "🆕 TRIAGEM"),
        ("portal_tab_agenda",       "🗓️ Agenda Med"),
        ("portal_tab_medidos",      f"📊 Já Medidos ({len(df_medidos)})"),
        ("portal_tab_sem_medicoes", f"⚠️ Sem Medições ({len(df_nao_medidos)})"),
        ("portal_tab_inativos",     f"🗄️ Arquivo Morto ({len(df_inativos)})"),
        ("portal_tab_pa",           "🩸 Pressão Arterial"),
    ]
    _dash_vis = [(c, n) for c, n in _DASH_ABAS_CFG if _portal_lib(c)]

    _tabs_dash = st.tabs([n for _, n in _dash_vis])
    _tab_d = {c: _tabs_dash[i] for i, (c, _) in enumerate(_dash_vis)}

    tab_alunos    = _tab_d.get("portal_tab_alunos")
    tab_patologias = _tab_d.get("portal_tab_patologias")
    tab_cracha    = _tab_d.get("portal_tab_cracha")
    tab_novo_cad  = _tab_d.get("portal_tab_novo_aluno")
    tab_triagem   = _tab_d.get("portal_tab_triagem")
    tab_ag        = _tab_d.get("portal_tab_agenda")
    tab_med       = _tab_d.get("portal_tab_medidos")
    tab_novos     = _tab_d.get("portal_tab_sem_medicoes")
    tab_inativos  = _tab_d.get("portal_tab_inativos")
    tab_pa        = _tab_d.get("portal_tab_pa")

    # --- ABA 1: AGENDA SEMANAL ---
    if tab_ag is not None:
        with tab_ag:
            try:
                agenda_atual = get_agendamentos_pendentes()
                if agenda_atual:
                    st.markdown(
                        "<div style='border-top: 2px solid #1E88E5; margin-bottom: 8px;'></div>",
                        unsafe_allow_html=True,
                    )
                    for ag in agenda_atual:
                        cd, ci, cb = st.columns([1, 4, 1.5], vertical_alignment="center")
                        dt = datetime.datetime.strptime(ag["data_agendamento"], "%Y-%m-%d")
                        cd.markdown(
                            f"<div style='text-align:center; padding: 6px 0;'><strong style='color:#1E88E5;font-size:16px;'>{dt.day}/{dt.strftime('%m')}</strong></div>",
                            unsafe_allow_html=True,
                        )
                        ci.markdown(
                            f"<div style='padding: 6px 0;'><strong style='font-size:14.5px;'>{ag['alunos']['nome']}</strong><br><span style='font-size:13px;color:#64748B;'>🕒 {ag['horario']} - {ag['motivo']}</span></div>",
                            unsafe_allow_html=True,
                        )
                        with cb:
                            st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                            if st.button(
                                "🩺 Avaliar",
                                key=f"go_{ag['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                st.session_state.aluno_prontuario = ag["alunos"]
                                concluir_ou_cancelar_agendamento(ag["id"], "Concluído")
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        st.markdown(
                            "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                        )
                else:
                    st.info("Nenhuma avaliação pendente na agenda.")
            except:
                pass

    # --- ABA 2: JÁ MEDIDOS (CRM DE INATIVIDADE) ---
    if tab_med is not None:
        with tab_med:
            if not df_medidos.empty:
                filtro_dias = st.selectbox(
                    "Status de Inatividade:",
                    ["Ver Todos", "Mais de 30 dias", "Mais de 60 dias", "Mais de 90 dias"],
                    label_visibility="collapsed",
                )
                limites = {
                    "Mais de 30 dias": 30,
                    "Mais de 60 dias": 60,
                    "Mais de 90 dias": 90,
                }
                df_exibir_m = (
                    df_medidos[df_medidos["dias_passados"] >= limites[filtro_dias]]
                    if filtro_dias != "Ver Todos"
                    else df_medidos
                )

                for _, a in df_exibir_m.iterrows():
                    c1, c2, c3, c4 = st.columns([3, 0.8, 0.8, 0.8], vertical_alignment="center")

                    # Renderiza o Avatar
                    foto_url = a.get('foto_url')
                    if pd.notna(foto_url) and str(foto_url).strip() and str(foto_url).strip().lower() not in ["none", "nan", "null", ""]:
                        avatar_html = f"<img src='{foto_url}' class='zoom-avatar-dash' alt='Foto'>"
                    else:
                        avatar_html = "<div class='avatar-placeholder'>👤</div>"

                    cor_alerta = "#B91C1C" if a["dias_passados"] >= 90 else "#64748B"
                    icone = "⚠️" if a["dias_passados"] >= 90 else "✔️"

                    c1.markdown(f"""
                        <div style='display: flex; align-items: center; gap: 12px; padding: 4px 0;'>
                            {avatar_html}
                            <div style='line-height:1.3;'>
                                <strong style='font-size: 14px; color:#0F172A;'>{a['nome']}</strong><br>
                                <span style='color:{cor_alerta}; font-size: 12px;'>{icone} Última: {a['data_avaliacao'].strftime('%d/%m/%Y')} <b>({int(a['dias_passados'])} dias)</b></span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    with c2:
                        st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                        if st.button("🗓️", key=f"med_ag_{a['id']}", help="Agendar"):
                            st.session_state[f"f_ag_{a['id']}"] = True
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c3:
                        st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                        if st.button(
                            "🩺",
                            key=f"med_av_{a['id']}",
                            type="primary",
                            help="Abrir Ficha",
                        ):
                            st.session_state.aluno_prontuario = a.to_dict()
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c4:
                        st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_{a['id']}", help="Excluir Aluno"):
                            st.session_state[f"del_mode_{a['id']}"] = True
                        st.markdown("</div>", unsafe_allow_html=True)

                    # Modal de Confirmação de Exclusão
                    if st.session_state.get(f"del_mode_{a['id']}"):
                        with st.container(border=True):
                            st.error(f"Deseja excluir {a['nome']}?")
                            if st.button("Confirmar Exclusão", key=f"c_del_{a['id']}"):
                                excluir_aluno_completo(
                                    a["id"], st.session_state.get("usuario_email")
                                )
                                st.rerun()
                            if st.button("Cancelar", key=f"can_{a['id']}"):
                                st.session_state[f"del_mode_{a['id']}"] = False
                                st.rerun()

                    # Modal de Agendamento Rápido
                    if st.session_state.get(f"f_ag_{a['id']}", False):
                        with st.container(border=True):
                            st.write(f"Agendar para {a['nome']}")
                            ca, cb = st.columns(2)
                            d_esc = ca.date_input(
                                "Data:",
                                min_value=datetime.date.today(),
                                key=f"d_m_{a['id']}",
                            )
                            h_esc = cb.time_input(
                                "Hora:", value=datetime.time(8, 0), key=f"h_m_{a['id']}"
                            )
                            if st.button(
                                "Confirmar Agendamento",
                                key=f"cf_m_{a['id']}",
                                type="primary",
                            ):
                                criar_agendamento(
                                    a["id"], d_esc, h_esc.strftime("%H:%M"), "Reavaliação"
                                )
                                st.session_state[f"f_ag_{a['id']}"] = False
                                st.rerun()
                    st.markdown(
                        "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                    )

    # --- ABA 3: AGUARDANDO MEDIÇÃO ---
    if tab_novos is not None:
        with tab_novos:
            if not df_nao_medidos.empty:
                for _, a in df_nao_medidos.iterrows():
                    c1, c2, c3 = st.columns([3.5, 0.8, 0.8], vertical_alignment="center")

                    # Renderiza o Avatar
                    foto_url = a.get('foto_url')
                    if pd.notna(foto_url) and str(foto_url).strip() and str(foto_url).strip().lower() not in ["none", "nan", "null", ""]:
                        avatar_html = f"<img src='{foto_url}' class='zoom-avatar-dash' alt='Foto'>"
                    else:
                        avatar_html = "<div class='avatar-placeholder'>👤</div>"

                    c1.markdown(f"""
                        <div style='display: flex; align-items: center; gap: 12px;'>
                            {avatar_html}
                            <div style='line-height:1.3;'>
                                <strong style='font-size:14px; color:#0F172A;'>{a['nome']}</strong><br>
                                <span style='font-size:12px;color:#64748B;'>Aguardando primeira medição</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    with c2:
                        st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                        if st.button("🗓️", key=f"n_ag_{a['id']}"):
                            st.session_state[f"f_ag_{a['id']}"] = True
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c3:
                        st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                        if st.button("🩺", key=f"n_av_{a['id']}", type="primary"):
                            st.session_state.aluno_prontuario = a.to_dict()
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown(
                        "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                    )

    # --- ABA 5: ARQUIVO MORTO ---
    if tab_inativos is not None:
        with tab_inativos:
            st.markdown("### 🗄️ Arquivo Morto")
            st.caption("Alunos desativados. Os dados clínicos ficam preservados. Use **📂 Ver Ficha** para editar, excluir ou gerar dossiê. Use **↩️ Reativar** para devolver ao sistema.")

            if df_inativos.empty:
                st.success("Nenhum aluno no Arquivo Morto.")
            else:
                # --- BUSCA DENTRO DO ARQUIVO ---
                if HAS_KEYUP:
                    busca_inativo = st_keyup(
                        "🔍 Buscar no Arquivo Morto:",
                        placeholder="🔍 Filtrar (mín. 2 letras)...",
                        key="busca_arquivo_morto",
                        label_visibility="collapsed",
                        debounce=300,
                    )
                else:
                    busca_inativo = st.text_input(
                        "🔍 Buscar no Arquivo Morto:",
                        placeholder="Digite parte do nome...",
                        key="busca_arquivo_morto",
                        label_visibility="collapsed",
                    )

                df_exibir = df_inativos.copy()
                if busca_inativo and len(busca_inativo.strip()) >= 2:
                    df_exibir = filtrar_alunos_df(df_exibir, busca_inativo, cols=["nome"], min_len=2)

                # --- FILTRO POR MOTIVO DE SAÍDA ---
                _MOTIVOS_SAIDA = ["Óbito", "Desistência", "Transferência", "Conclusão", "Outro"]
                _motivos_disponiveis = ["Todos"] + sorted(
                    [m for m in _MOTIVOS_SAIDA if m in df_inativos.get("motivo_saida", pd.Series(dtype=str)).dropna().unique().tolist()]
                ) if "motivo_saida" in df_inativos.columns else ["Todos"]
                if len(_motivos_disponiveis) > 1:
                    _filtro_motivo = st.selectbox(
                        "🚪 Filtrar por motivo de saída:",
                        _motivos_disponiveis,
                        key="filtro_motivo_saida_arq",
                    )
                    if _filtro_motivo != "Todos":
                        df_exibir = df_exibir[df_exibir.get("motivo_saida", pd.Series(dtype=str)) == _filtro_motivo] if "motivo_saida" in df_exibir.columns else df_exibir

                if df_exibir.empty:
                    st.info("Nenhum aluno encontrado para essa busca.")
                else:
                    st.caption(f"Exibindo **{len(df_exibir)}** de {len(df_inativos)} arquivados.")

                # --- EXPORTAÇÃO EXCEL DO ARQUIVO MORTO ---
                if not df_exibir.empty and "motivo_saida" in df_inativos.columns:
                    _colunas_export = ["nome", "turma", "motivo_saida", "data_saida", "obs_saida"]
                    _colunas_exist  = [c for c in _colunas_export if c in df_exibir.columns]
                    if _colunas_exist:
                        _df_exp = df_exibir[_colunas_exist].copy()
                        _rename_map = {
                            "nome": "Nome do Aluno", "turma": "Última Turma",
                            "motivo_saida": "Motivo de Saída", "data_saida": "Data de Saída",
                            "obs_saida": "Observação",
                        }
                        _df_exp.rename(columns={k: v for k, v in _rename_map.items() if k in _df_exp.columns}, inplace=True)
                        _buf_exp = io.BytesIO()
                        with pd.ExcelWriter(_buf_exp, engine="xlsxwriter") as _wr:
                            _df_exp.to_excel(_wr, index=False, sheet_name="Arquivo_Morto")
                            _ws = _wr.sheets["Arquivo_Morto"]
                            _ws.set_column(0, 0, 35)
                            _ws.set_column(1, 1, 20)
                            _ws.set_column(2, 2, 20)
                            _ws.set_column(3, 3, 15)
                            _ws.set_column(4, 4, 40)
                        st.download_button(
                            "📥 Exportar lista (Excel)",
                            _buf_exp.getvalue(),
                            f"Arquivo_Morto_{datetime.date.today().strftime('%d_%m_%Y')}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

                is_super = st.session_state.get("perfil") == "SuperAdmin"
                email_op = (
                    st.session_state.get("usuario_email")
                    or st.session_state.get("email_usuario")
                    or st.session_state.get("email", "sistema")
                )

                for _, a in df_exibir.iterrows():
                    chave_excl = f"conf_excluir_{a['id']}"
                    aguardando_excl = is_super and st.session_state.get(chave_excl)

                    # Destaque vermelho na linha que aguarda confirmação de exclusão
                    if aguardando_excl:
                        st.markdown(
                            f"<div style='background:#FEF2F2; border:2px solid #EF4444; border-radius:8px; padding:6px 10px; margin-bottom:2px;'>"
                            f"<span style='color:#B91C1C; font-size:12px; font-weight:700;'>⚠️ Confirmar exclusão permanente de: {a['nome']}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    cols = [4, 1.1, 1.1, 1.1] if is_super else [4, 1.1, 1.1]
                    colunas = st.columns(cols, vertical_alignment="center")
                    c1 = colunas[0]
                    c2 = colunas[1]
                    c3 = colunas[2]
                    c4 = colunas[3] if is_super else None

                    foto_url = a.get('foto_url')
                    if pd.notna(foto_url) and str(foto_url).strip() and str(foto_url).strip().lower() not in ["none", "nan", "null", ""]:
                        avatar_html = f"<img src='{foto_url}' class='zoom-avatar-dash' style='filter: grayscale(100%); opacity: 0.7;' alt='Foto'>"
                    else:
                        avatar_html = "<div class='avatar-placeholder' style='background-color: #F8FAFC; color: #CBD5E1;'>👤</div>"

                    ultima_turma = a.get('turma') or 'N/A'
                    _motivo_s = str(a.get('motivo_saida') or '').strip()
                    _data_s   = str(a.get('data_saida')   or '').strip()
                    _obs_s    = str(a.get('obs_saida')    or '').strip()
                    _ICONE_MOT = {"Óbito": "⚰️", "Desistência": "🚪", "Transferência": "🔄", "Conclusão": "🎓", "Outro": "📋"}
                    _icone_mot = _ICONE_MOT.get(_motivo_s, "📋") if _motivo_s else ""
                    # Formata data de saída para dd/mm/aaaa
                    if _data_s and _data_s not in ("None", "nan", "—"):
                        try:
                            import datetime as _dt
                            _data_s_fmt = _dt.date.fromisoformat(_data_s).strftime("%d/%m/%Y")
                        except Exception:
                            _data_s_fmt = _data_s
                    else:
                        _data_s_fmt = ""
                    _linha_saida = ""
                    if _motivo_s:
                        _linha_saida = f"<br><span style='font-size:11px;color:#64748B;'>{_icone_mot} <b>Motivo:</b> {_motivo_s}"
                        if _data_s_fmt:
                            _linha_saida += f" &nbsp;·&nbsp; 📅 {_data_s_fmt}"
                        _linha_saida += "</span>"
                    if _obs_s:
                        _linha_saida += f"<br><span style='font-size:11px;color:#94A3B8;font-style:italic;'>💬 {_obs_s}</span>"

                    c1.markdown(f"""
                        <div style='display: flex; align-items: center; gap: 12px;'>
                            {avatar_html}
                            <div style='line-height:1.4;'>
                                <strong style='font-size:14px; color:#64748B;'>{a['nome']}</strong><br>
                                <span style='font-size:12px;color:#94A3B8;'>🗄️ Arquivado · Última Turma: <strong>{ultima_turma}</strong></span>
                                {_linha_saida}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    with c2:
                        if st.button("📂 Ver Ficha", key=f"in_av_{a['id']}", use_container_width=True):
                            st.session_state.aluno_prontuario = a.to_dict()
                            st.rerun()

                    with c3:
                        chave_conf = f"conf_reativar_{a['id']}"
                        if st.session_state.get(chave_conf):
                            col_sim, col_nao = st.columns(2)
                            with col_sim:
                                if st.button("✅", key=f"sim_reat_{a['id']}", help="Confirmar reativação", use_container_width=True):
                                    ok, msg = alterar_status_aluno(a['id'], "Ativo")
                                    st.session_state.pop(chave_conf, None)
                                    if ok:
                                        st.success(f"{a['nome']} reativado!")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            with col_nao:
                                if st.button("❌", key=f"nao_reat_{a['id']}", help="Cancelar", use_container_width=True):
                                    st.session_state.pop(chave_conf, None)
                                    st.rerun()
                        else:
                            if st.button("↩️ Reativar", key=f"reat_{a['id']}", use_container_width=True):
                                st.session_state[chave_conf] = True
                                st.rerun()

                    # --- BOTÃO EXCLUIR (somente SuperAdmin) ---
                    if is_super and c4 is not None:
                        with c4:
                            if st.session_state.get(chave_excl):
                                col_ok, col_x = st.columns(2)
                                with col_ok:
                                    if st.button("✅", key=f"sim_excl_{a['id']}", help="Confirmar exclusão permanente", use_container_width=True):
                                        ok, msg = excluir_aluno_completo(a['id'], email_op)
                                        st.session_state.pop(chave_excl, None)
                                        if ok:
                                            st.success(f"'{a['nome']}' excluído permanentemente.")
                                            st.rerun()
                                        else:
                                            st.error(f"Erro: {msg}")
                                with col_x:
                                    if st.button("❌", key=f"nao_excl_{a['id']}", help="Cancelar", use_container_width=True):
                                        st.session_state.pop(chave_excl, None)
                                        st.rerun()
                            else:
                                if st.button("🗑️ Excluir", key=f"excl_{a['id']}", use_container_width=True, type="secondary", help="Exclusão permanente — irreversível"):
                                    st.session_state[chave_excl] = True
                                    st.rerun()

                    st.markdown("<div class='linha-divisoria'></div>", unsafe_allow_html=True)

    # --- ABA 6: NOVOS ALUNOS (TRIAGEM) ---
    if tab_triagem is not None:
        with tab_triagem:
            st.markdown("### 📥 Caixa de Entrada de Inscrições")
            st.caption("Aprove, edite ou rejeite os pré-cadastros vindos do formulário público.")

            from views.triagem_view import tela_triagem
            tela_triagem()

    # --- ABA 7: NOVO CADASTRO ---
    if tab_novo_cad is not None:
        with tab_novo_cad:
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
                "Preencha os dados da ficha com calma. Ao concluir, o aluno estará disponível "
                "na aba **🆕 NOVOS ALUNOS (Triagem)** para aprovação e alocação de turma."
            )

            from views.inscricao_publica_view import tela_inscricao_publica_move_right
            tela_inscricao_publica_move_right(modo_admin=True)

    # --- ABA: ALUNOS (DIRETÓRIO GLOBAL) ---
    if tab_alunos is not None:
        with tab_alunos:

            # ==========================================================================
            # 2. ACTION GRID (DIRETÓRIO GLOBAL) - MOVIDO PARA A BASE
            # ==========================================================================
            st.markdown("### 🔍 Diretório de Alunos e Emissão de Dossiês")

            with st.container(border=True):
                # Inicializa estado de ordenação por cabeçalho
                if "dash_sort_col" not in st.session_state:
                    st.session_state["dash_sort_col"] = "nome"
                    st.session_state["dash_sort_asc"] = True

                # Sempre exibe histórico completo
                hoje_ts = pd.Timestamp(datetime.date.today())
                corte = None
                label_periodo = "Histórico"

                # Recalcula métricas de frequência para o período selecionado
                if not df_freq_datado.empty and corte is not None:
                    df_periodo = df_freq_datado[df_freq_datado["data_aula"] >= corte].copy()
                else:
                    df_periodo = df_freq_datado.copy()

                _cols_drop = [c for c in ("total_aulas","total_presencas","taxa_presenca","aluno_id","dias_passados") if c in df_todos_crm.columns]
                df_base_periodo = df_todos_crm.drop(columns=_cols_drop).copy()

                if not df_periodo.empty:
                    # ── Presenças por aluno no período ────────────────────────────────
                    _pres_p = (
                        df_periodo.groupby("aluno_id")
                        .agg(total_presencas=("status", lambda x: (x == "PRESENTE").sum()))
                        .reset_index()
                    )

                    # ── Aulas por TURMA no período (datas distintas) ──────────────────
                    # Mapeia aluno_id → turma para identificar a turma de cada registro
                    _id_to_turma = df_todos_crm.set_index("id")["turma"].to_dict()
                    _df_per = df_periodo.copy()
                    _df_per["_turma"] = _df_per["aluno_id"].map(_id_to_turma)
                    _aulas_turma = (
                        _df_per.dropna(subset=["_turma", "data_aula"])
                        .drop_duplicates(subset=["_turma", "data_aula"])
                        .groupby("_turma")
                        .size()
                        .reset_index(name="total_aulas")
                        .rename(columns={"_turma": "turma"})
                    )

                    # ── Monta df_base_periodo ─────────────────────────────────────────
                    df_base_periodo = df_base_periodo.merge(
                        _pres_p, left_on="id", right_on="aluno_id", how="left"
                    )
                    df_base_periodo = df_base_periodo.merge(
                        _aulas_turma, on="turma", how="left"
                    )
                else:
                    df_base_periodo["total_aulas"]     = 0
                    df_base_periodo["total_presencas"] = 0

                df_base_periodo["total_aulas"]     = df_base_periodo["total_aulas"].fillna(0).astype(int)
                df_base_periodo["total_presencas"] = df_base_periodo["total_presencas"].fillna(0).astype(int)
                df_base_periodo["taxa_presenca"]   = (
                    df_base_periodo["total_presencas"] / df_base_periodo["total_aulas"].replace(0, pd.NA) * 100
                ).fillna(0.0)

                # Risco de evasão: considera 0 presenças no período = sem registro
                def _risco(row):
                    if row["total_aulas"] == 0:
                        return ("⚫", "#94A3B8", "Sem aula no período")
                    t = row["taxa_presenca"]
                    if t >= 75:
                        return ("🟢", "#10B981", "Regular")
                    elif t >= 50:
                        return ("🟡", "#F59E0B", "Atenção")
                    else:
                        return ("🔴", "#EF4444", "Risco de Evasão")

                df_base_periodo[["_risco_icon","_risco_cor","_risco_label"]] = pd.DataFrame(
                    df_base_periodo.apply(_risco, axis=1).tolist(),
                    index=df_base_periodo.index
                )

                # ── Dados de PA (última medição por aluno) ────────────────────────────
                _pa_dict = get_ultima_pa_todos()
                def _pa_row(row):
                    pa = _pa_dict.get(str(row.get("id", "")), {})
                    sis = pa.get("sis") or 0
                    dia = pa.get("dia") or 0
                    pul = pa.get("pul")
                    cls = pa.get("cls", "")
                    return pd.Series({
                        "_pa_sis":  int(sis) if sis else 0,
                        "_pa_txt":  _pa_compact_txt(sis, dia, pul, cls),
                        "_pa_html": _pa_compact_html(sis, dia, pul, cls),
                        "_pa_cls":  cls,
                        "_pa_pul":  int(pul) if pul else 0,
                    })
                df_base_periodo = pd.concat(
                    [df_base_periodo, df_base_periodo.apply(_pa_row, axis=1)], axis=1
                )

                st.markdown("<hr style='margin:8px 0 4px 0;border-color:#E2E8F0;'/>", unsafe_allow_html=True)

                # Controles Superiores
                c_busca, c_imp, c_pag = st.columns([4, 1, 1], vertical_alignment="bottom")

                # 🚀 BUSCA COM SUGESTÕES EM TEMPO REAL
                with c_busca:
                    busca, _ = busca_com_sugestoes(
                        df_base_periodo,
                        key="busca_dash",
                        placeholder="🔍 Digite pelo menos 3 letras do nome ou turma…",
                        label="Buscar aluno:",
                        debounce=250,
                        max_sugestoes=8,
                    )

                # Aplicação de Filtros no grid (Gatilho de 3 caracteres)
                df_grid = df_base_periodo.copy()
                if busca:
                    busca_limpa = normalizar_fonetica(busca).strip()
                    if len(busca_limpa) >= 3:
                        df_grid = filtrar_alunos_df(df_grid, busca, cols=["nome", "turma"], min_len=3)

                # Aplicação de Ordenação via session_state (cabeçalhos clicáveis)
                _scol = st.session_state.get("dash_sort_col", "nome")
                _sasc = st.session_state.get("dash_sort_asc", True)
                if _scol == "data_nascimento":
                    df_grid["_sort_dn"] = pd.to_datetime(df_grid["data_nascimento"], errors="coerce")
                    df_grid = df_grid.sort_values("_sort_dn", ascending=_sasc, na_position="last")
                    df_grid = df_grid.drop(columns=["_sort_dn"])
                elif _scol == "_pa_sis":
                    df_grid = df_grid.sort_values("_pa_sis", ascending=_sasc, na_position="last")
                else:
                    df_grid = df_grid.sort_values(_scol, ascending=_sasc, na_position="last")

                # ── Botão de impressão PDF (lista com ordenação atual) ────────────────
                _pdf_lista_key = "pdf_lista_grid"
                if st.session_state.get(_pdf_lista_key):
                    c_imp.download_button(
                        "📥 PDF",
                        data=st.session_state[_pdf_lista_key],
                        file_name=f"Lista_Alunos_{label_periodo.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key="dl_lista_pdf",
                        type="primary",
                        use_container_width=True,
                    )
                else:
                    if c_imp.button("🖨️ Imprimir", key="btn_imp_lista",
                                    use_container_width=True, help="Gerar PDF da lista com a ordenação atual"):
                        with st.spinner("Gerando PDF…"):
                            st.session_state[_pdf_lista_key] = _gerar_pdf_lista(df_grid, label_periodo)
                        st.rerun()

                # Paginação
                itens_por_pagina = 15
                total_pags = max(1, math.ceil(len(df_grid) / itens_por_pagina))
                pagina = c_pag.number_input(
                    f"Pág. (de {total_pags})",
                    min_value=1,
                    max_value=total_pags,
                    value=1,
                    label_visibility="collapsed",
                )

                inicio, fim = (pagina - 1) * itens_por_pagina, pagina * itens_por_pagina
                df_page = df_grid.iloc[inicio:fim]

                # Cabeçalho do Action Grid — botões clicáveis de ordenação
                def _sort_icon(col_key):
                    if st.session_state.get("dash_sort_col") == col_key:
                        return " ▲" if st.session_state.get("dash_sort_asc", True) else " ▼"
                    return ""

                def _on_sort(col_key):
                    if st.session_state.get("dash_sort_col") == col_key:
                        st.session_state["dash_sort_asc"] = not st.session_state.get("dash_sort_asc", True)
                    else:
                        st.session_state["dash_sort_col"] = col_key
                        st.session_state["dash_sort_asc"] = True

                st.markdown(
                    "<style>.sort-header button{background:transparent!important;border:none!important;"
                    "font-weight:700!important;color:#0F172A!important;padding:4px 2px!important;"
                    "font-size:13px!important;cursor:pointer!important;width:100%;}"
                    ".sort-header button:hover{color:#1D4ED8!important;}</style>",
                    unsafe_allow_html=True,
                )
                with st.container():
                    st.markdown("<div class='sort-header'>", unsafe_allow_html=True)
                    gh0, gh1, gh2, gh3, gh4, gh5, gh6 = st.columns([3, 0.8, 0.8, 0.8, 1.2, 1.5, 2])
                    if gh0.button(f"Aluno / Turma{_sort_icon('nome')}", key="sh_nome", use_container_width=True):
                        _on_sort("nome"); st.rerun()
                    if gh1.button(f"Nasc.{_sort_icon('data_nascimento')}", key="sh_nasc", use_container_width=True):
                        _on_sort("data_nascimento"); st.rerun()
                    if gh2.button(f"Aulas{_sort_icon('total_aulas')}", key="sh_aulas", use_container_width=True):
                        _on_sort("total_aulas"); st.rerun()
                    if gh3.button(f"Pres.{_sort_icon('total_presencas')}", key="sh_pres", use_container_width=True):
                        _on_sort("total_presencas"); st.rerun()
                    if gh4.button(f"Taxa/Risco{_sort_icon('taxa_presenca')}", key="sh_taxa", use_container_width=True):
                        _on_sort("taxa_presenca"); st.rerun()
                    if gh5.button(f"Últ. PA{_sort_icon('_pa_sis')}", key="sh_pa", use_container_width=True):
                        _on_sort("_pa_sis"); st.rerun()
                    gh6.markdown("<div style='text-align:center;font-weight:700;font-size:13px;padding:4px 2px;'>Ações</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<hr style='margin:0 0 6px 0;border-color:#CBD5E1;'/>", unsafe_allow_html=True)

                # ======================================================================
                # 🚀 MÁGICA UX: SE NÃO ENCONTRAR, MOSTRA FORMULÁRIO DE CADASTRO RÁPIDO
                # ======================================================================
                if df_page.empty:
                    if busca and len(busca.strip()) >= 3:
                        st.warning(f"🔍 Nenhum aluno encontrado para: **'{busca}'**")

                        with st.container(border=True):
                            st.markdown(f"<h4 style='color:#1E88E5; margin-bottom: 10px; margin-top: 0;'>✨ Criar Novo Cadastro Rápido</h4>", unsafe_allow_html=True)
                            st.caption("Preencha apenas a turma para matricular este aluno imediatamente.")

                            with st.form(key="form_quick_cad"):
                                turmas_df = get_todas_turmas(ativas_apenas=True)
                                lista_turmas = turmas_df["nome"].tolist() if not turmas_df.empty else ["Nenhuma turma disponível"]

                                c_n, c_t = st.columns([2, 1])
                                novo_nome = c_n.text_input("Nome do Aluno:", value=busca.upper().strip(), key="qs_nome")
                                # key estável garante que a seleção persiste mesmo com reruns do st_keyup.
                                nova_turma = c_t.selectbox("Alocar na Turma:", lista_turmas, key="qs_turma_sel")

                                if st.form_submit_button("✅ Cadastrar e Matricular", type="primary", use_container_width=True):
                                    if nova_turma == "Nenhuma turma disponível":
                                        st.error("Crie uma turma primeiro no menu 'Turmas'.")
                                    elif len(novo_nome) < 3:
                                        st.error("O nome deve ter pelo menos 3 letras.")
                                    else:
                                        sucesso = cadastrar_novo_aluno(nome=novo_nome, turma=nova_turma)
                                        if sucesso:
                                            obter_todos_alunos_cache.clear()
                                            carregar_dados_crm_avaliacoes_senior.clear()
                                            st.success(f"🎉 {novo_nome} foi matriculado com sucesso na turma {nova_turma}!")
                                            time.sleep(1.5)
                                            st.rerun()
                                        else:
                                            st.error("Erro ao tentar cadastrar no banco de dados.")
                    else:
                        st.info("Nenhum aluno encontrado para este filtro.")
                else:
                    # Renderização das Linhas do Grid
                    for _, a in df_page.iterrows():
                        c1, c2, c3, c4, c5, c6, c7 = st.columns(
                            [3, 0.8, 0.8, 0.8, 1.2, 1.5, 2], vertical_alignment="center"
                        )

                        # Col 1: Foto + Nome e Turma (MÁGICA DO FLEXBOX)
                        foto_url = a.get('foto_url')
                        if pd.notna(foto_url) and str(foto_url).strip() and str(foto_url).strip().lower() not in ["none", "nan", "null", ""]:
                            avatar_html = f"<img src='{foto_url}' class='zoom-avatar-dash' alt='Foto'>"
                        else:
                            avatar_html = "<div class='avatar-placeholder'>👤</div>"

                        c1.markdown(
                            f"""
                            <div style='display: flex; align-items: center; gap: 12px;'>
                                {avatar_html}
                                <div style='line-height:1.3;'>
                                    <strong style='font-size:14px; color:#0F172A;'>{a['nome']}</strong><br>
                                    <span style='font-size:12px;color:#64748B;'>{a['turma']}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Col 2: Nascimento
                        _dn = a.get("data_nascimento")
                        try:
                            _dn_fmt = pd.to_datetime(_dn).strftime("%d/%m/%Y") if pd.notna(_dn) and _dn else "—"
                        except Exception:
                            _dn_fmt = "—"
                        c2.markdown(
                            f"<div style='text-align:center; font-size:12px; color:#64748B;'>{_dn_fmt}</div>",
                            unsafe_allow_html=True,
                        )

                        # Col 3 e 4: Métricas do período selecionado
                        _aulas = int(a.get("total_aulas", 0))
                        _pres  = int(a.get("total_presencas", 0))
                        _cor_aulas = "#475569" if _aulas > 0 else "#CBD5E1"
                        _cor_pres  = "#10B981" if _pres  > 0 else "#CBD5E1"
                        c3.markdown(
                            f"<div style='text-align:center; font-size:14px; font-weight:600; color:{_cor_aulas};'>{_aulas}</div>",
                            unsafe_allow_html=True,
                        )
                        c4.markdown(
                            f"<div style='text-align:center; font-size:15px; font-weight:900; color:{_cor_pres};'>{_pres}</div>",
                            unsafe_allow_html=True,
                        )

                        # Col 5: Taxa % + badge de risco de evasão
                        taxa         = float(a.get("taxa_presenca", 0.0))
                        risco_icon   = a.get("_risco_icon",  "⚫")
                        risco_cor    = a.get("_risco_cor",   "#94A3B8")
                        risco_label  = a.get("_risco_label", "Sem dados")
                        _aulas_linha = int(a.get("total_aulas", 0))
                        if _aulas_linha == 0:
                            taxa_txt = "—"
                            barra_w  = 0
                        else:
                            taxa_txt = f"{taxa:.1f}%"
                            barra_w  = min(int(taxa), 100)
                        c5.markdown(
                            f"""
                        <div style='text-align:center;'>
                          <span style='font-size:13px;font-weight:800;color:{risco_cor};'>{taxa_txt}</span>
                          <span style='font-size:11px;margin-left:4px;' title='{risco_label}'>{risco_icon}</span>
                        </div>
                        <div style='width:90%;margin:2px auto 0;background:#E2E8F0;border-radius:4px;height:5px;'>
                          <div style='width:{barra_w}%;background:{risco_cor};height:100%;border-radius:4px;'></div>
                        </div>
                        <div style='text-align:center;font-size:9px;color:{risco_cor};margin-top:1px;font-weight:600;'>{risco_label}</div>
                        """,
                            unsafe_allow_html=True,
                        )

                        # Col 6: Última PA compacta
                        c6.markdown(
                            str(a.get("_pa_html", "<span style='color:#CBD5E1;font-size:12px;'>—</span>")),
                            unsafe_allow_html=True,
                        )

                        # Col 7: Botões de Ação Direta
                        with c7:
                            st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                            cb1, cb2, cb3 = st.columns(3, gap="small")

                            if cb1.button(
                                "🩺 Abrir", key=f"abr_{a['id']}", use_container_width=True
                            ):
                                st.session_state.aluno_prontuario = a.to_dict()
                                st.rerun()

                            pdf_key = f"pdf_grid_{a['id']}"
                            word_key = f"word_grid_{a['id']}"

                            if st.session_state.get(pdf_key):
                                cb2.download_button(
                                    "📥 PDF",
                                    data=st.session_state[pdf_key],
                                    file_name=f"Dossie_{a['nome'][:15]}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_grid_{a['id']}",
                                    type="primary",
                                    use_container_width=True,
                                )
                            else:
                                if cb2.button(
                                    "🖨️ PDF",
                                    key=f"dos_{a['id']}",
                                    use_container_width=True,
                                    type="primary",
                                ):
                                    with st.spinner("⏳"):
                                        from gerador_pdf import criar_documento_aluno_pdf
                                        estats = get_estatisticas_frequencia_aluno(a["id"])
                                        historico = get_historico_aulas_aluno(a["id"])
                                        avals = get_avaliacoes_aluno(a["id"])
                                        st.session_state[pdf_key] = criar_documento_aluno_pdf(
                                            a.to_dict(), avals, historico, estats
                                        )
                                    st.rerun()

                            word_err_key = f"word_err_{a['id']}"
                            if st.session_state.get(word_err_key):
                                cb3.error(st.session_state.pop(word_err_key))
                            elif st.session_state.get(word_key):
                                cb3.download_button(
                                    "📥 Word",
                                    data=st.session_state[word_key],
                                    file_name=f"Dossie_{a['nome'][:15]}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key=f"dl_word_{a['id']}",
                                    use_container_width=True,
                                )
                            else:
                                if cb3.button(
                                    "📘 Word",
                                    key=f"wrd_{a['id']}",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Gerando Word…"):
                                        try:
                                            from gerador_word import criar_documento_aluno_word
                                            estats = get_estatisticas_frequencia_aluno(a["id"])
                                            historico = get_historico_aulas_aluno(a["id"])
                                            avals = get_avaliacoes_aluno(a["id"])
                                            _wb = criar_documento_aluno_word(
                                                a.to_dict(), avals, historico, estats
                                            )
                                            if _wb:
                                                st.session_state[word_key] = _wb
                                            else:
                                                st.session_state[word_err_key] = "Falha: gerador retornou vazio."
                                        except Exception as _e:
                                            import traceback
                                            st.session_state[word_err_key] = f"Erro: {_e}"
                                    st.rerun()

                            st.markdown("</div>", unsafe_allow_html=True)

                        st.markdown(
                            "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                        )


    # --- ABA: PATOLOGIAS / ANAMNESE CLÍNICA ---
    if tab_patologias is not None:
        with tab_patologias:
            from views.patologias_clinicas_view import renderizar_aba_patologias
            renderizar_aba_patologias()

    # --- ABA: CARA-CRACHÁ ---
    if tab_cracha is not None:
        with tab_cracha:
            from views.relatorio_identificacao_view import renderizar_aba_caracracha
            renderizar_aba_caracracha()

    # --- ABA: PRESSÃO ARTERIAL ---
    if tab_pa is not None:
        with tab_pa:
            _pa_subtabs = st.tabs(["📲 Lançar Digitalmente", "🖨️ Formulário em Papel"])
            with _pa_subtabs[0]:
                from views.lancamento_pa_lote_view import tela_lancamento_pa_digital
                tela_lancamento_pa_digital()
            with _pa_subtabs[1]:
                from views.relatorio_pa_lote_view import tela_relatorio_pa_lote
                tela_relatorio_pa_lote()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Sincronizar Base de Dados", use_container_width=True):
        obter_todos_alunos_cache.clear()
        carregar_dados_crm_avaliacoes_senior.clear()
        st.rerun()