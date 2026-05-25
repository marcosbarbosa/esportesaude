# ==============================================================================
# 📄 views/config_niver_view.py
# ⚙️  Painel de Configuração — Automação de Aniversários
#    (E-mail + Z-API + Mensagem Padrão)
# ==============================================================================

import json
import streamlit as st
from utils.niver_automatico import (
    get_config_niver,
    salvar_config_niver,
    enviar_email_aniversariantes,
    disparar_zapi_aniversariantes,
)


def tela_config_niver():
    st.markdown("### 🎂 Automação de Aniversários")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-top:-8px;margin-bottom:16px;'>"
        "Configure e-mail de notificação diária e disparo automático via WhatsApp (Z-API).</p>",
        unsafe_allow_html=True,
    )

    cfg = get_config_niver()

    # ── MENSAGEM PADRÃO ───────────────────────────────────────────────────────
    with st.expander("💬 Mensagem Padrão de Aniversário", expanded=True):
        st.caption("Use {nome} para inserir o primeiro nome do aluno automaticamente.")
        nova_msg = st.text_area(
            "Texto da mensagem:",
            value=cfg["mensagem_padrao"],
            height=100,
            key="niver_msg_padrao",
        )
        st.markdown(
            f"<div style='background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;"
            f"padding:10px 14px;font-size:12px;color:#166534;margin-top:6px;'>"
            f"<strong>Prévia:</strong> {nova_msg.replace('{nome}', '<b>João</b>')}</div>",
            unsafe_allow_html=True,
        )
        if st.button("💾 Salvar Mensagem", key="btn_salvar_msg"):
            salvar_config_niver({"niver_mensagem_padrao": nova_msg})
            st.success("✅ Mensagem salva!")
            st.rerun()

    st.markdown("---")

    # ── E-MAIL ────────────────────────────────────────────────────────────────
    with st.expander("📧 Notificação por E-mail", expanded=True):
        st.markdown(
            "<p style='font-size:12px;color:#475569;margin:0 0 10px;'>"
            "Toda manhã o sistema envia um e-mail com os aniversariantes do dia. "
            "Cada aluno tem um botão clicável que abre o WhatsApp com a mensagem pronta.</p>",
            unsafe_allow_html=True,
        )

        email_hab = st.toggle(
            "Habilitar notificação por e-mail",
            value=cfg["email_habilitado"],
            key="niver_email_toggle",
        )

        col_em_dias, col_em_dest = st.columns([1, 2])
        with col_em_dias:
            aviso_dias = st.number_input(
                "Avisar com quantos dias de antecedência:",
                min_value=0,
                max_value=30,
                value=int(cfg.get("aviso_dias", 0)),
                step=1,
                key="niver_aviso_dias_input",
                help=(
                    "0 = avisa somente no dia do aniversário\n"
                    "1 = avisa também 1 dia antes\n"
                    "3 = avisa nos 3 dias anteriores + o próprio dia"
                ),
            )
        with col_em_dest:
            emails_input = st.text_input(
                "E-mails de destino (separados por vírgula):",
                value=", ".join(cfg["emails_destino"]),
                placeholder="gestor@academia.com, coordenador@academia.com",
                key="niver_emails_dest",
            )

        col_rem, col_sen = st.columns(2)
        with col_rem:
            remetente = st.text_input(
                "E-mail remetente (Gmail):",
                value=cfg["email_remetente"],
                placeholder="sistema@academia.com",
                key="niver_email_rem",
            )
        with col_sen:
            senha_app = st.text_input(
                "Senha de App Gmail:",
                value=cfg["email_senha_app"],
                type="password",
                placeholder="xxxx xxxx xxxx xxxx",
                key="niver_email_senha",
                help="Gere em: Conta Google → Segurança → Senhas de app",
            )

        st.info(
            "💡 **Como obter a Senha de App Gmail:** acesse myaccount.google.com → "
            "Segurança → Verificação em 2 etapas → Senhas de app → Selecione 'Outro' "
            "→ copie a senha gerada de 16 dígitos.",
            icon="ℹ️",
        )

        col_s, col_t = st.columns([1, 1])
        with col_s:
            if st.button("💾 Salvar Config. E-mail", key="btn_salvar_email", use_container_width=True):
                lista_emails = [e.strip() for e in emails_input.split(",") if e.strip()]
                salvar_config_niver({
                    "niver_email_habilitado": "1" if email_hab else "0",
                    "niver_emails_destino": json.dumps(lista_emails),
                    "niver_email_remetente": remetente,
                    "niver_email_senha_app": senha_app,
                    "niver_aviso_dias": str(int(aviso_dias)),
                })
                st.success("✅ Configurações de e-mail salvas!")
                st.rerun()
        with col_t:
            if st.button("🧪 Enviar E-mail de Teste", key="btn_teste_email", use_container_width=True):
                import pandas as pd, datetime
                df_teste = pd.DataFrame([{
                    "nome": "ALUNO TESTE",
                    "dia": datetime.date.today().day,
                    "mes": datetime.date.today().month,
                    "turma": "Turma A",
                    "whatsapp": "",
                }])
                cfg_atual = get_config_niver()
                cfg_atual["emails_destino"] = [e.strip() for e in emails_input.split(",") if e.strip()]
                cfg_atual["email_remetente"] = remetente
                cfg_atual["email_senha_app"] = senha_app
                ok, msg = enviar_email_aniversariantes(df_teste, cfg_atual)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    st.markdown("---")

    # ── Z-API ─────────────────────────────────────────────────────────────────
    with st.expander("📱 WhatsApp Automático via Z-API", expanded=False):
        st.markdown(
            "<p style='font-size:12px;color:#475569;margin:0 0 10px;'>"
            "Quando habilitado, o sistema dispara mensagens de parabéns automaticamente "
            "no horário configurado. Necessita conta em "
            "<a href='https://z-api.io' target='_blank'>z-api.io</a> (~R$79/mês).</p>",
            unsafe_allow_html=True,
        )

        zapi_hab = st.toggle(
            "Habilitar disparo automático via Z-API",
            value=cfg["zapi_habilitado"],
            key="niver_zapi_toggle",
        )

        col_inst, col_tok = st.columns(2)
        with col_inst:
            zapi_instance = st.text_input(
                "ID da Instância:",
                value=cfg["zapi_instance"],
                placeholder="Ex: 3D581E87A3341331BD6B",
                key="niver_zapi_inst",
                help="Encontrado no painel Z-API em 'Instâncias'",
            )
        with col_tok:
            zapi_token = st.text_input(
                "Token:",
                value=cfg["zapi_token"],
                placeholder="Ex: F75DC1CA4E36B5B8",
                type="password",
                key="niver_zapi_tok",
            )

        col_ct, col_hr = st.columns(2)
        with col_ct:
            zapi_client = st.text_input(
                "Client-Token (Security):",
                value=cfg["zapi_client_token"],
                placeholder="Opcional — encontrado em 'Security'",
                type="password",
                key="niver_zapi_client",
            )
        with col_hr:
            zapi_horario = st.text_input(
                "Horário do disparo automático:",
                value=cfg["zapi_horario"],
                placeholder="08:00",
                key="niver_zapi_hr",
                help="O operador que abrir o sistema perto desse horário aciona o disparo",
            )

        st.warning(
            "⚠️ O disparo automático ocorre quando **qualquer operador logado** abre o sistema "
            "no horário configurado (±30 min). Para disparo verdadeiramente agendado sem "
            "intervenção humana, configure um cron externo.",
            icon="⚠️",
        )

        col_sz, col_tz = st.columns([1, 1])
        with col_sz:
            if st.button("💾 Salvar Config. Z-API", key="btn_salvar_zapi", use_container_width=True):
                salvar_config_niver({
                    "niver_zapi_habilitado": "1" if zapi_hab else "0",
                    "niver_zapi_instance": zapi_instance,
                    "niver_zapi_token": zapi_token,
                    "niver_zapi_client_token": zapi_client,
                    "niver_zapi_horario": zapi_horario,
                })
                st.success("✅ Configurações Z-API salvas!")
                st.rerun()
        with col_tz:
            if st.button("🧪 Testar Conexão Z-API", key="btn_teste_zapi", use_container_width=True):
                if not zapi_instance or not zapi_token:
                    st.error("❌ Preencha instância e token antes de testar.")
                else:
                    url = (
                        f"https://api.z-api.io/instances/{zapi_instance}"
                        f"/token/{zapi_token}/status"
                    )
                    headers = {}
                    if zapi_client:
                        headers["Client-Token"] = zapi_client
                    try:
                        import requests as _req
                        r = _req.get(url, headers=headers, timeout=10)
                        if r.status_code == 200:
                            st.success(f"✅ Z-API conectada! Resposta: {r.json()}")
                        else:
                            st.error(f"❌ Z-API retornou {r.status_code}: {r.text[:300]}")
                    except Exception as e:
                        st.error(f"❌ Erro ao conectar Z-API: {e}")
