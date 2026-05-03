import streamlit as st
import pandas as pd
from database import (
    buscar_alunos_geral,
    buscar_aluno_por_id,
    atualizar_perfil_aluno_dict,
    excluir_aluno_completo,
    obter_dependencias_lote,
    ADMIN_MASTER,
)

# ==============================================================================
# MAPA DE CAMPOS — (grupo, campo_db, label_exibida)
# ==============================================================================
GRUPOS_CAMPOS = {
    "👤 Identificação": [
        ("nome",             "Nome Completo"),
        ("turma",            "Turma"),
        ("data_nascimento",  "Data de Nascimento"),
        ("status",           "Status"),
    ],
    "🪪 Documentos": [
        ("cpf",     "CPF"),
        ("rg",      "RG"),
    ],
    "🏠 Endereço": [
        ("endereco", "Endereço"),
        ("bairro",   "Bairro"),
        ("cep",      "CEP"),
    ],
    "📱 Contato": [
        ("whatsapp",            "WhatsApp"),
        ("email",               "E-mail"),
        ("contato_emergencia",  "Contato de Emergência"),
    ],
    "⚖️ Biometria": [
        ("peso",   "Peso (kg)"),
        ("altura", "Altura (m)"),
    ],
    "🏥 Saúde": [
        ("problemas_saude",    "Problemas de Saúde"),
        ("medicamentos",       "Medicamentos em Uso"),
        ("restricoes_fisicas", "Restrições Físicas"),
    ],
    "🏘️ Socioeconômico": [
        ("naturalidade",         "Naturalidade"),
        ("sexo",                 "Sexo"),
        ("estado_civil",         "Estado Civil"),
        ("aposentado",           "Aposentado(a)?"),
        ("nome_conjuge",         "Nome do Cônjuge"),
        ("qtd_moradores",        "Moradores na Residência"),
        ("grau_instrucao",       "Grau de Instrução"),
        ("principal_fonte_renda","Principal Fonte de Renda"),
        ("faixa_renda",          "Faixa de Renda da Casa"),
    ],
    "🤝 Voluntariado e Anamnese": [
        ("trabalho_voluntario_interesse", "Interesse em Voluntariado"),
        ("trabalho_voluntario_areas",     "Áreas de Voluntariado"),
        ("anamnese_incomodo_atividade",   "Incômodos na Atividade Física"),
    ],
    "📸 Foto de Perfil": [
        ("url_foto", "Foto de Perfil (URL)"),
    ],
}


def _limpar(v):
    """Retorna string limpa ou '' se vazio/nan."""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def _tem_valor(v):
    return _limpar(v) != ""


def _row_cor(fonte_v, receptor_v):
    """Define a cor de fundo da linha de comparação."""
    if not _tem_valor(fonte_v):
        return "#F8F8F8"     # fonte vazia — cinza claro
    if not _tem_valor(receptor_v):
        return "#FFF8E1"     # receptor vazio, fonte tem valor — amarelo suave
    if _limpar(fonte_v) == _limpar(receptor_v):
        return "#F0FFF4"     # iguais — verde suave
    return "#FFF3E0"         # diferentes — laranja suave


