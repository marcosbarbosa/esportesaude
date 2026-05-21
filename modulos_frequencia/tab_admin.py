# ==============================================================================
# 🗑️ MÓDULO: tab_admin.py — Exclusão de Dias de Aula (ADMIN MASTER)
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime

from database import (
    listar_datas_aulas_registradas,
    excluir_dia_aula_completo,
    bi_presencas_periodo,
    bi_frequencia_turmas,
    bi_resumo_studio,
    ADMIN_MASTER,
)

_DIAS_PT = {
    "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira", "Friday": "Sexta-feira",
    "Saturday": "Sábado", "Sunday": "Domingo",
}


def renderizar_aba_admin():
    email_op = (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or ""
    )

    if email_op != ADMIN_MASTER:
        st.error("🔒 Acesso restrito — apenas o Administrador Mestre pode usar este painel.")
        return

    st.markdown(
        """<div style='background:#FEF2F2;border:1.5px solid #FCA5A5;border-radius:10px;
        padding:14px 18px 10px;margin-bottom:18px;'>
        <p style='margin:0;font-size:1rem;font-weight:800;color:#991B1B;'>
        ⚠️ Painel de Exclusão de Dias de Aula — Administrador Master</p>
        <p style='margin:4px 0 0;font-size:12px;color:#7F1D1D;'>
        Esta operação apaga <b>permanentemente</b> todos os registros de frequência
        e o diário de aulas da data selecionada. Não há como desfazer.</p></div>""",
        unsafe_allow_html=True,
    )

    # ── Carregar datas registradas ────────────────────────────────────────
    with st.spinner("Carregando datas registradas..."):
        df_datas = listar_datas_aulas_registradas()

    if df_datas.empty:
        st.info("Nenhum dia de aula registrado no banco de dados.")
        return

    # ── Tabela de datas registradas ───────────────────────────────────────
    st.markdown("### 📋 Dias de Aula Registrados")

    df_display = df_datas.copy()
    df_display["data_fmt"] = pd.to_datetime(df_display["data_aula"]).dt.strftime("%d/%m/%Y")
    df_display["dia_semana"] = pd.to_datetime(df_display["data_aula"]).dt.day_name().map(_DIAS_PT)
    df_display["turmas"] = df_display["turmas_diario"].apply(
        lambda t: ", ".join(t) if isinstance(t, list) and t else "—"
    )

    # Identificar domingos/sábados (anomalias)
    df_display["anomalia"] = pd.to_datetime(df_display["data_aula"]).dt.weekday.apply(
        lambda d: "⚠️ Fim de semana" if d >= 5 else ""
    )

    cols_show = ["data_fmt", "dia_semana", "total_presencas", "turmas", "anomalia"]
    df_show = df_display[cols_show].rename(columns={
        "data_fmt": "Data", "dia_semana": "Dia da Semana",
        "total_presencas": "Presenças", "turmas": "Turmas (Diário)",
        "anomalia": "Alerta",
    })

    # Pré-selecionar domingos/sábados para facilitar
    idx_anomalos = df_display[df_display["anomalia"] != ""].index.tolist()
    if idx_anomalos:
        st.warning(
            f"⚠️ Encontrado(s) **{len(idx_anomalos)}** dia(s) de fim de semana com registros — "
            "provavelmente lançamentos incorretos."
        )

    st.dataframe(df_show, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Selecionar data para exclusão ────────────────────────────────────
    st.markdown("### 🗑️ Selecionar Data para Excluir")

    opcoes_datas = df_display["data_aula"].tolist()
    opcoes_label = {
        row["data_aula"]: (
            f"{row['data_fmt']} — {row['dia_semana']}"
            f"  ({row['total_presencas']} presenças)"
            f"{' ⚠️' if row['anomalia'] else ''}"
        )
        for _, row in df_display.iterrows()
    }

    data_sel_str = st.selectbox(
        "📅 Escolha a data a excluir:",
        options=opcoes_datas,
        format_func=lambda d: opcoes_label.get(d, d),
        key="admin_data_excluir",
    )

    if data_sel_str:
        row_sel = df_display[df_display["data_aula"] == data_sel_str].iloc[0]
        n_pres   = int(row_sel["total_presencas"])
        dia_nome = row_sel["dia_semana"]
        turmas_d = row_sel["turmas"]
        data_fmt = row_sel["data_fmt"]
        is_wknd  = row_sel["anomalia"] != ""

        # Resumo do impacto
        fundo = "#FEF2F2" if not is_wknd else "#FFF7ED"
        borda = "#FCA5A5" if not is_wknd else "#FCD34D"
        st.markdown(
            f"""<div style='background:{fundo};border:1.5px solid {borda};border-radius:10px;
            padding:14px 18px;margin:10px 0 16px;'>
            <p style='margin:0;font-size:0.95rem;font-weight:700;color:#1e293b;'>
            📌 Impacto da exclusão de <b>{data_fmt} ({dia_nome})</b></p>
            <ul style='margin:8px 0 0;color:#374151;font-size:13px;'>
            <li>🗂️ Registros de frequência a apagar: <b>{n_pres}</b></li>
            <li>📓 Diários de turma a apagar: <b>{turmas_d}</b></li>
            </ul></div>""",
            unsafe_allow_html=True,
        )

        # Confirmação por digitação
        st.markdown(
            f"Para confirmar, **digite a data exatamente** como aparece: "
            f"`{data_fmt}`"
        )
        confirmacao = st.text_input(
            "Confirmação:", placeholder=f"Ex: {data_fmt}", key="admin_confirma_data"
        )

        btn_excluir = st.button(
            f"🗑️ EXCLUIR {data_fmt} PERMANENTEMENTE",
            type="primary",
            use_container_width=True,
            key="admin_btn_excluir",
            disabled=(confirmacao.strip() != data_fmt),
        )

        if btn_excluir:
            if confirmacao.strip() != data_fmt:
                st.error("A data digitada não confere. Operação cancelada.")
            else:
                with st.spinner("Excluindo registros..."):
                    ok, msg, n_f, n_d = excluir_dia_aula_completo(data_sel_str, email_op)
                if ok:
                    st.success(
                        f"✅ Data **{data_fmt}** excluída com sucesso! "
                        f"({n_f} registros de frequência e {n_d} diários removidos)"
                    )
                    # Flush direto dos caches de BI e do listing
                    for fn in (bi_presencas_periodo, bi_frequencia_turmas,
                                bi_resumo_studio, listar_datas_aulas_registradas):
                        try:
                            fn.clear()
                        except Exception:
                            pass
                    # Sinaliza para a aba BI que houve exclusão
                    st.session_state["bi_cache_dirty"] = True
                    if "admin_confirma_data" in st.session_state:
                        del st.session_state["admin_confirma_data"]
                    st.rerun()
                else:
                    st.error(f"❌ Erro: {msg}")
