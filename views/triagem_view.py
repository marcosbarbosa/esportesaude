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
    registrar_log_matricula_doc,
    get_todas_turmas,
    get_ocupacao_turmas,
    verificar_aluno_existente,
    buscar_aluno_por_id,
    atualizar_perfil_aluno_dict,
    supabase,
    upload_midia,
    _com_fonetica,
    _inv_alunos,
)

# ==============================================================================
# APROVEITAMENTO DE DADOS: pre_cadastros → alunos (inscrição duplicata)
# ==============================================================================
_GRUPOS_APROVEITAMENTO = [
    ("📱 Contato", [
        ("whatsapp",   "whatsapp",   "WhatsApp"),
        ("email",      "email",      "E-mail"),
        ("contato_emergencia", "contato_emergencia", "Contato de Emergência"),
    ]),
    ("🪪 Documentos", [
        ("cpf", "cpf", "CPF"),
        ("rg",  "rg",  "RG"),
    ]),
    ("🏠 Endereço", [
        ("endereco",    "endereco",    "Endereço"),
        ("complemento", "complemento", "Complemento"),
        ("bairro",      "bairro",      "Bairro"),
        ("cep",         "cep",         "CEP"),
    ]),
    ("⚖️ Biometria", [
        ("peso",   "peso",   "Peso (kg)"),
        ("altura", "altura", "Altura (m)"),
    ]),
    ("🏥 Saúde", [
        ("problemas_saude",         "problemas_saude",         "Problemas de Saúde"),
        ("medicamentos",            "medicamentos",            "Medicamentos em Uso"),
        ("alergia_medicamento",     "alergia_medicamento",     "Alergia a Medicamentos"),
        ("restricoes_fisicas",      "restricoes_fisicas",      "Restrições Físicas"),
        ("pratica_outras_atividades","pratica_outras_atividades","Pratica Outras Atividades"),
        ("incomodo_atividades",     "incomodo_atividades",     "Incômodo nas Atividades"),
    ]),
    ("🏘️ Socioeconômico", [
        ("naturalidade",          "naturalidade",          "Naturalidade"),
        ("sexo",                  "sexo",                  "Sexo"),
        ("estado_civil",          "estado_civil",          "Estado Civil"),
        ("nome_conjuge",          "nome_conjuge",          "Nome do Cônjuge"),
        ("grau_instrucao",        "grau_instrucao",        "Grau de Instrução"),
        ("residentes_moradia",    "residentes_moradia",    "Moradores na Residência"),
        ("aposentado",            "aposentado",            "Aposentado(a)?"),
        ("fonte_renda",           "fonte_renda",           "Fonte de Renda"),
        ("renda_familiar",        "renda_familiar",        "Renda Familiar"),
        ("interesse_voluntariado","interesse_voluntariado","Interesse em Voluntariado"),
        ("areas_voluntariado",    "areas_voluntariado",    "Áreas de Voluntariado"),
    ]),
    ("📎 Documentos Digitais", [
        ("url_foto",           "url_foto",           "Foto de Perfil"),
        ("url_rg",             "url_rg",             "Imagem do RG"),
        ("url_receituario",    "url_receituario",    "Receituário Médico"),
        ("url_atestado_medico","url_atestado_medico","Atestado Médico"),
    ]),
]


def _lv(v):
    """Limpa valor para comparação/exibição."""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def _cor_linha(val_pre, val_aluno):
    if not _lv(val_pre):
        return "#F8F8F8"
    if not _lv(val_aluno):
        return "#FFF8E1"
    if _lv(val_pre) == _lv(val_aluno):
        return "#F0FFF4"
    return "#FFF3E0"


