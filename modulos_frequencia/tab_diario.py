# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_diario.py
# 🏷️ VERSÃO: 4.0 (Selectbox de turma + replicação de conteúdo)
# ⚙️ FUNÇÃO: Registo completo da aula com seleção de turma via combobox,
#             replicação opcional de conteúdo entre turmas e altura dinâmica.
# ==============================================================================
import streamlit as st
import pandas as pd
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


# ==============================================================================
# 📏 ALTURA DINÂMICA
# ==============================================================================
def calcular_altura_caixa(texto, min_altura=100, chars_por_linha=85):
    if not texto:
        return min_altura
    texto_str = str(texto)
    linhas_explicitas = texto_str.count("\n")
    linhas_implicitas = sum(
        len(linha) // chars_por_linha for linha in texto_str.split("\n")
    )
    total_linhas = linhas_explicitas + linhas_implicitas + 2
    return max(min_altura, total_linhas * 25)


# ==============================================================================
# 🔑 CHAVES DE SESSION STATE
# ==============================================================================
def _k(nome, chave_unica):
    return f"_diario_{nome}_{chave_unica}"


# ==============================================================================
# 📝 RENDERIZAÇÃO DA ABA DO DIÁRIO
# ==============================================================================
def renderizar_aba_diario(data_aula, turmas_combo, chave_unica):
    """
    data_aula    : datetime.date
    turmas_combo : list[str] — todas as turmas ativas do dia
    chave_unica  : str — chave da sessão do view pai
    """

    # ── 1. Selectbox de turma ──────────────────────────────────────────────────
    if not turmas_combo or turmas_combo == ["Dia não letivo (Fim de Semana)"]:
        st.warning("Nenhuma turma disponível para esta data.")
        return

    key_sel = _k("turma_sel", chave_unica)

    turma_interna = st.selectbox(
        "📚 Turma do Diário:",
        options=turmas_combo,
        key=key_sel,
        help="Selecione para qual turma deseja registrar ou visualizar o diário",
    )

    # ── 2. Lógica de detecção de troca de turma e oferta de replicação ─────────
    key_prev   = _k("turma_prev",   chave_unica)
    key_rep    = _k("rep_from",     chave_unica)   # turma de origem da replicação
    key_repdata = _k("rep_data",    chave_unica)   # dados pré-carregados para replicar

    turma_prev = st.session_state.get(key_prev)

    if turma_prev is not None and turma_prev != turma_interna:
        # Turma foi trocada — verifica se vale oferecer replicação
        diario_prev = get_diario_dia(data_aula, turma_prev)
        diario_novo = get_diario_dia(data_aula, turma_interna)

        prev_tem_dados = diario_prev and (
            diario_prev.get("objetivo_geral", "").strip()
            or diario_prev.get("exercicios_executados", "").strip()
            or diario_prev.get("foco_clinico_social", "").strip()
        )
        novo_vazio = not diario_novo or (
            not diario_novo.get("objetivo_geral", "").strip()
            and not diario_novo.get("exercicios_executados", "").strip()
            and not diario_novo.get("foco_clinico_social", "").strip()
        )

        if prev_tem_dados and novo_vazio:
            st.session_state[key_rep] = turma_prev
        else:
            # Limpa qualquer replicação pendente ao trocar para turma com dados
            st.session_state.pop(key_rep, None)
            st.session_state.pop(key_repdata, None)

    # Atualiza rastreador de turma anterior
    st.session_state[key_prev] = turma_interna

    # ── 3. Banner de replicação ────────────────────────────────────────────────
    turma_origem = st.session_state.get(key_rep)
    if turma_origem and turma_origem != turma_interna:
        st.info(
            f"💡 A turma **{turma_origem}** já tem conteúdo registrado para esta data.  \n"
            f"Deseja replicar o **Objetivo**, **Exercícios** e **Integração Clínica** "
            f"para a turma **{turma_interna}**?",
        )
        col_sim, col_nao, _ = st.columns([2, 2, 4])
        if col_sim.button(
            "✅ Sim, replicar",
            key=_k("rep_sim", chave_unica),
            use_container_width=True,
            type="primary",
        ):
            diario_orig = get_diario_dia(data_aula, turma_origem)
            if diario_orig:
                st.session_state[key_repdata] = {
                    "objetivo":    diario_orig.get("objetivo_geral", "") or "",
                    "exercicios":  diario_orig.get("exercicios_executados", "") or "",
                    "foco":        diario_orig.get("foco_clinico_social", "") or "",
                }
            st.session_state.pop(key_rep, None)
            st.rerun()
        if col_nao.button(
            "✗ Não, deixar vazio",
            key=_k("rep_nao", chave_unica),
            use_container_width=True,
        ):
            st.session_state.pop(key_rep, None)
            st.session_state.pop(key_repdata, None)
            st.rerun()
        return   # aguarda escolha do usuário antes de renderizar o formulário

    # ── 4. Carrega diário da turma selecionada ─────────────────────────────────
    # Chave de widget inclui a turma para zerar os campos ao trocar
    wk = f"{turma_interna}_{chave_unica}"

    diario = get_diario_dia(data_aula, turma_interna)
    midias_existentes = get_midias_diario(diario["id"]) if diario else []

    # Valores do banco (ou pré-carregados por replicação)
    rep = st.session_state.pop(key_repdata, None)

    val_obj = (rep["objetivo"]   if rep else None) or (diario["objetivo_geral"]         if diario else "") or ""
    val_ex  = (rep["exercicios"] if rep else None) or (diario.get("exercicios_executados", "") if diario else "") or ""
    val_foco_rep = (rep["foco"]  if rep else "") or ""

    with st.container(border=True):
        st.markdown("### 📝 Diário de Bordo")

        # ── Textos do diário ───────────────────────────────────────────────────
        obj = st.text_area(
            "🎯 Objetivo da Sessão:",
            value=val_obj,
            height=calcular_altura_caixa(val_obj),
            key=f"obj_{wk}",
        )
        ex = st.text_area(
            "🏃 Exercícios Executados:",
            value=val_ex,
            height=calcular_altura_caixa(val_ex),
            key=f"ex_{wk}",
        )

        st.divider()

        # ── Integração Clínica e Social ────────────────────────────────────────
        st.markdown("### 🧠 Integração Clínica e Social (60+)")
        st.caption("Marque os focos terapêuticos e sociais abordados com os alunos hoje:")

        focos_salvos = (
            val_foco_rep
            if val_foco_rep
            else (diario.get("foco_clinico_social", "") if diario else "")
        )
        focos_lista = (
            [f.strip() for f in str(focos_salvos).split(",")] if focos_salvos else []
        )

        opcoes_foco = [
            "Correção Postural Fina (Nível Consultório)",
            "Roda de Conversa / Socialização",
            "Consciência Corporal e Biomecânica",
            "Prevenção de Quedas / Equilíbrio",
            "Hábitos Alimentares e Qualidade de Vida",
            "Avaliação / Medição Coletiva",
        ]

        c_ck1, c_ck2 = st.columns(2)
        selecionados = []
        for i, op in enumerate(opcoes_foco):
            col = c_ck1 if i % 2 == 0 else c_ck2
            is_checked = op in focos_lista
            if col.checkbox(op, value=is_checked, key=f"ck_{i}_{wk}"):
                selecionados.append(op)

        foco_final_str = ", ".join(selecionados)

        # Campo qualitativo
        relatos_atuais = diario.get("relatos_melhora", "") if diario else ""
        val_relatos = relatos_atuais if pd.notna(relatos_atuais) else ""
        relatos = st.text_area(
            "🗣️ Relatos de Melhora e Impacto (Qualitativo):",
            value=val_relatos,
            placeholder=(
                "Ex: Hoje vários alunos relataram alívio de dores lombares após os "
                "ajustes biomecânicos. A Dona Maria comentou que já consegue varrer "
                "a casa com mais autonomia..."
            ),
            height=calcular_altura_caixa(val_relatos),
            key=f"rel_{wk}",
        )

        st.divider()

        # ── Fotografia e Evidências ────────────────────────────────────────────
        st.markdown("#### 📸 Foto Principal (Grupo)")
        col_f1, col_f2 = st.columns([1, 2])
        u_g_atual = diario.get("url_foto_grupo") if diario else None

        with col_f1:
            if u_g_atual:
                st.image(u_g_atual, caption="Foto Atual do Grupo", use_container_width=True)
            else:
                st.info("Sem foto de grupo.")

        with col_f2:
            foto_g = st.file_uploader(
                "Trocar/Adicionar Foto do Grupo:",
                type=["png", "jpg", "jpeg"],
                key=f"up_g_{wk}",
            )

        st.divider()

        st.markdown("#### 🏋️ Galeria de Exercícios")

        if midias_existentes:
            st.caption("Fotos já registadas nesta aula:")
            for m in midias_existentes:
                with st.expander(f"🖼️ Foto: {m.get('descricao_objetivo', 'Sem legenda')}"):
                    c1, c2 = st.columns([1, 2])
                    c1.image(m["url_midia"], use_container_width=True)
                    nova_legenda = c2.text_input(
                        "Editar Legenda:",
                        value=m.get("descricao_objetivo", ""),
                        key=f"leg_{m['id']}",
                    )
                    b_col1, b_col2 = c2.columns(2)
                    if b_col1.button("💾 Atualizar", key=f"btn_up_{m['id']}", use_container_width=True):
                        atualizar_legenda_midia(m["id"], nova_legenda)
                        st.rerun()
                    if b_col2.button("🗑️ Excluir", key=f"btn_del_{m['id']}", type="secondary", use_container_width=True):
                        excluir_midia_diario(m["id"])
                        st.rerun()

        novas_fotos_ex = st.file_uploader(
            "Adicionar Fotos de Exercícios (Múltiplas):",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key=f"up_ex_{wk}",
        )

        lista_novas_midias = []
        if novas_fotos_ex:
            st.info(f"✨ {len(novas_fotos_ex)} nova(s) foto(s) selecionada(s). Adicione as legendas abaixo:")
            for idx, f in enumerate(novas_fotos_ex):
                legenda_temp = st.text_input(
                    f"Legenda para a foto {idx + 1}:",
                    placeholder="Ex: Exercício de força lateral...",
                    key=f"new_leg_{idx}_{wk}",
                )
                lista_novas_midias.append({"file": f, "desc": legenda_temp})

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Botão Salvar ───────────────────────────────────────────────────────
        if st.button("💾 SALVAR DIÁRIO COMPLETO", use_container_width=True, type="primary", key=f"btn_salvar_{wk}"):
            with st.spinner("A processar e guardar no MoveRight..."):
                final_url_grupo = u_g_atual
                if foto_g:
                    img_g = Image.open(io.BytesIO(foto_g.getvalue())).convert("RGB")
                    buf_g = io.BytesIO()
                    img_g.save(buf_g, format="JPEG", quality=85)
                    final_url_grupo = upload_midia(buf_g.getvalue(), "grupo.jpg", "image/jpeg")

                midias_para_banco = []
                for idx, item in enumerate(lista_novas_midias):
                    img_ex = Image.open(io.BytesIO(item["file"].getvalue())).convert("RGB")
                    buf_ex = io.BytesIO()
                    img_ex.save(buf_ex, format="JPEG", quality=85)
                    url_ex = upload_midia(buf_ex.getvalue(), f"ex_{idx}.jpg", "image/jpeg")
                    if url_ex:
                        midias_para_banco.append({"url": url_ex, "descricao": item["desc"], "tipo": "foto"})

                sucesso, msg = salvar_diario(
                    data_aula,
                    turma_interna,
                    obj,
                    ex,
                    final_url_grupo,
                    midias_para_banco,
                    foco_final_str,
                    relatos,
                )

                if sucesso:
                    st.toast("Diário guardado com sucesso! 🚀", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")
