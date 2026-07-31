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
    email_session = st.session_state.get("email", "").strip().lower()

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

        # Checkboxes por grupo
        _grupos = [
            ("🗂️ Menus Principais", [
                ("principal",     "🏠 Início"),
                ("frequencia",    "✅ Frequência"),
                ("portal_aluno",  "🩺 Portal do Aluno"),
                ("relatorios_bi", "📊 Relatórios & BI"),
            ]),
            ("🎯 Gestor", [
                ("gestor",             "🎯 Gestor (acesso ao menu)"),
                ("gestor_radar",       "💙 Radar"),
                ("gestor_satisfacao",  "⭐ Satisfação"),
                ("gestor_emergencia",  "🚨 Emergência"),
            ]),
        ]

        _novas_perms = {}
        for _grupo_nome, _itens in _grupos:
            st.markdown(
                f"<span style='font-weight:700;color:#1E3A8A;font-size:13px;'>"
                f"{_grupo_nome}</span>",
                unsafe_allow_html=True,
            )
            _cols_perm = st.columns(4)
            for _pi, (_chave, _label) in enumerate(_itens):
                _val_atual = _perm_atual.get(_chave, True)  # default = liberado
                _novo_val = _cols_perm[_pi % 4].checkbox(
                    _label,
                    value=_val_atual,
                    key=f"perm_{_uid_perm}_{_chave}",
                )
                _novas_perms[_chave] = _novo_val
            st.markdown("<br>", unsafe_allow_html=True)

        # Aviso se Gestor desabilitado mas sub-abas habilitadas
        if not _novas_perms.get("gestor", True) and any(
            _novas_perms.get(k, True)
            for k in ["gestor_radar", "gestor_satisfacao", "gestor_emergencia"]
        ):
            st.caption(
                "ℹ️ Se 'Gestor (acesso ao menu)' estiver desmarcado, as sub-abas "
                "não aparecem mesmo que estejam marcadas."
            )

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
