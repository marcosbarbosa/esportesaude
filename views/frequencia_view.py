# ==============================================================================
# 📄 ARQUIVO: views/frequencia_view.py (ROTEADOR MESTRE)
# 🏷️ VERSÃO: 13.1 (PRO Elite - Roteamento Fiel para Nova Matrícula)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Roteador de frequência, busca global e dropdown espelhado no BD.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import time
import re

from utils.busca_aluno import busca_aluno_widget as _baw_freq, filtrar_alunos_df

# Importação do motor e permissões
from database import (
    buscar_alunos_geral,
    get_alunos_por_turma,
    get_presencas_dia,
    ADMIN_MASTER,
    alterar_status_aluno,
    atualizar_turma_aluno,
    get_todas_turmas,
    alternar_presenca,
    get_ultima_presenca_batch,
    get_numero_aula_no_ano,
    get_aulas_por_mes_no_ano,
    get_datas_letivas_detalhadas_no_ano,
    get_datas_comemorativas_bd,
    get_datas_comemorativas_custom,
)
from modulos_frequencia.tab_tablet import renderizar_aba_terminal
from modulos_frequencia.tab_diario import renderizar_aba_diario
from modulos_frequencia.tab_dossie import renderizar_aba_dossie
from modulos_frequencia.tab_emergencia import renderizar_aba_emergencia
from modulos_frequencia.tab_lgpd import renderizar_aba_lgpd
from modulos_frequencia.tab_atestado import renderizar_aba_atestado
from modulos_frequencia.tab_niver import renderizar_aba_niver
from modulos_frequencia.tab_admin import renderizar_aba_admin
from utils.texto import normalizar_fonetica


# ==============================================================================
# 📅 MOTOR DE CALENDÁRIO LETIVO
# ==============================================================================
def verificar_dia_letivo(data):
    if data.weekday() == 5:
        return False, "Sábado (Fim de Semana)"
    if data.weekday() == 6:
        return False, "Domingo (Fim de Semana)"

    feriados_fixos = {
        (1, 1): "Ano Novo",
        (1, 25): "Aniversário de São Paulo",
        (4, 21): "Tiradentes",
        (5, 1): "Dia do Trabalhador",
        (7, 9): "Revolução Constitucionalista (SP)",
        (9, 7): "Independência do Brasil",
        (10, 12): "Nossa Senhora Aparecida",
        (11, 2): "Finados",
        (11, 15): "Proclamação da República",
        (11, 20): "Dia da Consciência Negra",
        (12, 25): "Natal",
    }
    if (data.month, data.day) in feriados_fixos:
        return False, f"Feriado: {feriados_fixos[(data.month, data.day)]}"

    feriados_moveis = {
        datetime.date(2025, 3, 3): "Carnaval",
        datetime.date(2025, 3, 4): "Carnaval",
        datetime.date(2025, 4, 18): "Sexta-feira Santa",
        datetime.date(2025, 6, 19): "Corpus Christi",
        datetime.date(2026, 2, 16): "Carnaval",
        datetime.date(2026, 2, 17): "Carnaval",
        datetime.date(2026, 4, 3): "Sexta-feira Santa",
        datetime.date(2026, 6, 4): "Corpus Christi",
        datetime.date(2027, 2, 8): "Carnaval",
        datetime.date(2027, 2, 9): "Carnaval",
        datetime.date(2027, 3, 26): "Sexta-feira Santa",
        datetime.date(2027, 5, 27): "Corpus Christi",
    }
    if data in feriados_moveis:
        return False, f"Feriado: {feriados_moveis[data]}"

    return True, "Dia Letivo Válido"


@st.cache_data(ttl=300, show_spinner=False)
def obter_todos_alunos_cache():
    return buscar_alunos_geral("")


@st.cache_data(ttl=300, show_spinner=False)
def obter_todos_alunos_com_inativos_cache():
    return buscar_alunos_geral("", incluir_inativos=True)


def _limpar_cache_busca_global():
    """Invalida os caches locais usados pela Busca Global após transferir/reativar
    um aluno, garantindo que ele apareça imediatamente na turma correta."""
    for fn in (obter_todos_alunos_cache, obter_todos_alunos_com_inativos_cache):
        try:
            fn.clear()
        except Exception:
            pass


@st.cache_data(ttl=300, show_spinner=False)
def verificar_aniversariante_hoje_cache() -> bool:
    """Retorna True se há algum aluno aniversariando hoje. Cache de 5 min."""
    try:
        hoje = datetime.date.today()
        df = buscar_alunos_geral("")
        if df.empty:
            return False
        dts = pd.to_datetime(df["data_nascimento"], errors="coerce").dropna()
        return bool(((dts.dt.day == hoje.day) & (dts.dt.month == hoje.month)).any())
    except Exception:
        return False


def obter_alunos_por_selecao(selecao, mostrar_todos=False):
    """Busca os alunos dinamicamente do banco de dados, unindo turmas do mesmo horário se solicitado."""
    if mostrar_todos:
        hora_match = re.search(r"(0[789]H|1[012]H)", selecao)
        if hora_match:
            hora_busca = hora_match.group(1)
            df_todas = get_todas_turmas(ativas_apenas=True)

            if not df_todas.empty:
                turmas_mesmo_horario = [
                    t for t in df_todas["nome"].tolist() if hora_busca in t
                ]
                dfs = []
                for t in turmas_mesmo_horario:
                    df_t = get_alunos_por_turma(t)
                    if not df_t.empty:
                        dfs.append(df_t)

                if dfs:
                    return pd.concat(dfs).drop_duplicates(subset=["id"])

    return get_alunos_por_turma(selecao)


def obter_alunos_por_turmas(lista_turmas):
    """Busca e une (sem duplicar) os alunos de uma ou mais turmas selecionadas."""
    dfs = []
    for t in lista_turmas:
        df_t = get_alunos_por_turma(t)
        if not df_t.empty:
            dfs.append(df_t)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs).drop_duplicates(subset=["id"]).reset_index(drop=True)


