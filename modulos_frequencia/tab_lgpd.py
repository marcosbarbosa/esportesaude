# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_lgpd.py
# 🏷️ VERSÃO: 1.0 (Relatório LGPD — Não Autorizam Uso de Imagem)
# ⚙️ FUNÇÃO: Listagem e impressão de alunos sem autorização de imagem.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime

from database import get_alunos_sem_autorizacao_imagem, get_ultima_presenca_batch
from utils.busca_aluno import busca_aluno_widget, filtrar_alunos_df


def renderizar_aba_lgpd():
    # ── Banner informativo ────────────────────────────────────────────────────
    st.markdown("""
        <div style='background:#EEF2FF;border-left:4px solid #6366F1;
                    padding:12px 16px;border-radius:6px;margin-bottom:16px;'>
            <strong style='color:#3730A3;'>🔒 LGPD — Direitos de Imagem</strong><br>
            <span style='color:#4338CA;font-size:13px;'>
                Alunos abaixo <strong>não autorizaram</strong> o uso de imagem e voz.
                Evite fotografias, vídeos ou divulgação em redes sociais envolvendo essas pessoas.
            </span>
        </div>
    """, unsafe_allow_html=True)

    # ── Carregamento de dados ─────────────────────────────────────────────────
    df_raw = get_alunos_sem_autorizacao_imagem()

    if df_raw.empty:
        st.success("✅ Todos os alunos ativos autorizaram o uso de imagem.")
        return

    # ── Última presença ───────────────────────────────────────────────────────
    ids_tuple = tuple(str(i) for i in df_raw["id"].tolist())
    ult_pres_map = get_ultima_presenca_batch(ids_tuple)

    # ── Controles ─────────────────────────────────────────────────────────────
    c_search, c_sort, c_pdf = st.columns([3, 1, 1], vertical_alignment="bottom")

    busca = busca_aluno_widget(
        "busca_lgpd",
        container=c_search,
        placeholder="🔍 Filtrar (mín. 3 letras)...",
    )
    ordenacao = c_sort.selectbox("Ordenar:", ["A-Z", "Z-A"], key="lgpd_sort")

    gerar_pdf = c_pdf.button("🖨️ Imprimir PDF", use_container_width=True, type="primary", key="lgpd_pdf")

    st.markdown("<hr style='margin:10px 0 18px 0;border-color:#E2E8F0;'>", unsafe_allow_html=True)

    # ── Filtragem ─────────────────────────────────────────────────────────────
    df_exibir = filtrar_alunos_df(df_raw.copy(), busca, cols=["nome"])
    df_exibir = df_exibir.sort_values("nome", ascending=(ordenacao == "A-Z")).reset_index(drop=True)

    total = len(df_exibir)
    st.caption(f"🔒 {total} aluno(s) sem autorização de imagem")

    if df_exibir.empty:
        st.warning("Nenhum aluno encontrado.")
        return

    # ── CSS dos cards ─────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .lgpd-nome { font-size:15px;font-weight:900;color:#1E1B4B;margin:0;line-height:1.2;text-transform:uppercase; }
        .lgpd-sub  { font-size:12px;color:#6366F1;margin:2px 0 0 0;font-weight:600; }
        .lgpd-pres { font-size:11px;color:#64748B;margin:2px 0 0 0; }
        .zoom-avatar-lgpd {
            width:52px;height:52px;border-radius:50%;object-fit:cover;
            border:2px solid #6366F1;box-shadow:0 2px 4px rgba(0,0,0,.1);
            transition:transform .3s ease;cursor:zoom-in;position:relative;z-index:10;flex-shrink:0;
        }
        .zoom-avatar-lgpd:hover { transform:scale(3.5);z-index:99999 !important;box-shadow:0 10px 20px rgba(0,0,0,.5); }
        .lgpd-avatar-ph {
            width:52px;height:52px;border-radius:50%;background:#EEF2FF;color:#6366F1;
            display:flex;align-items:center;justify-content:center;
            font-size:22px;border:2px dashed #A5B4FC;flex-shrink:0;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Cards ─────────────────────────────────────────────────────────────────
    for _, row in df_exibir.iterrows():
        with st.container(border=True):
            c_img, c_info, c_ficha = st.columns([1.2, 5, 1.8], vertical_alignment="center")

            # Foto
            foto = row.get("foto_url", "")
            if foto and pd.notna(foto) and str(foto).strip() not in ["", "none", "nan", "null"]:
                c_img.markdown(f'<img src="{foto}" class="zoom-avatar-lgpd">', unsafe_allow_html=True)
            else:
                inicial = str(row.get("nome", "?"))[0].upper()
                c_img.markdown(f'<div class="lgpd-avatar-ph">{inicial}</div>', unsafe_allow_html=True)

            # Info
            nome    = str(row.get("nome", "Sem Nome")).strip()
            turma   = str(row.get("turma", "")).strip()
            ult_p   = ult_pres_map.get(str(row.get("id", "")), "—")

            idade_str = ""
            if pd.notna(row.get("data_nascimento")):
                try:
                    dt = pd.to_datetime(row["data_nascimento"])
                    hoje = datetime.date.today()
                    idade = hoje.year - dt.year - ((hoje.month, hoje.day) < (dt.month, dt.day))
                    idade_str = f" · {idade} anos"
                except Exception:
                    pass

            c_info.markdown(f"""
                <div style='line-height:1.4;'>
                    <p class='lgpd-nome'>{nome}</p>
                    <p class='lgpd-sub'>🚫 Não autoriza imagem{idade_str}</p>
                    <p class='lgpd-pres'>📅 Turma: {turma or '—'} &nbsp;|&nbsp; Última presença: <b>{ult_p}</b></p>
                </div>
            """, unsafe_allow_html=True)

            # Botão cadastro
            with c_ficha:
                if st.button("👤 Cadastro", key=f"lgpd_cad_{row['id']}", use_container_width=True, type="primary"):
                    st.session_state.aluno_prontuario = row.to_dict()
                    st.session_state.origem_prontuario = "Frequência"
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.rerun()

    # ── Geração do PDF ────────────────────────────────────────────────────────
    if gerar_pdf:
        _gerar_pdf_lgpd(df_exibir, ult_pres_map, total)


def _gerar_pdf_lgpd(df: pd.DataFrame, ult_pres_map: dict, total: int):
    """Monta HTML completo e abre janela de impressão."""
    hoje_fmt = datetime.date.today().strftime("%d/%m/%Y")

    linhas_html = ""
    for i, (_, row) in enumerate(df.iterrows(), 1):
        nome  = str(row.get("nome", "")).strip()
        turma = str(row.get("turma", "—")).strip()
        foto  = str(row.get("foto_url", "")).strip()
        ult_p = ult_pres_map.get(str(row.get("id", "")), "—")

        if foto and foto not in ["", "none", "nan", "null"]:
            foto_html = f"<img src='{foto}' style='width:40px;height:40px;border-radius:50%;object-fit:cover;border:1.5px solid #6366F1;'>"
        else:
            inicial = nome[0].upper() if nome else "?"
            foto_html = (
                f"<div style='width:40px;height:40px;border-radius:50%;background:#EEF2FF;"
                f"color:#6366F1;display:flex;align-items:center;justify-content:center;"
                f"font-weight:900;font-size:16px;border:1.5px dashed #A5B4FC;'>{inicial}</div>"
            )

        bg = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        linhas_html += f"""
        <tr style='background:{bg};'>
            <td style='padding:8px 6px;text-align:center;width:50px;'>{foto_html}</td>
            <td style='padding:8px 6px;font-weight:700;color:#1E1B4B;font-size:13px;'>{nome}</td>
            <td style='padding:8px 6px;color:#4B5563;font-size:12px;'>{turma}</td>
            <td style='padding:8px 6px;color:#4B5563;font-size:12px;text-align:center;'>{ult_p}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang='pt-BR'>
<head>
<meta charset='UTF-8'>
<title>LGPD — Não Autorizam Imagem</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; color:#1E293B; padding:24px 32px; }}
  .header {{ display:flex; align-items:center; justify-content:space-between;
             border-bottom:3px solid #6366F1; padding-bottom:12px; margin-bottom:20px; }}
  .header-title {{ font-size:20px; font-weight:900; color:#3730A3; }}
  .header-sub   {{ font-size:12px; color:#6B7280; margin-top:4px; }}
  .header-meta  {{ text-align:right; font-size:11px; color:#6B7280; }}
  .badge {{ display:inline-block; background:#EEF2FF; color:#4338CA; border:1px solid #A5B4FC;
            padding:2px 10px; border-radius:4px; font-size:11px; font-weight:700;
            margin-bottom:14px; }}
  table {{ width:100%; border-collapse:collapse; }}
  thead tr {{ background:#EEF2FF; }}
  thead th {{ padding:9px 6px; text-align:left; font-size:11px; font-weight:800;
              color:#4338CA; border-bottom:2px solid #A5B4FC; }}
  tbody tr:hover {{ background:#F5F3FF; }}
  td {{ border-bottom:1px solid #E5E7EB; vertical-align:middle; }}
  .footer {{ margin-top:24px; font-size:10px; color:#9CA3AF; text-align:center;
             border-top:1px solid #E5E7EB; padding-top:10px; }}
  @media print {{
    body {{ padding:16px 20px; }}
    .no-print {{ display:none !important; }}
  }}
</style>
</head>
<body>
<div class='header'>
  <div>
    <div class='header-title'>🔒 LGPD — Não Autorizam Uso de Imagem</div>
    <div class='header-sub'>Instituto Muda Brasil · MoveRight Elite</div>
  </div>
  <div class='header-meta'>
    Emitido em: <b>{hoje_fmt}</b><br>
    Total: <b>{total} aluno(s)</b>
  </div>
</div>

<div class='badge'>🚫 {total} aluno(s) sem autorização de imagem e voz</div>

<table>
  <thead>
    <tr>
      <th style='text-align:center;'>Foto</th>
      <th>Nome do Aluno</th>
      <th>Turma</th>
      <th style='text-align:center;'>Última Presença</th>
    </tr>
  </thead>
  <tbody>
    {linhas_html}
  </tbody>
</table>

<div class='footer'>
  Relatório gerado pelo Sistema IMBRA · {hoje_fmt} ·
  Uso restrito à equipe administrativa — LGPD Art. 18
</div>

<script>window.onload = function(){{ window.print(); }}</script>
</body>
</html>"""

    import base64
    b64 = base64.b64encode(html.encode("utf-8")).decode()
    js = f"""
    <script>
      var w = window.open('', '_blank');
      var html = atob('{b64}');
      w.document.open();
      w.document.write(html);
      w.document.close();
    </script>
    """
    st.html(js)
