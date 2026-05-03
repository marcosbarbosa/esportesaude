# ==============================================================================
# 📄 Arquivo: views/prontuario_ficha.py
# 📅 Versão: 4.9 (PRO Elite - Rotação Expressa em Nuvem + Fricção Zero)
# ⚙️ Função: Gestão individual cirúrgica. Preserva uploads, gráficos e UX original.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io
import time
import uuid
import requests
from PIL import Image, ImageOps
from views.utils_docs import url_eh_imagem, renderizar_documento_com_rotacao

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
    supabase,
)

try:
    from gerador_pdf import criar_documento_aluno_pdf
except ImportError:
    st.error("Erro: Arquivo gerador_pdf.py não encontrado.")


# ==============================================================================
# 🚀 MOTORES SEGUROS (COM DIAGNÓSTICO E BLINDAGEM DE ARQUIVO MORTO)
# ==============================================================================
def alterar_status_aluno_local(aluno_id, novo_status):
    try:
        supabase.from_("alunos").update({"status": novo_status}).eq("id", str(aluno_id)).execute()
        return True, f"Status alterado para {novo_status}"
    except Exception as e:
        return False, str(e)


def atualizar_perfil_aluno_dict_seguro(aluno_id, dados_atualizados):
    try:
        supabase.from_("alunos").update(dados_atualizados).eq("id", str(aluno_id)).execute()
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


def upload_midia_diagnostico(file_bytes, file_name, mime_type, bucket="diario_midias_imbra"):
    try:
        nome_u = f"upload_{uuid.uuid4().hex[:8]}.{file_name.split('.')[-1]}"
        supabase.storage.from_(bucket).upload(
            path=nome_u, file=file_bytes, file_options={"content-type": mime_type}
        )
        url_publica = supabase.storage.from_(bucket).get_public_url(nome_u)
        return url_publica, None
    except Exception as e:
        return None, str(e)


def processar_foto_perfil(file_bytes, angulo_rotacao=0):
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img = ImageOps.exif_transpose(img) 

        if angulo_rotacao != 0:
            img = img.rotate(angulo_rotacao, expand=True)

        try: filtro = Image.Resampling.LANCZOS
        except AttributeError: filtro = Image.LANCZOS

        img = ImageOps.fit(img, (300, 300), method=filtro, centering=(0.5, 0.5))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "perfil.jpg", "image/jpeg"
    except Exception:
        return None, None, None


# 🚀 MOTOR MÁGICO: Rotaciona fotos que já estão na nuvem com 1 clique
def rotacionar_foto_salva(aluno, url_atual, angulo):
    with st.spinner("A processar rotação na nuvem..."):
        try:
            response = requests.get(url_atual, timeout=10)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content)).convert("RGB")
                img = img.rotate(angulo, expand=True)

                try: filtro = Image.Resampling.LANCZOS
                except AttributeError: filtro = Image.LANCZOS

                img = ImageOps.fit(img, (300, 300), method=filtro, centering=(0.5, 0.5))

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                img_bytes = buf.getvalue()

                nova_url, erro = upload_midia_diagnostico(img_bytes, f"rot_{uuid.uuid4().hex[:6]}.jpg", "image/jpeg")
                if nova_url:
                    sucesso, msg = atualizar_perfil_aluno_dict_seguro(aluno["id"], {"url_foto": nova_url})
                    if sucesso:
                        st.session_state.aluno_prontuario["url_foto"] = nova_url
                        st.toast("Foto corrigida com sucesso!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro ao atualizar banco: {msg}")
                else:
                    st.error(f"Erro no upload: {erro}")
            else:
                st.error("Não foi possível baixar a foto atual para rotacionar.")
        except Exception as e:
            st.error(f"Erro ao processar imagem: {e}")


def processar_documento_prontuario(file_bytes, file_name, file_type):
    try:
        if "image" in file_type:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            img = ImageOps.exif_transpose(img)

            try: filtro = Image.Resampling.LANCZOS
            except AttributeError: filtro = Image.LANCZOS

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

        dor = int(aval.get("dor_nivel") or aval.get("nivel_dor") or 0)
        carinha = "😃" if dor <= 2 else ("😐" if dor <= 5 else "😟")
        col1.metric("Nível de Dor", f"{carinha} {dor}/10")

        tug = float(aval.get("tug_simples") or aval.get("tug") or 0.0)
        col2.metric("Equilíbrio (TUG)", f"{tug}s", delta_color="inverse")

        f_d = float(aval.get("forca_dir") or 0.0)
        f_e = float(aval.get("forca_esq") or 0.0)
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
                st.caption("Sem dados suficientes.")

        bristol_v = aval.get("bristol", "Não avaliado")
        urina_v = aval.get("urina", "Não avaliado")
        borg_v = aval.get("borg", "Não avaliado")

        if bristol_v != "Não avaliado" or urina_v != "Não avaliado" or borg_v != "Não avaliado":
            st.markdown("<br>**Marcadores Fisiológicos Atuais:**", unsafe_allow_html=True)
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.info(f"🏋️ **Borg:** {borg_v}")
            c_m2.warning(f"💩 **Bristol:** {bristol_v}")
            c_m3.success(f"💧 **Urina:** {urina_v}")

    except Exception:
        st.error("Erro ao processar gráficos visuais.")


