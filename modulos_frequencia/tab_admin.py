# ==============================================================================
# 📅 MÓDULO: tab_admin.py — Dias Regist./Anamnese + Exclusão (ADMIN MASTER)
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
    get_config_valor,
    set_config_valor,
    get_dias_sem_aula,
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


# ── Bloco: dias úteis sem frequência lançada ──────────────────────────────────
def _renderizar_bloco_sem_frequencia(df_registradas: pd.DataFrame):
    hoje = datetime.date.today()
    periodo_dias = st.session_state.get("admin_periodo_sem_freq", 90)

    col_titulo, col_periodo, col_baixa = st.columns([4, 2, 2])
    col_titulo.markdown("### ⚠️ Dias úteis sem frequência lançada")
    periodo_dias = col_periodo.number_input(
        "Período (dias retroativos):",
        min_value=7, max_value=365, step=7, value=periodo_dias,
        key="admin_periodo_sem_freq",
    )
    limite_baixa = col_baixa.number_input(
        "Alerta: presenças ≤",
        min_value=1, max_value=100, step=5, value=10,
        key="admin_limite_baixa_freq",
        help="Destaca dias registrados que tiveram poucas presenças",
    )

    ini = hoje - datetime.timedelta(days=int(periodo_dias))
    fim = hoje

    # Datas já registradas no banco — mapa data_str → total_presencas
    datas_registradas: set = set()
    mapa_presencas: dict = {}
    if not df_registradas.empty:
        for _, row in df_registradas.iterrows():
            try:
                d_parsed = pd.to_datetime(row["data_aula"]).date()
                datas_registradas.add(d_parsed)
                mapa_presencas[d_parsed] = int(row.get("total_presencas", 0))
            except Exception:
                pass

    # Dias sem aula do calendário institucional
    try:
        dias_inst = get_dias_sem_aula(str(ini), str(fim))
    except Exception:
        dias_inst = set()

    # Feriados SP/Nacional
    anos = {ini.year, fim.year}
    feriados = _feriados_sp(anos)

    # Dias úteis no período que NÃO foram registrados e NÃO são dias sem aula
    ausentes = []
    cursor = ini
    while cursor <= fim:
        if (
            cursor.weekday() < 5                   # seg–sex
            and cursor not in feriados             # não é feriado
            and cursor not in dias_inst            # não é dia sem aula cadastrado
            and cursor not in datas_registradas    # chamada não lançada
        ):
            ausentes.append(cursor)
        cursor += datetime.timedelta(days=1)

    # Dias registrados mas com frequência muito baixa
    baixa_freq = [
        d for d, n in mapa_presencas.items()
        if ini <= d <= fim
        and d.weekday() < 5
        and d not in feriados
        and d not in dias_inst
        and n <= int(limite_baixa)
    ]

    if not ausentes and not baixa_freq:
        st.success(
            f"✅ Nenhum dia útil sem frequência lançada nos últimos {int(periodo_dias)} dias. "
            "Todos os dias úteis têm chamada registrada!"
        )
        return

    # ── Dias sem nenhuma chamada ──────────────────────────────────────────────
    if ausentes:
        st.markdown(
            f"""<div style='background:#FEF2F2;border-left:4px solid #EF4444;
            padding:12px 16px;border-radius:8px;margin-bottom:12px;'>
            <strong style='color:#991B1B;'>🚫 {len(ausentes)} dia(s) útil(is) sem frequência registrada</strong><br>
            <span style='color:#7F1D1D;font-size:13px;'>
            Dias úteis (seg–sex, excluindo feriados e dias sem aula) sem nenhuma chamada no sistema.
            Clique em <b>→ Lançar chamada</b> para registrar.
            </span></div>""",
            unsafe_allow_html=True,
        )
        cab1, cab2, cab3 = st.columns([2, 3, 3])
        cab1.markdown("<small><b>Data</b></small>", unsafe_allow_html=True)
        cab2.markdown("<small><b>Dia da semana</b></small>", unsafe_allow_html=True)
        cab3.markdown("<small><b>Ação</b></small>", unsafe_allow_html=True)
        for d in sorted(ausentes, reverse=True):
            weekday_pt = _DIAS_PT.get(d.strftime("%A"), d.strftime("%A"))
            c1, c2, c3 = st.columns([2, 3, 3])
            c1.markdown(
                f"<span style='color:#DC2626;font-weight:700;'>{d.strftime('%d/%m/%Y')}</span>",
                unsafe_allow_html=True,
            )
            c2.markdown(
                f"<span style='color:#6B7280;font-size:13px;'>📌 {weekday_pt}</span>",
                unsafe_allow_html=True,
            )
            if c3.button(
                "→ Lançar chamada",
                key=f"admin_ir_freq_{d}",
                help=f"Abrir tela de frequência para {d.strftime('%d/%m/%Y')}",
                use_container_width=True,
            ):
                st.session_state["_freq_data_alvo"] = d
                st.session_state["_freq_ir_tablet"] = True
                st.session_state.menu_atual = "Frequência"
                st.rerun()

    # ── Dias com baixíssima frequência ───────────────────────────────────────
    if baixa_freq:
        st.markdown(
            f"""<div style='background:#FFFBEB;border-left:4px solid #F59E0B;
            padding:12px 16px;border-radius:8px;margin:12px 0;'>
            <strong style='color:#92400E;'>⚠️ {len(baixa_freq)} dia(s) com frequência muito baixa
            (≤ {int(limite_baixa)} presenças)</strong><br>
            <span style='color:#78350F;font-size:13px;'>
            Esses dias têm chamada registrada, mas com número de presenças abaixo do esperado.
            Clique em <b>→ Ver chamada</b> para revisar.
            </span></div>""",
            unsafe_allow_html=True,
        )
        cab1, cab2, cab3, cab4 = st.columns([2, 3, 1, 3])
        cab1.markdown("<small><b>Data</b></small>", unsafe_allow_html=True)
        cab2.markdown("<small><b>Dia da semana</b></small>", unsafe_allow_html=True)
        cab3.markdown("<small><b>Presenças</b></small>", unsafe_allow_html=True)
        cab4.markdown("<small><b>Ação</b></small>", unsafe_allow_html=True)
        for d in sorted(baixa_freq, reverse=True):
            weekday_pt = _DIAS_PT.get(d.strftime("%A"), d.strftime("%A"))
            n_pres = mapa_presencas.get(d, 0)
            c1, c2, c3, c4 = st.columns([2, 3, 1, 3])
            c1.markdown(
                f"<span style='color:#D97706;font-weight:700;'>{d.strftime('%d/%m/%Y')}</span>",
                unsafe_allow_html=True,
            )
            c2.markdown(
                f"<span style='color:#6B7280;font-size:13px;'>📌 {weekday_pt}</span>",
                unsafe_allow_html=True,
            )
            c3.markdown(
                f"<span style='color:#92400E;font-weight:700;font-size:13px;'>{n_pres}</span>",
                unsafe_allow_html=True,
            )
            if c4.button(
                "→ Ver chamada",
                key=f"admin_baixa_{d}",
                help=f"Abrir frequência de {d.strftime('%d/%m/%Y')} ({n_pres} presenças)",
                use_container_width=True,
            ):
                st.session_state["_freq_data_alvo"] = d
                st.session_state["_freq_ir_tablet"] = True
                st.session_state.menu_atual = "Frequência"
                st.rerun()

    st.markdown("---")


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

    # Carrega todas as datas registradas (usada em múltiplos blocos)
    with st.spinner("Carregando datas..."):
        df_datas = listar_datas_aulas_registradas()

    # ── 1. Dias úteis SEM frequência lançada ─────────────────────────────────
    _renderizar_bloco_sem_frequencia(df_datas)

    # ── 2. Dias de Aula Registrados ───────────────────────────────────────────
    st.markdown("### 📋 Dias de Aula Registrados")

    if df_datas.empty:
        st.info("Nenhum dia de aula registrado no banco de dados.")
    else:
        df_display = df_datas.copy()
        dts_parsed = pd.to_datetime(df_display["data_aula"])
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

        # Resumo de alertas
        idx_anomalos = df_display[df_display["anomalia"] != ""].index.tolist()
        if idx_anomalos:
            n_fds = (df_display["anomalia"].str.contains("Fim de semana", na=False)).sum()
            n_fer = (df_display["anomalia"].str.contains("Feriado", na=False)).sum()
            partes = []
            if n_fds: partes.append(f"**{n_fds}** fim(ns) de semana")
            if n_fer: partes.append(f"**{n_fer}** feriado(s)")
            st.warning(
                f"⚠️ Encontrado(s) {' e '.join(partes)} com registros de aula — "
                "verifique se foram lançamentos incorretos."
            )

        # Grade com botão de acesso rápido por linha
        cab_a, cab_b, cab_c, cab_d, cab_e, cab_f = st.columns([2, 2, 1, 3, 2, 2])
        for col, txt in zip(
            [cab_a, cab_b, cab_c, cab_d, cab_e, cab_f],
            ["Data", "Dia da Semana", "Presenças", "Turmas (Diário)", "Alerta", ""],
        ):
            col.markdown(f"<small><b>{txt}</b></small>", unsafe_allow_html=True)

        for _, row in df_display.sort_values("data_aula", ascending=False).iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1, 3, 2, 2])
            c1.markdown(f"**{row['data_fmt']}**")
            c2.markdown(f"<small>{row['dia_semana']}</small>", unsafe_allow_html=True)
            c3.markdown(f"<small>{int(row['total_presencas'])}</small>", unsafe_allow_html=True)
            c4.markdown(f"<small>{row['turmas']}</small>", unsafe_allow_html=True)
            c5.markdown(
                f"<small style='color:#D97706;'>{row['anomalia']}</small>" if row["anomalia"] else "<small>—</small>",
                unsafe_allow_html=True,
            )
            try:
                d_obj = datetime.date.fromisoformat(str(row["data_aula"]))
                if c6.button(
                    "→ Ver chamada",
                    key=f"admin_ver_freq_{row['data_aula']}",
                    help=f"Abrir frequência de {row['data_fmt']}",
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
