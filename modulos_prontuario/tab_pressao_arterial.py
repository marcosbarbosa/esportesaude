# ==============================================================================
# 📄 ARQUIVO: modulos_prontuario/tab_pressao_arterial.py
# 🏷️ VERSÃO: 1.0 — Registro Periódico de Pressão Arterial
# ⚙️ FUNÇÃO: Formulário + histórico de PA para o prontuário do aluno.
#            Classificação automática em tempo real (AHA/JNC guidelines).
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import uuid

try:
    from database import (
        salvar_registro_pa, atualizar_registro_pa,
        get_registros_pa, deletar_registro_pa,
        _tabela_pa_existe, SQL_CRIAR_REGISTROS_PA, SQL_CORRIGIR_RLS_PA,
    )
    _DB_PA_OK = True
except Exception:
    _DB_PA_OK = False


# ──────────────────────────────────────────────────────────────────────────────
# CLASSIFICAÇÃO / LÓGICA CLÍNICA
# ──────────────────────────────────────────────────────────────────────────────
_CLS = {
    "crise":    {"label": "💥 CRISE HIPERTENSIVA",       "cor": "#7F0000", "bg": "#FFEBEE", "badge_bg": "#B71C1C", "icone": "🚨"},
    "estagio2": {"label": "Estágio 2 — Hipertensão Alta","cor": "#B71C1C", "bg": "#FFEBEE", "badge_bg": "#C62828", "icone": "🔴"},
    "estagio1": {"label": "Estágio 1 — Hipertensão Leve","cor": "#C62828", "bg": "#FFF3E0", "badge_bg": "#E64A19", "icone": "🟠"},
    "elevada":  {"label": "Elevada — Atenção",           "cor": "#E65100", "bg": "#FFFDE7", "badge_bg": "#F57F17", "icone": "🟡"},
    "normal":   {"label": "Normal",                      "cor": "#1565C0", "bg": "#E3F2FD", "badge_bg": "#1976D2", "icone": "🔵"},
}

_MENSAGENS = {
    "normal":   "Leitura dentro da faixa normal. Manter acompanhamento periódico.",
    "elevada":  "Leitura de atenção. Observar rotina e repetir conforme protocolo.",
    "estagio1": "Leitura alterada. Registrar, monitorar e avaliar atividade com cautela.",
    "estagio2": "Leitura alta. Evitar liberação automática para esforço intenso e orientar avaliação médica.",
    "crise":    "⚠️ Valor crítico! Repetir aferição imediatamente. Considerar encaminhamento urgente — especialmente se houver sintomas.",
}

_CONDUTA = {
    "normal":   ("✅ Apto — sem restrições",        "#065F46", "#D1FAE5"),
    "elevada":  ("🔍 Apto com observação",           "#78350F", "#FEF3C7"),
    "estagio1": ("⚠️ Requer cautela na atividade",  "#7C2D12", "#FFF7ED"),
    "estagio2": ("🚫 Não liberar atividade intensa", "#7F1D1D", "#FEE2E2"),
    "crise":    ("🚨 Requer ação imediata!",         "#450A0A", "#FEE2E2"),
}


def classificar_pressao(sistolica, diastolica):
    """Retorna chave de classificação considerando sempre o nível mais grave."""
    if sistolica is None or diastolica is None:
        return None
    s, d = int(sistolica), int(diastolica)
    if s > 180 or d > 120:
        return "crise"
    if s >= 140 or d >= 90:
        return "estagio2"
    if s >= 130 or d >= 80:
        return "estagio1"
    if 120 <= s <= 129 and d < 80:
        return "elevada"
    if s < 120 and d < 80:
        return "normal"
    if d >= 90:
        return "estagio2"
    if d >= 80:
        return "estagio1"
    return "normal"


def gerar_mensagem(classificacao):
    return _MENSAGENS.get(classificacao, "")


