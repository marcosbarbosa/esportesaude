# ==============================================================================
# 📄 Arquivo: views/sem_avaliacao_view.py
# 🏷️ VERSÃO: 1.0 — Identificação de Alunos Sem Avaliação / Bloqueados
# ⚙️ FUNÇÃO: Listagem e PDF com cabeçalho prime de alunos nunca avaliados
#           e alunos bloqueados até (re)avaliação.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import io

from database import (
    get_alunos_sem_avaliacao,
    get_alunos_com_avaliacao_pendente,
    atualizar_avaliacao_pendente,
    get_ultima_presenca_batch,
    buscar_aluno_por_id,
)
from utils.busca_aluno import busca_aluno_widget, filtrar_alunos_df

try:
    from xhtml2pdf import pisa
    XHTML_DISPONIVEL = True
except ImportError:
    XHTML_DISPONIVEL = False


# ==============================================================================
# 🖼️ CABEÇALHO PRIME (logos + faixa institucional)
# ==============================================================================
def _html_cabecalho_prime() -> str:
    from utils.imagem import get_base64_image
    import os

    logo_muda = logo_sec = ""
    for nome, var in [
        ("assets/logo_muda.png", "logo_muda"),
        ("assets/logo_secretaria.png", "logo_sec"),
    ]:
        if os.path.exists(nome):
            b64 = get_base64_image(nome)
            if var == "logo_muda":
                logo_muda = b64
            else:
                logo_sec = b64

    img_muda = (
        f"<img src='data:image/png;base64,{logo_muda}' style='height:52px;'>"
        if logo_muda else ""
    )
    img_sec = (
        f"<img src='data:image/png;base64,{logo_sec}' style='height:52px;'>"
        if logo_sec else ""
    )

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:4px;">
      <tr>
        <td width="15%" style="vertical-align:middle;">{img_muda}</td>
        <td width="70%" style="text-align:center;vertical-align:middle;">
          <div style="font-size:13px;font-weight:900;color:#0A2540;letter-spacing:1px;
                      text-transform:uppercase;line-height:1.3;">
            Projeto Esporte e Saúde — MudaBrasil / MoveRight
          </div>
          <div style="font-size:10px;color:#475569;margin-top:2px;">
            Secretaria Municipal de Esportes e Lazer
          </div>
        </td>
        <td width="15%" style="text-align:right;vertical-align:middle;">{img_sec}</td>
      </tr>
    </table>
    <hr style="border:none;border-top:2px solid #1E88E5;margin:4px 0 8px 0;">
    """


# ==============================================================================
# 📄 GERADOR PDF PRIME — Alunos Sem Avaliação
# ==============================================================================
def _gerar_pdf_sem_avaliacao(
    df_nunca: pd.DataFrame,
    df_pendentes: pd.DataFrame,
    ult_pres_nunca: dict,
    ult_pres_pend: dict,
) -> bytes | None:
    if not XHTML_DISPONIVEL:
        return None

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    cabecalho = _html_cabecalho_prime()

    def _linhas_tabela(df: pd.DataFrame, ult_pres: dict, cor_linha: str) -> str:
        if df.empty:
            return "<tr><td colspan='4' style='text-align:center;color:#94A3B8;padding:10px;'>Nenhum registro</td></tr>"
        linhas = ""
        for _, r in df.iterrows():
            nome = str(r.get("nome", "")).strip()
            turma = str(r.get("turma") or "—").strip()
            up = ult_pres.get(str(r.get("id", "")))
            up_str = up.strftime("%d/%m/%Y") if up else "Sem registro"
            obs = str(r.get("obs_avaliacao_pendente") or "—").strip()
            linhas += f"""
            <tr style="background:{cor_linha};">
              <td style="padding:5px 8px;font-size:10px;font-weight:700;color:#0F172A;">{nome}</td>
              <td style="padding:5px 8px;font-size:10px;color:#475569;text-align:center;">{turma}</td>
              <td style="padding:5px 8px;font-size:10px;color:#475569;text-align:center;">{up_str}</td>
              <td style="padding:5px 8px;font-size:9px;color:#64748B;">{obs}</td>
            </tr>"""
        return linhas

    def _bloco(titulo: str, cor_titulo: str, cor_linha: str, df: pd.DataFrame, ult: dict, total: int) -> str:
        return f"""
        <div style="margin-bottom:18px;">
          <div style="background:{cor_titulo};padding:7px 14px;border-radius:4px;margin-bottom:6px;">
            <span style="font-size:12px;font-weight:900;color:white;">{titulo}</span>
            <span style="font-size:10px;color:rgba(255,255,255,0.85);margin-left:8px;">{total} aluno(s)</span>
          </div>
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border-collapse:collapse;border:1px solid #E2E8F0;">
            <tr style="background:#F8FAFC;">
              <th style="padding:5px 8px;font-size:10px;font-weight:800;color:#374151;border-bottom:1px solid #CBD5E1;text-align:left;">Nome</th>
              <th style="padding:5px 8px;font-size:10px;font-weight:800;color:#374151;border-bottom:1px solid #CBD5E1;text-align:center;">Turma</th>
              <th style="padding:5px 8px;font-size:10px;font-weight:800;color:#374151;border-bottom:1px solid #CBD5E1;text-align:center;">Última Presença</th>
              <th style="padding:5px 8px;font-size:10px;font-weight:800;color:#374151;border-bottom:1px solid #CBD5E1;text-align:left;">Observação</th>
            </tr>
            {_linhas_tabela(df, ult, cor_linha)}
          </table>
        </div>"""

    bloco_nunca = _bloco(
        "📋 Alunos que NUNCA foram avaliados",
        "#1E3A5F", "#FFFFFF", df_nunca, ult_pres_nunca, len(df_nunca)
    )
    bloco_pend = _bloco(
        "⚡ Alunos BLOQUEADOS — Aguardando (Re)avaliação",
        "#7C2D12", "#FFFBEB", df_pendentes, ult_pres_pend, len(df_pendentes)
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        @page {{ size: A4 portrait; margin: 14mm 12mm 12mm 12mm; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; color: #1E293B; }}
      </style>
    </head>
    <body>
      {cabecalho}
      <div style="text-align:center;margin-bottom:14px;">
        <div style="font-size:15px;font-weight:900;color:#0A2540;">
          🧪 Relatório de Avaliações Pendentes
        </div>
        <div style="font-size:10px;color:#64748B;margin-top:3px;">
          Gerado em {hoje} &nbsp;|&nbsp; Total sem avaliação: {len(df_nunca)} &nbsp;|&nbsp;
          Bloqueados: {len(df_pendentes)}
        </div>
      </div>
      {bloco_nunca}
      {bloco_pend}
      <div style="margin-top:16px;text-align:center;font-size:8px;color:#94A3B8;border-top:1px solid #E2E8F0;padding-top:6px;">
        Moveright™ Gestão Inteligente — Documento gerado automaticamente pelo sistema IMBRA
      </div>
    </body>
    </html>"""

    buf = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    return buf.getvalue() if not result.err else None


