# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_atestado.py
# 🏷️ VERSÃO: 1.0 — Controle de Atestado Médico / Bloqueio de Atividade
# ⚙️ FUNÇÃO: Lista alunos com atestado pendente e bloqueia participação.
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime

from database import get_alunos_com_atestado_bloqueado, get_ultima_presenca_batch
from utils.busca_aluno import busca_aluno_widget, filtrar_alunos_df


def renderizar_aba_atestado():
    st.markdown("""
        <div style='background:#FFF7ED;border-left:4px solid #F97316;
                    padding:12px 16px;border-radius:6px;margin-bottom:16px;'>
            <strong style='color:#9A3412;'>🏥 Controle de Atestado Médico</strong><br>
            <span style='color:#C2410C;font-size:13px;'>
                Alunos abaixo estão com <strong>participação bloqueada</strong> até apresentarem
                novo atestado médico. Eles não podem realizar atividades físicas até liberação.
            </span>
        </div>
    """, unsafe_allow_html=True)

    df_raw = get_alunos_com_atestado_bloqueado()

    if df_raw.empty:
        st.success("✅ Nenhum aluno com atestado médico pendente no momento.")
        return

    ids_tuple = tuple(str(i) for i in df_raw["id"].tolist())
    ult_pres_map = get_ultima_presenca_batch(ids_tuple)

    c_search, c_sort, c_pdf = st.columns([3, 1, 1], vertical_alignment="bottom")
    busca = busca_aluno_widget(
        "busca_atestado",
        container=c_search,
        placeholder="🔍 Filtrar (mín. 3 letras)...",
    )
    ordenacao = c_sort.selectbox("Ordenar:", ["A-Z", "Z-A"], key="atestado_sort")
    gerar_pdf = c_pdf.button("🖨️ Imprimir PDF", use_container_width=True,
                             type="primary", key="atestado_pdf")

    st.markdown("<hr style='margin:10px 0 18px 0;border-color:#FED7AA;'>", unsafe_allow_html=True)

    df_exibir = filtrar_alunos_df(df_raw.copy(), busca, cols=["nome"])
    df_exibir = df_exibir.sort_values("nome", ascending=(ordenacao == "A-Z")).reset_index(drop=True)

    total = len(df_exibir)
    st.caption(f"🏥 {total} aluno(s) com atestado médico pendente")

    if df_exibir.empty:
        st.warning("Nenhum aluno encontrado.")
        return

    st.markdown("""
    <style>
        .atestado-nome { font-size:15px;font-weight:900;color:#7C2D12;margin:0;
                         line-height:1.2;text-transform:uppercase; }
        .atestado-sub  { font-size:12px;color:#EA580C;margin:2px 0 0 0;font-weight:600; }
        .atestado-obs  { font-size:11px;color:#9A3412;background:#FFF7ED;border:1px solid #FED7AA;
                         border-radius:4px;padding:2px 8px;margin-top:4px;display:inline-block; }
        .atestado-pres { font-size:11px;color:#64748B;margin:2px 0 0 0; }
        .zoom-avatar-atestado {
            width:52px;height:52px;border-radius:50%;object-fit:cover;
            border:2px solid #F97316;box-shadow:0 2px 4px rgba(0,0,0,.1);
            transition:transform .3s ease;cursor:zoom-in;flex-shrink:0;
        }
        .zoom-avatar-atestado:hover { transform:scale(3.5);z-index:99999 !important; }
        .atestado-avatar-ph {
            width:52px;height:52px;border-radius:50%;background:#FFF7ED;color:#F97316;
            display:flex;align-items:center;justify-content:center;
            font-size:22px;border:2px dashed #FED7AA;flex-shrink:0;
        }
    </style>
    """, unsafe_allow_html=True)

    for _, row in df_exibir.iterrows():
        with st.container(border=True):
            c_img, c_info, c_ficha = st.columns([1.2, 5, 1.8], vertical_alignment="center")

            foto = row.get("foto_url", "")
            if foto and pd.notna(foto) and str(foto).strip() not in ["", "none", "nan", "null"]:
                c_img.markdown(f'<img src="{foto}" class="zoom-avatar-atestado">', unsafe_allow_html=True)
            else:
                inicial = str(row.get("nome", "?"))[0].upper()
                c_img.markdown(f'<div class="atestado-avatar-ph">{inicial}</div>', unsafe_allow_html=True)

            nome    = str(row.get("nome", "Sem Nome")).strip()
            turma   = str(row.get("turma", "")).strip()
            ult_p   = ult_pres_map.get(str(row.get("id", "")), "—")
            obs     = str(row.get("obs_atestado_bloqueio") or "").strip()

            idade_str = ""
            if pd.notna(row.get("data_nascimento")):
                try:
                    dt = pd.to_datetime(row["data_nascimento"])
                    hoje = datetime.date.today()
                    idade = hoje.year - dt.year - ((hoje.month, hoje.day) < (dt.month, dt.day))
                    idade_str = f" · {idade} anos"
                except Exception:
                    pass

            obs_html = (f"<br><span class='atestado-obs'>📋 {obs}</span>"
                        if obs else "")

            c_info.markdown(f"""
                <div style='line-height:1.4;'>
                    <p class='atestado-nome'>{nome}</p>
                    <p class='atestado-sub'>🚫 Bloqueado — Atestado Médico Pendente{idade_str}</p>
                    {obs_html}
                    <p class='atestado-pres'>📅 Turma: {turma or '—'} &nbsp;|&nbsp; Última presença: <b>{ult_p}</b></p>
                </div>
            """, unsafe_allow_html=True)

            with c_ficha:
                if st.button("👤 Cadastro", key=f"atestado_cad_{row['id']}",
                             use_container_width=True, type="primary"):
                    st.session_state.aluno_prontuario = row.to_dict()
                    st.session_state.origem_prontuario = "Frequência"
                    st.session_state.menu_atual = "Portal do Aluno"
                    st.rerun()

    if gerar_pdf:
        _gerar_pdf_atestado(df_exibir, ult_pres_map, total)