def _tela_aproveitamento_duplicata(pre: dict, aluno_id: str, pre_id: str):
    """Renderiza o painel de aproveitamento de dados campo-a-campo.
    Fonte = pre_cadastros (ficha nova do aluno).
    Receptor = registro em alunos (cadastro existente que ficará ativo).
    """
    aluno = buscar_aluno_por_id(aluno_id)
    if not aluno:
        st.error("Não foi possível carregar o cadastro existente.")
        return

    st.markdown(
        f"""
        <div style='background:#EFF6FF;border-left:4px solid #2563EB;
                    padding:12px 16px;border-radius:6px;margin-bottom:12px;'>
            <strong style='color:#1E40AF;'>📥 Aproveitamento de dados da nova ficha</strong><br>
            <span style='color:#1D4ED8;font-size:13px;'>
                <b>Fonte (nova ficha):</b> {_lv(pre.get('nome','—'))} &nbsp;|&nbsp;
                <b>Receptor (cadastro ativo):</b> {_lv(aluno.get('nome','—'))}
                (turma <b>{_lv(aluno.get('turma','—'))}</b>)<br>
                Marque os campos que deseja copiar da nova ficha para o cadastro existente.
                O registro antigo NÃO será excluído.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Legenda de cores
    leg = st.columns(4)
    leg[0].markdown(
        "<span style='background:#FFF8E1;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "🟡 Receptor vazio</span>", unsafe_allow_html=True
    )
    leg[1].markdown(
        "<span style='background:#FFF3E0;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "🟠 Valores diferentes</span>", unsafe_allow_html=True
    )
    leg[2].markdown(
        "<span style='background:#F0FFF4;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "🟢 Iguais</span>", unsafe_allow_html=True
    )
    leg[3].markdown(
        "<span style='background:#F8F8F8;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "⚪ Sem valor na ficha nova</span>", unsafe_allow_html=True
    )

    campos_selecionados = {}

    for grupo_label, campos in _GRUPOS_APROVEITAMENTO:
        with st.expander(grupo_label, expanded=True):
            h_cb, h_campo, h_nova, h_atual = st.columns([0.5, 2, 3, 3])
            h_cb.markdown("**✅**")
            h_campo.markdown("**Campo**")
            h_nova.markdown("**📤 Nova ficha** *(formulário público)*")
            h_atual.markdown(f"**📥 Cadastro ativo** *({_lv(aluno.get('nome','—'))})*")
            st.markdown("<hr style='margin:2px 0 6px 0;border-color:#e0e0e0'>",
                        unsafe_allow_html=True)

            for campo_pre, campo_aluno, label in campos:
                # Para whatsapp, considera também o campo "celular"
                if campo_pre == "whatsapp":
                    val_pre = _lv(pre.get("whatsapp") or pre.get("celular"))
                else:
                    val_pre = _lv(pre.get(campo_pre))
                val_aluno = _lv(aluno.get(campo_aluno))
                cor = _cor_linha(val_pre, val_aluno)

                desabilitado = not val_pre
                pre_selecionar = bool(val_pre) and not val_aluno

                c_cb, c_campo, c_nova, c_atual = st.columns([0.5, 2, 3, 3])

                with c_cb:
                    sel = st.checkbox(
                        f"Copiar {label}",
                        value=pre_selecionar,
                        key=f"aprov_cb_{pre_id}_{campo_aluno}",
                        disabled=desabilitado,
                        label_visibility="collapsed",
                    )
                campos_selecionados[campo_aluno] = sel and not desabilitado

                with c_campo:
                    st.markdown(
                        f"<div style='background:{cor};padding:4px 8px;"
                        f"border-radius:4px;font-size:13px;font-weight:600'>{label}</div>",
                        unsafe_allow_html=True,
                    )
                with c_nova:
                    _exibir_campo_aproveitamento(val_pre, cor, campo_aluno, "nova")
                with c_atual:
                    _exibir_campo_aproveitamento(val_aluno, cor, campo_aluno, "atual")

    # ── Botão de aplicar ──────────────────────────────────────────────────────
    st.markdown("---")
    a_copiar = {k: pre.get("whatsapp") or pre.get("celular")
                if k == "whatsapp" else pre.get(
                    [c[0] for c in sum([g[1] for g in _GRUPOS_APROVEITAMENTO], [])
                     if c[1] == k][0]
                )
                for k, v in campos_selecionados.items() if v}
    # forma mais limpa de montar o payload:
    pre_campo_map = {}
    for _, campos in _GRUPOS_APROVEITAMENTO:
        for cp, ca, _ in campos:
            pre_campo_map[ca] = cp
    a_copiar = {}
    for campo_aluno, selecionado in campos_selecionados.items():
        if not selecionado:
            continue
        campo_pre_k = pre_campo_map.get(campo_aluno, campo_aluno)
        if campo_pre_k == "whatsapp":
            val = pre.get("whatsapp") or pre.get("celular")
        else:
            val = pre.get(campo_pre_k)
        if val:
            a_copiar[campo_aluno] = val

    n = len(a_copiar)
    if n:
        st.success(f"**{n} campo(s)** marcado(s) para copiar: `{'`, `'.join(a_copiar.keys())}`")
    else:
        st.info("Nenhum campo marcado. Selecione os campos que deseja atualizar no cadastro existente.")

    ca1, ca2 = st.columns([2, 1])
    with ca1:
        if st.button(
            "✅ Aplicar campos selecionados no cadastro existente",
            type="primary",
            use_container_width=True,
            disabled=n == 0,
            key=f"btn_aprov_aplicar_{pre_id}",
        ):
            ok, msg = atualizar_perfil_aluno_dict(aluno_id, a_copiar)
            if ok:
                # Arquiva o pre_cadastro como aproveitado (não insere novo aluno)
                supabase.table("pre_cadastros").update({"status": "Aprovado"}).eq(
                    "id", str(pre_id)
                ).execute()
                get_pre_cadastros_pendentes.clear()

                # Limpa TODAS as caches do Portal do Aluno (CRM + lista geral)
                # para que a ficha aberta depois mostre os dados atualizados.
                try:
                    from views.prontuario_dashboard import (
                        carregar_dados_crm_avaliacoes_senior,
                        obter_todos_alunos_cache,
                    )
                    carregar_dados_crm_avaliacoes_senior.clear()
                    obter_todos_alunos_cache.clear()
                except Exception:
                    pass
                st.session_state["_force_reload_crm"] = True

                # Busca o cadastro já atualizado para mostrar ao operador
                aluno_novo = buscar_aluno_por_id(aluno_id)
                campos_verificados = []
                if aluno_novo:
                    for campo, valor_enviado in a_copiar.items():
                        valor_atual = _lv(aluno_novo.get(campo, ""))
                        campos_verificados.append(
                            f"**{campo}**: {valor_atual or '—'}"
                        )

                st.success(
                    f"✅ **{n} campo(s)** gravados no cadastro de "
                    f"**{_lv(aluno.get('nome','—'))}**. "
                    "A ficha da nova inscrição foi arquivada."
                )
                if campos_verificados:
                    st.markdown(
                        "📋 **Dados confirmados no banco:**  \n"
                        + "  \n".join(campos_verificados)
                    )
                st.session_state.pop(f"_aprov_{pre_id}", None)
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"Erro ao atualizar: {msg}")
    with ca2:
        if st.button(
            "✖ Cancelar",
            use_container_width=True,
            key=f"btn_aprov_cancel_{pre_id}",
        ):
            st.session_state.pop(f"_aprov_{pre_id}", None)
            st.rerun()


def _exibir_campo_aproveitamento(valor, cor, campo, sufixo):
    """Renderiza célula de valor na tabela de aproveitamento."""
    if campo.startswith("url_") and valor:
        try:
            st.image(valor, width=60)
        except Exception:
            st.markdown(
                f"<div style='background:{cor};padding:4px 8px;"
                f"border-radius:4px;font-size:11px'>{valor[:40]}…</div>",
                unsafe_allow_html=True,
            )
    else:
        exibir = valor if valor else "—"
        st.markdown(
            f"<div style='background:{cor};padding:4px 8px;"
            f"border-radius:4px;font-size:12px'>{exibir}</div>",
            unsafe_allow_html=True,
        )


def _salvar_doc_pre_cadastro(pre_id: str, campo: str, arquivo) -> tuple[bool, str]:
    """
    Faz upload do arquivo e salva a URL no campo indicado de pre_cadastros.
    Retorna (sucesso, mensagem).
    """
    try:
        b = arquivo.getvalue()
        nome = arquivo.name
        mime = arquivo.type
        url = upload_midia(b, nome, mime)
        if not url:
            return False, "Falha no upload — verifique o bucket 'diario_midias_imbra' no Supabase."
        supabase.table("pre_cadastros").update({campo: url}).eq("id", str(pre_id)).execute()
        get_pre_cadastros_pendentes.clear()
        return True, url
    except Exception as e:
        return False, str(e)

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
                        nome_norm = nome_exp.upper().strip()
                        existente = verificar_aluno_existente(
                            nome_norm, str(nasc_exp), cpf_exp.strip()
                        )
                        if existente:
                            st.error(
                                f"⚠️ '{nome_norm}' já está cadastrado(a) "
                                f"(turma {existente.get('turma') or '—'}, status {existente.get('status') or '—'}). "
                                "Cadastro cancelado para não criar duplicado. "
                                "Abra a ficha do aluno existente ou use 'Unificar Alunos' se precisar."
                            )
                            st.stop()
                        aluno_payload = {
                            "nome": nome_norm,
                            "turma": mapa_turmas[turma_exp_display],
                            "data_nascimento": str(nasc_exp),
                            "whatsapp": whats_exp.strip(),
                            "cpf": cpf_exp.strip(),
                            "status": "Ativo",
                            "problemas_saude": "Cadastrado via inclusão expressa.",
                            "medicamentos": "A preencher na anamnese."
                        }
                        # Inserção direta no banco OFICIAL
                        res = supabase.table("alunos").insert(_com_fonetica(aluno_payload)).execute()

                        if res.data:
                            novo_aluno = res.data[0]
                            _inv_alunos()
                            st.session_state["_force_reload_crm"] = True
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

    if st.session_state.get("_matricula_audit_fail"):
        st.error(st.session_state.pop("_matricula_audit_fail"))

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

        if status_atual == "Lista de Espera":
            icone_status = "⏳"
        elif status_atual == "Duplicata":
            icone_status = "⚠️"
        else:
            icone_status = "📝"

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

            _aid = str(aluno.get('id', ''))
            url_rg  = aluno.get('url_rg')
            url_rec = aluno.get('url_receituario')
            url_ate = aluno.get('url_atestado_medico')

            col_rg, col_rec, col_ate = st.columns(3)

            # ── 1. RG ────────────────────────────────────────────────────────
            with col_rg:
                st.markdown("**📄 1. Identidade (RG/CPF)**")
                if url_rg:
                    st.success("✅ Documento recebido")
                    renderizar_documento_com_rotacao(url_rg, f"tri_rg_{_aid}")
                else:
                    st.error("❌ RG não enviado")
                    arq_rg = st.file_uploader(
                        "Adicionar RG agora",
                        type=["jpg","jpeg","png","pdf"],
                        key=f"up_rg_{_aid}",
                    )
                    if arq_rg:
                        with st.spinner("Enviando RG…"):
                            ok, resultado = _salvar_doc_pre_cadastro(_aid, "url_rg", arq_rg)
                        if ok:
                            st.success("✅ RG salvo!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(f"Erro: {resultado}")

            # ── 2. Receituário (opcional) ─────────────────────────────────────
            with col_rec:
                st.markdown("**💊 2. Receituário Médico**")
                if url_rec:
                    st.success("✅ Documento recebido")
                    renderizar_documento_com_rotacao(url_rec, f"tri_rec_{_aid}")
                else:
                    st.caption("Nenhuma receita anexada.")
                    arq_rec = st.file_uploader(
                        "Adicionar Receituário",
                        type=["jpg","jpeg","png","pdf"],
                        key=f"up_rec_{_aid}",
                    )
                    if arq_rec:
                        with st.spinner("Enviando Receituário…"):
                            ok, resultado = _salvar_doc_pre_cadastro(_aid, "url_receituario", arq_rec)
                        if ok:
                            st.success("✅ Receituário salvo!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(f"Erro: {resultado}")

            # ── 3. Atestado (bloqueante para matrícula) ───────────────────────
            with col_ate:
                st.markdown("**🏥 3. Atestado Médico *(obrigatório)***")
                if url_ate:
                    st.success("✅ Documento recebido")
                    renderizar_documento_com_rotacao(url_ate, f"tri_ate_{_aid}")
                else:
                    st.error("❌ Atestado em falta — bloqueante para matrícula!")
                    arq_ate = st.file_uploader(
                        "Adicionar Atestado agora",
                        type=["jpg","jpeg","png","pdf"],
                        key=f"up_ate_{_aid}",
                    )
                    if arq_ate:
                        with st.spinner("Enviando Atestado…"):
                            ok, resultado = _salvar_doc_pre_cadastro(_aid, "url_atestado_medico", arq_ate)
                        if ok:
                            st.success("✅ Atestado salvo! Matrícula liberada.")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(f"Erro: {resultado}")

            st.markdown("---")

            # ==========================================
            # ⚖️ AÇÃO FINAL: MATRICULAR, ESPERAR OU REJEITAR
            # ==========================================
            st.markdown("### ⚖️ Decisão da Coordenação")

            # Documentos obrigatórios em falta (RG e Atestado de Aptidão)
            docs_faltantes = []
            if not url_rg:
                docs_faltantes.append("RG")
            if not url_ate:
                docs_faltantes.append("Atestado de Aptidão")

            def _fazer_matricula(faltantes, lotada=False, forcar=False):
                with st.spinner("A processar matrícula..."):
                    sucesso, msg = aprovar_inscricao_aluno(aluno['id'], turma_real_salvar, forcar=forcar)
                if sucesso:
                    if faltantes or lotada:
                        motivos = list(faltantes)
                        if lotada:
                            motivos.append("turma lotada")
                        log_ok = registrar_log_matricula_doc(
                            aluno['id'], nome, faltantes,
                            st.session_state.get("usuario_nome", "") or "—",
                            turma_real_salvar, lotada,
                        )
                        if log_ok:
                            st.toast(
                                "📝 Log registrado — matrícula forçada: " + ", ".join(motivos),
                                icon="📝",
                            )
                        else:
                            # Matrícula concluída mas a trilha de auditoria falhou: avisar de forma persistente.
                            st.session_state["_matricula_audit_fail"] = (
                                f"⚠️ {nome} foi matriculado(a) com exceções ({', '.join(motivos)}), "
                                "mas o LOG DE AUDITORIA FALHOU. Registre manualmente e verifique a conexão."
                            )
                    st.session_state["_force_reload_crm"] = True
                    st.session_state["_force_reload_freq"] = True
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)

            # ── Banner especial para inscrições bloqueadas por duplicata ─────
            if status_atual == "Duplicata":
                _aid = str(aluno["id"])
                existente_dup = verificar_aluno_existente(
                    nome,
                    aluno.get("data_nascimento"),
                    aluno.get("cpf"),
                )
                if existente_dup:
                    st.error(
                        f"🔴 **Duplicata detectada.** O sistema encontrou "
                        f"**{existente_dup.get('nome','—')}** "
                        f"(turma **{existente_dup.get('turma') or '—'}**, "
                        f"status **{existente_dup.get('status') or '—'}**) "
                        f"já cadastrado(a) com o mesmo nome/CPF.\n\n"
                        "Escolha uma das opções abaixo:"
                    )
                    cf1, cf2, cf3 = st.columns(3)
                    if cf1.button(
                        "📥 Aproveitar dados",
                        use_container_width=True,
                        key=f"btn_aprov_{_aid}",
                        help="Copia campos da nova ficha para o cadastro já existente.",
                    ):
                        atual = st.session_state.get(f"_aprov_{_aid}", False)
                        st.session_state[f"_aprov_{_aid}"] = not atual
                        st.rerun()
                    if cf2.button(
                        "⚡ Forçar Matrícula",
                        type="primary",
                        use_container_width=True,
                        key=f"force_dup_{_aid}",
                        help="Cria um NOVO cadastro mesmo com nome/CPF similar (pessoa diferente).",
                    ):
                        _fazer_matricula(docs_faltantes, turma_lotada, forcar=True)
                    if cf3.button(
                        "🔁 Tentar novamente",
                        use_container_width=True,
                        key=f"retry_dup_{_aid}",
                        help="Roda a verificação de duplicata novamente.",
                    ):
                        _fazer_matricula(docs_faltantes, turma_lotada, forcar=False)

                    # Painel de aproveitamento (toggle)
                    if st.session_state.get(f"_aprov_{_aid}", False):
                        st.markdown("---")
                        _tela_aproveitamento_duplicata(
                            pre=aluno,
                            aluno_id=str(existente_dup["id"]),
                            pre_id=_aid,
                        )
                else:
                    st.warning(
                        "⚠️ Esta inscrição foi marcada como **Duplicata** anteriormente, "
                        "mas o registro suspeito não está mais localizado. "
                        "Você pode matricular normalmente ou forçar a matrícula."
                    )
                    cf1, cf2 = st.columns(2)
                    if cf1.button(
                        "⚡ Forçar Matrícula",
                        type="primary",
                        use_container_width=True,
                        key=f"force_dup_{_aid}",
                    ):
                        _fazer_matricula(docs_faltantes, turma_lotada, forcar=True)
                    if cf2.button(
                        "🔁 Tentar novamente",
                        use_container_width=True,
                        key=f"retry_dup_{_aid}",
                    ):
                        _fazer_matricula(docs_faltantes, turma_lotada, forcar=False)
                st.markdown("---")

            c_turma, c_aprovar, c_espera, c_rejeitar = st.columns([2.5, 1.5, 1.5, 1.5], vertical_alignment="bottom")

            with c_turma:
                # O Admin escolhe a turma real baseada no termômetro
                # Pré-seleciona a turma salva no formulário de inscrição (se houver)
                _turma_salva = aluno.get("turma") or ""
                _idx_turma = 0
                if _turma_salva:
                    for _i, _disp in enumerate(lista_turmas_display):
                        if mapa_turmas.get(_disp) == _turma_salva:
                            _idx_turma = _i
                            break
                turma_escolhida_display = st.selectbox(
                    "Alocar na Turma:", 
                    options=lista_turmas_display,
                    index=_idx_turma,
                    key=f"turma_{aluno['id']}"
                )
                turma_real_salvar = mapa_turmas[turma_escolhida_display]

            turma_lotada = "🔴" in turma_escolhida_display

            with c_aprovar:
                if st.button("✅ MATRICULAR", type="primary", use_container_width=True, key=f"btn_ap_{aluno['id']}"):
                    if docs_faltantes or turma_lotada:
                        # Não bloqueia: pede confirmação para matricular com exceções
                        st.session_state[f"confirm_mat_{aluno['id']}"] = True
                    else:
                        _fazer_matricula([])

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

            # ── Confirmação: matricular MESMO com exceções (docs/turma lotada) ─
            if st.session_state.get(f"confirm_mat_{aluno['id']}"):
                avisos = []
                if turma_lotada:
                    avisos.append("a **turma está LOTADA** (capacidade excedida)")
                if docs_faltantes:
                    avisos.append("faltam documentos: **" + ", ".join(docs_faltantes) + "**")
                st.warning(
                    "⚠️ **Atenção:** " + " e ".join(avisos)
                    + ". Você pode matricular mesmo assim — será gerado um **log da matrícula** "
                    "com o motivo da exceção."
                )
                cf1, cf2 = st.columns([2, 1])
                if cf1.button(
                    "✅ Matricular mesmo assim (registrar log)",
                    type="primary", use_container_width=True,
                    key=f"force_mat_{aluno['id']}",
                ):
                    st.session_state.pop(f"confirm_mat_{aluno['id']}", None)
                    _fazer_matricula(docs_faltantes, turma_lotada)
                if cf2.button(
                    "Cancelar", use_container_width=True,
                    key=f"cancel_mat_{aluno['id']}",
                ):
                    st.session_state.pop(f"confirm_mat_{aluno['id']}", None)
                    st.rerun()