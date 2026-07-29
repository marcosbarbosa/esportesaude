# ==============================================================================
# 📄 views/voluntariado_config_view.py
# 🤝 CRUD de Ações Voluntariadas — Painel Config (SuperAdmin)
# ==============================================================================
import streamlit as st
from database import (
    get_acoes_voluntariado,
    salvar_acao_voluntariado,
    excluir_acao_voluntariado,
    seed_acoes_voluntariado_padrao,
    seed_vinculos_voluntariado_pdf,
    get_contagem_inscritos_por_acao,
)

_SQL_CRIACAO = """
-- Cole este SQL no Supabase SQL Editor e execute (UMA VEZ):

CREATE TABLE IF NOT EXISTS acoes_voluntariado (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT NOT NULL,
    descricao   TEXT,
    area        TEXT NOT NULL DEFAULT 'Geral',
    icone       TEXT NOT NULL DEFAULT '🤝',
    cor         TEXT NOT NULL DEFAULT '#059669',
    ativa       BOOLEAN NOT NULL DEFAULT true,
    ordem       INT NOT NULL DEFAULT 99,
    criado_em   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aluno_acoes_voluntariado (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id        TEXT NOT NULL,
    acao_id         UUID NOT NULL REFERENCES acoes_voluntariado(id) ON DELETE CASCADE,
    data_inscricao  DATE DEFAULT CURRENT_DATE,
    obs             TEXT,
    criado_em       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(aluno_id, acao_id)
);

CREATE INDEX IF NOT EXISTS idx_aluno_acoes_aluno_id ON aluno_acoes_voluntariado (aluno_id);
CREATE INDEX IF NOT EXISTS idx_aluno_acoes_acao_id  ON aluno_acoes_voluntariado (acao_id);

-- Desabilita RLS (sistema usa anon key — padrão de todas as tabelas do IMBRA)
ALTER TABLE acoes_voluntariado          DISABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_acoes_voluntariado    DISABLE ROW LEVEL SECURITY;
"""

_AREAS = ["Geral", "Arte e Cultura", "Educação", "Saúde", "Social",
          "Administração", "Eventos", "Inclusão"]


def _badge_acao(acao: dict) -> str:
    cor   = acao.get("cor", "#059669")
    icone = acao.get("icone", "🤝")
    nome  = acao.get("nome", "")
    area  = acao.get("area", "")
    return (
        f"<span style='background:{cor};color:white;padding:3px 12px;"
        f"border-radius:12px;font-size:12px;font-weight:700;'>{icone} {nome}</span>"
        f"&nbsp;<span style='color:#64748B;font-size:11px;'>{area}</span>"
    )


def tela_voluntariado_config():
    st.markdown("### 🤝 Ações de Voluntariado")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-top:-8px;margin-bottom:16px;'>"
        "Cadastre, edite e desative as ações voluntariadas disponíveis. "
        "Cada ação pode ser vinculada a múltiplos alunos na Ficha do Aluno e no Cadastro.</p>",
        unsafe_allow_html=True,
    )

    # ── SQL de criação ─────────────────────────────────────────────────────────
    with st.expander("🗄️ SQL — Criar tabelas no Supabase (executar uma vez)", expanded=False):
        st.code(_SQL_CRIACAO, language="sql")
        col_s1, col_s2 = st.columns(2)
        if col_s1.button("🌱 Inserir Ações Sugeridas (padrão)", key="seed_acoes_btn",
                         use_container_width=True):
            ok, msg = seed_acoes_voluntariado_padrao()
            if ok:
                st.success("✅ Ações padrão inseridas com sucesso!")
                st.rerun()
            else:
                st.warning(f"ℹ️ {msg}")

        if col_s2.button("🔗 Vincular alunos do PDF", key="seed_vinculos_btn",
                         use_container_width=True,
                         help="Vincula automaticamente os 23 alunos mapeados no PDF de voluntários às suas ações."):
            with st.spinner("Buscando alunos e criando vínculos…"):
                ok, msg = seed_vinculos_voluntariado_pdf()
            if ok:
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"Erro: {msg}")

    # ── Carregar ações e contagens ─────────────────────────────────────────────
    acoes    = get_acoes_voluntariado()
    contagem = get_contagem_inscritos_por_acao()

    # ── Formulário de nova ação ────────────────────────────────────────────────
    with st.expander("➕ Cadastrar nova ação", expanded=not bool(acoes)):
        _form_acao(None)

    if not acoes:
        st.info(
            "Nenhuma ação cadastrada ainda. Expanda '🗄️ SQL' acima, "
            "crie as tabelas, clique em **Inserir Ações Sugeridas** e recarregue."
        )
        return

    # ── Listagem ───────────────────────────────────────────────────────────────
    st.markdown(f"**{len(acoes)} ação(ões) ativa(s):**")
    for acao in acoes:
        _linha_acao(acao, contagem)


