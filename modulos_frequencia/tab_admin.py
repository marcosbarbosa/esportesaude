# ==============================================================================
# 🗑️ MÓDULO: tab_admin.py — Exclusão de Dias de Aula (ADMIN MASTER)
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
from dateutil.easter import easter

from database import (
    listar_datas_aulas_registradas,
    excluir_dia_aula_completo,
    bi_presencas_periodo,
    bi_frequencia_turmas,
    bi_resumo_studio,
    backfill_nome_fonetica,
    _coluna_fonetica_disponivel,
    _coluna_fonetica_pronta,
    ADMIN_MASTER,
)

_DIAS_PT = {
    "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira", "Friday": "Sexta-feira",
    "Saturday": "Sábado", "Sunday": "Domingo",
}


def _feriados_sp(anos) -> dict:
    """
    Retorna {date: nome_feriado} com feriados nacionais + SP estado + SP cidade
    para os anos solicitados.
    """
    feriados = {}
    for ano in anos:
        # ── Pascoa base para feriados moveis ──────────────────────────────
        p = easter(ano)
        td = datetime.timedelta

        # Nacionais fixos
        fixos = [
            (1,  1,  "Ano Novo"),
            (4,  21, "Tiradentes"),
            (5,  1,  "Dia do Trabalho"),
            (9,  7,  "Independência do Brasil"),
            (10, 12, "Nossa Senhora Aparecida"),
            (11, 2,  "Finados"),
            (11, 15, "Proclamação da República"),
            (11, 20, "Consciência Negra"),
            (12, 25, "Natal"),
        ]
        for mes, dia, nome in fixos:
            feriados[datetime.date(ano, mes, dia)] = nome

        # Nacionais móveis
        feriados[p - td(days=48)] = "Carnaval (2ª feira)"
        feriados[p - td(days=47)] = "Carnaval (3ª feira)"
        feriados[p - td(days=2)]  = "Sexta-feira Santa"
        feriados[p]               = "Páscoa"
        feriados[p + td(days=60)] = "Corpus Christi"

        # SP Estado
        feriados[datetime.date(ano, 7, 9)] = "Revolução Constitucionalista (SP)"

        # SP Cidade
        feriados[datetime.date(ano, 1, 25)] = "Aniversário de São Paulo"

    return feriados


def _classificar_anomalia(dt: datetime.date, feriados: dict) -> str:
    """Retorna string de alerta ou '' para a data informada."""
    alertas = []
    if dt.weekday() >= 5:
        alertas.append("Fim de semana")
    nome_fer = feriados.get(dt)
    if nome_fer:
        alertas.append(f"Feriado: {nome_fer}")
    return " + ".join(alertas) if alertas else ""


def _renderizar_bloco_fonetica():
    """Painel admin para ativar a busca rápida (índice fonético no banco).

    A coluna `alunos.nome_fonetica` precisa ser criada por DDL no Supabase
    (não há acesso ao schema a partir daqui). Depois de criada, este painel
    retro-preenche os alunos existentes via `backfill_nome_fonetica`, ativando
    o filtro server-side em `buscar_alunos_geral`."""
    with st.expander("🔎 Busca rápida (índice fonético)", expanded=False):
        coluna_existe = _coluna_fonetica_disponivel()
        coluna_pronta = _coluna_fonetica_pronta() if coluna_existe else False

        if not coluna_existe:
            st.warning(
                "A coluna `nome_fonetica` ainda **não existe** no Supabase. "
                "Enquanto isso, a busca usa o caminho atual (baixa a base inteira "
                "e filtra no app) — sem regressão, porém menos escalável."
            )
            st.markdown(
                "**Passo 1 — rodar no Supabase (SQL Editor):**\n"
                "```sql\n"
                "ALTER TABLE alunos ADD COLUMN nome_fonetica text;\n"
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;\n"
                "CREATE INDEX idx_alunos_nome_fonetica_trgm\n"
                "  ON alunos USING gin (nome_fonetica gin_trgm_ops);\n"
                "```\n"
                "**Passo 2** — voltar aqui e clicar em **Retro-preencher** abaixo."
            )
        elif coluna_pronta:
            st.success(
                "✅ Coluna `nome_fonetica` criada e **100% preenchida**. "
                "A busca já roda **server-side** (escalável)."
            )
            st.caption(
                "Rode o retro-preenchimento novamente apenas se importar alunos "
                "em massa por fora do app."
            )
        else:
            st.info(
                "A coluna `nome_fonetica` existe, mas há alunos **sem preenchimento**. "
                "Clique em **Retro-preencher** para ativar a busca server-side."
            )

        if st.button(
            "🔁 Retro-preencher índice fonético",
            use_container_width=True,
            key="admin_btn_backfill_fonetica",
            disabled=not coluna_existe,
        ):
            with st.spinner("Retro-preenchendo `nome_fonetica`..."):
                ok, msg = backfill_nome_fonetica()
            if ok:
                st.success(f"✅ {msg}")
                for fn in (_coluna_fonetica_disponivel, _coluna_fonetica_pronta):
                    try:
                        fn.clear()
                    except Exception:
                        pass
                st.rerun()
            else:
                st.error(f"❌ {msg}")


def renderizar_aba_admin():
    email_op = (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or ""
    )

    if email_op != ADMIN_MASTER:
        st.error("🔒 Acesso restrito — apenas o Administrador Mestre pode usar este painel.")
        return

    _renderizar_bloco_fonetica()

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
    dts_parsed = pd.to_datetime(df_display["data_aula"])
    df_display["data_fmt"]  = dts_parsed.dt.strftime("%d/%m/%Y")
    df_display["dia_semana"] = dts_parsed.dt.day_name().map(_DIAS_PT)
    df_display["turmas"] = df_display["turmas_diario"].apply(
        lambda t: ", ".join(t) if isinstance(t, list) and t else "—"
    )

    # Construir dicionário de feriados para todos os anos presentes nos dados
    anos_dados = set(dts_parsed.dt.year.dropna().astype(int).tolist())
    feriados = _feriados_sp(anos_dados)

    # Classificar cada data: fim de semana, feriado ou ambos
    df_display["anomalia"] = dts_parsed.apply(
        lambda dt: _classificar_anomalia(dt.date(), feriados) if pd.notna(dt) else ""
    )

    cols_show = ["data_fmt", "dia_semana", "total_presencas", "turmas", "anomalia"]
    df_show = df_display[cols_show].rename(columns={
        "data_fmt": "Data", "dia_semana": "Dia da Semana",
        "total_presencas": "Presenças", "turmas": "Turmas (Diário)",
        "anomalia": "Alerta",
    })

    # Resumo dos alertas encontrados
    idx_anomalos = df_display[df_display["anomalia"] != ""].index.tolist()
    if idx_anomalos:
        n_fds      = (df_display["anomalia"].str.contains("Fim de semana", na=False)).sum()
        n_fer      = (df_display["anomalia"].str.contains("Feriado", na=False)).sum()
        partes = []
        if n_fds: partes.append(f"**{n_fds}** fim(ns) de semana")
        if n_fer: partes.append(f"**{n_fer}** feriado(s)")
        st.warning(
            f"⚠️ Encontrado(s) {' e '.join(partes)} com registros de aula — "
            "verifique se foram lançamentos incorretos."
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
