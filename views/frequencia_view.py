# ==============================================================================
# 📄 ARQUIVO: views/frequencia_view.py (ROTEADOR MESTRE)
# 🏷️ VERSÃO: 13.1 (PRO Elite - Roteamento Fiel para Nova Matrícula)
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Roteador de frequência, busca global e dropdown espelhado no BD.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import time
import re

try:
    from st_keyup import st_keyup

    HAS_KEYUP = True
except ImportError:
    HAS_KEYUP = False

# Importação do motor e permissões
from database import (
    buscar_alunos_geral,
    get_alunos_por_turma,
    get_presencas_dia,
    ADMIN_MASTER,
    alterar_status_aluno,
    atualizar_turma_aluno,
    get_todas_turmas,
)
from modulos_frequencia.tab_tablet import renderizar_aba_terminal
from modulos_frequencia.tab_diario import renderizar_aba_diario
from modulos_frequencia.tab_dossie import renderizar_aba_dossie
from modulos_frequencia.tab_emergencia import renderizar_aba_emergencia
from modulos_frequencia.tab_niver import renderizar_aba_niver
from utils.texto import remover_acentos


# ==============================================================================
# 📅 MOTOR DE CALENDÁRIO LETIVO
# ==============================================================================
def verificar_dia_letivo(data):
    if data.weekday() == 5:
        return False, "Sábado (Fim de Semana)"
    if data.weekday() == 6:
        return False, "Domingo (Fim de Semana)"

    feriados_fixos = {
        (1, 1): "Ano Novo",
        (1, 25): "Aniversário de São Paulo",
        (4, 21): "Tiradentes",
        (5, 1): "Dia do Trabalhador",
        (7, 9): "Revolução Constitucionalista (SP)",
        (9, 7): "Independência do Brasil",
        (10, 12): "Nossa Senhora Aparecida",
        (11, 2): "Finados",
        (11, 15): "Proclamação da República",
        (11, 20): "Dia da Consciência Negra",
        (12, 25): "Natal",
    }
    if (data.month, data.day) in feriados_fixos:
        return False, f"Feriado: {feriados_fixos[(data.month, data.day)]}"

    feriados_moveis = {
        datetime.date(2025, 3, 3): "Carnaval",
        datetime.date(2025, 3, 4): "Carnaval",
        datetime.date(2025, 4, 18): "Sexta-feira Santa",
        datetime.date(2025, 6, 19): "Corpus Christi",
        datetime.date(2026, 2, 16): "Carnaval",
        datetime.date(2026, 2, 17): "Carnaval",
        datetime.date(2026, 4, 3): "Sexta-feira Santa",
        datetime.date(2026, 6, 4): "Corpus Christi",
        datetime.date(2027, 2, 8): "Carnaval",
        datetime.date(2027, 2, 9): "Carnaval",
        datetime.date(2027, 3, 26): "Sexta-feira Santa",
        datetime.date(2027, 5, 27): "Corpus Christi",
    }
    if data in feriados_moveis:
        return False, f"Feriado: {feriados_moveis[data]}"

    return True, "Dia Letivo Válido"


@st.cache_data(ttl=60)
def obter_todos_alunos_cache():
    return buscar_alunos_geral("")


@st.cache_data(ttl=60)
def obter_todos_alunos_com_inativos_cache():
    return buscar_alunos_geral("", incluir_inativos=True)


def obter_alunos_por_selecao(selecao, mostrar_todos=False):
    """Busca os alunos dinamicamente do banco de dados, unindo turmas do mesmo horário se solicitado."""
    if mostrar_todos:
        hora_match = re.search(r"(0[789]H|1[012]H)", selecao)
        if hora_match:
            hora_busca = hora_match.group(1)
            df_todas = get_todas_turmas(ativas_apenas=True)

            if not df_todas.empty:
                turmas_mesmo_horario = [
                    t for t in df_todas["nome"].tolist() if hora_busca in t
                ]
                dfs = []
                for t in turmas_mesmo_horario:
                    df_t = get_alunos_por_turma(t)
                    if not df_t.empty:
                        dfs.append(df_t)

                if dfs:
                    return pd.concat(dfs).drop_duplicates(subset=["id"])

    return get_alunos_por_turma(selecao)


