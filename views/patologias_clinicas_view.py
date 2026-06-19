# ==============================================================================
# 📄 views/patologias_clinicas_view.py
# 🏷️ VERSÃO: 1.0 — Patologias / Anamnese Clínica
# ⚙️ Painel de saúde com peso, altura, IMC, última PA e escala Borg.
#    Exporta PDF completo para análise por IA (escala Borg, carga individualizada).
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import re

from database import (
    buscar_alunos_geral,
    get_todas_turmas,
    get_ultima_pa_todos,
)
from utils.busca_aluno import filtrar_alunos_df as _faf_pat

# ── Palavras-chave que disparam alerta clínico ────────────────────────────────
_PALAVRAS_ALERTA = [
    # ── Cardiovascular / Neurológico ──────────────────────────────────────────
    "cirurgia", "cardiaco", "cardíaco", "pressao", "pressão", "infarto",
    "marcapasso", "insuficiencia", "coagulação", "anticoagulante",
    "arritmia", "avc", "acidente vascular", "trombose", "hemofilia",
    # ── Metabólico / Oncológico ───────────────────────────────────────────────
    "diabetes", "quimioterapia", "radioterapia", "cancer", "câncer",
    # ── Neurológico / Cognitivo ───────────────────────────────────────────────
    "epilepsia", "parkinson", "alzheimer", "autismo",
    # ── Respiratório ─────────────────────────────────────────────────────────
    "dpoc", "asma", "bronco",
    # ── Musculoesquelético ────────────────────────────────────────────────────
    "osteoporose", "artrose", "artrite", "condromalacia", "condromalácia",
    "fibromialgia",
    # ── Endócrino ────────────────────────────────────────────────────────────
    "hipotireoidismo", "hashimoto",
]

_PA_CLS_PT = {
    "normal":   "Normal",
    "elevada":  "Elevada",
    "estagio1": "Est.1",
    "estagio2": "Est.2",
    "crise":    "Crise",
}

_PA_COR = {
    "Normal":  "#10B981",
    "Elevada": "#F59E0B",
    "Est.1":   "#E64A19",
    "Est.2":   "#B71C1C",
    "Crise":   "#7F0000",
}


# ── Helpers internos ──────────────────────────────────────────────────────────

