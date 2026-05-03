# ==============================================================================
# 📄 views/identidade_view.py
# ⚙️ Ecrã de edição da Identidade Visual do sistema
# ==============================================================================

import streamlit as st
import os
import shutil
from utils.identidade import get_config, salvar_config, render_cabecalho_html, render_rodape_html


def tela_identidade_visual():
    st.markdown(
        "<h3 style='color:#0A2540;font-weight:800;margin-bottom:4px;'>"
        "🎨 Identidade Visual do Sistema</h3>"
        "<p style='color:#64748B;margin-bottom:20px;'>Configure o cabeçalho e rodapé padrão "
        "que aparece em <strong>todos os relatórios</strong>: fichas, PDFs, Word e Excel.</p>",
        unsafe_allow_html=True,
    )

    cfg = get_config()

    # ── Preview ──────────────────────────────────────────────────────────────
    with st.expander("👁️ Pré-visualização do cabeçalho e rodapé actuais", expanded=True):
        st.markdown(
            render_cabecalho_html(cfg, extra="Exemplo de período: Janeiro/2026")
            + render_rodape_html(cfg),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Formulário de edição ─────────────────────────────────────────────────
    with st.form("form_identidade"):
        st.markdown("#### 📝 Textos do Projecto")
        c1, c2 = st.columns(2)
        titulo = c1.text_input("Título do Projecto (linha 1)", value=cfg.get("titulo_projeto", ""))
        subtitulo = c2.text_input("Subtítulo (linha 2)", value=cfg.get("subtitulo_projeto", ""))

        st.markdown("#### 🏢 Dados da Organização")
        c3, c4 = st.columns(2)
        nome_org = c3.text_input("Nome da Organização", value=cfg.get("nome_organizacao", ""))
        cnpj = c4.text_input("CNPJ", value=cfg.get("cnpj", ""))

        c5, c6 = st.columns(2)
        site = c5.text_input("Site (sem https://)", value=cfg.get("site", ""))
        instagram = c6.text_input("Instagram (ex: @institutomudabrasil)", value=cfg.get("instagram", ""))

        c7, c8 = st.columns(2)
        telefone = c7.text_input("Telefone / WhatsApp", value=cfg.get("telefone", ""))
        email = c8.text_input("E-mail de Contacto", value=cfg.get("email_contato", ""))

        endereco = st.text_input("Endereço Completo", value=cfg.get("endereco", ""))

        st.markdown("#### 🖼️ Logomarcas")
        st.caption(
            "Faça upload para substituir as imagens actuais. "
            "Formatos aceites: PNG, JPG. Tamanho ideal: 300×100 px."
        )
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            st.markdown(f"**Logo Principal** — `{cfg.get('logo_principal','logo-imbra.png')}`")
            st.caption("Geralmente o logo da organização executora (Instituto Muda Brasil)")
            upload_principal = st.file_uploader(
                "Substituir Logo Principal", type=["png", "jpg", "jpeg"],
                key="up_logo_p", label_visibility="collapsed"
            )
        with col_l2:
            st.markdown(f"**Logo Secundária** — `{cfg.get('logo_secundaria','logo-secretaria.png')}`")
            st.caption("Geralmente o logo do parceiro/secretaria")
            upload_sec = st.file_uploader(
                "Substituir Logo Secundária", type=["png", "jpg", "jpeg"],
                key="up_logo_s", label_visibility="collapsed"
            )

        salvar = st.form_submit_button("💾 Salvar Identidade Visual", type="primary", use_container_width=True)

    if salvar:
        # Guardar logos se enviadas
        base_dir = os.path.dirname(os.path.dirname(__file__))

        nome_logo_p = cfg.get("logo_principal", "logo-imbra.png")
        if upload_principal is not None:
            ext = upload_principal.name.rsplit(".", 1)[-1].lower()
            nome_logo_p = f"logo-principal.{ext}"
            with open(os.path.join(base_dir, nome_logo_p), "wb") as f:
                f.write(upload_principal.read())

        nome_logo_s = cfg.get("logo_secundaria", "logo-secretaria.png")
        if upload_sec is not None:
            ext = upload_sec.name.rsplit(".", 1)[-1].lower()
            nome_logo_s = f"logo-secundaria.{ext}"
            with open(os.path.join(base_dir, nome_logo_s), "wb") as f:
                f.write(upload_sec.read())

        nova_cfg = {
            "titulo_projeto":    titulo.strip(),
            "subtitulo_projeto": subtitulo.strip(),
            "nome_organizacao":  nome_org.strip(),
            "cnpj":              cnpj.strip(),
            "endereco":          endereco.strip(),
            "telefone":          telefone.strip(),
            "email_contato":     email.strip(),
            "site":              site.strip(),
            "instagram":         instagram.strip(),
            "logo_principal":    nome_logo_p,
            "logo_secundaria":   nome_logo_s,
        }
        salvar_config(nova_cfg)
        st.success("✅ Identidade Visual actualizada! Todos os relatórios vão usar os novos dados.")
        st.rerun()

    # ── Ajuda ────────────────────────────────────────────────────────────────
    with st.expander("ℹ️ Quais relatórios são afectados?", expanded=False):
        st.markdown("""
Os seguintes documentos usam automaticamente esta configuração:

| Relatório | Cabeçalho | Rodapé |
|---|---|---|
| 🖨️ Ficha de Matrícula (PDF) | ✅ | ✅ |
| 📊 Planilha de Frequência (Excel) | ✅ | ✅ |
| 📋 Lista de Presença (PDF) | ✅ | ✅ |
| ⭐ Relatório de Satisfação (Word/PDF) | ✅ | ✅ |
| 🎂 Cartaz Aniversariantes (Word/PDF) | ✅ | — |
| 📄 Dossiê do Aluno | ✅ | ✅ |

> Após salvar, todos os documentos gerados a seguir já reflectem as alterações.
        """)
