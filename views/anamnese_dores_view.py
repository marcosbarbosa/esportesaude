# ==============================================================================
# 🩻 Módulo: Mapa Corporal de Dores — Anamnese Visual
# ==============================================================================
import streamlit as st
import datetime
import json

from database import (
    salvar_anamnese_dores,
    buscar_historico_dores,
    excluir_anamnese_dores,
    ADMIN_MASTER,
)

# ──────────────────────────────────────────────────────────────────────────────
# DEFINIÇÃO DAS REGIÕES CORPORAIS
# Cada região: label (nome exibido), view (frente/costas), shape (cx,cy,rx,ry)
# Convenção: Esq/Dir = lado do PACIENTE (sua esquerda/direita)
# ──────────────────────────────────────────────────────────────────────────────
REGIOES = {
    # ── FRENTE ────────────────────────────────────────────────────────────────
    "f_cabeca":      {"label": "Cabeça",            "view": "frente", "cx": 60,  "cy": 21,  "rx": 16, "ry": 16},
    "f_pescoco":     {"label": "Pescoço",            "view": "frente", "cx": 60,  "cy": 45,  "rx":  9, "ry":  8},
    "f_ombro_e":     {"label": "Ombro Esq.",         "view": "frente", "cx": 23,  "cy": 63,  "rx": 12, "ry":  9},
    "f_ombro_d":     {"label": "Ombro Dir.",         "view": "frente", "cx": 97,  "cy": 63,  "rx": 12, "ry":  9},
    "f_braco_e":     {"label": "Braço Esq.",         "view": "frente", "cx": 18,  "cy": 80,  "rx":  7, "ry": 17},
    "f_braco_d":     {"label": "Braço Dir.",         "view": "frente", "cx": 102, "cy": 80,  "rx":  7, "ry": 17},
    "f_cotovelo_e":  {"label": "Cotovelo Esq.",      "view": "frente", "cx": 17,  "cy": 101, "rx":  7, "ry":  7},
    "f_cotovelo_d":  {"label": "Cotovelo Dir.",      "view": "frente", "cx": 103, "cy": 101, "rx":  7, "ry":  7},
    "f_antebraco_e": {"label": "Antebraço Esq.",     "view": "frente", "cx": 17,  "cy": 118, "rx":  6, "ry": 13},
    "f_antebraco_d": {"label": "Antebraço Dir.",     "view": "frente", "cx": 103, "cy": 118, "rx":  6, "ry": 13},
    "f_punho_e":     {"label": "Punho Esq.",         "view": "frente", "cx": 17,  "cy": 134, "rx":  6, "ry":  6},
    "f_punho_d":     {"label": "Punho Dir.",         "view": "frente", "cx": 103, "cy": 134, "rx":  6, "ry":  6},
    "f_peitoral":    {"label": "Peitoral",           "view": "frente", "cx": 60,  "cy": 70,  "rx": 18, "ry": 12},
    "f_abdomen":     {"label": "Abdômen",            "view": "frente", "cx": 60,  "cy": 96,  "rx": 16, "ry": 13},
    "f_quadril_e":   {"label": "Quadril Esq.",       "view": "frente", "cx": 40,  "cy": 125, "rx": 11, "ry":  9},
    "f_quadril_d":   {"label": "Quadril Dir.",       "view": "frente", "cx": 80,  "cy": 125, "rx": 11, "ry":  9},
    "f_coxa_e":      {"label": "Coxa Esq.",          "view": "frente", "cx": 45,  "cy": 157, "rx": 12, "ry": 20},
    "f_coxa_d":      {"label": "Coxa Dir.",          "view": "frente", "cx": 75,  "cy": 157, "rx": 12, "ry": 20},
    "f_joelho_e":    {"label": "Joelho Esq.",        "view": "frente", "cx": 45,  "cy": 188, "rx": 11, "ry":  8},
    "f_joelho_d":    {"label": "Joelho Dir.",        "view": "frente", "cx": 75,  "cy": 188, "rx": 11, "ry":  8},
    "f_canela_e":    {"label": "Canela Esq.",        "view": "frente", "cx": 45,  "cy": 208, "rx":  9, "ry": 13},
    "f_canela_d":    {"label": "Canela Dir.",        "view": "frente", "cx": 75,  "cy": 208, "rx":  9, "ry": 13},
    "f_tornozelo_e": {"label": "Tornozelo Esq.",     "view": "frente", "cx": 44,  "cy": 228, "rx":  8, "ry":  6},
    "f_tornozelo_d": {"label": "Tornozelo Dir.",     "view": "frente", "cx": 76,  "cy": 228, "rx":  8, "ry":  6},
    "f_pe_e":        {"label": "Pé Esq. (dorso)",   "view": "frente", "cx": 43,  "cy": 239, "rx": 14, "ry":  5},
    "f_pe_d":        {"label": "Pé Dir. (dorso)",   "view": "frente", "cx": 77,  "cy": 239, "rx": 14, "ry":  5},
    # ── COSTAS ────────────────────────────────────────────────────────────────
    "c_nuca":          {"label": "Nuca",               "view": "costas", "cx": 60,  "cy": 45,  "rx":  9, "ry":  8},
    "c_trapezio_e":    {"label": "Trapézio Esq.",      "view": "costas", "cx": 37,  "cy": 63,  "rx": 14, "ry":  8},
    "c_trapezio_d":    {"label": "Trapézio Dir.",      "view": "costas", "cx": 83,  "cy": 63,  "rx": 14, "ry":  8},
    "c_dorsal_e":      {"label": "Dorsal Esq.",        "view": "costas", "cx": 47,  "cy": 84,  "rx": 12, "ry": 17},
    "c_dorsal_d":      {"label": "Dorsal Dir.",        "view": "costas", "cx": 73,  "cy": 84,  "rx": 12, "ry": 17},
    "c_lombar":        {"label": "Lombar",             "view": "costas", "cx": 60,  "cy": 108, "rx": 17, "ry": 11},
    "c_gluteo_e":      {"label": "Glúteo Esq.",        "view": "costas", "cx": 43,  "cy": 126, "rx": 13, "ry": 11},
    "c_gluteo_d":      {"label": "Glúteo Dir.",        "view": "costas", "cx": 77,  "cy": 126, "rx": 13, "ry": 11},
    "c_pcoxa_e":       {"label": "Post. Coxa Esq.",    "view": "costas", "cx": 45,  "cy": 157, "rx": 12, "ry": 20},
    "c_pcoxa_d":       {"label": "Post. Coxa Dir.",    "view": "costas", "cx": 75,  "cy": 157, "rx": 12, "ry": 20},
    "c_joelho_e":      {"label": "Joelho Post. Esq.",  "view": "costas", "cx": 45,  "cy": 188, "rx": 11, "ry":  8},
    "c_joelho_d":      {"label": "Joelho Post. Dir.",  "view": "costas", "cx": 75,  "cy": 188, "rx": 11, "ry":  8},
    "c_panturrilha_e": {"label": "Panturrilha Esq.",   "view": "costas", "cx": 45,  "cy": 208, "rx": 10, "ry": 14},
    "c_panturrilha_d": {"label": "Panturrilha Dir.",   "view": "costas", "cx": 75,  "cy": 208, "rx": 10, "ry": 14},
    "c_calcanhar_e":   {"label": "Calcanhar Esq.",     "view": "costas", "cx": 43,  "cy": 232, "rx":  9, "ry":  6},
    "c_calcanhar_d":   {"label": "Calcanhar Dir.",     "view": "costas", "cx": 77,  "cy": 232, "rx":  9, "ry":  6},
}

