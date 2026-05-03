# ==============================================================================
# 📊 Módulo: BI Prime — Dashboard Geral do Estúdio
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime

from database import (
    bi_resumo_studio,
    bi_evolucao_cadastros,
    bi_frequencia_turmas,
    bi_alunos_risco_abandono,
    bi_distribuicao_risco,
    bi_dores_studio,
    buscar_alunos_geral,
)

_COR_AZUL   = "#0056b3"
_COR_VERDE  = "#10B981"
_COR_AMAR   = "#F59E0B"
_COR_VERM   = "#EF4444"
_COR_CINZA  = "#94A3B8"
_BG         = "#F8FAFC"

# ── helpers ──────────────────────────────────────────────────────────────────
def _card_metrica(label, valor, delta=None, cor="#0056b3", icone=""):
    delta_html = ""
    if delta is not None:
        sinal = "▲" if delta >= 0 else "▼"
        dor   = _COR_VERDE if delta >= 0 else _COR_VERM
        delta_html = f"<div style='font-size:11px;color:{dor};margin-top:2px;'>{sinal} {abs(delta)}</div>"
    st.markdown(
        f"""<div style='background:#fff;border-radius:12px;padding:16px 18px;
        border-left:4px solid {cor};box-shadow:0 2px 8px rgba(0,0,0,.07);'>
        <div style='font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;
        letter-spacing:.5px;'>{icone} {label}</div>
        <div style='font-size:28px;font-weight:900;color:{cor};line-height:1.1;margin-top:4px;'>
        {valor}</div>{delta_html}</div>""",
        unsafe_allow_html=True,
    )


def _gauge_presenca(taxa):
    cor = _COR_VERDE if taxa >= 75 else (_COR_AMAR if taxa >= 50 else _COR_VERM)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=taxa,
        number={"suffix": "%", "font": {"size": 32, "color": cor}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#CBD5E1"},
            "bar": {"color": cor, "thickness": 0.25},
            "bgcolor": "#F1F5F9",
            "steps": [
                {"range": [0, 50],  "color": "#FEE2E2"},
                {"range": [50, 75], "color": "#FEF9C3"},
                {"range": [75, 100],"color": "#DCFCE7"},
            ],
            "threshold": {"line": {"color": cor, "width": 3}, "thickness": 0.75, "value": taxa},
        },
        title={"text": "Taxa de Presença (30 dias)", "font": {"size": 13, "color": "#475569"}},
    ))
    fig.update_layout(height=200, margin=dict(t=40, b=10, l=20, r=20), paper_bgcolor=_BG)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ──────────────────────────────────────────────────────────────────────────────
