# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_tablet.py
# 🏷️ VERSÃO: 32.1 (PRIME GOLD - Super Zoom & Ciclo de 3 Estados com Atestado)
# ⚙️ FUNÇÃO: Grid visual de alunos com suporte a trava de governação de 10 dias.
# ==============================================================================
import streamlit as st
import pandas as pd
from database import alternar_presenca, supabase

def atualizar_status_presenca_3_estados(aluno_id, data_aula, novo_status):
    """Motor injetado diretamente para lidar com os 3 estados no Supabase."""
    try:
        if novo_status == "AUSENTE":
            # Apaga o registo se a pessoa faltou sem justificativa
            supabase.table("frequencia").delete().eq("aluno_id", str(aluno_id)).eq("data_aula", str(data_aula)).execute()
            return True
        else:
            # Insere ou atualiza (Upsert) para PRESENTE ou JUSTIFICADA
            payload = {
                "aluno_id": str(aluno_id),
                "data_aula": str(data_aula),
                "status": novo_status
            }
            existe = supabase.table("frequencia").select("id").eq("aluno_id", str(aluno_id)).eq("data_aula", str(data_aula)).execute()
            if hasattr(existe, 'data') and len(existe.data) > 0:
                supabase.table("frequencia").update({"status": novo_status}).eq("id", existe.data[0]["id"]).execute()
            else:
                supabase.table("frequencia").insert(payload).execute()
            return True
    except Exception as e:
        print(f"Erro frequencia 3 estados: {e}")
        return False

def cycle_presence_btn(aluno_id, data_aula, status_atual, nome_aluno):
    """Gira entre: AUSENTE -> PRESENTE -> JUSTIFICADA -> AUSENTE..."""
    if status_atual == "PRESENTE":
        novo_status = "JUSTIFICADA"
        msg, icone = "ATESTADO/JUSTIFICADA", "🟡"
    elif status_atual == "JUSTIFICADA":
        novo_status = "AUSENTE"
        msg, icone = "FALTA (DESMARCADO)", "🔴"
    else:
        novo_status = "PRESENTE"
        msg, icone = "PRESENTE", "🟢"

    if atualizar_status_presenca_3_estados(aluno_id, data_aula, novo_status):
        st.toast(f"👤 {nome_aluno.split()[0]}: {msg}", icon=icone)
    else:
        st.toast("🚨 Erro crítico de rede.", icon="🚨")

