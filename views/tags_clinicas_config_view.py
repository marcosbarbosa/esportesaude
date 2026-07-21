# ==============================================================================
# 📄 views/tags_clinicas_config_view.py
# 🏷️ CRUD de Tags Clínicas de Saúde — Painel Config (SuperAdmin)
# ==============================================================================
import streamlit as st
from database import get_tags_clinicas, salvar_tag_clinica, excluir_tag_clinica, seed_tags_clinicas_padrao, sincronizar_tags_clinicas

_SQL_CRIACAO = """
-- Cole este SQL no Supabase SQL Editor e execute:

CREATE TABLE IF NOT EXISTS tags_clinicas_sistema (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT NOT NULL,
    icone       TEXT NOT NULL DEFAULT '🏷️',
    cor         TEXT NOT NULL DEFAULT '#6B7280',
    tipo_alerta TEXT NOT NULL DEFAULT 'warning',  -- 'error' | 'warning' | 'info'
    dica_treino TEXT,
    ativo       BOOLEAN NOT NULL DEFAULT true,
    ordem       INT NOT NULL DEFAULT 99,
    criado_em   TIMESTAMPTZ DEFAULT now()
);
"""

_TIPO_LABEL = {"error": "🔴 Vermelho (Grave)", "warning": "🟡 Âmbar (Atenção)", "info": "🔵 Azul (Info)"}
_TIPO_OPTS = list(_TIPO_LABEL.keys())


def _badge(tag: dict) -> str:
    cor = tag.get("cor", "#6B7280")
    icone = tag.get("icone", "🏷️")
    nome = tag.get("nome", "")
    return (
        f"<span style='background:{cor};color:white;padding:3px 12px;"
        f"border-radius:12px;font-size:12px;font-weight:700;'>{icone} {nome}</span>"
    )


def tela_tags_clinicas_config():
    st.markdown("### 🏷️ Tags Clínicas de Saúde")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-top:-8px;margin-bottom:16px;'>"
        "Crie, edite e desative condições de saúde. As tags aparecem na Ficha do Aluno "
        "e como badges no Tablet de Chamada para alertar o professor.</p>",
        unsafe_allow_html=True,
    )

    # ── SQL de criação ─────────────────────────────────────────────────────────
    with st.expander("🗄️ SQL — Criar tabela no Supabase (executar uma vez)", expanded=False):
        st.code(_SQL_CRIACAO, language="sql")
        col_seed, col_sync = st.columns(2)
        if col_seed.button("🌱 Inserir Tags Sugeridas (padrão)", key="seed_tags_btn"):
            ok, msg = seed_tags_clinicas_padrao()
            if ok:
                st.success("✅ Tags padrão inseridas com sucesso!")
                st.rerun()
            else:
                st.warning(f"ℹ️ {msg}")
        if col_sync.button("🔄 Sincronizar / Atualizar todas as tags do sistema", key="sync_tags_btn",
                           help="Insere tags novas (ex: Colesterol) e atualiza as existentes. Não remove tags customizadas."):
            ok, msg = sincronizar_tags_clinicas()
            if ok:
                st.success(f"✅ Sincronização concluída: {msg}")
                st.rerun()
            else:
                st.error(f"❌ Erro: {msg}")

    # ── Carregar tags ───────────────────────────────────────────────────────────
    tags = get_tags_clinicas()

    # ── Formulário de nova tag ─────────────────────────────────────────────────
    with st.expander("➕ Cadastrar nova tag clínica", expanded=not bool(tags)):
        _form_tag(None)

    if not tags:
        st.info(
            "Nenhuma tag cadastrada ainda. Expanda '🗄️ SQL' acima, "
            "crie a tabela, clique em **Inserir Tags Sugeridas** e recarregue."
        )
        return

    # ── Listagem ───────────────────────────────────────────────────────────────
    st.markdown(f"**{len(tags)} tag(s) ativa(s):**")

    for tag in tags:
        _linha_tag(tag)


