# ==============================================================================
# Arquivo: views/conferencia_facial_view.py
# Modulo: Conferencia de Presenca por Reconhecimento Facial
# Autor: Marcos Barbosa - MoveRight (c)
# Funcao: Processa alunos em lotes de 3, salva imediatamente apos confirmacao
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

LOTE_SIZE = 3  # alunos processados por vez


# ==============================================================================
# Helpers de banco de dados
# ==============================================================================


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


def _presencas_ja_lancadas(data_aula: str, aluno_ids: list) -> set:
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


def _gravar_lote(resultados: list, data_aula: str):
    rows = [
        {"aluno_id": item["aluno_id"], "data_aula": data_aula, "status": item["status"]}
        for item in resultados
    ]
    supabase.table("frequencia").upsert(rows, on_conflict="aluno_id,data_aula").execute()


def _buscar_diario_com_foto(turma_id: str):
    r = (
        supabase.table("diario_aulas")
        .select("id,data_aula,turma,turma_id,url_foto_grupo")
        .eq("turma_id", turma_id)
        .order("data_aula", desc=True)
        .limit(60)
        .execute()
    )
    return [d for d in (r.data or []) if d.get("url_foto_grupo")]


# ==============================================================================
# Helpers de imagem
# ==============================================================================


def _url_para_array(url: str):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return np.array(img)
    except Exception:
        return None


def _upload_para_array(uploaded_file):
    try:
        img = Image.open(uploaded_file).convert("RGB")
        return np.array(img)
    except Exception:
        return None


def _salvar_img_temp(arr: np.ndarray) -> str:
    """Salva numpy array em arquivo temporario e retorna o path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    Image.fromarray(arr).save(tmp.name)
    tmp.close()
    return tmp.name


# ==============================================================================
# Motor de reconhecimento facial (um aluno por vez)
# ==============================================================================


def _reconhecer_aluno(grupo_path: str, aluno: dict) -> dict:
    from deepface import DeepFace

    aluno_id = aluno["id"]
    nome = aluno["nome"]
    url_foto = aluno.get("url_foto") or ""

    if not url_foto:
        return {
            "aluno_id": aluno_id, "nome": nome,
            "status": "FALTA", "confianca": 0,
            "tem_foto": False, "motivo": "Sem foto cadastrada",
        }

    arr_individual = _url_para_array(url_foto)
    if arr_individual is None:
        return {
            "aluno_id": aluno_id, "nome": nome,
            "status": "FALTA", "confianca": 0,
            "tem_foto": True, "motivo": "Erro ao carregar foto",
        }

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        individual_path = f.name
    Image.fromarray(arr_individual).save(individual_path)

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
        confianca = max(0, int((1 - distancia / max(limiar * 2, 0.01)) * 100))
        confianca = min(confianca, 99)
        return {
            "aluno_id": aluno_id, "nome": nome,
            "status": "PRESENTE" if encontrado else "FALTA",
            "confianca": confianca, "tem_foto": True, "motivo": "",
        }
    except Exception as e:
        return {
            "aluno_id": aluno_id, "nome": nome,
            "status": "FALTA", "confianca": 0,
            "tem_foto": True, "motivo": f"Erro: {str(e)[:60]}",
        }
    finally:
        try:
            os.unlink(individual_path)
        except Exception:
            pass


# ==============================================================================
# Tela principal — dispatcher
# ==============================================================================


def tela_conferencia_facial():
    st.markdown(
        "<h3 style='color:#0A2540;font-weight:800;margin-bottom:4px;'>"
        "Conferencia de Presenca por Foto</h3>"
        "<p style='color:#64748B;margin-bottom:12px;'>"
        "Processa em lotes de 3 alunos — salva cada lote imediatamente, "
        "retoma de onde parou em caso de queda.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("facial_sessao_ativa"):
        _modo_processamento()
    else:
        _modo_configuracao()


# ==============================================================================
# Modo 1: Configuracao inicial
# ==============================================================================


def _modo_configuracao():
    with st.expander("Como funciona", expanded=False):
        st.markdown("""
**Fluxo modular por lotes:**
1. Selecione turma, data e foto da turma
2. Clique em "Iniciar Conferencia"
3. O sistema analisa **3 alunos por vez** — revise e confirme cada lote
4. Cada lote confirmado e **gravado imediatamente** no banco
5. Se o sistema travar, basta reiniciar — quem ja foi confirmado nao sera reprocessado
6. No final, um resumo completo da sessao