# 🚀 NOVA ASSINATURA: Agora recebe a variável bloqueio_ativo
def renderizar_aba_terminal(df_alunos_tab, data_aula, presencas_turma_geral, bloqueio_ativo=False):
    if df_alunos_tab.empty:
        st.warning("Selecione uma turma para carregar os alunos.")
        return

    # O CSS encostado na margem esquerda para evitar formatação de código do Markdown
    st.markdown("""
<style>
    /* 🛡️ QUARENTENA CSS: Isolado apenas para a aba Tablet */
    [data-testid="stColumn"]:has(.celula-tablet) {
        position: relative !important;
    }

    [data-testid="stColumn"]:has(.celula-tablet) div[data-testid="stButton"] button {
        position: absolute !important;
        top: 10px !important; 
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 140% !important;
        height: 220px !important; 
        min-height: 220px !important;
        max-height: 220px !important;
        z-index: 9999 !important; 
        opacity: 0 !important; 
        background: transparent !important;
        border: none !important;
        cursor: pointer !important;
    }

    /* ESTRUTURA VISUAL DA CÉLULA */
    .celula-tablet {
        display: flex;
        flex-direction: column;
        align-items: center;
        height: 240px; 
        padding-top: 10px;
        pointer-events: none; 
    }

    /* A FOTO DO ALUNO */
    .avatar-visual {
        position: relative;
        margin-top: 10px;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 5px solid #E2E8F0; 
        background-color: #F8FAFC;
        display: flex; align-items: center; justify-content: center;
        transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275), border-color 0.3s, box-shadow 0.3s;
    }

    .img-container {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        overflow: hidden;
    }
    .img-container img { width: 100%; height: 100%; object-fit: cover; }
    .avatar-visual-text { font-size: 11px; font-weight: 900; color: #94A3B8; text-transform: uppercase; text-align: center; padding: 10px; line-height: 1.1; }

    /* 🔒 CADEADO VISUAL */
    .lock-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background: #FEE2E2;
        border: 2px solid #EF4444;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        font-size: 13px;
        z-index: 100;
    }

    /* DISTINTIVO CLEAN */
    .badge-status {
        position: absolute;
        top: 105px; 
        left: 50%;
        transform: translateX(-50%);
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 900; font-size: 14px;
        border: 2px solid white;
        transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275), background 0.3s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        z-index: 60;
    }

    /* NOME DO ALUNO */
    .nome-aluno {
        position: absolute;
        top: 145px; 
        left: 0;
        width: 100%;
        text-align: center;
        font-size: 11px; font-weight: 900; color: #1E293B;
        text-transform: uppercase; line-height: 1.2;
        transition: all 0.4s ease-out; 
    }

    /* 🚀 A MÁGICA DO SUPER ZOOM (ATUALIZADA) */
    [data-testid="stColumn"]:has(.celula-tablet):hover .avatar-visual {
        transform: scale(3.8) !important; /* Escala aumentada para igualar ao tab_lista */
        box-shadow: 0 25px 60px rgba(0,0,0,0.6);
        z-index: 99999; /* Z-index gigante para sobrepor tudo */
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .badge-status {
        transform: translateX(-50%) translateY(90px) scale(1.5) !important; /* Movido um pouco mais para baixo para não cobrir a foto grande */
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .nome-aluno {
        transform: translateY(40px);
        opacity: 0;
    }

    /* 🟢/🔴/🟡 ESTADOS DE PRESENÇA */
    .status-ausente .avatar-visual { border-color: #CBD5E1; }
    .status-ausente .badge-status { background: #F1F5F9; color: #94A3B8; }
    .status-ausente .img-container,
    .status-ausente .avatar-visual-text {
        filter: brightness(0.8) grayscale(50%);
        transition: filter 0.4s ease;
    }

    .status-presente .avatar-visual { border-color: #22C55E !important; box-shadow: 0 0 15px rgba(34,197,94,0.3); }
    .status-presente .badge-status { background: #22C55E !important; color: white !important; }
    .status-presente .img-container,
    .status-presente .avatar-visual-text {
        filter: brightness(1) grayscale(0%);
        transition: filter 0.4s ease;
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .status-presente .avatar-visual {
        box-shadow: 0 35px 80px rgba(34,197,94,0.6) !important; /* Brilho mais forte no zoom */
    }

    /* 🟡 JUSTIFICADA / ATESTADO (NOVO) */
    .status-justificada .avatar-visual { border-color: #F59E0B !important; box-shadow: 0 0 15px rgba(245,158,11,0.3); }
    .status-justificada .badge-status { background: #F59E0B !important; color: white !important; }
    .status-justificada .img-container, .status-justificada .avatar-visual-text { filter: brightness(0.95) sepia(0.3) hue-rotate(-15deg); transition: filter 0.4s ease; }
    [data-testid="stColumn"]:has(.celula-tablet):hover .status-justificada .avatar-visual { box-shadow: 0 35px 80px rgba(245,158,11,0.6) !important; }
</style>
""", unsafe_allow_html=True)

    # 📊 LÓGICA DA BARRA DE PROGRESSO (ATUALIZADA PARA 3 ESTADOS)
    total_alunos = len(df_alunos_tab)

    q_presentes = 0
    q_justificadas = 0

    for status_bd in presencas_turma_geral.values():
        if status_bd == "JUSTIFICADA": q_justificadas += 1
        elif status_bd == "PRESENTE" or status_bd is True: q_presentes += 1

    # O "Total Apto" remove os atestados da conta! É a proteção do aluno!
    total_aptos = total_alunos - q_justificadas

    if total_aptos > 0:
        razao_progresso = q_presentes / total_aptos
        percentagem = int(razao_progresso * 100)
    else:
        razao_progresso = 0.0
        percentagem = 0

    bloco_justificativas = f" <span style='font-size:16px; color:#F59E0B;'>| {q_justificadas} ATESTADOS</span>" if q_justificadas > 0 else ""

    st.markdown(f"""
<div style='text-align: center; margin-bottom: 10px;'>
    <h2 style='color: #1E88E5; font-weight: 900; margin-bottom:0;'>{q_presentes} / {total_aptos} PRESENTES {bloco_justificativas}</h2>
    <span style='font-size:13px; color:#64748B;'>*Os atestados médicos não penalizam a barra de presença.</span>
</div>
""", unsafe_allow_html=True)

    st.progress(razao_progresso, text=f"Taxa de Presença Útil: {percentagem}%")
    st.markdown("<br><br>", unsafe_allow_html=True)

    # ==============================================================================
    # 🖼️ RENDERIZAÇÃO DOS ALUNOS (6 COLUNAS)
    # ==============================================================================
    COLS = 6

    for i in range(0, total_alunos, COLS):
        cols = st.columns(COLS, gap="large")

        for j, (_, row) in enumerate(df_alunos_tab.iloc[i : i + COLS].iterrows()):
            with cols[j]:
                # 🚀 INTERPRETAÇÃO DO STATUS
                status_bd = presencas_turma_geral.get(row["id"])

                if status_bd == "JUSTIFICADA":
                    status_atual = "JUSTIFICADA"
                    status_class = "status-justificada"
                    indicador = "⚕️"
                elif status_bd == "PRESENTE" or status_bd is True:
                    status_atual = "PRESENTE"
                    status_class = "status-presente"
                    indicador = "✓"
                else:
                    status_atual = "AUSENTE"
                    status_class = "status-ausente"
                    indicador = "X"

                url_foto = row.get("url_foto")
                nome_formatado = str(row["nome"])[:30].strip()

                cadeado_html = "<div class='lock-badge'>🔒</div>" if bloqueio_ativo else ""

                if not bloqueio_ativo:
                    if st.button(" ", key=f"tbt_prod_{row['id']}", use_container_width=True):
                        cycle_presence_btn(row["id"], data_aula, status_atual, row["nome"])
                        st.rerun()

                if pd.notna(url_foto) and str(url_foto).strip() != "":
                    avatar_html = f'<div class="img-container"><img src="{url_foto}"></div>'
                else:
                    avatar_html = f'<div class="avatar-visual-text">{nome_formatado}</div>'

                # HTML inline para evitar falhas no Markdown
                cartao_html_seguro = f'<div class="celula-tablet {status_class}"><div class="avatar-visual">{avatar_html}{cadeado_html}</div><div class="badge-status">{indicador}</div><div class="nome-aluno">{nome_formatado}</div></div>'

                st.markdown(cartao_html_seguro, unsafe_allow_html=True)