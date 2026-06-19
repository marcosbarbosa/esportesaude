# ==============================================================================
# 📄 ARQUIVO: views/lancamento_pa_lote_view.py
# 🏷️ VERSÃO: 1.0 — Lançamento Digital de PA em Lote
# ⚙️ FUNÇÃO: Grade de lançamento rápido de pressão arterial para toda uma turma,
#            com classificação AHA em tempo real e salvamento no Supabase.
# ==============================================================================
import streamlit as st
import datetime
import uuid

from database import (
    get_alunos_por_turma,
    get_todas_turmas,
    salvar_registro_pa,
    get_registros_pa_turma,
    deletar_registros_pa_lote,
    _tabela_pa_existe,
    SQL_CRIAR_REGISTROS_PA,
    SQL_CORRIGIR_RLS_PA,
)


# ── Classificação AHA ────────────────────────────────────────────────────────
_CLS = {
    "crise":    ("💥 Crise Hipertensiva", "#7F0000", "#FFEBEE"),
    "estagio2": ("🔴 Estágio 2",          "#B71C1C", "#FFEBEE"),
    "estagio1": ("🟠 Estágio 1",          "#E64A19", "#FFF3E0"),
    "elevada":  ("🟡 Elevada",            "#F57F17", "#FFFDE7"),
    "normal":   ("🔵 Normal",             "#1565C0", "#E3F2FD"),
}


def _classificar(s, d):
    if not s or not d or s <= 0 or d <= 0:
        return None
    s, d = int(s), int(d)
    if s > 180 or d > 120:  return "crise"
    if s >= 140 or d >= 90: return "estagio2"
    if s >= 130 or d >= 80: return "estagio1"
    if 120 <= s <= 129 and d < 80: return "elevada"
    if s < 120 and d < 80:  return "normal"
    if d >= 90: return "estagio2"
    return "normal"


def _badge(chave):
    if not chave:
        return "<span style='color:#94A3B8;font-size:12px;'>—</span>"
    lbl, cor, bg = _CLS[chave]
    return (f"<span style='background:{bg};color:{cor};padding:2px 8px;"
            f"border-radius:4px;font-size:11px;font-weight:800;white-space:nowrap;'>"
            f"{lbl}</span>")


# ── CSS ──────────────────────────────────────────────────────────────────────
_CSS = """
<style>
.lpa-header {
    background: linear-gradient(135deg,#EFF6FF,#DBEAFE);
    padding: 18px 22px; border-radius: 12px;
    border-left: 6px solid #1D4ED8; margin-bottom: 16px;
}
.lpa-header h3 { margin: 0 0 4px; color: #1e3a8a; font-size: 1.2rem; }
.lpa-header p  { margin: 0; color: #475569; font-size: 13px; }
.lpa-col-hdr {
    font-size: 11px; font-weight: 800; color: #64748B;
    text-transform: uppercase; padding: 4px 2px;
}
.lpa-nome {
    padding: 10px 4px; font-size: 14px;
    font-weight: 600; color: #0F172A; line-height: 1.2;
}
.lpa-alerta {
    background: #FEF2F2; border-left: 4px solid #EF4444;
    padding: 8px 12px; border-radius: 6px; margin: 3px 0;
}
.lpa-hist-row {
    border: 1px solid #E2E8F0;
    border-radius: 8px; padding: 8px 14px; margin: 4px 0;
    display: flex; justify-content: space-between; align-items: center;
}

/* ── GRADE — linhas alternadas (tema claro) ──────────────────────────────── */
[data-testid="stForm"] [data-testid="stHorizontalBlock"]:nth-child(odd) {
    background: rgba(219,234,254,0.38) !important;
    border-radius: 6px !important;
}
[data-testid="stForm"] [data-testid="stHorizontalBlock"]:nth-child(even) {
    background: rgba(248,250,252,0.70) !important;
    border-radius: 6px !important;
}

/* ── GRADE — linhas alternadas (tema escuro) ─────────────────────────────── */
[data-testid="stApp"][data-theme="dark"]
[data-testid="stForm"] [data-testid="stHorizontalBlock"]:nth-child(odd) {
    background: rgba(99,132,199,0.15) !important;
    border-radius: 6px !important;
}
[data-testid="stApp"][data-theme="dark"]
[data-testid="stForm"] [data-testid="stHorizontalBlock"]:nth-child(even) {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 6px !important;
}
</style>
"""


