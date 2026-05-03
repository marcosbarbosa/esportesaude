import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px # Usado para os gráficos de pizza/donut
from database import (
    get_alunos_por_turma, get_relatorio_periodo, 
    get_presencas_dia, buscar_alunos_geral, atualizar_turma_aluno, 
    cadastrar_novo_aluno, excluir_aluno, upload_midia, salvar_diario, 
    get_diario_dia, atualizar_data_nascimento, atualizar_aluno_completo,
    alternar_presenca, get_midias_diario, excluir_midia_diario, atualizar_legenda_midia,
    salvar_avaliacao_prontuario, get_avaliacoes_aluno, atualizar_perfil_aluno,
    excluir_avaliacao_prontuario
)

# --- FUNÇÕES DE APOIO ---
def is_data_valida(data_nasc_str, ano_atual):
    try:
        if pd.isna(data_nasc_str) or not data_nasc_str: return False
        data_limpa = str(data_nasc_str).strip()
        if data_limpa.lower() in ['nan', 'none', 'nat', '']: return False
        ano = int(data_limpa.split('-')[0])
        return 1920 <= ano <= ano_atual
    except: return False

def obter_badge_aniversario(data_nasc_str, data_referencia):
    try:
        if not is_data_valida(data_nasc_str, data_referencia.year): return "", None
        niver = datetime.datetime.strptime(str(data_nasc_str).strip(), "%Y-%m-%d").date()
        niver_este_ano = datetime.date(data_referencia.year, niver.month, niver.day)
        if niver_este_ano == data_referencia: return " 🔴", "🎉 HOJE!"
        if niver_este_ano.isocalendar()[1] == data_referencia.isocalendar()[1]: return " 🟡", "Semana"
        return "", None
    except: return "", None

# --- LÓGICA DE INDICADORES DE SAÚDE ---
def analisar_saude_visual(aval):
    """Gera a análise visual baseada em protocolos de saúde"""

    # 1. DOR (Escala de Carinhas / Borg Adaptada)
    dor = aval.get('dor_nivel', 0)
    if dor <= 2: carinha, cor_dor, txt_dor = "😃", "green", "Confortável"
    elif dor <= 5: carinha, cor_dor, txt_dor = "😐", "orange", "Moderada"
    else: carinha, cor_dor, txt_dor = "😟", "red", "Intensa"

    # 2. EQUILÍBRIO (Protocolo TUG: <10s Independente, >20s Risco Queda)
    tug = aval.get('tug_simples', 0)
    if tug < 10: cor_tug, status_tug = "green", "Equilíbrio Excelente"
    elif tug <= 20: cor_tug, status_tug = "orange", "Atenção: Equilíbrio Médio"
    else: cor_tug, status_tug = "red", "Risco de Queda Elevado"

    # 3. FORÇA (Gráfico de Pizza/Donut - Baseado em meta de 15 reps)
    f_dir = aval.get('forca_dir', 0)
    f_esq = aval.get('forca_esq', 0)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"**Nível de Dor**")
        st.markdown(f"<h1 style='text-align: center; color: {cor_dor};'>{carinha}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>{txt_dor} (Nível {dor})</p>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"**Equilíbrio (TUG)**")
        st.markdown(f"<h2 style='text-align: center; color: {cor_tug};'>{tug}s</h2>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align: center;'>{status_tug}</p>", unsafe_allow_html=True)

    with col3:
        st.markdown(f"**Mobilidade**")
        mob = aval.get('mobilidade_pes_dir', 'Não testado')
        icon_mob = "✅" if "Passa" in mob or "Toca" in mob else "⚠️"
        st.markdown(f"<h2 style='text-align: center;'>{icon_mob}</h2>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align: center;'>{mob}</p>", unsafe_allow_html=True)

    # Gráfico de Pizza para Força (Comparativo Lados)
    st.markdown("---")
    if f_dir > 0 or f_esq > 0:
        fig_forca = px.pie(
            values=[f_dir, f_esq], 
            names=['Braço Direito', 'Braço Esquerdo'],
            title='Simetria de Força (Repetições)',
            hole=0.4,
            color_discrete_sequence=['#1E88E5', '#EF5350']
        )
        fig_forca.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_forca, use_container_width=True)

