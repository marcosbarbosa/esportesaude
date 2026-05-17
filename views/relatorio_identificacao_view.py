# ==============================================================================
# 📄 Arquivo: views/relatorio_identificacao_view.py
# 🏷️ VERSÃO: 1.2 (Ordenação clicável no grid + PDF segue última ordenação)
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import io
import base64
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import buscar_alunos_geral, get_todas_turmas
from utils.identidade import render_cabecalho_html, render_rodape_html, get_config as _get_id_cfg

try:
    from xhtml2pdf import pisa
    XHTML_DISPONIVEL = True
except ImportError:
    XHTML_DISPONIVEL = False


def _url_para_base64(url, timeout=4):
    """Baixa uma imagem e retorna data URI base64, ou None se falhar."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
            b64 = base64.b64encode(r.content).decode("utf-8")
            return f"data:{mime};base64,{b64}"
    except Exception:
        pass
    return None


def _prefetch_fotos(df, max_workers=12):
    """
    Retorna dict {url: data_uri} para todas as fotos do DataFrame.
    Usa ThreadPoolExecutor para downloads paralelos.
    """
    urls = [
        str(u) for u in df["url_foto"].dropna().unique()
        if str(u).strip() and str(u) != "nan"
    ]
    resultado = {}
    if not urls:
        return resultado
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(_url_para_base64, u): u for u in urls}
        for fut in as_completed(fut_map):
            url = fut_map[fut]
            data_uri = fut.result()
            if data_uri:
                resultado[url] = data_uri
    return resultado


_JS_SORT = """
<script>
(function () {
  var _dir = {};   // colIdx -> 'asc'|'desc'

  function updateArrows(ths, activeIdx, asc) {
    ths.forEach(function (th, i) {
      var txt = th.textContent.replace(/ [▲▼]$/, '').trimEnd();
      th.textContent = txt + (i === activeIdx ? (asc ? ' ▲' : ' ▼') : '');
    });
  }

  function sortTable(idx) {
    var table  = document.getElementById('cc-table');
    var tbody  = table.querySelector('tbody');
    var ths    = Array.from(table.querySelectorAll('thead th'));
    var rows   = Array.from(tbody.querySelectorAll('tr'));

    var asc = (_dir[idx] !== 'asc');
    _dir[idx] = asc ? 'asc' : 'desc';

    rows.sort(function (a, b) {
      var av = (a.cells[idx] ? a.cells[idx].textContent.trim() : '');
      var bv = (b.cells[idx] ? b.cells[idx].textContent.trim() : '');
      // Tenta comparação numérica/data primeiro
      var an = parseFloat(av.replace(/[^0-9.]/g, ''));
      var bn = parseFloat(bv.replace(/[^0-9.]/g, ''));
      if (!isNaN(an) && !isNaN(bn)) {
        return asc ? an - bn : bn - an;
      }
      return asc ? av.localeCompare(bv, 'pt-BR') : bv.localeCompare(av, 'pt-BR');
    });
    rows.forEach(function (r) { tbody.appendChild(r); });
    updateArrows(ths, idx, asc);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var ths = document.querySelectorAll('#cc-table thead th');
    ths.forEach(function (th, idx) {
      th.style.cursor = 'pointer';
      th.title = 'Clique para ordenar';
      th.addEventListener('click', function () { sortTable(idx); });
    });
  });
})();
</script>
"""


def _css_base(page_size):
    return f"""
        @page {{ size: {page_size}; margin: 1cm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11px; color: #1E293B; }}
        h2 {{ text-align: center; color: #0F172A; margin-bottom: 5px;
              text-transform: uppercase; font-size: 18px; }}
        p {{ text-align: center; color: #64748B; margin-top: 0;
             margin-bottom: 20px; font-size: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #CBD5E1; padding: 8px; vertical-align: middle; }}
        th {{ background-color: #0F172A; color: white; font-weight: bold;
              font-size: 10px; user-select: none; }}
        th:hover {{ background-color: #1E3A5F; }}
        tr:nth-child(even) {{ background-color: #F8FAFC; }}
        .footer {{ text-align: center; font-size: 8px; color: #94A3B8; margin-top: 20px; }}
    """


def _css_pdf(page_size):
    return f"""
        @page {{ size: {page_size}; margin: 1cm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11px; color: #1E293B; }}
        h2 {{ text-align: center; color: #0F172A; margin-bottom: 5px;
              text-transform: uppercase; font-size: 18px; }}
        p {{ text-align: center; color: #64748B; margin-top: 0; margin-bottom: 20px; font-size: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #CBD5E1; padding: 8px; vertical-align: middle; }}
        th {{ background-color: #0F172A; color: white; font-weight: bold; font-size: 10px; }}
        tr:nth-child(even) {{ background-color: #F8FAFC; }}
        .footer {{ text-align: center; font-size: 8px; color: #94A3B8; margin-top: 20px; }}
    """


def _formatar_valor(row, c):
    val = str(row.get(c, ""))
    if val in ("nan", "None", ""):
        return "-"
    if c == "data_nascimento":
        try:
            return pd.to_datetime(val).strftime("%d/%m/%Y")
        except Exception:
            pass
    return val


def _cabecalhos_html(campos_sel, opcoes_campos):
    th = ("<th style='width:60px;text-align:center;'>FOTO</th>"
          "<th>NOME DO ALUNO</th><th>TURMA</th>")
    for c in campos_sel:
        th += f"<th>{opcoes_campos[c].upper()}</th>"
    return th


_FOTO_SIZE = 68   # 1.5× de 45 px


def _linhas_html(df, campos_sel, opcoes_campos, fotos_b64=None):
    """
    fotos_b64: dict {url: data_uri} para PDF.
                None = usa URLs externas (preview no browser).
    """
    sz  = _FOTO_SIZE
    tr = ""
    for _, row in df.iterrows():
        foto_url = str(row.get("url_foto") or "").strip()
        tem_foto = bool(foto_url and foto_url not in ("nan", "None"))

        if fotos_b64 is not None:
            # Modo PDF: usa base64 quando disponível
            data_uri = fotos_b64.get(foto_url) if tem_foto else None
            if data_uri:
                foto_cell = (
                    f"<img src='{data_uri}' "
                    f"style='width:{sz}px;height:{sz}px;border-radius:50%;object-fit:cover;'>"
                )
            else:
                foto_cell = (
                    f"<div style='width:{sz}px;height:{sz}px;background:#E2E8F0;"
                    f"text-align:center;line-height:{sz}px;border-radius:50%;"
                    "font-size:8px;color:#64748B;margin:0 auto;'>Sem Foto</div>"
                )
        else:
            # Modo preview: usa URL externa diretamente
            if tem_foto:
                foto_cell = (
                    f"<img src='{foto_url}' style='width:{sz}px;height:{sz}px;"
                    "border-radius:50%;object-fit:cover;'>"
                )
            else:
                foto_cell = (
                    f"<div style='width:{sz}px;height:{sz}px;background:#E2E8F0;"
                    f"text-align:center;line-height:{sz}px;border-radius:50%;"
                    "font-size:9px;color:#64748B;margin:0 auto;'>Sem Foto</div>"
                )

        nome  = str(row.get("nome", "")).upper()
        turma = str(row.get("turma", ""))
        tds = (f"<td style='text-align:center;'>{foto_cell}</td>"
               f"<td><b>{nome}</b></td><td>{turma}</td>")
        for c in campos_sel:
            tds += f"<td>{_formatar_valor(row, c)}</td>"
        tr += f"<tr>{tds}</tr>"
    return tr


def gerar_html_preview(df, campos_sel, opcoes_campos, orientacao, turma_sel):
    cfg = _get_id_cfg()
    page_size = "A4 portrait" if "Retrato" in orientacao else "A4 landscape"
    data_hora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    cabecalho = render_cabecalho_html(cfg, extra=f"Relatório de Identificação (Cara-Crachá) — {turma_sel}")
    rodape    = render_rodape_html(cfg)
    th = _cabecalhos_html(campos_sel, opcoes_campos)
    tr = _linhas_html(df, campos_sel, opcoes_campos, fotos_b64=None)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{_css_base(page_size)}</style>
{_JS_SORT}
</head><body>
{cabecalho}
<p style="text-align:center;font-size:10px;color:#64748B;margin-bottom:12px;">
  Escopo: <b>{turma_sel}</b> | Gerado em: {data_hora}
</p>
<table id="cc-table">
  <thead><tr>{th}</tr></thead>
  <tbody>{tr}</tbody>
</table>
{rodape}
</body></html>"""


def gerar_html_pdf(df, campos_sel, opcoes_campos, orientacao, turma_sel, sort_col, sort_asc, fotos_b64=None):
    """HTML para xhtml2pdf — imagens base64 embutidas, cabeçalho padrão, ordenação aplicada."""
    cfg = _get_id_cfg()
    df_sorted = df.sort_values(
        by=sort_col,
        ascending=sort_asc,
        key=lambda s: s.astype(str).str.lower(),
        na_position="last",
    )
    page_size = "A4 portrait" if "Retrato" in orientacao else "A4 landscape"
    data_hora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    label_dir = "crescente ▲" if sort_asc else "decrescente ▼"
    cabecalho = render_cabecalho_html(cfg, extra="Relatório de Identificação (Cara-Crachá)")
    rodape    = render_rodape_html(cfg)
    th = _cabecalhos_html(campos_sel, opcoes_campos)
    tr = _linhas_html(df_sorted, campos_sel, opcoes_campos, fotos_b64=fotos_b64 or {})
    return f"""<html><head><meta charset="UTF-8">
<style>{_css_pdf(page_size)}</style>
</head><body>
{cabecalho}
<p style="text-align:center;font-size:10px;color:#64748B;margin-bottom:12px;">
  Escopo: <b>{turma_sel}</b> &nbsp;|&nbsp; Ordenado por: <b>{sort_col}</b> ({label_dir}) &nbsp;|&nbsp; {data_hora}
</p>
<table>
  <thead><tr>{th}</tr></thead>
  <tbody>{tr}</tbody>
</table>
{rodape}
</body></html>"""


def _gerar_pdf(html):
    buf = io.BytesIO()
    try:
        status = pisa.pisaDocument(io.StringIO(html), buf)
        if status.err:
            return None, f"Erro na geração do PDF (código {status.err})."
        return buf.getvalue(), None
    except Exception as e:
        return None, str(e)


def renderizar_aba_caracracha():
    st.markdown(
        "<h4 style='color: #0A2540; font-weight: 800;'>🪪 Relatório Cara-Crachá (Identificação)</h4>",
        unsafe_allow_html=True,
    )
    st.caption("Configure os campos e gere o preview. Para imprimir, clique em 'Preparar PDF' — as fotos serão embutidas.")

    opcoes_campos = {
        "whatsapp":           "WhatsApp / Celular",
        "data_nascimento":    "Data de Nascimento",
        "cpf":                "CPF",
        "rg":                 "RG",
        "endereco":           "Endereço",
        "bairro":             "Bairro",
        "contato_emergencia": "Contato de Emergência",
        "problemas_saude":    "Problemas de Saúde",
        "medicamentos":       "Medicamentos",
    }

    # ── Configurações ─────────────────────────────────────────────────────────
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 3, 2], vertical_alignment="top")

        turmas = get_todas_turmas(ativas_apenas=True)
        lista_turmas = (
            ["Todas as Turmas"] + turmas["nome"].tolist()
            if not turmas.empty else ["Todas as Turmas"]
        )
        turma_sel  = c1.selectbox("Filtrar Turma", lista_turmas, key="cc_turma")
        campos_sel = c2.multiselect(
            "Campos Extras (Foto, Nome e Turma já fixos)",
            options=list(opcoes_campos.keys()),
            format_func=lambda x: opcoes_campos[x],
            default=["whatsapp", "data_nascimento"],
            help="Se escolher muitos campos, mude a Orientação para Paisagem.",
        )
        orientacao = c3.radio(
            "Orientação da Folha",
            ["Retrato (Vertical)", "Paisagem (Wide/Horizontal)"],
            key="cc_ori",
        )

    # ── PASSO 1 — Gerar Preview (rápido, sem download de fotos) ───────────────
    if st.button("👁️ GERAR PREVIEW DO RELATÓRIO", type="primary", use_container_width=True):
        with st.spinner("Buscando alunos..."):
            df_todos = buscar_alunos_geral(incluir_inativos=False)
            if df_todos.empty:
                st.warning("⚠️ Nenhum aluno encontrado.")
                return

            df_alunos = (
                df_todos[df_todos["turma"] == turma_sel].copy()
                if turma_sel != "Todas as Turmas" else df_todos.copy()
            )
            if df_alunos.empty:
                st.warning(f"⚠️ Nenhum aluno para a turma: **{turma_sel}**.")
                return

            df_alunos = df_alunos.sort_values("nome").reset_index(drop=True)

            # Salva estado — sem fotos (PDF ainda não preparado)
            st.session_state.update({
                "cc_df":        df_alunos,
                "cc_turma_sel": turma_sel,
                "cc_campos":    campos_sel,
                "cc_orient":    orientacao,
                "cc_sort_col":  "nome",
                "cc_sort_asc":  True,
                "cc_pdf_bytes": None,   # PDF será gerado no passo 2
                "cc_fotos_b64": {},
            })

    # ── Sem dados ainda ───────────────────────────────────────────────────────
    if "cc_df" not in st.session_state:
        return

    df_alunos     = st.session_state["cc_df"]
    turma_label   = st.session_state["cc_turma_sel"]
    campos_ativos = st.session_state["cc_campos"]
    orient        = st.session_state["cc_orient"]

    st.markdown("<hr style='margin-top:8px;margin-bottom:12px;'/>", unsafe_allow_html=True)

    # ── Controles de ordenação ────────────────────────────────────────────────
    cols_disp = {"nome": "Nome do Aluno", "turma": "Turma"}
    for c in campos_ativos:
        cols_disp[c] = opcoes_campos[c]

    col_ord1, col_ord2, col_prep, col_dl = st.columns([2, 2, 2, 2], vertical_alignment="bottom")

    sort_col = col_ord1.selectbox(
        "📋 Ordenar por",
        options=list(cols_disp.keys()),
        format_func=lambda x: cols_disp[x],
        index=list(cols_disp.keys()).index(st.session_state.get("cc_sort_col", "nome")),
        key="cc_sort_col_sel",
    )
    sort_dir = col_ord2.radio(
        "Direção", ["Crescente ▲", "Decrescente ▼"],
        horizontal=True,
        index=0 if st.session_state.get("cc_sort_asc", True) else 1,
        key="cc_sort_dir_sel",
    )
    sort_asc = "Crescente" in sort_dir
    st.session_state["cc_sort_col"] = sort_col
    st.session_state["cc_sort_asc"] = sort_asc

    # ── PASSO 2 — Preparar PDF com fotos (download paralelo) ─────────────────
    if col_prep.button("📥 Preparar PDF com fotos", use_container_width=True):
        with st.spinner(f"Baixando fotos de {len(df_alunos)} aluno(s)..."):
            fotos = _prefetch_fotos(df_alunos)
            st.session_state["cc_fotos_b64"] = fotos

        with st.spinner("Gerando PDF..."):
            html_pdf = gerar_html_pdf(
                df_alunos, campos_ativos, opcoes_campos, orient, turma_label,
                sort_col, sort_asc, fotos_b64=fotos,
            )
            pdf_bytes, pdf_erro = _gerar_pdf(html_pdf)
            if pdf_bytes:
                st.session_state["cc_pdf_bytes"] = pdf_bytes
                st.session_state["cc_pdf_nome"]  = f"CaraCracha_{turma_label}.pdf"
            else:
                st.session_state["cc_pdf_bytes"] = None
                st.error(f"Erro ao gerar PDF: {pdf_erro}")

    # ── Botão de download (aparece quando PDF está pronto) ────────────────────
    pdf_bytes = st.session_state.get("cc_pdf_bytes")
    if pdf_bytes and XHTML_DISPONIVEL:
        col_dl.download_button(
            label="🖨️ BAIXAR PDF",
            data=pdf_bytes,
            file_name=st.session_state.get("cc_pdf_nome", "CaraCracha.pdf"),
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    elif not XHTML_DISPONIVEL:
        col_dl.error("xhtml2pdf não instalado.")
    else:
        col_dl.info("← Prepare o PDF primeiro")

    st.caption(
        f"💡 Clique nos **cabeçalhos** da tabela para reordenar o preview. "
        f"Ordenação atual para PDF: **{cols_disp[sort_col]}** {'▲' if sort_asc else '▼'}"
    )

    # ── Preview ───────────────────────────────────────────────────────────────
    df_prev = df_alunos.sort_values(
        by=sort_col, ascending=sort_asc,
        key=lambda s: s.astype(str).str.lower(), na_position="last",
    )
    html_prev = gerar_html_preview(df_prev, campos_ativos, opcoes_campos, orient, turma_label)

    st.markdown(f"#### 👀 Preview — {len(df_alunos)} aluno(s) | {turma_label}")
    st.iframe(html_prev, height=640)
