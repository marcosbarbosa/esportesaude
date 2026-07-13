# ==============================================================================
# 📅 MÓDULO: tab_admin.py — Dias Regist./Anamnese + Exclusão (ADMIN MASTER)
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
from dateutil.easter import easter

from database import (
    listar_datas_aulas_registradas,
    contar_presencas_periodo_direto,
    excluir_dia_aula_completo,
    bi_presencas_periodo,
    bi_frequencia_turmas,
    bi_resumo_studio,
    backfill_nome_fonetica,
    _coluna_fonetica_disponivel,
    _coluna_fonetica_pronta,
    ADMIN_MASTER,
    get_config_valor,
    set_config_valor,
)

CHAVE_DIAS_VALIDADE_ANAMNESE = "config_dias_validade_anamnese"
DIAS_VALIDADE_ANAMNESE_PADRAO = 180


def get_dias_validade_anamnese() -> int:
    try:
        return int(get_config_valor(CHAVE_DIAS_VALIDADE_ANAMNESE, DIAS_VALIDADE_ANAMNESE_PADRAO))
    except (TypeError, ValueError):
        return DIAS_VALIDADE_ANAMNESE_PADRAO


_DIAS_PT = {
    "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira", "Friday": "Sexta-feira",
    "Saturday": "Sábado", "Sunday": "Domingo",
}


def _feriados_sp(anos) -> dict:
    feriados = {}
    for ano in anos:
        p = easter(ano)
        td = datetime.timedelta
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
        feriados[p - td(days=48)] = "Carnaval (2ª feira)"
        feriados[p - td(days=47)] = "Carnaval (3ª feira)"
        feriados[p - td(days=2)]  = "Sexta-feira Santa"
        feriados[p]               = "Páscoa"
        feriados[p + td(days=60)] = "Corpus Christi"
        feriados[datetime.date(ano, 7, 9)]  = "Revolução Constitucionalista (SP)"
        feriados[datetime.date(ano, 1, 25)] = "Aniversário de São Paulo"
    return feriados


def _classificar_anomalia(dt: datetime.date, feriados: dict) -> str:
    alertas = []
    if dt.weekday() >= 5:
        alertas.append("Fim de semana")
    nome_fer = feriados.get(dt)
    if nome_fer:
        alertas.append(f"Feriado: {nome_fer}")
    return " + ".join(alertas) if alertas else ""


# ── Bloco: busca fonética ──────────────────────────────────────────────────────
def _renderizar_bloco_fonetica():
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


# ── Bloco: validade da anamnese ────────────────────────────────────────────────
def _renderizar_bloco_validade_anamnese():
    with st.expander("🩺 Validade da Anamnese (reavaliação clínica)", expanded=False):
        atual = get_dias_validade_anamnese()
        st.caption(
            f"Período atual: **{atual} dias** desde a última avaliação registrada "
            "no prontuário. Após esse prazo, o aluno aparece como 'Vencida' na "
            "coluna Anamnese do grid Alunos Ativos."
        )
        novo = st.number_input(
            "Dias de validade da anamnese",
            min_value=30, max_value=730, step=10, value=atual,
            key="admin_dias_validade_anamnese",
        )
        if st.button("💾 Salvar validade da anamnese", key="admin_btn_salvar_validade_anamnese"):
            ok, msg = set_config_valor(CHAVE_DIAS_VALIDADE_ANAMNESE, int(novo))
            if ok:
                st.success(f"✅ Validade da anamnese atualizada para {int(novo)} dias.")
                st.rerun()
            else:
                st.error(f"❌ Erro ao salvar: {msg}")


