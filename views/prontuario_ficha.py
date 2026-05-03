# ==============================================================================
# 📄 Arquivo: views/prontuario_ficha.py
# 📅 Versão: 5.1 (PRO Elite - Modular + Blindagem Anti-NaN SQL/JSON)
# ⚙️ Função: Gestão individual cirúrgica. Código limpo, modular e escalável.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io
import time
import uuid
import requests
import math
from PIL import Image, ImageOps

from database import (
    salvar_avaliacao_prontuario,
    get_avaliacoes_aluno,
    atualizar_turma_aluno,
    excluir_avaliacao_prontuario,
    revisar_texto_ia,
    get_historico_aulas_aluno,
    get_estatisticas_frequencia_aluno,
    get_todas_turmas,
    get_ocupacao_turmas,
    get_atestados_temporarios,
    salvar_atestado_temporario,
    atualizar_dados_sociais_aluno,
    excluir_aluno_completo,
    ADMIN_MASTER,
    supabase,
)
from views.anamnese_dores_view import render_aba_mapa_dores

try:
    from gerador_pdf import criar_documento_aluno_pdf
except ImportError:
    st.error("Erro: Arquivo gerador_pdf.py não encontrado.")


# ==============================================================================
# 🛡️ FUNÇÃO DE BLINDAGEM DE DADOS (QA SÊNIOR)
# ==============================================================================
def blindar_float(valor):
    """Garante que nenhum valor NaN ou Infinity quebre o JSON do Supabase."""
    try:
        if pd.isna(valor):
            return 0.0
        val = float(valor)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0


# ==============================================================================
# 🛠️ 1. MOTORES SEGUROS E DIAGNÓSTICO
# ==============================================================================
def alterar_status_aluno_local(aluno_id, novo_status):
    try:
        supabase.from_("alunos").update({"status": novo_status}).eq(
            "id", str(aluno_id)
        ).execute()
        return True, f"Status alterado para {novo_status}"
    except Exception as e:
        return False, str(e)


def excluir_atestado_temporario_local(atestado_id):
    try:
        supabase.table("atestados_temporarios").delete().eq(
            "id", str(atestado_id)
        ).execute()
        return True, "Atestado removido."
    except Exception as e:
        return False, str(e)


def atualizar_perfil_aluno_dict_seguro(aluno_id, dados_atualizados):
    try:
        supabase.from_("alunos").update(dados_atualizados).eq(
            "id", str(aluno_id)
        ).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


def upload_midia_diagnostico(
    file_bytes, file_name, mime_type, bucket="diario_midias_imbra"
):
    try:
        nome_u = f"upload_{uuid.uuid4().hex[:8]}.{file_name.split('.')[-1]}"
        supabase.storage.from_(bucket).upload(
            path=nome_u, file=file_bytes, file_options={"content-type": mime_type}
        )
        url_publica = supabase.storage.from_(bucket).get_public_url(nome_u)
        return url_publica, None
    except Exception as e:
        return None, str(e)


def processar_foto_perfil(file_bytes):
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        try:
            filtro = Image.Resampling.LANCZOS
        except AttributeError:
            filtro = Image.LANCZOS
        img = ImageOps.fit(img, (300, 300), method=filtro, centering=(0.5, 0.5))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "perfil.jpg", "image/jpeg"
    except Exception:
        return None, None, None


def rotacionar_imagem_supabase(aluno_id, url_atual, angulo):
    try:
        resposta = requests.get(url_atual)
        if resposta.status_code != 200:
            return False, "Falha ao descarregar a imagem."
        img = Image.open(io.BytesIO(resposta.content))
        img_rotacionada = img.rotate(angulo, expand=True)
        if img_rotacionada.mode == "RGBA":
            img_rotacionada = img_rotacionada.convert("RGB")
        buf = io.BytesIO()
        img_rotacionada.save(buf, format="JPEG", quality=85)
        nova_url, erro = upload_midia_diagnostico(
            buf.getvalue(), "foto_rotacionada.jpg", "image/jpeg"
        )
        if nova_url:
            sucesso, msg = atualizar_perfil_aluno_dict_seguro(
                aluno_id, {"url_foto": nova_url}
            )
            return (True, nova_url) if sucesso else (False, f"Erro BD: {msg}")
        return False, f"Erro Upload: {erro}"
    except Exception as e:
        return False, f"Erro Crítico: {str(e)}"


from views.utils_docs import url_eh_imagem, renderizar_documento_com_rotacao


def processar_documento_prontuario(file_bytes, file_name, file_type):
    try:
        if "image" in file_type:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            try:
                filtro = Image.Resampling.LANCZOS
            except AttributeError:
                filtro = Image.LANCZOS
            img.thumbnail((1500, 1500), filtro)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue(), f"doc_{file_name.split('.')[0]}.jpg", "image/jpeg"
        return file_bytes, file_name, file_type
    except Exception:
        return file_bytes, file_name, file_type


def analisar_saude_visual(aval):
    try:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        dor = int(blindar_float(aval.get("dor_nivel") or aval.get("nivel_dor") or 0))
        carinha = "😃" if dor <= 2 else ("😐" if dor <= 5 else "😟")
        col1.metric("Nível de Dor", f"{carinha} {dor}/10")

        tug = blindar_float(aval.get("tug_simples") or aval.get("tug") or 0.0)
        col2.metric("Equilíbrio (TUG)", f"{tug}s", delta_color="inverse")

        f_d = blindar_float(aval.get("forca_dir") or 0.0)
        f_e = blindar_float(aval.get("forca_esq") or 0.0)
        with col3:
            st.markdown("**Simetria de Força**")
            if f_d > 0 or f_e > 0:
                fig = px.pie(
                    values=[f_d, f_e],
                    names=["Dir", "Esq"],
                    hole=0.4,
                    color_discrete_sequence=["#1f77b4", "#ff7f0e"],
                )
                fig.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0), height=100, showlegend=False
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key=f"chart_pie_{aval.get('id', 'temp')}",
                )
            else:
                st.caption("Sem dados.")

        bristol_v, urina_v, borg_v = (
            aval.get("bristol", "Não avaliado"),
            aval.get("urina", "Não avaliado"),
            aval.get("borg", "Não avaliado"),
        )
        if (
            bristol_v != "Não avaliado"
            or urina_v != "Não avaliado"
            or borg_v != "Não avaliado"
        ):
            st.markdown(
                "<br>**Marcadores Fisiológicos Atuais:**", unsafe_allow_html=True
            )
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.info(f"🏋️ **Borg:** {borg_v}")
            c_m2.warning(f"💩 **Bristol:** {bristol_v}")
            c_m3.success(f"💧 **Urina:** {urina_v}")
    except Exception:
        st.error("Erro ao processar gráficos visuais.")