def definir_cor_risco(classificacao):
    return _CLS.get(classificacao, {}).get("cor", "#64748B")


def avaliar_conduta(classificacao, sintomas):
    if sintomas and any(s in sintomas for s in ["Dor no peito", "Falta de ar", "Visão embaçada"]) \
            and classificacao in ("estagio1", "estagio2", "crise"):
        return ("🚨 Sintomas críticos presentes — encaminhar imediatamente", "#450A0A", "#FEE2E2")
    return _CONDUTA.get(classificacao, ("—", "#374151", "#F9FAFB"))



def _chave(aluno_id, sufixo):
    return f"pa_{sufixo}_{aluno_id}"


def _init_historico(aluno_id):
    """Carrega histórico do Supabase; fallback para lista vazia se DB indisponível."""
    k = _chave(aluno_id, "hist")
    if k not in st.session_state:
        if _DB_PA_OK:
            try:
                st.session_state[k] = get_registros_pa(aluno_id)
            except Exception:
                st.session_state[k] = []
        else:
            st.session_state[k] = []


def salvar_registro(aluno_id, dados):
    k = _chave(aluno_id, "hist")
    dados["aluno_nome"] = st.session_state.get(f"pa_nome_{aluno_id}", "")
    if _DB_PA_OK:
        dados["aluno_id"] = aluno_id
        dados.setdefault("id", str(uuid.uuid4()))
        ok, msg = salvar_registro_pa(dados)
        if not ok:
            st.error(f"Erro ao salvar no banco: {msg}")
            if "row-level security" in msg.lower() or "42501" in msg:
                st.warning("🔒 **Problema de RLS detectado.** Execute o SQL abaixo no Supabase → SQL Editor:")
                st.code(SQL_CORRIGIR_RLS_PA, language="sql")
            return
        st.session_state.pop(k, None)
    else:
        _init_historico(aluno_id)
        st.session_state[k].insert(0, dados)


def editar_registro(aluno_id, registro_id, dados):
    k = _chave(aluno_id, "hist")
    if _DB_PA_OK:
        ok, msg = atualizar_registro_pa(registro_id, dados)
        if not ok:
            st.error(f"Erro ao atualizar: {msg}")
            return
        st.session_state.pop(k, None)
    else:
        _init_historico(aluno_id)
        for i, r in enumerate(st.session_state[k]):
            if r["id"] == registro_id:
                st.session_state[k][i] = {**r, **dados}
                break


def excluir_registro(aluno_id, registro_id):
    k = _chave(aluno_id, "hist")
    if _DB_PA_OK:
        deletar_registro_pa(registro_id)
        st.session_state.pop(k, None)
    else:
        _init_historico(aluno_id)
        st.session_state[k] = [r for r in st.session_state[k] if r["id"] != registro_id]

def filtrar_historico(registros, periodo_ini, periodo_fim, cls_filtro, momento_filtro):
    res = registros
    if periodo_ini:
        res = [r for r in res if r["data"] >= str(periodo_ini)]
    if periodo_fim:
        res = [r for r in res if r["data"] <= str(periodo_fim)]
    if cls_filtro and cls_filtro != "Todas":
        mapa = {"Normal": "normal", "Elevada": "elevada",
                "Estágio 1": "estagio1", "Estágio 2": "estagio2", "Crise": "crise"}
        res = [r for r in res if r.get("classificacao") == mapa.get(cls_filtro)]
    if momento_filtro and momento_filtro != "Todos":
        res = [r for r in res if r.get("momento") == momento_filtro]
    return res