# ==============================================================================
# MÓDULO 1: PAINEL DE FREQUÊNCIA
# ==============================================================================
def tela_frequencia():
    if st.button("⬅️ Voltar ao Menu"):
        st.session_state.menu_atual = "Principal"; st.rerun()

    st.title("📋 Painel de Gestão da Aula")

    if not st.session_state.get("admin_logado", False):
        with st.form("form_login_admin"):
            senha = st.text_input("Senha Mestra:", type="password")
            if st.form_submit_button("Entrar"): # CORREÇÃO LOGIN
                if senha == "123": st.session_state.admin_logado = True; st.rerun()
                else: st.error("Senha incorreta!")
        return

    st.divider()
    c1, c2 = st.columns(2)
    data_aula = c1.date_input("Data:", datetime.date.today(), format="DD/MM/YYYY")
    turma_sel = c2.selectbox("Turma:", ["Turma 1 (08:00)", "Turma 2 (09:00)"])

    tab_f, tab_d, tab_ds, tab_al = st.tabs(["👥 Frequência", "📝 Diário", "🖨️ Dossiê", "🔍 Alunos"])

    with tab_f:
        df = get_alunos_por_turma(turma_sel)
        if not df.empty:
            pres = get_presencas_dia(data_aula, df['id'].tolist())
            st.info("🎂 **Nivers:** 🔴 Hoje | 🟡 Semana")
            st.markdown("<style>div[data-testid='stHorizontalBlock'] { margin-bottom: -25px !important; align-items: center; }</style>", unsafe_allow_html=True)
            for i in range(0, len(df), 3):
                cols = st.columns(3)
                for j, (_, row) in enumerate(df.iloc[i:i+3].iterrows()):
                    with cols[j]:
                        is_p = pres.get(row['id'], False)
                        badge, _ = obter_badge_aniversario(row.get('data_nascimento'), data_aula)
                        with st.container():
                            ci, cb, ce = st.columns([1.8, 5.7, 1.5])
                            with ci: 
                                with st.popover("👤" if not row.get("url_foto") else "🖼️", use_container_width=True):
                                    if row.get("url_foto"): st.image(row["url_foto"], use_container_width=True)
                                    else: st.write("Sem foto.")
                            with cb:
                                st.markdown(f"""<style>#pres_{row['id']} button {{ border: 1px solid {"#dc3545" if is_p else "#dddddd"} !important; height: 38px !important; }}</style>""", unsafe_allow_html=True)
                                st.markdown(f'<div id="pres_{row["id"]}">', unsafe_allow_html=True)
                                if st.button(row['nome'][:11]+badge, key=f"f_{row['id']}", type="primary" if is_p else "secondary", use_container_width=True):
                                    alternar_presenca(row['id'], data_aula, not is_p); st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                            with ce:
                                if st.button("✏️", key=f"e_{row['id']}"):
                                    st.session_state.aluno_editar = row; st.rerun()
        else: st.warning("Sem alunos.")