# ==============================================================================
# 🧩 2. COMPONENTES MODULARES DA INTERFACE
# ==============================================================================


def render_formulario_medicao(aluno, edit=None):
    """Componente: Formulário de Medição Clínica"""
    suffix = f"_{edit['id']}" if edit else "_new"
    try:
        d_val = (
            datetime.datetime.strptime(edit["data_avaliacao"], "%Y-%m-%d").date()
            if edit
            else datetime.date.today()
        )
    except:
        d_val = datetime.date.today()
    if d_val > datetime.date.today():
        d_val = datetime.date.today()

    d_av = st.date_input(
        "Data do Atendimento:", value=d_val, key=f"dav{suffix}", format="DD/MM/YYYY"
    )

    st.markdown("#### 1. Anamnese")
    c1, c2 = st.columns(2)
    dor = c1.slider(
        "Escala de Dor (0-10):",
        0,
        10,
        value=int(blindar_float(edit.get("dor_nivel") if edit else 0)),
        key=f"dor{suffix}",
    )
    quedas = c2.number_input(
        "Quedas (últimos 6 meses):",
        min_value=0,
        value=int(blindar_float(edit.get("quedas_6m") if edit else 0)),
        key=f"q{suffix}",
    )
    cirurgias = st.text_input(
        "Cirurgias / Lesões Recentes:",
        value=edit.get("cirurgias", "") if edit else "",
        key=f"cir{suffix}",
    )
    meds = st.text_area(
        "Medicamentos / Observações:",
        value=edit.get("medicamentos", "") if edit else "",
        height=80,
        key=f"meds{suffix}",
    )

    st.markdown("#### 2. Testes Físicos")
    c3, c4 = st.columns(2)
    op_mob = ["Não testado", "Não alcança", "Toca nos pés", "Passa dos pés"]
    mob_d = c3.selectbox(
        "Mobilidade (Perna Dir):",
        op_mob,
        index=op_mob.index(edit.get("mobilidade_pes_dir", "Não testado"))
        if edit and edit.get("mobilidade_pes_dir") in op_mob
        else 0,
        key=f"md{suffix}",
    )
    mob_e = c4.selectbox(
        "Mobilidade (Perna Esq):",
        op_mob,
        index=op_mob.index(edit.get("mobilidade_pes_esq", "Não testado"))
        if edit and edit.get("mobilidade_pes_esq") in op_mob
        else 0,
        key=f"me{suffix}",
    )

    c5, c6 = st.columns(2)
    f_d = c5.number_input(
        "Força Dir (Reps):",
        value=int(blindar_float(edit.get("forca_dir") if edit else 0)),
        key=f"fd{suffix}",
    )
    f_e = c6.number_input(
        "Força Esq (Reps):",
        value=int(blindar_float(edit.get("forca_esq") if edit else 0)),
        key=f"fe{suffix}",
    )

    st.markdown("#### 3. TUG (Timed Up and Go)")
    c7, c8, c9 = st.columns(3)
    tug1 = c7.number_input(
        "Simples (s):",
        value=blindar_float(edit.get("tug_simples") if edit else 0),
        key=f"t1{suffix}",
    )
    tug2 = c8.number_input(
        "Cog. Animais (s):",
        value=blindar_float(edit.get("tug_cog_animais") if edit else 0),
        key=f"t2{suffix}",
    )
    tug3 = c9.number_input(
        "Cog. Perguntas (s):",
        value=blindar_float(edit.get("tug_cog_perguntas") if edit else 0),
        key=f"t3{suffix}",
    )

    st.markdown("<br>#### 4. Marcadores Clínicos e Biofeedback", unsafe_allow_html=True)
    borg_op = [
        "0 - Repouso",
        "2 - Leve",
        "4 - Pouco Cansativo",
        "6 - Cansativo",
        "8 - Muito Pesado",
        "10 - Exaustivo",
    ]
    borg = st.select_slider(
        "🏋️ Escala de Borg:",
        options=borg_op,
        value=next(
            (x for x in borg_op if str(edit.get("borg", "4") if edit else "4") in x),
            "4 - Pouco Cansativo",
        ),
        key=f"borg{suffix}",
    )

    c10, c11 = st.columns(2)
    bristol_op = [
        "Tipo 1: Caroços duros (Constipação Severa)",
        "Tipo 2: Forma de salsicha, grumoso (Constipação Leve)",
        "Tipo 3: Salsicha com rachaduras (Normal)",
        "Tipo 4: Salsicha lisa e macia (Ótimo)",
        "Tipo 5: Pedaços macios (Falta de Fibra)",
        "Tipo 6: Pastoso, fofo (Diarreia Leve)",
        "Tipo 7: Aquoso, líquido (Diarreia Severa)",
    ]
    bristol = c10.selectbox(
        "💩 Escala de Bristol:",
        bristol_op,
        index=next(
            (
                i
                for i, v in enumerate(bristol_op)
                if str(edit.get("bristol", "Tipo 3") if edit else "Tipo 3") in v
            ),
            2,
        ),
        key=f"bris{suffix}",
    )

    urina_op = [
        "Nível 1 - Transparente (Excesso de Água)",
        "Nível 2 - Amarelo Muito Claro (Ótimo)",
        "Nível 3 - Amarelo Claro (Bom)",
        "Nível 4 - Amarelo (Desidratação Leve)",
        "Nível 5 - Amarelo Escuro (Desidratação Moderada)",
        "Nível 6 - Âmbar (Desidratação Severa)",
        "Nível 7 - Castanho (Alerta Médico)",
    ]
    urina = c11.selectbox(
        "💧 Cor da Urina:",
        urina_op,
        index=next(
            (
                i
                for i, v in enumerate(urina_op)
                if str(edit.get("urina", "Nível 2") if edit else "Nível 2") in v
            ),
            1,
        ),
        key=f"uri{suffix}",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    def salvar_medicao_backend():
        borg_clean, bristol_clean, urina_clean = (
            borg.split(" - ")[0],
            bristol.split(":")[0],
            urina.split(" - ")[0],
        )
        sug = revisar_texto_ia(meds)
        final_meds = sug if sug else meds
        return salvar_avaliacao_prontuario(
            aluno["id"],
            d_av,
            dor,
            quedas,
            cirurgias,
            final_meds,
            mob_d,
            mob_e,
            f_d,
            f_e,
            tug1,
            tug2,
            tug3,
            edit["id"] if edit else None,
            bristol_clean,
            urina_clean,
            borg_clean,
        )

    if edit:
        c_save, c_cancel = st.columns(2)
        if c_save.button(
            "💾 Salvar Alterações",
            type="primary",
            use_container_width=True,
            key=f"bsave{suffix}",
        ):
            with st.spinner("A atualizar medição..."):
                sucesso, msg = salvar_medicao_backend()
                if sucesso:
                    st.cache_data.clear()
                    st.success("✅ Alterações salvas com sucesso! 🏋️‍♂️")
                    time.sleep(1.5)
                    st.session_state.medicao_editar = None
                    st.rerun()
                else:
                    st.error(f"Erro: {msg}")
        if c_cancel.button(
            "❌ Cancelar Edição", use_container_width=True, key=f"bcancel{suffix}"
        ):
            st.session_state.medicao_editar = None
            st.rerun()
    else:
        if st.button(
            "💾 Salvar Nova Medição Clínica",
            type="primary",
            use_container_width=True,
            key="bsavenew",
        ):
            historico = get_avaliacoes_aluno(aluno["id"])
            datas_existentes = (
                [a.get("data_avaliacao") for a in historico]
                if not historico.empty
                else []
            )
            if str(d_av) in datas_existentes:
                st.error(
                    f"⚠️ Atenção: Já existe medição na data {d_av.strftime('%d/%m/%Y')}."
                )
            else:
                with st.spinner("A guardar..."):
                    sucesso, msg = salvar_medicao_backend()
                    if sucesso:
                        st.cache_data.clear()
                        st.toast("Medição salva com sucesso!", icon="🩺")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"Erro: {msg}")