# ──────────────────────────────────────────────────────────────────────────────
# CSS GLOBAL DO MÓDULO
# ──────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
.pa-titulo {
    font-size: 1.25rem; font-weight: 900; color: #0A2540;
    border-bottom: 3px solid #1976D2; padding-bottom: 8px; margin-bottom: 4px;
}
.pa-secao {
    font-size: 0.95rem; font-weight: 800; color: #1E3A5F;
    text-transform: uppercase; letter-spacing: 0.04em;
    margin: 16px 0 6px 0;
}
.pa-edu-box {
    background: #EFF6FF; border-left: 4px solid #3B82F6;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;
    font-size: 13px; color: #1E3A5F; line-height: 1.7;
}
.pa-edu-box strong { color: #1D4ED8; }
.pa-card {
    border-radius: 12px; padding: 16px 20px;
    border: 2px solid; margin-bottom: 10px;
}
.pa-valor-grande {
    font-size: 2.4rem; font-weight: 900; line-height: 1.1;
    letter-spacing: -1px;
}
.pa-badge {
    display: inline-block; padding: 4px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 800; color: #fff;
    text-transform: uppercase; letter-spacing: 0.05em;
}
.pa-conduta {
    border-radius: 8px; padding: 10px 14px;
    font-size: 13px; font-weight: 700; margin-top: 8px;
}
.pa-legenda-item {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 600; margin-right: 12px;
    white-space: nowrap;
}
.pa-legenda-dot {
    width: 12px; height: 12px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
}
.pa-hist-row {
    padding: 10px 12px; border-radius: 8px; margin-bottom: 6px;
    border: 1px solid #E2E8F0; background: #FAFAFA;
}
.pa-hist-critico {
    border: 2px solid #EF4444 !important;
    background: #FFF5F5 !important;
    animation: pa-pulso 1.4s infinite;
}
@keyframes pa-pulso {
    0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,.4); }
    50%      { box-shadow: 0 0 0 6px rgba(239,68,68,0); }
}
.pa-crise-badge {
    animation: pa-pisca 0.9s step-start infinite;
    background: #7F0000 !important;
}
@keyframes pa-pisca { 50% { opacity: 0; } }
.pa-info-label {
    font-size: 11px; color: #94A3B8; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em;
}
.pa-info-val {
    font-size: 13px; color: #1E293B; font-weight: 700;
}
</style>
"""


# ──────────────────────────────────────────────────────────────────────────────
# CARD DE CLASSIFICAÇÃO EM TEMPO REAL
# ──────────────────────────────────────────────────────────────────────────────
def _render_card_classificacao(sys_val, dia_val, pul_val):
    cls = classificar_pressao(sys_val, dia_val) if (sys_val and dia_val) else None
    info = _CLS.get(cls, {})

    if not cls:
        st.markdown("""
        <div class='pa-card' style='border-color:#CBD5E1;background:#F8FAFC;'>
          <p class='pa-info-label'>Aguardando valores</p>
          <p style='font-size:13px;color:#94A3B8;margin:0;'>
            Digite a pressão sistólica e diastólica para ver a classificação automática.
          </p>
        </div>""", unsafe_allow_html=True)
        return

    bg   = info["bg"]
    cor  = info["cor"]
    bdg  = info["badge_bg"]
    icn  = info["icone"]
    lbl  = info["label"]
    msg  = gerar_mensagem(cls)
    crise = cls == "crise"

    badge_cls = "pa-crise-badge" if crise else ""
    card_cls  = "pa-hist-critico" if crise else ""

    sys_str = str(sys_val) if sys_val else "—"
    dia_str = str(dia_val) if dia_val else "—"
    pul_str = str(pul_val) if pul_val else "—"

    st.markdown(f"""
    <div class='pa-card {card_cls}' style='border-color:{cor};background:{bg};'>
      <div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-bottom:8px;'>
        <span class='pa-valor-grande' style='color:{cor};'>{sys_str}/{dia_str}</span>
        <span class='pa-badge {badge_cls}' style='background:{bdg};font-size:12px;padding:6px 12px;'>
          {icn} {lbl}
        </span>
      </div>
      <p style='font-size:12px;color:{cor};margin:0 0 8px 0;font-weight:600;'>
        mmHg &nbsp;|&nbsp; Pulso: <strong>{pul_str} bpm</strong>
      </p>
      <p style='font-size:13px;color:#374151;margin:0;line-height:1.5;'>{msg}</p>
    </div>""", unsafe_allow_html=True)


def _render_conduta(cls, sintomas):
    if not cls:
        return
    txt, cor_txt, cor_bg = avaliar_conduta(cls, sintomas or [])
    st.markdown(f"""
    <div class='pa-conduta' style='background:{cor_bg};color:{cor_txt};border-left:4px solid {cor_txt};'>
      <span style='font-size:14px;'>🩺 Conduta sugerida: {txt}</span>
    </div>""", unsafe_allow_html=True)


def _render_legenda():
    st.markdown("""
    <div style='padding:8px 0 4px 0;flex-wrap:wrap;display:flex;gap:4px;'>
      <span class='pa-legenda-item'><span class='pa-legenda-dot' style='background:#1976D2;'></span> Normal</span>
      <span class='pa-legenda-item'><span class='pa-legenda-dot' style='background:#F57F17;'></span> Elevada</span>
      <span class='pa-legenda-item'><span class='pa-legenda-dot' style='background:#E64A19;'></span> Estágio 1</span>
      <span class='pa-legenda-item'><span class='pa-legenda-dot' style='background:#C62828;'></span> Estágio 2</span>
      <span class='pa-legenda-item'><span class='pa-legenda-dot' style='background:#7F0000;'></span> Crise</span>
    </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# FORMULÁRIO DE REGISTRO