# ── Renderizador principal da aba ──────────────────────────────────────────────
def renderizar_aba_admin():
    email_op = (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or ""
    )

    if email_op != ADMIN_MASTER:
        st.error("🔒 Acesso restrito — apenas o Administrador Mestre pode usar este painel.")
        return

    with st.spinner("Carregando datas..."):
        df_datas = listar_datas_aulas_registradas()

    # ── Dias de Aula Registrados ───────────────────────────────────────────────
    st.markdown("### 📋 Dias de Aula Registrados")

    hoje = datetime.date.today()

    # Default De: 5º dia de aula mais recente registrado no banco.
    # Usa df_datas (já carregado) para encontrar exatamente as datas reais de aula,
    # evitando janelas de 30 dias com muitos dias sem dados.
    _KEY_INI_DEFAULT = "admin_data_ini_default_computado"
    if _KEY_INI_DEFAULT not in st.session_state:
        if not df_datas.empty:
            _datas_ord = sorted(
                [d[:10] for d in df_datas["data_aula"].astype(str).tolist() if d],
                reverse=True,
            )
            _idx = min(4, len(_datas_ord) - 1)   # 5º mais recente (índice 4)
            try:
                st.session_state[_KEY_INI_DEFAULT] = datetime.date.fromisoformat(
                    _datas_ord[_idx]
                )
            except Exception:
                st.session_state[_KEY_INI_DEFAULT] = hoje - datetime.timedelta(days=7)
        else:
            st.session_state[_KEY_INI_DEFAULT] = hoje - datetime.timedelta(days=7)

    # ── Filtros ────────────────────────────────────────────────────────────────
    col_de, col_ate, col_alerta = st.columns([2, 2, 2])
    data_ini = col_de.date_input(
        "📅 De:",
        value=st.session_state[_KEY_INI_DEFAULT],
        format="DD/MM/YYYY",
        key="admin_data_ini",
    )
    # Persiste o valor escolhido pelo operador para não voltar ao default ao recarregar
    st.session_state[_KEY_INI_DEFAULT] = data_ini
    data_fim = col_ate.date_input(
        "📅 Até:",
        value=hoje,
        format="DD/MM/YYYY",
        key="admin_data_fim",
    )
    limite_baixa = col_alerta.number_input(
        "⚠️ Alerta: presenças ≤",
        min_value=1, max_value=200, step=5, value=10,
        key="admin_limite_baixa_freq",
        help="Linhas com presenças abaixo desse valor são destacadas em amarelo",
    )

    # ── Botão de recálculo em lote ─────────────────────────────────────────────
    _KEY_FRESCOS = "admin_presencas_frescas"
    _KEY_FRESCOS_PERIODO = "admin_presencas_frescas_periodo"

    col_btn, col_status = st.columns([2, 6])
    if col_btn.button(
        "🔄 Recalcular Presenças",
        key="admin_btn_recalcular",
        use_container_width=True,
        help="Consulta o banco diretamente (ignora cache) e atualiza a coluna Presenças",
    ):
        with st.spinner(f"Consultando banco para {data_ini.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}..."):
            frescos = contar_presencas_periodo_direto(data_ini, data_fim)
        if "_erro" in frescos:
            col_status.error(f"❌ Erro na consulta: {frescos['_erro']}")
        else:
            st.session_state[_KEY_FRESCOS] = frescos
            st.session_state[_KEY_FRESCOS_PERIODO] = (str(data_ini), str(data_fim))
            # Invalida o cache para que próxima carga já traga dados corretos
            try:
                listar_datas_aulas_registradas.clear()
            except Exception:
                pass
            n_dias = len(frescos)
            total_pres = sum(frescos.values())
            col_status.success(
                f"✅ Recálculo concluído — {n_dias} dia(s) com PRESENTE no período · "
                f"{total_pres} presenças totais"
            )

    # Exibe nota quando há contagens frescas disponíveis para o período atual
    frescos_periodo = st.session_state.get(_KEY_FRESCOS_PERIODO)
    frescos_dict    = st.session_state.get(_KEY_FRESCOS, {})
    usando_frescos  = (
        frescos_periodo == (str(data_ini), str(data_fim))
        and bool(frescos_dict)
    )
    if usando_frescos:
        st.caption("🟢 Presenças exibidas com dados **frescos do banco** (recálculo manual).")

    if df_datas.empty and not frescos_dict:
        st.info("Nenhum dia de aula registrado no banco de dados.")
    else:
        df_display = df_datas.copy() if not df_datas.empty else pd.DataFrame(
            columns=["data_aula", "total_presencas", "turmas_diario"]
        )

        # Se temos contagens frescas para este período, injeta no DataFrame
        if usando_frescos:
            # Garante que todas as datas do período com PRESENTE aparecem
            datas_frescas = set(frescos_dict.keys())
            datas_df = set(df_display["data_aula"].astype(str).str[:10].tolist()) if not df_display.empty else set()
            faltando = datas_frescas - datas_df
            for d_falt in faltando:
                df_display = pd.concat([
                    df_display,
                    pd.DataFrame([{"data_aula": d_falt, "total_presencas": frescos_dict[d_falt], "turmas_diario": []}])
                ], ignore_index=True)

            # Sobrescreve total_presencas com os valores frescos
            df_display["data_aula_str"] = df_display["data_aula"].astype(str).str[:10]
            df_display["total_presencas"] = df_display["data_aula_str"].map(
                lambda d: frescos_dict.get(d, df_display.loc[df_display["data_aula_str"] == d, "total_presencas"].iloc[0]
                          if (df_display["data_aula_str"] == d).any() else 0)
            )

        dts_parsed = pd.to_datetime(df_display["data_aula"])
        df_display["data_date"]  = dts_parsed.dt.date
        df_display["data_fmt"]   = dts_parsed.dt.strftime("%d/%m/%Y")
        df_display["dia_semana"] = dts_parsed.dt.day_name().map(_DIAS_PT)
        df_display["turmas"]     = df_display["turmas_diario"].apply(
            lambda t: ", ".join(t) if isinstance(t, list) and t else "—"
        )
        anos_dados = set(dts_parsed.dt.year.dropna().astype(int).tolist())
        feriados   = _feriados_sp(anos_dados)
        df_display["anomalia"] = dts_parsed.apply(
            lambda dt: _classificar_anomalia(dt.date(), feriados) if pd.notna(dt) else ""
        )

        # Aplica filtro de período
        df_filtrado = df_display[
            (df_display["data_date"] >= data_ini) &
            (df_display["data_date"] <= data_fim)
        ].sort_values("data_aula", ascending=False)

        # Garante coluna motivo_sem_aula mesmo em cache antigo
        if "motivo_sem_aula" not in df_filtrado.columns:
            df_filtrado = df_filtrado.copy()
            df_filtrado["motivo_sem_aula"] = ""

        n_total = len(df_filtrado)
        # Dias com evento calendário não contam como "baixa frequência"
        mask_evento = df_filtrado["motivo_sem_aula"].fillna("") != ""
        n_baixa = (
            (df_filtrado["total_presencas"] <= int(limite_baixa)) & ~mask_evento
        ).sum()

        partes_info = [f"**{n_total}** dia(s) no período"]
        if n_baixa:
            partes_info.append(f"**{n_baixa}** com ≤ {int(limite_baixa)} presenças ⚠️")
        n_eventos = mask_evento.sum()
        if n_eventos:
            partes_info.append(f"**{n_eventos}** evento(s) de calendário 📅")
        st.caption(" · ".join(partes_info))

        anomalos = df_filtrado[df_filtrado["anomalia"] != ""]
        if not anomalos.empty:
            n_fds = anomalos["anomalia"].str.contains("Fim de semana", na=False).sum()
            n_fer = anomalos["anomalia"].str.contains("Feriado", na=False).sum()
            partes = []
            if n_fds: partes.append(f"**{n_fds}** fim(ns) de semana")
            if n_fer: partes.append(f"**{n_fer}** feriado(s)")
            st.warning(f"⚠️ {' e '.join(partes)} com registros de aula no período — verifique.")

        if df_filtrado.empty:
            st.info("Nenhum registro no período selecionado.")
        else:
            cab_a, cab_b, cab_c, cab_d, cab_e = st.columns([2, 2, 1, 4, 2])
            for col, txt in zip(
                [cab_a, cab_b, cab_c, cab_d, cab_e],
                ["Data", "Dia da Semana", "Presenças", "Turmas (Diário)", ""],
            ):
                col.markdown(f"<small><b>{txt}</b></small>", unsafe_allow_html=True)

            for _, row in df_filtrado.iterrows():
                n_pres   = int(row["total_presencas"])
                motivo   = str(row.get("motivo_sem_aula", "") or "")
                evento   = bool(motivo)          # True → dia de evento/sem aula
                # Baixa frequência real = zerado SEM motivo de calendário
                baixa    = (n_pres <= int(limite_baixa)) and not evento

                if evento:
                    cor_data = "#1E3A5F"          # azul escuro neutro
                elif baixa:
                    cor_data = "#D97706"          # âmbar
                else:
                    cor_data = "#1E40AF"          # azul normal

                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 4, 2])
                c1.markdown(
                    f"<span style='color:{cor_data};font-weight:700;'>{row['data_fmt']}"
                    f"{'  ⚠️' if row['anomalia'] else ''}</span>",
                    unsafe_allow_html=True,
                )
                c2.markdown(
                    f"<small style='color:#6B7280;'>{row['dia_semana']}</small>",
                    unsafe_allow_html=True,
                )

                if evento:
                    # Badge verde-azulado com nome do evento
                    c3.markdown(
                        f"<span style='background:#DBEAFE;color:#1E40AF;"
                        f"font-size:11px;padding:2px 7px;border-radius:4px;"
                        f"white-space:nowrap;'>📅 {motivo}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    cor_pres = "#92400E" if baixa else "#166534"
                    bg_pres  = "#FEF3C7" if baixa else "transparent"
                    c3.markdown(
                        f"<span style='background:{bg_pres};color:{cor_pres};"
                        f"font-weight:700;font-size:13px;padding:2px 6px;"
                        f"border-radius:4px;'>{n_pres}</span>",
                        unsafe_allow_html=True,
                    )

                c4.markdown(
                    f"<small style='color:#374151;'>{row['turmas']}</small>",
                    unsafe_allow_html=True,
                )
                try:
                    d_obj = datetime.date.fromisoformat(str(row["data_aula"])[:10])
                    if c5.button(
                        "→ Ver chamada",
                        key=f"admin_ver_freq_{row['data_aula']}",
                        help=f"Abrir frequência de {row['data_fmt']} ({n_pres} presenças)",
                        use_container_width=True,
                    ):
                        st.session_state["_freq_data_alvo"] = d_obj
                        st.session_state["_freq_ir_tablet"] = True
                        st.session_state.menu_atual = "Frequência"
                        st.rerun()
                except Exception:
                    pass

    st.markdown("---")

    # ── 3. Ferramentas de configuração (expanders) ────────────────────────────
    _renderizar_bloco_fonetica()
    _renderizar_bloco_validade_anamnese()

    st.markdown("---")

    # ── 4. Painel de exclusão permanente (zona de perigo) ─────────────────────
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

    if df_datas.empty:
        return

    df_display_del = df_datas.copy()
    dts_del = pd.to_datetime(df_display_del["data_aula"])
    df_display_del["data_fmt"]   = dts_del.dt.strftime("%d/%m/%Y")
    df_display_del["dia_semana"] = dts_del.dt.day_name().map(_DIAS_PT)
    df_display_del["turmas"]     = df_display_del["turmas_diario"].apply(
        lambda t: ", ".join(t) if isinstance(t, list) and t else "—"
    )
    anos_del  = set(dts_del.dt.year.dropna().astype(int).tolist())
    fer_del   = _feriados_sp(anos_del)
    df_display_del["anomalia"] = dts_del.apply(
        lambda dt: _classificar_anomalia(dt.date(), fer_del) if pd.notna(dt) else ""
    )

    st.markdown("### 🗑️ Selecionar Data para Excluir")
    opcoes_datas = df_display_del["data_aula"].tolist()
    opcoes_label = {
        row["data_aula"]: (
            f"{row['data_fmt']} — {row['dia_semana']}"
            f"  ({row['total_presencas']} presenças)"
            f"{' ⚠️' if row['anomalia'] else ''}"
        )
        for _, row in df_display_del.iterrows()
    }

    data_sel_str = st.selectbox(
        "📅 Escolha a data a excluir:",
        options=opcoes_datas,
        format_func=lambda d: opcoes_label.get(d, d),
        key="admin_data_excluir",
    )

    if data_sel_str:
        row_sel  = df_display_del[df_display_del["data_aula"] == data_sel_str].iloc[0]
        n_pres   = int(row_sel["total_presencas"])
        dia_nome = row_sel["dia_semana"]
        turmas_d = row_sel["turmas"]
        data_fmt = row_sel["data_fmt"]
        is_wknd  = row_sel["anomalia"] != ""

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

        st.markdown(
            f"Para confirmar, **digite a data exatamente** como aparece: `{data_fmt}`"
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
                    for fn in (bi_presencas_periodo, bi_frequencia_turmas,
                               bi_resumo_studio, listar_datas_aulas_registradas):
                        try:
                            fn.clear()
                        except Exception:
                            pass
                    st.session_state["bi_cache_dirty"] = True
                    if "admin_confirma_data" in st.session_state:
                        del st.session_state["admin_confirma_data"]
                    st.rerun()
                else:
                    st.error(f"❌ Erro: {msg}")