# ==============================================================================
# 🖥️ RENDERIZAÇÃO DA ABA — TELA PRINCIPAL
# ==============================================================================
def renderizar_aba_sem_avaliacao():
    st.markdown("""
        <div style='background:linear-gradient(135deg,#EFF6FF,#FEF3C7);
                    border-left:5px solid #1E3A5F;padding:14px 18px;
                    border-radius:8px;margin-bottom:16px;'>
            <strong style='color:#1E3A5F;font-size:15px;'>🧪 Avaliações Pendentes</strong><br>
            <span style='color:#334155;font-size:13px;'>
                Identifique alunos que <strong>nunca foram avaliados</strong> e alunos
                <strong>bloqueados</strong> até que sejam (re)avaliados.
                O SQL necessário:<br>
                <code style='background:#F1F5F9;padding:2px 6px;border-radius:3px;font-size:11px;'>
                ALTER TABLE alunos ADD COLUMN IF NOT EXISTS avaliacao_pendente boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS obs_avaliacao_pendente text;
                </code>
            </span>
        </div>
    """, unsafe_allow_html=True)

    df_nunca    = get_alunos_sem_avaliacao()
    df_pend     = get_alunos_com_avaliacao_pendente()

    ids_nunca   = tuple(str(i) for i in df_nunca["id"].tolist()) if not df_nunca.empty else ()
    ids_pend    = tuple(str(i) for i in df_pend["id"].tolist()) if not df_pend.empty else ()
    ult_nunca   = get_ultima_presenca_batch(ids_nunca) if ids_nunca else {}
    ult_pend    = get_ultima_presenca_batch(ids_pend) if ids_pend else {}

    # ── Barra de ação ──────────────────────────────────────────────────────────
    c_busca, c_sort, c_pdf = st.columns([3, 1, 1.2], vertical_alignment="bottom")
    busca = busca_aluno_widget("busca_sem_av", container=c_busca,
                               placeholder="🔍 Filtrar por nome…")
    sort_op = c_sort.selectbox("Ordenar:", ["A-Z", "Z-A"], key="sem_av_sort")
    gerar_pdf = c_pdf.button("🖨️ Exportar PDF Prime", use_container_width=True,
                             type="primary", key="sem_av_pdf_btn")

    if gerar_pdf:
        with st.spinner("Gerando PDF…"):
            pdf_bytes = _gerar_pdf_sem_avaliacao(df_nunca, df_pend, ult_nunca, ult_pend)
        if pdf_bytes:
            st.download_button(
                "📥 Baixar PDF — Avaliações Pendentes",
                pdf_bytes,
                f"avaliacoes_pendentes_{datetime.date.today()}.pdf",
                "application/pdf",
                use_container_width=True,
            )
        else:
            st.error("Erro ao gerar PDF. Verifique se xhtml2pdf está instalado.")

    st.markdown("<hr style='margin:10px 0 18px 0;border-color:#CBD5E1;'>",
                unsafe_allow_html=True)

    tab_nunca, tab_bloq = st.tabs([
        f"📋 Nunca Avaliados ({len(df_nunca)})",
        f"⚡ Bloqueados p/ Reavaliação ({len(df_pend)})",
    ])

    # ===========================================================================
    # ABA 1 — NUNCA AVALIADOS
    # ===========================================================================
    with tab_nunca:
        _renderizar_secao_nunca_avaliados(df_nunca, ult_nunca, busca, sort_op)

    # ===========================================================================
    # ABA 2 — BLOQUEADOS
    # ===========================================================================
    with tab_bloq:
        _renderizar_secao_bloqueados(df_pend, ult_pend, busca, sort_op)