GRUPOS = {
    "🧠 Cabeça e Pescoço":             ["f_cabeca", "f_pescoco", "c_nuca"],
    "💪 Membros Superiores Esquerdos": ["f_ombro_e", "f_braco_e", "f_cotovelo_e", "f_antebraco_e", "f_punho_e"],
    "💪 Membros Superiores Direitos":  ["f_ombro_d", "f_braco_d", "f_cotovelo_d", "f_antebraco_d", "f_punho_d"],
    "🫁 Tronco — Frente":              ["f_peitoral", "f_abdomen"],
    "🔙 Tronco — Costas":             ["c_trapezio_e", "c_trapezio_d", "c_dorsal_e", "c_dorsal_d", "c_lombar"],
    "🍑 Quadril e Glúteos":            ["f_quadril_e", "f_quadril_d", "c_gluteo_e", "c_gluteo_d"],
    "🦵 Membros Inferiores Esquerdos": ["f_coxa_e", "f_joelho_e", "f_canela_e", "f_tornozelo_e", "f_pe_e",
                                        "c_pcoxa_e", "c_joelho_e", "c_panturrilha_e", "c_calcanhar_e"],
    "🦵 Membros Inferiores Direitos":  ["f_coxa_d", "f_joelho_d", "f_canela_d", "f_tornozelo_d", "f_pe_d",
                                        "c_pcoxa_d", "c_joelho_d", "c_panturrilha_d", "c_calcanhar_d"],
}

