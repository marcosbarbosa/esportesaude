# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_emergencia.py
# 🏷️ VERSÃO: 3.0 — Busca Global + Grau de Parentesco + PDF Prime
# ⚙️ FUNÇÃO: Listagem rápida, acionamento de contatos e atalho para Ficha Digital.
#            Busca cross-turma: quando o usuário digita, encontra qualquer aluno.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import re
import io
from utils.texto import formatar_whatsapp_link as limpar_whatsapp_emergencia, formatar_whatsapp_numero as _wa_num_em
from utils.busca_aluno import busca_aluno_widget, filtrar_alunos_df

try:
    from xhtml2pdf import pisa
    XHTML_DISPONIVEL = True
except ImportError:
    XHTML_DISPONIVEL = False


def _extrair_hashtag(texto: str, tag: str) -> str:
    """Extrai conteúdo de uma seção #Tag: dentro de problemas_saude."""
    if not texto:
        return ""
    m = re.search(
        rf"#{re.escape(tag)}:\s*(.+?)(?=\n\n#|\Z)",
        texto, re.IGNORECASE | re.DOTALL
    )
    return m.group(1).strip() if m else ""


# ==============================================================================
# 🖨️ PDF PRIME — Ficha de Emergência
# ==============================================================================
def _gerar_pdf_emergencia(df: pd.DataFrame, turma: str) -> bytes | None:
    if not XHTML_DISPONIVEL or df.empty:
        return None

    from utils.imagem import get_base64_image
    import os

    logo_muda = logo_sec = ""
    for nome_arq, var in [("assets/logo_muda.png", "logo_muda"), ("assets/logo_secretaria.png", "logo_sec")]:
        if os.path.exists(nome_arq):
            b64 = get_base64_image(nome_arq)
            if var == "logo_muda":
                logo_muda = b64
            else:
                logo_sec = b64

    img_m = f"<img src='data:image/png;base64,{logo_muda}' style='height:48px;'>" if logo_muda else ""
    img_s = f"<img src='data:image/png;base64,{logo_sec}' style='height:48px;'>" if logo_sec else ""

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    linhas = ""
    for _, r in df.iterrows():
        nome = str(r.get("nome", "")).strip()
        contato = str(r.get("contato_emergencia") or "—").strip()
        parentesco = str(r.get("grau_parentesco") or "—").strip()
        ps_text = str(r.get("problemas_saude") or "")
        alergia = _extrair_hashtag(ps_text, "Alergias") or "—"
        saude   = ps_text[:100] if ps_text else "—"
        idade_str = "—"
        if pd.notna(r.get("data_nascimento")):
            try:
                dt = pd.to_datetime(r["data_nascimento"])
                h = datetime.date.today()
                idade_str = f"{h.year - dt.year - ((h.month, h.day) < (dt.month, dt.day))} anos"
            except Exception:
                pass
        cor = "#FFFFFF" if int(r.name) % 2 == 0 else "#F8FAFC"
        linhas += f"""
        <tr style='background:{cor};'>
          <td style='padding:5px 7px;font-size:10px;font-weight:700;color:#0F172A;'>{nome}</td>
          <td style='padding:5px 7px;font-size:10px;color:#475569;text-align:center;'>{idade_str}</td>
          <td style='padding:5px 7px;font-size:10px;color:#DC2626;font-weight:700;'>{contato}</td>
          <td style='padding:5px 7px;font-size:10px;color:#374151;text-align:center;'>{parentesco}</td>
          <td style='padding:5px 7px;font-size:9px;color:#B45309;'>{alergia[:50]}</td>
          <td style='padding:5px 7px;font-size:9px;color:#6B7280;'>{saude[:50]}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
    <style>
        @page {{ size: A4 landscape; margin: 10mm 12mm; }}
        body {{ font-family: Arial, sans-serif; color: #1E293B; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th {{ font-size: 9px; font-weight: 900; color: white; background:#1E3A5F;
              padding: 5px 7px; text-align: left; }}
    </style></head><body>
    <table style='margin-bottom:6px;'>
      <tr>
        <td width='12%' style='vertical-align:middle;'>{img_m}</td>
        <td width='76%' style='text-align:center;vertical-align:middle;'>
          <div style='font-size:12px;font-weight:900;color:#0A2540;text-transform:uppercase;'>
            Ficha de Emergência — {turma or "Todos os Alunos"}
          </div>
          <div style='font-size:9px;color:#64748B;'>Projeto Esporte e Saúde · MudaBrasil / MoveRight · Gerado em {hoje}</div>
        </td>
        <td width='12%' style='text-align:right;vertical-align:middle;'>{img_s}</td>
      </tr>
    </table>
    <hr style='border:none;border-top:2px solid #EF4444;margin:4px 0 8px 0;'>
    <div style='background:#FEF2F2;border-left:3px solid #EF4444;padding:4px 10px;
                border-radius:3px;margin-bottom:8px;font-size:9px;color:#991B1B;font-weight:700;'>
        ⚠️ DOCUMENTO DE USO RESTRITO — APENAS PARA EMERGÊNCIAS. Total de alunos: {len(df)}
    </div>
    <table>
      <tr>
        <th>Nome do Aluno</th><th>Idade</th><th>Contato de Emergência</th>
        <th>Parentesco</th><th>Alergias</th><th>Condições de Saúde</th>
      </tr>
      {linhas}
    </table>
    <div style='margin-top:12px;text-align:center;font-size:7px;color:#94A3B8;border-top:1px solid #E2E8F0;padding-top:4px;'>
        Moveright™ Gestão Inteligente — Documento CONFIDENCIAL gerado automaticamente pelo sistema IMBRA
    </div>
    </body></html>"""

    buf = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    return buf.getvalue() if not result.err else None


