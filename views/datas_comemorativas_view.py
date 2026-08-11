# ==============================================================================
# 📄 views/datas_comemorativas_view.py
# 📅 Gestão de Datas Comemorativas Personalizadas da Instituição
# ==============================================================================

import html
import re as _re
import streamlit as st
from database import get_datas_comemorativas_custom, set_datas_comemorativas_custom

_MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

_DIAS_POR_MES = {
    1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
}

_EMOJIS_SUGERIDOS = [
    "🎉", "🎂", "🎊", "🥳", "🏆", "🌟", "💪", "🙌", "🎈", "🎁",
    "🌺", "💝", "🎆", "🪘", "⭐", "🔥", "🏅", "🎖️", "🎗️", "💫",
]

_COR_RE = _re.compile(r'^#[0-9A-Fa-f]{3,8}$')

# Flag de disponibilidade do componente de arrastar
try:
    from streamlit_sortables import sort_items as _sort_items
    _SORTABLES_OK = True
except Exception:
    _SORTABLES_OK = False


def _safe_cor(cor: str) -> str:
    return cor if _COR_RE.match(cor) else "#F59E0B"


def _card_html(emoji: str, nome: str, dia: int, mes: int, cor: str) -> str:
    cor_s = _safe_cor(cor)
    mes_nome = _MESES[mes] if 1 <= mes <= 12 else "?"
    return (
        f"<div style='background:#F8FAFC;border:1.5px solid {cor_s};"
        f"border-radius:10px;padding:10px 14px;margin-bottom:6px;"
        f"display:flex;align-items:center;gap:12px;'>"
        f"<span style='font-size:26px;'>{html.escape(emoji)}</span>"
        f"<div>"
        f"<p style='margin:0;font-weight:800;color:#0A2540;font-size:1rem;'>"
        f"{html.escape(nome)}</p>"
        f"<p style='margin:0;color:#64748B;font-size:0.85rem;'>"
        f"Todo dia {dia} de {html.escape(mes_nome)}"
        f"</p>"
        f"</div>"
        f"<span style='margin-left:auto;background:{cor_s};color:#fff;"
        f"border-radius:20px;padding:3px 12px;font-size:0.78rem;font-weight:700;'>"
        f"{html.escape(cor_s)}</span>"
        f"</div>"
    )


def _label_para_data(dt: dict, idx: int) -> str:
    """Gera rótulo único para o componente de ordenação."""
    emoji = dt.get("emoji", "🎉")
    nome = dt.get("nome", "—")
    dia = dt.get("dia", 1)
    mes = dt.get("mes", 1)
    # Inclui o índice original para garantir unicidade mesmo com nomes iguais
    return f"⠿  {emoji} {nome} — {dia:02d}/{mes:02d}  [{idx}]"


def _reordenar_com_sortables(datas: list) -> list | None:
    """
    Exibe o componente de arrastar. Retorna a lista reordenada se o usuário
    arrastou algo; None se não houve mudança.
    """
    if not _SORTABLES_OK or len(datas) < 2:
        return None

    labels_orig = [_label_para_data(dt, i) for i, dt in enumerate(datas)]

    try:
        labels_novos = _sort_items(
            labels_orig,
            direction="vertical",
            key="sortable_datas_comemorativas",
        )
    except Exception:
        return None

    if labels_novos == labels_orig:
        return None

    # Mapeia rótulo → dict original
    mapa = {label: datas[i] for i, label in enumerate(labels_orig)}
    nova_lista = [mapa[lb] for lb in labels_novos if lb in mapa]

    # Garante que nenhum item foi perdido
    if len(nova_lista) != len(datas):
        return None

    return nova_lista