def _render_arquivo_morto(df_todos: pd.DataFrame, email_usuario: str):
    """Seção de gestão dos alunos arquivados (Inativo) com exclusão permanente."""
    df_inativos = df_todos[df_todos["status"] == "Inativo"].copy()

    with st.expander(
        f"🗃️ Arquivo Morto — {len(df_inativos)} aluno(s) arquivado(s)",
        expanded=False,
    ):
        if df_inativos.empty:
            st.success("Nenhum aluno arquivado. O arquivo morto está limpo.")
            return

        st.caption(
            "Estes alunos foram arquivados e não aparecem no fluxo normal do sistema. "
            "Os contadores de dependências abaixo ajudam a decidir com segurança o que excluir."
        )

        # ── Legenda dos badges ─────────────────────────────────────────────────
        st.markdown(
            "<div style='display:flex;gap:16px;margin-bottom:8px;font-size:12px'>"
            "<span>📅 <b>Aulas</b> — presenças registadas</span>"
            "<span>📋 <b>Aval.</b> — avaliações/medições</span>"
            "<span>📄 <b>Ates.</b> — atestados temporários</span>"
            "<span style='margin-left:16px'>"
            "🟢 zero &nbsp; 🟡 poucos &nbsp; 🔴 muitos</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Busca todas as dependências de uma vez (3 queries para N alunos)
        ids_inativos = df_inativos["id"].tolist()
        dependencias = obter_dependencias_lote(ids_inativos)

        def _badge(rotulo, valor, limiar_amarelo=1, limiar_vermelho=10):
            if valor == 0:
                cor_bg, cor_tx = "#DCFCE7", "#166534"
            elif valor < limiar_vermelho:
                cor_bg, cor_tx = "#FEF9C3", "#854D0E"
            else:
                cor_bg, cor_tx = "#FEE2E2", "#991B1B"
            return (
                f"<span style='background:{cor_bg};color:{cor_tx};padding:2px 9px;"
                f"border-radius:10px;font-size:12px;font-weight:700'>"
                f"{rotulo} {valor}</span>"
            )

        for _, row in df_inativos.sort_values("nome").iterrows():
            aluno_id   = str(row.get("id", ""))
            nome       = str(row.get("nome") or "Sem nome").strip()
            turma      = str(row.get("turma") or "—").strip()
            cpf        = str(row.get("cpf") or "—").strip()
            whatsapp   = str(row.get("whatsapp") or "—").strip()
            nascimento = str(row.get("data_nascimento") or "—").strip()

            deps   = dependencias.get(aluno_id, {"frequencias": 0, "avaliacoes": 0, "atestados": 0})
            n_aul  = deps["frequencias"]
            n_aval = deps["avaliacoes"]
            n_ates = deps["atestados"]
            tem_historico = (n_aul + n_aval + n_ates) > 0

            with st.container(border=True):
                c_info, c_deps, c_btn = st.columns([4, 2.5, 1], vertical_alignment="center")

                with c_info:
                    st.markdown(
                        f"**{nome}** &nbsp;"
                        f"<span style='background:#FEE2E2;color:#991B1B;padding:2px 8px;"
                        f"border-radius:10px;font-size:11px'>INATIVO</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"Turma: {turma} &nbsp;|&nbsp; Nasc.: {nascimento} &nbsp;|&nbsp; "
                        f"CPF: {cpf} &nbsp;|&nbsp; WhatsApp: {whatsapp}"
                    )

                with c_deps:
                    alerta = (
                        "⚠️ <b>Atenção:</b> este aluno tem histórico real."
                        if tem_historico else
                        "✅ Sem histórico — seguro excluir."
                    )
                    st.markdown(
                        f"{_badge('📅 Aulas', n_aul, 1, 10)} &nbsp;"
                        f"{_badge('📋 Aval.', n_aval, 1, 5)} &nbsp;"
                        f"{_badge('📄 Ates.', n_ates, 1, 3)}<br>"
                        f"<span style='font-size:11px'>{alerta}</span>",
                        unsafe_allow_html=True,
                    )

                with c_btn:
                    if st.button(
                        "🗑️ Excluir",
                        key=f"btn_abrir_del_{aluno_id}",
                        use_container_width=True,
                        help="Excluir permanentemente este aluno arquivado",
                    ):
                        atual = st.session_state.get(f"del_arq_{aluno_id}", False)
                        st.session_state[f"del_arq_{aluno_id}"] = not atual

                # Painel de confirmação inline
                if st.session_state.get(f"del_arq_{aluno_id}", False):
                    if email_usuario.lower() == ADMIN_MASTER.lower():
                        if tem_historico:
                            st.error(
                                f"⛔ **{nome}** tem {n_aul} aula(s), {n_aval} avaliação(ões) "
                                f"e {n_ates} atestado(s) registados. "
                                "Esses dados serão **permanentemente apagados** junto com o aluno."
                            )
                        else:
                            st.warning(
                                f"Confirme a exclusão de **{nome}**. "
                                "Não há histórico vinculado — operação de baixo risco."
                            )
                        c_conf, c_exec, c_cancel = st.columns([3, 2, 1])
                        confirmacao = c_conf.text_input(
                            "Nome completo para confirmar:",
                            key=f"conf_input_{aluno_id}",
                            placeholder=nome,
                            label_visibility="collapsed",
                        )
                        habilitado = confirmacao.strip().upper() == nome.upper()
                        with c_exec:
                            if st.button(
                                "✅ CONFIRMAR EXCLUSÃO",
                                key=f"btn_del_exec_{aluno_id}",
                                type="primary",
                                use_container_width=True,
                                disabled=not habilitado,
                            ):
                                ok, msg = excluir_aluno_completo(aluno_id, email_usuario)
                                if ok:
                                    st.session_state.pop(f"del_arq_{aluno_id}", None)
                                    st.toast(f"'{nome}' excluído definitivamente.", icon="🗑️")
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with c_cancel:
                            if st.button(
                                "✖",
                                key=f"btn_del_cancel_{aluno_id}",
                                use_container_width=True,
                                help="Cancelar",
                            ):
                                st.session_state[f"del_arq_{aluno_id}"] = False
                                st.rerun()
                    else:
                        st.error("Apenas o administrador mestre pode excluir registos.")


def tela_merge_alunos():
    st.markdown("## 🔀 Mesclagem de Fichas Duplicadas")
    st.caption(
        "Selecione a **Fonte** (cadastro com os dados corretos) e o **Receptor** "
        "(cadastro que ficará ativo). Escolha campo a campo o que será copiado."
    )

    # ── Carrega lista de alunos + dependências em lote ────────────────────────
    df = buscar_alunos_geral(incluir_inativos=True)
    if df.empty:
        st.warning("Nenhum aluno encontrado.")
        return

    todos_ids   = df["id"].tolist()
    todas_deps  = obter_dependencias_lote(todos_ids)   # 3 queries para todos

    def _fmt_created(val):
        """Formata created_at para DD/MM/AAAA ou '?' se inválido."""
        try:
            if not val or str(val).strip().lower() in ("nan", "none", ""):
                return "?"
            import datetime as _dt
            dt = _dt.datetime.fromisoformat(str(val)[:19])
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return "?"

    def _label_aluno(r):
        nome    = r.get("nome") or "Sem nome"
        turma   = r.get("turma") or "?"
        status  = r.get("status", "Ativo")
        aid     = str(r["id"])
        deps    = todas_deps.get(aid, {"frequencias": 0, "avaliacoes": 0, "atestados": 0})
        total   = deps["frequencias"] + deps["avaliacoes"] + deps["atestados"]
        data    = _fmt_created(r.get("created_at", ""))

        prefixo = "🗃️ [INATIVO] " if status == "Inativo" else ""
        hist    = f"📊 {deps['frequencias']} aulas" if total > 0 else "⭕ sem histórico"
        return f"{prefixo}{nome}  [{turma}]  |  {hist}  |  📅 {data}"

    opcoes = {_label_aluno(r): r["id"] for _, r in df.sort_values("nome").iterrows()}
    lista  = list(opcoes.keys())

    # ── Etapa 1: seleção dos dois alunos ──────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 1️⃣  Selecione as duas fichas")
        st.caption(
            "**📊 x aulas** = tem histórico de presenças &nbsp;|&nbsp; "
            "**⭕ sem histórico** = nenhum registo associado, seguro excluir &nbsp;|&nbsp; "
            "**📅 data** = quando o cadastro foi criado no sistema"
        )
        c_f, c_r = st.columns(2)
        with c_f:
            st.markdown("**📤 Fonte** — ficha com os dados mais completos/corretos")
            sel_fonte = st.selectbox(
                "Aluno Fonte:", lista, key="merge_fonte",
                index=None, placeholder="Busque pelo nome..."
            )
        with c_r:
            st.markdown("**📥 Receptor** — ficha que será mantida no sistema")
            sel_receptor = st.selectbox(
                "Aluno Receptor:", lista, key="merge_receptor",
                index=None, placeholder="Busque pelo nome..."
            )

    if not sel_fonte or not sel_receptor:
        st.info("Selecione as duas fichas acima para iniciar a comparação.")
        return

    id_fonte    = opcoes[sel_fonte]
    id_receptor = opcoes[sel_receptor]

    if id_fonte == id_receptor:
        st.error("⚠️ Fonte e Receptor não podem ser o mesmo aluno.")
        return

    fonte    = buscar_aluno_por_id(id_fonte)
    receptor = buscar_aluno_por_id(id_receptor)

    if not fonte or not receptor:
        st.error("Não foi possível carregar os dados de um dos alunos.")
        return

    # ── Painel de diagnóstico rápido ──────────────────────────────────────────
    deps_f = todas_deps.get(str(id_fonte),    {"frequencias": 0, "avaliacoes": 0, "atestados": 0})
    deps_r = todas_deps.get(str(id_receptor), {"frequencias": 0, "avaliacoes": 0, "atestados": 0})
    total_f = deps_f["frequencias"] + deps_f["avaliacoes"] + deps_f["atestados"]
    total_r = deps_r["frequencias"] + deps_r["avaliacoes"] + deps_r["atestados"]

    import datetime as _dt
    def _parse_dt(v):
        try:
            return _dt.datetime.fromisoformat(str(v)[:19])
        except Exception:
            return None

    dt_f = _parse_dt(fonte.get("created_at"))
    dt_r = _parse_dt(receptor.get("created_at"))

    mais_antigo_f  = dt_f and dt_r and dt_f < dt_r
    mais_antigo_r  = dt_f and dt_r and dt_r < dt_f
    mais_hist_f    = total_f >= total_r
    mais_hist_r    = total_r > total_f

    def _card_diag(titulo, role_icon, is_antigo, total_deps, deps, dt):
        tag_ant  = "🕰️ <b>MAIS ANTIGO</b>" if is_antigo else "🆕 mais recente"
        data_str = dt.strftime("%d/%m/%Y") if dt else "?"
        hist_str = (
            f"📅 {deps['frequencias']} aulas &nbsp; "
            f"📋 {deps['avaliacoes']} aval. &nbsp; "
            f"📄 {deps['atestados']} ates."
        ) if total_deps > 0 else "⭕ <b>sem histórico</b> — nenhum registo associado"
        cor_borda = "#1E88E5" if role_icon == "📤" else "#43A047"
        return (
            f"<div style='border:2px solid {cor_borda};border-radius:10px;"
            f"padding:12px 16px;font-size:13px;line-height:1.9'>"
            f"<div style='font-size:15px;font-weight:700;margin-bottom:4px'>"
            f"{role_icon} {titulo}</div>"
            f"📆 Cadastrado em: <b>{data_str}</b> &nbsp;|&nbsp; {tag_ant}<br>"
            f"{hist_str}"
            f"</div>"
        )

    st.markdown("---")
    st.markdown("#### 🔍 Diagnóstico rápido dos dois cadastros")
    cd_f, cd_r = st.columns(2)
    cd_f.markdown(
        _card_diag(_limpar(fonte.get("nome")), "📤", mais_antigo_f, total_f, deps_f, dt_f),
        unsafe_allow_html=True
    )
    cd_r.markdown(
        _card_diag(_limpar(receptor.get("nome")), "📥", mais_antigo_r, total_r, deps_r, dt_r),
        unsafe_allow_html=True
    )

    # Recomendação automática
    if total_f == 0 and total_r > 0:
        st.info(
            "💡 **Sugestão:** A Fonte não tem histórico e o Receptor tem. "
            "Considere inverter: use o cadastro **sem histórico como Fonte** "
            "(para copiar dados) e o **com histórico como Receptor** (para manter)."
        )
    elif total_r == 0 and total_f > 0:
        st.success(
            "✅ **Configuração ideal:** Fonte tem histórico e Receptor não. "
            "Após mesclar, o Receptor herdará os dados da Fonte — e a Fonte "
            "(sem histórico) pode ser excluída com segurança."
        )
    elif total_f == 0 and total_r == 0:
        st.success("✅ Nenhum dos dois tem histórico — qualquer um pode ser excluído sem riscos.")

    # ── Etapa 2: comparativo campo a campo com checkboxes ─────────────────────
    st.markdown("---")
    st.markdown(
        "#### 2️⃣  Comparativo de campos"
        " — marque os que deseja **copiar da Fonte → Receptor**"
    )

    # Legenda de cores
    cols_leg = st.columns(4)
    cols_leg[0].markdown(
        "<span style='background:#FFF8E1;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "🟡 Receptor vazio</span>", unsafe_allow_html=True
    )
    cols_leg[1].markdown(
        "<span style='background:#FFF3E0;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "🟠 Valores diferentes</span>", unsafe_allow_html=True
    )
    cols_leg[2].markdown(
        "<span style='background:#F0FFF4;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "🟢 Valores iguais</span>", unsafe_allow_html=True
    )
    cols_leg[3].markdown(
        "<span style='background:#F8F8F8;padding:2px 8px;border-radius:4px;font-size:12px'>"
        "⚪ Fonte sem valor</span>", unsafe_allow_html=True
    )

    campos_selecionados = {}   # {campo_db: True/False}

    for grupo, campos in GRUPOS_CAMPOS.items():
        with st.expander(grupo, expanded=True):
            # Cabeçalho da tabela
            h_cb, h_campo, h_fonte, h_receptor = st.columns([0.5, 2, 3, 3])
            h_cb.markdown("**✅**")
            h_campo.markdown("**Campo**")
            h_fonte.markdown(f"**📤 Fonte**<br><small>{_limpar(fonte.get('nome'))}</small>",
                             unsafe_allow_html=True)
            h_receptor.markdown(f"**📥 Receptor**<br><small>{_limpar(receptor.get('nome'))}</small>",
                                unsafe_allow_html=True)
            st.markdown(
                "<hr style='margin:2px 0 6px 0;border-color:#e0e0e0'>",
                unsafe_allow_html=True
            )

            for campo_db, label in campos:
                fonte_v    = _limpar(fonte.get(campo_db))
                receptor_v = _limpar(receptor.get(campo_db))
                cor        = _row_cor(fonte_v, receptor_v)

                # Pré-seleciona: fonte tem valor E receptor está vazio
                default_check = _tem_valor(fonte_v) and not _tem_valor(receptor_v)

                c_cb, c_campo, c_fonte, c_receptor = st.columns([0.5, 2, 3, 3])

                # Desabilita checkbox se fonte não tiver valor
                disabled = not _tem_valor(fonte_v)

                with c_cb:
                    selecionado = st.checkbox(
                        f"Copiar {label}",
                        value=default_check,
                        key=f"merge_cb_{campo_db}",
                        disabled=disabled,
                        help="Copiar valor da Fonte para o Receptor",
                        label_visibility="collapsed",
                    )
                campos_selecionados[campo_db] = selecionado and not disabled

                with c_campo:
                    st.markdown(
                        f"<div style='background:{cor};padding:4px 8px;"
                        f"border-radius:4px;font-size:13px;font-weight:600'>{label}</div>",
                        unsafe_allow_html=True
                    )
                with c_fonte:
                    if campo_db == "url_foto" and _tem_valor(fonte_v):
                        try:
                            st.image(fonte_v, width=60)
                        except Exception:
                            st.code(fonte_v[:60] + "...", language=None)
                    else:
                        exibir = fonte_v if _tem_valor(fonte_v) else "—"
                        st.markdown(
                            f"<div style='background:{cor};padding:4px 8px;"
                            f"border-radius:4px;font-size:12px'>{exibir}</div>",
                            unsafe_allow_html=True
                        )
                with c_receptor:
                    if campo_db == "url_foto" and _tem_valor(receptor_v):
                        try:
                            st.image(receptor_v, width=60)
                        except Exception:
                            st.code(receptor_v[:60] + "...", language=None)
                    else:
                        exibir = receptor_v if _tem_valor(receptor_v) else "—"
                        st.markdown(
                            f"<div style='background:{cor};padding:4px 8px;"
                            f"border-radius:4px;font-size:12px'>{exibir}</div>",
                            unsafe_allow_html=True
                        )

    # ── Etapa 3: aplicar mesclagem ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 3️⃣  Aplicar Mesclagem")

    campos_para_copiar = {k for k, v in campos_selecionados.items() if v}

    if campos_para_copiar:
        st.success(f"**{len(campos_para_copiar)} campo(s)** marcado(s) para cópia: "
                   f"`{'`, `'.join(campos_para_copiar)}`")
    else:
        st.warning("Nenhum campo marcado. Selecione ao menos um campo acima.")

    col_btn, col_del = st.columns([2, 2])

    with col_btn:
        if st.button(
            "✅ Aplicar Mesclagem no Receptor",
            type="primary",
            use_container_width=True,
            disabled=len(campos_para_copiar) == 0,
            key="btn_aplicar_merge"
        ):
            if campos_para_copiar:
                payload = {campo: fonte.get(campo) for campo in campos_para_copiar}
                sucesso, msg = atualizar_perfil_aluno_dict(id_receptor, payload)
                if sucesso:
                    st.success(
                        f"✅ {len(payload)} campo(s) copiado(s) com sucesso "
                        f"para **{_limpar(receptor.get('nome'))}**!"
                    )
                    st.session_state.pop("merge_fonte", None)
                    st.session_state.pop("merge_receptor", None)
                    st.rerun()
                else:
                    st.error(f"Erro ao atualizar receptor: {msg}")

    # ── Etapa 4: exclusão da fonte (opcional, apenas SuperAdmin) ──────────────
    with col_del:
        email_usuario = st.session_state.get("usuario_email", "")
        if email_usuario.lower() == ADMIN_MASTER.lower():
            with st.expander("🗑️ Excluir ficha Fonte após mesclagem"):
                st.warning(
                    f"Isso **excluirá permanentemente** a ficha de "
                    f"**{_limpar(fonte.get('nome'))}** e todos os seus registos "
                    f"(presenças, avaliações, atestados). Esta ação é irreversível."
                )
                confirmar = st.text_input(
                    "Digite CONFIRMAR para habilitar a exclusão:",
                    key="merge_confirmar_exclusao"
                )
                if st.button(
                    "🗑️ Excluir Ficha Fonte",
                    type="secondary",
                    use_container_width=True,
                    disabled=(confirmar.strip().upper() != "CONFIRMAR"),
                    key="btn_excluir_fonte"
                ):
                    ok, msg_del = excluir_aluno_completo(id_fonte, email_usuario)
                    if ok:
                        st.success("Ficha Fonte excluída com sucesso.")
                        st.session_state.pop("merge_fonte", None)
                        st.session_state.pop("merge_receptor", None)
                        st.rerun()
                    else:
                        st.error(msg_del)
        else:
            st.info("Apenas o administrador mestre pode excluir a ficha Fonte.")

    # ── Seção separada: Gestão do Arquivo Morto ───────────────────────────────
    st.markdown("---")
    _render_arquivo_morto(df, st.session_state.get("usuario_email", ""))
