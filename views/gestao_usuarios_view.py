import streamlit as st
from database import listar_usuarios_sistema, atualizar_usuario_sistema, excluir_usuario_sistema


def _badge_ativo(ativo):
    if ativo is False:
        return "<span style='background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>⛔ Inativo</span>"
    return "<span style='background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;'>✅ Ativo</span>"


def tela_gestao_usuarios():
    st.markdown("""
        <div style='background:#F0FDF4;border-left:4px solid #16A34A;
                    padding:12px 16px;border-radius:6px;margin-bottom:18px;'>
            <strong style='color:#14532D;'>👥 Gestão de Logins</strong><br>
            <span style='color:#15803D;font-size:13px;'>
                Edite nome, e-mail ou senha de qualquer conta, inative acessos temporariamente
                ou exclua permanentemente. Apenas o SuperAdmin tem acesso a esta tela.
            </span>
        </div>
    """, unsafe_allow_html=True)

    email_session = st.session_state.get("email", "")
    edit_id = st.session_state.get("_usr_edit_id")

    usuarios = listar_usuarios_sistema()

    # ── Aviso: coluna "ativo" pode não existir ainda ──────────────────────
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

    # ══════════════════════════════════════════════════════════════════════
    # EDITOR
    # ══════════════════════════════════════════════════════════════════════
    if edit_id:
        u = next((x for x in usuarios if x["id"] == edit_id), None)
        if u is None:
            st.error("Usuário não encontrado.")
            st.session_state.pop("_usr_edit_id", None)
            st.rerun()

        st.markdown(f"### ✏️ Editando: **{u['nome']}**")

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
            novo_ativo = st.toggle("Conta ativa", value=bool(ativo_atual),
                                   help="Desative para bloquear o acesso sem excluir o cadastro.")

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
                    "nome":  novo_nome.strip(),
                    "email": novo_email.strip().lower(),
                    "ativo": novo_ativo,
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
    # LISTAGEM
    # ══════════════════════════════════════════════════════════════════════
    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
        return

    col_h1, col_h2, col_h3, col_h4 = st.columns([3, 2, 1.5, 2])
    col_h1.markdown("**Nome**")
    col_h2.markdown("**E-mail**")
    col_h3.markdown("**Status**")
    col_h4.markdown("**Ações**")
    st.markdown("<hr style='margin:4px 0 8px 0;'>", unsafe_allow_html=True)

    for u in usuarios:
        uid   = u["id"]
        ativo = u.get("ativo", True)
        if ativo is None:
            ativo = True
        is_me = u.get("email", "").strip().lower() == email_session.strip().lower()

        c1, c2, c3, c4 = st.columns([3, 2, 1.5, 2])
        c1.markdown(f"{'**[Você]** ' if is_me else ''}{u.get('nome','—')}")
        c2.markdown(f"<small>{u.get('email','—')}</small>", unsafe_allow_html=True)
        c3.markdown(_badge_ativo(ativo), unsafe_allow_html=True)

        with c4:
            ba, bb, bc = st.columns(3)

            if ba.button("✏️", key=f"usr_ed_{uid}", help="Editar nome / e-mail / senha"):
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

        # ── Confirmar exclusão ────────────────────────────────────────────
        if st.session_state.get(f"_usr_conf_del_{uid}"):
            st.warning(
                f"⚠️ Excluir **{u.get('nome','—')}** ({u.get('email','—')}) permanentemente? "
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
