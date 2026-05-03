# ==============================================================================
# 👤 Módulo: BI Prime — Relatório Individual do Aluno
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import json

from database import (
    buscar_alunos_geral,
    bi_dados_individuais,
)
from views.anamnese_dores_view import render_mapa_corporal, REGIOES

_COR_AZUL  = "#0056b3"
_COR_VERDE = "#10B981"
_COR_AMAR  = "#F59E0B"
_COR_VERM  = "#EF4444"
_COR_CINZA = "#94A3B8"
_BG        = "#F8FAFC"


# ── helpers ───────────────────────────────────────────────────────────────────
def _imc(peso, altura_cm):
    try:
        h = float(altura_cm) / 100
        return round(float(peso) / (h * h), 1) if h > 0 else None
    except Exception:
        return None


def _idade(dn_str):
    try:
        dn = datetime.date.fromisoformat(str(dn_str)[:10])
        return (datetime.date.today() - dn).days // 365
    except Exception:
        return None


def _fmt_data(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10]).strftime("%d/%m/%Y")
    except Exception:
        return str(v) if v else "—"


def _mini_card(label, valor, cor="#0056b3", icone=""):
    st.markdown(
        f"""<div style='background:#fff;border-radius:10px;padding:14px 16px;
        border-left:4px solid {cor};box-shadow:0 2px 8px rgba(0,0,0,.06);height:90px;'>
        <div style='font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;
        letter-spacing:.4px;'>{icone} {label}</div>
        <div style='font-size:22px;font-weight:900;color:{cor};line-height:1.2;margin-top:6px;'>
        {valor}</div></div>""",
        unsafe_allow_html=True,
    )


def _linha_vazia():
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)


# ── presença mensal ───────────────────────────────────────────────────────────
def _df_presenca_mensal(df_freq):
    if df_freq.empty:
        return pd.DataFrame()
    df = df_freq.copy()
    df["data_aula"] = pd.to_datetime(df["data_aula"], errors="coerce")
    df = df.dropna(subset=["data_aula"])
    df["mes"] = df["data_aula"].dt.to_period("M").astype(str)
    grp = df.groupby("mes").apply(
        lambda g: pd.Series({
            "presentes": (g["status"] == "PRESENTE").sum(),
            "faltas":    (g["status"] == "FALTA").sum(),
            "total":     len(g),
        })
    ).reset_index()
    grp["taxa"] = (grp["presentes"] / grp["total"] * 100).round(1)
    return grp.tail(18)


# ── mapa de dores acumulado ───────────────────────────────────────────────────
def _mapa_acumulado(dores_list):
    """
    Recebe lista de registos de anamnese_dores e retorna
    (regioes_set, intensidades_dict) com frequência → intensidade.
    """
    from collections import Counter
    counter = Counter()
    for reg in dores_list:
        for rid in (reg.get("regioes") or []):
            counter[rid] += 1
    if not counter:
        return [], {}
    max_count = max(counter.values())
    regioes_sel = list(counter.keys())
    intensidades = {}
    for rid, cnt in counter.items():
        ratio = cnt / max_count
        intensidades[rid] = 3 if ratio > 0.6 else (2 if ratio > 0.3 else 1)
    return regioes_sel, intensidades