def _renderizar_secao_nunca_avaliados(df_raw, ult_pres, busca, sort_op):
    if df_raw.empty:
        st.success("✅ Todos os alunos ativos já foram avaliados ao menos uma vez!")
        return

    df = filtrar_alunos_df(df_raw.copy(), busca, cols=["nome"])
    df = df.sort_values("nome", ascending=(sort_op == "A-Z")).reset_index(drop=True)
    st.caption(f"📋 {len(df)} aluno(s) sem nenhuma avaliação registrada")

    if df.empty:
        st.warning("Nenhum aluno encontrado.")
        return

    st.markdown(_css_cards_aval(), unsafe_allow_html=True)

    for _, row in df.iterrows():
        _card_aluno(row, ult_pres, bloqueado=bool(row.get("avaliacao_pendente")),
                    modo="nunca", obs=str(row.get("obs_avaliacao_pendente") or ""))


def _renderizar_secao_bloqueados(df_raw, ult_pres, busca, sort_op):
    if df_raw.empty:
        st.success("✅ Nenhum aluno bloqueado por reavaliação pendente.")
        return

    df = filtrar_alunos_df(df_raw.copy(), busca, cols=["nome"])
    df = df.sort_values("nome", ascending=(sort_op == "A-Z")).reset_index(drop=True)
    st.caption(f"⚡ {len(df)} aluno(s) bloqueado(s) aguardando reavaliação")

    if df.empty:
        st.warning("Nenhum aluno encontrado.")
        return

    st.markdown(_css_cards_aval(), unsafe_allow_html=True)

    for _, row in df.iterrows():
        _card_aluno(row, ult_pres, bloqueado=True, modo="bloqueado",
                    obs=str(row.get("obs_avaliacao_pendente") or ""))


def _css_cards_aval() -> str:
    return """
    <style>
        .aval-nome  { font-size:15px;font-weight:900;color:#0F172A;margin:0;line-height:1.2; }
        .aval-sub   { font-size:12px;color:#64748B;margin:2px 0 0 0; }
        .aval-obs   { font-size:11px;color:#92400E;background:#FEF3C7;border:1px solid #FCD34D;
                      border-radius:4px;padding:2px 8px;margin-top:4px;display:inline-block; }
        .aval-badge { font-size:10px;font-weight:800;padding:2px 8px;border-radius:4px;
                      display:inline-block;margin-top:4px; }
        .badge-nunca  { background:#EFF6FF;color:#1D4ED8;border:1px solid #BFDBFE; }
        .badge-bloq   { background:#FEF3C7;color:#92400E;border:1px solid #FCD34D; }
        .zoom-avatar-aval {
            width:52px;height:52px;border-radius:50%;object-fit:cover;
            border:2px solid #CBD5E1;box-shadow:0 2px 4px rgba(0,0,0,.1);
            transition:transform .3s ease;cursor:zoom-in;flex-shrink:0;
        }
        .zoom-avatar-aval:hover { transform:scale(3.5);z-index:99999 !important; }
        .aval-avatar-ph {
            width:52px;height:52px;border-radius:50%;background:#EFF6FF;color:#1D4ED8;
            display:flex;align-items:center;justify-content:center;
            font-size:22px;border:2px dashed #BFDBFE;flex-shrink:0;
        }
    </style>"""