def render_bi_dashboard():
    st.markdown("## 📊 BI Prime — Dashboard do Estúdio")
    st.caption("Indicadores em tempo real para tomada de decisão estratégica e operacional.")

    # ── Filtros ──────────────────────────────────────────────────────────────
    col_fil, col_refresh = st.columns([4, 1])
    with col_fil:
        periodo = st.radio(
            "Janela de análise:",
            [30, 60, 90],
            format_func=lambda x: f"Últimos {x} dias",
            horizontal=True,
            key="bi_periodo",
        )
    with col_refresh:
        if st.button("🔄 Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── Carrega dados ─────────────────────────────────────────────────────────
    with st.spinner("Carregando indicadores..."):
        resumo     = bi_resumo_studio()
        df_cad     = bi_evolucao_cadastros()
        df_turmas  = bi_frequencia_turmas(dias=periodo)
        df_risco   = bi_distribuicao_risco()
        df_abandono= bi_alunos_risco_abandono(dias=periodo)
        df_dores   = bi_dores_studio()
        df_todos   = buscar_alunos_geral(incluir_inativos=False)

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO 1 — KPI CARDS
    # ═══════════════════════════════════════════════════════════════════════
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        _card_metrica("Alunos Ativos", resumo.get("total_ativos", 0), icone="👥", cor=_COR_AZUL)
    with c2:
        _card_metrica("Inativos", resumo.get("total_inativos", 0), icone="🗃️", cor=_COR_CINZA)
    with c3:
        taxa = resumo.get("taxa_presenca_30", 0.0)
        cor_taxa = _COR_VERDE if taxa >= 75 else (_COR_AMAR if taxa >= 50 else _COR_VERM)
        _card_metrica("Presença (30d)", f"{taxa}%", icone="✅", cor=cor_taxa)
    with c4:
        n_verm = resumo.get("risco_vermelho", 0)
        _card_metrica("Em Alerta 🔴", n_verm, icone="⚠️", cor=_COR_VERM if n_verm > 0 else _COR_CINZA)
    with c5:
        n_amar = resumo.get("risco_amarelo", 0)
        _card_metrica("Atenção 🟡", n_amar, icone="🟡", cor=_COR_AMAR if n_amar > 0 else _COR_CINZA)
    with c6:
        n_sp = resumo.get("sem_presenca_15", 0)
        _card_metrica("Sem presença 15d", n_sp, icone="😶", cor=_COR_VERM if n_sp > 3 else _COR_AMAR)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO 2 — CADASTROS + GAUGE PRESENÇA
    # ═══════════════════════════════════════════════════════════════════════
    col_cad, col_gauge = st.columns([3, 1], gap="large")

    with col_cad:
        with st.container(border=True):
            st.markdown("#### 📈 Evolução de Cadastros (últimos 18 meses)")
            if not df_cad.empty:
                fig_cad = px.bar(
                    df_cad, x="mes", y="novos_alunos",
                    color_discrete_sequence=[_COR_AZUL],
                    labels={"mes": "Mês", "novos_alunos": "Novos Alunos"},
                    text="novos_alunos",
                )
                fig_cad.update_traces(textposition="outside")
                fig_cad.update_layout(
                    height=260, paper_bgcolor=_BG, plot_bgcolor=_BG,
                    margin=dict(t=10, b=30, l=0, r=0),
                    xaxis=dict(tickangle=-45, showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                    showlegend=False,
                )
                st.plotly_chart(fig_cad, use_container_width=True)
            else:
                st.info("Nenhum dado de cadastro disponível.")

    with col_gauge:
        with st.container(border=True):
            st.plotly_chart(_gauge_presenca(resumo.get("taxa_presenca_30", 0.0)),
                            use_container_width=True)
            n_ativos = resumo.get("total_ativos", 0)
            taxa = resumo.get("taxa_presenca_30", 0.0)
            if taxa >= 75:
                st.success(f"✅ Excelente engajamento")
            elif taxa >= 50:
                st.warning(f"⚠️ Presença moderada")
            else:
                st.error(f"🔴 Presença baixa")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO 3 — PRESENÇA POR TURMA + DISTRIBUIÇÃO DE RISCO
    # ═══════════════════════════════════════════════════════════════════════
    col_pt, col_risco = st.columns([3, 2], gap="large")

    with col_pt:
        with st.container(border=True):
            st.markdown(f"#### ✅ Presença por Turma (últimos {periodo} dias)")
            if not df_turmas.empty:
                def _cor_barra(v):
                    if v >= 75: return _COR_VERDE
                    if v >= 50: return _COR_AMAR
                    return _COR_VERM
                cores = [_cor_barra(v) for v in df_turmas["taxa_presenca"]]
                fig_t = go.Figure(go.Bar(
                    x=df_turmas["taxa_presenca"],
                    y=df_turmas["turma"],
                    orientation="h",
                    marker_color=cores,
                    text=[f"{v}%" for v in df_turmas["taxa_presenca"]],
                    textposition="outside",
                ))
                fig_t.add_vline(x=75, line_dash="dash", line_color=_COR_VERDE,
                                annotation_text="Meta 75%", annotation_position="top right")
                fig_t.update_layout(
                    height=max(200, len(df_turmas) * 44),
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    margin=dict(t=10, b=10, l=0, r=60),
                    xaxis=dict(range=[0, 110], showgrid=True, gridcolor="#E2E8F0",
                               title="Taxa de Presença (%)"),
                    yaxis=dict(showgrid=False),
                    showlegend=False,
                )
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("Nenhuma presença registada no período.")

    with col_risco:
        with st.container(border=True):
            st.markdown("#### 🚦 Distribuição de Risco dos Alunos")
            if not df_risco.empty:
                mapa_cor = {
                    "🟢": _COR_VERDE,
                    "🟡": _COR_AMAR,
                    "🔴": _COR_VERM,
                    "⚪": _COR_CINZA,
                }
                mapa_label = {
                    "🟢": "🟢 Baixo risco",
                    "🟡": "🟡 Atenção",
                    "🔴": "🔴 Alto risco",
                    "⚪": "⚪ Sem avaliação",
                }
                df_risco["label_cor"] = df_risco["cor_alerta_atual"].map(
                    lambda x: mapa_label.get(str(x).strip(), str(x))
                )
                df_risco["hex"] = df_risco["cor_alerta_atual"].map(
                    lambda x: mapa_cor.get(str(x).strip(), _COR_CINZA)
                )
                fig_r = px.pie(
                    df_risco, names="label_cor", values="total",
                    color="label_cor",
                    color_discrete_map={v: mapa_cor.get(k, _COR_CINZA)
                                        for k, v in mapa_label.items()},
                    hole=0.48,
                )
                fig_r.update_traces(textinfo="percent+label", textfont_size=11)
                fig_r.update_layout(
                    height=280,
                    paper_bgcolor=_BG,
                    margin=dict(t=10, b=10, l=0, r=0),
                    showlegend=False,
                )
                st.plotly_chart(fig_r, use_container_width=True)
            else:
                st.info("Nenhuma avaliação de risco registada.")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO 4 — FAIXA ETÁRIA + DORES MAIS COMUNS
    # ═══════════════════════════════════════════════════════════════════════
    col_idade, col_dores = st.columns([1, 1], gap="large")

    with col_idade:
        with st.container(border=True):
            st.markdown("#### 🎂 Distribuição por Faixa Etária")
            if not df_todos.empty and "data_nascimento" in df_todos.columns:
                hoje = datetime.date.today()
                df_i = df_todos.copy()
                df_i["dn"] = pd.to_datetime(df_i["data_nascimento"], errors="coerce")
                df_i = df_i.dropna(subset=["dn"])
                df_i["idade"] = df_i["dn"].apply(
                    lambda d: (hoje - d.date()).days // 365 if pd.notna(d) else None
                )
                df_i = df_i.dropna(subset=["idade"])
                bins   = [0, 40, 50, 60, 70, 80, 120]
                labels = ["< 40", "40–49", "50–59", "60–69", "70–79", "80+"]
                df_i["faixa"] = pd.cut(df_i["idade"], bins=bins, labels=labels, right=False)
                contagem = df_i["faixa"].value_counts().reindex(labels, fill_value=0).reset_index()
                contagem.columns = ["faixa", "total"]

                fig_id = px.bar(
                    contagem, x="faixa", y="total",
                    color_discrete_sequence=[_COR_AZUL],
                    labels={"faixa": "Faixa Etária", "total": "Alunos"},
                    text="total",
                )
                fig_id.update_traces(textposition="outside")
                fig_id.update_layout(
                    height=260, paper_bgcolor=_BG, plot_bgcolor=_BG,
                    margin=dict(t=10, b=20, l=0, r=0),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                    showlegend=False,
                )
                st.plotly_chart(fig_id, use_container_width=True)
            else:
                st.info("Sem dados de data de nascimento suficientes.")

    with col_dores:
        with st.container(border=True):
            st.markdown("#### 🩻 Top 10 Dores mais Reportadas no Estúdio")
            if not df_dores.empty:
                fig_d = px.bar(
                    df_dores.sort_values("count"), x="count", y="label",
                    orientation="h",
                    color_discrete_sequence=[_COR_VERM],
                    labels={"count": "Frequência", "label": "Região"},
                    text="count",
                )
                fig_d.update_traces(textposition="outside")
                fig_d.update_layout(
                    height=260, paper_bgcolor=_BG, plot_bgcolor=_BG,
                    margin=dict(t=10, b=10, l=0, r=40),
                    xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                    yaxis=dict(showgrid=False),
                    showlegend=False,
                )
                st.plotly_chart(fig_d, use_container_width=True)
            else:
                st.info("Nenhum mapa de dores registado ainda.")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO 5 — PERFIL SOCIAL (RENDA + INSTRUÇÃO)
    # ═══════════════════════════════════════════════════════════════════════
    col_renda, col_instr = st.columns([1, 1], gap="large")

    with col_renda:
        with st.container(border=True):
            st.markdown("#### 💰 Distribuição por Faixa de Renda")
            if not df_todos.empty and "faixa_renda" in df_todos.columns:
                df_r2 = df_todos["faixa_renda"].dropna()
                df_r2 = df_r2[df_r2.str.strip() != ""].value_counts().reset_index()
                df_r2.columns = ["faixa", "total"]
                if not df_r2.empty:
                    fig_renda = px.pie(df_r2, names="faixa", values="total", hole=0.4,
                                       color_discrete_sequence=px.colors.sequential.Blues_r)
                    fig_renda.update_traces(textinfo="percent+label", textfont_size=10)
                    fig_renda.update_layout(height=240, paper_bgcolor=_BG,
                                             margin=dict(t=5, b=5, l=0, r=0), showlegend=False)
                    st.plotly_chart(fig_renda, use_container_width=True)
                else:
                    st.info("Sem dados de renda preenchidos.")
            else:
                st.info("Sem dados de renda preenchidos.")

    with col_instr:
        with st.container(border=True):
            st.markdown("#### 🎓 Grau de Instrução")
            if not df_todos.empty and "grau_instrucao" in df_todos.columns:
                df_gi = df_todos["grau_instrucao"].dropna()
                df_gi = df_gi[df_gi.str.strip() != ""].value_counts().reset_index()
                df_gi.columns = ["grau", "total"]
                if not df_gi.empty:
                    fig_gi = px.bar(df_gi.sort_values("total"), x="total", y="grau",
                                     orientation="h",
                                     color_discrete_sequence=[_COR_AZUL],
                                     text="total",
                                     labels={"total": "Alunos", "grau": ""})
                    fig_gi.update_traces(textposition="outside")
                    fig_gi.update_layout(height=240, paper_bgcolor=_BG, plot_bgcolor=_BG,
                                          margin=dict(t=5, b=5, l=0, r=40),
                                          xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                                          yaxis=dict(showgrid=False), showlegend=False)
                    st.plotly_chart(fig_gi, use_container_width=True)
                else:
                    st.info("Sem dados de instrução preenchidos.")
            else:
                st.info("Sem dados de instrução preenchidos.")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO 6 — ALUNOS EM RISCO DE ABANDONO
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    n_ab = len(df_abandono) if not df_abandono.empty else 0
    with st.expander(
        f"😶 Alunos sem presença nos últimos {periodo} dias — {n_ab} aluno(s)",
        expanded=n_ab > 0,
    ):
        if n_ab == 0:
            st.success("✅ Todos os alunos ativos tiveram presença no período.")
        else:
            st.caption(
                "Estes alunos estão ativos no sistema mas não apareceram nas aulas. "
                "Considere entrar em contacto para reactivar o engajamento."
            )
            for _, row in df_abandono.iterrows():
                dias_aus = row.get("dias_ausente", 0)
                ult = row.get("ultima_presenca")
                try:
                    import pandas as _pd
                    ult_str = (
                        datetime.date.fromisoformat(str(ult)).strftime("%d/%m/%Y")
                        if ult and not _pd.isna(ult) else "Nunca apareceu"
                    )
                except Exception:
                    ult_str = "Nunca apareceu"
                cor_risco = str(row.get("cor_alerta_atual", "") or "")
                badge_risco = cor_risco if cor_risco in ("🔴", "🟡", "🟢") else "🟢"
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 1.5, 1])
                    c1.markdown(f"**{row.get('nome','?')}**")
                    c2.markdown(
                        f"<span style='color:#64748B;font-size:12px;'>"
                        f"🏫 {row.get('turma','?')}</span>",
                        unsafe_allow_html=True,
                    )
                    c3.markdown(
                        f"<span style='color:#EF4444;font-weight:700;font-size:12px;'>"
                        f"⏱ {dias_aus}d ausente</span>",
                        unsafe_allow_html=True,
                    )
                    c4.markdown(f"{badge_risco} {ult_str}")

    st.markdown(
        "<div style='height:80px'></div>", unsafe_allow_html=True
    )