# ==============================================================================
# 🖥️ RENDERIZAÇÃO PRINCIPAL
# ==============================================================================
def renderizar_aba_emergencia(df_alunos_tab, turma_selecionada):
    if df_alunos_tab is None:
        df_alunos_tab = pd.DataFrame()

    st.markdown("""
        <div style='background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px;'>
            <strong style='color: #991B1B;'>⚠️ USO RESTRITO DE EMERGÊNCIA:</strong><br>
            <span style='color: #B91C1C; font-size: 13px;'>Em caso de incidente grave, consulte os dados clínicos abaixo e clique em <strong>'🚨 Acionar'</strong> para abrir diretamente o WhatsApp ou a linha telefónica do responsável.</span>
        </div>
    """, unsafe_allow_html=True)

    c_search, c_sort, c_export = st.columns([3, 1, 1], vertical_alignment="bottom")
    busca = busca_aluno_widget(
        "busca_emergencia",
        container=c_search,
        placeholder="🔍 Buscar qualquer aluno (mín. 3 letras)...",
    )
    ordenacao = c_sort.selectbox("Ordenar:", ["A-Z", "Z-A"], key="em_sort")

    # ── Busca Global Cross-Turma ───────────────────────────────────────────────
    # Quando o usuário digita, pesquisamos em TODOS os alunos ativos,
    # não apenas na turma selecionada — igual ao comportamento das outras telas.
    busca_ativa = busca and len(busca.strip()) >= 3
    if busca_ativa:
        try:
            from database import buscar_alunos_geral
            df_todos = buscar_alunos_geral("")
            if not df_todos.empty:
                df_base = df_todos[df_todos["status"] != "Inativo"].copy()
            else:
                df_base = df_alunos_tab.copy()
        except Exception:
            df_base = df_alunos_tab.copy()
        df_exibir = filtrar_alunos_df(df_base, busca, cols=["nome"])
        st.caption(f"🌍 Busca em toda a base — {len(df_exibir)} aluno(s) encontrado(s)")
    else:
        df_exibir = df_alunos_tab.copy() if not df_alunos_tab.empty else pd.DataFrame()

    if not df_exibir.empty and "nome" in df_exibir.columns:
        df_exibir = df_exibir.sort_values("nome", ascending=(ordenacao != "Z-A"))

    # ── PDF ──────────────────────────────────────────────────────────────────
    if c_export.button("🖨️ Exportar PDF", use_container_width=True, type="primary", key="em_pdf_btn"):
        with st.spinner("Gerando Ficha de Emergência…"):
            pdf_bytes = _gerar_pdf_emergencia(df_exibir, turma_selecionada)
        if pdf_bytes:
            st.download_button(
                "📥 Baixar Ficha de Emergência (PDF)",
                pdf_bytes,
                f"emergencia_{turma_selecionada.replace(' ','_')}_{datetime.date.today()}.pdf",
                "application/pdf",
                use_container_width=True,
            )
        else:
            st.error("Erro ao gerar PDF.")

    st.markdown("<hr style='margin: 10px 0px 20px 0px; border-color: #E2E8F0;'>", unsafe_allow_html=True)

    if df_exibir.empty:
        if busca_ativa:
            st.warning("Nenhum aluno encontrado com este nome em toda a base.")
        else:
            st.warning("Selecione uma turma para carregar os alunos.")
        return

    # ── CSS ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .em-nome { font-size: 16px; font-weight: 900; color: #0F172A; margin: 0; line-height: 1.2; text-transform: uppercase; }
        .em-idade { font-size: 12.5px; color: #64748B; margin: 0 0 4px 0; font-weight: 600; }
        .em-parentesco { font-size: 11px; color: #1D4ED8; background:#EFF6FF; border:1px solid #BFDBFE;
                         padding: 2px 8px; border-radius: 4px; display:inline-block; margin-bottom:3px; font-weight:700; }
        .em-badge-alergia { background-color: #FEF2F2; color: #DC2626; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800; display: inline-block; border: 1px solid #FCA5A5; margin-bottom: 3px; }
        .em-badge-saude { background-color: #FFFBEB; color: #D97706; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800; display: inline-block; border: 1px solid #FCD34D; margin-bottom: 3px; }
        .em-badge-vazio { background-color: #F8FAFC; color: #94A3B8; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; border: 1px dashed #CBD5E1; }
        .em-turma-badge { font-size: 10px; background:#DBEAFE; color:#1E40AF; padding:1px 6px; border-radius:3px; font-weight:700; }
        .zoom-avatar-em { width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid #EF4444; box-shadow: 0px 2px 4px rgba(0,0,0,0.1); transition: transform 0.3s ease; cursor: zoom-in; position: relative; z-index: 10; flex-shrink: 0; }
        .zoom-avatar-em:hover { transform: scale(3.5); z-index: 99999 !important; box-shadow: 0px 10px 20px rgba(0,0,0,0.5); }
        .em-avatar-placeholder { width: 55px; height: 55px; border-radius: 50%; background-color: #F1F5F9; color: #94A3B8; display: flex; align-items: center; justify-content: center; font-size: 24px; border: 2px dashed #CBD5E1; flex-shrink: 0; }
    </style>
    """, unsafe_allow_html=True)

    for _, row in df_exibir.iterrows():
        with st.container(border=True):
            c_img, c_info, c_acao, c_ficha = st.columns([1.2, 4.5, 1.8, 1.5], vertical_alignment="center")

            # Avatar
            foto = str(row.get("foto_url") or "").strip()
            if foto.startswith("http"):
                c_img.markdown(f'<img src="{foto}" class="zoom-avatar-em">', unsafe_allow_html=True)
            else:
                c_img.markdown('<div class="em-avatar-placeholder">👤</div>', unsafe_allow_html=True)

            # Dados
            nome = str(row.get("nome", "Sem Nome")).strip()
            contato_str = str(row.get("contato_emergencia", "")).strip()
            parentesco_str = str(row.get("grau_parentesco") or "").strip()
            turma_str = str(row.get("turma") or "").strip()

            # Idade
            idade_str = "Idade N/I"
            if pd.notna(row.get("data_nascimento")):
                try:
                    dt_nasc = pd.to_datetime(row["data_nascimento"])
                    hoje = datetime.date.today()
                    idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
                    idade_str = f"{idade} anos"
                except Exception:
                    pass

            # Contato
            if pd.isna(contato_str) or contato_str in ["", "nan", "não informado", "none"]:
                contato_html = "<span style='color:#94A3B8;'>Sem Contato</span>"
            else:
                contato_html = f"<span style='color:#EF4444;font-weight:800;'>📞 {contato_str}</span>"

            # Parentesco
            parentesco_html = (
                f"<span class='em-parentesco'>👥 {parentesco_str}</span>"
                if parentesco_str and parentesco_str.lower() not in ["nan", "none", "—"]
                else "<span style='color:#CBD5E1;font-size:11px;'>Parentesco não informado</span>"
            )

            # Turma badge (útil na busca global que mistura turmas)
            turma_html = (
                f"&nbsp;<span class='em-turma-badge'>{turma_str}</span>"
                if busca_ativa and turma_str else ""
            )

            # Badges clínicos
            _ps_txt     = str(row.get("problemas_saude") or "")
            alergia_str = _extrair_hashtag(_ps_txt, "Alergias")
            alergia_html = (
                f"<div class='em-badge-alergia'>⚠️ Alergia: {alergia_str[:40]}</div><br>"
                if alergia_str and alergia_str.lower() not in ["nan", "none", "não", ""] else ""
            )
            saude_str = str(row.get("problemas_saude", "")).strip()
            saude_html = (
                f"<div class='em-badge-saude'>🏥 Saúde: {saude_str[:45]}</div><br>"
                if saude_str and saude_str.lower() not in ["nan", "none", "não", ""] else ""
            )
            tags_html = f"{alergia_html}{saude_html}" if (alergia_html or saude_html) else "<div class='em-badge-vazio'>Sem restrições clínicas reportadas.</div>"

            c_info.markdown(f"""
                <div style="line-height: 1.4;">
                    <p class="em-nome">{nome}{turma_html}</p>
                    <p class="em-idade">{idade_str} &nbsp;•&nbsp; {contato_html}</p>
                    {parentesco_html}<br>
                    {tags_html}
                </div>
            """, unsafe_allow_html=True)

            # Botões de acionamento
            with c_acao:
                if pd.isna(contato_str) or contato_str in ["", "nan", "não informado", "none"]:
                    st.button("🚨 Acionar", disabled=True, key=f"em_dis_{row['id']}", use_container_width=True)
                else:
                    num_wa = _wa_num_em(contato_str)
                    if num_wa:
                        import urllib.parse as _up
                        _msg_wa = (
                            f"Olá, somos do Muda Brasil. Estamos em atendimento e precisamos "
                            f"confirmar uma informação sobre {nome}. "
                            f"Pode nos responder assim que visualizar?"
                        )
                        link_w = f"https://wa.me/{num_wa}?text={_up.quote(_msg_wa)}"
                        st.link_button("🚨 WhatsApp", link_w, use_container_width=True)
                    else:
                        numero_limpo = re.sub(r"\D", "", contato_str)
                        if numero_limpo:
                            st.link_button("🚨 Ligar Agora", f"tel:{numero_limpo}", use_container_width=True)
                        else:
                            st.button("🚨 Acionar", disabled=True, key=f"em_nd_{row['id']}", use_container_width=True)

            # Botão ficha
            with c_ficha:
                if st.button("🩺 Ver Ficha", key=f"em_f_{row['id']}", use_container_width=True, type="primary"):
                    st.session_state.aluno_prontuario = row.to_dict()
                    st.session_state.origem_prontuario = "Frequência"
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.rerun()