def _reordenar_com_botoes(datas: list, nova_lista: list) -> bool:
    """
    Fallback: botões ↑/↓ quando streamlit-sortables não está disponível.
    Retorna True se houve mudança e ela foi salva.
    """
    houve_mudanca = False
    for idx, dt in enumerate(datas):
        mes = dt.get("mes", 1)
        emoji = dt.get("emoji", "🎉")
        nome = dt.get("nome", "—")
        dia = dt.get("dia", 1)

        col_handle, col_up, col_down = st.columns([8, 1, 1])
        with col_handle:
            st.markdown(
                f"<div style='padding:6px 0;color:#475569;font-size:0.9rem;'>"
                f"<b>⠿</b>&ensp;{html.escape(emoji)} {html.escape(nome)} "
                f"— {dia:02d}/{mes:02d}</div>",
                unsafe_allow_html=True,
            )
        with col_up:
            if idx > 0 and st.button("↑", key=f"up_{idx}", help="Mover para cima"):
                nova_lista[idx], nova_lista[idx - 1] = nova_lista[idx - 1], nova_lista[idx]
                houve_mudanca = True
        with col_down:
            if idx < len(datas) - 1 and st.button("↓", key=f"down_{idx}", help="Mover para baixo"):
                nova_lista[idx], nova_lista[idx + 1] = nova_lista[idx + 1], nova_lista[idx]
                houve_mudanca = True

    return houve_mudanca