def _render_painel_exclusao(aluno):
    """Painel de confirmação de exclusão permanente — somente leitura + confirmação textual."""
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "<div style='background:#FEE2E2;border-left:5px solid #DC2626;"
            "padding:12px 16px;border-radius:6px;margin-bottom:12px;'>"
            "<strong style='color:#991B1B;font-size:16px'>⛔ Zona de Exclusão Permanente</strong><br>"
            "<span style='color:#7F1D1D;font-size:13px'>Esta ação remove o aluno e "
            "<u>todos</u> os seus registos (presenças, avaliações, atestados, documentos). "
            "Não há recuperação.</span></div>",
            unsafe_allow_html=True,
        )

        # ── Resumo compacto somente leitura ───────────────────────────────────
        st.markdown("##### 📋 Dados do aluno que será excluído")

        def campo(label, valor):
            v = str(valor).strip() if valor and str(valor).strip().lower() not in ("nan","none","") else "—"
            return f"<b>{label}:</b> {v}"

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(
                f"<div style='background:#FFF8F8;padding:10px 14px;border-radius:8px;"
                f"border:1px solid #FECACA;font-size:13px;line-height:2'>"
                f"{campo('Nome', aluno.get('nome'))}<br>"
                f"{campo('Turma', aluno.get('turma'))}<br>"
                f"{campo('Status', aluno.get('status'))}<br>"
                f"{campo('Nascimento', aluno.get('data_nascimento'))}"
                f"</div>", unsafe_allow_html=True
            )
        with col_b:
            st.markdown(
                f"<div style='background:#FFF8F8;padding:10px 14px;border-radius:8px;"
                f"border:1px solid #FECACA;font-size:13px;line-height:2'>"
                f"{campo('CPF', aluno.get('cpf'))}<br>"
                f"{campo('RG', aluno.get('rg'))}<br>"
                f"{campo('WhatsApp', aluno.get('whatsapp'))}<br>"
                f"{campo('E-mail', aluno.get('email'))}"
                f"</div>", unsafe_allow_html=True
            )
        with col_c:
            st.markdown(
                f"<div style='background:#FFF8F8;padding:10px 14px;border-radius:8px;"
                f"border:1px solid #FECACA;font-size:13px;line-height:2'>"
                f"{campo('Endereço', aluno.get('endereco'))}<br>"
                f"{campo('Bairro', aluno.get('bairro'))}<br>"
                f"{campo('Contato Emerg.', aluno.get('contato_emergencia'))}<br>"
                f"{campo('Restrições', aluno.get('restricoes_fisicas'))}"
                f"</div>", unsafe_allow_html=True
            )

        if aluno.get("problemas_saude") or aluno.get("medicamentos"):
            st.markdown(
                f"<div style='background:#FFF8F8;padding:8px 14px;border-radius:8px;"
                f"border:1px solid #FECACA;font-size:13px;margin-top:8px'>"
                f"{campo('Problemas de Saúde', aluno.get('problemas_saude'))} &nbsp;|&nbsp; "
                f"{campo('Medicamentos', aluno.get('medicamentos'))}"
                f"</div>", unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Confirmação textual ────────────────────────────────────────────────
        nome_aluno = str(aluno.get("nome", "")).strip()
        st.markdown(
            f"Para confirmar a exclusão de **{nome_aluno}**, "
            f"digite o nome completo exatamente como aparece acima:"
        )
        c_inp, c_btn, c_cancel = st.columns([3, 1.5, 1.5])
        confirmacao = c_inp.text_input(
            "Confirmação:", key="exclusao_nome_confirmacao",
            placeholder=nome_aluno, label_visibility="collapsed"
        )
        nome_digitado = confirmacao.strip().upper()
        nome_esperado = nome_aluno.strip().upper()
        habilitado    = nome_digitado == nome_esperado

        with c_btn:
            if st.button(
                "🗑️ EXCLUIR DEFINITIVAMENTE",
                type="primary",
                use_container_width=True,
                disabled=not habilitado,
                key="btn_confirmar_exclusao_final",
            ):
                email_user = st.session_state.get("usuario_email", "")
                ok, msg = excluir_aluno_completo(aluno["id"], email_user)
                if ok:
                    st.session_state.aluno_prontuario = None
                    st.session_state.painel_exclusao_aberto = False
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.toast(f"Aluno {nome_aluno} excluído.", icon="🗑️")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)

        with c_cancel:
            if st.button("✖ Cancelar", use_container_width=True, key="btn_cancelar_exclusao"):
                st.session_state.painel_exclusao_aberto = False
                st.rerun()


