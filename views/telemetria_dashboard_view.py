# 📡 Dashboard de Telemetria de Uso — restrito a SuperAdmin
# Exibe métricas de navegação, funil de uso e ranking de módulos
# com base nos dados da tabela telemetria_uso.

import streamlit as st
from datetime import datetime, timezone, timedelta


def tela_dashboard_telemetria() -> None:
    """Renderiza o painel de BI interno de telemetria de uso."""

    st.markdown(
        "<h3 style='color:#0A2540;margin-bottom:4px;'>📡 Telemetria de Uso</h3>"
        "<p style='color:#64748B;font-size:0.85rem;margin-bottom:16px;'>"
        "Dados de navegação e ações dos operadores no sistema.</p>",
        unsafe_allow_html=True,
    )

    # ── Controle de período ───────────────────────────────────────────────────
    col_ctrl1, col_ctrl2, _ = st.columns([1, 1, 4])
    with col_ctrl1:
        dias = st.selectbox(
            "Período",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda d: f"Últimos {d} dias",
            key="tel_periodo",
        )
    with col_ctrl2:
        if st.button("🔄 Atualizar", key="tel_refresh"):
            st.cache_data.clear()

    # ── Carregar dados ────────────────────────────────────────────────────────
    from database import get_telemetria_uso_df

    with st.spinner("Carregando dados de telemetria…"):
        df = get_telemetria_uso_df(dias=dias)

    if df is None or df.empty:
        st.info(
            "Nenhum dado de telemetria encontrado para o período selecionado. "
            "Verifique se a tabela `telemetria_uso` foi criada no Supabase."
        )
        return

    import pandas as pd

    now_utc = datetime.now(timezone.utc)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 1 — KPIs de topo
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)

    total_eventos = len(df)
    usuarios_unicos = df["usuario_id"].nunique()
    dias_com_atividade = df["ts"].dt.date.nunique()
    media_dia = round(total_eventos / max(dias_com_atividade, 1), 1)

    k1.metric("📊 Total de Eventos", f"{total_eventos:,}".replace(",", "."))
    k2.metric("👤 Operadores Únicos", usuarios_unicos)
    k3.metric("📅 Dias com Atividade", dias_com_atividade)
    k4.metric("⚡ Média Eventos/Dia", media_dia)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 2 — Módulos mais usados
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "#### 🏆 Módulos Mais Usados"
        f"<span style='font-size:0.78rem;color:#94A3B8;margin-left:8px;'>"
        f"últimos {dias} dias</span>",
        unsafe_allow_html=True,
    )

    ranking = (
        df.groupby("acao_modulo")
        .agg(
            eventos=("id", "count"),
            usuarios=("usuario_id", "nunique"),
        )
        .reset_index()
        .rename(columns={
            "acao_modulo": "Módulo / Ação",
            "eventos":     "Eventos",
            "usuarios":    "Usuários Únicos",
        })
        .sort_values("Eventos", ascending=False)
        .reset_index(drop=True)
    )
    ranking.index += 1   # ranking começa em 1

    st.dataframe(
        ranking,
        use_container_width=True,
        height=min(40 + len(ranking) * 35, 520),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 3 — Funil de Frequência (últimos 7 dias)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "#### 🔽 Funil — Módulo de Frequência"
        "<span style='font-size:0.78rem;color:#94A3B8;margin-left:8px;'>"
        "últimos 7 dias</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Mostra quantos operadores navegaram para Frequência → abriram a tela "
        "→ executaram ao menos uma reativação de aluno."
    )

    cutoff_7d = now_utc - timedelta(days=7)
    df7 = df[df["ts"] >= cutoff_7d]

    def _cnt(acao: str) -> int:
        return int((df7["acao_modulo"] == acao).sum())

    navegou  = _cnt("nav_frequencia")
    abriu    = _cnt("vis_frequencia")
    reativou = _cnt("acao_reativou_aluno")

    f1, f2, f3 = st.columns(3)
    f1.metric("🗺️ Navegou para Frequência", navegou)
    f2.metric(
        "🖥️ Abriu a Tela",
        abriu,
        delta=f"{abriu - navegou:+d} vs navegou" if navegou else None,
        delta_color="off",
    )
    f3.metric(
        "♻️ Reativou Aluno",
        reativou,
        delta=f"{reativou - abriu:+d} vs abriu" if abriu else None,
        delta_color="off",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 4 — Atividade por perfil
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "#### 👥 Eventos por Perfil de Usuário"
        f"<span style='font-size:0.78rem;color:#94A3B8;margin-left:8px;'>"
        f"últimos {dias} dias</span>",
        unsafe_allow_html=True,
    )

    por_perfil = (
        df.groupby("perfil")
        .agg(
            eventos=("id", "count"),
            usuarios=("usuario_id", "nunique"),
        )
        .reset_index()
        .rename(columns={
            "perfil":   "Perfil",
            "eventos":  "Eventos",
            "usuarios": "Usuários Únicos",
        })
        .sort_values("Eventos", ascending=False)
        .reset_index(drop=True)
    )

    st.dataframe(por_perfil, use_container_width=True, height=min(80 + len(por_perfil) * 35, 300))

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCO 5 — Eventos por dia (série temporal simples)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "#### 📈 Volume de Eventos por Dia"
        f"<span style='font-size:0.78rem;color:#94A3B8;margin-left:8px;'>"
        f"últimos {dias} dias</span>",
        unsafe_allow_html=True,
    )

    df_copy = df.copy()
    df_copy["data"] = df_copy["ts"].dt.date
    por_dia = (
        df_copy.groupby("data")["id"]
        .count()
        .reset_index()
        .rename(columns={"id": "Eventos", "data": "Data"})
        .sort_values("Data")
    )
    por_dia["Data"] = pd.to_datetime(por_dia["Data"])
    por_dia = por_dia.set_index("Data")

    st.line_chart(por_dia["Eventos"], use_container_width=True, height=200)

    st.caption(
        f"Dados extraídos de `telemetria_uso` · "
        f"{total_eventos:,} registros · gerado em "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}".replace(",", ".")
    )