def _form_tag(tag_existente: dict | None):
    """Renderiza o formulário de criação ou edição de uma tag."""
    prefixo = f"edit_{tag_existente['id']}" if tag_existente else "nova"

    col_n, col_i, col_c = st.columns([3, 1, 1])
    nome = col_n.text_input(
        "Nome da condição:",
        value=tag_existente.get("nome", "") if tag_existente else "",
        key=f"{prefixo}_nome",
        placeholder="Ex: Diabetes Mellitus Tipo II",
    )
    icone = col_i.text_input(
        "Ícone (emoji):",
        value=tag_existente.get("icone", "🏷️") if tag_existente else "🏷️",
        key=f"{prefixo}_icone",
        max_chars=4,
    )
    cor = col_c.color_picker(
        "Cor do badge:",
        value=tag_existente.get("cor", "#6B7280") if tag_existente else "#6B7280",
        key=f"{prefixo}_cor",
    )

    tipo_atual = tag_existente.get("tipo_alerta", "warning") if tag_existente else "warning"
    tipo_idx = _TIPO_OPTS.index(tipo_atual) if tipo_atual in _TIPO_OPTS else 1
    tipo = st.selectbox(
        "Nível de alerta:",
        options=_TIPO_OPTS,
        format_func=lambda x: _TIPO_LABEL[x],
        index=tipo_idx,
        key=f"{prefixo}_tipo",
        help="Define a cor da caixa de alerta na Ficha do Aluno (não afeta a cor do badge).",
    )

    ordem = st.number_input(
        "Ordem de exibição:",
        min_value=1, max_value=999,
        value=int(tag_existente.get("ordem", 99)) if tag_existente else 99,
        step=1,
        key=f"{prefixo}_ordem",
    )

    dica = st.text_area(
        "💡 Dica de exercício / orientação para o professor:",
        value=tag_existente.get("dica_treino", "") if tag_existente else "",
        height=110,
        key=f"{prefixo}_dica",
        placeholder="Ex: Evitar isometria e manobra de Valsalva. Monitorar PA antes/durante/após...",
    )

    # Preview ao vivo
    if nome:
        st.markdown(
            f"Pré-visualização: &nbsp;"
            f"<span style='background:{cor};color:white;padding:3px 12px;"
            f"border-radius:12px;font-size:12px;font-weight:700;'>{icone} {nome}</span>",
            unsafe_allow_html=True,
        )

    label_btn = "💾 Salvar Alterações" if tag_existente else "✅ Cadastrar Tag"
    if st.button(label_btn, key=f"{prefixo}_salvar", type="primary", use_container_width=True):
        if not nome.strip():
            st.error("O nome da condição é obrigatório.")
            return
        payload = {
            "nome": nome.strip(),
            "icone": icone.strip() or "🏷️",
            "cor": cor,
            "tipo_alerta": tipo,
            "ordem": int(ordem),
            "dica_treino": dica.strip() or None,
            "ativo": True,
        }
        if tag_existente:
            payload["id"] = tag_existente["id"]
        ok, msg = salvar_tag_clinica(payload)
        if ok:
            st.success("✅ Tag guardada com sucesso!")
            st.rerun()
        else:
            st.error(f"Erro: {msg}")


def _linha_tag(tag: dict):
    """Renderiza uma linha da listagem com ações inline."""
    tag_id = tag["id"]
    edit_key = f"editando_{tag_id}"

    with st.container(border=True):
        col_badge, col_dica, col_acoes = st.columns([3, 4, 2], vertical_alignment="top")

        with col_badge:
            st.markdown(_badge(tag), unsafe_allow_html=True)
            st.caption(f"Alerta: {_TIPO_LABEL.get(tag.get('tipo_alerta','warning'))} · Ordem: {tag.get('ordem',99)}")

        with col_dica:
            dica = tag.get("dica_treino") or ""
            if dica:
                st.markdown(
                    f"<p style='font-size:12px;color:#475569;margin:0;'>{dica[:180]}{'…' if len(dica)>180 else ''}</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Sem dica de exercício cadastrada.")

        with col_acoes:
            c1, c2 = st.columns(2)
            if c1.button("✏️", key=f"btn_edit_{tag_id}", help="Editar esta tag", use_container_width=True):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
            if c2.button("🗑️", key=f"btn_del_{tag_id}", help="Excluir esta tag", use_container_width=True):
                st.session_state[f"confirm_del_{tag_id}"] = True
                st.rerun()

        # Confirmação de exclusão
        if st.session_state.get(f"confirm_del_{tag_id}"):
            st.warning(
                f"⚠️ Confirma exclusão permanente de **{tag['nome']}**? "
                "Alunos que têm esta tag não serão afetados (o texto fica salvo no banco), "
                "mas a tag não aparecerá mais nas opções."
            )
            cc1, cc2 = st.columns(2)
            if cc1.button("✅ Confirmar exclusão", key=f"del_ok_{tag_id}", type="primary", use_container_width=True):
                ok, msg = excluir_tag_clinica(tag_id)
                if ok:
                    del st.session_state[f"confirm_del_{tag_id}"]
                    st.success("Tag excluída.")
                    st.rerun()
                else:
                    st.error(f"Erro: {msg}")
            if cc2.button("Cancelar", key=f"del_no_{tag_id}", use_container_width=True):
                del st.session_state[f"confirm_del_{tag_id}"]
                st.rerun()

        # Painel de edição inline
        if st.session_state.get(edit_key):
            st.markdown("---")
            _form_tag(tag)