def render_cabecalho_aluno(aluno):
    """Componente: Cabeçalho superior, foto e botões de ação do Dossiê."""
    col_titulo, col_voltar = st.columns([4, 2], vertical_alignment="center")
    with col_titulo:
        st.title("🩺 Ficha Digital do Aluno")
    with col_voltar:
        origem = st.session_state.get("origem_prontuario")
        mapa = {"Frequência": "Turmas", "Principal": "Início"}
        if st.button(
            f"🔙 Voltar p/ {mapa.get(origem, origem) if origem else 'Portal'}",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state.aluno_prontuario = None
            st.session_state.medicao_editar = None
            if origem:
                st.session_state.menu_atual = origem
                del st.session_state["origem_prontuario"]
            st.rerun()
    st.divider()

    u_v = aluno.get("url_foto")
    cp_f, cp_i, cp_pdf, cp_word = st.columns([1.2, 4.3, 0.9, 0.9], vertical_alignment="center")
    with cp_f:
        if pd.notna(u_v) and str(u_v).strip().lower() not in [
            "none",
            "nan",
            "null",
            "",
        ]:
            st.markdown(
                f'<img src="{u_v}" class="zoom-avatar-lg">', unsafe_allow_html=True
            )
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            c_esq, c_dir = st.columns(2)
            if c_esq.button(
                "↺", key="rot_esq", help="Girar esquerda", use_container_width=True
            ):
                with st.spinner("🔄"):
                    ok, url = rotacionar_imagem_supabase(aluno["id"], u_v, 90)
                    if ok:
                        st.session_state.aluno_prontuario["url_foto"] = url
                        st.rerun()
            if c_dir.button(
                "↻", key="rot_dir", help="Girar direita", use_container_width=True
            ):
                with st.spinner("🔄"):
                    ok, url = rotacionar_imagem_supabase(aluno["id"], u_v, -90)
                    if ok:
                        st.session_state.aluno_prontuario["url_foto"] = url
                        st.rerun()
        else:
            st.markdown(
                '<div style="font-size:45px;background:#f0f2f6;border-radius:50%;text-align:center;width:90px;height:90px;line-height:90px;border:3px solid #1E88E5; color:#94A3B8;">👤</div>',
                unsafe_allow_html=True,
            )

    with cp_i:
        st_badge = (
            "<span style='background:#DCFCE7; color:#166534; padding:3px 10px; border-radius:12px; font-size:14px; margin-left: 10px;'>Ativo</span>"
            if aluno.get("status", "Ativo") != "Inativo"
            else "<span style='background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:12px; font-size:14px; margin-left: 10px;'>Inativo</span>"
        )
        st.markdown(
            f"<h2 style='margin-bottom:0px; display:inline-block;'>{aluno.get('nome', '')}</h2> {st_badge}",
            unsafe_allow_html=True,
        )
        st.caption(f"Turma: {aluno.get('turma', '')}")

    with cp_pdf:
        pdf_bytes = criar_documento_aluno_pdf(
            aluno,
            get_avaliacoes_aluno(aluno.get("id")),
            get_historico_aulas_aluno(aluno.get("id")),
            get_estatisticas_frequencia_aluno(aluno.get("id")),
        )
        st.download_button(
            "🖨️ PDF Dossiê",
            data=pdf_bytes,
            file_name=f"Dossie_{aluno.get('nome', '')[:15].replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    with cp_word:
        _wkey = f"word_ficha_{aluno.get('id')}"
        if st.session_state.get(_wkey):
            st.download_button(
                "📥 Word",
                data=st.session_state[_wkey],
                file_name=f"Dossie_{aluno.get('nome', '')[:15].replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        elif st.button("📘 Word Dossiê", use_container_width=True):
            with st.spinner("A gerar Word..."):
                try:
                    from gerador_word import criar_documento_aluno_word
                    _wb = criar_documento_aluno_word(
                        aluno,
                        get_avaliacoes_aluno(aluno.get("id")),
                        get_historico_aulas_aluno(aluno.get("id")),
                        get_estatisticas_frequencia_aluno(aluno.get("id")),
                    )
                    if _wb:
                        st.session_state[_wkey] = _wb
                        st.rerun()
                except Exception as _e:
                    st.error(f"Erro Word: {_e}")
        if aluno.get("status", "Ativo") != "Inativo":
            if st.button("🗄️ Arquivar Aluno", use_container_width=True):
                ok, _ = alterar_status_aluno_local(aluno["id"], "Inativo")
                if ok:
                    aluno["status"] = "Inativo"
                    st.session_state.aluno_prontuario = None
                    st.rerun()
        else:
            if st.button("♻️ Reativar Aluno", type="primary", use_container_width=True):
                ok, _ = alterar_status_aluno_local(aluno["id"], "Ativo")
                if ok:
                    aluno["status"] = "Ativo"
                    st.rerun()

        email_user = st.session_state.get("usuario_email", "")
        if email_user.lower() == ADMIN_MASTER.lower():
            if st.button(
                "🗑️ Excluir Aluno",
                use_container_width=True,
                key="btn_abrir_exclusao",
                help="Exclusão permanente — apenas admin mestre",
            ):
                st.session_state["painel_exclusao_aberto"] = not st.session_state.get(
                    "painel_exclusao_aberto", False
                )

    # ── Painel de confirmação de exclusão ─────────────────────────────────────
    if st.session_state.get("painel_exclusao_aberto", False):
        _render_painel_exclusao(aluno)


def render_aba_perfil(aluno):
    """Componente: Aba de Informações Pessoais (Com Blindagem de Dados)."""
    with st.container(border=True):
        c_head, c_top_btn = st.columns([4, 1], vertical_alignment="center")
        c_head.markdown("#### 👤 Informações Pessoais")
        btn_save_top = c_top_btn.button(
            "💾 Guardar",
            key="save_top_perfil",
            type="primary",
            use_container_width=True,
        )

        col_n, col_t, col_d = st.columns([2, 1.5, 1])
        n_ed = col_n.text_input(
            "Nome Completo:",
            value="" if pd.isna(aluno.get("nome")) else str(aluno.get("nome")),
        )

        df_turmas_ativas = get_todas_turmas(ativas_apenas=True)
        ocupacao = get_ocupacao_turmas()
        lista_turmas_display, mapa_turmas = [], {}

        for t_nome in df_turmas_ativas["nome"].tolist():
            info = ocupacao.get(t_nome, {})
            vagas = info.get("vagas", 40)
            if vagas <= 0:
                display = f"🔴 {t_nome} (LOTADA)"
            elif vagas <= 5:
                display = f"🟡 {t_nome} (ALERTA)"
            else:
                display = f"🟢 {t_nome} ({vagas} vagas livres)"
            lista_turmas_display.append(display)
            mapa_turmas[display] = t_nome

        turma_atual = aluno.get("turma", "")
        if turma_atual and turma_atual not in mapa_turmas.values():
            display_atual = f"⚪ {turma_atual} (Antiga/Inativa)"
            lista_turmas_display.insert(0, display_atual)
            mapa_turmas[display_atual] = turma_atual

        idx = next(
            (
                i
                for i, d in enumerate(lista_turmas_display)
                if mapa_turmas[d] == turma_atual
            ),
            0,
        )
        t_ed_display = col_t.selectbox("Turma Atual:", lista_turmas_display, index=idx)
        t_ed_salvar = mapa_turmas[t_ed_display]

        data_bd = aluno.get("data_nascimento")
        hoje = datetime.date.today()
        limite_min = datetime.date(1920, 1, 1)
        data_padrao = datetime.date(2000, 1, 1)
        try:
            if pd.notna(data_bd) and str(data_bd).strip().lower() not in [
                "nan",
                "none",
                "nat",
                "",
            ]:
                dt_parsed = pd.to_datetime(data_bd).date()
                if dt_parsed > hoje:
                    try:
                        dt_parsed = dt_parsed.replace(year=dt_parsed.year - 100)
                    except ValueError:
                        dt_parsed = hoje
                if limite_min <= dt_parsed <= hoje:
                    data_padrao = dt_parsed
                elif dt_parsed < limite_min:
                    data_padrao = limite_min
                else:
                    data_padrao = hoje
        except Exception:
            pass
        d_ed = col_d.date_input("Nascimento:", value=data_padrao, min_value=limite_min, max_value=hoje, format="DD/MM/YYYY")

        st.markdown("#### 📸 Foto de Perfil")
        foto_nova = st.file_uploader(
            "Trocar Foto:", type=["jpg", "png", "jpeg"], label_visibility="collapsed"
        )

        st.markdown("#### 🪪 Documentos e Endereço")
        c_cpf, c_rg = st.columns(2)
        cpf_ed = c_cpf.text_input(
            "CPF:", value="" if pd.isna(aluno.get("cpf")) else str(aluno.get("cpf"))
        )
        rg_ed = c_rg.text_input(
            "RG:", value="" if pd.isna(aluno.get("rg")) else str(aluno.get("rg"))
        )

        c_end, c_bai, c_cep = st.columns([2, 1, 1])
        end_ed = c_end.text_input(
            "Endereço Completo:",
            value="" if pd.isna(aluno.get("endereco")) else str(aluno.get("endereco")),
        )
        bai_ed = c_bai.text_input(
            "Bairro:",
            value="" if pd.isna(aluno.get("bairro")) else str(aluno.get("bairro")),
        )
        cep_ed = c_cep.text_input(
            "CEP:", value="" if pd.isna(aluno.get("cep")) else str(aluno.get("cep"))
        )

        st.markdown("#### 📱 Biometria e Contactos")
        c_p, c_a, c_w, c_e = st.columns([1, 1, 2, 2])

        # 🚀 AQUI A BLINDAGEM ENTRA EM AÇÃO PARA PESO E ALTURA
        p_ed = c_p.number_input(
            "Peso (kg):", value=blindar_float(aluno.get("peso")), step=0.1
        )
        a_ed = c_a.number_input(
            "Altura (m):", value=blindar_float(aluno.get("altura")), step=0.01
        )

        w_ed = c_w.text_input(
            "WhatsApp:",
            value="" if pd.isna(aluno.get("whatsapp")) else str(aluno.get("whatsapp")),
        )
        e_ed = c_e.text_input(
            "E-mail:",
            value="" if pd.isna(aluno.get("email")) else str(aluno.get("email")),
        )

        st.markdown("#### 🏥 Saúde e Alertas")
        cont_em_ed = st.text_input(
            "Contato de Emergência:",
            value=""
            if pd.isna(aluno.get("contato_emergencia"))
            else str(aluno.get("contato_emergencia")),
        )
        c_s1, c_s2 = st.columns(2)
        prob_ed = c_s1.text_area(
            "Problemas de Saúde:",
            value=""
            if pd.isna(aluno.get("problemas_saude"))
            else str(aluno.get("problemas_saude")),
        )
        meds_ed = c_s2.text_area(
            "Uso de Medicamentos:",
            value=""
            if pd.isna(aluno.get("medicamentos"))
            else str(aluno.get("medicamentos")),
        )
        rest_ed = st.text_input(
            "Restrições Físicas:",
            value=""
            if pd.isna(aluno.get("restricoes_fisicas"))
            else str(aluno.get("restricoes_fisicas")),
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_save_bot = st.button(
            "💾 Guardar Cadastro Completo",
            key="save_bot_perfil",
            type="primary",
            use_container_width=True,
        )

        if btn_save_top or btn_save_bot:
            with st.spinner("A guardar perfil..."):
                nova_url, upload_ok = aluno.get("url_foto"), True
                if foto_nova:
                    img_b, f_n, f_t = processar_foto_perfil(foto_nova.getvalue())
                    if img_b:
                        url_temp, erro = upload_midia_diagnostico(img_b, f_n, f_t)
                        if url_temp:
                            nova_url = url_temp
                        else:
                            upload_ok = False
                            st.error(f"❌ Falha Storage: {erro}")

                if upload_ok:
                    dados_salvar = {
                        "nome": n_ed.upper().strip(),
                        "turma": t_ed_salvar,
                        "data_nascimento": str(d_ed),
                        "peso": blindar_float(p_ed),
                        "altura": blindar_float(a_ed),
                        "whatsapp": w_ed,
                        "email": e_ed,
                        "url_foto": nova_url,
                        "cpf": cpf_ed,
                        "rg": rg_ed,
                        "endereco": end_ed,
                        "bairro": bai_ed,
                        "cep": cep_ed,
                        "contato_emergencia": cont_em_ed,
                        "problemas_saude": prob_ed,
                        "medicamentos": meds_ed,
                        "restricoes_fisicas": rest_ed,
                    }
                    sucesso, msg_bd = atualizar_perfil_aluno_dict_seguro(
                        aluno["id"], dados_salvar
                    )
                    if sucesso:
                        if t_ed_salvar != turma_atual:
                            atualizar_turma_aluno(aluno["id"], t_ed_salvar)
                        st.session_state.aluno_prontuario.update(dados_salvar)
                        st.toast("Ficha guardada com sucesso! 💪", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro SQL: {msg_bd}")


def _val(aluno, campo):
    """Retorna string limpa ou vazia, nunca 'nan'/'None'."""
    v = aluno.get(campo, "")
    return "" if pd.isna(v) or str(v).strip().lower() in ("nan", "none") else str(v).strip()


def _idx_select(opcoes: list, valor_atual: str) -> int:
    """Retorna o índice do valor_atual na lista de opções (case-insensitive). Default 0."""
    v = str(valor_atual).strip().lower()
    for i, op in enumerate(opcoes):
        if op.lower() == v:
            return i
    return 0


def render_aba_social(aluno):
    """Componente: Aba de Perfil Socioeconômico e Anamnese Complementar."""
    with st.container(border=True):
        c_head, c_btn = st.columns([4, 1], vertical_alignment="center")
        c_head.markdown("#### 🏘️ Perfil Socioeconômico e Anamnese")
        btn_top = c_btn.button(
            "💾 Guardar", key="save_social_top", type="primary", use_container_width=True
        )
        st.info(
            "Dados de mapeamento demográfico e social para relatórios institucionais. "
            "Não afetam as operações diárias — apenas análises e estatísticas."
        )

        # ── Bloco 1: Dados Demográficos ──────────────────────────────────────
        st.markdown("##### 👤 Dados Demográficos")
        c1, c2, c3 = st.columns(3)

        OPCOES_SEXO = ["Feminino", "Masculino", "Outro", "Prefiro não informar"]
        sexo_ed = c1.selectbox(
            "Sexo:", OPCOES_SEXO, index=_idx_select(OPCOES_SEXO, _val(aluno, "sexo"))
        )
        natural_ed = c2.text_input("Naturalidade:", value=_val(aluno, "naturalidade"))

        OPCOES_CIVIL = ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável", "Outro"]
        estado_civil_ed = c3.selectbox(
            "Estado Civil:", OPCOES_CIVIL,
            index=_idx_select(OPCOES_CIVIL, _val(aluno, "estado_civil"))
        )

        c4, c5, c6 = st.columns(3)
        OPCOES_APOS = ["Não", "Sim"]
        aposentado_ed = c4.selectbox(
            "Aposentado(a)?", OPCOES_APOS,
            index=_idx_select(OPCOES_APOS, _val(aluno, "aposentado"))
        )
        conjuge_ed = c5.text_input("Nome do Cônjuge:", value=_val(aluno, "nome_conjuge"))
        moradores_ed = c6.text_input(
            "Qtd. de Moradores na Residência:", value=_val(aluno, "qtd_moradores")
        )

        # ── Bloco 2: Socioeconômico ───────────────────────────────────────────
        st.markdown("##### 💰 Situação Socioeconômica")
        c7, c8, c9 = st.columns(3)

        OPCOES_INSTRUCAO = [
            "Sem instrução", "Ensino fundamental incompleto", "Ensino fundamental completo",
            "Ensino médio incompleto", "Ensino médio completo",
            "Ensino superior incompleto", "Ensino superior completo",
            "Pós-graduação", "Outro",
        ]
        instrucao_ed = c7.selectbox(
            "Grau de Instrução:", OPCOES_INSTRUCAO,
            index=_idx_select(OPCOES_INSTRUCAO, _val(aluno, "grau_instrucao"))
        )
        fonte_ed = c8.text_input(
            "Principal Fonte de Renda:", value=_val(aluno, "principal_fonte_renda")
        )
        renda_ed = c9.text_input(
            "Faixa de Renda da Casa:", value=_val(aluno, "faixa_renda")
        )

        # ── Bloco 3: Voluntariado ─────────────────────────────────────────────
        st.markdown("##### 🤝 Interesse em Voluntariado")
        c10, c11 = st.columns([1, 2])
        OPCOES_VOL = ["Não", "Sim"]
        vol_int_ed = c10.selectbox(
            "Tem interesse?", OPCOES_VOL,
            index=_idx_select(OPCOES_VOL, _val(aluno, "trabalho_voluntario_interesse"))
        )
        vol_areas_ed = c11.text_input(
            "Áreas de interesse:", value=_val(aluno, "trabalho_voluntario_areas")
        )

        # ── Bloco 4: Anamnese Complementar ───────────────────────────────────
        st.markdown("##### 🏃 Anamnese de Atividade Física")
        anamnese_ed = st.text_area(
            "Incômodos durante ou após a prática de atividades físicas:",
            value=_val(aluno, "anamnese_incomodo_atividade"),
            height=120,
            placeholder="Descreva qualquer desconforto relatado pelo aluno...",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_bot = st.button(
            "💾 Guardar Perfil Social Completo",
            key="save_social_bot",
            type="primary",
            use_container_width=True,
        )

        if btn_top or btn_bot:
            with st.spinner("A guardar perfil social..."):
                payload = {
                    "sexo":                         sexo_ed,
                    "naturalidade":                 natural_ed,
                    "estado_civil":                 estado_civil_ed,
                    "aposentado":                   aposentado_ed,
                    "nome_conjuge":                 conjuge_ed,
                    "qtd_moradores":                moradores_ed,
                    "grau_instrucao":               instrucao_ed,
                    "principal_fonte_renda":        fonte_ed,
                    "faixa_renda":                  renda_ed,
                    "trabalho_voluntario_interesse": vol_int_ed,
                    "trabalho_voluntario_areas":    vol_areas_ed,
                    "anamnese_incomodo_atividade":  anamnese_ed,
                }
                sucesso, msg = atualizar_dados_sociais_aluno(aluno["id"], payload)
                if sucesso:
                    st.session_state.aluno_prontuario.update(payload)
                    st.toast("Perfil social guardado! 🏘️", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Erro: {msg}")


def render_aba_historico(aluno):
    """Componente: Aba de Histórico Clínico."""
    hist = get_avaliacoes_aluno(aluno["id"])
    if hist is not None and not hist.empty:
        for _, a in hist.iterrows():
            a_dict = a.to_dict()
            c_h1, c_h2, c_h3 = st.columns([3, 0.5, 0.5], vertical_alignment="center")
            c_h1.write(f"📅 **Avaliação em {a_dict.get('data_avaliacao', '')}**")
            with c_h2:
                if st.button("✏️", key=f"ed_{a_dict['id']}", help="Editar medição"):
                    st.session_state.medicao_editar = a_dict
                    st.rerun()
            with c_h3:
                if st.button("🗑️", key=f"dl_{a_dict['id']}", help="Excluir medição"):
                    excluir_avaliacao_prontuario(a_dict["id"])
                    st.rerun()
            with st.expander("Ver Biofeedback"):
                analisar_saude_visual(a_dict)
            st.markdown("<hr style='margin: 4px 0px 8px 0px;'>", unsafe_allow_html=True)
    else:
        st.info("Sem histórico registado.")


def render_aba_documentos(aluno):
    """Componente: Aba de Documentos Legais com Sistema Anti-Lixo."""
    with st.container(border=True):
        c_head_doc, c_top_doc = st.columns([4, 1], vertical_alignment="center")
        c_head_doc.markdown("### 📂 Documentação Legal Anual")
        btn_doc_top = c_top_doc.button(
            "💾 Guardar Arquivos",
            key="save_top_doc",
            type="primary",
            use_container_width=True,
        )
        st.info(
            "Se anexou um ficheiro errado, clique em '🗑️ Remover' abaixo dele para limpar o registo."
        )

        c_rg, c_rec, c_ate = st.columns(3, gap="large")

        # --- 1. RG ---
        with c_rg:
            st.markdown("**1. Identidade (RG/CPF)**")
            url_rg = aluno.get("url_rg")
            if (
                pd.notna(url_rg)
                and isinstance(url_rg, str)
                and str(url_rg).strip().lower() not in ["nan", "none", ""]
            ):
                renderizar_documento_com_rotacao(url_rg, "rg")
                if st.button(
                    "🗑️ Remover RG",
                    key="del_rg_btn",
                    type="secondary",
                    use_container_width=True,
                ):
                    ok, _ = atualizar_perfil_aluno_dict_seguro(
                        aluno["id"], {"url_rg": None}
                    )
                    if ok:
                        st.session_state.aluno_prontuario["url_rg"] = None
                        st.rerun()
            else:
                st.warning("Nenhum RG anexado.")
            novo_rg = st.file_uploader(
                "Atualizar RG",
                type=["jpg", "png", "jpeg", "pdf"],
                key="up_rg_p",
                label_visibility="collapsed",
            )

        # --- 2. Receita ---
        with c_rec:
            st.markdown("**2. Receituário Médico**")
            url_rec = aluno.get("url_receituario")
            if (
                pd.notna(url_rec)
                and isinstance(url_rec, str)
                and str(url_rec).strip().lower() not in ["nan", "none", ""]
            ):
                renderizar_documento_com_rotacao(url_rec, "rec")
                if st.button(
                    "🗑️ Remover Receita",
                    key="del_rec_btn",
                    type="secondary",
                    use_container_width=True,
                ):
                    ok, _ = atualizar_perfil_aluno_dict_seguro(
                        aluno["id"], {"url_receituario": None}
                    )
                    if ok:
                        st.session_state.aluno_prontuario["url_receituario"] = None
                        st.rerun()
            else:
                st.info("Nenhuma receita anexada.")
            novo_rec = st.file_uploader(
                "Atualizar Receita",
                type=["jpg", "png", "jpeg", "pdf"],
                key="up_rec_p",
                label_visibility="collapsed",
            )

        # --- 3. Atestado ---
        with c_ate:
            st.markdown("**3. Atestado Físico**")
            url_ate = aluno.get("url_atestado_medico")
            if (
                pd.notna(url_ate)
                and isinstance(url_ate, str)
                and str(url_ate).strip().lower() not in ["nan", "none", ""]
            ):
                renderizar_documento_com_rotacao(url_ate, "ate")
                if st.button(
                    "🗑️ Remover Atestado",
                    key="del_ate_btn",
                    type="secondary",
                    use_container_width=True,
                ):
                    ok, _ = atualizar_perfil_aluno_dict_seguro(
                        aluno["id"], {"url_atestado_medico": None}
                    )
                    if ok:
                        st.session_state.aluno_prontuario["url_atestado_medico"] = None
                        st.rerun()
            else:
                st.error("Atestado em falta!")
            novo_ate = st.file_uploader(
                "Atualizar Atestado",
                type=["jpg", "png", "jpeg", "pdf"],
                key="up_ate_p",
                label_visibility="collapsed",
            )

        st.markdown("---")
        btn_doc_bot = st.button(
            "💾 Guardar Novos Documentos Anexados",
            key="save_bot_doc",
            type="primary",
            use_container_width=True,
        )

        if btn_doc_top or btn_doc_bot:
            if novo_rg or novo_rec or novo_ate:
                with st.spinner("A guardar na nuvem..."):
                    final_rg, final_rec, final_ate = url_rg, url_rec, url_ate
                    upload_docs_ok = True

                    if novo_rg:
                        b_rg, n_rg, t_rg = processar_documento_prontuario(
                            novo_rg.getvalue(), novo_rg.name, novo_rg.type
                        )
                        u_rg, err_rg = upload_midia_diagnostico(b_rg, n_rg, t_rg)
                        if u_rg:
                            final_rg = u_rg
                        else:
                            upload_docs_ok = False
                            st.error(f"Erro RG: {err_rg}")

                    if novo_rec:
                        b_rec, n_rec, t_rec = processar_documento_prontuario(
                            novo_rec.getvalue(), novo_rec.name, novo_rec.type
                        )
                        u_rec, err_rec = upload_midia_diagnostico(b_rec, n_rec, t_rec)
                        if u_rec:
                            final_rec = u_rec
                        else:
                            upload_docs_ok = False
                            st.error(f"Erro Receita: {err_rec}")

                    if novo_ate:
                        b_ate, n_ate, t_ate = processar_documento_prontuario(
                            novo_ate.getvalue(), novo_ate.name, novo_ate.type
                        )
                        u_ate, err_ate = upload_midia_diagnostico(b_ate, n_ate, t_ate)
                        if u_ate:
                            final_ate = u_ate
                        else:
                            upload_docs_ok = False
                            st.error(f"Erro Atestado: {err_ate}")

                    if upload_docs_ok:
                        docs_salvar = {}
                        if final_rg != url_rg:
                            docs_salvar["url_rg"] = final_rg
                        if final_rec != url_rec:
                            docs_salvar["url_receituario"] = final_rec
                        if final_ate != url_ate:
                            docs_salvar["url_atestado_medico"] = final_ate

                        if docs_salvar:
                            sucesso, msg_bd = atualizar_perfil_aluno_dict_seguro(
                                aluno["id"], docs_salvar
                            )
                            if sucesso:
                                st.session_state.aluno_prontuario.update(docs_salvar)
                                st.toast("Guardado com sucesso!", icon="✅")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Erro BD: {msg_bd}")
            else:
                st.warning("Anexe pelo menos um documento novo para guardar.")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(
        "🟡 Histórico de Atestados Temporários (Faltas Justificadas)", expanded=False
    ):
        st.info("Use esta secção para arquivar atestados curtos (gripes, exames).")
        with st.form("form_novo_atestado_temp", clear_on_submit=True):
            c_dt, c_motivo = st.columns([1, 2])
            data_atestado = c_dt.date_input(
                "Data:", datetime.date.today(), format="DD/MM/YYYY"
            )
            motivo = c_motivo.text_input("Motivo:", placeholder="Ex: Gripe (3 dias)")
            arq_atestado = st.file_uploader(
                "Anexar Ficheiro:", type=["jpg", "png", "jpeg", "pdf"]
            )

            if st.form_submit_button(
                "➕ Arquivar Temporário", type="primary", use_container_width=True
            ):
                if not arq_atestado:
                    st.error("Anexe o ficheiro.")
                else:
                    with st.spinner("A enviar..."):
                        b_arq, n_arq, t_arq = processar_documento_prontuario(
                            arq_atestado.getvalue(),
                            arq_atestado.name,
                            arq_atestado.type,
                        )
                        url_arq, err_arq = upload_midia_diagnostico(b_arq, n_arq, t_arq)
                        if url_arq:
                            sucesso, msg = salvar_atestado_temporario(
                                aluno["id"], data_atestado, motivo, url_arq
                            )
                            if sucesso:
                                st.rerun()
                            else:
                                st.error(f"Erro ao salvar: {msg}")
                        else:
                            st.error(f"Erro no envio: {err_arq}")

        atestados_hist = get_atestados_temporarios(aluno["id"])
        if atestados_hist is not None and not atestados_hist.empty:
            st.markdown("#### 📁 Arquivo de Atestados")
            for _, at_temp in atestados_hist.iterrows():
                with st.container(border=True):
                    c_ht1, c_ht2, c_ht3 = st.columns(
                        [3.5, 1, 0.5], vertical_alignment="center"
                    )
                    dt_format = pd.to_datetime(at_temp["data_registro"]).strftime(
                        "%d/%m/%Y"
                    )
                    c_ht1.markdown(
                        f"**Data:** {dt_format} <br> **Motivo:** {at_temp.get('motivo', '')}",
                        unsafe_allow_html=True,
                    )
                    with c_ht2:
                        url_t = at_temp["url_documento"]
                        if isinstance(url_t, str) and url_eh_imagem(url_t):
                            with st.popover("Ver / Girar Foto"):
                                renderizar_documento_com_rotacao(
                                    url_t, f"at_tmp_{at_temp['id']}"
                                )
                        elif isinstance(url_t, str):
                            st.link_button(
                                "📄 Abrir PDF", url_t, use_container_width=True
                            )
                    with c_ht3:
                        if st.button(
                            "🗑️",
                            key=f"del_at_tmp_{at_temp['id']}",
                            help="Excluir permanentemente",
                        ):
                            excluir_atestado_temporario_local(at_temp["id"])
                            st.rerun()
        else:
            st.caption("Nenhum atestado temporário arquivado.")


# ==============================================================================
# 🚀 3. MOTOR PRINCIPAL (RENDERIZADOR DE ECRÃ)
# ==============================================================================
def renderizar_ficha():
    st.markdown(
        """
        <style>
            .zoom-avatar-lg { width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 3px solid #1E88E5; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 50; }
            .zoom-avatar-lg:hover { transform: scale(3.5); z-index: 99999 !important; box-shadow: 0px 20px 40px rgba(0,0,0,0.6); }
            .btn-excluir-anexo { margin-top: 5px !important; }
        </style>
    """,
        unsafe_allow_html=True,
    )

    aluno = st.session_state.aluno_prontuario
    render_cabecalho_aluno(aluno)

    edit = st.session_state.get("medicao_editar")
    if edit:
        st.markdown(
            f"<h3 style='color: #E65100; margin-top: 20px;'>✏️ Edição de Registro: {edit.get('data_avaliacao', '')}</h3>",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            render_formulario_medicao(aluno, edit=edit)
    else:
        t1, t2, t3, t4, t5, t6 = st.tabs(
            [
                "👤 Perfil e Contato",
                "📝 Nova Medição",
                "📊 Histórico Clínico",
                "📂 Documentação Legal",
                "🏘️ Perfil Social",
                "🩻 Mapa de Dores",
            ]
        )
        with t1:
            render_aba_perfil(aluno)
        with t2:
            with st.container(border=True):
                render_formulario_medicao(aluno, edit=None)
        with t3:
            render_aba_historico(aluno)
        with t4:
            render_aba_documentos(aluno)
        with t5:
            render_aba_social(aluno)
        with t6:
            render_aba_mapa_dores(aluno, email_usuario=st.session_state.get("email", ""))