# ── Tela Principal ───────────────────────────────────────────────────────────
def tela_lancamento_pa_digital():
    """Módulo de lançamento digital de pressão arterial em lote por turma."""
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class='lpa-header'>
      <h3>📲 Lançamento Digital — PA em Lote</h3>
      <p>Selecione a turma, preencha os valores aferidos e salve tudo de uma vez.
         Cada registro fica vinculado ao histórico individual do aluno.</p>
    </div>""", unsafe_allow_html=True)

    # ── Verificar tabela ──────────────────────────────────────────────────────
    if not _tabela_pa_existe():
        st.error("⚠️ A tabela `registros_pa` ainda não existe no banco de dados.")
        with st.expander("🛠️ SQL para criar a tabela — copie e execute no Supabase SQL Editor",
                         expanded=True):
            st.code(SQL_CRIAR_REGISTROS_PA, language="sql")
        st.info("Após executar o SQL acima, recarregue a página para habilitar o lançamento digital.")
        return

    # ── Configuração da sessão ─────────────────────────────────────────────────
    turmas_df    = get_todas_turmas(ativas_apenas=True)
    turmas_lista = sorted(turmas_df["nome"].tolist()) if not turmas_df.empty else []

    if not turmas_lista:
        st.warning("Nenhuma turma ativa cadastrada no sistema.")
        return

    with st.container(border=True):
        st.markdown("#### ⚙️ Configurar Sessão de Coleta")
        c1, c2, c3, c4 = st.columns([2.5, 1.5, 2.5, 1.5])
        turma_sel  = c1.selectbox("👥 Turma", turmas_lista, key="lpa_turma")
        data_sel   = c2.date_input("📅 Data", datetime.date.today(),
                                   format="DD/MM/YYYY", key="lpa_data")
        professor  = c3.text_input("👤 Professor", key="lpa_prof",
                                   placeholder="Nome do professor responsável…")
        momentos   = ["Antes da aula", "Depois da aula", "Em repouso", "Outro"]
        momento    = c4.selectbox("⏱️ Momento", momentos, key="lpa_momento")

        btn_carregar = st.button("🔍 Carregar Turma", type="primary",
                                 key="lpa_btn_carregar")

    # ── Carregar alunos ───────────────────────────────────────────────────────
    if btn_carregar:
        alunos_raw = get_alunos_por_turma(turma_sel)
        # get_alunos_por_turma pode retornar lista ou DataFrame
        try:
            import pandas as pd
            if not isinstance(alunos_raw, list):
                alunos_raw = alunos_raw.to_dict("records") if not alunos_raw.empty else []
        except Exception:
            pass
        ativos = [a for a in alunos_raw if a.get("status", "Ativo") != "Inativo"]
        ativos.sort(key=lambda x: x.get("nome", "").lower())
        st.session_state["lpa_alunos"]     = ativos
        st.session_state["lpa_carregado"]  = True
        st.session_state["lpa_cfg"]        = {
            "turma": turma_sel, "data": str(data_sel),
            "professor": professor, "momento": momento,
        }

    if not st.session_state.get("lpa_carregado"):
        st.info("👆 Selecione a turma e clique em **Carregar Turma** para iniciar o lançamento.")
        return

    alunos = st.session_state.get("lpa_alunos", [])
    cfg    = st.session_state.get("lpa_cfg", {})

    if not alunos:
        st.warning(f"Nenhum aluno ativo em **{cfg.get('turma', turma_sel)}**.")
        st.session_state["lpa_carregado"] = False
        return

    st.success(f"✅ **{len(alunos)}** aluno(s) carregado(s) — "
               f"**{cfg.get('turma')}** · {cfg.get('data')} · {cfg.get('momento')}")

    # ── Grade de lançamento ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Grade de Lançamento")
    st.caption("Preencha sistólica e diastólica. Alunos com valor 0 serão ignorados.")

    hdrs = st.columns([3.5, 1.2, 1.2, 1.2, 2])
    for col, lbl in zip(hdrs, ["Aluno", "Sistólica", "Diastólica", "Pulso (bpm)", "Classificação"]):
        col.markdown(f"<span class='lpa-col-hdr'>{lbl}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0 6px;border-color:#E2E8F0;'>", unsafe_allow_html=True)

    with st.form("lpa_form"):
        entradas = {}
        for al in alunos:
            aid  = str(al.get("id", ""))
            nome = al.get("nome", "Aluno")
            row  = st.columns([3.5, 1.2, 1.2, 1.2, 2])
            row[0].markdown(f"<div class='lpa-nome'>{nome}</div>", unsafe_allow_html=True)
            sis = row[1].number_input("Sis", min_value=0, max_value=300, step=1,
                                       value=0, key=f"lpa_s_{aid}",
                                       label_visibility="collapsed")
            dia = row[2].number_input("Dia", min_value=0, max_value=200, step=1,
                                       value=0, key=f"lpa_d_{aid}",
                                       label_visibility="collapsed")
            pul = row[3].number_input("Pul", min_value=0, max_value=300, step=1,
                                       value=0, key=f"lpa_p_{aid}",
                                       label_visibility="collapsed")
            cls_k = _classificar(sis, dia)
            row[4].markdown(_badge(cls_k), unsafe_allow_html=True)
            entradas[aid] = {"nome": nome, "sis": sis, "dia": dia, "pul": pul}

        st.markdown("<br>", unsafe_allow_html=True)
        btn_salvar = st.form_submit_button(
            "💾 Salvar Registros Preenchidos",
            type="primary",
            use_container_width=True,
        )

    # ── Processar salvamento ───────────────────────────────────────────────────
    if btn_salvar:
        salvos, alertas, erros_salvo = [], [], []
        registrado_por = st.session_state.get("usuario_email", "sistema")

        for aid, vals in entradas.items():
            sis, dia, pul = vals["sis"], vals["dia"], vals["pul"]
            if sis <= 0 or dia <= 0:
                continue
            cls_k = _classificar(sis, dia)
            payload = {
                "id":              str(uuid.uuid4()),
                "aluno_id":        aid,
                "data":            cfg.get("data"),
                "hora":            datetime.datetime.now().strftime("%H:%M"),
                "sistolica":       sis,
                "diastolica":      dia,
                "pulso":           pul if pul > 0 else None,
                "momento":         cfg.get("momento", "Antes da aula"),
                "turma":           cfg.get("turma"),
                "professor":       cfg.get("professor") or None,
                "registrado_por":  registrado_por,
                "sintomas":        ["Sem sintomas"],
                "braco":           "Esquerdo",
                "posicao":         "Sentado",
                "repeticao":       "1ª aferição",
                "classificacao":   cls_k,
            }
            ok, msg = salvar_registro_pa(payload)
            if ok:
                salvos.append(vals["nome"])
                if cls_k in ("estagio2", "crise"):
                    alertas.append((vals["nome"], sis, dia, cls_k))
            else:
                erros_salvo.append(f"{vals['nome']}: {msg}")

        if salvos:
            st.success(f"✅ **{len(salvos)}** registro(s) salvos com sucesso!")

        if alertas:
            st.markdown("---")
            st.warning("⚠️ **Atenção — valores elevados registrados:**")
            for nome, s, d, c in alertas:
                lbl, cor, bg = _CLS[c]
                st.markdown(
                    f"<div class='lpa-alerta'>"
                    f"<strong style='color:#0F172A;'>{nome}</strong>"
                    f" — <span style='font-size:15px;font-weight:700;'>{s}/{d} mmHg</span>"
                    f" &nbsp; <span style='color:{cor};font-weight:800;'>{lbl}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        rls_detectado = any("row-level security" in e.lower() or "42501" in e for e in erros_salvo)
        for err in erros_salvo:
            st.error(f"Erro: {err}")

        if rls_detectado:
            st.warning(
                "🔒 **Bloqueio de segurança (RLS) detectado na tabela `registros_pa`.**\n\n"
                "Isso acontece quando a tabela foi criada sem desabilitar o Row-Level Security. "
                "Execute o SQL abaixo no **Supabase → SQL Editor** e tente salvar novamente:"
            )
            with st.expander("🛠️ SQL de correção — copie e execute no Supabase", expanded=True):
                st.code(SQL_CORRIGIR_RLS_PA, language="sql")

        if not salvos and not erros_salvo:
            st.info("Nenhum valor preenchido. "
                    "Insira sistólica e diastólica (acima de 0) para salvar.")

    # ── Histórico desta turma/data ─────────────────────────────────────────────
    st.markdown("---")
    _mostrar_historico_turma(cfg.get("turma"), cfg.get("data"))


def _limpar_checkboxes_pa():
    """Remove todos os estados de checkbox de PA do session_state."""
    for k in list(st.session_state.keys()):
        if k.startswith("lpa_chk_"):
            del st.session_state[k]
    st.session_state["lpa_confirmar_lote"] = False


def _mostrar_historico_turma(turma, data):
    """Exibe registros de PA desta sessão com seleção em lote e exclusão em lote."""
    if not turma or not data:
        return

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    col_tit, col_ref = st.columns([5, 1])
    col_tit.markdown("#### 📊 Registros Desta Sessão")
    if col_ref.button("🔄", key="lpa_refresh_hist", help="Atualizar histórico"):
        _limpar_checkboxes_pa()
        st.rerun()

    registros = get_registros_pa_turma(turma, data)

    # Mapa aluno_id → nome (via cache de alunos da turma, sem query extra)
    try:
        _df_al = get_alunos_por_turma(turma)
        _nomes = dict(zip(_df_al["id"].astype(str), _df_al["nome"])) if not _df_al.empty else {}
    except Exception:
        _nomes = {}

    if not registros:
        _limpar_checkboxes_pa()
        st.info("Nenhum registro lançado para esta turma e data ainda.")
        return

    total     = len(registros)
    todos_ids = [str(r.get("id", "")) for r in registros]

    if "lpa_confirmar_lote" not in st.session_state:
        st.session_state["lpa_confirmar_lote"] = False

    # ── Botões de seleção rápida ───────────────────────────────────────────────
    st.markdown("<hr style='margin:4px 0 8px;border-color:#E2E8F0;'>", unsafe_allow_html=True)
    b_l, _, b_r = st.columns([2, 7, 2])
    if b_l.button("☑ Todos", key="lpa_sel_todos", use_container_width=True):
        for rid in todos_ids:
            st.session_state[f"lpa_chk_{rid}"] = True
        st.session_state["lpa_confirmar_lote"] = False
        st.rerun()
    if b_r.button("☐ Nenhum", key="lpa_sel_nenhum", use_container_width=True):
        for rid in todos_ids:
            st.session_state[f"lpa_chk_{rid}"] = False
        st.session_state["lpa_confirmar_lote"] = False
        st.rerun()

    st.markdown("<hr style='margin:6px 0 8px;border-color:#E2E8F0;'>", unsafe_allow_html=True)

    # ── Lista de registros com checkbox ───────────────────────────────────────
    # IMPORTANTE: os checkboxes são renderizados ANTES de calcular sel/n_sel.
    # Assim, quando o usuário clica num checkbox, o st.session_state[key]
    # é atualizado pelo Streamlit antes de continuar a execução — e a barra
    # de ação abaixo lê os valores corretos no mesmo run.
    for r in registros:
        rid   = str(r.get("id", ""))
        nome  = _nomes.get(str(r.get("aluno_id", ""))) or "Aluno"
        sis   = r.get("sistolica", 0)
        dia   = r.get("diastolica", 0)
        pul   = r.get("pulso")
        cls_k = r.get("classificacao") or _classificar(sis, dia)
        hora  = r.get("hora", "")
        lbl, cor, bg = _CLS.get(cls_k, ("—", "#64748B", "#F8FAFC"))
        pul_txt = f" · Pulso: <strong>{pul}</strong> bpm" if pul else ""

        # Checkbox sem value= : Streamlit gerencia o estado pelo key
        is_sel = st.session_state.get(f"lpa_chk_{rid}", False)
        borda  = "3px solid #1D4ED8" if is_sel else f"4px solid {cor}"
        bg_row = "#DBEAFE" if is_sel else bg

        c_chk, c_info = st.columns([0.5, 11])
        c_chk.checkbox("sel", key=f"lpa_chk_{rid}", label_visibility="collapsed")
        c_info.markdown(
            f"<div class='lpa-hist-row' style='border-left:{borda};"
            f"background:{bg_row};margin:0;'>"
            f"<span style='font-weight:700;color:#0F172A;min-width:180px;"
            f"display:inline-block;'>{nome}</span>"
            f"<span style='color:#475569;font-size:13px;'>"
            f"<strong>{sis}/{dia}</strong> mmHg{pul_txt}"
            f"{'&nbsp;·&nbsp;'+hora if hora else ''}</span>"
            f"&nbsp;&nbsp;<span style='color:{cor};font-weight:800;"
            f"font-size:12px;white-space:nowrap;'>{lbl}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Barra de ação — calculada DEPOIS dos checkboxes ───────────────────────
    # Os st.checkbox() acima já atualizaram session_state neste run,
    # então sel reflete exatamente o que o usuário marcou.
    sel   = {rid for rid in todos_ids if st.session_state.get(f"lpa_chk_{rid}", False)}
    n_sel = len(sel)

    st.markdown("<hr style='margin:10px 0 6px;border-color:#E2E8F0;'>", unsafe_allow_html=True)
    act_l, act_m, act_r = st.columns([4, 2, 3])

    legenda = f"**{total}** registro(s) · **{turma}** · {data}"
    if n_sel:
        legenda += f" &nbsp;·&nbsp; ✔ **{n_sel} selecionado(s)**"
    act_l.markdown(f"<small>{legenda}</small>", unsafe_allow_html=True)

    if n_sel > 0 and not st.session_state.get("lpa_confirmar_lote"):
        if act_r.button(
            f"🗑️ Excluir {n_sel} selecionado(s)",
            type="secondary",
            use_container_width=True,
            key="lpa_btn_del_lote",
        ):
            st.session_state["lpa_confirmar_lote"] = True
            st.rerun()

    # ── Confirmação de exclusão ────────────────────────────────────────────────
    if st.session_state.get("lpa_confirmar_lote"):
        # Recalcula sel no momento da confirmação (pode ter mudado)
        sel_conf = {rid for rid in todos_ids
                    if st.session_state.get(f"lpa_chk_{rid}", False)}
        n_conf = len(sel_conf)
        if n_conf > 0:
            st.warning(
                f"⚠️ Excluir permanentemente **{n_conf}** registro(s)? "
                "Esta ação não pode ser desfeita.",
                icon="🚨",
            )
            c_ok, c_no = st.columns(2)
            if c_ok.button("✅ Confirmar exclusão", type="primary",
                           use_container_width=True, key="lpa_lote_ok"):
                ids_del = list(sel_conf)
                qtd, erros = deletar_registros_pa_lote(ids_del)
                for rid in ids_del:
                    st.session_state.pop(f"lpa_chk_{rid}", None)
                st.session_state["lpa_confirmar_lote"] = False
                if erros:
                    st.error(f"Erro: {erros[0]}")
                else:
                    st.success(f"✅ {qtd} registro(s) excluído(s) com sucesso.")
                st.rerun()
            if c_no.button("❌ Cancelar", use_container_width=True, key="lpa_lote_nao"):
                st.session_state["lpa_confirmar_lote"] = False
                st.rerun()
        else:
            st.session_state["lpa_confirmar_lote"] = False
