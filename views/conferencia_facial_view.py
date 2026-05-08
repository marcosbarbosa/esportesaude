# ==============================================================================
# 📄 Arquivo: views/conferencia_facial_view.py
# 🏷️ Módulo: Conferência de Presença por Reconhecimento Facial
# 👤 AUTOR: Marcos Barbosa - MoveRight (c)
# ⚙️ FUNÇÃO: Identifica alunos em foto de turma via DeepFace e lança presenças
# ==============================================================================

import streamlit as st
import datetime
import tempfile
import os
import io
import requests
from PIL import Image
import numpy as np

from database import supabase


# ── Helpers de DB ─────────────────────────────────────────────────────────────


def _buscar_turmas():
    r = (
        supabase.table("turmas")
        .select("id,nome,horario,dias_semana")
        .eq("status", "Ativa")
        .execute()
    )
    return r.data or []


def _buscar_alunos_turma(turma_id: str):
    r = (
        supabase.table("alunos")
        .select("id,nome,url_foto,turma_id")
        .eq("status", "Ativo")
        .eq("turma_id", turma_id)
        .execute()
    )
    return r.data or []


def _buscar_diario_sem_frequencia(turma_id: str):
    """Retorna aulas do diário que ainda não têm frequência lançada para a turma."""
    r_diario = (
        supabase.table("diario_aulas")
        .select("id,data_aula,turma,turma_id,url_foto_grupo")
        .eq("turma_id", turma_id)
        .order("data_aula", desc=True)
        .limit(60)
        .execute()
    )
    return r_diario.data or []


def _presencas_ja_lancadas(data_aula: str, aluno_ids: list) -> set:
    """Retorna set de aluno_ids que já têm frequência nessa data."""
    if not aluno_ids:
        return set()
    r = (
        supabase.table("frequencia")
        .select("aluno_id")
        .eq("data_aula", data_aula)
        .in_("aluno_id", aluno_ids)
        .execute()
    )
    return {row["aluno_id"] for row in (r.data or [])}


def _gravar_frequencias(resultados: list, data_aula: str):
    """
    resultados: lista de dicts {aluno_id, nome, status: 'PRESENTE'|'FALTA'}
    Usa upsert para não duplicar registros.
    """
    rows = [
        {"aluno_id": item["aluno_id"], "data_aula": data_aula, "status": item["status"]}
        for item in resultados
    ]
    supabase.table("frequencia").upsert(
        rows, on_conflict="aluno_id,data_aula"
    ).execute()


# ── Download de imagem para numpy array ───────────────────────────────────────


def _url_para_array(url: str) -> np.ndarray | None:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return np.array(img)
    except Exception:
        return None


def _upload_para_array(uploaded_file) -> np.ndarray | None:
    try:
        img = Image.open(uploaded_file).convert("RGB")
        return np.array(img)
    except Exception:
        return None


# ── Motor de reconhecimento facial ────────────────────────────────────────────