def render_formulario_medicao(aluno, edit=None):
    suffix = f"_{edit['id']}" if edit else "_new"

    try:
        d_val = (
            datetime.datetime.strptime(edit["data_avaliacao"], "%Y-%m-%d").date()
            if edit
            else datetime.date.today()
        )
        if d_val > datetime.date.today():
            d_val = datetime.date.today()
    except:
        d_val = datetime.date.today()

    d_av = st.date_input(
        "Data do Atendimento:", value=d_val, key=f"dav{suffix}", format="DD/MM/YYYY"
    )

    st.markdown("#### 1. Anamnese")
    c1, c2 = st.columns(2)
    try: dor_val = int(edit["dor_nivel"]) if edit else 0
    except: dor_val = 0
    dor = c1.slider("Escala de Dor (0-10):", 0, 10, value=dor_val, key=f"dor{suffix}")

    try: q_val = int(edit.get("quedas_6m", 0)) if edit else 0
    except: q_val = 0
    quedas = c2.number_input(
        "Quedas (últimos 6 meses):", min_value=0, value=q_val, key=f"q{suffix}"
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
    idx_d = op_mob.index(edit["mobilidade_pes_dir"]) if edit and edit.get("mobilidade_pes_dir") in op_mob else 0
    idx_e = op_mob.index(edit["mobilidade_pes_esq"]) if edit and edit.get("mobilidade_pes_esq") in op_mob else 0

    mob_d = c3.selectbox("Mobilidade (Perna Dir):", op_mob, index=idx_d, key=f"md{suffix}")
    mob_e = c4.selectbox("Mobilidade (Perna Esq):", op_mob, index=idx_e, key=f"me{suffix}")

    c5, c6 = st.columns(2)
    try: fd_val = float(edit.get("forca_dir", 0)) if edit else 0.0
    except: fd_val = 0.0
    try: fe_val = float(edit.get("forca_esq", 0)) if edit else 0.0
    except: fe_val = 0.0

    if pd.isna(fd_val): fd_val = 0.0
    if pd.isna(fe_val): fe_val = 0.0

    f_d = c5.number_input("Força Dir (Reps):", value=int(fd_val), key=f"fd{suffix}")
    f_e = c6.number_input("Força Esq (Reps):", value=int(fe_val), key=f"fe{suffix}")

    st.markdown("#### 3. TUG (Timed Up and Go)")
    c7, c8, c9 = st.columns(3)
    try: t1_val = float(edit.get("tug_simples", 0.0)) if edit else 0.0
    except: t1_val = 0.0
    try: t2_val = float(edit.get("tug_cog_animais", 0.0)) if edit else 0.0
    except: t2_val = 0.0
    try: t3_val = float(edit.get("tug_cog_perguntas", 0.0)) if edit else 0.0
    except: t3_val = 0.0

    if pd.isna(t1_val): t1_val = 0.0
    if pd.isna(t2_val): t2_val = 0.0
    if pd.isna(t3_val): t3_val = 0.0

    tug1 = c7.number_input("Simples (s):", value=t1_val, key=f"t1{suffix}")
    tug2 = c8.number_input("Cog. Animais (s):", value=t2_val, key=f"t2{suffix}")
    tug3 = c9.number_input("Cog. Perguntas (s):", value=t3_val, key=f"t3{suffix}")

    st.markdown("<br>#### 4. Marcadores Clínicos e Biofeedback", unsafe_allow_html=True)

    try: borg_val = str(edit.get("borg", "4")) if edit else "4"
    except: borg_val = "4"
    try: bristol_val = str(edit.get("bristol", "Tipo 3")) if edit else "Tipo 3"
    except: bristol_val = "Tipo 3"
    try: urina_val = str(edit.get("urina", "Nível 2")) if edit else "Nível 2"
    except: urina_val = "Nível 2"

    borg_op = ["0 - Repouso", "2 - Leve", "4 - Pouco Cansativo", "6 - Cansativo", "8 - Muito Pesado", "10 - Exaustivo"]
    borg = st.select_slider(
        "🏋️ Escala de Borg (Perceção de Esforço Global):", 
        options=borg_op, 
        value=next((x for x in borg_op if borg_val in x), "4 - Pouco Cansativo"), 
        key=f"borg{suffix}"
    )

    c10, c11 = st.columns(2)
    bristol_op = ["Tipo 1: Caroços duros (Constipação Severa)", "Tipo 2: Forma de salsicha, grumoso (Constipação Leve)", "Tipo 3: Salsicha com rachaduras (Normal)", "Tipo 4: Salsicha lisa e macia (Ótimo)", "Tipo 5: Pedaços macios (Falta de Fibra)", "Tipo 6: Pastoso, fofo (Diarreia Leve)", "Tipo 7: Aquoso, líquido (Diarreia Severa)"]
    bristol = c10.selectbox(
        "💩 Escala de Bristol (Consistência das Fezes):", 
        bristol_op, 
        index=next((i for i, v in enumerate(bristol_op) if bristol_val in v), 2), 
        key=f"bris{suffix}"
    )

    urina_op = ["Nível 1 - Transparente (Excesso de Água)", "Nível 2 - Amarelo Muito Claro (Ótimo)", "Nível 3 - Amarelo Claro (Bom)", "Nível 4 - Amarelo (Desidratação Leve)", "Nível 5 - Amarelo Escuro (Desidratação Moderada)", "Nível 6 - Âmbar (Desidratação Severa)", "Nível 7 - Castanho (Alerta Médico)"]
    urina = c11.selectbox(
        "💧 Cor da Urina (Nível de Hidratação):", 
        urina_op, 
        index=next((i for i, v in enumerate(urina_op) if urina_val in v), 1), 
        key=f"uri{suffix}"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    def salvar_medicao_backend():
        borg_clean = borg.split(" - ")[0]
        bristol_clean = bristol.split(":")[0]
        urina_clean = urina.split(" - ")[0]
        sug = revisar_texto_ia(meds)
        final_meds = sug if sug else meds

        try:
            return salvar_avaliacao_prontuario(
                aluno_id=aluno["id"], data=d_av, dor=dor, quedas=quedas, cirurgias=cirurgias, 
                meds=final_meds, m_dir=mob_d, m_esq=mob_e, f_dir=f_d, f_esq=f_e, 
                t1=tug1, t2=tug2, t3=tug3, aval_id=edit["id"] if edit else None,
                bristol=bristol_clean, urina=urina_clean, borg=borg_clean
            )
        except TypeError:
            return salvar_avaliacao_prontuario(
                aluno["id"], d_av, dor, quedas, cirurgias, final_meds, mob_d, mob_e, f_d, f_e, tug1, tug2, tug3, edit["id"] if edit else None
            )

    if edit:
        c_save, c_cancel = st.columns(2)
        if c_save.button("💾 Salvar Alterações", type="primary", use_container_width=True, key=f"bsave{suffix}"):
            with st.spinner("Atualizando medição..."):
                sucesso, msg = salvar_medicao_backend()
                if sucesso:
                    st.cache_data.clear()
                    st.success("✅ Alterações salvas com sucesso! 🏋️‍♂️")
                    time.sleep(1.5)
                    st.session_state.medicao_editar = None
                    st.rerun()
                else:
                    st.error(f"Erro ao atualizar: {msg}")

        if c_cancel.button("❌ Cancelar Edição", use_container_width=True, key=f"bcancel{suffix}"):
            st.session_state.medicao_editar = None
            st.rerun()

    else:
        if st.button("💾 Salvar Nova Medição Clínica", type="primary", use_container_width=True, key="bsavenew"):
            historico_aluno = get_avaliacoes_aluno(aluno["id"])
            datas_existentes = ([a.get("data_avaliacao") for a in historico_aluno] if historico_aluno else [])

            if str(d_av) in datas_existentes:
                st.error(f"⚠️ Atenção: Já existe uma medição registrada para este aluno na data {d_av.strftime('%d/%m/%Y')}.")
            else:
                with st.spinner("A salvar os dados clínicos..."):
                    sucesso, msg = salvar_medicao_backend()
                    if sucesso:
                        st.cache_data.clear()
                        st.toast("Medição salva com sucesso! 🫀", icon="🩺")
                        st.success("✅ Prontuário registrado com sucesso no banco de dados!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"Erro crítico ao salvar no banco de dados: {msg}")


def renderizar_ficha():
    st.markdown(
        """
        <style>
            .zoom-avatar-lg {
                width: 90px; height: 90px; border-radius: 50%; object-fit: cover;
                border: 3px solid #1E88E5; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
                transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 50;
            }
            .zoom-avatar-lg:hover {
                transform: scale(3.5); z-index: 99999 !important; box-shadow: 0px 20px 40px rgba(0,0,0,0.6);
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    aluno = st.session_state.aluno_prontuario

    if f"key_foto_uploader_{aluno['id']}" not in st.session_state:
        st.session_state[f"key_foto_uploader_{aluno['id']}"] = str(uuid.uuid4())

    col_titulo, col_voltar = st.columns([4, 2], vertical_alignment="center")
    with col_titulo:
        st.title("🩺 Ficha Digital do Aluno")
    with col_voltar:
        origem = st.session_state.get("origem_prontuario")
        mapa_nomes = {"Frequência": "Turmas", "Principal": "Início"}
        label_voltar = f"🔙 Voltar p/ {mapa_nomes.get(origem, origem)}" if origem else "🔙 Voltar ao Portal"

        if st.button(label_voltar, type="secondary", use_container_width=True):
            st.session_state.aluno_prontuario = None
            st.session_state.medicao_editar = None
            if origem:
                st.session_state.menu_atual = origem
                del st.session_state["origem_prontuario"]
            st.rerun()

    st.divider()

    u_v = aluno.get("url_foto")
    cp_f, cp_i, cp_pdf = st.columns([1, 4.5, 1.5], vertical_alignment="center")

    with cp_f:
        if pd.notna(u_v) and str(u_v).strip() and str(u_v).strip().lower() not in ["none", "nan", "null"]:
            st.markdown(f'<img src="{u_v}" class="zoom-avatar-lg">', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="font-size:45px;background:#f0f2f6;border-radius:50%;text-align:center;width:90px;height:90px;line-height:90px;border:3px solid #1E88E5; color:#94A3B8; cursor: default;">👤</div>',
                unsafe_allow_html=True,
            )

    with cp_i:
        st_badge = "<span style='background:#DCFCE7; color:#166534; padding:3px 10px; border-radius:12px; font-size:14px; margin-left: 10px; vertical-align: middle;'>Ativo</span>" if aluno.get("status", "Ativo") != "Inativo" else "<span style='background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:12px; font-size:14px; margin-left: 10px; vertical-align: middle;'>Inativo</span>"
        st.markdown(f"<h2 style='margin-bottom:0px; padding-bottom:0px; display:inline-block;'>{aluno.get('nome', '')}</h2> {st_badge}", unsafe_allow_html=True)
        st.caption(f"Turma: {aluno.get('turma', '')}")

    with cp_pdf:
        estatisticas_pdf = get_estatisticas_frequencia_aluno(aluno.get("id", ""))
        avaliacoes_pdf = get_avaliacoes_aluno(aluno.get("id", ""))
        historico_pdf = get_historico_aulas_aluno(aluno.get("id", ""))
        pdf_bytes = criar_documento_aluno_pdf(aluno, avaliacoes_pdf, historico_pdf, estatisticas_pdf)

        st.download_button(
            label="🖨️ Exportar Dossiê",
            data=pdf_bytes,
            file_name=f"Dossie_Clinico_{aluno.get('nome', '')[:15].replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

        if aluno.get("status", "Ativo") != "Inativo":
            if st.button("🗄️ Arquivar Aluno", use_container_width=True):
                ok, msg = alterar_status_aluno_local(aluno["id"], "Inativo")
                if ok:
                    st.toast("Transferido para o Arquivo Morto!")
                    aluno["status"] = "Inativo"
                    time.sleep(1)
                    st.session_state.aluno_prontuario = None
                    st.rerun()
        else:
            if st.button("♻️ Reativar Aluno", type="primary", use_container_width=True):
                ok, msg = alterar_status_aluno_local(aluno["id"], "Ativo")
                if ok:
                    st.toast("Aluno reativado no sistema!")
                    aluno["status"] = "Ativo"
                    time.sleep(1)
                    st.rerun()

    edit = st.session_state.get("medicao_editar")

    if edit:
        st.markdown(f"<h3 style='color: #E65100; margin-top: 20px;'>✏️ Edição de Registro: {edit.get('data_avaliacao', '')}</h3>", unsafe_allow_html=True)
        st.info("Você entrou no modo de edição. Ajuste os dados e clique em salvar, ou cancele para voltar ao histórico.")
        with st.container(border=True):
            render_formulario_medicao(aluno, edit=edit)
    else:
        t1, t2, t3, t4 = st.tabs(["👤 Perfil e Contato", "📝 Nova Medição", "📊 Histórico Clínico", "📂 Documentação Legal"])

        with t1:
            with st.container(border=True):
                c_head, c_top_btn = st.columns([4, 1], vertical_alignment="center")
                c_head.markdown("#### 👤 Informações Pessoais")
                btn_save_top = c_top_btn.button("💾 Guardar", key="save_top_perfil", type="primary", use_container_width=True)

                col_n, col_t, col_d = st.columns([2, 1.5, 1])

                nome_seguro = "" if pd.isna(aluno.get("nome")) else str(aluno.get("nome"))
                n_ed = col_n.text_input("Nome Completo:", value=nome_seguro)

                df_turmas_ativas = get_todas_turmas(ativas_apenas=True)
                ocupacao = get_ocupacao_turmas()

                lista_turmas_display = []
                mapa_turmas = {}

                for t_nome in df_turmas_ativas["nome"].tolist():
                    info = ocupacao.get(t_nome, {})
                    qtd = info.get("qtd", 0)
                    limite = info.get("limite", 40)
                    vagas = info.get("vagas", 40)

                    if vagas <= 0: display = f"🔴 {t_nome} (LOTADA - {qtd}/{limite})"
                    elif vagas <= 5: display = f"🟡 {t_nome} (ALERTA - {vagas} vagas)"
                    else: display = f"🟢 {t_nome} ({vagas} vagas livres)"

                    lista_turmas_display.append(display)
                    mapa_turmas[display] = t_nome

                turma_atual = aluno.get("turma", "")
                if turma_atual and turma_atual not in mapa_turmas.values():
                    display_atual = f"⚪ {turma_atual} (Antiga/Inativa)"
                    lista_turmas_display.insert(0, display_atual)
                    mapa_turmas[display_atual] = turma_atual

                idx = next((i for i, d_name in enumerate(lista_turmas_display) if mapa_turmas[d_name] == turma_atual), 0)

                t_ed_display = col_t.selectbox("Turma Atual:", lista_turmas_display, index=idx)
                t_ed_salvar = mapa_turmas[t_ed_display]

                data_bd = aluno.get("data_nascimento")
                hoje = datetime.date.today()
                limite_min = datetime.date(1920, 1, 1)
                data_padrao = datetime.date(2000, 1, 1)

                try:
                    if pd.notna(data_bd) and str(data_bd).strip().lower() not in ["nan", "none", "nat", ""]:
                        dt_parsed = pd.to_datetime(data_bd).date()
                        if dt_parsed > hoje:
                            try: dt_parsed = dt_parsed.replace(year=dt_parsed.year - 100)
                            except ValueError: dt_parsed = hoje
                        if limite_min <= dt_parsed <= hoje: data_padrao = dt_parsed
                        elif dt_parsed < limite_min: data_padrao = limite_min
                        else: data_padrao = hoje
                except Exception:
                    pass

                d_ed = col_d.date_input("Nascimento:", value=data_padrao, min_value=limite_min, max_value=hoje, format="DD/MM/YYYY")

                st.markdown("#### 📸 Foto de Perfil")

                # 🚀 INJEÇÃO DE UX EXTREMA: Painel de Rotação de Foto Salva
                url_atual_foto = aluno.get("url_foto")
                if pd.notna(url_atual_foto) and str(url_atual_foto).strip() and str(url_atual_foto).strip().lower() not in ["none", "nan", "null"]:
                    with st.container(border=True):
                        st.markdown("**A foto atual está deitada?** Corrija aqui com 1 clique:")
                        c_rot1, c_rot2, _ = st.columns([1, 1, 2])
                        if c_rot1.button("↩️ Girar Esquerda", key="rot_esq_salva", use_container_width=True):
                            rotacionar_foto_salva(aluno, url_atual_foto, 90)
                        if c_rot2.button("↻ Girar Direita", key="rot_dir_salva", use_container_width=True):
                            rotacionar_foto_salva(aluno, url_atual_foto, -90)

                foto_nova = st.file_uploader("Substituir Foto:", type=["jpg", "png", "jpeg"], label_visibility="collapsed", key=st.session_state[f"key_foto_uploader_{aluno['id']}"])

                rotacao_foto = 0
                if foto_nova:
                    st.info("🔄 Se a foto veio do WhatsApp, ela pode ficar deitada. Corrija a rotação aqui antes de clicar em Guardar:")
                    rotacao_opt = st.radio("Ajuste manual de rotação:", ["Normal", "↩️ Esquerda", "↻ Direita", "🙃 Inverter"], horizontal=True, label_visibility="collapsed")
                    if rotacao_opt == "↩️ Esquerda": rotacao_foto = 90
                    elif rotacao_opt == "↻ Direita": rotacao_foto = -90
                    elif rotacao_opt == "🙃 Inverter": rotacao_foto = 180

                st.markdown("#### 🪪 Documentos e Endereço")
                c_cpf, c_rg = st.columns(2)
                cpf_seguro = "" if pd.isna(aluno.get("cpf")) else str(aluno.get("cpf"))
                rg_seguro = "" if pd.isna(aluno.get("rg")) else str(aluno.get("rg"))
                cpf_ed = c_cpf.text_input("CPF:", value=cpf_seguro)
                rg_ed = c_rg.text_input("RG:", value=rg_seguro)

                c_end, c_bai, c_cep = st.columns([2, 1, 1])
                end_seguro = "" if pd.isna(aluno.get("endereco")) else str(aluno.get("endereco"))
                bai_seguro = "" if pd.isna(aluno.get("bairro")) else str(aluno.get("bairro"))
                cep_seguro = "" if pd.isna(aluno.get("cep")) else str(aluno.get("cep"))
                end_ed = c_end.text_input("Endereço Completo:", value=end_seguro)
                bai_ed = c_bai.text_input("Bairro:", value=bai_seguro)
                cep_ed = c_cep.text_input("CEP:", value=cep_seguro)

                st.markdown("#### 📱 Biometria e Contactos")
                c_p, c_a, c_w, c_e = st.columns([1, 1, 2, 2])

                peso_db = aluno.get("peso", 0.0)
                peso_val = 0.0 if pd.isna(peso_db) else float(peso_db)
                p_ed = c_p.number_input("Peso (kg):", value=peso_val, step=0.1)

                altura_db = aluno.get("altura", 0.0)
                altura_val = 0.0 if pd.isna(altura_db) else float(altura_db)
                a_ed = c_a.number_input("Altura (m):", value=altura_val, step=0.01)

                w_seguro = "" if pd.isna(aluno.get("whatsapp")) else str(aluno.get("whatsapp"))
                e_seguro = "" if pd.isna(aluno.get("email")) else str(aluno.get("email"))
                w_ed = c_w.text_input("WhatsApp:", value=w_seguro)
                e_ed = c_e.text_input("E-mail:", value=e_seguro)

                st.markdown("#### 🏥 Saúde e Alertas")
                em_seguro = "" if pd.isna(aluno.get("contato_emergencia")) else str(aluno.get("contato_emergencia"))
                cont_em_ed = st.text_input("Contato de Emergência:", value=em_seguro)

                c_s1, c_s2 = st.columns(2)
                prob_seguro = "" if pd.isna(aluno.get("problemas_saude")) else str(aluno.get("problemas_saude"))
                med_seguro = "" if pd.isna(aluno.get("medicamentos")) else str(aluno.get("medicamentos"))
                prob_ed = c_s1.text_area("Problemas de Saúde:", value=prob_seguro)
                meds_ed = c_s2.text_area("Uso de Medicamentos:", value=med_seguro)

                rest_seguro = "" if pd.isna(aluno.get("restricoes_fisicas")) else str(aluno.get("restricoes_fisicas"))
                rest_ed = st.text_input("Restrições Físicas:", value=rest_seguro)

                st.markdown("<br>", unsafe_allow_html=True)
                btn_save_bot = st.button("💾 Guardar Cadastro Completo", key="save_bot_perfil", type="primary", use_container_width=True)

                if btn_save_top or btn_save_bot:
                    with st.spinner("A processar e validar informações..."):
                        nova_url = u_v
                        upload_ok = True

                        if foto_nova:
                            img_b, f_n, f_t = processar_foto_perfil(foto_nova.getvalue(), rotacao_foto)
                            if img_b:
                                url_temp, erro = upload_midia_diagnostico(img_b, f_n, f_t)
                                if url_temp:
                                    nova_url = url_temp
                                    st.session_state[f"key_foto_uploader_{aluno['id']}"] = str(uuid.uuid4())
                                else:
                                    upload_ok = False
                                    st.error(f"❌ Falha crítica no Supabase Storage: {erro}. Verifique se o bucket 'diario_midias_imbra' permite envios.")

                        if upload_ok:
                            dados_salvar = {
                                "nome": n_ed.upper().strip(), "turma": t_ed_salvar, "data_nascimento": str(d_ed),
                                "peso": float(p_ed), "altura": float(a_ed), "whatsapp": w_ed, "email": e_ed,
                                "url_foto": nova_url, "cpf": cpf_ed, "rg": rg_ed, "endereco": end_ed,
                                "bairro": bai_ed, "cep": cep_ed, "contato_emergencia": cont_em_ed,
                                "problemas_saude": prob_ed, "medicamentos": meds_ed, "restricoes_fisicas": rest_ed,
                            }

                            sucesso, msg_bd = atualizar_perfil_aluno_dict_seguro(aluno["id"], dados_salvar)

                            if sucesso:
                                if t_ed_salvar != turma_atual: atualizar_turma_aluno(aluno["id"], t_ed_salvar)
                                st.cache_data.clear()
                                st.toast("Ficha gravada com segurança na Base de Dados! 💪", icon="✅")
                                st.session_state.aluno_prontuario.update(dados_salvar)
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(f"❌ Erro na gravação SQL: {msg_bd}")

        with t2:
            with st.container(border=True):
                render_formulario_medicao(aluno, edit=None)

        with t3:
            try:
                hist = get_avaliacoes_aluno(aluno["id"])
                if hist is not None and not hist.empty:
                    st.markdown("<div style='border-top: 2px solid #1E88E5; margin-bottom: 5px;'></div>", unsafe_allow_html=True)
                    for _, a in hist.iterrows():
                        a_dict = a.to_dict()
                        c_h1, c_h2, c_h3 = st.columns([3, 0.5, 0.5], vertical_alignment="center")
                        c_h1.write(f"📅 **Avaliação em {a_dict.get('data_avaliacao', '')}**")
                        with c_h2:
                            st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                            if st.button("✏️", key=f"ed_{a_dict['id']}", help="Editar medição"):
                                st.session_state.medicao_editar = a_dict
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        with c_h3:
                            st.markdown('<div class="btn-compact">', unsafe_allow_html=True)
                            if st.button("🗑️", key=f"dl_{a_dict['id']}", help="Excluir medição"):
                                excluir_avaliacao_prontuario(a_dict["id"])
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        with st.expander("Ver Biofeedback"):
                            analisar_saude_visual(a_dict)
                        st.markdown("<hr style='margin: 4px 0px 8px 0px;'>", unsafe_allow_html=True)
                else:
                    st.info("Sem histórico registado.")
            except Exception:
                st.error("Erro ao carregar histórico.")

        with t4:
            with st.container(border=True):
                c_head_doc, c_top_doc = st.columns([4, 1], vertical_alignment="center")
                c_head_doc.markdown("### 📂 Documentação Legal Anual")
                btn_doc_top = c_top_doc.button("💾 Guardar Arquivos", key="save_top_doc", type="primary", use_container_width=True)

                st.info("Documentos permanentes/anuais do aluno (RG, Receituário contínuo e Atestado de Aptidão Física).")

                c_rg, c_rec, c_ate = st.columns(3, gap="large")

                with c_rg:
                    st.markdown("**1. Identidade (RG/CPF)**")
                    url_rg_atual = aluno.get("url_rg")
                    if url_rg_atual:
                        renderizar_documento_com_rotacao(url_rg_atual, "pv_rg")
                    else:
                        st.warning("Nenhum RG anexado.")
                    novo_rg = st.file_uploader("Atualizar RG", type=["jpg", "png", "jpeg", "pdf"], key="up_rg_p")

                with c_rec:
                    st.markdown("**2. Receituário Médico**")
                    url_rec_atual = aluno.get("url_receituario")
                    if url_rec_atual:
                        renderizar_documento_com_rotacao(url_rec_atual, "pv_rec")
                    else:
                        st.info("Nenhuma receita anexada.")
                    novo_rec = st.file_uploader("Atualizar Receita", type=["jpg", "png", "jpeg", "pdf"], key="up_rec_p")

                with c_ate:
                    st.markdown("**3. Atestado de Aptidão Física**")
                    url_ate_atual = aluno.get("url_atestado_medico")
                    if url_ate_atual:
                        renderizar_documento_com_rotacao(url_ate_atual, "pv_ate")
                    else:
                        st.error("Atestado em falta!")
                    novo_ate = st.file_uploader("Atualizar Atestado", type=["jpg", "png", "jpeg", "pdf"], key="up_ate_p")

                st.markdown("---")
                btn_doc_bot = st.button("💾 Guardar Novos Documentos Permanentes", key="save_bot_doc", type="primary", use_container_width=True)

                if btn_doc_top or btn_doc_bot:
                    if novo_rg or novo_rec or novo_ate:
                        with st.spinner("A processar ficheiros e a guardar na nuvem do MoveRight..."):
                            final_rg, final_rec, final_ate = url_rg_atual, url_rec_atual, url_ate_atual
                            upload_docs_ok = True

                            if novo_rg:
                                b_rg, n_rg, t_rg = processar_documento_prontuario(novo_rg.getvalue(), novo_rg.name, novo_rg.type)
                                u_rg, err_rg = upload_midia_diagnostico(b_rg, n_rg, t_rg)
                                if u_rg: final_rg = u_rg
                                else: upload_docs_ok = False; st.error(f"Erro RG: {err_rg}")

                            if novo_rec:
                                b_rec, n_rec, t_rec = processar_documento_prontuario(novo_rec.getvalue(), novo_rec.name, novo_rec.type)
                                u_rec, err_rec = upload_midia_diagnostico(b_rec, n_rec, t_rec)
                                if u_rec: final_rec = u_rec
                                else: upload_docs_ok = False; st.error(f"Erro Receita: {err_rec}")

                            if novo_ate:
                                b_ate, n_ate, t_ate = processar_documento_prontuario(novo_ate.getvalue(), novo_ate.name, novo_ate.type)
                                u_ate, err_ate = upload_midia_diagnostico(b_ate, n_ate, t_ate)
                                if u_ate: final_ate = u_ate
                                else: upload_docs_ok = False; st.error(f"Erro Atestado: {err_ate}")

                            if upload_docs_ok:
                                docs_salvar = {}
                                if final_rg != url_rg_atual: docs_salvar["url_rg"] = final_rg
                                if final_rec != url_rec_atual: docs_salvar["url_receituario"] = final_rec
                                if final_ate != url_ate_atual: docs_salvar["url_atestado_medico"] = final_ate

                                if docs_salvar:
                                    sucesso, msg_bd = atualizar_perfil_aluno_dict_seguro(aluno["id"], docs_salvar)
                                    if sucesso:
                                        st.cache_data.clear()
                                        st.toast("Documentos legais guardados com sucesso!", icon="✅")
                                        st.session_state.aluno_prontuario.update(docs_salvar)
                                        time.sleep(1.5)
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Erro ao guardar na base de dados: {msg_bd}")
                                else:
                                    st.info("Nenhuma alteração detetada nos documentos.")
                    else:
                        st.warning("Para guardar, anexe pelo menos um novo documento.")

            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🟡 Histórico de Atestados Temporários (Faltas Justificadas)", expanded=False):
                st.info("Use esta secção para arquivar atestados curtos (gripes, exames, etc) que justificaram as faltas do aluno. Eles não substituem o Atestado de Aptidão Física acima.")

                with st.form("form_novo_atestado_temp", clear_on_submit=True):
                    c_dt, c_motivo = st.columns([1, 2])
                    data_atestado = c_dt.date_input("Data do Atestado:", datetime.date.today(), format="DD/MM/YYYY")
                    motivo = c_motivo.text_input("Motivo / Observação:", placeholder="Ex: Gripe forte (3 dias de repouso)")
                    arq_atestado = st.file_uploader("Anexar Atestado (Foto ou PDF):", type=["jpg", "png", "jpeg", "pdf"])

                    if st.form_submit_button("➕ Arquivar Novo Atestado Temporário", type="primary", use_container_width=True):
                        if not arq_atestado:
                            st.error("Por favor, anexe a foto ou PDF do atestado.")
                        else:
                            with st.spinner("A enviar para a nuvem..."):
                                b_arq, n_arq, t_arq = processar_documento_prontuario(arq_atestado.getvalue(), arq_atestado.name, arq_atestado.type)
                                url_arq, err_arq = upload_midia_diagnostico(b_arq, n_arq, t_arq)

                                if url_arq:
                                    sucesso, msg = salvar_atestado_temporario(aluno["id"], data_atestado, motivo, url_arq)
                                    if sucesso:
                                        st.success("Atestado temporário arquivado com sucesso!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"Erro ao salvar na base de dados: {msg}")
                                else:
                                    st.error(f"Erro no envio do ficheiro: {err_arq}")

                atestados_hist = get_atestados_temporarios(aluno["id"])
                if atestados_hist is not None and not atestados_hist.empty:
                    st.markdown("#### 📁 Arquivo de Atestados")
                    for _, at_temp in atestados_hist.iterrows():
                        with st.container(border=True):
                            c_ht1, c_ht2 = st.columns([4, 1], vertical_alignment="center")
                            dt_format = pd.to_datetime(at_temp['data_registro']).strftime("%d/%m/%Y")
                            c_ht1.markdown(f"**Data:** {dt_format} <br> **Motivo:** {at_temp.get('motivo', 'Sem descrição')}", unsafe_allow_html=True)

                            with c_ht2:
                                url_t = at_temp['url_documento']
                                if ".pdf" in url_t.lower():
                                    st.link_button("📄 Abrir PDF", url_t, use_container_width=True)
                                else:
                                    with st.popover("Ver Foto"):
                                        st.image(url_t, use_container_width=True)
                else:
                    st.caption("Nenhum atestado temporário arquivado para este aluno.")