INTENSIDADE_COR = {
    1: ("rgba(250,204,21,0.70)",  "#92400E", "🟡 Leve"),
    2: ("rgba(249,115,22,0.75)",  "#7C2D12", "🟠 Moderada"),
    3: ("rgba(220,38,38,0.80)",   "#7F1D1D", "🔴 Intensa"),
}

# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DO SVG DO CORPO HUMANO
# ──────────────────────────────────────────────────────────────────────────────
_BODY_OUTLINE = """
  <!-- Cabeça -->
  <circle cx="60" cy="21" r="18" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.5"/>
  <!-- Pescoço -->
  <rect x="53" y="38" width="14" height="13" rx="4" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Torso -->
  <rect x="34" y="50" width="52" height="72" rx="7" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.5"/>
  <!-- Pelvis -->
  <rect x="31" y="118" width="58" height="22" rx="10" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.2"/>
  <!-- Ombro esq -->
  <ellipse cx="24" cy="62" rx="12" ry="10" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Ombro dir -->
  <ellipse cx="96" cy="62" rx="12" ry="10" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Braço esq -->
  <rect x="11" y="54" width="14" height="46" rx="7" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Braço dir -->
  <rect x="95" y="54" width="14" height="46" rx="7" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Antebraço esq -->
  <rect x="11" y="102" width="13" height="38" rx="6" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Antebraço dir -->
  <rect x="96" y="102" width="13" height="38" rx="6" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Mão esq -->
  <ellipse cx="17" cy="148" rx="9" ry="7" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Mão dir -->
  <ellipse cx="103" cy="148" rx="9" ry="7" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Coxa esq -->
  <rect x="33" y="135" width="24" height="51" rx="10" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.2"/>
  <!-- Coxa dir -->
  <rect x="63" y="135" width="24" height="51" rx="10" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.2"/>
  <!-- Joelho esq -->
  <ellipse cx="45" cy="188" rx="13" ry="9" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Joelho dir -->
  <ellipse cx="75" cy="188" rx="13" ry="9" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Perna esq -->
  <rect x="33" y="194" width="24" height="42" rx="9" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.2"/>
  <!-- Perna dir -->
  <rect x="63" y="194" width="24" height="42" rx="9" fill="#D8DEE9" stroke="#8896A8" stroke-width="1.2"/>
  <!-- Pé esq -->
  <ellipse cx="44" cy="239" rx="15" ry="6" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
  <!-- Pé dir -->
  <ellipse cx="76" cy="239" rx="15" ry="6" fill="#D8DEE9" stroke="#8896A8" stroke-width="1"/>
"""