# ──────────────────────────────────────────────────────────────────────────────
def _render_formulario(aluno_id, email_usuario):
    eid = st.session_state.get(_chave(aluno_id, "editar_id"))
    edit_data = None
    if eid:
        hist = st.session_state.get(_chave(aluno_id, "hist"), [])
        matches = [r for r in hist if r["id"] == eid]
        if matches:
            edit_data = matches[0]

    prefixo = "pae" if edit_data else "pan"
    titulo  = "✏️ Editar Registro" if edit_data else "📋 Nova Aferição"

    def _v(campo, default):
        return edit_data.get(campo, default) if edit_data else default

    st.markdown(f"<p class='pa-secao'>{titulo}</p>", unsafe_allow_html=True)

    col_form, col_card = st.columns([1.1, 0.9], gap="large")

    with col_form:
        r1c1, r1c2 = st.columns(2)
        data_med = r1c1.date_input(
            "📅 Data da medição",
            value=datetime.date.fromisoformat(_v("data", str(datetime.date.today()))),
            key=f"{prefixo}_data",
        )
        hora_med = r1c2.text_input(
            "🕐 Hora (HH:MM)",
            value=_v("hora", datetime.datetime.now().strftime("%H:%M")),
            key=f"{prefixo}_hora",
            placeholder="08:30",
        )

        st.markdown("<p class='pa-secao' style='margin-top:8px;'>Valores Medidos</p>", unsafe_allow_html=True)
        rc1, rc2, rc3 = st.columns(3)
        sistolica = rc1.number_input(
            "Sistólica (mmHg)",
            min_value=40, max_value=300, step=1,
            value=int(_v("sistolica", 120)),
            key=f"{prefixo}_sis",
            help="Pressão quando o coração BOMBEIA o sangue.",
        )
        diastolica = rc2.number_input(
            "Diastólica (mmHg)",
            min_value=20, max_value=200, step=1,
            value=int(_v("diastolica", 80)),
            key=f"{prefixo}_dia",
            help="Pressão quando o coração RELAXA entre os batimentos.",
        )
        pulso = rc3.number_input(
            "Pulso (bpm)",
            min_value=20, max_value=250, step=1,
            value=int(_v("pulso", 72)),
            key=f"{prefixo}_pul",
            help="Batimentos cardíacos por minuto.",
        )

        st.markdown("<p class='pa-secao' style='margin-top:8px;'>Contexto da Medição</p>", unsafe_allow_html=True)
        mc1, mc2 = st.columns(2)
        momento_opts = ["Antes da aula", "Depois da aula", "Em repouso", "Outro"]
        momento = mc1.selectbox(
            "Momento da coleta",
            momento_opts,
            index=momento_opts.index(_v("momento", "Antes da aula")),
            key=f"{prefixo}_momento",
        )
        rep_opts = ["1ª aferição", "2ª aferição", "3ª aferição ou mais"]
        repeticao = mc2.selectbox(
            "Repetição da medida",
            rep_opts,
            index=rep_opts.index(_v("repeticao", "1ª aferição")) if _v("repeticao", "1ª aferição") in rep_opts else 0,
            key=f"{prefixo}_rep",
        )

        mc3, mc4, mc5 = st.columns(3)
        braco_opts = ["Esquerdo", "Direito"]
        braco = mc3.selectbox(
            "Braço",
            braco_opts,
            index=braco_opts.index(_v("braco", "Esquerdo")) if _v("braco", "Esquerdo") in braco_opts else 0,
            key=f"{prefixo}_braco",
        )
        pos_opts = ["Sentado", "Em pé", "Deitado"]
        posicao = mc4.selectbox(
            "Posição",
            pos_opts,
            index=pos_opts.index(_v("posicao", "Sentado")) if _v("posicao", "Sentado") in pos_opts else 0,
            key=f"{prefixo}_pos",
        )

        sint_opts = ["Sem sintomas", "Tontura", "Dor no peito", "Falta de ar",
                     "Dor de cabeça", "Visão embaçada", "Outro"]
        sint_default = _v("sintomas", ["Sem sintomas"])
        sintomas = st.multiselect(
            "Sintomas relatados",
            sint_opts,
            default=[s for s in sint_default if s in sint_opts],
            key=f"{prefixo}_sint",
        )

        ex1, ex2 = st.columns(2)
        exercicio = ex1.checkbox(
            "🏃 Fez exercício antes?",
            value=bool(_v("exercicio_antes", False)),
            key=f"{prefixo}_ex",
            help="Evitar exercício intenso por pelo menos 30 min antes da medição.",
        )
        estimulantes = ex2.checkbox(
            "☕ Café, cigarro ou estimulantes?",
            value=bool(_v("estimulantes", False)),
            key=f"{prefixo}_est",
            help="Evitar café, álcool e cigarro por pelo menos 30 min antes da medição.",
        )

        profissional = st.text_input(
            "👤 Profissional responsável",
            value=_v("profissional", email_usuario or ""),
            key=f"{prefixo}_prof",
        )
        obs = st.text_area(
            "📝 Observações",
            value=_v("obs", ""),
            key=f"{prefixo}_obs",
            height=80,
            placeholder="Condições especiais, histórico relevante, intercorrências…",
        )

        cls_calc = classificar_pressao(sistolica, diastolica)
        btn_cols = st.columns([1, 1, 2]) if edit_data else st.columns([1, 3])

        with btn_cols[0]:
            salvar = st.button(
                "💾 Salvar Registro" if not edit_data else "✅ Confirmar Edição",
                type="primary",
                use_container_width=True,
                key=f"{prefixo}_salvar",
            )
        if edit_data:
            with btn_cols[1]:
                if st.button("✕ Cancelar", use_container_width=True, key=f"{prefixo}_cancel"):
                    st.session_state.pop(_chave(aluno_id, "editar_id"), None)
                    st.rerun()

        if salvar:
            erros = []
            if not hora_med or len(hora_med) < 4:
                erros.append("Informe a hora no formato HH:MM.")
            if sistolica <= 0:
                erros.append("Pressão sistólica inválida.")
            if diastolica <= 0:
                erros.append("Pressão diastólica inválida.")
            if not sintomas:
                erros.append("Selecione ao menos um sintoma (ou 'Sem sintomas').")

            if erros:
                for e in erros:
                    st.error(e)
            else:
                payload = {
                    "id": eid or str(uuid.uuid4())[:8],
                    "data": str(data_med),
                    "hora": hora_med,
                    "sistolica": sistolica,
                    "diastolica": diastolica,
                    "pulso": pulso,
                    "momento": momento,
                    "sintomas": sintomas,
                    "braco": braco,
                    "posicao": posicao,
                    "repeticao": repeticao,
                    "exercicio_antes": exercicio,
                    "estimulantes": estimulantes,
                    "profissional": profissional,
                    "obs": obs,
                    "classificacao": cls_calc,
                }
                if edit_data:
                    editar_registro(aluno_id, eid, payload)
                    st.session_state.pop(_chave(aluno_id, "editar_id"), None)
                    st.success("Registro atualizado com sucesso!")
                else:
                    salvar_registro(aluno_id, payload)
                    st.success(f"Registro salvo! Classificação: {_CLS[cls_calc]['label']}")
                st.rerun()

    with col_card:
        st.markdown("<p class='pa-secao'>Classificação em Tempo Real</p>", unsafe_allow_html=True)
        _render_card_classificacao(sistolica, diastolica, pulso)
        _render_conduta(cls_calc, sintomas if 'sintomas' in dir() else [])
        _render_legenda()

        with st.expander("📚 Guia de Medição Correta", expanded=False):
            st.markdown("""
            <div class='pa-edu-box'>
            <strong>🫀 Sistólica</strong> — pressão quando o coração <em>bombeia</em> o sangue.
            Representa o pico de pressão nas artérias.<br><br>
            <strong>🫀 Diastólica</strong> — pressão quando o coração <em>relaxa</em> entre os batimentos.
            Representa a pressão mínima nas artérias.<br><br>
            <strong>💓 Pulso</strong> — número de batimentos cardíacos por minuto.
            Normal em adultos: 60–100 bpm em repouso.<br><br>
            <strong>✅ Para medir corretamente:</strong><br>
            • Aluno sentado, costas apoiadas, pés no chão<br>
            • Braço ao nível do coração, sem tensão<br>
            • 5 min de repouso antes da medição<br>
            • Sem falar durante a aferição<br>
            • Evitar café, cigarro e exercício por 30 min antes
            </div>""", unsafe_allow_html=True)

        with st.expander("📊 Tabela de Classificação (AHA)", expanded=False):
            st.markdown("""
            <div style='font-size:12px;'>
            <table style='width:100%;border-collapse:collapse;'>
              <tr style='background:#1976D2;color:#fff;'>
                <th style='padding:6px 8px;text-align:left;border-radius:4px 0 0 0;'>Categoria</th>
                <th style='padding:6px;text-align:center;'>Sistólica</th>
                <th style='padding:6px;text-align:center;'>Diastólica</th>
              </tr>
              <tr style='background:#E3F2FD;'>
                <td style='padding:5px 8px;font-weight:700;color:#1565C0;'>🔵 Normal</td>
                <td style='padding:5px;text-align:center;'>&lt; 120</td>
                <td style='padding:5px;text-align:center;'>e &lt; 80</td>
              </tr>
              <tr style='background:#FFFDE7;'>
                <td style='padding:5px 8px;font-weight:700;color:#F57F17;'>🟡 Elevada</td>
                <td style='padding:5px;text-align:center;'>120–129</td>
                <td style='padding:5px;text-align:center;'>e &lt; 80</td>
              </tr>
              <tr style='background:#FFF3E0;'>
                <td style='padding:5px 8px;font-weight:700;color:#E64A19;'>🟠 Estágio 1</td>
                <td style='padding:5px;text-align:center;'>130–139</td>
                <td style='padding:5px;text-align:center;'>ou 80–89</td>
              </tr>
              <tr style='background:#FFEBEE;'>
                <td style='padding:5px 8px;font-weight:700;color:#C62828;'>🔴 Estágio 2</td>
                <td style='padding:5px;text-align:center;'>≥ 140</td>
                <td style='padding:5px;text-align:center;'>ou ≥ 90</td>
              </tr>
              <tr style='background:#FFEBEE;'>
                <td style='padding:5px 8px;font-weight:700;color:#7F0000;'>💥 Crise</td>
                <td style='padding:5px;text-align:center;'>&gt; 180</td>
                <td style='padding:5px;text-align:center;'>e/ou &gt; 120</td>
              </tr>
            </table>
            <p style='margin:6px 0 0 0;color:#64748B;font-size:11px;'>
              Fonte: American Heart Association (AHA). Quando sistólica e diastólica
              se enquadram em categorias diferentes, prevalece a mais grave.
            </p>
            </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# HISTÓRICO
# ──────────────────────────────────────────────────────────────────────────────
def renderizar_historico(aluno_id):
    _init_historico(aluno_id)
    hist = st.session_state.get(_chave(aluno_id, "hist"), [])

    st.markdown("<p class='pa-secao' style='margin-top:16px;'>📋 Histórico de Medições</p>", unsafe_allow_html=True)

    if not hist:
        st.info("Nenhuma medição registrada ainda.")
        return

    with st.expander("🔍 Filtros", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns([1.2, 1.2, 1.2, 1.2])
        hoje = datetime.date.today()
        f_ini = fc1.date_input("De", value=hoje - datetime.timedelta(days=365),
                               key=f"paf_ini_{aluno_id}")
        f_fim = fc2.date_input("Até", value=hoje, key=f"paf_fim_{aluno_id}")
        f_cls = fc3.selectbox("Classificação", ["Todas", "Normal", "Elevada",
                               "Estágio 1", "Estágio 2", "Crise"],
                              key=f"paf_cls_{aluno_id}")
        f_mom = fc4.selectbox("Momento",
                              ["Todos", "Antes da aula", "Depois da aula", "Em repouso", "Outro"],
                              key=f"paf_mom_{aluno_id}")

    filtrado = filtrar_historico(hist, f_ini, f_fim, f_cls, f_mom)

    st.caption(f"{len(filtrado)} registro(s) encontrado(s)")

    if not filtrado:
        st.warning("Nenhum registro encontrado com os filtros selecionados.")
        return

    for reg in filtrado:
        cls = reg.get("classificacao", "normal")
        info = _CLS.get(cls, _CLS["normal"])
        is_crise = cls == "crise"
        row_cls = "pa-hist-critico" if is_crise else "pa-hist-row"
        bdg_cls = "pa-crise-badge" if is_crise else ""

        sint_str  = ", ".join(reg.get("sintomas", []) or ["—"])
        data_fmt  = reg.get("data", "")
        try:
            data_fmt = datetime.date.fromisoformat(reg["data"]).strftime("%d/%m/%Y")
        except Exception:
            pass

        ex_str  = "Sim" if reg.get("exercicio_antes") else "Não"
        est_str = "Sim" if reg.get("estimulantes")    else "Não"

        with st.container():
            st.markdown(f"""
            <div class='{row_cls}'>
              <div style='display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:8px;'>
                <div>
                  <span style='font-size:1.15rem;font-weight:900;color:{info["cor"]};'>
                    {reg.get("sistolica","—")}/{reg.get("diastolica","—")} mmHg
                  </span>
                  <span style='font-size:13px;color:#64748B;margin-left:8px;'>
                    💓 {reg.get("pulso","—")} bpm
                  </span>
                </div>
                <span class='pa-badge {bdg_cls}' style='background:{info["badge_bg"]};'>
                  {info["icone"]} {info["label"]}
                </span>
              </div>
              <div style='display:flex;flex-wrap:wrap;gap:16px;margin-top:8px;'>
                <span><span class='pa-info-label'>Data</span><br>
                  <span class='pa-info-val'>{data_fmt} {reg.get("hora","")}</span></span>
                <span><span class='pa-info-label'>Momento</span><br>
                  <span class='pa-info-val'>{reg.get("momento","—")}</span></span>
                <span><span class='pa-info-label'>Braço / Posição</span><br>
                  <span class='pa-info-val'>{reg.get("braco","—")} / {reg.get("posicao","—")}</span></span>
                <span><span class='pa-info-label'>Aferição</span><br>
                  <span class='pa-info-val'>{reg.get("repeticao","—")}</span></span>
                <span><span class='pa-info-label'>Exercício antes</span><br>
                  <span class='pa-info-val'>{ex_str}</span></span>
                <span><span class='pa-info-label'>Estimulantes</span><br>
                  <span class='pa-info-val'>{est_str}</span></span>
              </div>
              <div style='margin-top:6px;display:flex;flex-wrap:wrap;gap:16px;'>
                <span><span class='pa-info-label'>Sintomas</span><br>
                  <span class='pa-info-val' style='color:{"#C62828" if "Sem" not in sint_str else "#059669"};'>
                    {sint_str}
                  </span></span>
                <span><span class='pa-info-label'>Profissional</span><br>
                  <span class='pa-info-val'>{reg.get("profissional","—")}</span></span>
              </div>""" + (f"""
              <div style='margin-top:4px;'>
                <span class='pa-info-label'>Obs:</span>
                <span class='pa-info-val' style='font-weight:400;color:#475569;'>
                  {reg.get("obs","—")}
                </span>
              </div>""" if reg.get("obs") else "") + """
            </div>""", unsafe_allow_html=True)

            act1, act2, act3 = st.columns([1, 1, 6])
            with act1:
                if st.button("✏️", key=f"pa_edit_{reg['id']}_{aluno_id}",
                             help="Editar registro", use_container_width=True):
                    st.session_state[_chave(aluno_id, "editar_id")] = reg["id"]
                    st.rerun()
            with act2:
                if st.button("🗑️", key=f"pa_del_{reg['id']}_{aluno_id}",
                             help="Excluir registro", use_container_width=True):
                    excluir_registro(aluno_id, reg["id"])
                    st.toast("Registro excluído.", icon="🗑️")
                    st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
def renderizar_aba_pressao_arterial(aluno, email_usuario=""):
    """Renderiza a aba completa de pressão arterial no prontuário do aluno."""
    st.markdown(_CSS, unsafe_allow_html=True)

    aluno_id  = str(aluno.get("id", "demo"))
    nome      = aluno.get("nome", "Aluno")

    # Armazena nome para uso interno em salvar_registro
    st.session_state[f"pa_nome_{aluno_id}"] = nome

    # Verificar disponibilidade do banco
    if not _DB_PA_OK:
        st.warning("⚠️ Banco de dados indisponível. Os registros serão perdidos ao encerrar a sessão.")
    elif not _tabela_pa_existe():
        st.error("⚠️ Tabela `registros_pa` ainda não existe no banco de dados.")
        with st.expander("🛠️ SQL para criar — copie e execute no Supabase SQL Editor", expanded=True):
            st.code(SQL_CRIAR_REGISTROS_PA, language="sql")
        return

    _init_historico(aluno_id)

    st.markdown(f"""
    <div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;
                gap:8px;margin-bottom:12px;'>
      <div>
        <p class='pa-titulo'>🩺 Pressão Arterial — {nome}</p>
        <p style='font-size:12px;color:#64748B;margin:0;'>
          Monitoramento cardiovascular periódico · Classificação automática (AHA Guidelines)
        </p>
      </div>
    </div>""", unsafe_allow_html=True)

    _render_formulario(aluno_id, email_usuario)

    st.divider()

    renderizar_historico(aluno_id)
