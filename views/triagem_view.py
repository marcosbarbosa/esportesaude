# ==============================================================================
# 📄 ARQUIVO: views/triagem_view.py
# 🏷️ VERSÃO: 2.4 (PRO Elite - Fluxo Turbo + Integridade Total do Layout)
# 📅 DATA: Atualizado
# ⚙️ FUNÇÃO: Auditoria de inscrições, cadastro oficial direto e controle de vagas.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import time
from views.utils_docs import url_eh_imagem, renderizar_documento_com_rotacao

from database import (
    get_pre_cadastros_pendentes, 
    aprovar_inscricao_aluno, 
    rejeitar_inscricao_aluno,
    get_todas_turmas,
    get_ocupacao_turmas,
    supabase
)

def mover_para_espera(cadastro_id, nome):
    """Muda o status da inscrição para a Lista de Espera."""
    try:
        supabase.table("pre_cadastros").update({"status": "Lista de Espera"}).eq("id", cadastro_id).execute()
        st.toast(f"{nome} movido para a Lista de Espera!", icon="⏳")
        return True
    except Exception as e:
        st.error(f"Erro ao mover para espera: {e}")
        return False

def tela_triagem():
    st.markdown("""
        <div style='margin-bottom: 20px;'>
            <h2 style='color: #0A2540; font-weight: 900; margin-bottom: 0px;'>🛡️ Painel de Triagem</h2>
            <p style='color: #64748B; font-size: 14px;'>Instituto Muda Brasil: Auditoria de inscrições, conferência de documentos e alocação orientada a dados.</p>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================================================
    # MOTOR DE VAGAS (Movido para cima para alimentar o formulário Turbo)
    # ==========================================================================
    df_turmas_ativas = get_todas_turmas(ativas_apenas=True)
    ocupacao = get_ocupacao_turmas()

    if df_turmas_ativas.empty:
        st.warning("⚠️ Não há turmas ativas cadastradas. Vá ao módulo de 'Gestão de Turmas' para criá-las.")
        return

    turmas_nomes = df_turmas_ativas['nome'].tolist()

    # Prepara o Dropdown Inteligente de Turmas e Vagas
    lista_turmas_display = []
    mapa_turmas = {} 

    for t_nome in turmas_nomes:
        info = ocupacao.get(t_nome, {})
        vagas = info.get('vagas', 40)

        if vagas <= 0: display = f"🔴 {t_nome} (LOTADA)"
        elif vagas <= 5: display = f"🟡 {t_nome} ({vagas} vagas restantes)"
        else: display = f"🟢 {t_nome} ({vagas} vagas livres)"

        lista_turmas_display.append(display)
        mapa_turmas[display] = t_nome


    # ==========================================================================
    # 1. TERMÔMETRO VISUAL (DASHBOARD DE VAGAS)
    # ==========================================================================
    st.markdown("### 📊 Ocupação das Turmas em Tempo Real")

    colunas_por_linha = 3
    for i in range(0, len(turmas_nomes), colunas_por_linha):
        cols = st.columns(colunas_por_linha)
        for j, t_nome in enumerate(turmas_nomes[i:i+colunas_por_linha]):
            info = ocupacao.get(t_nome, {})
            qtd = info.get('qtd', 0)
            limite = info.get('limite', 40)
            vagas_reais = info.get('vagas', 40)

            if vagas_reais <= 0:
                cor_borda, cor_fundo, icone = "#EF4444", "#FEF2F2", "🔴 LOTADA"
            elif vagas_reais <= 5:
                cor_borda, cor_fundo, icone = "#F59E0B", "#FFFBEB", "🟡 ALERTA"
            else:
                cor_borda, cor_fundo, icone = "#10B981", "#ECFDF5", "🟢 LIVRE"

            html_card = f"""
            <div style="border: 2px solid {cor_borda}; background-color: {cor_fundo}; border-radius: 8px; padding: 12px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 13px; font-weight: bold; color: #334155; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{t_nome}">
                    {t_nome.split(' - ')[0]}
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 18px; font-weight: 900; color: #0F172A;">{qtd}/{limite}</span>
                    <span style="font-size: 12px; font-weight: bold; color: {cor_borda};">{icone}</span>
                </div>
            </div>
            """
            cols[j].markdown(html_card, unsafe_allow_html=True)

    st.divider()

    # ==========================================================================
    # 2. FLUXO TURBO: INCLUSÃO IMEDIATA E TELETRANSPORTE
    # ==========================================================================
    st.markdown("### ⚡ Inclusão Imediata (Oficial)")
    with st.expander("➕ Inserir Aluno Novo Manualmente (Sem Ficha Pública)", expanded=False):
        st.info("Como operador, este aluno será cadastrado **diretamente no sistema oficial** (sem passar pela triagem) e você será levado à ficha dele imediatamente.")

        with st.form("form_cadastro_expresso_direto", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            nome_exp = col1.text_input("Nome Completo do Aluno:*", placeholder="Como consta no RG")
            turma_exp_display = col2.selectbox("Alocar na Turma:*", lista_turmas_display)

            c1, c2, c3 = st.columns([1.5, 1, 1.5])
            whats_exp = c1.text_input("WhatsApp:*", placeholder="Ex: 11988887777")
            nasc_exp = c2.date_input("Nascimento:", datetime.date(2000, 1, 1), min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today(), format="DD/MM/YYYY")
            cpf_exp = c3.text_input("CPF (Opcional):", placeholder="Apenas números")

            if st.form_submit_button("🚀 CADASTRAR E ABRIR FICHA", type="primary", use_container_width=True):
                if not nome_exp or not whats_exp:
                    st.error("❌ Por favor, preencha o Nome e o WhatsApp obrigatoriamente!")
                elif "🔴" in turma_exp_display:
                    st.error("❌ Esta turma está LOTADA! Alocação bloqueada para manter a qualidade.")
                else:
                    try:
                        aluno_payload = {
                            "nome": nome_exp.upper().strip(),
                            "turma": mapa_turmas[turma_exp_display],
                            "data_nascimento": str(nasc_exp),
                            "whatsapp": whats_exp.strip(),
                            "cpf": cpf_exp.strip(),
                            "status": "Ativo",
                            "problemas_saude": "Cadastrado via inclusão expressa.",
                            "medicamentos": "A preencher na anamnese."
                        }
                        # Inserção direta no banco OFICIAL
                        res = supabase.table("alunos").insert(aluno_payload).execute()

                        if res.data:
                            novo_aluno = res.data[0]
                            st.success(f"✅ {nome_exp} cadastrado com sucesso!")

                            # MÁGICA: Teletransporte para a ficha!
                            st.session_state.aluno_prontuario = novo_aluno
                            st.session_state.origem_prontuario = "Triagem"
                            st.session_state.menu_atual = "Portal do Aluno"

                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco oficial: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================================================
    # 3. FILA DE ANÁLISE (LISTA DE ESPERA E PENDENTES VIA LINK PÚBLICO)
    # ==========================================================================
    st.markdown("### 📋 Fila de Análise e Matrícula (Cadastros Externos)")

    pendentes = get_pre_cadastros_pendentes()

    if not pendentes:
        st.info("✅ Excelente! A caixa de entrada do MoveRight está limpa. Nenhuma inscrição pendente.")
        return

    st.warning(f"🚨 Você possui **{len(pendentes)}** alunos aguardando alocação ou análise.")

    # ==========================================================================
    # RENDERIZAÇÃO DOS ACORDEÕES (EXPANDERS ORIGINAIS RECUPERADOS)
    # ==========================================================================
    for aluno in pendentes:
        nome = aluno.get('nome', 'Sem Nome')
        data_inscricao = aluno.get('created_at', 'Recente')[:10] 
        whats = aluno.get('whatsapp', 'Não informado')
        status_atual = aluno.get('status', 'Pendente')

        icone_status = "⏳" if status_atual == "Lista de Espera" else "📝"

        with st.expander(f"{icone_status} {nome.upper()} | 📅 Inscrição: {data_inscricao} | [{status_atual.upper()}]"):

            st.markdown("### 🔍 Auditoria de Dados Pessoais")
            c_dados1, c_dados2 = st.columns(2)
            with c_dados1:
                st.write(f"**Nome Completo:** {nome}")
                st.write(f"**CPF:** {aluno.get('cpf', 'N/A')} | **RG:** {aluno.get('rg', 'N/A')}")
                st.write(f"**Data de Nasc.:** {aluno.get('data_nascimento', 'N/A')}")
                st.write(f"**WhatsApp:** {whats}")
                st.write(f"**E-mail:** {aluno.get('email', 'N/A')}")
            with c_dados2:
                st.write(f"**Peso:** {aluno.get('peso', 'N/A')} kg | **Altura:** {aluno.get('altura', 'N/A')} m")
                st.write(f"**Contato Emergência:** {aluno.get('contato_emergencia', 'N/A')}")
                st.write(f"**Opção 1:** {aluno.get('horario_preferencial', 'N/A')} ({aluno.get('dias_preferenciais', 'N/A')})")
                st.write(f"**Opção 2:** {aluno.get('horario_preferencial_2', 'Nenhuma')}")
                st.write(f"**Endereço:** {aluno.get('endereco', 'N/A')}, {aluno.get('bairro', 'N/A')}")

            st.markdown("### ⚠️ Histórico Clínico Declarado")
            st.error(f"**Problemas de Saúde:** {aluno.get('problemas_saude', 'Nenhum declarado')}")
            st.warning(f"**Medicamentos:** {aluno.get('medicamentos', 'Nenhum declarado')}")
            st.info(f"**Restrições Físicas:** {aluno.get('restricoes_fisicas', 'Nenhuma declarada')}")

            st.markdown("---")

            st.markdown("### 📎 Conferência de Documentação Legal")
            col_rg, col_rec, col_ate = st.columns(3)

            with col_rg:
                st.info("📄 **1. Identidade (RG/CPF)**")
                url_rg = aluno.get('url_rg')
                if url_rg:
                    renderizar_documento_com_rotacao(url_rg, f"tri_rg_{aluno.get('id','')}")
                else:
                    st.error("❌ RG não enviado.")

            with col_rec:
                st.warning("💊 **2. Receituário Médico**")
                url_rec = aluno.get('url_receituario')
                if url_rec:
                    renderizar_documento_com_rotacao(url_rec, f"tri_rec_{aluno.get('id','')}")
                else:
                    st.markdown("<p style='color:#64748B;'>Nenhuma receita anexada.</p>", unsafe_allow_html=True)

            with col_ate:
                st.success("🏥 **3. Atestado Médico**")
                url_ate = aluno.get('url_atestado_medico')
                if url_ate:
                    renderizar_documento_com_rotacao(url_ate, f"tri_ate_{aluno.get('id','')}")
                else:
                    st.error("❌ Atestado em falta! (Bloqueante)")

            st.markdown("---")

            # ==========================================
            # ⚖️ AÇÃO FINAL: MATRICULAR, ESPERAR OU REJEITAR
            # ==========================================
            st.markdown("### ⚖️ Decisão da Coordenação")

            c_turma, c_aprovar, c_espera, c_rejeitar = st.columns([2.5, 1.5, 1.5, 1.5], vertical_alignment="bottom")

            with c_turma:
                # O Admin escolhe a turma real baseada no termômetro
                turma_escolhida_display = st.selectbox(
                    "Alocar na Turma:", 
                    options=lista_turmas_display, 
                    key=f"turma_{aluno['id']}"
                )
                turma_real_salvar = mapa_turmas[turma_escolhida_display]

            with c_aprovar:
                if st.button("✅ MATRICULAR", type="primary", use_container_width=True, key=f"btn_ap_{aluno['id']}"):
                    if not url_ate:
                        st.error("Não é possível matricular sem Atestado de Aptidão!")
                    elif "🔴" in turma_escolhida_display:
                        st.error("Esta turma está LOTADA! Alocação bloqueada para manter a qualidade.")
                    else:
                        with st.spinner("A processar matrícula..."):
                            sucesso, msg = aprovar_inscricao_aluno(aluno['id'], turma_real_salvar)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

            with c_espera:
                if status_atual != "Lista de Espera":
                    if st.button("⏳ ESPERA", use_container_width=True, key=f"btn_esp_{aluno['id']}", help="Colocar aluno na Lista de Espera por falta de vagas"):
                        if mover_para_espera(aluno['id'], nome):
                            st.rerun()
                else:
                    st.button("⏳ Em Espera", disabled=True, use_container_width=True, key=f"btn_esp_dis_{aluno['id']}")

            with c_rejeitar:
                if st.button("❌ RECUSAR", type="secondary", use_container_width=True, key=f"btn_rej_{aluno['id']}", help="Arquivar por falta de documentos ou perfil inadequado"):
                    sucesso, msg = rejeitar_inscricao_aluno(aluno['id'])
                    if sucesso:
                        st.toast("Inscrição arquivada.", icon="🗑️")
                        st.rerun()
                    else:
                        st.error(msg)