def carregar_css_global():
    st.markdown(
        """
        <style>
            .zoom-avatar { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 50; }
            .zoom-avatar:hover { transform: scale(10.0); z-index: 99999 !important; box-shadow: 0px 20px 40px rgba(0,0,0,0.6); position: relative; }
            div[data-baseweb="select"] > div { border: 2px solid #1E88E5 !important; border-radius: 8px !important; background-color: #F8FAFC !important; font-weight: 800 !important; font-size: 16px !important; color: #0A2540 !important; }
        </style>
    """,
        unsafe_allow_html=True,
    )


def tela_frequencia():
    carregar_css_global()

    df_niver_check = obter_todos_alunos_cache()
    hoje_check = datetime.date.today()
    tem_aniversariante_hoje = False
    for _, r in df_niver_check.iterrows():
        try:
            if pd.notna(r.get("data_nascimento")):
                dt = pd.to_datetime(r.get("data_nascimento")).date()
                if dt.day == hoje_check.day and dt.month == hoje_check.month:
                    tem_aniversariante_hoje = True
                    break
        except:
            continue

    label_niver = (
        "🎂 Niver 🍰 HOJE TEM BOLO!!!" if tem_aniversariante_hoje else "🎂 Niver"
    )

    st.markdown(
        "<h2 style='color: #0A2540; font-weight: 900; margin-bottom: 0px;'>📊 Gestão de Fluxo</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        col_turma, col_data, col_busca = st.columns(
            [4, 2, 4], vertical_alignment="bottom"
        )

        with col_data:
            data_aula = st.date_input(
                "📅 Data da Aula:", hoje_check, format="DD/MM/YYYY"
            )

        dia_semana = data_aula.weekday()
        if dia_semana in [5, 6]:
            turmas_combo = ["Dia não letivo (Fim de Semana)"]
        else:
            df_turmas_ativas = get_todas_turmas(ativas_apenas=True)
            if not df_turmas_ativas.empty:
                turmas_combo = df_turmas_ativas["nome"].tolist()
            else:
                turmas_combo = ["Nenhuma turma ativa cadastrada"]

        with col_turma:
            turma_selecionada = st.selectbox("👥 Selecione a Turma:", turmas_combo)

        chave_unica = f"{data_aula}_{turma_selecionada}"

        with col_busca:
            placeholder_texto = "🔍 Filtrar (mín. 3 letras)..."
            if HAS_KEYUP:
                busca_grid = st_keyup(
                    "🔍 Busca Global:",
                    placeholder=placeholder_texto,
                    debounce=300,
                    key=f"bg_{chave_unica}",
                )
            else:
                busca_grid = st.text_input(
                    "🔍 Busca Global:",
                    placeholder=placeholder_texto,
                    key=f"bg_{chave_unica}",
                )

    eh_valido, motivo_bloqueio = verificar_dia_letivo(data_aula)

    if not eh_valido:
        st.markdown(
            f"""
            <div style='background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 20px;'>
                <h3 style='color: #991B1B; margin-top: 0; font-weight: 900;'>🛑 Data Bloqueada: {motivo_bloqueio}</h3>
                <p style='color: #7F1D1D; margin-bottom: 0; font-size: 16px;'>O sistema não permite o registo de frequência ou diários em fins de semana e feriados. Selecione um <b>dia útil</b>.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        return

    dias_passados = (hoje_check - data_aula).days
    bloqueio_ativo = False

    if dias_passados > 10 and st.session_state.get("usuario_email") != ADMIN_MASTER:
        bloqueio_ativo = True
        st.error(
            "🔒 **Edição Bloqueada:** Esta aula ocorreu há mais de 10 dias. O registo de frequência encontra-se selado por segurança. Apenas o Administrador Mestre pode efetuar alterações."
        )

    busca_limpa = remover_acentos(busca_grid).strip() if busca_grid else ""
    mostrar_todos_horario = False

    if len(busca_limpa) >= 3:
        df_todos_com_inativos = obter_todos_alunos_com_inativos_cache()

        if not df_todos_com_inativos.empty:
            df_temp_nome = df_todos_com_inativos["nome"].apply(remover_acentos)
            df_encontrados = df_todos_com_inativos[
                df_temp_nome.str.contains(busca_limpa, case=False, na=False)
            ]
        else:
            df_encontrados = pd.DataFrame()

        if not df_encontrados.empty:
            st.success(
                f"🌍 Busca Global Ativada: Encontrámos {len(df_encontrados)} aluno(s) na base geral."
            )

            alunos_prontos = []
            df_valida = obter_alunos_por_selecao(turma_selecionada, False)
            ids_validos_na_tela = (
                df_valida["id"].tolist() if not df_valida.empty else []
            )

            for _, aluno in df_encontrados.iterrows():
                is_inativo = aluno.get("status") == "Inativo"
                is_outra_turma = aluno["id"] not in ids_validos_na_tela

                if is_inativo or is_outra_turma:
                    with st.container(border=True):
                        st_atual = (
                            "INATIVO (Arquivo Morto)"
                            if is_inativo
                            else f"Ativo na turma: {aluno.get('turma')}"
                        )
                        st.warning(
                            f"⚠️ Atenção! **{aluno['nome']}** foi encontrado, mas encontra-se **{st_atual}**."
                        )

                        c_btn1, c_btn2 = st.columns([1, 1])

                        with c_btn1:
                            if st.button(
                                f"🩺 Abrir Ficha Digital",
                                key=f"f_pr_{aluno['id']}",
                                use_container_width=True,
                            ):
                                st.session_state.aluno_prontuario = aluno.to_dict()
                                st.session_state.origem_prontuario = "Frequência"
                                st.session_state.menu_atual = "Portal do Aluno"
                                st.rerun()

                        with c_btn2:
                            lbl_botao = (
                                "♻️ Ativar e Transferir p/ Turma Atual"
                                if is_inativo
                                else "🔄 Transferir p/ Turma Atual"
                            )
                            if st.button(
                                lbl_botao,
                                key=f"fix_{aluno['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                if is_inativo:
                                    alterar_status_aluno(aluno["id"], "Ativo")
                                atualizar_turma_aluno(aluno["id"], turma_selecionada)
                                st.cache_data.clear()
                                st.toast(
                                    f"✅ {aluno['nome'].split()[0]} foi integrado(a) nesta turma com sucesso!"
                                )
                                time.sleep(1)
                                st.rerun()
                else:
                    alunos_prontos.append(aluno)

            df_alunos = pd.DataFrame(alunos_prontos)
        else:
            df_alunos = pd.DataFrame()
            st.warning(
                f"Nenhum aluno encontrado com o nome '{busca_grid}' (nem ativos, nem inativos)."
            )

            # 🚀 AQUI A MÁGICA: O BOTÃO AGORA TRANSPORTA PARA O MÓDULO CORRETO!
            if st.button("➕ O Aluno é Novo? CADASTRAR AGORA", type="primary", use_container_width=True):
                st.session_state.menu_atual = "Nova Matrícula"
                st.rerun()
    else:
        if len(busca_limpa) > 0:
            st.caption("⏳ Digite pelo menos 3 letras para ativar a Busca Global...")

        hora_match = re.search(r"(0[789]H|1[012]H)", turma_selecionada)
        if hora_match:
            hora_turma = hora_match.group(1)
            mostrar_todos_horario = st.checkbox(
                f"🌍 Exibir TODOS os alunos do horário das {hora_turma} (Misturar turmas de outros dias)",
                value=False,
            )

        df_alunos = obter_alunos_por_selecao(turma_selecionada, mostrar_todos_horario)

    if not df_alunos.empty and "nome" in df_alunos.columns:
        df_alunos = df_alunos.sort_values(by="nome").reset_index(drop=True)

    presencas_turma_geral = (
        get_presencas_dia(data_aula, df_alunos["id"].tolist())
        if not df_alunos.empty
        else {}
    )

    tab_tablet, tab_d, tab_ds, tab_em, tab_niver = st.tabs(
        ["📱 Chamada Tablet", "📝 Diário", "🖨️ Dossiê", "🚨 Emergência", label_niver]
    )

    with tab_tablet:
        renderizar_aba_terminal(
            df_alunos, data_aula, presencas_turma_geral, bloqueio_ativo
        )

    with tab_d:
        renderizar_aba_diario(data_aula, turma_selecionada, chave_unica)

    with tab_ds:
        renderizar_aba_dossie(df_alunos, data_aula, turma_selecionada, chave_unica)

    with tab_em:
        renderizar_aba_emergencia(df_alunos, turma_selecionada)

    with tab_niver:
        renderizar_aba_niver()