def _gerar_pdf_atestado(df: pd.DataFrame, ult_pres_map: dict, total: int):
    from gerador_pdf import criar_prestacao_diaria_pdf
    import base64
    hoje_fmt = datetime.date.today().strftime("%d/%m/%Y")

    linhas_html = ""
    for i, (_, row) in enumerate(df.iterrows(), 1):
        nome  = str(row.get("nome", "")).strip()
        turma = str(row.get("turma", "—")).strip()
        foto  = str(row.get("foto_url", "")).strip()
        ult_p = ult_pres_map.get(str(row.get("id", "")), "—")
        obs   = str(row.get("obs_atestado_bloqueio") or "—").strip()

        if foto and foto not in ["", "none", "nan", "null"]:
            foto_html = (f"<img src='{foto}' style='width:40px;height:40px;"
                         f"border-radius:50%;object-fit:cover;"
                         f"border:1.5px solid #F97316;'>")
        else:
            inicial   = nome[0].upper() if nome else "?"
            foto_html = (
                f"<div style='width:40px;height:40px;border-radius:50%;"
                f"background:#FFF7ED;color:#F97316;"
                f"display:flex;align-items:center;justify-content:center;"
                f"font-weight:900;font-size:16px;"
                f"border:1.5px dashed #FED7AA;'>{inicial}</div>"
            )

        bg = "#FFF7ED" if i % 2 == 0 else "#FFFFFF"
        linhas_html += f"""
        <tr style='background:{bg};'>
            <td style='padding:8px 6px;text-align:center;width:50px;'>{foto_html}</td>
            <td style='padding:8px 6px;font-weight:700;color:#7C2D12;font-size:13px;'>{nome}</td>
            <td style='padding:8px 6px;color:#4B5563;font-size:12px;'>{turma}</td>
            <td style='padding:8px 6px;color:#9A3412;font-size:11px;'>{obs}</td>
            <td style='padding:8px 6px;color:#4B5563;font-size:12px;text-align:center;'>{ult_p}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang='pt-BR'>
<head>
<meta charset='UTF-8'>
<title>Atestado Médico Pendente</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; color:#1E293B; padding:24px 32px; }}
  .header {{ display:flex; align-items:center; justify-content:space-between;
             border-bottom:3px solid #F97316; padding-bottom:12px; margin-bottom:20px; }}
  .header-title {{ font-size:18px; font-weight:900; color:#9A3412; }}
  .header-sub   {{ font-size:12px; color:#6B7280; margin-top:4px; }}
  .header-meta  {{ text-align:right; font-size:11px; color:#6B7280; }}
  .badge {{ display:inline-block; background:#FFF7ED; color:#C2410C;
            border:1px solid #FED7AA; padding:2px 10px; border-radius:4px;
            font-size:11px; font-weight:700; margin-bottom:14px; }}
  table {{ width:100%; border-collapse:collapse; }}
  thead tr {{ background:#FFF7ED; }}
  thead th {{ padding:9px 6px; text-align:left; font-size:11px; font-weight:800;
              color:#9A3412; border-bottom:2px solid #FED7AA; }}
  td {{ border-bottom:1px solid #FEF3C7; vertical-align:middle; }}
  .footer {{ margin-top:24px; font-size:10px; color:#9CA3AF; text-align:center;
             border-top:1px solid #E5E7EB; padding-top:10px; }}
</style>
</head>
<body>
<div class='header'>
  <div>
    <div class='header-title'>🏥 Atestado Médico Pendente — Bloqueio de Atividade</div>
    <div class='header-sub'>Alunos impedidos de realizar atividades físicas até liberação médica</div>
  </div>
  <div class='header-meta'>
    Emitido em: <b>{hoje_fmt}</b><br>
    Total: <b>{total} aluno(s)</b>
  </div>
</div>
<div class='badge'>🚫 {total} aluno(s) com participação bloqueada</div>
<table>
  <thead>
    <tr>
      <th style='text-align:center;'>Foto</th>
      <th>Nome do Aluno</th>
      <th>Turma</th>
      <th>Observação / Tipo de Atestado</th>
      <th style='text-align:center;'>Última Presença</th>
    </tr>
  </thead>
  <tbody>{linhas_html}</tbody>
</table>
<div class='footer'>
  Relatório gerado pelo Sistema IMBRA · {hoje_fmt} · Uso restrito à equipe administrativa
</div>
<script>window.onload = function(){{ window.print(); }}</script>
</body>
</html>"""

    b64 = base64.b64encode(html.encode("utf-8")).decode()
    js = f"""
    <script>
      var w = window.open('', '_blank');
      var html = atob('{b64}');
      w.document.open(); w.document.write(html); w.document.close();
    </script>"""
    st.html(js)
