import streamlit as st
import datetime
import requests
from database import supabase

# 🛡️ MOTOR DE AUDITORIA (IP E GEOLOCALIZAÇÃO)
def capturar_dados_auditoria():
    ip = "IP não rastreado"
    localizacao = "Localização não rastreada"
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "Desconhecido")).split(",")[0].strip()

        if ip and ip not in ["Desconhecido", "127.0.0.1", "localhost", "IP não rastreado"]:
            try:
                resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=3).json()
                if resp.get("status") == "success":
                    localizacao = f"{resp.get('city', '')} - {resp.get('region', '')}, {resp.get('countryCode', '')}"
            except:
                pass
    except:
        pass
    return ip, localizacao

def tela_pesquisa_satisfacao_move_right():
    # ==============================================================================
    # 🎨 CSS ULTRA-ACESSÍVEL (PÚBLICO 60+)
    # ==============================================================================
    st.markdown("""
        <style>
            #MainMenu, header, footer {visibility: hidden;}
            .block-container {padding-top: 0.5rem !important; max-width: 900px !important;}
            .stApp { background-color: #F8FAFC !important; }
            .painel-pesquisa { background-color: #FFFFFF; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border: 1px solid #E2E8F0; margin-bottom: 30px; }
            .titulo-pesquisa { color: #0A2540; text-align: center; font-weight: 950; font-size: 2.2rem; margin-bottom: 5px; text-transform: uppercase; }

            /* Aumento expressivo do tamanho e espaçamento dos botões */
            div[role="radiogroup"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; justify-content: center !important; align-items: flex-start !important; margin: 15px 0 35px 0 !important; gap: 20px !important; }
            div[role="radiogroup"] label { width: 220px !important; padding: 0 !important; display: flex !important; flex-direction: column !important; align-items: center !important; background: transparent !important; cursor: pointer !important; }
            div[role="radiogroup"] label > div:first-child { display: none !important; }

            /* Textos das opções com Fonte Gigante e Estrelas */
            div[role="radiogroup"] label p { font-size: 18px !important; font-weight: 950 !important; margin-top: 20px !important; line-height: 1.3 !important; padding: 12px 8px !important; border-radius: 12px !important; text-align: center !important; width: 100% !important; text-transform: uppercase !important; letter-spacing: 1px !important; color: #475569; background-color: #F1F5F9; border: 3px solid #E2E8F0; transition: all 0.3s ease !important; }

            /* Carinhas (Emojis) ainda maiores */
            div[role="radiogroup"] label strong { width: 120px !important; height: 120px !important; border-radius: 50% !important; background-color: #FFFFFF !important; box-shadow: 0 8px 15px rgba(0,0,0,0.1) !important; display: flex !important; justify-content: center !important; align-items: center !important; margin: -30px auto 10px auto !important; position: relative !important; z-index: 10 !important; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important; font-size: 85px !important; border: 5px solid #E2E8F0 !important; filter: grayscale(100%) !important; opacity: 0.6 !important; }

            /* Efeitos de Hover e Seleção mantidos com cores vibrantes */
            div[role="radiogroup"] label:nth-child(1):hover strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.15) translateY(-10px) !important; border-color: #EF4444 !important; box-shadow: 0 10px 25px rgba(239, 68, 68, 0.4) !important; z-index: 99 !important; }
            div[role="radiogroup"] label:nth-child(1):has(input:checked) strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.15) translateY(-10px) !important; border-color: #EF4444 !important; background-color: #FEE2E2 !important; box-shadow: 0 0 25px rgba(239, 68, 68, 0.6) !important; border-width: 8px !important; z-index: 99 !important; }
            div[role="radiogroup"] label:nth-child(1):has(input:checked) p { background-color: #EF4444 !important; color: white !important; border-color: #B91C1C !important; }

            div[role="radiogroup"] label:nth-child(2):hover strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.15) translateY(-10px) !important; border-color: #F59E0B !important; box-shadow: 0 10px 25px rgba(245, 158, 11, 0.4) !important; z-index: 99 !important; }
            div[role="radiogroup"] label:nth-child(2):has(input:checked) strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.15) translateY(-10px) !important; border-color: #F59E0B !important; background-color: #FEF3C7 !important; box-shadow: 0 0 25px rgba(245, 158, 11, 0.6) !important; border-width: 8px !important; z-index: 99 !important; }
            div[role="radiogroup"] label:nth-child(2):has(input:checked) p { background-color: #F59E0B !important; color: white !important; border-color: #B45309 !important; }

            div[role="radiogroup"] label:nth-child(3):hover strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.15) translateY(-10px) !important; border-color: #10B981 !important; box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4) !important; z-index: 99 !important; }
            div[role="radiogroup"] label:nth-child(3):has(input:checked) strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.15) translateY(-10px) !important; border-color: #10B981 !important; background-color: #D1FAE5 !important; box-shadow: 0 0 25px rgba(16, 185, 129, 0.6) !important; border-width: 8px !important; z-index: 99 !important; }
            div[role="radiogroup"] label:nth-child(3):has(input:checked) p { background-color: #10B981 !important; color: white !important; border-color: #047857 !important; }

            /* 🚀 FIX: Aumento massivo da fonte das perguntas */
            .pergunta-texto { font-size: 26px; font-weight: 900; line-height: 1.3; color: #0A2540; margin-bottom: 35px; border-left: 8px solid #1E88E5; padding-left: 15px; background: #F8FAFC; padding: 15px; border-radius: 4px 15px 15px 4px; box-shadow: 2px 2px 8px rgba(0,0,0,0.08); }
            hr { margin: 25px 0 !important; border-top: 2px solid #E2E8F0 !important;}

            /* Responsividade para não quebrar em tablets menores */
            @media (max-width: 768px) {
                div[role="radiogroup"] { gap: 15px !important; padding-top: 25px !important; }
                div[role="radiogroup"] label { width: 160px !important; }
                div[role="radiogroup"] label strong { width: 90px !important; height: 90px !important; font-size: 65px !important; margin-top: -20px !important; }
                div[role="radiogroup"] label p { font-size: 15px !important; padding: 10px 6px !important; }
                .pergunta-texto { font-size: 22px !important; }
                .titulo-pesquisa { font-size: 1.8rem !important; }
            }
        </style>
    """, unsafe_allow_html=True)

    param_t = st.query_params.get("t", "AUTO")

    if param_t == "1":
        trimestre_display = "1º Trimestre (Jan a Mar)"
        trimestre_db = "1º Trimestre"
    elif param_t == "2":
        trimestre_display = "2º Trimestre (Abr a Jun)"
        trimestre_db = "2º Trimestre"
    elif param_t == "3":
        trimestre_display = "3º Trimestre (Jul a Set)"
        trimestre_db = "3º Trimestre"
    elif param_t == "4":
        trimestre_display = "4º Trimestre (Out a Dez)"
        trimestre_db = "4º Trimestre"
    else:
        trimestre_display = "Período Atual (Automático)"
        trimestre_db = "Automático"

    st.markdown("<div class='painel-pesquisa'><div class='titulo-pesquisa'>Pesquisa de Satisfação</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; margin-bottom: 30px; color: #64748B; font-weight: 700; font-size: 15px; border-bottom: 2px dashed #E2E8F0; padding-bottom: 12px;'>📌 Referência da Avaliação: <span style='color: #0056b3;'>{trimestre_display}</span></div>", unsafe_allow_html=True)

    with st.form("form_pesquisa_definitiva", clear_on_submit=True):
        turma = st.selectbox("Selecione a sua Turma:", ["Turma 08:00", "Turma 09:00", "Turma 10:00"])
        st.markdown("<hr>", unsafe_allow_html=True)

        # 🚀 FIX: Injeção das Estrelinhas e Textos Ultra-Resumidos
        opcoes_q1 = ["**😞** \n⭐ SEM ENERGIA", "**😐** \n⭐⭐⭐ MAIS OU MENOS", "**😄** \n⭐⭐⭐⭐⭐ ÓTIMO!"]
        opcoes_q2 = ["**😞** \n⭐ AINDA DÓI", "**😐** \n⭐⭐⭐ MELHOROU POUCO", "**😄** \n⭐⭐⭐⭐⭐ PASSOU!"]
        opcoes_q3 = ["**😞** \n⭐ NÃO NOTEI", "**😐** \n⭐⭐⭐ UM POUCO", "**😄** \n⭐⭐⭐⭐⭐ MUITO!"]
        opcoes_q4 = ["**😞** \n⭐ REGULAR", "**😐** \n⭐⭐⭐ BOAS", "**😄** \n⭐⭐⭐⭐⭐ ÓTIMAS!"]

        # 🚀 FIX: Perguntas diretas e gigantes
        st.markdown("<div class='pergunta-texto'>1. Disposição no dia a dia?</div>", unsafe_allow_html=True)
        q1 = st.radio("q1", opcoes_q1, index=None, horizontal=True, label_visibility="collapsed")

        st.markdown("<div class='pergunta-texto'>2. Melhora nas dores?</div>", unsafe_allow_html=True)
        q2 = st.radio("q2", opcoes_q2, index=None, horizontal=True, label_visibility="collapsed")

        st.markdown("<div class='pergunta-texto'>3. Efeito das aulas na sua vida?</div>", unsafe_allow_html=True)
        q3 = st.radio("q3", opcoes_q3, index=None, horizontal=True, label_visibility="collapsed")

        st.markdown("<div class='pergunta-texto'>4. O que achou das aulas?</div>", unsafe_allow_html=True)
        q4 = st.radio("q4", opcoes_q4, index=None, horizontal=True, label_visibility="collapsed")

        # CAMPO DISSERTATIVO REMOVIDO COM SUCESSO ✂️

        st.markdown("<br>", unsafe_allow_html=True)

        # Botão ainda mais amigável
        btn_enviar = st.form_submit_button("🚀 FINALIZAR E ENVIAR", type="primary", use_container_width=True)

        if btn_enviar:
            if not all([q1, q2, q3, q4]):
                st.error("⚠️ Por favor, escolha uma carinha para cada pergunta antes de enviar!")
            else:
                try:
                    ip_audit, geo_audit = capturar_dados_auditoria()

                    # O Payload não precisa mais enviar a variável de "comentario"
                    payload = {
                        "turma": turma,
                        "q1_disposicao": q1.replace("**", "").replace("  \n", " ").strip(),
                        "q2_dores": q2.replace("**", "").replace("  \n", " ").strip(),
                        "q3_efeito_vida": q3.replace("**", "").replace("  \n", " ").strip(),
                        "q4_avaliacao_geral": q4.replace("**", "").replace("  \n", " ").strip(),
                        "data_resposta": datetime.datetime.now().isoformat(),
                        "trimestre_referencia": trimestre_db,
                        "ip_registro": ip_audit,
                        "localizacao_registro": geo_audit
                    }
                    supabase.table("pesquisas_satisfacao").insert(payload).execute()
                    st.success("💚 Muito obrigado! A sua opinião foi registada com sucesso.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}.")

    st.markdown("</div>", unsafe_allow_html=True)