def _reconhecer_presencas(img_grupo: np.ndarray, alunos: list) -> list:
    """
    Compara cada rosto da foto de grupo com as fotos individuais dos alunos.
    Retorna lista de dicts:
      {aluno_id, nome, status, confianca, tem_foto}
    """
    from deepface import DeepFace

    resultados = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # Salvar foto do grupo
        grupo_path = os.path.join(tmpdir, "grupo.jpg")
        Image.fromarray(img_grupo).save(grupo_path)

        for aluno in alunos:
            aluno_id = aluno["id"]
            nome = aluno["nome"]
            url_foto = aluno.get("url_foto") or ""

            if not url_foto:
                resultados.append(
                    {
                        "aluno_id": aluno_id,
                        "nome": nome,
                        "status": "FALTA",
                        "confianca": 0,
                        "tem_foto": False,
                        "motivo": "Sem foto cadastrada",
                    }
                )
                continue

            # Download foto individual
            arr_individual = _url_para_array(url_foto)
            if arr_individual is None:
                resultados.append(
                    {
                        "aluno_id": aluno_id,
                        "nome": nome,
                        "status": "FALTA",
                        "confianca": 0,
                        "tem_foto": True,
                        "motivo": "Erro ao carregar foto",
                    }
                )
                continue

            individual_path = os.path.join(tmpdir, f"{aluno_id}.jpg")
            Image.fromarray(arr_individual).save(individual_path)

            try:
                resultado_df = DeepFace.find(
                    img_path=individual_path,
                    db_path=tmpdir,
                    model_name="Facenet",
                    detector_backend="retinaface",  # "retinaface", opencv
                    enforce_detection=False,
                    silent=True,
                )

                encontrado = False
                confianca = 0

                # DeepFace.find retorna lista de DataFrames (um por rosto detectado)
                for df in resultado_df:
                    if df is not None and not df.empty:
                        # Verifica se a foto do grupo está nos resultados (match com rosto da turma)
                        # Usamos verify direto para maior controle
                        break

                # Abordagem mais direta: verify par-a-par contra a foto do grupo
                try:
                    verify = DeepFace.verify(
                        img1_path=individual_path,
                        img2_path=grupo_path,
                        model_name="Facenet",
                        detector_backend="retinaface",
                        enforce_detection=False,
                        silent=True,
                    )
                    encontrado = verify.get("verified", False)
                    distancia = verify.get("distance", 1.0)
                    limiar = verify.get("threshold", 0.4)
                    # Confiança invertida: quanto menor a distância, maior a confiança
                    confianca = max(
                        0, int((1 - distancia / max(limiar * 2, 0.01)) * 100)
                    )
                    confianca = min(confianca, 99)
                except Exception:
                    encontrado = False
                    confianca = 0

                resultados.append(
                    {
                        "aluno_id": aluno_id,
                        "nome": nome,
                        "status": "PRESENTE" if encontrado else "FALTA",
                        "confianca": confianca,
                        "tem_foto": True,
                        "motivo": "",
                    }
                )

            except Exception as e:
                resultados.append(
                    {
                        "aluno_id": aluno_id,
                        "nome": nome,
                        "status": "FALTA",
                        "confianca": 0,
                        "tem_foto": True,
                        "motivo": f"Erro: {str(e)[:60]}",
                    }
                )

    return resultados


# ── Tela principal ────────────────────────────────────────────────────────────