def _extrair_secao_hashtag(texto: str, hashtag: str) -> str:
    """Extrai o conteúdo de uma seção #Hashtag: de um texto multilinha."""
    if not texto:
        return ""
    pattern = rf"#{re.escape(hashtag)}:\s*(.+?)(?=\n\n#|\Z)"
    m = re.search(pattern, texto, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _tem_alerta(texto: str) -> bool:
    t = texto.lower() if texto else ""
    return any(p in t for p in _PALAVRAS_ALERTA)


def _calcular_imc(peso, altura) -> tuple[float | None, str]:
    """Retorna (valor_float, 'valor (Categoria)') ou (None, '—')."""
    try:
        p = float(peso or 0)
        h = float(altura or 0)
        if p > 10 and h > 0.5:
            imc = p / (h * h)
            if imc < 18.5:
                cat = "Baixo peso"
            elif imc < 25.0:
                cat = "Normal"
            elif imc < 30.0:
                cat = "Sobrepeso"
            elif imc < 35.0:
                cat = "Obesidade I"
            elif imc < 40.0:
                cat = "Obesidade II"
            else:
                cat = "Obesidade III"
            return imc, f"{imc:.1f} — {cat}"
    except Exception:
        pass
    return None, "—"


# ── Função principal ──────────────────────────────────────────────────────────

def renderizar_aba_patologias():
    st.markdown("""
        <div style='background:linear-gradient(135deg,#FFF1F2,#FEF2F2);
                    border-left:5px solid #EF4444;padding:18px 20px;
                    border-radius:8px;margin-bottom:20px;'>
            <h3 style='margin:0 0 4px 0;color:#991B1B;'>🧬 Patologias — Anamnese Clínica</h3>
            <p style='margin:0;color:#B91C1C;font-size:13px;'>
                Painel completo de saúde: patologias, restrições, medicamentos,
                <strong>peso, altura, IMC</strong> e <strong>última PA</strong> de cada aluno.<br>
                Use a coluna <strong>Borg / Risco</strong> para registrar o esforço percebido.<br>
                Exporte o PDF e envie para uma IA para obter sugestões de carga, escala Borg e BORG
                individualizados.<br>
                ⚠️ <em>Dados confidenciais — acesso restrito à equipe técnica.</em>
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Filtros ────────────────────────────────────────────────────────────────
    c_turma, c_alerta, c_busca = st.columns([2, 1, 2])
    with c_turma:
        df_turmas = get_todas_turmas(ativas_apenas=True)
        opcoes_turma = ["Todas as Turmas"] + (
            df_turmas["nome"].tolist() if not df_turmas.empty else []
        )
        turma_filtro = st.selectbox("Turma:", opcoes_turma, key="pat_turma")
    with c_alerta:
        so_alertas = st.checkbox("🔴 Apenas Alertas", key="pat_alertas")
    with c_busca:
        busca_pat = st.text_input(
            "🔍 Buscar aluno:", key="pat_busca", placeholder="Nome…"
        )

    # ── Carrega dados ─────────────────────────────────────────────────────────
    with st.spinner("Carregando dados clínicos…"):
        df_raw  = buscar_alunos_geral("", incluir_inativos=False)
        pa_dict = get_ultima_pa_todos()

    if df_raw is None or df_raw.empty:
        st.warning("Nenhum aluno ativo encontrado.")
        return

    if "status" in df_raw.columns:
        df_raw = df_raw[df_raw["status"] != "Inativo"]

    if turma_filtro != "Todas as Turmas":
        df_raw = df_raw[df_raw["turma"] == turma_filtro]

    if busca_pat and len(busca_pat.strip()) >= 2:
        df_raw = _faf_pat(df_raw, busca_pat, cols=["nome"], min_len=2)

    # ── Monta tabela ───────────────────────────────────────────────────────────
    registros = []
    for _, r in df_raw.iterrows():
        ps          = str(r.get("problemas_saude") or "")
        patologias  = _extrair_secao_hashtag(ps, "Patologias") or (ps[:80] if ps else "")
        restricoes  = _extrair_secao_hashtag(ps, "Restrições_Físicas")
        alergias    = _extrair_secao_hashtag(ps, "Alergias")
        incomodos   = _extrair_secao_hashtag(ps, "Incômodos_Físicos")
        medicament  = _extrair_secao_hashtag(ps, "Uso_Contínuo_Medicamentos")
        alerta      = _tem_alerta(patologias) or _tem_alerta(ps)

        # Peso / Altura / IMC
        peso   = r.get("peso")
        altura = r.get("altura")
        try:
            peso_fmt = f"{float(peso):.1f}" if peso and float(peso) > 0 else "—"
        except Exception:
            peso_fmt = "—"
        try:
            altura_fmt = f"{float(altura):.2f}" if altura and float(altura) > 0.5 else "—"
        except Exception:
            altura_fmt = "—"
        _, imc_fmt = _calcular_imc(peso, altura)

        # PA
        aid    = str(r.get("id", ""))
        pa     = pa_dict.get(aid, {})
        sis    = pa.get("sis") or 0
        dia    = pa.get("dia") or 0
        pul    = pa.get("pul") or 0
        cls    = pa.get("cls", "")
        pa_txt = f"{sis}/{dia}" if sis and dia else "—"
        pa_cls = _PA_CLS_PT.get(cls, cls.capitalize() if cls else "—")
        pa_dat = (pa.get("data") or "")[:10]

        # Borg — padrão vem do banco (risco_borg), override via session_state
        borg_key   = f"borg_pat_{aid}"
        borg_db    = int(r.get("risco_borg") or 0)
        borg_atual = st.session_state.get(borg_key, borg_db)

        registros.append({
            "id":             aid,
            "Foto":           str(r.get("foto_url") or ""),
            "🔴":             "🔴" if alerta else "",
            "Nome":           str(r.get("nome", "")),
            "Turma":          str(r.get("turma") or "")[:3].strip(),
            "Borg/Risco":     borg_atual,
            "Peso (kg)":      peso_fmt,
            "Altura (m)":     altura_fmt,
            "IMC":            imc_fmt,
            "PA Sis/Dia":     pa_txt,
            "PA Classe":      pa_cls,
            "Data PA":        pa_dat,
            "Pulso (bpm)":    str(int(pul)) if pul else "—",
            "Patologias":     patologias[:120],
            "Restrições":     restricoes[:80],
            "Alergias":       alergias[:60],
            "Incômodos":      incomodos[:60],
            "Medicamentos":   medicament[:80],
            "Ct. Emergência": str(r.get("contato_emergencia", "") or "")[:100],
        })

    df_monitor = pd.DataFrame(registros)

    if so_alertas:
        df_monitor = df_monitor[df_monitor["🔴"] == "🔴"]

    if df_monitor.empty:
        st.info("Nenhum aluno encontrado com os filtros selecionados.")
        return

    # ── Legenda Borg ──────────────────────────────────────────────────────────
    with st.expander("📖 Legenda da Escala Borg (0–10)", expanded=False):
        st.markdown("""
        | Valor | Significado |
        |-------|-------------|
        | 0 | Nenhum esforço / Sem dor |
        | 1–2 | Muito leve |
        | 3–4 | Moderado — atenção |
        | 5–6 | Pesado — monitorar de perto |
        | 7–8 | Muito pesado — considerar adaptações |
        | 9–10 | **Máximo / Emergência — intervir imediatamente** |
        """)

    st.markdown(
        f"**{len(df_monitor)} aluno(s)** — edite a coluna **Borg/Risco** (0–10) "
        f"e clique em 💾 Salvar para registrar na sessão:"
    )

    col_config = {
        "id":             st.column_config.TextColumn("ID", disabled=True, width="small"),
        "Foto":           st.column_config.ImageColumn("📸", width="small"),
        "🔴":             st.column_config.TextColumn("⚠️", width="small"),
        "Nome":           st.column_config.TextColumn("Nome", disabled=True, width="medium"),
        "Turma":          st.column_config.TextColumn("Turma", disabled=True, width="small"),
        "Borg/Risco":     st.column_config.NumberColumn(
            "Borg / Risco (0–10)", min_value=0, max_value=10, step=1, width="small",
            help="0 = sem risco  ·  10 = emergência",
        ),
        "Peso (kg)":      st.column_config.TextColumn("Peso (kg)", disabled=True, width="small"),
        "Altura (m)":     st.column_config.TextColumn("Altura (m)", disabled=True, width="small"),
        "IMC":            st.column_config.TextColumn("IMC", disabled=True, width="medium",
                              help="IMC calculado a partir do peso e altura cadastrados na ficha"),
        "PA Sis/Dia":     st.column_config.TextColumn("PA Sis/Dia (mmHg)", disabled=True, width="small"),
        "PA Classe":      st.column_config.TextColumn("Classif. PA", disabled=True, width="small"),
        "Data PA":        st.column_config.TextColumn("Data PA", disabled=True, width="small"),
        "Pulso (bpm)":    st.column_config.TextColumn("Pulso (bpm)", disabled=True, width="small"),
        "Patologias":     st.column_config.TextColumn("Patologias / Saúde", disabled=True, width="large"),
        "Restrições":     st.column_config.TextColumn("Restrições Físicas", disabled=True, width="medium"),
        "Alergias":       st.column_config.TextColumn("Alergias", disabled=True, width="medium"),
        "Incômodos":      st.column_config.TextColumn("Incômodos", disabled=True, width="medium"),
        "Medicamentos":   st.column_config.TextColumn("Medicamentos", disabled=True, width="medium"),
        "Ct. Emergência": st.column_config.TextColumn(
            "🚨 Ct. Emergência", disabled=True, width="medium",
            help="Contato de emergência cadastrado na ficha do aluno",
        ),
    }

    _col_order = [
        "Foto", "🔴", "Nome", "Turma", "Borg/Risco",
        "Peso (kg)", "Altura (m)", "IMC",
        "PA Sis/Dia", "PA Classe", "Data PA", "Pulso (bpm)",
        "Patologias", "Restrições", "Alergias", "Incômodos", "Medicamentos", "Ct. Emergência",
    ]

    df_editado = st.data_editor(
        df_monitor, column_config=col_config,
        column_order=_col_order,
        use_container_width=True, hide_index=True,
        key="data_editor_pat", num_rows="fixed",
    )

    # ── Botões de ação ────────────────────────────────────────────────────────
    c_salvar, c_reset, c_pdf, _ = st.columns([2, 1, 2, 1])
    with c_salvar:
        if st.button(
            "💾 Salvar Borg (sessão)", type="primary",
            use_container_width=True, key="pat_salvar",
        ):
            for _, row_e in df_editado.iterrows():
                st.session_state[f"borg_pat_{row_e['id']}"] = int(row_e["Borg/Risco"])
            st.toast(f"✅ {len(df_editado)} classificações salvas!", icon="💾")
    with c_reset:
        if st.button("🔄 Limpar Borg", use_container_width=True, key="pat_reset"):
            for _, row_e in df_editado.iterrows():
                k = f"borg_pat_{row_e['id']}"
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    with c_pdf:
        with st.spinner("Preparando PDF…"):
            try:
                from gerador_pdf import gerar_pdf_patologias
                _pdf_pat = gerar_pdf_patologias(
                    df_editado.drop(columns=["id", "Foto"], errors="ignore"),
                    turma_filtro=turma_filtro,
                )
                st.download_button(
                    label="📄 Baixar PDF Anamnese",
                    data=_pdf_pat,
                    file_name=f"patologias_anamnese_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="pat_download_pdf",
                )
            except Exception as _ep:
                st.error(f"Erro PDF: {_ep}")

    # ── Preview HTML ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🖥️ Preview do Relatório (idêntico ao PDF)")

    _hoje_prev = datetime.date.today().strftime("%d/%m/%Y")
    _hora_prev = datetime.datetime.now().strftime("%H:%M")
    _n_alertas = int((df_editado["🔴"] == "🔴").sum())
    _n_borg7   = int((df_editado["Borg/Risco"].fillna(0).astype(int) >= 7).sum())

    def _wa_html(contato: str) -> str:
        if not contato or contato in ("nan", "None", "—", ""):
            return "<span style='color:#94A3B8;font-size:9px;'>—</span>"
        grupos = re.findall(r"\d{8,13}", contato)
        wa_url = None
        if grupos:
            phone = grupos[-1]
            if len(phone) <= 11:
                phone = "55" + phone
            wa_url = f"https://wa.me/{phone}"
        texto_exib = contato[:55] + ("…" if len(contato) > 55 else "")
        if wa_url:
            return (
                f"<span style='font-size:9px;display:block;'>{texto_exib}</span>"
                f"<a href='{wa_url}' target='_blank' "
                f"style='font-size:9px;color:#fff;background:#25D366;padding:1px 5px;"
                f"border-radius:8px;text-decoration:none;font-weight:700;"
                f"display:inline-block;margin-top:1px;'>📲 WA</a>"
            )
        return f"<span style='font-size:9px;'>{texto_exib}</span>"

    _linhas_html = ""
    for _zi, (_, _row) in enumerate(df_editado.iterrows()):
        _alerta = str(_row.get("🔴", "")) == "🔴"
        _bv     = int(_row.get("Borg/Risco", 0) or 0)
        _borg7  = _bv >= 7
        _bg = (
            "background:#FEE2E2;" if _alerta else
            "background:#FEF3C7;" if _borg7 else
            "background:#F5F7FA;" if _zi % 2 == 1 else
            "background:#FFFFFF;"
        )
        _icone    = "🔴" if _alerta else ""
        _borg_txt = str(_bv) if _bv > 0 else "—"
        _pa_cls   = str(_row.get("PA Classe", "") or "—")
        _pa_cor   = _PA_COR.get(_pa_cls, "#475569")
        _ct_html  = _wa_html(str(_row.get("Ct. Emergência", "") or ""))
        _furl = str(_row.get("Foto", "") or "")
        _foto_cell = (
            f"<img src='{_furl}' style='width:28px;height:28px;border-radius:50%;"
            f"object-fit:cover;vertical-align:middle;'>"
            if _furl.startswith("http") else
            "<div style='width:28px;height:28px;border-radius:50%;background:#E2E8F0;"
            "display:inline-block;'></div>"
        )

        _linhas_html += (
            f"<tr style='{_bg}'>"
            f"<td style='text-align:center;padding:3px 4px;border:1px solid #CBD5E1;'>{_foto_cell}</td>"
            f"<td style='text-align:center;padding:3px 4px;border:1px solid #CBD5E1;font-size:10px;'>{_icone}</td>"
            f"<td style='padding:3px 5px;border:1px solid #CBD5E1;font-size:10px;font-weight:600;'>{_row.get('Nome','')}</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9.5px;'>{_row.get('Turma','')}</td>"
            f"<td style='text-align:center;padding:3px 4px;border:1px solid #CBD5E1;font-size:10px;"
            f"font-weight:700;color:{'#991B1B' if _borg7 else '#0A2540'};'>{_borg_txt}</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9px;text-align:center;'>"
            f"  <span style='font-weight:600;'>{_row.get('Peso (kg)','—')} kg</span><br>"
            f"  <span style='color:#475569;'>{_row.get('Altura (m)','—')} m</span><br>"
            f"  <span style='font-size:8.5px;color:#1E40AF;'>{_row.get('IMC','—')}</span>"
            f"</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9.5px;text-align:center;"
            f"font-weight:600;color:{_pa_cor};'>{_row.get('PA Sis/Dia','—')}<br>"
            f"<span style='font-size:8px;'>{_pa_cls}</span></td>"
            f"<td style='padding:3px 5px;border:1px solid #CBD5E1;font-size:9.5px;'>{_row.get('Patologias','')}</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9.5px;'>{_row.get('Restrições','')}</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9.5px;'>{_row.get('Alergias','')}</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9.5px;'>{_row.get('Medicamentos','')}</td>"
            f"<td style='padding:3px 4px;border:1px solid #CBD5E1;font-size:9.5px;'>{_ct_html}</td>"
            f"</tr>"
        )

    _preview_html = f"""
    <div style="font-family:Arial,sans-serif;background:#fff;border:1px solid #CBD5E1;
                border-radius:8px;overflow-x:auto;padding:12px 14px;margin-top:4px;">
      <div style="border-bottom:2px solid #991B1B;padding-bottom:8px;margin-bottom:6px;
                  display:flex;align-items:center;justify-content:space-between;">
        <div style="font-size:11px;color:#64748B;">Instituto Muda Brasil</div>
        <div style="text-align:center;">
          <div style="font-size:13px;font-weight:900;color:#0A2540;">🧬 Patologias — Anamnese Clínica</div>
          <div style="font-size:9px;color:#64748B;">
            Emitido em {_hoje_prev} às {_hora_prev} &nbsp;|&nbsp; Turma: {turma_filtro}
          </div>
        </div>
        <div style="font-size:11px;color:#64748B;text-align:right;">{len(df_editado)} alunos</div>
      </div>
      <div style="font-size:9.5px;color:#991B1B;font-weight:700;margin-bottom:5px;">
        CONFIDENCIAL — Alertas clínicos: {_n_alertas} &nbsp;|&nbsp; Borg ≥ 7: {_n_borg7}
      </div>
      <div style="font-size:8.5px;margin-bottom:6px;display:flex;gap:12px;flex-wrap:wrap;">
        <span><span style="display:inline-block;width:10px;height:10px;background:#FEE2E2;
              border:1px solid #CBD5E1;vertical-align:middle;"></span> Alerta clínico</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:#FEF3C7;
              border:1px solid #CBD5E1;vertical-align:middle;"></span> Borg ≥ 7</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:#F5F7FA;
              border:1px solid #CBD5E1;vertical-align:middle;"></span> Normal</span>
      </div>
      <table style="width:100%;border-collapse:collapse;min-width:900px;">
        <thead>
          <tr style="background:#7F1D1D;color:#fff;">
            <th style="padding:4px 3px;font-size:9px;border:1px solid #991B1B;width:4%;">📸</th>
            <th style="padding:4px 3px;font-size:9px;border:1px solid #991B1B;width:2%;">⚠️</th>
            <th style="padding:4px 5px;font-size:9px;border:1px solid #991B1B;text-align:left;width:10%;">Nome</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;width:4%;">Turma</th>
            <th style="padding:4px 3px;font-size:9px;border:1px solid #991B1B;width:3%;">Borg</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;text-align:center;width:9%;">Peso / Alt / IMC</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;text-align:center;width:7%;">PA / Classe</th>
            <th style="padding:4px 5px;font-size:9px;border:1px solid #991B1B;text-align:left;width:13%;">Patologias / Saúde</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;text-align:left;width:8%;">Restrições</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;text-align:left;width:5%;">Alergias</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;text-align:left;width:8%;">Medicamentos</th>
            <th style="padding:4px 4px;font-size:9px;border:1px solid #991B1B;text-align:left;width:13%;">🚨 Ct. Emergência</th>
          </tr>
        </thead>
        <tbody>{_linhas_html}</tbody>
      </table>
      <div style="border-top:1px solid #E2E8F0;margin-top:6px;padding-top:5px;
                  font-size:8.5px;color:#991B1B;font-weight:700;">
        Resumo: {len(df_editado)} alunos &nbsp;|&nbsp;
        {_n_alertas} alertas clínicos &nbsp;|&nbsp; {_n_borg7} com Borg ≥ 7
      </div>
      <div style="font-size:7.5px;color:#94A3B8;margin-top:2px;">
        Documento confidencial — uso restrito à equipe técnica.
        Proibida reprodução sem autorização da coordenação.
      </div>
    </div>
    """
    st.markdown(_preview_html, unsafe_allow_html=True)

    # ── Alertas ativos ────────────────────────────────────────────────────────
    alertas_borg = df_editado[df_editado["Borg/Risco"] >= 7]
    alertas_clin = df_editado[df_editado["🔴"] == "🔴"]
    if not alertas_borg.empty or not alertas_clin.empty:
        st.markdown("### 🚨 Alertas Ativos")
        col_b, col_c = st.columns(2)
        with col_b:
            if not alertas_borg.empty:
                st.error(f"⚡ **{len(alertas_borg)} aluno(s) com Borg ≥ 7:**")
                for _, ar in alertas_borg.iterrows():
                    st.markdown(
                        f"  - **{ar['Nome']}** ({ar['Turma']}) — Borg: `{int(ar['Borg/Risco'])}`"
                    )
        with col_c:
            if not alertas_clin.empty:
                st.warning(f"🔴 **{len(alertas_clin)} aluno(s) com alertas clínicos:**")
                for _, ar in alertas_clin.iterrows():
                    st.markdown(
                        f"  - **{ar['Nome']}** ({ar['Turma']}) — {ar['Patologias'][:60]}"
                    )

    st.info(
        "💡 **Dica IA:** Exporte o PDF acima e envie para o ChatGPT ou Claude com o prompt: "
        "*'Analise a anamnese clínica abaixo e sugira, para cada aluno, a escala Borg "
        "recomendada, adaptações de carga e alertas de segurança para atividade física.'*"
    )