**Privacidade:** as fotos sao processadas localmente, sem servicos externos.
        """)

    turmas = _buscar_turmas()
    if not turmas:
        st.warning("Nenhuma turma ativa encontrada.")
        return

    col_turma, col_data = st.columns([2, 1])
    with col_turma:
        opcoes_turma = {t["nome"]: t for t in turmas}
        turma_nome = st.selectbox("Turma", list(opcoes_turma.keys()))
    turma_sel = opcoes_turma[turma_nome]
    turma_id = turma_sel["id"]

    with col_data:
        data_aula = st.date_input(
            "Data da Aula",
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

    ja_lancadas = _presencas_ja_lancadas(str(data_aula), [a["id"] for a in alunos])
    pendentes_count = total_alunos - len(ja_lancadas)

    st.markdown(
        f"<div style='background:#F0F9FF;border-left:4px solid #0056b3;"
        f"padding:10px 16px;border-radius:6px;margin-bottom:12px;font-size:13px;'>"
        f"<b>{total_alunos} alunos</b> na turma &nbsp;|&nbsp; "
        f"<span style='color:#16a34a;'>{com_foto} com foto</span> &nbsp;|&nbsp; "
        f"<span style='color:#dc2626;'>{sem_foto} sem foto</span>"
        f"{f'<br><b style=color:#92400e;>{len(ja_lancadas)} ja confirmados nesta data — serao pulados</b>' if ja_lancadas else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**Foto da Turma**")
    origem = st.radio(
        "Origem",
        ["Upload manual", "Usar foto do Diario"],
        horizontal=True,
        label_visibility="collapsed",
    )

    img_grupo = None

    if origem == "Upload manual":
        uploaded = st.file_uploader(
            "Envie a foto da turma",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        if uploaded:
            img_grupo = _upload_para_array(uploaded)
            st.image(uploaded, caption="Foto carregada", use_container_width=True)
    else:
        diario = _buscar_diario_com_foto(turma_id)
        if not diario:
            st.info("Nenhuma entrada no Diario com foto para esta turma.")
        else:
            opcoes_diario = {f"{d['data_aula']} — {d['turma']}": d for d in diario}
            entrada_sel_key = st.selectbox("Aula do diario", list(opcoes_diario.keys()))
            entrada_sel = opcoes_diario[entrada_sel_key]
            try:
                data_aula = datetime.date.fromisoformat(entrada_sel["data_aula"])
            except Exception:
                pass
            arr = _url_para_array(entrada_sel["url_foto_grupo"])
            if arr is not None:
                img_grupo = arr
                st.image(
                    entrada_sel["url_foto_grupo"],
                    caption=f"Diario — {entrada_sel['data_aula']}",
                    use_container_width=True,
                )
            else:
                st.error("Nao foi possivel carregar a foto do diario.")

    st.markdown("---")

    btn_iniciar = st.button(
        f"Iniciar Conferencia ({pendentes_count} alunos para processar)",
        type="primary",
        use_container_width=True,
        disabled=(img_grupo is None or pendentes_count == 0),
    )

    if img_grupo is None:
        st.caption("Forneca a foto da turma para habilitar o reconhecimento.")
    elif pendentes_count == 0:
        st.success(f"Todos os {total_alunos} alunos ja tem frequencia lancada para esta data.")

    if btn_iniciar and img_grupo is not None and pendentes_count > 0:
        grupo_path = _salvar_img_temp(img_grupo)
        pendentes = [a for a in alunos if a["id"] not in ja_lancadas]

        st.session_state["facial_sessao_ativa"] = True
        st.session_state["facial_turma_nome"] = turma_nome
        st.session_state["facial_data_str"] = str(data_aula)
        st.session_state["facial_grupo_path"] = grupo_path
        st.session_state["facial_pendentes"] = pendentes
        st.session_state["facial_alunos_mapa"] = {a["id"]: a for a in alunos}
        st.session_state["facial_confirmados"] = []
        st.session_state["facial_lote_resultado"] = None
        st.session_state["facial_lote_editado"] = {}
        st.rerun()


# ==============================================================================
# Modo 2: Processamento em lotes
# ==============================================================================


def _modo_processamento():
    data_str = st.session_state.get("facial_data_str", "")
    turma_nome = st.session_state.get("facial_turma_nome", "")
    grupo_path = st.session_state.get("facial_grupo_path", "")
    pendentes: list = st.session_state.get("facial_pendentes", [])
    confirmados: list = st.session_state.get("facial_confirmados", [])
    lote_resultado: list | None = st.session_state.get("facial_lote_resultado")

    try:
        data_fmt = datetime.date.fromisoformat(data_str).strftime("%d/%m/%Y")
    except Exception:
        data_fmt = data_str

    total_sessao = len(pendentes) + len(confirmados)
    n_confirmados = len(confirmados)

    # ── Cabecalho da sessao ────────────────────────────────────────────────
    col_info, col_cancel = st.columns([5, 1])
    with col_info:
        st.markdown(
            f"<div style='background:#F0F9FF;border-left:4px solid #0056b3;"
            f"padding:10px 16px;border-radius:6px;font-size:13px;margin-bottom:8px;'>"
            f"<b>{turma_nome}</b> &nbsp;|&nbsp; {data_fmt} &nbsp;|&nbsp; "
            f"<b style='color:#16a34a;'>{n_confirmados} confirmados</b> &nbsp;|&nbsp; "
            f"<b style='color:#92400e;'>{len(pendentes)} pendentes</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_cancel:
        if st.button("Cancelar sessao", use_container_width=True):
            _limpar_sessao()
            st.rerun()

    # Barra de progresso geral
    if total_sessao > 0:
        pct_geral = int((n_confirmados / total_sessao) * 100)
        st.progress(pct_geral, text=f"{n_confirmados}/{total_sessao} alunos conferidos")

    # ── Exibir ja confirmados (resumo colapsavel) ──────────────────────────
    if confirmados:
        with st.expander(f"Ja confirmados nesta sessao ({len(confirmados)} alunos)", expanded=False):
            for r in confirmados:
                icone = "OK" if r["status"] == "PRESENTE" else "--"
                st.markdown(f"**{icone} {r['nome']}** — {r['status']}")

    st.markdown("---")

    # ── Verificar se arquivo de grupo ainda existe ─────────────────────────
    if not grupo_path or not os.path.exists(grupo_path):
        st.error(
            "A foto da turma foi perdida (o servidor pode ter reiniciado). "
            "Cancele a sessao e inicie novamente — os alunos ja confirmados NAO precisam ser reprocessados."
        )
        return

    # ── FASE A: Ha um lote aguardando revisao ─────────────────────────────
    if lote_resultado:
        _mostrar_revisao_lote(lote_resultado, data_str, data_fmt, pendentes, confirmados)
        return

    # ── FASE B: Ha alunos pendentes — processar proximo lote ──────────────
    if pendentes:
        proximo_lote = pendentes[:LOTE_SIZE]
        nomes_lote = ", ".join(a["nome"].split()[0] for a in proximo_lote)

        st.markdown(
            f"<div style='background:#FFFBEB;border-left:4px solid #F59E0B;"
            f"padding:10px 16px;border-radius:6px;margin-bottom:12px;font-size:13px;'>"
            f"<b>Proximo lote ({len(proximo_lote)} alunos):</b> {nomes_lote}"
            f"</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            f"Analisar proximo lote ({len(proximo_lote)} alunos)",
            type="primary",
            use_container_width=True,
        ):
            _processar_lote(proximo_lote, grupo_path)
        return

    # ── FASE C: Todos processados — resumo final ───────────────────────────
    _mostrar_resumo_final(confirmados, data_fmt)


def _processar_lote(lote: list, grupo_path: str):
    barra = st.progress(0, text="Preparando analise...")
    resultados_lote = []
    total = len(lote)

    for i, aluno in enumerate(lote):
        pct = int((i / total) * 100)
        barra.progress(pct, text=f"Analisando {i + 1}/{total}: {aluno['nome'][:30]}...")
        resultado = _reconhecer_aluno(grupo_path, aluno)
        resultados_lote.append(resultado)

    barra.progress(100, text="Lote analisado!")

    st.session_state["facial_lote_resultado"] = resultados_lote
    st.session_state["facial_lote_editado"] = {r["aluno_id"]: r["status"] for r in resultados_lote}
    st.rerun()


def _mostrar_revisao_lote(
    lote_resultado: list, data_str: str, data_fmt: str,
    pendentes: list, confirmados: list
):
    st.markdown(
        f"<h4 style='color:#0A2540;margin-bottom:8px;'>"
        f"Revise o lote ({len(lote_resultado)} alunos) — {data_fmt}</h4>",
        unsafe_allow_html=True,
    )

    lote_editado: dict = st.session_state.get("facial_lote_editado", {})

    for r in lote_resultado:
        aluno_id = r["aluno_id"]
        nome = r["nome"]
        conf = r["confianca"]
        tem_foto = r["tem_foto"]
        motivo = r.get("motivo", "")
        status_atual = lote_editado.get(aluno_id, r["status"])

        with st.container(border=True):
            c_nome, c_conf, c_status = st.columns([3, 2, 2])

            with c_nome:
                icone = "OK" if status_atual == "PRESENTE" else "--"
                st.markdown(f"**{icone} {nome}**")
                if not tem_foto:
                    st.caption("Sem foto cadastrada")
                elif motivo:
                    st.caption(f"{motivo}")

            with c_conf:
                if tem_foto and not motivo:
                    cor = "#16a34a" if conf >= 50 else "#dc2626"
                    nivel = "Alta" if conf >= 70 else ("Media" if conf >= 40 else "Baixa")
                    st.markdown(
                        f"<span style='color:{cor};font-weight:700;font-size:13px;'>"
                        f"Confianca: {conf}%</span><br>"
                        f"<span style='font-size:11px;color:#64748B;'>{nivel}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("—")

            with c_status:
                novo_status = st.selectbox(
                    "Status",
                    ["PRESENTE", "FALTA"],
                    index=0 if status_atual == "PRESENTE" else 1,
                    key=f"lote_sel_{aluno_id}",
                    label_visibility="collapsed",
                )
                lote_editado[aluno_id] = novo_status

    st.session_state["facial_lote_editado"] = lote_editado

    # Resumo do lote
    n_presentes = sum(1 for v in lote_editado.values() if v == "PRESENTE")
    n_faltas = sum(1 for v in lote_editado.values() if v == "FALTA")

    st.markdown(
        f"<div style='background:#F0FDF4;border:1px solid #86efac;border-radius:8px;"
        f"padding:10px 16px;margin:8px 0;font-size:13px;'>"
        f"Este lote: <b style='color:#16a34a;'>{n_presentes} PRESENTE(S)</b> &nbsp;|&nbsp; "
        f"<b style='color:#dc2626;'>{n_faltas} FALTA(S)</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_confirmar, col_reanalisar = st.columns([2, 1])

    with col_confirmar:
        if st.button(
            f"Confirmar e gravar este lote",
            type="primary",
            use_container_width=True,
        ):
            # Montar lista final com status editado
            lista_gravar = [
                {"aluno_id": r["aluno_id"], "nome": r["nome"], "status": lote_editado[r["aluno_id"]]}
                for r in lote_resultado
            ]

            with st.spinner("Gravando lote no banco..."):
                _gravar_lote(lista_gravar, data_str)

            # Atualizar estado: mover do pendentes para confirmados
            ids_lote = {r["aluno_id"] for r in lote_resultado}
            novos_pendentes = [a for a in pendentes if a["id"] not in ids_lote]
            novos_confirmados = confirmados + lista_gravar

            st.session_state["facial_pendentes"] = novos_pendentes
            st.session_state["facial_confirmados"] = novos_confirmados
            st.session_state["facial_lote_resultado"] = None
            st.session_state["facial_lote_editado"] = {}
            st.rerun()

    with col_reanalisar:
        if st.button("Reanalisar este lote", use_container_width=True):
            grupo_path = st.session_state.get("facial_grupo_path", "")
            if not grupo_path or not os.path.exists(grupo_path):
                st.error("Foto da turma perdida — cancele e reinicie.")
            else:
                alunos_mapa = st.session_state.get("facial_alunos_mapa", {})
                ids_lote = {r["aluno_id"] for r in lote_resultado}
                # Reconstruir dicts completos do lote usando o mapa original
                alunos_lote = [
                    alunos_mapa[aid]
                    for aid in ids_lote
                    if aid in alunos_mapa
                ]
                # Colocar de volta na frente da fila
                pendentes_sem_lote = [a for a in pendentes if a["id"] not in ids_lote]
                st.session_state["facial_pendentes"] = alunos_lote + pendentes_sem_lote
                st.session_state["facial_lote_resultado"] = None
                st.session_state["facial_lote_editado"] = {}
                st.rerun()


def _mostrar_resumo_final(confirmados: list, data_fmt: str):
    presentes_final = [r for r in confirmados if r["status"] == "PRESENTE"]
    faltas_final = [r for r in confirmados if r["status"] == "FALTA"]

    st.markdown(
        f"<div style='background:#F0FDF4;border:2px solid #16a34a;border-radius:10px;"
        f"padding:16px 20px;margin-bottom:16px;'>"
        f"<h4 style='color:#15803d;margin:0 0 8px 0;'>Conferencia concluida — {data_fmt}</h4>"
        f"<b style='color:#16a34a;font-size:18px;'>{len(presentes_final)} PRESENTES</b> &nbsp;|&nbsp; "
        f"<b style='color:#dc2626;font-size:18px;'>{len(faltas_final)} FALTAS</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Ver detalhes completos", expanded=False):
        for r in sorted(confirmados, key=lambda x: (0 if x["status"] == "PRESENTE" else 1)):
            icone = "PRESENTE" if r["status"] == "PRESENTE" else "FALTA"
            st.markdown(f"**{icone}** — {r['nome']}")

    if st.button("Nova conferencia", type="primary", use_container_width=True):
        _limpar_sessao()
        st.rerun()


def _limpar_sessao():
    grupo_path = st.session_state.get("facial_grupo_path", "")
    if grupo_path:
        try:
            os.unlink(grupo_path)
        except Exception:
            pass

    for k in [
        "facial_sessao_ativa", "facial_turma_nome", "facial_data_str",
        "facial_grupo_path", "facial_pendentes", "facial_pendentes_completo",
        "facial_confirmados", "facial_lote_resultado", "facial_lote_editado",
    ]:
        st.session_state.pop(k, None)
