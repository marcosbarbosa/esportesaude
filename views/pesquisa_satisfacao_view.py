# ==============================================================================
# 📄 ARQUIVO: views/pesquisa_satisfacao_view.py
# 🏷️ VERSÃO: 6.4 (ULTRA-PRIME - Auto-Scroll + Modo Totem com Reset Automático)
# ==============================================================================

import streamlit as st
import datetime
import requests
import time  # 🚀 NECESSÁRIO PARA O TEMPORIZADOR DO MODO TOTEM
from database import supabase


# 🛡️ MOTOR DE AUDITORIA (IP E GEOLOCALIZAÇÃO)
def capturar_dados_auditoria():
    ip = "IP não rastreado"
    localizacao = "Localização não rastreada"
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = (
                headers.get("X-Forwarded-For", headers.get("X-Real-IP", "Desconhecido"))
                .split(",")[0]
                .strip()
            )

        if ip and ip not in [
            "Desconhecido",
            "127.0.0.1",
            "localhost",
            "IP não rastreado",
        ]:
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
    # 🎨 CSS ULTRA-ACESSÍVEL E BOTÃO GIGANTE
    # ==============================================================================
    st.markdown(
        """
        <style>
            #MainMenu, header, footer {visibility: hidden;}
            .block-container {padding-top: 0.5rem !important; max-width: 900px !important;}
            .stApp { background-color: #F8FAFC !important; }
            .painel-pesquisa { background-color: #FFFFFF; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border: 1px solid #E2E8F0; margin-bottom: 30px; }
            .titulo-pesquisa { color: #0A2540; text-align: center; font-weight: 950; font-size: 2.2rem; margin-bottom: 5px; text-transform: uppercase; }

            div[role="radiogroup"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; justify-content: space-between !important; margin: 15px 0 35px 0 !important; gap: 12px !important; }
            div[role="radiogroup"] label { flex: 1 1 0px !important; width: 100% !important; padding: 0 !important; display: flex !important; flex-direction: column !important; align-items: center !important; background: transparent !important; cursor: pointer !important; }
            div[role="radiogroup"] label > div:first-child { display: none !important; }
            div[role="radiogroup"] label p { font-size: 18px !important; font-weight: 950 !important; margin-top: 15px !important; line-height: 1.2 !important; padding: 12px 6px !important; border-radius: 12px !important; text-align: center !important; width: 100% !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; color: #475569; background-color: #F1F5F9; border: 3px solid #E2E8F0; transition: all 0.3s ease !important; }

            div[role="radiogroup"] label:has(input:checked) p { background-color: #1E88E5 !important; color: white !important; border-color: #1565C0 !important; box-shadow: 0 5px 15px rgba(30, 136, 229, 0.4) !important; }

            div[role="radiogroup"] label strong { width: 100px !important; height: 100px !important; border-radius: 50% !important; background-color: #FFFFFF !important; box-shadow: 0 8px 15px rgba(0,0,0,0.1) !important; display: flex !important; justify-content: center !important; align-items: center !important; margin: -20px auto 5px auto !important; position: relative !important; z-index: 10 !important; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important; font-size: 70px !important; border: 5px solid #E2E8F0 !important; filter: grayscale(100%) !important; opacity: 0.6 !important; }

            div[role="radiogroup"] label:has(strong):nth-child(1):has(input:checked) p { background-color: #EF4444 !important; color: white !important; border-color: #B91C1C !important; }
            div[role="radiogroup"] label:has(strong):nth-child(2):has(input:checked) p { background-color: #F59E0B !important; color: white !important; border-color: #B45309 !important; }
            div[role="radiogroup"] label:has(strong):nth-child(3):has(input:checked) p { background-color: #10B981 !important; color: white !important; border-color: #047857 !important; }
            div[role="radiogroup"] label:has(strong):has(input:checked) strong { filter: grayscale(0%) !important; opacity: 1 !important; transform: scale(1.1) !important; border-width: 6px !important; }

            .pergunta-texto { font-size: 26px; font-weight: 900; line-height: 1.3; color: #0A2540; margin-bottom: 35px; border-left: 8px solid #1E88E5; padding: 15px; background: #F8FAFC; border-radius: 4px 15px 15px 4px; box-shadow: 2px 2px 8px rgba(0,0,0,0.08); text-transform: uppercase; }

            button[kind="primaryFormSubmit"] { font-size: 28px !important; font-weight: 950 !important; padding: 25px 20px !important; height: auto !important; background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important; border: none !important; border-radius: 15px !important; box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4) !important; text-transform: uppercase !important; letter-spacing: 2px !important; transition: all 0.3s ease !important; }
            button[kind="primaryFormSubmit"]:hover { transform: translateY(-3px) !important; box-shadow: 0 15px 30px rgba(16, 185, 129, 0.6) !important; background: linear-gradient(135deg, #34D399 0%, #10B981 100%) !important; }

            hr { margin: 25px 0 !important; border-top: 2px solid #E2E8F0 !important;}

            @media (max-width: 600px) {
                div[role="radiogroup"] label strong { width: 65px !important; height: 65px !important; font-size: 45px !important; }
                div[role="radiogroup"] label p { font-size: 13px !important; }
                .pergunta-texto { font-size: 22px !important; }
                button[kind="primaryFormSubmit"] { font-size: 22px !important; }
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    param_t = st.query_params.get("t", "AUTO")
    if param_t == "1":
        trimestre_db = "1º Trimestre (Jan a Mar)"
    elif param_t == "2":
        trimestre_db = "2º Trimestre (Abr a Jun)"
    elif param_t == "3":
        trimestre_db = "3º Trimestre (Jul a Set)"
    elif param_t == "4":
        trimestre_db = "4º Trimestre (Out a Dez)"
    else:
        trimestre_db = "Período Atual"

    # ALVO PARA ROLAGEM DE TELA
    st.markdown("<div id='topo-da-pesquisa'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='painel-pesquisa'><div class='titulo-pesquisa'>Pesquisa de Satisfação</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='text-align: center; margin-bottom: 25px; color: #64748B; font-weight: 900; font-size: 22px; text-transform: uppercase;'>📌 {trimestre_db}</div>",
        unsafe_allow_html=True,
    )

    # 🟢 AQUI APARECERÁ A MENSAGEM GIGANTE DE SUCESSO
    placeholder_sucesso = st.empty()

    with st.form("form_pesquisa_definitiva", clear_on_submit=True):
        st.markdown(
            "<div class='pergunta-texto'>Qual é a sua Turma?</div>",
            unsafe_allow_html=True,
        )
        turma_opcao = st.radio(
            "turma",
            ["⏰ 08:00", "⏰ 09:00", "⏰ 10:00"],
            index=None,
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown("<hr>", unsafe_allow_html=True)

        opcoes_q1 = [
            "**😞** \n⭐ SEM ENERGIA",
            "**😐** \n⭐⭐⭐ MAIS OU MENOS",
            "**😄** \n⭐⭐⭐⭐⭐ ÓTIMO!",
        ]
        opcoes_q2 = [
            "**😞** \n⭐ AINDA DÓI",
            "**😐** \n⭐⭐⭐ MELHOROU POUCO",
            "**😄** \n⭐⭐⭐⭐⭐ PASSOU!",
        ]
        opcoes_q3 = [
            "**😞** \n⭐ NÃO NOTEI",
            "**😐** \n⭐⭐⭐ UM POUCO",
            "**😄** \n⭐⭐⭐⭐⭐ MUITO!",
        ]
        opcoes_q4 = [
            "**😞** \n⭐ REGULAR",
            "**😐** \n⭐⭐⭐ BOAS",
            "**😄** \n⭐⭐⭐⭐⭐ ÓTIMAS!",
        ]

        st.markdown(
            "<div class='pergunta-texto'>1. Disposição no dia a dia?</div>",
            unsafe_allow_html=True,
        )
        q1 = st.radio(
            "q1", opcoes_q1, index=None, horizontal=True, label_visibility="collapsed"
        )

        st.markdown(
            "<div class='pergunta-texto'>2. Melhora nas dores?</div>",
            unsafe_allow_html=True,
        )
        q2 = st.radio(
            "q2", opcoes_q2, index=None, horizontal=True, label_visibility="collapsed"
        )

        st.markdown(
            "<div class='pergunta-texto'>3. Efeito das aulas na sua vida?</div>",
            unsafe_allow_html=True,
        )
        q3 = st.radio(
            "q3", opcoes_q3, index=None, horizontal=True, label_visibility="collapsed"
        )

        st.markdown(
            "<div class='pergunta-texto'>4. O que achou das aulas?</div>",
            unsafe_allow_html=True,
        )
        q4 = st.radio(
            "q4", opcoes_q4, index=None, horizontal=True, label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_enviar = st.form_submit_button(
            "🚀 FINALIZAR E ENVIAR", type="primary", use_container_width=True
        )

        if btn_enviar:
            if not all([turma_opcao, q1, q2, q3, q4]):
                st.error(
                    "⚠️ Por favor, escolha a sua Turma e uma carinha para todas as perguntas antes de enviar!"
                )
            else:
                try:
                    ip_audit, geo_audit = capturar_dados_auditoria()
                    turma_db = f"Turma {turma_opcao.replace('⏰', '').strip()}"

                    payload = {
                        "turma": turma_db,
                        "q1_disposicao": q1.replace("**", "")
                        .replace("  \n", " ")
                        .strip(),
                        "q2_dores": q2.replace("**", "").replace("  \n", " ").strip(),
                        "q3_efeito_vida": q3.replace("**", "")
                        .replace("  \n", " ")
                        .strip(),
                        "q4_avaliacao_geral": q4.replace("**", "")
                        .replace("  \n", " ")
                        .strip(),
                        "data_resposta": datetime.datetime.now().isoformat(),
                        "trimestre_referencia": trimestre_db.split(" (")[0],
                        "ip_registro": ip_audit,
                        "localizacao_registro": geo_audit,
                    }
                    supabase.table("pesquisas_satisfacao").insert(payload).execute()

                    # 1️⃣ MOSTRA A MENSAGEM GIGANTE
                    mensagem_sucesso = """
                    <div id="msg-sucesso-fim" style="background-color: #D1FAE5; border: 5px solid #10B981; border-radius: 15px; padding: 35px; text-align: center; margin-bottom: 25px; box-shadow: 0 10px 25px rgba(16, 185, 129, 0.3);">
                        <h1 style="color: #047857; font-size: 45px; font-weight: 950; margin: 0; text-transform: uppercase;">💚 OBRIGADO!</h1>
                        <p style="color: #065F46; font-size: 26px; font-weight: 800; margin: 15px 0 0 0; line-height: 1.2;">PESQUISA ENVIADA COM SUCESSO!</p>
                    </div>
                    """
                    placeholder_sucesso.markdown(
                        mensagem_sucesso, unsafe_allow_html=True
                    )

                    # 2️⃣ SOLTA OS BALÕES E SOBE A TELA
                    st.balloons()
                    st.components.v1.html(
                        """
                        <script>
                            var doc = window.parent.document;
                            var elem = doc.getElementById('topo-da-pesquisa');
                            if(elem) {
                                elem.scrollIntoView({behavior: 'smooth', block: 'start'});
                            }
                        </script>
                        """,
                        height=0,
                    )

                    # 3️⃣ A MÁGICA: ESPERA 3.5 SEGUNDOS E REINICIA A TELA
                    time.sleep(3.5)
                    st.rerun()

                except Exception as e:
                    st.error(f"Erro ao salvar: {e}.")

    st.markdown("</div>", unsafe_allow_html=True)