def carregar_css_global():
    st.markdown(
        """
        <style>
            .zoom-avatar {
                display: block;
                width: 63px !important; height: 63px !important;
                min-width: 63px; min-height: 63px;
                max-width: 63px; max-height: 63px;
                aspect-ratio: 1 / 1;
                border-radius: 50%;
                object-fit: cover;
                object-position: center center;
                flex-shrink: 0;
                box-shadow: 0 0 0 2.5px #3B82F6, 0 2px 8px rgba(59,130,246,0.25);
                transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.25s ease;
                cursor: zoom-in;
                position: relative;
                z-index: 50;
            }
            .zoom-avatar:hover {
                transform: scale(3.5);
                box-shadow: 0 0 0 2.5px #3B82F6, 0 12px 36px rgba(0,0,0,0.5);
                z-index: 99999 !important;
                position: relative;
            }
            .zoom-avatar-initials {
                display: flex; align-items: center; justify-content: center;
                width: 42px; height: 42px;
                min-width: 42px; min-height: 42px;
                aspect-ratio: 1 / 1;
                border-radius: 50%;
                background: linear-gradient(135deg, #3B82F6, #06B6D4);
                color: #fff;
                font-weight: 900;
                font-size: 16px;
                box-shadow: 0 0 0 2px #BFDBFE;
                flex-shrink: 0;
            }
            div[data-baseweb="select"] > div { border: 2px solid #1E88E5 !important; border-radius: 8px !important; background-color: #F8FAFC !important; font-weight: 800 !important; font-size: 16px !important; color: #0A2540 !important; }
        </style>
    """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 🎉 BADGE DE NÚMERO DA AULA + SISTEMA DE CELEBRAÇÕES FESTIVAS
# ==============================================================================

# Marcos de aula que disparam celebração
_MARCOS_AULA = {
    1:   ("🌅", "#92400E", "#FEF3C7", "#F59E0B", "Primeira aula do ano!"),
    50:  ("🎯", "#5B21B6", "#EDE9FE", "#8B5CF6", "50ª aula — metade do caminho!"),
    100: ("🎉", "#991B1B", "#FEE2E2", "#EF4444", "100ª aula — marco histórico!"),
    150: ("🚀", "#0C4A6E", "#E0F2FE", "#0EA5E9", "150 aulas em " + str(datetime.date.today().year) + "!"),
    200: ("🏆", "#78350F", "#FEF3C7", "#D97706", "200 aulas — que turma incrível!"),
    250: ("⭐", "#831843", "#FDF2F8", "#EC4899", "250ª aula — vocês são demais!"),
    300: ("💎", "#312E81", "#EEF2FF", "#6366F1", "300 aulas! Épico! Parabéns!"),
}
for _m in range(400, 10_000, 100):
    _MARCOS_AULA[_m] = ("🚀", "#0C4A6E", "#E0F2FE", "#0EA5E9", f"{_m}ª aula — inacreditável!")

# Datas de calendário que disparam celebração (mês, dia)
_DATAS_FESTIVAS = {
    (2, 14): ("💝", "#BE185D", "#FDF2F8", "#EC4899", "Dia dos Namorados!"),
    (3,  8): ("🌺", "#6B21A8", "#F5F3FF", "#9333EA", "Dia Internacional da Mulher!"),
    (6, 12): ("💑", "#BE185D", "#FDF2F8", "#EC4899", "Dia dos Namorados!"),
    (6, 23): ("🎆", "#92400E", "#FEF3C7", "#F59E0B", "Véspera de São João! Arriba!"),
    (6, 24): ("🪘", "#92400E", "#FEF3C7", "#F59E0B", "Festa de São João! Forró!"),
    (10, 31): ("🎃", "#9A3412", "#FFF7ED", "#EA580C", "Feliz Halloween!"),
}

# Marcos grandes (disparam balões flutuantes maiores)
_MARCOS_GRANDES = {100, 200, 300, 400, 500}


def _gerar_baloes_css(num_baloes: int = 14) -> str:
    """Gera CSS de balões flutuando da base para o topo da tela."""
    import random as _rnd
    _rnd.seed(42)
    emojis = ["🎈", "🎊", "🎉", "🎈", "🎈", "✨", "🎈", "🥳", "🎈", "🎊"]
    baloes_html = ""
    for i in range(num_baloes):
        emoji = emojis[i % len(emojis)]
        left  = _rnd.randint(2, 97)
        delay = round(_rnd.uniform(0, 3.5), 2)
        dur   = round(_rnd.uniform(4, 7), 2)
        size  = _rnd.randint(24, 42)
        baloes_html += (
            f"<div class='_balao' style='left:{left}%;animation-delay:{delay}s;"
            f"animation-duration:{dur}s;font-size:{size}px;'>{emoji}</div>"
        )
    return f"""
    <style>
    @keyframes _subir {{
        0%   {{ transform: translateY(0)   rotate(-6deg); opacity:1; }}
        50%  {{ transform: translateY(-40vh) rotate(6deg);  opacity:0.85; }}
        100% {{ transform: translateY(-100vh) rotate(-3deg); opacity:0; }}
    }}
    ._overlay_festivo {{
        position:fixed; inset:0; z-index:99999; pointer-events:none;
        overflow:hidden;
    }}
    ._balao {{
        position:absolute; bottom:-60px;
        animation: _subir linear forwards;
        will-change: transform;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,0.18));
    }}
    </style>
    <div class='_overlay_festivo'>{baloes_html}</div>
    """


def _renderizar_badge_aula(data_aula: datetime.date, num_aula: int) -> None:
    """
    Renderiza o badge de número da aula logo abaixo do date_input.
    Detecta marcos (50ª, 100ª…), datas fixas (_DATAS_FESTIVAS) e datas
    comemorativas registradas pelo admin no Calendário Institucional.
    Em celebrações: badge pulsa + balões sobem pela tela.
    """
    # ── 1. Marcos de aula ──────────────────────────────────────────────────
    marco = _MARCOS_AULA.get(num_aula)

    # ── 2. Datas festivas fixas (hardcoded — anuais) ───────────────────────
    data_fest = _DATAS_FESTIVAS.get((data_aula.month, data_aula.day))

    # ── 2b. Datas comemorativas anuais cadastradas pelo admin (configuracoes_sistema) ──
    custom_fest = None
    if not marco and not data_fest:
        try:
            import html as _html
            import re as _re_cor
            for _c in get_datas_comemorativas_custom():
                if _c.get("mes") == data_aula.month and _c.get("dia") == data_aula.day:
                    # Escape user-controlled text; validate color to prevent CSS injection
                    _emoji = _html.escape((str(_c.get("emoji") or "🎉")).strip())
                    _raw_cor = str(_c.get("cor") or "#F59E0B")
                    _cor = _raw_cor if _re_cor.match(r'^#[0-9A-Fa-f]{3,8}$', _raw_cor) else "#F59E0B"
                    _nome  = _html.escape(str(_c.get("nome") or "Data comemorativa!"))
                    custom_fest = (_emoji, "#92400E", "#FEF3C7", _cor, _nome)
                    break
        except Exception:
            pass

    # ── 3. Datas comemorativas registradas pelo admin no Calendário ─────────
    db_fest = None
    if not marco and not data_fest and not custom_fest:
        try:
            _db_map = get_datas_comemorativas_bd()
            _entrada = _db_map.get(data_aula.isoformat())
            if _entrada:
                motivo_db = _entrada.get("motivo") or "Data comemorativa!"
                db_fest = ("🎉", "#92400E", "#FEF3C7", "#F59E0B", motivo_db)
        except Exception:
            pass

    eh_celebr = bool(marco or data_fest or custom_fest or db_fest)
    eh_grande = num_aula in _MARCOS_GRANDES

    # ── 4. Escolher visual ─────────────────────────────────────────────────
    if marco:
        ico, txt_c, bg, borda, legenda = marco
    elif data_fest:
        ico, txt_c, bg, borda, legenda = data_fest
    elif custom_fest:
        ico, txt_c, bg, borda, legenda = custom_fest
    elif db_fest:
        ico, txt_c, bg, borda, legenda = db_fest
    else:
        ico, txt_c, bg, borda, legenda = "📚", "#1E40AF", "#EFF6FF", "#BFDBFE", ""

    # ── 5. Montar HTML (style em linha única — evita interpretação Markdown) ─
    ano        = data_aula.year
    aula_label = f"Aula #{num_aula}" if num_aula else "—"

    _pulse_css = (
        "@keyframes _pbadge{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.4)}"
        "50%{box-shadow:0 0 0 8px rgba(239,68,68,0)}}"
    ) if eh_celebr else ""

    _anim = "animation:_pbadge 1.4s ease-in-out infinite;" if eh_celebr else ""

    _style = (
        f"display:inline-flex;align-items:center;gap:7px;"
        f"background:{bg};border:1.5px solid {borda};border-radius:20px;"
        f"padding:4px 13px 4px 9px;margin-top:6px;"
        f"font-size:13px;font-weight:700;color:{txt_c};"
        f"white-space:nowrap;{_anim}"
        f"box-shadow:0 1px 5px rgba(0,0,0,.08);"
    )

    _leg = (
        f"<span style='font-size:11px;font-weight:700;color:{txt_c};"
        f"background:{bg};border-radius:8px;padding:1px 7px;"
        f"white-space:nowrap;'>{legenda}</span>"
    ) if legenda else ""

    badge_html = (
        f"<style>{_pulse_css}</style>"
        f"<div style='{_style}' role='status' aria-label='{aula_label} de {ano}'>"
        f"<span aria-hidden='true' style='font-size:16px;line-height:1;'>{ico}</span>"
        f"<span style='font-size:13px;font-weight:900;'>{aula_label} · {ano}</span>"
        f"{_leg}"
        f"</div>"
    )
    st.markdown(badge_html, unsafe_allow_html=True)

    # ── 6. Balões flutuantes (somente em celebrações, uma vez por sessão/data) ──
    if eh_celebr:
        _chave_celebr = f"_celebr_vista_{data_aula.isoformat()}"
        if not st.session_state.get(_chave_celebr):
            st.session_state[_chave_celebr] = True
            st.markdown(_gerar_baloes_css(18 if eh_grande else 12), unsafe_allow_html=True)


def _renderizar_progresso_anual(data_aula: datetime.date, num_aula_ate_hoje: int) -> None:
    """
    Exibe um expander "📈 Progresso do ano" abaixo do badge de número da aula.
    Mostra um mini gráfico de barras horizontal (HTML/CSS) com aulas por mês,
    o mês atual destacado, total no ano e projeção até dezembro.
    Permite navegar entre anos com botões ◀ / ▶ no topo do expander.
    Suporta modo de comparação lado a lado de dois anos.
    """
    ano_data = data_aula.year
    mes_ref_data = data_aula.month

    # Inicializa (ou reseta quando a data muda de ano) o ano exibido no gráfico
    _KEY_ANO = "_prog_ano_grafico"
    _KEY_ANO_BASE = "_prog_ano_base"
    _KEY_COMPARAR = "_prog_comparar"
    _KEY_ANO_COMP = "_prog_ano_comp"

    if st.session_state.get(_KEY_ANO_BASE) != ano_data:
        st.session_state[_KEY_ANO_BASE] = ano_data
        st.session_state[_KEY_ANO] = ano_data
        st.session_state[_KEY_COMPARAR] = False
        st.session_state[_KEY_ANO_COMP] = ano_data - 1

    ano_grafico = st.session_state.get(_KEY_ANO, ano_data)
    modo_comparar = st.session_state.get(_KEY_COMPARAR, False)
    ano_comp = st.session_state.get(_KEY_ANO_COMP, ano_grafico - 1)

    with st.expander("📈 Progresso do ano", expanded=False):
        # ── Navegação de anos ────────────────────────────────────────────────
        col_prev, col_ano_lbl, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button(f"◀ {ano_grafico - 1}", key="_prog_ano_prev",
                         use_container_width=True):
                st.session_state[_KEY_ANO] = ano_grafico - 1
                # Atualiza ano de comparação para não colidir com o principal
                new_ano = ano_grafico - 1
                if st.session_state.get(_KEY_ANO_COMP, new_ano - 1) == new_ano:
                    st.session_state[_KEY_ANO_COMP] = new_ano - 1
                st.rerun()
        with col_ano_lbl:
            st.markdown(
                f"<div style='text-align:center;font-size:15px;font-weight:800;"
                f"color:#1E40AF;padding:4px 0;'>{ano_grafico}</div>",
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button(f"{ano_grafico + 1} ▶", key="_prog_ano_next",
                         use_container_width=True):
                st.session_state[_KEY_ANO] = ano_grafico + 1
                new_ano = ano_grafico + 1
                if st.session_state.get(_KEY_ANO_COMP, new_ano - 1) == new_ano:
                    st.session_state[_KEY_ANO_COMP] = new_ano - 1
                st.rerun()

        # ── Toggle de comparação ─────────────────────────────────────────────
        comparar_novo = st.toggle(
            "🔀 Comparar com outro ano",
            value=modo_comparar,
            key="_prog_toggle_comparar",
        )
        if comparar_novo != modo_comparar:
            st.session_state[_KEY_COMPARAR] = comparar_novo
            modo_comparar = comparar_novo
            st.rerun()

        if modo_comparar:
            # Seletor do ano de comparação (exclui o ano principal)
            anos_disponiveis = [a for a in range(ano_grafico - 5, ano_grafico + 6) if a != ano_grafico]
            # Garantir que ano_comp esteja na lista
            if ano_comp not in anos_disponiveis:
                ano_comp = ano_grafico - 1
                st.session_state[_KEY_ANO_COMP] = ano_comp
            idx_default = anos_disponiveis.index(ano_comp) if ano_comp in anos_disponiveis else 0
            ano_comp_sel = st.selectbox(
                "Comparar com:",
                options=anos_disponiveis,
                index=idx_default,
                key="_prog_sel_ano_comp",
                format_func=lambda a: str(a),
            )
            if ano_comp_sel != ano_comp:
                st.session_state[_KEY_ANO_COMP] = ano_comp_sel
                ano_comp = ano_comp_sel
                st.rerun()

        # Mês de referência: o mês da data selecionada só é relevante no ano atual
        mes_ref = mes_ref_data if ano_grafico == ano_data else 12

        with st.spinner("Carregando..."):
            aulas_mes = get_aulas_por_mes_no_ano(ano_grafico)
            if modo_comparar:
                aulas_mes_comp = get_aulas_por_mes_no_ano(ano_comp)
            else:
                aulas_mes_comp = {}

        if not aulas_mes and not aulas_mes_comp:
            st.caption("Nenhuma aula registrada em %d ainda." % ano_grafico)
            return

        import plotly.graph_objects as go

        _MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                     "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

        total_ano = sum(aulas_mes.values())

        # Projeção: apenas para o ano atual e somente se há meses completos (modo simples)
        projecao = None
        if not modo_comparar and ano_grafico == ano_data:
            meses_completos = [m for m in range(1, mes_ref) if aulas_mes.get(m, 0) > 0]
            if meses_completos:
                media_mensal = total_ano / len(meses_completos)
                meses_restantes = 12 - mes_ref
                projecao = round(total_ano + media_mensal * meses_restantes)

        meses_display = list(range(1, 13))
        labels = [_MESES_PT[m - 1] for m in meses_display]

        if modo_comparar:
            # ── Gráfico de barras agrupadas (comparação) ─────────────────────
            counts_1 = [aulas_mes.get(m, 0) for m in meses_display]
            counts_2 = [aulas_mes_comp.get(m, 0) for m in meses_display]

            # Diferença mês a mês: positivo = ano atual melhor
            diffs = [c1 - c2 for c1, c2 in zip(counts_1, counts_2)]

            # Cores dos dois anos
            COR_ANO1 = "#3B82F6"   # azul — ano principal
            COR_ANO2 = "#F97316"   # laranja — ano comparado

            # Texto de variação para os hovers
            def _diff_hover(d: int) -> str:
                if d > 0:
                    return f"▲ +{d} aula{'s' if abs(d) != 1 else ''} vs {ano_comp}"
                elif d < 0:
                    return f"▼ {d} aula{'s' if abs(d) != 1 else ''} vs {ano_comp}"
                return f"= igual a {ano_comp}"

            diff_hover_labels = [_diff_hover(d) for d in diffs]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=str(ano_grafico),
                x=counts_1,
                y=labels,
                orientation="h",
                marker_color=COR_ANO1,
                text=[str(c) if c > 0 else "" for c in counts_1],
                textposition="outside",
                cliponaxis=False,
                customdata=diff_hover_labels,
                hovertemplate=(
                    f"<b>%{{y}} {ano_grafico}</b>: %{{x}} aulas<br>"
                    f"<i>%{{customdata}}</i><extra></extra>"
                ),
            ))
            fig.add_trace(go.Bar(
                name=str(ano_comp),
                x=counts_2,
                y=labels,
                orientation="h",
                marker_color=COR_ANO2,
                text=[str(c) if c > 0 else "" for c in counts_2],
                textposition="outside",
                cliponaxis=False,
                customdata=diff_hover_labels,
                hovertemplate=(
                    f"<b>%{{y}} {ano_comp}</b>: %{{x}} aulas<br>"
                    f"<i>%{{customdata}}</i><extra></extra>"
                ),
            ))

            # ── Anotações nos top 3 meses com maior variação absoluta ─────────
            diffs_ranked = sorted(
                [(abs(d), i, d) for i, d in enumerate(diffs) if d != 0],
                reverse=True,
            )
            top3_idx = {idx for _, idx, _ in diffs_ranked[:3]}

            max_val = max(max(counts_1, default=0), max(counts_2, default=0))
            # Deixar espaço extra à direita para os badges de variação
            x_range_max = max_val * 1.55 if max_val else 1
            x_annot = max_val * 1.32 if max_val else 0.8

            annot_x, annot_y, annot_text, annot_colors = [], [], [], []
            for i, d in enumerate(diffs):
                if i in top3_idx:
                    seta = "▲" if d > 0 else "▼"
                    sinal = "+" if d > 0 else ""
                    annot_x.append(x_annot)
                    annot_y.append(labels[i])
                    annot_text.append(f"<b>{seta}{sinal}{d}</b>")
                    annot_colors.append("#16A34A" if d > 0 else "#DC2626")

            if annot_x:
                fig.add_trace(go.Scatter(
                    x=annot_x,
                    y=annot_y,
                    mode="text",
                    text=annot_text,
                    textfont=dict(size=11, color=annot_colors),
                    hoverinfo="skip",
                    showlegend=False,
                    cliponaxis=False,
                ))

            fig.update_layout(
                barmode="group",
                height=370,
                margin=dict(l=0, r=10, t=4, b=0),
                xaxis=dict(visible=False, range=[0, x_range_max]),
                yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
                plot_bgcolor="white",
                paper_bgcolor="white",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.01,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=12),
                ),
                dragmode=False,
            )

            st.plotly_chart(fig, use_container_width=True, key=f"_prog_chart_cmp_{ano_grafico}_{ano_comp}")

            # ── Rodapé comparativo ───────────────────────────────────────────
            total_comp = sum(aulas_mes_comp.values())
            diff_total = total_ano - total_comp
            sinal_total = "+" if diff_total >= 0 else ""
            cor_diff_total = "#16A34A" if diff_total >= 0 else "#DC2626"
            diff_txt = (
                f"<span style='color:{cor_diff_total};font-weight:700;'>"
                f"({sinal_total}{diff_total} vs {ano_comp})</span>"
            )

            # Meses com melhora / piora
            meses_melhor = [labels[i] for i, d in enumerate(diffs) if d > 0]
            meses_pior   = [labels[i] for i, d in enumerate(diffs) if d < 0]
            partes_legenda = []
            if meses_melhor:
                partes_legenda.append(
                    f"<span style='color:#16A34A;font-size:11px;'>"
                    f"▲ Melhores: {', '.join(meses_melhor)}</span>"
                )
            if meses_pior:
                partes_legenda.append(
                    f"<span style='color:#DC2626;font-size:11px;'>"
                    f"▼ Abaixo: {', '.join(meses_pior)}</span>"
                )
            legenda_meses_html = (
                f"<div style='padding-top:4px;display:flex;gap:14px;flex-wrap:wrap;'>"
                f"{'<span style=\"color:#CBD5E1;font-size:11px;\"> | </span>'.join(partes_legenda)}"
                f"</div>"
                if partes_legenda else ""
            )

            st.markdown(
                f"<div style='padding-top:6px;border-top:1px solid #E2E8F0;display:flex;"
                f"align-items:center;gap:12px;flex-wrap:wrap;'>"
                f"<span style='color:#3B82F6;font-size:13px;font-weight:700;'>"
                f"🔵 {ano_grafico}: {total_ano} aulas</span>"
                f"<span style='color:#F97316;font-size:13px;font-weight:700;'>"
                f"🟠 {ano_comp}: {total_comp} aulas</span>"
                f"<span style='font-size:12px;color:#64748B;'>{diff_txt}</span>"
                f"</div>"
                f"{legenda_meses_html}",
                unsafe_allow_html=True,
            )

        else:
            # ── Gráfico de barras simples (modo original) ────────────────────
            _KEY_MES_SEL = f"_prog_mes_sel_{ano_grafico}"

            counts = [aulas_mes.get(m, 0) for m in meses_display]
            cores = []
            for m in meses_display:
                eh_atual = (m == mes_ref) and (ano_grafico == ano_data)
                eh_futuro = (ano_grafico == ano_data) and (m > mes_ref)
                if eh_atual:
                    cores.append("#3B82F6")
                elif eh_futuro:
                    cores.append("#CBD5E1")
                else:
                    cores.append("#60A5FA")

            mes_sel_atual = st.session_state.get(_KEY_MES_SEL, mes_ref)

            line_colors = [
                "#1E40AF" if meses_display[i] == mes_sel_atual else "rgba(0,0,0,0)"
                for i in range(12)
            ]
            line_widths = [
                2 if meses_display[i] == mes_sel_atual else 0
                for i in range(12)
            ]

            text_vals = [str(c) if c > 0 else "" for c in counts]

            fig = go.Figure(go.Bar(
                x=counts,
                y=labels,
                orientation="h",
                marker=dict(
                    color=cores,
                    line=dict(color=line_colors, width=line_widths),
                ),
                text=text_vals,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b>: %{x} aulas<extra></extra>",
            ))
            fig.update_layout(
                height=310,
                margin=dict(l=0, r=35, t=4, b=0),
                xaxis=dict(visible=False, range=[0, max(counts) * 1.25 if counts else 1]),
                yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
                dragmode=False,
            )

            chart_key = f"_prog_chart_{ano_grafico}"
            evento = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                key=chart_key,
            )

            # Detectar clique e atualizar o mês selecionado
            if evento and getattr(evento, "selection", None):
                pts = getattr(evento.selection, "points", [])
                if pts:
                    idx_clicado = pts[0].get("point_index", None)
                    if idx_clicado is not None and 0 <= idx_clicado < 12:
                        mes_clicado = meses_display[idx_clicado]
                        if mes_clicado != mes_sel_atual:
                            st.session_state[_KEY_MES_SEL] = mes_clicado
                            mes_sel_atual = mes_clicado
                            st.rerun()

            # ── Rodapé: total + projeção ─────────────────────────────────────
            proj_txt = ""
            if projecao is not None and projecao != total_ano:
                proj_txt = f" · projeção até Dez: **{projecao}** aulas"

            st.markdown(
                f"<div style='padding-top:6px;border-top:1px solid #E2E8F0;'>"
                f"<span style='color:#1E40AF;font-size:13px;font-weight:700;'>"
                f"✅ {total_ano} aulas em {ano_grafico}</span>"
                f"<span style='color:#64748B;font-size:12px;margin-left:10px;'>{proj_txt}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # ── Lista de dias letivos do mês selecionado pela barra ──────────
            qtd_mes_sel = aulas_mes.get(mes_sel_atual, 0)
            st.markdown(
                f"<div style='margin-top:8px;font-size:12px;color:#475569;'>"
                f"📅 Clique em uma barra para ver os dias letivos &nbsp;·&nbsp; "
                f"<strong style='color:#1E40AF;'>{_MESES_PT[mes_sel_atual - 1]}</strong>"
                f" — {qtd_mes_sel} aula{'s' if qtd_mes_sel != 1 else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )

            if qtd_mes_sel > 0:
                with st.spinner(""):
                    datas_detalhadas = get_datas_letivas_detalhadas_no_ano(ano_grafico)

                datas_do_mes = datas_detalhadas.get(mes_sel_atual, [])

                _DIAS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                _MESES_ABR = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                              "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
                linhas_html = ""
                for date_str, num_aula in datas_do_mes:
                    try:
                        dt = datetime.date.fromisoformat(date_str)
                    except Exception:
                        continue
                    dia_sem = _DIAS_PT[dt.weekday()]
                    mes_abr = _MESES_ABR[dt.month - 1]
                    linhas_html += (
                        f"<div style='padding:3px 0;font-size:12px;color:#1E40AF;"
                        f"border-bottom:1px solid #F1F5F9;'>"
                        f"{dia_sem}, {dt.day:02d} {mes_abr}"
                        f" &nbsp;·&nbsp; "
                        f"<span style='color:#64748B;'>Aula #{num_aula}</span>"
                        f"</div>"
                    )

                if linhas_html:
                    st.markdown(
                        f"<div style='background:#F8FAFC;border:1px solid #E2E8F0;"
                        f"border-radius:8px;padding:8px 12px;margin-top:6px;'>"
                        f"{linhas_html}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Nenhuma aula registrada neste mês.")


def tela_frequencia():
    if st.session_state.pop("_force_reload_freq", False):
        for fn in (obter_todos_alunos_cache, obter_todos_alunos_com_inativos_cache):
            try:
                fn.clear()
            except Exception:
                pass

    carregar_css_global()

    hoje_check = datetime.date.today()
    tem_aniversariante_hoje = verificar_aniversariante_hoje_cache()

    label_niver = (
        "🎂 Niver 🍰 HOJE TEM BOLO!!!" if tem_aniversariante_hoje else "🎂 Niver"
    )

    # Total de alunos ativos (cache 5 min — zero custo extra)
    try:
        _df_total_geral = obter_todos_alunos_cache()
        _total_geral = len(_df_total_geral) if not _df_total_geral.empty else 0
    except Exception:
        _total_geral = 0

    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:0;'>
          <h2 style='color:#0A2540;font-weight:900;margin:0;'>📊 Gestão de Fluxo</h2>
          <span style='display:inline-flex;align-items:center;gap:6px;
                       background:#EFF6FF;border:1.5px solid #BFDBFE;
                       border-radius:24px;padding:4px 14px 4px 10px;
                       font-size:13px;font-weight:600;color:#475569;
                       box-shadow:0 1px 4px rgba(59,130,246,0.12);
                       white-space:nowrap;letter-spacing:0.1px;'>
            <span style='font-size:17px;line-height:1;'>👥</span>
            <span style='color:#1E40AF;font-weight:900;font-size:15px;'>{_total_geral}</span>
            <span style='color:#64748B;'>alunos ativos</span>
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        col_data, col_busca = st.columns([3, 5], vertical_alignment="bottom")

        with col_data:
            if "_freq_data_alvo" in st.session_state:
                st.session_state["freq_data_aula"] = st.session_state.pop("_freq_data_alvo")
            data_aula = st.date_input(
                "📅 Data da Aula:", hoje_check, format="DD/MM/YYYY", key="freq_data_aula"
            )
            # ── Badge: número da aula no ano ──────────────────────────────
            _num_aula = get_numero_aula_no_ano(data_aula)
            _renderizar_badge_aula(data_aula, _num_aula)
            # ── Expander: progresso anual (aulas por mês) ─────────────────
            _renderizar_progresso_anual(data_aula, _num_aula)

        dia_semana = data_aula.weekday()
        if dia_semana in [5, 6]:
            turmas_combo = ["Dia não letivo (Fim de Semana)"]
            df_turmas_ativas = pd.DataFrame()
        else:
            df_turmas_ativas = get_todas_turmas(ativas_apenas=True)
            if not df_turmas_ativas.empty:
                turmas_combo = df_turmas_ativas["nome"].tolist()
            else:
                turmas_combo = ["Nenhuma turma ativa cadastrada"]

        st.markdown(
            "<span style='font-size:13px;color:#64748B;font-weight:700;'>"
            "👥 Selecione a(s) Turma(s):</span>",
            unsafe_allow_html=True,
        )
        turmas_selecionadas = []
        _n_por_linha = 4
        for _i in range(0, len(turmas_combo), _n_por_linha):
            _linha_turmas = turmas_combo[_i : _i + _n_por_linha]
            _cols_turmas_chk = st.columns(_n_por_linha)
            for _idx_t, _nome_t in enumerate(_linha_turmas):
                _marcado_t = _cols_turmas_chk[_idx_t].checkbox(
                    _nome_t,
                    value=(_nome_t == turmas_combo[0]),
                    key=f"chk_turma_all_{data_aula}_{_nome_t}",
                )
                if _marcado_t:
                    turmas_selecionadas.append(_nome_t)
        if not turmas_selecionadas:
            turmas_selecionadas = [turmas_combo[0]]

        # ── Checkbox: incluir alunos de outras turmas ──────────────────────
        _incluir_outras = False
        if len(turmas_combo) > 1 and dia_semana not in [5, 6]:
            _incluir_outras = st.checkbox(
                "➕ Incluir alunos de outras turmas na chamada",
                key=f"chk_outras_{data_aula}",
                help=(
                    "Mescla alunos das demais turmas na grade — "
                    "útil para registrar reposições sem mudar a turma principal"
                ),
            )

        turma_selecionada = turmas_selecionadas[0]

        chave_unica = f"{data_aula}_{'_'.join(turmas_selecionadas)}"

        busca_grid = _baw_freq(
            f"bg_{chave_unica}",
            container=col_busca,
            placeholder="🔍 Filtrar (mín. 3 letras)...",
            label="🔍 Busca Global:",
        )

    eh_valido, motivo_bloqueio = verificar_dia_letivo(data_aula)

    if not eh_valido:
        st.markdown(
            f"""
            <div style='background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 20px;'>
                <h3 style='color: #991B1B; margin-top: 0; font-weight: 900;'>🛑 Data Bloqueada: {motivo_bloqueio}</h3>
                <p style='color: #7F1D1D; margin-bottom: 0; font-size: 16px;'>O sistema não permite o registo de frequência ou diários em fins de semana e feriados. Selecione um <b>dia útil</b>.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        return

    bloqueio_ativo = False

    busca_limpa = normalizar_fonetica(busca_grid).strip() if busca_grid else ""

    if len(busca_limpa) >= 3:
        df_todos_com_inativos = obter_todos_alunos_com_inativos_cache()

        if not df_todos_com_inativos.empty:
            df_encontrados = filtrar_alunos_df(
                df_todos_com_inativos, busca_grid, cols=["nome"], min_len=3
            )
        else:
            df_encontrados = pd.DataFrame()

        if not df_encontrados.empty:
            st.success(
                f"🌍 Busca Global Ativada: Encontrámos {len(df_encontrados)} aluno(s) na base geral."
            )

            alunos_prontos = []
            df_valida = obter_alunos_por_selecao(turma_selecionada, False)
            ids_validos_na_tela = (
                df_valida["id"].tolist() if not df_valida.empty else []
            )

            _ult_freq_map = get_ultima_presenca_batch(
                tuple(str(i) for i in df_encontrados["id"].tolist())
            )

            for _, aluno in df_encontrados.iterrows():
                is_inativo   = aluno.get("status") == "Inativo"
                is_outra_turma = aluno["id"] not in ids_validos_na_tela

                if is_inativo or is_outra_turma:
                    with st.container(border=True):
                        # ── layout: avatar | info | botões ──────────────────────
                        col_av, col_info, col_acoes = st.columns(
                            [0.55, 3.2, 3.5], vertical_alignment="center"
                        )

                        # ── Avatar redondo ───────────────────────────────────────
                        with col_av:
                            foto = aluno.get("foto_url")
                            if foto and not pd.isna(foto) and str(foto).strip():
                                st.markdown(
                                    f"<img src='{foto}' class='zoom-avatar' "
                                    f"style='width:40px;height:40px;border-radius:50%;"
                                    f"object-fit:cover;'>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                inicial = str(aluno["nome"])[0].upper()
                                st.markdown(
                                    f"<div style='width:40px;height:40px;border-radius:50%;"
                                    f"background:#E2E8F0;display:flex;align-items:center;"
                                    f"justify-content:center;font-weight:900;font-size:17px;"
                                    f"color:#475569;'>{inicial}</div>",
                                    unsafe_allow_html=True,
                                )

                        # ── Nome + badge de status ───────────────────────────────
                        with col_info:
                            if is_inativo:
                                badge = (
                                    "<span style='background:#FEE2E2;color:#991B1B;"
                                    "padding:2px 8px;border-radius:5px;font-size:10px;"
                                    "font-weight:800;'>INATIVO</span>"
                                )
                                caption = "Inativo — ative e transfira se necessário."
                            else:
                                turma_tag = str(aluno.get("turma", "outra turma"))
                                badge = (
                                    f"<span style='background:#DBEAFE;color:#1E40AF;"
                                    f"padding:2px 8px;border-radius:5px;font-size:10px;"
                                    f"font-weight:800;'>{turma_tag}</span>"
                                )
                                caption = "Visitante / Reposição — conta para turma original."

                            ult_f   = _ult_freq_map.get(str(aluno["id"]))
                            ult_txt = f"  ·  Freq: {ult_f}" if ult_f else "  ·  Freq: —"

                            st.markdown(
                                f"**{aluno['nome']}** &nbsp;{badge}",
                                unsafe_allow_html=True,
                            )
                            st.caption(caption + ult_txt)

                        # ── Botões de ação ───────────────────────────────────────
                        with col_acoes:
                            if is_inativo:
                                # Inativo: só Ficha e Ativar+Transferir
                                cb1, cb2 = st.columns(2, gap="small")
                                with cb1:
                                    if st.button(
                                        "🩺 Ficha",
                                        key=f"f_pr_{aluno['id']}",
                                        use_container_width=True,
                                        help="Abrir prontuário do aluno",
                                    ):
                                        st.session_state.aluno_prontuario = aluno.to_dict()
                                        st.session_state.origem_prontuario = "Frequência"
                                        st.session_state.menu_atual = "Portal do Aluno"
                                        st.rerun()
                                with cb2:
                                    if st.button(
                                        "♻️ Ativar+Transferir",
                                        key=f"fix_{aluno['id']}",
                                        type="primary",
                                        use_container_width=True,
                                        help="Reativar o aluno e movê-lo para esta turma",
                                    ):
                                        alterar_status_aluno(aluno["id"], "Ativo")
                                        atualizar_turma_aluno(aluno["id"], turma_selecionada)
                                        _limpar_cache_busca_global()
                                        st.toast(
                                            f"{aluno['nome'].split()[0]} reativado(a) e transferido(a)!",
                                            icon="♻️",
                                        )
                                        time.sleep(0.8)
                                        st.rerun()

                            else:
                                # Outra turma: Ficha | Visitante (novo) | Transferir
                                cb1, cb2, cb3 = st.columns(3, gap="small")
                                with cb1:
                                    if st.button(
                                        "🩺 Ficha",
                                        key=f"f_pr_{aluno['id']}",
                                        use_container_width=True,
                                        help="Abrir prontuário do aluno",
                                    ):
                                        st.session_state.aluno_prontuario = aluno.to_dict()
                                        st.session_state.origem_prontuario = "Frequência"
                                        st.session_state.menu_atual = "Portal do Aluno"
                                        st.rerun()

                                with cb2:
                                    if st.button(
                                        "✅ Visitante",
                                        key=f"vis_{aluno['id']}",
                                        type="primary",
                                        use_container_width=True,
                                        help="Marca PRESENTE nesta data sem alterar a turma original",
                                    ):
                                        _email_log = (
                                            st.session_state.get("usuario_email")
                                            or st.session_state.get("email_usuario")
                                            or ""
                                        )
                                        alternar_presenca(
                                            aluno["id"], data_aula, True, _email_log
                                        )
                                        st.toast(
                                            f"Presença de reposição registrada para "
                                            f"{aluno['nome'].split()[0]}!",
                                            icon="✅",
                                        )
                                        # Limpa o campo de busca para continuar o trabalho
                                        st.session_state[f"bg_{chave_unica}"] = ""
                                        time.sleep(0.8)
                                        st.rerun()

                                with cb3:
                                    if st.button(
                                        "🔄 Transferir",
                                        key=f"fix_{aluno['id']}",
                                        use_container_width=True,
                                        help="Move o aluno permanentemente para esta turma",
                                    ):
                                        atualizar_turma_aluno(aluno["id"], turma_selecionada)
                                        _limpar_cache_busca_global()
                                        st.toast(
                                            f"{aluno['nome'].split()[0]} transferido(a) "
                                            f"para {turma_selecionada}!",
                                            icon="🔄",
                                        )
                                        time.sleep(0.8)
                                        st.rerun()
                else:
                    alunos_prontos.append(aluno)

            df_alunos = pd.DataFrame(alunos_prontos)
        else:
            df_alunos = pd.DataFrame()
            st.warning(
                f"Nenhum aluno encontrado com o nome '{busca_grid}' (nem ativos, nem inativos)."
            )

            if st.button(
                "➕ O Aluno é Novo? CADASTRAR AGORA",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.menu_atual = "Nova Matrícula"
                st.rerun()
    else:
        if len(busca_limpa) > 0:
            st.caption("⏳ Digite pelo menos 3 letras para ativar a Busca Global...")

        df_alunos = obter_alunos_por_turmas(turmas_selecionadas)

        # Mescla alunos de outras turmas quando checkbox ativo
        if _incluir_outras and len(turmas_combo) > 1:
            _turmas_outras = [t for t in turmas_combo if t not in turmas_selecionadas]
            if _turmas_outras:
                df_extras = obter_alunos_por_turmas(_turmas_outras)
                if not df_extras.empty:
                    df_alunos = (
                        pd.concat([df_alunos, df_extras])
                        .drop_duplicates(subset=["id"])
                        .reset_index(drop=True)
                    )
                    st.info(
                        f"➕ {len(df_extras)} aluno(s) de outras turmas incluídos na grade.",
                        icon="ℹ️",
                    )

    if not df_alunos.empty and "nome" in df_alunos.columns:
        df_alunos = df_alunos.sort_values(by="nome").reset_index(drop=True)

    presencas_turma_geral = (
        get_presencas_dia(data_aula, df_alunos["id"].tolist())
        if not df_alunos.empty
        else {}
    )

    email_atual = (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or ""
    )
    eh_admin = email_atual == ADMIN_MASTER

    # ── Navegação direta: pré-renderiza tablet antes das abas ─────────────────
    _ir_tablet = st.session_state.pop("_freq_ir_tablet", False)
    if _ir_tablet:
        st.markdown(
            f"<div style='background:#EFF6FF;border-left:4px solid #3B82F6;"
            f"padding:10px 16px;border-radius:8px;margin-bottom:8px;font-size:13px;'>"
            f"📱 <b>Chamada de {data_aula.strftime('%d/%m/%Y')}</b> carregada — "
            f"grade de presenças abaixo. Use as abas para outros recursos.</div>",
            unsafe_allow_html=True,
        )
        renderizar_aba_terminal(
            df_alunos, data_aula, presencas_turma_geral, bloqueio_ativo, chave_unica
        )
        st.markdown("---")
        st.caption("⬇️ Recursos adicionais disponíveis nas abas:")

    nomes_abas = ["📱 Chamada Tablet", "📝 Diário", "🖨️ Dossiê", "🚨 Emergência",
                  "🔒 LGPD", "🏥 Atestado", label_niver]
    if eh_admin:
        nomes_abas.append("📅 Dias Regist./Anamnese")

    abas = st.tabs(nomes_abas)

    with abas[0]:
        if _ir_tablet:
            st.caption("👆 Grade de chamada exibida acima — role para cima para ver.")
        else:
            renderizar_aba_terminal(
                df_alunos, data_aula, presencas_turma_geral, bloqueio_ativo, chave_unica
            )

    with abas[1]:
        renderizar_aba_diario(data_aula, turmas_combo, chave_unica)

    with abas[2]:
        renderizar_aba_dossie(df_alunos, data_aula, turma_selecionada, chave_unica)

    with abas[3]:
        renderizar_aba_emergencia(df_alunos, turma_selecionada)

    with abas[4]:
        renderizar_aba_lgpd()

    with abas[5]:
        renderizar_aba_atestado()

    with abas[6]:
        renderizar_aba_niver()

    if eh_admin:
        with abas[7]:
            renderizar_aba_admin()