def _gerar_zonas_svg(view: str, regioes_sel: list, intensidades: dict) -> str:
    """Retorna os elementos SVG das zonas de dor ativas para uma view."""
    partes = []
    for rid, reg in REGIOES.items():
        if reg["view"] != view or rid not in regioes_sel:
            continue
        intens = intensidades.get(rid, 2)
        fill, stroke_c, _ = INTENSIDADE_COR.get(intens, INTENSIDADE_COR[2])
        cx, cy, rx, ry = reg["cx"], reg["cy"], reg["rx"], reg["ry"]
        partes.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke_c}" stroke-width="1.5">'
            f'<title>{reg["label"]}</title></ellipse>'
        )
    return "\n".join(partes)


def _svg_view(titulo: str, view: str, regioes_sel: list, intensidades: dict) -> str:
    zonas = _gerar_zonas_svg(view, regioes_sel, intensidades)
    return f"""
      <div style="text-align:center;">
        <div style="font-weight:700;font-size:13px;color:#334155;
                    margin-bottom:6px;letter-spacing:.5px;">{titulo}</div>
        <svg width="200" height="420" viewBox="0 0 120 250"
             style="border-radius:12px;background:#F8FAFC;
                    box-shadow:0 2px 8px rgba(0,0,0,.10);">
          {_BODY_OUTLINE}
          {zonas}
        </svg>
      </div>
    """