def tela_datas_comemorativas():
    st.markdown(
        "<h3 style='color:#0A2540;font-weight:800;margin-bottom:4px;'>"
        "📅 Datas Comemorativas da Instituição</h3>"
        "<p style='color:#64748B;margin-bottom:20px;'>Cadastre datas especiais que serão "
        "celebradas automaticamente na tela de Frequência com balões e badge festivo — "
        "além das datas nacionais já fixas no sistema.</p>",
        unsafe_allow_html=True,
    )

    datas = get_datas_comemorativas_custom()

    # Índice do item em edição (None = nenhum)
    if "editando_data_idx" not in st.session_state:
        st.session_state.editando_data_idx = None

    # Índice do item aguardando confirmação de remoção (None = nenhum)
    if "confirmando_del_idx" not in st.session_state:
        st.session_state.confirmando_del_idx = None

    editando_idx = st.session_state.editando_data_idx
    confirmando_del_idx = st.session_state.confirmando_del_idx

    # ── Lista das datas cadastradas ──────────────────────────────────────────
    if datas:
        st.markdown(
            f"<p style='color:#0A2540;font-weight:700;font-size:0.95rem;margin-bottom:8px;'>"
            f"✅ {len(datas)} data(s) cadastrada(s)</p>",
            unsafe_allow_html=True,
        )
        nova_lista = list(datas)  # cópia para mutação

        # ── Botão de ordenação automática por mês e dia ───────────────────
        if len(datas) >= 2 and editando_idx is None:
            col_sort, _ = st.columns([3, 7])
            with col_sort:
                if st.button(
                    "📅 Ordenar por data (Jan → Dez)",
                    key="btn_ordenar_por_data",
                    help="Reordena todas as datas automaticamente por mês e depois por dia.",
                    use_container_width=True,
                ):
                    lista_ordenada = sorted(
                        nova_lista,
                        key=lambda d: (d.get("mes", 1), d.get("dia", 1)),
                    )
                    ok, msg = set_datas_comemorativas_custom(lista_ordenada)
                    if ok:
                        st.success("✅ Datas ordenadas por mês e dia!")
                        st.rerun()
                    else:
                        st.error(f"Erro ao salvar ordem: {msg}")

        # ── Seção de reordenação (drag ou ↑/↓) ───────────────────────────
        if len(datas) >= 2 and editando_idx is None:
            with st.expander(
                "⠿ Reordenar datas (arraste para reorganizar)" if _SORTABLES_OK
                else "⠿ Reordenar datas (use os botões ↑/↓)",
                expanded=False,
            ):
                if _SORTABLES_OK:
                    st.markdown(
                        "<p style='color:#64748B;font-size:0.85rem;margin-bottom:8px;'>"
                        "Arraste os itens para definir a nova ordem. "
                        "A ordem é salva automaticamente ao soltar.</p>",
                        unsafe_allow_html=True,
                    )
                    reordenada = _reordenar_com_sortables(datas)
                    if reordenada is not None:
                        ok, msg = set_datas_comemorativas_custom(reordenada)
                        if ok:
                            st.success("✅ Ordem salva!")
                            st.rerun()
                        else:
                            st.error(f"Erro ao salvar ordem: {msg}")
                else:
                    houve = _reordenar_com_botoes(datas, nova_lista)
                    if houve:
                        ok, msg = set_datas_comemorativas_custom(nova_lista)
                        if ok:
                            st.rerun()
                        else:
                            st.error(f"Erro ao salvar ordem: {msg}")

        # ── Cards com edição/exclusão ────────────────────────────────────
        for idx, dt in enumerate(datas):
            mes = dt.get("mes", 1)
            emoji = dt.get("emoji", "🎉")
            cor = dt.get("cor", "#F59E0B")
            nome = dt.get("nome", "—")
            dia = dt.get("dia", 1)

            col_info, col_edit, col_del = st.columns([5, 1, 1])

            with col_info:
                st.markdown(
                    _card_html(emoji, nome, dia, mes, cor),
                    unsafe_allow_html=True,
                )

            with col_edit:
                label_edit = "✏️" if editando_idx != idx else "✖️"
                help_edit = "Editar esta data" if editando_idx != idx else "Cancelar edição"
                if st.button(label_edit, key=f"edit_data_{idx}", help=help_edit):
                    if st.session_state.editando_data_idx == idx:
                        st.session_state.editando_data_idx = None
                    else:
                        st.session_state.editando_data_idx = idx
                    st.rerun()

            with col_del:
                if confirmando_del_idx != idx:
                    if st.button("🗑️", key=f"del_data_{idx}", help="Remover esta data"):
                        st.session_state.confirmando_del_idx = idx
                        st.rerun()
                else:
                    # Botão já clicado: mostrar confirmação inline abaixo do card
                    pass  # handled below

            # ── Confirmação de remoção inline ────────────────────────────
            if confirmando_del_idx == idx:
                st.markdown(
                    "<div style='background:#FEF2F2;border:1.5px solid #EF4444;"
                    "border-radius:8px;padding:10px 14px;margin-bottom:8px;"
                    "display:flex;align-items:center;gap:12px;'>",
                    unsafe_allow_html=True,
                )
                st.warning(
                    f"⚠️ Tem certeza que deseja remover **{html.escape(nome)}**? "
                    "Esta ação não pode ser desfeita."
                )
                conf_col1, conf_col2, _ = st.columns([1, 1, 4])
                with conf_col1:
                    if st.button("✅ Confirmar", key=f"confirm_del_{idx}", type="primary"):
                        nova_lista.pop(idx)
                        ok, msg = set_datas_comemorativas_custom(nova_lista)
                        st.session_state.confirmando_del_idx = None
                        if ok:
                            if st.session_state.editando_data_idx == idx:
                                st.session_state.editando_data_idx = None
                            st.success("Data removida.")
                            st.rerun()
                        else:
                            st.error(f"Erro ao remover: {msg}")
                with conf_col2:
                    if st.button("❌ Cancelar", key=f"cancel_del_{idx}"):
                        st.session_state.confirmando_del_idx = None
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # ── Formulário de edição inline (logo abaixo do item) ──────────
            if editando_idx == idx:
                with st.container():
                    st.markdown(
                        "<div style='background:#EFF6FF;border:1.5px solid #3B82F6;"
                        "border-radius:10px;padding:14px 16px;margin-bottom:10px;'>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<p style='margin:0 0 10px;font-weight:800;color:#1D4ED8;'>"
                        f"✏️ Editando: {html.escape(nome)}</p>",
                        unsafe_allow_html=True,
                    )

                    with st.form(f"form_editar_data_{idx}", clear_on_submit=False):
                        ec1, ec2 = st.columns(2)
                        novo_nome = ec1.text_input(
                            "Nome da data *",
                            value=nome,
                            max_chars=80,
                            key=f"edit_nome_{idx}",
                        )
                        novo_emoji = ec2.text_input(
                            "Emoji *",
                            value=emoji,
                            max_chars=4,
                            help="Um emoji que representa a data. Sugestões: "
                                 + " ".join(_EMOJIS_SUGERIDOS[:10]),
                            key=f"edit_emoji_{idx}",
                        )

                        ec3, ec4 = st.columns(2)
                        novo_mes = ec3.selectbox(
                            "Mês *",
                            options=list(range(1, 13)),
                            format_func=lambda m: _MESES[m],
                            index=mes - 1,
                            key=f"edit_mes_{idx}",
                        )
                        max_dia = _DIAS_POR_MES.get(novo_mes, 31)
                        novo_dia = ec4.number_input(
                            "Dia *",
                            min_value=1,
                            max_value=max_dia,
                            value=min(dia, max_dia),
                            step=1,
                            key=f"edit_dia_{idx}",
                        )

                        nova_cor = st.color_picker(
                            "Cor do badge",
                            value=_safe_cor(cor),
                            help="Cor da borda e do badge exibido na tela de Frequência.",
                            key=f"edit_cor_{idx}",
                        )

                        # Preview inline
                        if novo_nome.strip():
                            st.markdown(
                                f"<div style='margin-top:6px;'>"
                                + _card_html(
                                    (novo_emoji or "🎉").strip(),
                                    novo_nome.strip(),
                                    int(novo_dia),
                                    novo_mes,
                                    nova_cor,
                                )
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                        cb1, cb2 = st.columns(2)
                        salvar_edicao = cb1.form_submit_button(
                            "💾 Salvar alterações",
                            type="primary",
                            use_container_width=True,
                        )
                        cancelar_edicao = cb2.form_submit_button(
                            "✖️ Cancelar",
                            use_container_width=True,
                        )

                    st.markdown("</div>", unsafe_allow_html=True)

                    if cancelar_edicao:
                        st.session_state.editando_data_idx = None
                        st.rerun()

                    if salvar_edicao:
                        nome_strip = novo_nome.strip()
                        emoji_strip = (novo_emoji or "🎉").strip()

                        if not nome_strip:
                            st.error("O nome da data é obrigatório.")
                        else:
                            # Verificar duplicata de mês+dia em outro item
                            duplicata = any(
                                i != idx
                                and d.get("mes") == int(novo_mes)
                                and d.get("dia") == int(novo_dia)
                                for i, d in enumerate(datas)
                            )
                            if duplicata:
                                st.warning(
                                    f"⚠️ Já existe outra data cadastrada para "
                                    f"{int(novo_dia)} de {_MESES[novo_mes]}."
                                )
                            else:
                                nova_lista[idx] = {
                                    "nome": nome_strip,
                                    "mes": int(novo_mes),
                                    "dia": int(novo_dia),
                                    "emoji": emoji_strip,
                                    "cor": nova_cor,
                                }
                                ok, msg = set_datas_comemorativas_custom(nova_lista)
                                if ok:
                                    st.session_state.editando_data_idx = None
                                    st.success(
                                        f"✅ '{nome_strip}' atualizado com sucesso!"
                                    )
                                    st.rerun()
                                else:
                                    st.error(f"Erro ao salvar: {msg}")
    else:
        st.info(
            "Nenhuma data comemorativa personalizada cadastrada ainda. "
            "Use o formulário abaixo para adicionar a primeira! 👇"
        )

    st.markdown("---")

    # ── Formulário de cadastro (apenas quando nenhum item está em edição) ───
    if editando_idx is None:
        st.markdown(
            "<p style='font-weight:800;color:#0A2540;font-size:1rem;margin-bottom:4px;'>"
            "➕ Cadastrar nova data comemorativa</p>",
            unsafe_allow_html=True,
        )

        with st.form("form_nova_data_comemorativa", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome_data = c1.text_input(
                "Nome da data *",
                placeholder="Ex: Aniversário da Academia",
                max_chars=80,
            )
            emoji_input = c2.text_input(
                "Emoji *",
                value="🎉",
                max_chars=4,
                help="Um emoji que representa a data. Sugestões: " + " ".join(_EMOJIS_SUGERIDOS[:10]),
            )

            c3, c4 = st.columns(2)
            mes_sel = c3.selectbox(
                "Mês *",
                options=list(range(1, 13)),
                format_func=lambda m: _MESES[m],
                index=0,
            )
            max_dia = _DIAS_POR_MES.get(mes_sel, 31)
            dia_sel = c4.number_input(
                "Dia *",
                min_value=1,
                max_value=max_dia,
                value=1,
                step=1,
            )

            cor_sel = st.color_picker(
                "Cor do badge",
                value="#F59E0B",
                help="Cor da borda e do badge exibido na tela de Frequência.",
            )

            # Preview inline
            if nome_data.strip():
                st.markdown(
                    f"<div style='margin-top:8px;'>"
                    + _card_html(
                        (emoji_input or "🎉").strip(),
                        nome_data.strip(),
                        int(dia_sel),
                        mes_sel,
                        cor_sel,
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )

            salvar = st.form_submit_button(
                "💾 Salvar data comemorativa",
                type="primary",
                use_container_width=True,
            )

        if salvar:
            nome_strip = nome_data.strip()
            emoji_strip = (emoji_input or "🎉").strip()

            if not nome_strip:
                st.error("O nome da data é obrigatório.")
            else:
                # Verificar duplicata (mesmo mês+dia)
                duplicata = any(
                    d.get("mes") == int(mes_sel) and d.get("dia") == int(dia_sel)
                    for d in datas
                )
                if duplicata:
                    st.warning(
                        f"⚠️ Já existe uma data comemorativa cadastrada para "
                        f"{int(dia_sel)} de {_MESES[mes_sel]}. Remova-a antes de substituir."
                    )
                else:
                    nova = {
                        "nome": nome_strip,
                        "mes": int(mes_sel),
                        "dia": int(dia_sel),
                        "emoji": emoji_strip,
                        "cor": cor_sel,
                    }
                    nova_lista = list(datas) + [nova]
                    ok, msg = set_datas_comemorativas_custom(nova_lista)
                    if ok:
                        st.success(
                            f"✅ Data '{nome_strip}' salva! "
                            f"A celebração aparecerá automaticamente em {int(dia_sel)} de {_MESES[mes_sel]}."
                        )
                        st.rerun()
                    else:
                        st.error(f"Erro ao salvar: {msg}")
    else:
        st.info("💡 Termine a edição acima antes de cadastrar uma nova data.")

    # ── Datas fixas do sistema (informativo) ─────────────────────────────────
    with st.expander("ℹ️ Datas fixas já incluídas no sistema", expanded=False):
        st.markdown("""
Além das suas datas personalizadas, o sistema já celebra automaticamente:

| Data | Celebração |
|---|---|
| 14 de Fevereiro | 💝 Dia dos Namorados |
| 8 de Março | 🌺 Dia Internacional da Mulher |
| 12 de Junho | 💑 Dia dos Namorados (BR) |
| 23 de Junho | 🎆 Véspera de São João |
| 24 de Junho | 🪘 Festa de São João |
| 31 de Outubro | 🎃 Halloween |

> Marcos de aula (50ª, 100ª, 150ª, …) também geram celebração independentemente da data.
        """)