# ──────────────────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ──────────────────────────────────────────────────────────────────────────────
def render_bi_individual():
    st.markdown("## 👤 BI Prime — Relatório Individual do Aluno")
    st.caption(
        "Visão clínica e de engajamento completa de cada aluno — "
        "evolução de saúde, presença, dores e histórico de avaliações."
    )

    # ── seletor de aluno ─────────────────────────────────────────────────────
    df_todos = buscar_alunos_geral(incluir_inativos=True)
    if df_todos.empty:
        st.warning("Nenhum aluno encontrado.")
        return

    def _lbl(r):
        st = "🗃️ " if r.get("status") == "Inativo" else ""
        return f"{st}{r.get('nome','?')}  [{r.get('turma','?')}]"

    opcoes = {_lbl(r): r["id"] for _, r in df_todos.sort_values("nome").iterrows()}
    escolha = st.selectbox(
        "Selecione o aluno:",
        options=list(opcoes.keys()),
        index=None,
        placeholder="Busque pelo nome…",
        key="bi_ind_aluno",
    )
    if not escolha:
        st.info("Selecione um aluno acima para ver o relatório completo.")
        return

    aluno_id = opcoes[escolha]
    aluno    = df_todos[df_todos["id"] == aluno_id].iloc[0].to_dict()

    with st.spinner("Carregando dados do aluno…"):
        dados = bi_dados_individuais(str(aluno_id))

    df_aval  = dados.get("avaliacoes", pd.DataFrame())
    df_freq  = dados.get("frequencias", pd.DataFrame())
    df_ates  = dados.get("atestados",   pd.DataFrame())
    dores    = dados.get("dores",        [])

    # ── cabeçalho do aluno ────────────────────────────────────────────────────
    nome   = aluno.get("nome", "?")
    turma  = aluno.get("turma", "?")
    status = aluno.get("status", "Ativo")
    idade  = _idade(aluno.get("data_nascimento"))
    created = _fmt_data(aluno.get("created_at"))
    cor_alerta = aluno.get("cor_alerta_atual", "")
    badge_status = (
        "<span style='background:#DCFCE7;color:#166534;padding:2px 10px;"
        "border-radius:12px;font-size:12px;font-weight:700;'>✅ Ativo</span>"
        if status == "Ativo" else
        "<span style='background:#F1F5F9;color:#475569;padding:2px 10px;"
        "border-radius:12px;font-size:12px;font-weight:700;'>🗃️ Inativo</span>"
    )
    badge_risco = {
        "🟢": "<span style='background:#DCFCE7;color:#166534;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;'>🟢 Baixo risco</span>",
        "🟡": "<span style='background:#FEF9C3;color:#854D0E;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;'>🟡 Atenção</span>",
        "🔴": "<span style='background:#FEE2E2;color:#991B1B;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;'>🔴 Alto risco</span>",
    }.get(str(cor_alerta).strip(), "")

    url_foto = aluno.get("url_foto") or aluno.get("foto_url") or ""

    col_foto, col_info = st.columns([1, 5], gap="large")
    with col_foto:
        if url_foto:
            st.image(url_foto, width=90)
        else:
            st.markdown(
                "<div style='width:80px;height:80px;border-radius:50%;background:#E2E8F0;"
                "display:flex;align-items:center;justify-content:center;"
                "font-size:32px;'>👤</div>",
                unsafe_allow_html=True,
            )
    with col_info:
        st.markdown(
            f"<h3 style='margin:0;color:#0A2540;'>{nome}</h3>"
            f"<div style='margin-top:4px;display:flex;gap:8px;flex-wrap:wrap;'>"
            f"{badge_status} {badge_risco}"
            f"<span style='color:#64748B;font-size:13px;'>🏫 {turma}</span>"
            + (f"<span style='color:#64748B;font-size:13px;'>🎂 {idade} anos</span>" if idade else "")
            + f"<span style='color:#64748B;font-size:13px;'>📅 desde {created}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── KPI cards ────────────────────────────────────────────────────────────
    _linha_vazia()
    n_total   = len(df_freq)
    n_pres    = len(df_freq[df_freq["status"] == "PRESENTE"]) if not df_freq.empty else 0
    taxa_pres = round(n_pres / n_total * 100, 1) if n_total > 0 else 0.0
    cor_taxa  = _COR_VERDE if taxa_pres >= 75 else (_COR_AMAR if taxa_pres >= 50 else _COR_VERM)

    ultima_pres_str = "—"
    dias_ausente    = None
    if not df_freq.empty:
        pres_df = df_freq[df_freq["status"] == "PRESENTE"]
        if not pres_df.empty:
            ult_data = pres_df["data_aula"].max()
            ultima_pres_str = _fmt_data(ult_data)
            try:
                dias_ausente = (datetime.date.today() - datetime.date.fromisoformat(str(ult_data)[:10])).days
            except Exception:
                pass

    ultima_aval_str = "—"
    nota_risco_str  = "—"
    peso_atual      = "—"
    imc_atual       = "—"
    if not df_aval.empty:
        ultima_aval = df_aval.sort_values("data_avaliacao").iloc[-1]
        ultima_aval_str = _fmt_data(ultima_aval.get("data_avaliacao"))
        nota_risco_str  = str(ultima_aval.get("nivel_dor", "—"))
        p = ultima_aval.get("peso"); h = ultima_aval.get("altura")
        if p and h:
            peso_atual = f"{p} kg"
            imc_v = _imc(p, h)
            if imc_v:
                imc_atual = f"{imc_v}"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _mini_card("Presença Geral", f"{taxa_pres}%", cor=cor_taxa, icone="✅")
    with c2:
        cor_d = _COR_VERM if dias_ausente and dias_ausente > 15 else _COR_AZUL
        _mini_card("Dias sem presença", f"{dias_ausente}d" if dias_ausente is not None else "—",
                   cor=cor_d, icone="📅")
    with c3:
        _mini_card("Última avaliação", ultima_aval_str, cor=_COR_AZUL, icone="📋")
    with c4:
        _mini_card("Peso atual", peso_atual, cor=_COR_AZUL, icone="⚖️")
    with c5:
        imc_f = float(imc_atual) if imc_atual != "—" else None
        cor_imc = (
            _COR_VERDE if imc_f and imc_f < 25
            else (_COR_AMAR if imc_f and imc_f < 30 else _COR_VERM)
        ) if imc_f else _COR_CINZA
        _mini_card("IMC", imc_atual, cor=cor_imc, icone="📐")

    _linha_vazia()

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO A — EVOLUÇÃO CLÍNICA (Peso/IMC + Nível de Dor)
    # ═══════════════════════════════════════════════════════════════════════
    col_imc, col_dor = st.columns([1, 1], gap="large")

    with col_imc:
        with st.container(border=True):
            st.markdown("#### ⚖️ Evolução de Peso e IMC")
            if not df_aval.empty and "peso" in df_aval.columns and "altura" in df_aval.columns:
                df_p = df_aval.copy()
                df_p["data_avaliacao"] = pd.to_datetime(df_p["data_avaliacao"], errors="coerce")
                df_p = df_p.dropna(subset=["data_avaliacao", "peso", "altura"])
                df_p["imc"] = df_p.apply(
                    lambda r: _imc(r["peso"], r["altura"]), axis=1
                )
                df_p = df_p.dropna(subset=["imc"])
                if not df_p.empty:
                    fig_imc = go.Figure()
                    fig_imc.add_trace(go.Scatter(
                        x=df_p["data_avaliacao"], y=df_p["peso"],
                        name="Peso (kg)", line=dict(color=_COR_AZUL, width=2),
                        mode="lines+markers",
                    ))
                    fig_imc.add_trace(go.Scatter(
                        x=df_p["data_avaliacao"], y=df_p["imc"],
                        name="IMC", line=dict(color=_COR_AMAR, width=2, dash="dot"),
                        mode="lines+markers", yaxis="y2",
                    ))
                    fig_imc.update_layout(
                        height=260, paper_bgcolor=_BG, plot_bgcolor=_BG,
                        margin=dict(t=10, b=20, l=0, r=50),
                        legend=dict(orientation="h", y=-0.25),
                        yaxis=dict(title="Peso (kg)", showgrid=True, gridcolor="#E2E8F0"),
                        yaxis2=dict(title="IMC", overlaying="y", side="right", showgrid=False),
                        xaxis=dict(showgrid=False),
                    )
                    st.plotly_chart(fig_imc, use_container_width=True)
                    # IMC reference
                    st.caption("IMC: 🟢 < 25 normal | 🟡 25–30 sobrepeso | 🔴 > 30 obesidade")
                else:
                    st.info("Dados insuficientes para calcular IMC.")
            else:
                st.info("Nenhuma avaliação com peso/altura registada.")

    with col_dor:
        with st.container(border=True):
            st.markdown("#### 😣 Evolução do Nível de Dor e TUG")
            if not df_aval.empty and "nivel_dor" in df_aval.columns:
                df_d = df_aval.copy()
                df_d["data_avaliacao"] = pd.to_datetime(df_d["data_avaliacao"], errors="coerce")
                df_d = df_d.dropna(subset=["data_avaliacao"])

                fig_d = go.Figure()
                if df_d["nivel_dor"].notna().any():
                    fig_d.add_trace(go.Scatter(
                        x=df_d["data_avaliacao"], y=pd.to_numeric(df_d["nivel_dor"], errors="coerce"),
                        name="Nível de Dor (0–10)", line=dict(color=_COR_VERM, width=2),
                        mode="lines+markers",
                    ))
                if "tug_segundos" in df_d.columns and df_d["tug_segundos"].notna().any():
                    fig_d.add_trace(go.Scatter(
                        x=df_d["data_avaliacao"],
                        y=pd.to_numeric(df_d["tug_segundos"], errors="coerce"),
                        name="TUG (s)", line=dict(color=_COR_AZUL, width=2, dash="dot"),
                        mode="lines+markers", yaxis="y2",
                    ))
                fig_d.update_layout(
                    height=260, paper_bgcolor=_BG, plot_bgcolor=_BG,
                    margin=dict(t=10, b=20, l=0, r=50),
                    legend=dict(orientation="h", y=-0.25),
                    yaxis=dict(title="Dor (0–10)", range=[0, 10],
                               showgrid=True, gridcolor="#E2E8F0"),
                    yaxis2=dict(title="TUG (s)", overlaying="y", side="right",
                                showgrid=False),
                    xaxis=dict(showgrid=False),
                )
                if fig_d.data:
                    st.plotly_chart(fig_d, use_container_width=True)
                    st.caption("TUG ≤ 12s normal | > 20s risco de queda elevado")
                else:
                    st.info("Sem dados de dor/TUG registados.")
            else:
                st.info("Nenhuma avaliação registada.")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO B — PRESENÇA MENSAL
    # ═══════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown("#### ✅ Frequência Mensal")
        df_pm = _df_presenca_mensal(df_freq)
        if not df_pm.empty:
            fig_pm = go.Figure()
            fig_pm.add_trace(go.Bar(
                x=df_pm["mes"], y=df_pm["presentes"],
                name="Presenças", marker_color=_COR_VERDE,
            ))
            fig_pm.add_trace(go.Bar(
                x=df_pm["mes"], y=df_pm["faltas"],
                name="Faltas", marker_color=_COR_VERM,
            ))
            fig_pm.add_trace(go.Scatter(
                x=df_pm["mes"], y=df_pm["taxa"],
                name="Taxa %", mode="lines+markers",
                line=dict(color=_COR_AZUL, width=2),
                yaxis="y2",
            ))
            fig_pm.update_layout(
                barmode="stack", height=280,
                paper_bgcolor=_BG, plot_bgcolor=_BG,
                margin=dict(t=10, b=30, l=0, r=50),
                legend=dict(orientation="h", y=-0.3),
                xaxis=dict(tickangle=-45, showgrid=False),
                yaxis=dict(title="Aulas", showgrid=True, gridcolor="#E2E8F0"),
                yaxis2=dict(title="Taxa (%)", overlaying="y", side="right",
                            range=[0, 110], showgrid=False),
            )
            st.plotly_chart(fig_pm, use_container_width=True)

            total_p  = int(df_pm["presentes"].sum())
            total_f  = int(df_pm["faltas"].sum())
            taxa_ger = round(total_p / (total_p + total_f) * 100, 1) if (total_p + total_f) > 0 else 0
            st.caption(
                f"Total: **{total_p + total_f}** registos — "
                f"**{total_p}** presenças / **{total_f}** faltas — "
                f"taxa geral: **{taxa_ger}%**"
            )
        else:
            st.info("Nenhum registo de frequência para este aluno.")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO C — MAPA DE DORES ACUMULADO
    # ═══════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown("#### 🩻 Mapa de Dores Acumulado")
        if dores:
            n_sessoes = len(dores)
            st.caption(
                f"Acumulado de **{n_sessoes}** avaliação(ões). "
                "🔴 Intensa = região muito recorrente | "
                "🟠 Moderada = aparece frequentemente | "
                "🟡 Leve = poucas ocorrências."
            )
            regioes_ac, intensidades_ac = _mapa_acumulado(dores)
            render_mapa_corporal(regioes_ac, intensidades_ac, height=500)

            # Ranking de regiões
            from collections import Counter
            counter = Counter()
            for reg in dores:
                for rid in (reg.get("regioes") or []):
                    counter[rid] += 1
            if counter:
                st.markdown("**Regiões mais frequentes:**")
                badges = []
                for rid, cnt in counter.most_common(10):
                    label = REGIOES.get(rid, {}).get("label", rid)
                    badges.append(
                        f"<span style='background:#FEE2E2;color:#991B1B;padding:3px 10px;"
                        f"border-radius:12px;font-size:12px;font-weight:600;margin:2px;"
                        f"display:inline-block;'>{label} ×{cnt}</span>"
                    )
                st.markdown(" ".join(badges), unsafe_allow_html=True)
        else:
            st.info("Nenhum mapa de dores registado para este aluno.")

    # ═══════════════════════════════════════════════════════════════════════
    # SEÇÃO D — ATESTADOS E ÚLTIMAS AVALIAÇÕES
    # ═══════════════════════════════════════════════════════════════════════
    col_ates, col_aval = st.columns([1, 1], gap="large")

    with col_ates:
        with st.container(border=True):
            st.markdown("#### 📄 Atestados e Afastamentos")
            if not df_ates.empty:
                for _, row in df_ates.head(10).iterrows():
                    with st.container(border=False):
                        st.markdown(
                            f"📅 **{_fmt_data(row.get('data_registro'))}** — "
                            f"{row.get('motivo') or '(sem motivo registado)'}"
                        )
                    st.divider()
            else:
                st.info("Nenhum atestado registado.")

    with col_aval:
        with st.container(border=True):
            st.markdown("#### 📋 Últimas Avaliações Clínicas")
            if not df_aval.empty:
                colunas_exibir = [
                    "data_avaliacao", "peso", "altura",
                    "nivel_dor", "tug_segundos", "borg",
                ]
                colunas_ok = [c for c in colunas_exibir if c in df_aval.columns]
                df_show = df_aval.sort_values("data_avaliacao", ascending=False)[colunas_ok].head(8)
                rename = {
                    "data_avaliacao": "Data",
                    "peso":           "Peso (kg)",
                    "altura":         "Altura (cm)",
                    "nivel_dor":      "Dor (0–10)",
                    "tug_segundos":   "TUG (s)",
                    "borg":           "Borg",
                }
                df_show = df_show.rename(columns=rename)
                if "Data" in df_show.columns:
                    df_show["Data"] = df_show["Data"].apply(_fmt_data)
                st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma avaliação clínica registada.")

    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
