# ==============================================================================
# 📄 views/datas_comemorativas_view.py
# 📅 Gestão de Datas Comemorativas Personalizadas da Instituição
# ==============================================================================

import html
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

    # ── Lista das datas cadastradas ──────────────────────────────────────────
    if datas:
        st.markdown(
            f"<p style='color:#0A2540;font-weight:700;font-size:0.95rem;margin-bottom:8px;'>"
            f"✅ {len(datas)} data(s) cadastrada(s)</p>",
            unsafe_allow_html=True,
        )
        nova_lista = list(datas)  # cópia para mutação

        for idx, dt in enumerate(datas):
            mes_nome = _MESES[dt.get("mes", 1)] if 1 <= dt.get("mes", 1) <= 12 else "?"
            emoji = dt.get("emoji", "🎉")
            cor = dt.get("cor", "#F59E0B")
            nome = dt.get("nome", "—")
            dia = dt.get("dia", 1)

            col_info, col_del = st.columns([5, 1])
            with col_info:
                # Escape all user-supplied text to prevent stored XSS
                _safe_nome     = html.escape(nome)
                _safe_emoji    = html.escape(emoji)
                _safe_mes_nome = html.escape(mes_nome)
                # cor is validated to be a CSS hex color — only allow safe chars
                import re as _re
                _safe_cor = cor if _re.match(r'^#[0-9A-Fa-f]{3,8}$', cor) else "#F59E0B"
                st.markdown(
                    f"<div style='background:#F8FAFC;border:1.5px solid {_safe_cor};"
                    f"border-radius:10px;padding:10px 14px;margin-bottom:6px;"
                    f"display:flex;align-items:center;gap:12px;'>"
                    f"<span style='font-size:26px;'>{_safe_emoji}</span>"
                    f"<div>"
                    f"<p style='margin:0;font-weight:800;color:#0A2540;font-size:1rem;'>{_safe_nome}</p>"
                    f"<p style='margin:0;color:#64748B;font-size:0.85rem;'>"
                    f"Todo dia {dia} de {_safe_mes_nome}"
                    f"</p>"
                    f"</div>"
                    f"<span style='margin-left:auto;background:{_safe_cor};color:#fff;"
                    f"border-radius:20px;padding:3px 12px;font-size:0.78rem;font-weight:700;'>"
                    f"{html.escape(_safe_cor)}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑️", key=f"del_data_{idx}", help="Remover esta data"):
                    nova_lista.pop(idx)
                    ok, msg = set_datas_comemorativas_custom(nova_lista)
                    if ok:
                        st.success("Data removida.")
                        st.rerun()
                    else:
                        st.error(f"Erro ao remover: {msg}")
    else:
        st.info(
            "Nenhuma data comemorativa personalizada cadastrada ainda. "
            "Use o formulário abaixo para adicionar a primeira! 👇"
        )

    st.markdown("---")

    # ── Formulário de cadastro ───────────────────────────────────────────────
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

        # Preview inline (escape user input to prevent XSS)
        if nome_data.strip():
            import re as _re
            _prev_cor = cor_sel if _re.match(r'^#[0-9A-Fa-f]{3,8}$', cor_sel) else "#F59E0B"
            st.markdown(
                f"<div style='margin-top:8px;background:#F8FAFC;border:1.5px solid {_prev_cor};"
                f"border-radius:10px;padding:10px 14px;display:inline-flex;align-items:center;gap:10px;'>"
                f"<span style='font-size:24px;'>{html.escape((emoji_input or '🎉').strip())}</span>"
                f"<div>"
                f"<p style='margin:0;font-weight:800;color:#0A2540;'>{html.escape(nome_data.strip())}</p>"
                f"<p style='margin:0;color:#64748B;font-size:0.82rem;'>"
                f"Todo dia {int(dia_sel)} de {html.escape(_MESES[mes_sel])}</p>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        salvar = st.form_submit_button("💾 Salvar data comemorativa", type="primary", use_container_width=True)

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