def _form_acao(acao_existente: dict | None):
    """Formulário de criação ou edição de uma ação."""
    pfx = f"edit_{acao_existente['id']}" if acao_existente else "nova_acao"

    col_n, col_i, col_c = st.columns([3, 1, 1])
    nome = col_n.text_input(
        "Nome da ação:",
        value=acao_existente.get("nome", "") if acao_existente else "",
        key=f"{pfx}_nome",
        placeholder="Ex: Trabalhos Manuais e Artesanato",
    )
    icone = col_i.text_input(
        "Ícone (emoji):",
        value=acao_existente.get("icone", "🤝") if acao_existente else "🤝",
        key=f"{pfx}_icone",
        max_chars=4,
    )
    cor = col_c.color_picker(
        "Cor do badge:",
        value=acao_existente.get("cor", "#059669") if acao_existente else "#059669",
        key=f"{pfx}_cor",
    )

    area_atual = acao_existente.get("area", "Geral") if acao_existente else "Geral"
    area_idx   = _AREAS.index(area_atual) if area_atual in _AREAS else 0
    col_a, col_o = st.columns([3, 1])
    area = col_a.selectbox(
        "Área temática:",
        options=_AREAS,
        index=area_idx,
        key=f"{pfx}_area",
    )
    ordem = col_o.number_input(
        "Ordem:",
        min_value=1, max_value=999,
        value=int(acao_existente.get("ordem", 99)) if acao_existente else 99,
        step=1,
        key=f"{pfx}_ordem",
    )

    descricao = st.text_area(
        "📝 Descrição da atividade:",
        value=acao_existente.get("descricao", "") if acao_existente else "",
        height=90,
        key=f"{pfx}_desc",
        placeholder="Ex: Confecção de peças manuais, apoio em oficinas de artesanato...",
    )

    # Preview ao vivo
    if nome:
        st.markdown(
            f"Pré-visualização: &nbsp;"
            f"<span style='background:{cor};color:white;padding:3px 12px;"
            f"border-radius:12px;font-size:12px;font-weight:700;'>{icone} {nome}</span>"
            f"&nbsp;<span style='color:#64748B;font-size:11px;'>{area}</span>",
            unsafe_allow_html=True,
        )

    label_btn = "💾 Salvar Alterações" if acao_existente else "✅ Cadastrar Ação"
    if st.button(label_btn, key=f"{pfx}_salvar", type="primary", use_container_width=True):
        if not nome.strip():
            st.error("O nome da ação é obrigatório.")
            return
        payload = {
            "nome":      nome.strip(),
            "icone":     icone.strip() or "🤝",
            "cor":       cor,
            "area":      area,
            "ordem":     int(ordem),
            "descricao": descricao.strip() or None,
            "ativa":     True,
        }
        if acao_existente:
            payload["id"] = acao_existente["id"]
        ok, msg = salvar_acao_voluntariado(payload)
        if ok:
            st.success("✅ Ação guardada com sucesso!")
            st.rerun()
        else:
            st.error(f"Erro: {msg}")


def _linha_acao(acao: dict, contagem: dict):
    """Renderiza uma linha da listagem com ações inline."""
    acao_id  = acao["id"]
    edit_key = f"editando_acao_{acao_id}"
    n_inscritos = contagem.get(acao_id, 0)

    with st.container(border=True):
        col_badge, col_desc, col_acoes = st.columns([3, 4, 2], vertical_alignment="top")

        with col_badge:
            st.markdown(_badge_acao(acao), unsafe_allow_html=True)
            st.caption(f"Ordem: {acao.get('ordem', 99)} · 👤 {n_inscritos} inscritos")

        with col_desc:
            desc = acao.get("descricao") or ""
            if desc:
                st.markdown(
                    f"<p style='font-size:12px;color:#475569;margin:0;'>"
                    f"{desc[:200]}{'…' if len(desc) > 200 else ''}</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Sem descrição cadastrada.")

        with col_acoes:
            c1, c2 = st.columns(2)
            if c1.button("✏️", key=f"btn_edit_acao_{acao_id}",
                         help="Editar esta ação", use_container_width=True):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
            if c2.button("🗑️", key=f"btn_del_acao_{acao_id}",
                         help="Excluir esta ação", use_container_width=True):
                st.session_state[f"confirm_del_acao_{acao_id}"] = True
                st.rerun()

        # Confirmação de exclusão
        if st.session_state.get(f"confirm_del_acao_{acao_id}"):
            st.warning(
                f"⚠️ Confirma exclusão permanente de **{acao['nome']}**? "
                f"Os {n_inscritos} vínculos com alunos também serão removidos."
            )
            cc1, cc2 = st.columns(2)
            if cc1.button("✅ Confirmar exclusão",
                          key=f"del_acao_ok_{acao_id}", type="primary",
                          use_container_width=True):
                ok, msg = excluir_acao_voluntariado(acao_id)
                if ok:
                    del st.session_state[f"confirm_del_acao_{acao_id}"]
                    st.success("Ação excluída.")
                    st.rerun()
                else:
                    st.error(f"Erro: {msg}")
            if cc2.button("Cancelar", key=f"del_acao_no_{acao_id}",
                          use_container_width=True):
                del st.session_state[f"confirm_del_acao_{acao_id}"]
                st.rerun()

        # Painel de edição inline
        if st.session_state.get(edit_key):
            st.markdown("---")
            _form_acao(acao)
