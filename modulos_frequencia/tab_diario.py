# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_diario.py
# 🏷️ VERSÃO: 3.1 (PRO Elite - Integração Clínica e Social 60+ com Pandas Fix)
# 📅 DATA: Atualizado
# ⚙️ FUNÇÃO: Registo completo da aula com foto de grupo, exercícios e impacto social.
# ==============================================================================
import streamlit as st
import pandas as pd  # <--- AQUI ESTAVA A FALTAR ESTA LINHA! 🚀
import time
import io
from PIL import Image
from database import (
    get_diario_dia,
    get_midias_diario,
    upload_midia,
    salvar_diario,
    atualizar_legenda_midia,
    excluir_midia_diario,
)


def renderizar_aba_diario(data_aula, turma_selecionada, chave_unica):
    diario = get_diario_dia(data_aula, turma_selecionada)
    midias_existentes = get_midias_diario(diario["id"]) if diario else []

    with st.container(border=True):
        st.markdown("### 📝 Diário de Bordo")

        # 1. TEXTOS DO DIÁRIO (BÁSICO)
        obj = st.text_area(
            "🎯 Objetivo da Sessão:",
            value=diario["objetivo_geral"] if diario else "",
            height=80,
            key=f"obj_{chave_unica}",
        )
        ex = st.text_area(
            "🏃 Exercícios Executados:",
            value=diario.get("exercicios_executados", "") if diario else "",
            height=80,
            key=f"ex_{chave_unica}",
        )

        st.divider()

        # ==============================================================================
        # 🚀 NOVO: INTEGRAÇÃO CLÍNICA E SOCIAL (MÓDULO 60+)
        # ==============================================================================
        st.markdown("### 🧠 Integração Clínica e Social (60+)")
        st.caption("Marque os focos terapêuticos e sociais abordados com os alunos hoje:")

        # Tratamento seguro dos dados já guardados no banco
        focos_salvos = diario.get("foco_clinico_social", "") if diario else ""
        focos_lista = [f.strip() for f in str(focos_salvos).split(",")] if focos_salvos else []

        opcoes_foco = [
            "Correção Postural Fina (Nível Consultório)",
            "Roda de Conversa / Socialização",
            "Consciência Corporal e Biomecânica",
            "Prevenção de Quedas / Equilíbrio",
            "Hábitos Alimentares e Qualidade de Vida",
            "Avaliação / Medição Coletiva"
        ]

        # Renderização dinâmica de Checkboxes em 2 Colunas para UI Limpa
        c_ck1, c_ck2 = st.columns(2)
        selecionados = []
        for i, op in enumerate(opcoes_foco):
            col = c_ck1 if i % 2 == 0 else c_ck2
            is_checked = op in focos_lista
            if col.checkbox(op, value=is_checked, key=f"ck_{i}_{chave_unica}"):
                selecionados.append(op)

        foco_final_str = ", ".join(selecionados)

        # Campo Qualitativo (Opcional, mas de altíssimo valor)
        relatos_atuais = diario.get("relatos_melhora", "") if diario else ""
        relatos = st.text_area(
            "🗣️ Relatos de Melhora e Impacto (Qualitativo):",
            value=relatos_atuais if pd.notna(relatos_atuais) else "",
            placeholder="Ex: Hoje vários alunos relataram alívio de dores lombares após os ajustes biomecânicos. A Dona Maria comentou que já consegue varrer a casa com mais autonomia...",
            height=100,
            key=f"rel_{chave_unica}"
        )

        st.divider()

        # ==============================================================================
        # FOTOGRAFIA E EVIDÊNCIAS
        # ==============================================================================
        st.markdown("#### 📸 Foto Principal (Grupo)")
        col_f1, col_f2 = st.columns([1, 2])
        u_g_atual = diario.get("url_foto_grupo") if diario else None

        with col_f1:
            if u_g_atual:
                st.image(
                    u_g_atual, caption="Foto Atual do Grupo", use_container_width=True
                )
            else:
                st.info("Sem foto de grupo.")

        with col_f2:
            foto_g = st.file_uploader(
                "Trocar/Adicionar Foto do Grupo:",
                type=["png", "jpg", "jpeg"],
                key=f"up_g_{chave_unica}",
            )

        st.divider()

        st.markdown("#### 🏋️ Galeria de Exercícios")

        if midias_existentes:
            st.caption("Fotos já registadas nesta aula:")
            for m in midias_existentes:
                with st.expander(
                    f"🖼️ Foto: {m.get('descricao_objetivo', 'Sem legenda')}"
                ):
                    c1, c2 = st.columns([1, 2])
                    c1.image(m["url_midia"], use_container_width=True)
                    nova_legenda = c2.text_input(
                        "Editar Legenda:",
                        value=m.get("descricao_objetivo", ""),
                        key=f"leg_{m['id']}",
                    )

                    b_col1, b_col2 = c2.columns(2)
                    if b_col1.button(
                        "💾 Atualizar",
                        key=f"btn_up_{m['id']}",
                        use_container_width=True,
                    ):
                        atualizar_legenda_midia(m["id"], nova_legenda)
                        st.rerun()
                    if b_col2.button(
                        "🗑️ Excluir",
                        key=f"btn_del_{m['id']}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        excluir_midia_diario(m["id"])
                        st.rerun()

        novas_fotos_ex = st.file_uploader(
            "Adicionar Fotos de Exercícios (Múltiplas):",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key=f"up_ex_{chave_unica}",
        )

        lista_novas_midias = []
        if novas_fotos_ex:
            st.info(
                f"✨ {len(novas_fotos_ex)} nova(s) foto(s) selecionada(s). Adicione as legendas abaixo:"
            )
            for idx, f in enumerate(novas_fotos_ex):
                legenda_temp = st.text_input(
                    f"Legenda para a foto {idx + 1}:",
                    placeholder="Ex: Exercício de força lateral...",
                    key=f"new_leg_{idx}_{chave_unica}",
                )
                lista_novas_midias.append({"file": f, "desc": legenda_temp})

        st.markdown("<br>", unsafe_allow_html=True)

        # ==============================================================================
        # BOTÃO SALVAR (MÁGICA FINAL)
        # ==============================================================================
        if st.button(
            "💾 SALVAR DIÁRIO COMPLETO", use_container_width=True, type="primary"
        ):
            with st.spinner("A processar informações e a guardar no MoveRight..."):
                final_url_grupo = u_g_atual
                if foto_g:
                    img_g = Image.open(io.BytesIO(foto_g.getvalue())).convert("RGB")
                    buf_g = io.BytesIO()
                    img_g.save(buf_g, format="JPEG", quality=85)
                    final_url_grupo = upload_midia(
                        buf_g.getvalue(), "grupo.jpg", "image/jpeg"
                    )

                midias_para_banco = []
                for idx, item in enumerate(lista_novas_midias):
                    img_ex = Image.open(io.BytesIO(item["file"].getvalue())).convert(
                        "RGB"
                    )
                    buf_ex = io.BytesIO()
                    img_ex.save(buf_ex, format="JPEG", quality=85)
                    url_ex = upload_midia(
                        buf_ex.getvalue(), f"ex_{idx}.jpg", "image/jpeg"
                    )
                    if url_ex:
                        midias_para_banco.append(
                            {"url": url_ex, "descricao": item["desc"], "tipo": "foto"}
                        )

                # Chama a nova função atualizada no database.py com os novos campos
                sucesso, msg = salvar_diario(
                    data_aula,
                    turma_selecionada,
                    obj,
                    ex,
                    final_url_grupo,
                    midias_para_banco,
                    foco_final_str, # A string consolidada dos checkboxes
                    relatos         # O texto qualitativo
                )

                if sucesso:
                    st.toast("Integração Clínica guardada com sucesso! 🚀", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")