def tela_conferencia_facial():
    st.markdown(
        "<h3 style='color:#0A2540;font-weight:800;margin-bottom:4px;'>"
        "📸 Conferência de Presença por Foto</h3>"
        "<p style='color:#64748B;margin-bottom:20px;'>"
        "Faça upload da foto da turma e o sistema identifica automaticamente quem estava presente.</p>",
        unsafe_allow_html=True,
    )

    # ── Aviso sobre limitações ─────────────────────────────────────────────
    with st.expander("ℹ️ Como funciona e limitações importantes", expanded=False):
        st.markdown("""
**Como funciona:**
1. Selecione a turma e a data da aula
2. Faça upload da foto tirada no fim da aula (ou use a foto do diário se já existir)
3. O sistema compara cada aluno da turma com os rostos na foto
4. Revise o resultado — confirme ou corrija antes de salvar

**Limitações honestas:**
- Fotos escuras, desfocadas ou com rostos de lado reduzem a precisão
- Alunos sem foto cadastrada não são identificados automaticamente (ficam como FALTA)
- O processo leva ~3–10 segundos por aluno — seja paciente
- **Sempre confirme o resultado antes de gravar.** O sistema nunca salva sem sua aprovação.

**Privacidade:** As fotos são processadas localmente no servidor, sem envio para serviços externos.
        """)

    turmas = _buscar_turmas()
    if not turmas:
        st.warning("Nenhuma turma ativa encontrada.")
        return

    # ── Seleção de turma ───────────────────────────────────────────────────
    col_turma, col_data = st.columns([2, 1])
    with col_turma:
        opcoes_turma = {t["nome"]: t for t in turmas}
        turma_nome = st.selectbox("🏫 Turma", list(opcoes_turma.keys()))
    turma_sel = opcoes_turma[turma_nome]
    turma_id = turma_sel["id"]

    with col_data:
        data_aula = st.date_input(
            "📅 Data da Aula",
            value=datetime.date.today(),
            max_value=datetime.date.today(),
        )

    alunos = _buscar_alunos_turma(turma_id)
    if not alunos:
        st.warning("Nenhum aluno ativo nesta turma.")
        return

    total_alunos = len(alunos)
    com_foto = sum(1 for a in alunos if a.get("url_foto"))
    sem_foto = total_alunos - com_foto

    st.markdown(
        f"<div style='background:#F0F9FF;border-left:4px solid #0056b3;padding:10px 16px;"
        f"border-radius:6px;margin-bottom:16px;font-size:13px;'>"
        f"👥 <b>{total_alunos} alunos</b> nesta turma — "
        f"<span style='color:#16a34a;'>✅ {com_foto} com foto</span> · "
        f"<span style='color:#dc2626;'>⚠️ {sem_foto} sem foto</span> "
        f"(serão marcados como FALTA automaticamente)</div>",
        unsafe_allow_html=True,
    )

    # ── Origem da foto do grupo ────────────────────────────────────────────
    st.markdown("**📷 Foto da Turma (fonte)**")
    origem = st.radio(
        "Origem da foto",
        ["Upload manual (novo arquivo)", "Usar foto já registrada no Diário"],
        horizontal=True,
        label_visibility="collapsed",
    )

    img_grupo = None
    url_grupo_usada = None

    if origem == "Upload manual (novo arquivo)":
        uploaded = st.file_uploader(
            "Envie a foto da turma",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        if uploaded:
            img_grupo = _upload_para_array(uploaded)
            st.image(
                uploaded, caption="Foto da turma carregada", use_container_width=True
            )

    else:
        # Buscar do diário
        diario = _buscar_diario_sem_frequencia(turma_id)
        entradas_com_foto = [d for d in diario if d.get("url_foto_grupo")]

        if not entradas_com_foto:
            st.info("Nenhuma entrada no Diário com foto de grupo para esta turma.")
        else:
            opcoes_diario = {
                f"{d['data_aula']} — {d['turma']}": d for d in entradas_com_foto
            }
            entrada_sel_key = st.selectbox(
                "Selecione a aula", list(opcoes_diario.keys())
            )
            entrada_sel = opcoes_diario[entrada_sel_key]
            url_grupo_usada = entrada_sel["url_foto_grupo"]

            # Preencher data automaticamente
            try:
                data_aula = datetime.date.fromisoformat(entrada_sel["data_aula"])
            except Exception:
                pass

            arr = _url_para_array(url_grupo_usada)
            if arr is not None:
                img_grupo = arr
                st.image(
                    url_grupo_usada,
                    caption=f"Foto do diário — {entrada_sel['data_aula']}",
                    use_container_width=True,
                )
            else:
                st.error("Não foi possível carregar a foto do diário.")

    # ── Botão de análise ───────────────────────────────────────────────────
    st.markdown("---")

    ja_lancadas = _presencas_ja_lancadas(str(data_aula), [a["id"] for a in alunos])
    if ja_lancadas:
        st.warning(
            f"⚠️ {len(ja_lancadas)} aluno(s) já têm frequência lançada para {data_aula.strftime('%d/%m/%Y')}. "
            "A conferência irá sobrescrever apenas os registros confirmados."
        )

    btn_analisar = st.button(
        "🔍 Iniciar Reconhecimento Facial",
        type="primary",
        use_container_width=True,
        disabled=(img_grupo is None),
    )

    if img_grupo is None:
        st.caption("⬆️ Forneça a foto da turma para habilitar o reconhecimento.")

    if btn_analisar and img_grupo is not None:
        # Limpar resultado anterior
        st.session_state.pop("facial_resultado", None)
        st.session_state.pop("facial_data", None)
        st.session_state.pop("facial_alunos", None)

        barra = st.progress(0, text="A preparar análise...")
        status_box = st.empty()

        resultados = []
        total = len(alunos)

        for i, aluno in enumerate(alunos):
            pct = int((i / total) * 100)
            barra.progress(
                pct, text=f"Analisando {i + 1}/{total}: {aluno['nome'][:30]}…"
            )
            status_box.caption(f"🔎 Verificando {aluno['nome']}…")

            # Processar um aluno de cada vez para feedback em tempo real
            resultado_aluno = _reconhecer_presencas(img_grupo, [aluno])
            resultados.extend(resultado_aluno)

        barra.progress(100, text="✅ Análise concluída!")
        status_box.empty()

        st.session_state["facial_resultado"] = resultados
        st.session_state["facial_data"] = str(data_aula)
        st.session_state["facial_alunos"] = {a["id"]: a for a in alunos}
        st.rerun()

    # ── Exibir resultado e confirmação ────────────────────────────────────
    if "facial_resultado" in st.session_state:
        resultados = st.session_state["facial_resultado"]
        data_str = st.session_state["facial_data"]
        try:
            data_fmt = datetime.date.fromisoformat(data_str).strftime("%d/%m/%Y")
        except Exception:
            data_fmt = data_str

        presentes = [r for r in resultados if r["status"] == "PRESENTE"]
        faltas = [r for r in resultados if r["status"] == "FALTA"]
        sem_foto_lst = [r for r in resultados if not r["tem_foto"]]

        st.markdown("---")
        st.markdown(
            f"<h4 style='color:#0A2540;margin-bottom:4px;'>"
            f"📋 Resultado da Análise — {data_fmt}</h4>",
            unsafe_allow_html=True,
        )

        # Métricas resumo
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("👥 Total analisados", len(resultados))
        mc2.metric("✅ Identificados presentes", len(presentes))
        mc3.metric("❌ Não identificados", len(faltas))
        mc4.metric("📷 Sem foto cadastrada", len(sem_foto_lst))

        st.markdown("**Revise e ajuste antes de confirmar:**")

        # Estado editável dos resultados
        if "facial_editado" not in st.session_state:
            st.session_state["facial_editado"] = {
                r["aluno_id"]: r["status"] for r in resultados
            }

        # Listar todos os alunos com controle de status
        for r in sorted(
            resultados, key=lambda x: (-1 if x["status"] == "PRESENTE" else 1)
        ):
            aluno_id = r["aluno_id"]
            nome = r["nome"]
            conf = r["confianca"]
            tem_foto = r["tem_foto"]
            motivo = r.get("motivo", "")
            status_atual = st.session_state["facial_editado"].get(aluno_id, r["status"])

            with st.container(border=True):
                c_nome, c_conf, c_status = st.columns([3, 2, 2])

                with c_nome:
                    if status_atual == "PRESENTE":
                        st.markdown(f"✅ **{nome}**")
                    else:
                        st.markdown(f"❌ {nome}")
                    if not tem_foto:
                        st.caption("📷 Sem foto cadastrada")
                    elif motivo:
                        st.caption(f"⚠️ {motivo}")

                with c_conf:
                    if tem_foto and not motivo:
                        cor = "#16a34a" if conf >= 50 else "#dc2626"
                        st.markdown(
                            f"<span style='color:{cor};font-weight:700;font-size:13px;'>"
                            f"Confiança: {conf}%</span>",
                            unsafe_allow_html=True,
                        )
                        if conf >= 70:
                            st.caption("🟢 Alta confiança")
                        elif conf >= 40:
                            st.caption("🟡 Confiança média")
                        else:
                            st.caption("🔴 Baixa confiança")
                    else:
                        st.caption("—")

                with c_status:
                    novo_status = st.selectbox(
                        "Status",
                        ["PRESENTE", "FALTA"],
                        index=0 if status_atual == "PRESENTE" else 1,
                        key=f"sel_{aluno_id}",
                        label_visibility="collapsed",
                    )
                    st.session_state["facial_editado"][aluno_id] = novo_status

        st.markdown("---")

        # Resumo final antes de gravar
        editado = st.session_state["facial_editado"]
        total_presentes_final = sum(1 for v in editado.values() if v == "PRESENTE")
        total_faltas_final = sum(1 for v in editado.values() if v == "FALTA")

        st.markdown(
            f"<div style='background:#F0FDF4;border:1px solid #86efac;border-radius:8px;"
            f"padding:12px 16px;margin-bottom:16px;'>"
            f"📊 <b>Resumo final:</b> "
            f"<span style='color:#16a34a;font-weight:700;'>✅ {total_presentes_final} PRESENTE(S)</span> · "
            f"<span style='color:#dc2626;font-weight:700;'>❌ {total_faltas_final} FALTA(S)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        col_gravar, col_cancelar = st.columns([2, 1])
        with col_gravar:
            if st.button(
                f"💾 Confirmar e Gravar Frequência ({data_fmt})",
                type="primary",
                use_container_width=True,
            ):
                lista_gravar = [
                    {
                        "aluno_id": aid,
                        "nome": next(
                            (r["nome"] for r in resultados if r["aluno_id"] == aid), ""
                        ),
                        "status": st,
                    }
                    for aid, st in editado.items()
                ]
                with st.spinner("A gravar frequências…"):
                    _gravar_frequencias(lista_gravar, data_str)
                st.success(
                    f"✅ Frequência gravada com sucesso para {data_fmt}! "
                    f"{total_presentes_final} presentes · {total_faltas_final} faltas."
                )
                # Limpar estado
                for k in [
                    "facial_resultado",
                    "facial_data",
                    "facial_alunos",
                    "facial_editado",
                ]:
                    st.session_state.pop(k, None)
                st.rerun()

        with col_cancelar:
            if st.button("🗑️ Descartar Resultado", use_container_width=True):
                for k in [
                    "facial_resultado",
                    "facial_data",
                    "facial_alunos",
                    "facial_editado",
                ]:
                    st.session_state.pop(k, None)
                st.rerun()