# ==============================================================================
# MÓDULO 2: PRONTUÁRIO CLÍNICO (COM DASHBOARD GRÁFICO)
# ==============================================================================
def tela_prontuario():
    col_v, col_clear = st.columns([3, 1])
    with col_v:
        if st.button("⬅️ Voltar ao Menu", key="btn_p_back"):
            st.session_state.aluno_prontuario = None
            st.session_state.menu_atual = "Principal"; st.rerun()
    with col_clear:
        if st.session_state.get("aluno_prontuario") is not None:
            if st.button("🔎 Nova Busca", type="primary", use_container_width=True):
                st.session_state.aluno_prontuario = None; st.rerun()

    st.title("🩺 Prontuário Clínico")

    if st.session_state.get("aluno_prontuario") is None:
        with st.form("form_pesquisa"):
            st.markdown("🔍 **Pesquisar Aluno:**")
            col_in, col_bt = st.columns([4, 1])
            busca_termo = col_in.text_input("Nome...", label_visibility="collapsed")
            if col_bt.form_submit_button("Avançar ➡️", use_container_width=True):
                if busca_termo:
                    df_b = buscar_alunos_geral(busca_termo)
                    if not df_b.empty:
                        for _, row in df_b.iterrows():
                            with st.container(border=True):
                                c1, c2 = st.columns([4, 1])
                                c1.write(f"**{row['nome']}** ({row['turma']})")
                                if c2.button("Abrir", key=f"ab_{row['id']}", type="primary"):
                                    st.session_state.aluno_prontuario = row; st.rerun()
                    else: st.warning("Não encontrado.")

    if st.session_state.get("aluno_prontuario") is not None:
        aluno = st.session_state.aluno_prontuario
        st.divider()

        # Header com Zoom
        cp_f, cp_i = st.columns([1, 6])
        u_v = aluno.get('url_foto')
        with cp_f:
            if u_v:
                with st.popover("🖼️", use_container_width=True): st.image(u_v, use_container_width=True)
                st.markdown(f'<img src="{u_v}" style="width:85px;height:85px;border-radius:50%;object-fit:cover;border:3px solid #1E88E5;margin-top:-95px;pointer-events:none;">', unsafe_allow_html=True)
            else: st.markdown("👤")
        with cp_i: st.markdown(f"## {aluno['nome']}"); st.caption(f"Turma: {aluno['turma']}")

        t1, t2, t3 = st.tabs(["👤 1. Dados Pessoais", "📝 2. Nova Medição", "📊 3. Dashboard"])

        with t1: # DADOS PESSOAIS
            with st.container(border=True):
                st.markdown("#### 📋 Cadastro"); col_n, col_dn = st.columns([2, 1])
                n_ed = col_n.text_input("Nome:", value=aluno['nome'])
                dn_ed = col_dn.date_input("Nascimento:", value=datetime.date(2000,1,1))
                cp, ca, cw = st.columns(3)
                p_ed = cp.number_input("Peso (kg):", value=float(aluno.get('peso') or 0.0))
                a_ed = ca.number_input("Altura (m):", value=float(aluno.get('altura') or 0.0))
                w_ed = cw.text_input("WhatsApp:", value=str(aluno.get('whatsapp') or ""))
                if st.button("💾 Guardar Alterações", type="primary", use_container_width=True):
                    ok, m = atualizar_perfil_aluno(aluno['id'], n_ed, dn_ed, p_ed, a_ed, w_ed, "", u_v)
                    if ok: st.toast("Salvo! ✅"); st.rerun()

        with t2: # NOVA MEDIÇÃO
            edit_val = st.session_state.get("medicao_editar")
            with st.form("form_med"):
                st.markdown("#### 📝 " + ("Editar" if edit_val else "Nova Medição"))
                d_av = st.date_input("Data:", value=datetime.date.today())
                dor_v = st.slider("Escala de Dor (0-10):", 0, 10, 0)
                que_v = st.number_input("Quedas (6 meses):", min_value=0, value=0)
                c_md, c_me = st.columns(2)
                ops = ["Não testado", "Não alcança", "Toca nos pés", "Passa dos pés"]
                m_d = c_md.selectbox("Mob. Dir:", ops)
                m_e = c_me.selectbox("Mob. Esq:", ops)
                f_d = c_md.number_input("Rosca Dir:", value=0)
                f_e = c_me.number_input("Rosca Esq:", value=0)
                tu1 = st.number_input("TUG Simples (s):", value=0.0)
                if st.form_submit_button("💾 Salvar Medição"):
                    res_ok, res_m = salvar_avaliacao_prontuario(aluno['id'], d_av, dor_v, que_v, "", "", m_d, m_e, f_d, f_e, tu1, 0, 0, aval_id=edit_val['id'] if edit_val else None)
                    if res_ok: st.toast("Sucesso! ✅"); st.session_state.medicao_editar = None; st.rerun()

        with t3: # DASHBOARD GRÁFICO
            st.markdown("#### 📊 Histórico e Indicadores de Qualidade de Vida")
            hist = get_avaliacoes_aluno(aluno['id'])
            if hist:
                for a in hist:
                    with st.container(border=True):
                        c_info, c_edit, c_del = st.columns([3, 0.5, 0.5])
                        c_info.write(f"📅 **Medição de {a['data_avaliacao']}**")
                        if c_edit.button("✏️", key=f"ed_{a['id']}"): st.session_state.medicao_editar = a; st.rerun()
                        if c_del.button("🗑️", key=f"dl_{a['id']}"): excluir_avaliacao_prontuario(a['id']); st.rerun()

                        # NOVA ÁREA VISUAL
                        with st.expander("📊 Ver Análise Visual da Saúde"):
                            analisar_saude_visual(a)
            else: st.info("Sem histórico.")

def tela_relatorio():
    if st.button("⬅️ Voltar"): st.session_state.menu_atual = "Principal"; st.rerun()
    st.title("📊 Painel de Controle")