def _card_aluno(row, ult_pres: dict, bloqueado: bool, modo: str, obs: str):
    aluno_id = str(row.get("id", ""))
    nome = str(row.get("nome", "")).strip()
    turma = str(row.get("turma") or "—").strip()
    foto_url = str(row.get("foto_url") or "").strip()
    inic = "".join(p[0].upper() for p in nome.split()[:2] if p)
    up = ult_pres.get(aluno_id)
    up_str = str(up) if up else "Sem registro"
    badge_html = (
        "<span class='aval-badge badge-bloq'>⚡ Bloqueado — Reavaliação Pendente</span>"
        if bloqueado else
        "<span class='aval-badge badge-nunca'>📋 Nunca Avaliado</span>"
    )

    with st.container(border=True):
        c_foto, c_info, c_btn = st.columns([0.6, 5, 1.5], vertical_alignment="center")
        with c_foto:
            if foto_url.startswith("http"):
                st.markdown(
                    f"<img class='zoom-avatar-aval' src='{foto_url}' alt='{inic}' "
                    f"onerror=\"this.outerHTML='<div class=aval-avatar-ph>👤</div>'\">",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='aval-avatar-ph'><span style='font-size:16px;font-weight:900;"
                    f"color:#1D4ED8;'>{inic}</span></div>",
                    unsafe_allow_html=True,
                )
        with c_info:
            obs_linha = f"<div class='aval-obs'>📝 {obs}</div>" if obs and obs != "—" else ""
            st.markdown(
                f"<p class='aval-nome'>{nome}</p>"
                f"<p class='aval-sub'>🏋️ {turma} &nbsp;|&nbsp; ⏱ Última pres.: {up_str}</p>"
                f"{badge_html}"
                f"{obs_linha}",
                unsafe_allow_html=True,
            )
        with c_btn:
            col_av, col_bl = st.columns(2)
            # Botão abrir prontuário
            if col_av.button("🩺", key=f"av_open_{aluno_id}",
                             use_container_width=True, help="Abrir Prontuário"):
                fresh = buscar_aluno_por_id(aluno_id)
                if fresh:
                    st.session_state.aluno_prontuario = fresh
                    st.session_state.origem_prontuario = "Relatórios"
                    st.session_state.prontuario_aba = "Nova Medição"
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.rerun()

            # Botão toggle bloqueio
            if bloqueado:
                if col_bl.button("✅", key=f"av_lib_{aluno_id}",
                                 use_container_width=True,
                                 help="Liberar — avaliação realizada"):
                    op = st.session_state.get("usuario_nome", "")
                    ok, msg = atualizar_avaliacao_pendente(aluno_id, False, "", op, nome)
                    if ok:
                        st.toast(f"✅ {nome.split()[0]} liberado(a).", icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                if col_bl.button("⚡", key=f"av_bloq_{aluno_id}",
                                 use_container_width=True,
                                 help="Bloquear até reavaliação"):
                    st.session_state[f"_aval_bloquear_{aluno_id}"] = True

        # Formulário de bloqueio inline
        if st.session_state.get(f"_aval_bloquear_{aluno_id}"):
            with st.form(f"form_av_{aluno_id}", clear_on_submit=True):
                obs_inp = st.text_input(
                    "Motivo do bloqueio (opcional):",
                    placeholder="Ex: Precisa avaliação inicial, reavaliação semestral…",
                    key=f"av_obs_{aluno_id}",
                )
                c_ok, c_cancel = st.columns(2)
                if c_ok.form_submit_button("⚡ Confirmar Bloqueio", type="primary",
                                           use_container_width=True):
                    op = st.session_state.get("usuario_nome", "")
                    ok, msg = atualizar_avaliacao_pendente(aluno_id, True, obs_inp, op, nome)
                    if ok:
                        del st.session_state[f"_aval_bloquear_{aluno_id}"]
                        st.toast(f"⚡ {nome.split()[0]} bloqueado(a).", icon="⚡")
                        st.rerun()
                    else:
                        st.error(msg)
                if c_cancel.form_submit_button("Cancelar", use_container_width=True):
                    del st.session_state[f"_aval_bloquear_{aluno_id}"]
                    st.rerun()
