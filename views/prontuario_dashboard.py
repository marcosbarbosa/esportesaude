# ==============================================================================
# 📄 Arquivo: views/prontuario_dashboard.py
# 🏷️ VERSÃO: 4.4 (PRIME ELITE - UI Standardization & Cadastro Rápido Inline)
# ⚙️ FUNÇÃO: Portal do Aluno (Painel de Gestão no Topo e Action Grid na Base)
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import time
import math

try:
    from st_keyup import st_keyup
    HAS_KEYUP = True
except ImportError:
    HAS_KEYUP = False

from database import (
    buscar_alunos_geral,
    get_agendamentos_pendentes,
    concluir_ou_cancelar_agendamento,
    excluir_aluno_completo,
    get_estatisticas_frequencia_aluno,
    get_historico_aulas_aluno,
    get_avaliacoes_aluno,
    criar_agendamento,
    cadastrar_novo_aluno,
    get_todas_turmas,
    alterar_status_aluno,
    supabase,
)
from utils.texto import remover_acentos


# ==============================================================================
# 🛠️ MOTORES DE DADOS (ALTA PERFORMANCE)
# ==============================================================================


@st.cache_data(ttl=60)
def obter_todos_alunos_cache():
    return buscar_alunos_geral("")


@st.cache_data(ttl=30)
def carregar_dados_crm_avaliacoes_senior():
    """Motor de processamento em lote. Separa Ativos do Arquivo Morto."""
    try:
        # Usando .from_() para proteção do Supabase
        res_al = supabase.from_("alunos").select("*").execute()
        df_al = pd.DataFrame(res_al.data)
        if df_al.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Garante que a coluna status existe no DF
        if 'status' not in df_al.columns:
            df_al['status'] = 'Ativo'

        # SEPARAÇÃO: Arquivo Morto vs Ativos
        df_inativos = df_al[df_al['status'] == 'Inativo'].copy()
        df_ativos = df_al[df_al['status'] != 'Inativo'].copy()

        if df_ativos.empty:
             return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), df_inativos

        res_av = (
            supabase.from_("prontuario_avaliacoes")
            .select("aluno_id, data_avaliacao")
            .execute()
        )
        df_av = pd.DataFrame(res_av.data)

        res_freq = supabase.from_("frequencia").select("aluno_id, status").execute()
        df_f_bruto = pd.DataFrame(res_freq.data)

        if not df_av.empty:
            df_av["data_avaliacao"] = pd.to_datetime(
                df_av["data_avaliacao"], errors="coerce"
            )
            df_av_latest = (
                df_av.groupby("aluno_id")["data_avaliacao"].max().reset_index()
            )
            df_merged = pd.merge(
                df_ativos, df_av_latest, left_on="id", right_on="aluno_id", how="left"
            )
        else:
            df_merged = df_ativos.copy()
            df_merged["data_avaliacao"] = pd.NaT

        if not df_f_bruto.empty:
            df_stats = (
                df_f_bruto.groupby("aluno_id")
                .agg(
                    total_aulas=("status", "count"),
                    total_presencas=("status", lambda x: (x == "PRESENTE").sum()),
                )
                .reset_index()
            )
            df_merged = pd.merge(
                df_merged, df_stats, left_on="id", right_on="aluno_id", how="left"
            )
        else:
            df_merged["total_aulas"] = 0
            df_merged["total_presencas"] = 0

        df_merged["total_presencas"] = (
            df_merged["total_presencas"].fillna(0).astype(int)
        )
        df_merged["total_aulas"] = df_merged["total_aulas"].fillna(0).astype(int)
        df_merged["taxa_presenca"] = (
            df_merged["total_presencas"] / df_merged["total_aulas"] * 100
        ).fillna(0.0)

        hoje = pd.Timestamp(datetime.date.today())
        df_merged["dias_passados"] = (hoje - df_merged["data_avaliacao"]).dt.days

        df_medidos = (
            df_merged[df_merged["data_avaliacao"].notna()]
            .sort_values("dias_passados", ascending=False)
            .copy()
        )
        df_nao_medidos = (
            df_merged[df_merged["data_avaliacao"].isna()].sort_values("nome").copy()
        )
        df_todos_crm = df_merged.sort_values("nome").copy()

        return df_medidos, df_nao_medidos, df_todos_crm, df_inativos
    except Exception as e:
        st.error(f"Falha Crítica no Motor de Dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ==============================================================================
# 🖥️ RENDERIZAÇÃO DA INTERFACE
# ==============================================================================
def renderizar_dashboard():
    # Injeção de CSS para o Action Grid + Micro Avatar + Hover Zoom
    st.markdown(
        """
    <style>
        .header-portal { background: linear-gradient(135deg, #F8FAFC 0%, #E0F2FE 100%); padding: 25px; border-radius: 12px; border-left: 6px solid #1E88E5; margin-bottom: 15px; }
        .header-portal h1 { color: #0A2540; font-size: 28px; margin: 0 0 5px 0; font-weight: 900; }
        .header-portal p { color: #64748B; font-size: 15px; margin: 0; font-weight: 500; }

        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] { overflow: visible !important; }

        .linha-divisoria { height: 1px; background-color: #E2E8F0; margin: 4px 0px 8px 0px; }
        .btn-compact button { min-height: 36px !important; padding: 4px 8px !important; font-size: 13px !important; }
        .grid-header { display:flex; background-color:#F8FAFC; padding:12px; border-radius:6px; font-weight:800; color:#475569; font-size:12px; border: 1px solid #E2E8F0; margin-bottom: 5px; text-transform: uppercase; }
        .grid-row { display:flex; align-items:center; padding: 8px 0; border-bottom: 1px solid #F1F5F9; }

        .zoom-avatar-dash {
            width: 36px; height: 36px; border-radius: 50%; object-fit: cover;
            border: 2px solid #1E88E5; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 10;
            flex-shrink: 0;
        }
        .zoom-avatar-dash:hover {
            transform: scale(4.0); z-index: 99999 !important; box-shadow: 0px 10px 20px rgba(0,0,0,0.5);
        }
        .avatar-placeholder {
            width: 36px; height: 36px; border-radius: 50%; background-color: #F1F5F9;
            color: #94A3B8; display: flex; align-items: center; justify-content: center;
            font-size: 18px; border: 1px dashed #CBD5E1; flex-shrink: 0;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    df_medidos, df_nao_medidos, df_todos_crm, df_inativos = carregar_dados_crm_avaliacoes_senior()

    if df_todos_crm.empty and df_inativos.empty:
        st.warning("A base de dados de alunos está vazia.")
        # Não damos return aqui para permitir o cadastro do primeiro aluno via busca.

    # ==========================================================================
    # 1. PAINEL DE CONTROLE (HERO SECTION & TABS) - MOVIDO PARA O TOPO
    # ==========================================================================
    st.markdown("""
        <div class="header-portal">
            <h1>🩺 Portal do Aluno & Gestão Clínica</h1>
            <p>Central de Admissões, Prontuários, Arquivo Morto e Agenda da Semana.</p>
        </div>
    """, unsafe_allow_html=True)

    tab_ag, tab_med, tab_novos, tab_todos, tab_inativos, tab_triagem = st.tabs([
        "🗓️ Agenda da Semana",
        f"📊 Já Medidos ({len(df_medidos)})",
        f"⚠️ Sem Medições ({len(df_nao_medidos)})",
        f"🌍 Visão Global ({len(df_todos_crm)})",
        f"🗄️ Arquivo Morto ({len(df_inativos)})",
        "🆕 NOVOS ALUNOS (Triagem)"
    ])

    # --- ABA 1: AGENDA SEMANAL ---
    with tab_ag:
        try:
            agenda_atual = get_agendamentos_pendentes()
            if agenda_atual:
                st.markdown(
                    "<div style='border-top: 2px solid #1E88E5; margin-bottom: 8px;'></div>",
                    unsafe_allow_html=True,
                )
                for ag in agenda_atual:
                    cd, ci, cb = st.columns([1, 4, 1.5], vertical_alignment="center")
                    dt = datetime.datetime.strptime(ag["data_agendamento"], "%Y-%m-%d")
                    cd.markdown(
                        f"<div style='text-align:center; padding: 6px 0;'><strong style='color:#1E88E5;font-size:16px;'>{dt.day}/{dt.strftime('%m')}</strong></div>",
                        unsafe_allow_html=True,
                    )
                    ci.markdown(
                        f"<div style='padding: 6px 0;'><strong style='font-size:14.5px;'>{ag['alunos']['nome']}</strong><br><span style='font-size:13px;color:#64748B;'>🕒 {ag['horario']} - {ag['motivo']}</span></div>",
                        unsafe_allow_html=True,
                    )
                    with cb:
                        st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                        if st.button(
                            "🩺 Avaliar",
                            key=f"go_{ag['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            st.session_state.aluno_prontuario = ag["alunos"]
                            concluir_ou_cancelar_agendamento(ag["id"], "Concluído")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown(
                        "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                    )
            else:
                st.info("Nenhuma avaliação pendente na agenda.")
        except:
            pass

    # --- ABA 2: JÁ MEDIDOS (CRM DE INATIVIDADE) ---
    with tab_med:
        if not df_medidos.empty:
            filtro_dias = st.selectbox(
                "Status de Inatividade:",
                ["Ver Todos", "Mais de 30 dias", "Mais de 60 dias", "Mais de 90 dias"],
                label_visibility="collapsed",
            )
            limites = {
                "Mais de 30 dias": 30,
                "Mais de 60 dias": 60,
                "Mais de 90 dias": 90,
            }
            df_exibir_m = (
                df_medidos[df_medidos["dias_passados"] >= limites[filtro_dias]]
                if filtro_dias != "Ver Todos"
                else df_medidos
            )

            for _, a in df_exibir_m.iterrows():
                c1, c2, c3, c4 = st.columns([3, 0.8, 0.8, 0.8], vertical_alignment="center")

                # Renderiza o Avatar
                url_foto = a.get('url_foto')
                if pd.notna(url_foto) and str(url_foto).strip() and str(url_foto).strip().lower() not in ["none", "nan", "null", ""]:
                    avatar_html = f"<img src='{url_foto}' class='zoom-avatar-dash' alt='Foto'>"
                else:
                    avatar_html = "<div class='avatar-placeholder'>👤</div>"

                cor_alerta = "#B91C1C" if a["dias_passados"] >= 90 else "#64748B"
                icone = "⚠️" if a["dias_passados"] >= 90 else "✔️"

                c1.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 12px; padding: 4px 0;'>
                        {avatar_html}
                        <div style='line-height:1.3;'>
                            <strong style='font-size: 14px; color:#0F172A;'>{a['nome']}</strong><br>
                            <span style='color:{cor_alerta}; font-size: 12px;'>{icone} Última: {a['data_avaliacao'].strftime('%d/%m/%Y')} <b>({int(a['dias_passados'])} dias)</b></span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                with c2:
                    st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                    if st.button("🗓️", key=f"med_ag_{a['id']}", help="Agendar"):
                        st.session_state[f"f_ag_{a['id']}"] = True
                    st.markdown("</div>", unsafe_allow_html=True)
                with c3:
                    st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                    if st.button(
                        "🩺",
                        key=f"med_av_{a['id']}",
                        type="primary",
                        help="Abrir Ficha",
                    ):
                        st.session_state.aluno_prontuario = a.to_dict()
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{a['id']}", help="Excluir Aluno"):
                        st.session_state[f"del_mode_{a['id']}"] = True
                    st.markdown("</div>", unsafe_allow_html=True)

                # Modal de Confirmação de Exclusão
                if st.session_state.get(f"del_mode_{a['id']}"):
                    with st.container(border=True):
                        st.error(f"Deseja excluir {a['nome']}?")
                        if st.button("Confirmar Exclusão", key=f"c_del_{a['id']}"):
                            excluir_aluno_completo(
                                a["id"], st.session_state.get("usuario_email")
                            )
                            st.rerun()
                        if st.button("Cancelar", key=f"can_{a['id']}"):
                            st.session_state[f"del_mode_{a['id']}"] = False
                            st.rerun()

                # Modal de Agendamento Rápido
                if st.session_state.get(f"f_ag_{a['id']}", False):
                    with st.container(border=True):
                        st.write(f"Agendar para {a['nome']}")
                        ca, cb = st.columns(2)
                        d_esc = ca.date_input(
                            "Data:",
                            min_value=datetime.date.today(),
                            key=f"d_m_{a['id']}",
                        )
                        h_esc = cb.time_input(
                            "Hora:", value=datetime.time(8, 0), key=f"h_m_{a['id']}"
                        )
                        if st.button(
                            "Confirmar Agendamento",
                            key=f"cf_m_{a['id']}",
                            type="primary",
                        ):
                            criar_agendamento(
                                a["id"], d_esc, h_esc.strftime("%H:%M"), "Reavaliação"
                            )
                            st.session_state[f"f_ag_{a['id']}"] = False
                            st.rerun()
                st.markdown(
                    "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                )

    # --- ABA 3: AGUARDANDO MEDIÇÃO ---
    with tab_novos:
        if not df_nao_medidos.empty:
            for _, a in df_nao_medidos.iterrows():
                c1, c2, c3 = st.columns([3.5, 0.8, 0.8], vertical_alignment="center")

                # Renderiza o Avatar
                url_foto = a.get('url_foto')
                if pd.notna(url_foto) and str(url_foto).strip() and str(url_foto).strip().lower() not in ["none", "nan", "null", ""]:
                    avatar_html = f"<img src='{url_foto}' class='zoom-avatar-dash' alt='Foto'>"
                else:
                    avatar_html = "<div class='avatar-placeholder'>👤</div>"

                c1.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        {avatar_html}
                        <div style='line-height:1.3;'>
                            <strong style='font-size:14px; color:#0F172A;'>{a['nome']}</strong><br>
                            <span style='font-size:12px;color:#64748B;'>Aguardando primeira medição</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                with c2:
                    st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                    if st.button("🗓️", key=f"n_ag_{a['id']}"):
                        st.session_state[f"f_ag_{a['id']}"] = True
                    st.markdown("</div>", unsafe_allow_html=True)
                with c3:
                    st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                    if st.button("🩺", key=f"n_av_{a['id']}", type="primary"):
                        st.session_state.aluno_prontuario = a.to_dict()
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(
                    "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                )

    # --- ABA 4: VISÃO GLOBAL ---
    with tab_todos:
        st.write("Base consolidada para auditoria rápida (Apenas Alunos Ativos).")
        st.dataframe(
            df_todos_crm[["nome", "turma", "data_avaliacao", "taxa_presenca"]],
            use_container_width=True,
            hide_index=True,
        )

    # --- ABA 5: ARQUIVO MORTO ---
    with tab_inativos:
        st.markdown("### 🗄️ Arquivo Morto")
        st.caption("Alunos desativados. Os dados clínicos ficam preservados. Use **📂 Ver Ficha** para editar, excluir ou gerar dossiê. Use **↩️ Reativar** para devolver ao sistema.")

        if df_inativos.empty:
            st.success("Nenhum aluno no Arquivo Morto.")
        else:
            # --- BUSCA DENTRO DO ARQUIVO ---
            busca_inativo = st.text_input(
                "🔍 Buscar no Arquivo Morto:",
                placeholder="Digite parte do nome...",
                key="busca_arquivo_morto",
                label_visibility="collapsed",
            )

            df_exibir = df_inativos.copy()
            if busca_inativo and len(busca_inativo.strip()) >= 2:
                termo = busca_inativo.strip().lower()
                df_exibir = df_exibir[df_exibir["nome"].str.lower().str.contains(termo, na=False)]

            if df_exibir.empty:
                st.info("Nenhum aluno encontrado para essa busca.")
            else:
                st.caption(f"Exibindo **{len(df_exibir)}** de {len(df_inativos)} arquivados.")

            is_super = st.session_state.get("perfil") == "SuperAdmin"
            email_op = (
                st.session_state.get("usuario_email")
                or st.session_state.get("email_usuario")
                or st.session_state.get("email", "sistema")
            )

            for _, a in df_exibir.iterrows():
                chave_excl = f"conf_excluir_{a['id']}"
                aguardando_excl = is_super and st.session_state.get(chave_excl)

                # Destaque vermelho na linha que aguarda confirmação de exclusão
                if aguardando_excl:
                    st.markdown(
                        f"<div style='background:#FEF2F2; border:2px solid #EF4444; border-radius:8px; padding:6px 10px; margin-bottom:2px;'>"
                        f"<span style='color:#B91C1C; font-size:12px; font-weight:700;'>⚠️ Confirmar exclusão permanente de: {a['nome']}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                cols = [4, 1.1, 1.1, 1.1] if is_super else [4, 1.1, 1.1]
                colunas = st.columns(cols, vertical_alignment="center")
                c1 = colunas[0]
                c2 = colunas[1]
                c3 = colunas[2]
                c4 = colunas[3] if is_super else None

                url_foto = a.get('url_foto')
                if pd.notna(url_foto) and str(url_foto).strip() and str(url_foto).strip().lower() not in ["none", "nan", "null", ""]:
                    avatar_html = f"<img src='{url_foto}' class='zoom-avatar-dash' style='filter: grayscale(100%); opacity: 0.7;' alt='Foto'>"
                else:
                    avatar_html = "<div class='avatar-placeholder' style='background-color: #F8FAFC; color: #CBD5E1;'>👤</div>"

                ultima_turma = a.get('turma') or 'N/A'

                c1.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        {avatar_html}
                        <div style='line-height:1.3;'>
                            <strong style='font-size:14px; color:#64748B;'>{a['nome']}</strong><br>
                            <span style='font-size:12px;color:#94A3B8;'>🗄️ Arquivado · Última Turma: <strong>{ultima_turma}</strong></span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                with c2:
                    if st.button("📂 Ver Ficha", key=f"in_av_{a['id']}", use_container_width=True):
                        st.session_state.aluno_prontuario = a.to_dict()
                        st.rerun()

                with c3:
                    chave_conf = f"conf_reativar_{a['id']}"
                    if st.session_state.get(chave_conf):
                        col_sim, col_nao = st.columns(2)
                        with col_sim:
                            if st.button("✅", key=f"sim_reat_{a['id']}", help="Confirmar reativação", use_container_width=True):
                                ok, msg = alterar_status_aluno(a['id'], "Ativo")
                                st.session_state.pop(chave_conf, None)
                                if ok:
                                    st.success(f"{a['nome']} reativado!")
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col_nao:
                            if st.button("❌", key=f"nao_reat_{a['id']}", help="Cancelar", use_container_width=True):
                                st.session_state.pop(chave_conf, None)
                                st.rerun()
                    else:
                        if st.button("↩️ Reativar", key=f"reat_{a['id']}", use_container_width=True):
                            st.session_state[chave_conf] = True
                            st.rerun()

                # --- BOTÃO EXCLUIR (somente SuperAdmin) ---
                if is_super and c4 is not None:
                    with c4:
                        if st.session_state.get(chave_excl):
                            col_ok, col_x = st.columns(2)
                            with col_ok:
                                if st.button("✅", key=f"sim_excl_{a['id']}", help="Confirmar exclusão permanente", use_container_width=True):
                                    ok, msg = excluir_aluno_completo(a['id'], email_op)
                                    st.session_state.pop(chave_excl, None)
                                    if ok:
                                        st.success(f"'{a['nome']}' excluído permanentemente.")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(f"Erro: {msg}")
                            with col_x:
                                if st.button("❌", key=f"nao_excl_{a['id']}", help="Cancelar", use_container_width=True):
                                    st.session_state.pop(chave_excl, None)
                                    st.rerun()
                        else:
                            if st.button("🗑️ Excluir", key=f"excl_{a['id']}", use_container_width=True, type="secondary", help="Exclusão permanente — irreversível"):
                                st.session_state[chave_excl] = True
                                st.rerun()

                st.markdown("<div class='linha-divisoria'></div>", unsafe_allow_html=True)

    # --- ABA 6: NOVOS ALUNOS (TRIAGEM) ---
    with tab_triagem:
        st.markdown("### 📥 Caixa de Entrada de Inscrições")
        st.caption("Aprove, edite ou rejeite os pré-cadastros vindos do formulário público.")

        if st.session_state.get("perfil") == "SuperAdmin":
            from views.triagem_view import tela_triagem
            tela_triagem()
        else:
            st.error("⚠️ Acesso Restrito: Apenas a coordenação pode aprovar e matricular novos alunos.")

    st.divider()

    # ==========================================================================
    # 2. ACTION GRID (DIRETÓRIO GLOBAL) - MOVIDO PARA A BASE
    # ==========================================================================
    st.markdown("### 🔍 Diretório de Alunos e Emissão de Dossiês")

    with st.container(border=True):
        # Controles Superiores
        c_busca, c_ordem, c_pag = st.columns([3, 2, 1], vertical_alignment="bottom")

        # 🚀 A MÁGICA DO LIVE SEARCH (ST_KEYUP)
        placeholder_texto = "🔍 Filtrar Ativos (mín. 3 letras)..."
        with c_busca:
            if HAS_KEYUP:
                busca = st_keyup(
                    "Filtrar Aluno:",
                    placeholder=placeholder_texto,
                    debounce=300,
                    key="busca_dash",
                    label_visibility="collapsed",
                )
            else:
                busca = st.text_input(
                    "Filtrar Aluno:",
                    placeholder=placeholder_texto,
                    key="busca_dash_fallback",
                    label_visibility="collapsed",
                )

        ordenacao = c_ordem.selectbox(
            "Ordenar por:",
            [
                "Nome (A-Z)",
                "Nome (Z-A)",
                "Mais Presenças",
                "Menos Presenças",
                "Maior Taxa de Presença",
                "Menor Taxa de Presença",
            ],
            label_visibility="collapsed",
        )

        # 🚀 Aplicação de Filtros (Gatilho de 3 Caracteres e Ignorando Acentos)
        df_grid = df_todos_crm.copy()

        if busca:
            busca_limpa = remover_acentos(busca).strip()

            if len(busca_limpa) >= 3:
                # Cria colunas temporárias normalizadas para a busca
                df_temp_nome = df_grid["nome"].apply(remover_acentos)
                df_temp_turma = df_grid["turma"].apply(remover_acentos)

                # Filtra onde a string limpa bate com os dados limpos
                df_grid = df_grid[
                    df_temp_nome.str.contains(busca_limpa, case=False, na=False)
                    | df_temp_turma.str.contains(busca_limpa, case=False, na=False)
                ]
            elif len(busca_limpa) > 0:
                st.caption("⏳ Digite pelo menos 3 letras para iniciar a filtragem rápida...")

        # Aplicação de Ordenação
        if ordenacao == "Nome (A-Z)":
            df_grid = df_grid.sort_values("nome", ascending=True)
        elif ordenacao == "Nome (Z-A)":
            df_grid = df_grid.sort_values("nome", ascending=False)
        elif ordenacao == "Mais Presenças":
            df_grid = df_grid.sort_values("total_presencas", ascending=False)
        elif ordenacao == "Menos Presenças":
            df_grid = df_grid.sort_values("total_presencas", ascending=True)
        elif ordenacao == "Maior Taxa de Presença":
            df_grid = df_grid.sort_values("taxa_presenca", ascending=False)
        elif ordenacao == "Menor Taxa de Presença":
            df_grid = df_grid.sort_values("taxa_presenca", ascending=True)

        # Paginação
        itens_por_pagina = 15
        total_pags = max(1, math.ceil(len(df_grid) / itens_por_pagina))
        pagina = c_pag.number_input(
            f"Pág. (de {total_pags})",
            min_value=1,
            max_value=total_pags,
            value=1,
            label_visibility="collapsed",
        )

        inicio, fim = (pagina - 1) * itens_por_pagina, pagina * itens_por_pagina
        df_page = df_grid.iloc[inicio:fim]

        # Cabeçalho do Action Grid (HTML)
        st.markdown(
            """
        <div class='grid-header'>
            <div style='flex: 3.5;'>Aluno / Turma</div>
            <div style='flex: 0.9; text-align:center;'>Nascimento</div>
            <div style='flex: 1; text-align:center;'>Aulas</div>
            <div style='flex: 1; text-align:center;'>Presenças</div>
            <div style='flex: 1.5; text-align:center;'>Taxa Global</div>
            <div style='flex: 2; text-align:center;'>Ações</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ======================================================================
        # 🚀 MÁGICA UX: SE NÃO ENCONTRAR, MOSTRA FORMULÁRIO DE CADASTRO RÁPIDO
        # ======================================================================
        if df_page.empty:
            if busca and len(busca.strip()) >= 3:
                st.warning(f"🔍 Nenhum aluno encontrado para: **'{busca}'**")

                with st.container(border=True):
                    st.markdown(f"<h4 style='color:#1E88E5; margin-bottom: 10px; margin-top: 0;'>✨ Criar Novo Cadastro Rápido</h4>", unsafe_allow_html=True)
                    st.caption("Preencha apenas a turma para matricular este aluno imediatamente.")

                    with st.form(key=f"form_quick_cad_{busca}"):
                        turmas_df = get_todas_turmas(ativas_apenas=True)
                        lista_turmas = turmas_df["nome"].tolist() if not turmas_df.empty else ["Nenhuma turma disponível"]

                        c_n, c_t = st.columns([2, 1])
                        novo_nome = c_n.text_input("Nome do Aluno:", value=busca.upper().strip())
                        nova_turma = c_t.selectbox("Alocar na Turma:", lista_turmas)

                        if st.form_submit_button("✅ Cadastrar e Matricular", type="primary", use_container_width=True):
                            if nova_turma == "Nenhuma turma disponível":
                                st.error("Crie uma turma primeiro no menu 'Turmas'.")
                            elif len(novo_nome) < 3:
                                st.error("O nome deve ter pelo menos 3 letras.")
                            else:
                                sucesso = cadastrar_novo_aluno(nome=novo_nome, turma=nova_turma)
                                if sucesso:
                                    st.success(f"🎉 {novo_nome} foi matriculado com sucesso na turma {nova_turma}!")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("Erro ao tentar cadastrar no banco de dados.")
            else:
                st.info("Nenhum aluno encontrado para este filtro.")
        else:
            # Renderização das Linhas do Grid
            for _, a in df_page.iterrows():
                c1, c2, c3, c4, c5, c6 = st.columns(
                    [3.5, 0.9, 1, 1, 1.5, 2], vertical_alignment="center"
                )

                # Col 1: Foto + Nome e Turma (MÁGICA DO FLEXBOX)
                url_foto = a.get('url_foto')
                if pd.notna(url_foto) and str(url_foto).strip() and str(url_foto).strip().lower() not in ["none", "nan", "null", ""]:
                    avatar_html = f"<img src='{url_foto}' class='zoom-avatar-dash' alt='Foto'>"
                else:
                    avatar_html = "<div class='avatar-placeholder'>👤</div>"

                c1.markdown(
                    f"""
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        {avatar_html}
                        <div style='line-height:1.3;'>
                            <strong style='font-size:14px; color:#0F172A;'>{a['nome']}</strong><br>
                            <span style='font-size:12px;color:#64748B;'>{a['turma']}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Col 2: Nascimento
                _dn = a.get("data_nascimento")
                try:
                    _dn_fmt = pd.to_datetime(_dn).strftime("%d/%m/%Y") if pd.notna(_dn) and _dn else "—"
                except Exception:
                    _dn_fmt = "—"
                c2.markdown(
                    f"<div style='text-align:center; font-size:12px; color:#64748B;'>{_dn_fmt}</div>",
                    unsafe_allow_html=True,
                )

                # Col 3 e 4: Métricas
                c3.markdown(
                    f"<div style='text-align:center; font-size:14px; font-weight:600; color:#475569;'>{int(a['total_aulas'])}</div>",
                    unsafe_allow_html=True,
                )
                c4.markdown(
                    f"<div style='text-align:center; font-size:15px; font-weight:900; color:#10B981;'>{int(a['total_presencas'])}</div>",
                    unsafe_allow_html=True,
                )

                # Col 5: Barra de Progresso Customizada
                taxa = a["taxa_presenca"]
                cor_barra = (
                    "#10B981"
                    if taxa >= 65
                    else ("#F59E0B" if taxa >= 40 else "#EF4444")
                )
                c5.markdown(
                    f"""
                <div style='text-align:center; font-size:13px; font-weight:800; color:{cor_barra}; margin-bottom:2px;'>{taxa:.1f}%</div>
                <div style='width:90%; margin:0 auto; background-color:#E2E8F0; border-radius:4px; height:6px;'>
                    <div style='width:{taxa}%; background-color:{cor_barra}; height:100%; border-radius:4px;'></div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Col 6: Botões de Ação Direta
                with c6:
                    st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                    cb1, cb2, cb3 = st.columns(3, gap="small")

                    if cb1.button(
                        "🩺 Abrir", key=f"abr_{a['id']}", use_container_width=True
                    ):
                        st.session_state.aluno_prontuario = a.to_dict()
                        st.rerun()

                    pdf_key = f"pdf_grid_{a['id']}"
                    word_key = f"word_grid_{a['id']}"

                    if st.session_state.get(pdf_key):
                        cb2.download_button(
                            "📥 PDF",
                            data=st.session_state[pdf_key],
                            file_name=f"Dossie_{a['nome'][:15]}.pdf",
                            mime="application/pdf",
                            key=f"dl_grid_{a['id']}",
                            type="primary",
                            use_container_width=True,
                        )
                    else:
                        if cb2.button(
                            "🖨️ PDF",
                            key=f"dos_{a['id']}",
                            use_container_width=True,
                            type="primary",
                        ):
                            with st.spinner("⏳"):
                                from gerador_pdf import criar_documento_aluno_pdf
                                estats = get_estatisticas_frequencia_aluno(a["id"])
                                historico = get_historico_aulas_aluno(a["id"])
                                avals = get_avaliacoes_aluno(a["id"])
                                st.session_state[pdf_key] = criar_documento_aluno_pdf(
                                    a.to_dict(), avals, historico, estats
                                )
                            st.rerun()

                    word_err_key = f"word_err_{a['id']}"
                    if st.session_state.get(word_err_key):
                        cb3.error(st.session_state.pop(word_err_key))
                    elif st.session_state.get(word_key):
                        cb3.download_button(
                            "📥 Word",
                            data=st.session_state[word_key],
                            file_name=f"Dossie_{a['nome'][:15]}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_word_{a['id']}",
                            use_container_width=True,
                        )
                    else:
                        if cb3.button(
                            "📘 Word",
                            key=f"wrd_{a['id']}",
                            use_container_width=True,
                        ):
                            with st.spinner("Gerando Word…"):
                                try:
                                    from gerador_word import criar_documento_aluno_word
                                    estats = get_estatisticas_frequencia_aluno(a["id"])
                                    historico = get_historico_aulas_aluno(a["id"])
                                    avals = get_avaliacoes_aluno(a["id"])
                                    _wb = criar_documento_aluno_word(
                                        a.to_dict(), avals, historico, estats
                                    )
                                    if _wb:
                                        st.session_state[word_key] = _wb
                                    else:
                                        st.session_state[word_err_key] = "Falha: gerador retornou vazio."
                                except Exception as _e:
                                    import traceback
                                    st.session_state[word_err_key] = f"Erro: {_e}"
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown(
                    "<div class='linha-divisoria'></div>", unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Sincronizar Base de Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()