def render_mapa_corporal(regioes_sel: list, intensidades: dict, height: int = 480):
    """Renderiza o mapa corporal completo (frente + costas) via HTML."""
    frente_svg = _svg_view("▶ FRENTE", "frente", regioes_sel, intensidades)
    costas_svg = _svg_view("◀ COSTAS", "costas", regioes_sel, intensidades)

    legenda_items = []
    for nivel, (fill, _, rotulo) in INTENSIDADE_COR.items():
        legenda_items.append(
            f'<span style="background:{fill};color:#1e293b;'
            f'padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">'
            f'{rotulo}</span>'
        )
    legenda = " &nbsp; ".join(legenda_items)

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;">
      <div style="display:flex;gap:32px;justify-content:center;align-items:flex-start;">
        {frente_svg}
        {costas_svg}
      </div>
      <div style="text-align:center;margin-top:10px;display:flex;
                  gap:10px;justify-content:center;flex-wrap:wrap;">
        {legenda}
      </div>
      <p style="text-align:center;font-size:11px;color:#94A3B8;margin-top:6px;">
        Esq. / Dir. = lado do <b>paciente</b>
      </p>
    </div>
    """
    st.components.v1.html(html, height=height, scrolling=False)


# ──────────────────────────────────────────────────────────────────────────────
# SELETOR DE REGIÕES + INTENSIDADE
# ──────────────────────────────────────────────────────────────────────────────
def _inicializar_estado(prefix: str):
    if f"{prefix}_regioes" not in st.session_state:
        st.session_state[f"{prefix}_regioes"] = []
    if f"{prefix}_intensidades" not in st.session_state:
        st.session_state[f"{prefix}_intensidades"] = {}


def render_seletor_regioes(prefix: str = "dor_nova") -> tuple:
    """
    Renderiza os multiselects organizados por grupo.
    Retorna (regioes_selecionadas: list[str], intensidades: dict[str, int]).
    """
    _inicializar_estado(prefix)
    regioes_sel = list(st.session_state[f"{prefix}_regioes"])
    intensidades = dict(st.session_state[f"{prefix}_intensidades"])

    st.markdown("##### Selecione as regiões com dor")
    st.caption("Marque todos os locais que o aluno reporta dor ou desconforto.")

    cols = st.columns(2)
    grupos_lista = list(GRUPOS.items())
    metade = (len(grupos_lista) + 1) // 2

    mudou = False
    for col_idx, col in enumerate(cols):
        with col:
            for grp_nome, grp_ids in grupos_lista[col_idx * metade:(col_idx + 1) * metade]:
                opcoes = {REGIOES[rid]["label"]: rid for rid in grp_ids}
                selecionados_labels = [
                    REGIOES[rid]["label"] for rid in grp_ids if rid in regioes_sel
                ]
                novos_labels = st.multiselect(
                    grp_nome,
                    options=list(opcoes.keys()),
                    default=selecionados_labels,
                    key=f"{prefix}_ms_{grp_nome}",
                    label_visibility="visible",
                )
                novos_ids = [opcoes[l] for l in novos_labels]
                # Adicionar/remover regiões
                for rid in grp_ids:
                    if rid in novos_ids and rid not in regioes_sel:
                        regioes_sel.append(rid)
                        intensidades.setdefault(rid, 2)
                        mudou = True
                    elif rid not in novos_ids and rid in regioes_sel:
                        regioes_sel.remove(rid)
                        intensidades.pop(rid, None)
                        mudou = True

    if mudou:
        st.session_state[f"{prefix}_regioes"] = regioes_sel
        st.session_state[f"{prefix}_intensidades"] = intensidades

    # Seletor de intensidade por região ativa
    if regioes_sel:
        st.markdown("---")
        st.markdown("##### Intensidade por região")
        st.caption("Ajuste a intensidade de cada local marcado.")
        intens_cols = st.columns(min(len(regioes_sel), 4))
        for idx, rid in enumerate(regioes_sel):
            with intens_cols[idx % 4]:
                label_reg = REGIOES[rid]["label"]
                intens_atual = intensidades.get(rid, 2)
                opcoes_intens = {v[2]: k for k, v in INTENSIDADE_COR.items()}
                label_atual = INTENSIDADE_COR[intens_atual][2]
                escolha = st.selectbox(
                    label_reg,
                    options=list(opcoes_intens.keys()),
                    index=list(opcoes_intens.keys()).index(label_atual),
                    key=f"{prefix}_int_{rid}",
                )
                novo_nivel = opcoes_intens[escolha]
                if novo_nivel != intensidades.get(rid):
                    intensidades[rid] = novo_nivel
                    st.session_state[f"{prefix}_intensidades"] = intensidades

    return regioes_sel, intensidades


# ──────────────────────────────────────────────────────────────────────────────
# RENDERIZA HISTÓRICO EM MODO LEITURA
# ──────────────────────────────────────────────────────────────────────────────
def _render_historico(aluno_id: str, email_usuario: str):
    historico = buscar_historico_dores(aluno_id)
    if not historico:
        st.info("Nenhum mapa de dores registado para este aluno.")
        return

    opcoes = {}
    for h in historico:
        try:
            dt = datetime.date.fromisoformat(str(h["data_avaliacao"]))
            label = dt.strftime("%d/%m/%Y")
        except Exception:
            label = str(h["data_avaliacao"])
        regioes = h.get("regioes") or []
        n = len(regioes)
        opcoes[f"📅 {label}  —  {n} região(ões) marcada(s)"] = h

    escolha = st.selectbox(
        "Selecione uma avaliação para visualizar:",
        options=list(opcoes.keys()),
        key="hist_dores_sel",
    )
    reg = opcoes[escolha]
    regioes = reg.get("regioes") or []
    intensidades = reg.get("intensidade") or {}
    if isinstance(intensidades, str):
        try:
            intensidades = json.loads(intensidades)
        except Exception:
            intensidades = {}
    intensidades = {k: int(v) for k, v in intensidades.items()}

    # Mapa visual (leitura)
    render_mapa_corporal(regioes, intensidades)

    # Detalhes
    if regioes:
        st.markdown("**Regiões marcadas:**")
        badges = []
        for rid in regioes:
            label = REGIOES.get(rid, {}).get("label", rid)
            nivel = intensidades.get(rid, 2)
            fill, _, rotulo_n = INTENSIDADE_COR.get(nivel, INTENSIDADE_COR[2])
            badges.append(
                f"<span style='background:{fill};color:#1e293b;"
                f"padding:2px 10px;border-radius:12px;font-size:12px;"
                f"font-weight:600;margin:2px;display:inline-block;'>"
                f"{label} {rotulo_n}</span>"
            )
        st.markdown(" ".join(badges), unsafe_allow_html=True)

    obs = (reg.get("observacoes") or "").strip()
    if obs:
        st.markdown(f"**Observações:** {obs}")

    criado_por = (reg.get("criado_por") or "").strip()
    if criado_por:
        st.caption(f"Registado por: {criado_por}")

    # Excluir (somente ADMIN_MASTER)
    if email_usuario.lower() == ADMIN_MASTER.lower():
        st.markdown("---")
        with st.expander("🗑️ Excluir esta avaliação", expanded=False):
            st.warning("Esta ação não pode ser desfeita.")
            if st.button("✅ Confirmar exclusão", key=f"del_dor_{reg['id']}", type="primary"):
                ok, msg = excluir_anamnese_dores(reg["id"])
                if ok:
                    st.toast("Avaliação excluída.", icon="🗑️")
                    st.rerun()
                else:
                    st.error(msg)


# ──────────────────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
def render_aba_mapa_dores(aluno: dict, email_usuario: str = ""):
    aluno_id = str(aluno.get("id", ""))
    nome_aluno = aluno.get("nome", "Aluno")

    st.markdown("#### 🩻 Mapa Corporal de Dores")
    st.caption(
        "Registe as regiões onde o aluno reporta dor ou desconforto. "
        "As manchas coloridas aparecem automaticamente no corpo humano conforme a seleção."
    )

    aba_nova, aba_hist = st.tabs(["➕ Nova Avaliação", "📋 Histórico de Dores"])

    # ── NOVA AVALIAÇÃO ────────────────────────────────────────────────────────
    with aba_nova:
        prefix = f"dor_{aluno_id}"
        _inicializar_estado(prefix)

        col_mapa, col_form = st.columns([1, 1], gap="large")

        with col_form:
            data_aval = st.date_input(
                "📅 Data da avaliação",
                value=datetime.date.today(),
                key=f"{prefix}_data",
                format="DD/MM/YYYY",
            )

            regioes_sel, intensidades = render_seletor_regioes(prefix)

            st.markdown("---")
            obs = st.text_area(
                "💬 Observações clínicas",
                placeholder="Descreva o contexto, início das dores, situações que agravam, etc.",
                key=f"{prefix}_obs",
                height=110,
            )

            n_regioes = len(regioes_sel)
            btn_label = (
                f"💾 Salvar mapa ({n_regioes} região{'ões' if n_regioes != 1 else ''})"
                if n_regioes else "💾 Salvar mapa"
            )
            if st.button(btn_label, type="primary", key=f"{prefix}_salvar",
                         use_container_width=True, disabled=n_regioes == 0):
                ok, msg = salvar_anamnese_dores(
                    aluno_id=aluno_id,
                    data_avaliacao=data_aval,
                    regioes=regioes_sel,
                    intensidade=intensidades,
                    observacoes=obs.strip(),
                    criado_por=email_usuario,
                )
                if ok:
                    st.toast("Mapa de dores salvo! 🩻", icon="✅")
                    # Limpa o estado para nova avaliação
                    st.session_state[f"{prefix}_regioes"] = []
                    st.session_state[f"{prefix}_intensidades"] = {}
                    st.rerun()
                else:
                    st.error(msg)

            if n_regioes == 0:
                st.caption("Selecione ao menos uma região para habilitar o botão.")

        with col_mapa:
            render_mapa_corporal(regioes_sel, intensidades)

    # ── HISTÓRICO ─────────────────────────────────────────────────────────────
    with aba_hist:
        _render_historico(aluno_id, email_usuario)
