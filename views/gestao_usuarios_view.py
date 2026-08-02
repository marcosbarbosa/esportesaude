import streamlit as st
from database import (
    listar_usuarios_sistema, atualizar_usuario_sistema, excluir_usuario_sistema,
    get_menu_permissoes_usuario, set_menu_permissoes_usuario, MENU_CATALOGO,
)

ADMIN_RESTRITO = "marcosbarbosa.am@gmail.com"


def _badge_ativo(ativo):
    if ativo is False:
        return "<span style='background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>⛔ Inativo</span>"
    return "<span style='background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>✅ Ativo</span>"


def _badge_perfil(perfil):
    cores = {
        "SuperAdmin": ("#1D4ED8", "#DBEAFE"),
        "Admin":      ("#6D28D9", "#EDE9FE"),
        "Operador":   ("#0F766E", "#CCFBF1"),
    }
    c_txt, c_bg = cores.get(str(perfil), ("#374151", "#F3F4F6"))
    label = str(perfil or "—")
    return (
        f"<span style='background:{c_bg};color:{c_txt};"
        f"padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>"
        f"{label}</span>"
    )


def tela_gestao_usuarios():
    email_session = (
        st.session_state.get("usuario_email")
        or st.session_state.get("email_usuario")
        or st.session_state.get("email")
        or ""
    ).strip().lower()

    if email_session != ADMIN_RESTRITO.lower():
        st.warning(
            "🔒 Esta área é restrita ao administrador principal do sistema. "
            f"Somente **{ADMIN_RESTRITO}** tem acesso."
        )
        return

    st.markdown("""
        <div style='background:#F0FDF4;border-left:4px solid #16A34A;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#14532D;'>👥 Gestão de Operadores</strong><br>
            <span style='color:#15803D;font-size:13px;'>
                Edite nome, e-mail ou senha dos operadores que fazem login no sistema.
                Inative acessos temporariamente ou exclua permanentemente.
                Apenas o administrador principal tem acesso a esta tela.
            </span>
        </div>
    """, unsafe_allow_html=True)

    edit_id = st.session_state.get("_usr_edit_id")

    usuarios, erro_bd = listar_usuarios_sistema()

    if erro_bd:
        st.error(
            f"❌ Erro ao acessar a tabela `usuarios` no banco de dados:\n\n`{erro_bd}`\n\n"
            "Verifique se a tabela existe e se as colunas estão criadas."
        )
        return

    if usuarios and "ativo" not in usuarios[0]:
        st.warning(
            "⚠️ A coluna `ativo` ainda não existe na tabela `usuarios`. "
            "Execute o SQL abaixo no **Supabase → SQL Editor** para habilitar inativar/reativar:"
        )
        st.code(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo boolean NOT NULL DEFAULT true;",
            language="sql",
        )
        st.markdown("---")

    if usuarios and "perfil" not in usuarios[0]:
        st.info(
            "ℹ️ A coluna `perfil` não existe ainda. Execute no **Supabase → SQL Editor**:\n\n"
            "`ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perfil TEXT DEFAULT 'Operador';`"
        )
        st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # EDITOR
    # ══════════════════════════════════════════════════════════════════════
    if edit_id:
        u = next((x for x in usuarios if x["id"] == edit_id), None)
        if u is None:
            st.error("Operador não encontrado.")
            st.session_state.pop("_usr_edit_id", None)
            st.rerun()

        st.markdown(f"### ✏️ Editando operador: **{u.get('nome', '—')}**")

        with st.form("form_editar_usuario"):
            c1, c2 = st.columns(2)
            novo_nome  = c1.text_input("Nome completo", value=u.get("nome", ""))
            novo_email = c2.text_input("E-mail de login", value=u.get("email", ""))
            nova_senha = st.text_input(
                "Nova senha (deixe em branco para não alterar)",
                value="", type="password",
                help="Mínimo 6 caracteres.",
            )

            ativo_atual = u.get("ativo", True)
            if ativo_atual is None:
                ativo_atual = True
            novo_ativo = st.toggle(
                "Conta ativa", value=bool(ativo_atual),
                help="Desative para bloquear o acesso sem excluir o cadastro.",
            )

            perfil_opcoes = ["Operador", "Admin", "SuperAdmin"]
            perfil_atual = u.get("perfil") or "Operador"
            if perfil_atual not in perfil_opcoes:
                perfil_opcoes.append(perfil_atual)
            novo_perfil = st.selectbox(
                "Perfil de acesso",
                options=perfil_opcoes,
                index=perfil_opcoes.index(perfil_atual),
            )

            st.markdown("---")
            cs1, cs2 = st.columns(2)
            btn_salvar   = cs1.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
            btn_cancelar = cs2.form_submit_button("❌ Cancelar", use_container_width=True)

        if btn_cancelar:
            st.session_state.pop("_usr_edit_id", None)
            st.rerun()

        if btn_salvar:
            if not novo_nome.strip():
                st.error("O nome não pode ficar em branco.")
            elif not novo_email.strip():
                st.error("O e-mail não pode ficar em branco.")
            else:
                payload = {
                    "nome":   novo_nome.strip(),
                    "email":  novo_email.strip().lower(),
                    "ativo":  novo_ativo,
                    "perfil": novo_perfil,
                }
                if nova_senha.strip():
                    if len(nova_senha.strip()) < 6:
                        st.error("A senha precisa ter no mínimo 6 caracteres.")
                        st.stop()
                    payload["senha"] = nova_senha.strip()
                ok, msg = atualizar_usuario_sistema(edit_id, payload)
                if ok:
                    st.success(msg)
                    st.session_state.pop("_usr_edit_id", None)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        return

    # ══════════════════════════════════════════════════════════════════════
    # LISTAGEM EM GRID
    # ══════════════════════════════════════════════════════════════════════
    if not usuarios:
        st.info(
            "Nenhum operador cadastrado ainda. "
            "Crie o primeiro operador pelo formulário de cadastro do sistema."
        )
        return

    st.caption(f"{len(usuarios)} operador(es) cadastrado(s)")

    col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2.5, 2.5, 1.2, 1.2, 1.8])
    col_h1.markdown("**Nome**")
    col_h2.markdown("**E-mail**")
    col_h3.markdown("**Perfil**")
    col_h4.markdown("**Status**")
    col_h5.markdown("**Ações**")
    st.markdown("<hr style='margin:4px 0 8px 0;'>", unsafe_allow_html=True)

    for u in usuarios:
        uid   = u["id"]
        ativo = u.get("ativo", True)
        if ativo is None:
            ativo = True
        is_me = u.get("email", "").strip().lower() == email_session

        c1, c2, c3, c4, c5 = st.columns([2.5, 2.5, 1.2, 1.2, 1.8])
        c1.markdown(f"{'**[Você]** ' if is_me else ''}{u.get('nome', '—')}")
        c2.markdown(f"<small>{u.get('email', '—')}</small>", unsafe_allow_html=True)
        c3.markdown(_badge_perfil(u.get("perfil")), unsafe_allow_html=True)
        c4.markdown(_badge_ativo(ativo), unsafe_allow_html=True)

        with c5:
            ba, bb, bc = st.columns(3)

            if ba.button("✏️", key=f"usr_ed_{uid}", help="Editar dados e senha"):
                st.session_state["_usr_edit_id"] = uid
                st.rerun()

            lbl_tog = "⛔" if ativo else "✅"
            tip_tog = "Inativar acesso" if ativo else "Reativar acesso"
            if bb.button(lbl_tog, key=f"usr_tog_{uid}", help=tip_tog, disabled=is_me):
                ok, msg = atualizar_usuario_sistema(uid, {"ativo": not ativo})
                if ok:
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

            if bc.button("🗑️", key=f"usr_del_{uid}", help="Excluir permanentemente", disabled=is_me):
                st.session_state[f"_usr_conf_del_{uid}"] = True
                st.rerun()

        if st.session_state.get(f"_usr_conf_del_{uid}"):
            st.warning(
                f"⚠️ Excluir **{u.get('nome', '—')}** ({u.get('email', '—')}) permanentemente? "
                "Esta ação não pode ser desfeita."
            )
            cd1, cd2, _ = st.columns([1.5, 1.5, 4])
            if cd1.button("✅ Confirmar exclusão", key=f"usr_del_ok_{uid}", type="primary"):
                ok, msg = excluir_usuario_sistema(uid, email_session)
                if ok:
                    st.session_state.pop(f"_usr_conf_del_{uid}", None)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            if cd2.button("Cancelar", key=f"usr_del_no_{uid}"):
                st.session_state.pop(f"_usr_conf_del_{uid}", None)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # PERMISSÕES DE MENU
    # ══════════════════════════════════════════════════════════════════════
    st.markdown(
        "<hr style='margin:28px 0 18px 0;border-color:#CBD5E1;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style='background:#EFF6FF;border-left:4px solid #1D4ED8;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#1E3A8A;'>🔐 Permissões de Menu</strong><br>
            <span style='color:#1D4ED8;font-size:13px;'>
                Controle quais seções do sistema cada operador pode acessar.
                <b>SuperAdmin</b> sempre tem acesso completo e não aparece aqui.
                Desmarcar um menu o torna invisível para o operador.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filtra usuários que não são o próprio SuperAdmin
    usuarios_filtraveis = [
        u for u in usuarios
        if u.get("email", "").strip().lower() != ADMIN_RESTRITO.lower()
    ]

    if not usuarios_filtraveis:
        st.info("Nenhum operador disponível para configurar permissões.")
    else:
        # Seletor de usuário
        _nomes_perm = {
            f"{u.get('nome', '—')} ({u.get('email', '—')})": u
            for u in usuarios_filtraveis
        }
        _sel_label = st.selectbox(
            "👤 Selecionar operador:",
            options=list(_nomes_perm.keys()),
            key="perm_usr_sel",
        )
        _usr_perm = _nomes_perm[_sel_label]
        _uid_perm = _usr_perm["id"]
        _perm_atual = get_menu_permissoes_usuario(_uid_perm)

        st.markdown(
            f"<small style='color:#64748B;'>Configurando permissões para: "
            f"<strong>{_usr_perm.get('nome','—')}</strong> — "
            f"perfil <em>{_usr_perm.get('perfil','—')}</em></small>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Catálogo de seções com hierarquia pai → filhos ────────────────
        _GRUPOS_PERM = [
            {
                "emoji": "🏠", "titulo": "Início",
                "cor_bg": "#EFF6FF", "cor_bd": "#1D4ED8", "cor_txt": "#1E3A8A",
                "pai": "principal",
                "descricao": "Painel inicial com resumo geral do dia.",
                "filhos": [],
            },
            {
                "emoji": "✅", "titulo": "Frequência",
                "cor_bg": "#F0FDF4", "cor_bd": "#16A34A", "cor_txt": "#14532D",
                "pai": "frequencia",
                "descricao": "Registro de presença nas aulas.",
                "filhos": [
                    ("freq_conf_facial", "📸 Conf. Facial",
                     "Acesso à verificação de presença por foto."),
                ],
            },
            {
                "emoji": "🩺", "titulo": "Portal do Aluno",
                "cor_bg": "#FFF7ED", "cor_bd": "#EA580C", "cor_txt": "#7C2D12",
                "pai": "portal_aluno",
                "descricao": "Cadastros, prontuários e fichas dos alunos.",
                "filhos": [
                    ("portal_prontuario",      "🩺 Prontuário/Ficha",
                     "Ver e editar ficha individual do aluno."),
                    ("portal_ficha_impressao", "🖨️ Imprimir Ficha",
                     "Central de impressão de fichas de matrícula."),
                ],
            },
            {
                "emoji": "📊", "titulo": "Relatórios & BI",
                "cor_bg": "#F5F3FF", "cor_bd": "#7C3AED", "cor_txt": "#4C1D95",
                "pai": "relatorios_bi",
                "descricao": "Relatórios gerenciais, prestação de contas e análise de dados.",
                "filhos": [
                    ("rel_relatorios",    "📋 Relatórios",
                     "Acesso à aba de relatórios (Prestação de Contas etc.)."),
                    ("rel_bi_dashboard",  "📊 BI Dashboard",
                     "Painel analítico com KPIs gerenciais."),
                    ("rel_bi_individual", "👤 BI Individual",
                     "Relatório de evolução individual do aluno."),
                ],
                "sub_grupos": [
                    {
                        "titulo": "↳ Abas dentro de 📋 Relatórios",
                        "cor_bg": "#FAF5FF", "cor_bd": "#A78BFA", "cor_txt": "#5B21B6",
                        "pai_cond": "rel_relatorios",
                        "itens": [
                            ("rel_lista_freq",    "📋 Lista Freq. Oficial",
                             "Frequência por aluno e turma para um período."),
                            ("rel_plan_freq",     "📊 Plan. Frequência",
                             "Planilha de frequência com controle de presenças e faltas."),
                            ("rel_auditoria",     "🔎 Auditoria",
                             "Auditoria de cadastros e documentos pendentes."),
                            ("rel_prestacao_ped", "🏆 Prestação Pedag.",
                             "Relatório pedagógico mensal com exportação Word."),
                            ("rel_avaliacoes",    "🧪 Avaliações",
                             "Alunos pendentes de avaliação física."),
                            ("rel_patologias",    "🧬 Patologias",
                             "Anamnese clínica e condições de saúde registradas."),
                            ("rel_pa_lote",       "🩺 Coleta PA em Lote",
                             "Registro de pressão arterial em lote por turma."),
                        ],
                    }
                ],
            },
            {
                "emoji": "🎯", "titulo": "Gestor",
                "cor_bg": "#FFF1F2", "cor_bd": "#BE123C", "cor_txt": "#881337",
                "pai": "gestor",
                "descricao": "Monitoramento, satisfação e ferramentas de gestão.",
                "filhos": [
                    ("gestor_radar",      "💙 Radar",
                     "Monitoramento e alertas de acolhimento individual."),
                    ("gestor_satisfacao", "⭐ Satisfação",
                     "Pesquisas de satisfação e impacto na saúde."),
                    ("gestor_emergencia", "🚨 Emergência",
                     "Protocolo e contatos de emergência."),
                ],
            },
        ]

        st.markdown(
            "<p style='color:#475569;font-size:12px;margin-bottom:12px;'>"
            "🔑 <b>Acesso ao menu</b> controla a visibilidade do módulo inteiro. "
            "As sub-opções só tomam efeito quando o módulo pai está <em>ativo</em>. "
            "Passe o cursor sobre cada item para ver a descrição."
            "</p>",
            unsafe_allow_html=True,
        )

        _novas_perms = {}
        for _g in _GRUPOS_PERM:
            _chave_pai = _g["pai"]
            _val_pai_atual = _perm_atual.get(_chave_pai, True)
            _n_filhos = len(_g["filhos"])

            # ── Card colorido com título da seção ─────────────────────────
            st.markdown(
                f"<div style='background:{_g['cor_bg']};border-left:4px solid {_g['cor_bd']};"
                f"border-radius:6px;padding:5px 12px;margin-bottom:2px;'>"
                f"<span style='color:{_g['cor_txt']};font-weight:700;font-size:13px;'>"
                f"{_g['emoji']} {_g['titulo']}</span>"
                f"<span style='color:#64748B;font-size:11px;margin-left:10px;'>"
                f"{_g['descricao']}</span></div>",
                unsafe_allow_html=True,
            )

            # ── Checkboxes: pai (col 0) + filhos (cols 1-3) ───────────────
            _cols_g = st.columns(4)

            # Pai
            _val_pai_novo = _cols_g[0].checkbox(
                "🔓 Acesso ao menu",
                value=_val_pai_atual,
                key=f"perm_{_uid_perm}_{_chave_pai}",
                help=f"Habilita ou oculta '{_g['titulo']}' para este operador.",
            )
            _novas_perms[_chave_pai] = _val_pai_novo

            # Filhos (desabilitados automaticamente se pai estiver off)
            for _fi, (_chave_f, _label_f, _tip_f) in enumerate(_g["filhos"]):
                _val_f_atual = _perm_atual.get(_chave_f, True)
                _val_f_novo = _cols_g[_fi + 1].checkbox(
                    _label_f,
                    value=_val_f_atual,
                    key=f"perm_{_uid_perm}_{_chave_f}",
                    disabled=not _val_pai_novo,
                    help=_tip_f if _val_pai_novo else
                         f"⚠️ Habilite '{_g['titulo']}' primeiro para configurar esta sub-opção.",
                )
                # Forçar False se pai estiver desabilitado
                _novas_perms[_chave_f] = _val_f_novo and _val_pai_novo

            # Aviso de dependência apenas se pai desabilitado e há filhos
            if not _val_pai_novo and _n_filhos > 0:
                st.markdown(
                    f"<div style='margin-left:8px;'>"
                    f"<small style='color:#94A3B8;'>"
                    f"↳ As {_n_filhos} sub-opção(ões) acima ficam inativas enquanto "
                    f"'{_g['titulo']}' estiver desabilitado."
                    f"</small></div>",
                    unsafe_allow_html=True,
                )

            # ── Sub-grupos aninhados (3º nível — ex: abas internas de Relatórios) ──
            for _sg in _g.get("sub_grupos", []):
                _pai_cond  = _sg.get("pai_cond")
                _pai_cond_ok = _novas_perms.get(_pai_cond, True) if _pai_cond else True
                _sg_ativo  = _val_pai_novo and _pai_cond_ok
                _sg_itens  = _sg["itens"]

                # Mini-cabeçalho do sub-grupo
                _dica_off = (
                    f" <span style='color:#94A3B8;font-size:10px;'>"
                    f"(habilite '📋 Relatórios' acima para editar)</span>"
                ) if not _sg_ativo else ""
                st.markdown(
                    f"<div style='margin-left:24px;background:{_sg['cor_bg']};"
                    f"border-left:3px solid {_sg['cor_bd']};border-radius:4px;"
                    f"padding:3px 10px;margin-bottom:2px;margin-top:2px;'>"
                    f"<span style='color:{_sg['cor_txt']};font-weight:600;font-size:12px;'>"
                    f"{_sg['titulo']}</span>{_dica_off}</div>",
                    unsafe_allow_html=True,
                )

                # Checkboxes em linhas de 4 (com coluna-espaçador à esquerda)
                _n_sg_rows = (len(_sg_itens) + 3) // 4
                for _sgr in range(_n_sg_rows):
                    _sg_cols = st.columns([0.3, 1, 1, 1, 1])
                    for _sgi, (_chave_sg, _label_sg, _tip_sg) in enumerate(
                        _sg_itens[_sgr * 4 : (_sgr + 1) * 4]
                    ):
                        _val_sg = _perm_atual.get(_chave_sg, True)
                        _val_sg_novo = _sg_cols[_sgi + 1].checkbox(
                            _label_sg,
                            value=_val_sg,
                            key=f"perm_{_uid_perm}_{_chave_sg}",
                            disabled=not _sg_ativo,
                            help=_tip_sg if _sg_ativo else
                                 "Habilite '📊 Relatórios & BI' e '📋 Relatórios' primeiro.",
                        )
                        _novas_perms[_chave_sg] = _val_sg_novo and _sg_ativo

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        _btn_salvar_perm = st.button(
            "💾 Salvar Permissões",
            type="primary",
            key=f"perm_salvar_{_uid_perm}",
            use_container_width=False,
        )
        if _btn_salvar_perm:
            _ok_perm, _msg_perm = set_menu_permissoes_usuario(_uid_perm, _novas_perms)
            if _ok_perm:
                st.success(f"✅ Permissões de **{_usr_perm.get('nome','—')}** salvas com sucesso!")
                # Força recarga do cache de permissões se for o próprio usuário logado
                if st.session_state.get("usuario_id") == _uid_perm:
                    st.session_state.pop("_menu_perms_cache", None)
            else:
                st.error(f"❌ {_msg_perm}")
