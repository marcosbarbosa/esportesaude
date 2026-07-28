# ==============================================================================
# 📄 ARQUIVO: modulos_frequencia/tab_tablet.py
# 🏷️ VERSÃO: 32.2.1 (PRIME GOLD - Tablet Grid 8 Colunas)
# 🔢 LINHAS (aprox.): atualizar manualmente após grandes mudanças
# 🧩 FUNÇÕES PRINCIPAIS:
#   - atualizar_status_presenca_3_estados(aluno_id, data_aula, novo_status)
#       Sincroniza no Supabase os três estados de frequência (AUSENTE / PRESENTE / JUSTIFICADA).
#   - cycle_presence_btn(aluno_id, data_aula, status_atual, nome_aluno)
#       Gira o ciclo de presença na UI e dispara o motor de atualização, com feedback via toast.
#   - renderizar_aba_terminal(df_alunos_tab, data_aula, presencas_turma_geral, bloqueio_ativo=False)
#       Monta a aba Tablet: aplica CSS de grid, calcula barra de presença, renderiza fotos, badges
#       (LGPD, atestado, avaliação, tags de saúde) e botão invisível de chamada em até 8 colunas.
# ⚙️ FUNÇÃO GLOBAL DO MÓDULO:
#   Grid visual de alunos com trava de governação de 10 dias, otimizado para operação rápida em tablet.
# ==============================================================================
import streamlit as st
import pandas as pd
from database import alternar_presenca, supabase, listar_datas_aulas_registradas


def atualizar_status_presenca_3_estados(aluno_id, data_aula, novo_status):
    """Motor injetado diretamente para lidar com os 3 estados no Supabase."""
    try:
        if novo_status == "AUSENTE":
            # Apaga o registo se a pessoa faltou sem justificativa
            supabase.table("frequencia").delete().eq("aluno_id", str(aluno_id)).eq(
                "data_aula", str(data_aula)
            ).execute()
        else:
            # Insere ou atualiza (Upsert) para PRESENTE ou JUSTIFICADA
            payload = {
                "aluno_id": str(aluno_id),
                "data_aula": str(data_aula),
                "status": novo_status,
            }
            existe = (
                supabase.table("frequencia")
                .select("id")
                .eq("aluno_id", str(aluno_id))
                .eq("data_aula", str(data_aula))
                .execute()
            )
            if hasattr(existe, "data") and len(existe.data) > 0:
                supabase.table("frequencia").update({"status": novo_status}).eq(
                    "id", existe.data[0]["id"]
                ).execute()
            else:
                supabase.table("frequencia").insert(payload).execute()

        # Invalida o cache de datas registradas para que "Dias de Aula Registrados"
        # reflita imediatamente a contagem atualizada de presenças.
        try:
            listar_datas_aulas_registradas.clear()
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"Erro frequencia 3 estados: {e}")
        return False


def cycle_presence_btn(aluno_id, data_aula, status_atual, nome_aluno):
    """Gira entre: AUSENTE -> PRESENTE -> JUSTIFICADA -> AUSENTE..."""
    if status_atual == "PRESENTE":
        novo_status = "JUSTIFICADA"
        msg, icone = "ATESTADO/JUSTIFICADA", "🟡"
    elif status_atual == "JUSTIFICADA":
        novo_status = "AUSENTE"
        msg, icone = "FALTA (DESMARCADO)", "🔴"
    else:
        novo_status = "PRESENTE"
        msg, icone = "PRESENTE", "🟢"

    if atualizar_status_presenca_3_estados(aluno_id, data_aula, novo_status):
        st.toast(f"👤 {nome_aluno.split()[0]}: {msg}", icon=icone)
    else:
        st.toast("🚨 Erro crítico de rede.", icon="🚨")


# 🚀 NOVA ASSINATURA: Agora recebe a variável bloqueio_ativo + chave_unica (data+turmas)
def renderizar_aba_terminal(
    df_alunos_tab, data_aula, presencas_turma_geral, bloqueio_ativo=False, chave_unica=""
):
    if df_alunos_tab.empty:
        st.warning("Selecione uma turma para carregar os alunos.")
        return

    # 🧼 Garante SEMPRE a ordem alfabética e um índice limpo antes de desenhar
    # qualquer célula — evita qualquer resquício de ordenação/índice de uma
    # combinação de turmas anterior "vazando" para a exibição atual.
    if "nome" in df_alunos_tab.columns:
        df_alunos_tab = df_alunos_tab.sort_values(by="nome").reset_index(drop=True)

    _chave_sanit = "".join(
        c if c.isalnum() else "_" for c in str(chave_unica)
    ) or "sem_chave"

    # O CSS encostado na margem esquerda para evitar formatação de código do Markdown
    st.markdown(
        """
<style>
    /* 🛡️ QUARENTENA CSS: Isolado apenas para a aba Tablet */
    [data-testid="stColumn"]:has(.celula-tablet) {
        position: relative !important;
    }

    /* 🔧 Ajuste fino de espaçamento para comportar até 8 colunas sem mexer na foto (150px) */
    [data-testid="stHorizontalBlock"]:has(.celula-tablet) {
        gap: 0.15rem !important;
    }
    [data-testid="stColumn"]:has(.celula-tablet) {
        padding-left: 0.10rem !important;
        padding-right: 0.10rem !important;
    }

    [data-testid="stColumn"]:has(.celula-tablet) div[data-testid="stButton"] button {
        position: absolute !important;
        top: 4px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 140% !important;
        height: 185px !important;
        min-height: 185px !important;
        max-height: 185px !important;
        z-index: 9999 !important;
        opacity: 0 !important;
        background: transparent !important;
        border: none !important;
        cursor: pointer !important;
    }

    /* ESTRUTURA VISUAL DA CÉLULA */
    .celula-tablet {
        display: flex;
        flex-direction: column;
        align-items: center;
        height: 200px;
        padding-top: 4px;
        pointer-events: none;
    }

    /* A FOTO DO ALUNO */
    .avatar-visual {
        position: relative;
        margin-top: 4px;
        width: 150px;
        height: 150px;
        border-radius: 50%;
        border: 3px solid #E2E8F0;
        background-color: #F8FAFC;
        display: flex; align-items: center; justify-content: center;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), border-color 0.3s, box-shadow 0.3s;
    }

    .img-container {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        overflow: hidden;
    }
    .img-container img { width: 100%; height: 100%; object-fit: cover; object-position: center center; }
    .avatar-visual-text { font-size: 22px; font-weight: 900; color: #94A3B8; text-transform: uppercase; text-align: center; padding: 3px; line-height: 1.1; }

    /* 🔒 CADEADO VISUAL */
    .lock-badge {
        position: absolute;
        top: -8px; right: -8px;
        background: #FEE2E2;
        border: 2px solid #EF4444;
        border-radius: 50%;
        width: 26px; height: 26px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        font-size: 13px;
        z-index: 100;
    }

    /* 🚫 LGPD */
    .lgpd-proibido {
        position: absolute;
        top: -8px; left: -8px;
        background: #1E293B;
        border: 2px solid #F59E0B;
        border-radius: 50%;
        width: 26px; height: 26px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        font-size: 13px;
        z-index: 100;
    }

    /* 🏥 ATESTADO */
    .atestado-alerta {
        position: absolute;
        bottom: -8px; left: -8px;
        background: #FFF7ED;
        border: 2px solid #F97316;
        border-radius: 50%;
        width: 26px; height: 26px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 2px 6px rgba(249,115,22,0.45);
        font-size: 13px;
        z-index: 100;
    }

    /* DISTINTIVO DE STATUS */
    .badge-status {
        position: absolute;
        top: 142px;
        left: 50%;
        transform: translateX(-50%);
        width: 28px; height: 28px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 900; font-size: 14px;
        border: 2px solid white;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), background 0.3s;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        z-index: 60;
    }

    /* NOME DO ALUNO */
    .nome-aluno {
        position: absolute;
        top: 176px;
        left: 0;
        width: 100%;
        text-align: center;
        font-size: 11px; font-weight: 900; color: #1E293B;
        text-transform: uppercase; line-height: 1.2;
        transition: all 0.4s ease-out;
        overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
    }

    /* 💬 TOOLTIP DE CONDIÇÕES — aparece no lugar do nome no hover */
    .tooltip-saude {
        position: absolute;
        top: 172px;
        left: 50%;
        transform: translateX(-50%);
        width: 148px;
        background: rgba(15,23,42,0.91);
        color: #E2E8F0;
        font-size: 9.5px;
        font-weight: 500;
        padding: 5px 7px;
        border-radius: 8px;
        text-align: center;
        line-height: 1.45;
        z-index: 99998;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease, transform 0.25s ease;
        box-shadow: 0 4px 16px rgba(0,0,0,0.45);
        letter-spacing: 0.2px;
    }

    /* 🚀 ZOOM NO HOVER — apenas 40% maior para destacar o hover */
    [data-testid="stColumn"]:has(.celula-tablet):hover .avatar-visual {
        transform: scale(1.4) !important;
        box-shadow: 0 0 0 3px #3B82F6, 0 16px 48px rgba(0,0,0,0.55);
        z-index: 99999;
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .badge-status {
        transform: translateX(-50%) translateY(40px) scale(1.2) !important;
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .nome-aluno {
        transform: translateY(12px);
        opacity: 0;
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .tooltip-saude {
        opacity: 1;
    }

    /* 🟢/🔴/🟡 ESTADOS DE PRESENÇA */
    .status-ausente .avatar-visual { border-color: #CBD5E1; }
    .status-ausente .badge-status { background: #F1F5F9; color: #94A3B8; }
    .status-ausente .img-container, .status-ausente .avatar-visual-text {
        filter: brightness(0.8) grayscale(50%);
        transition: filter 0.4s ease;
    }

    .status-presente .avatar-visual { border-color: #22C55E !important; box-shadow: 0 0 12px rgba(34,197,94,0.4); }
    .status-presente .badge-status { background: #22C55E !important; color: white !important; }
    .status-presente .img-container, .status-presente .avatar-visual-text {
        filter: brightness(1) grayscale(0%);
        transition: filter 0.4s ease;
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .status-presente .avatar-visual {
        box-shadow: 0 0 0 3px #22C55E, 0 16px 48px rgba(34,197,94,0.6) !important;
    }

    .status-justificada .avatar-visual { border-color: #F59E0B !important; box-shadow: 0 0 12px rgba(245,158,11,0.35); }
    .status-justificada .badge-status { background: #F59E0B !important; color: white !important; }
    .status-justificada .img-container, .status-justificada .avatar-visual-text {
        filter: brightness(0.95) sepia(0.3) hue-rotate(-15deg);
        transition: filter 0.4s ease;
    }
    [data-testid="stColumn"]:has(.celula-tablet):hover .status-justificada .avatar-visual {
        box-shadow: 0 0 0 3px #F59E0B, 0 16px 48px rgba(245,158,11,0.6) !important;
    }
</style>
""",
        unsafe_allow_html=True,
    )

    # 📊 LÓGICA DA BARRA DE PROGRESSO (ATUALIZADA PARA 3 ESTADOS)
    total_alunos = len(df_alunos_tab)

    q_presentes = 0
    q_justificadas = 0

    for status_bd in presencas_turma_geral.values():
        if status_bd == "JUSTIFICADA":
            q_justificadas += 1
        elif status_bd == "PRESENTE" or status_bd is True:
            q_presentes += 1

    # O "Total Apto" remove os atestados da conta! É a proteção do aluno!
    total_aptos = total_alunos - q_justificadas

    if total_aptos > 0:
        razao_progresso = q_presentes / total_aptos
        percentagem = int(razao_progresso * 100)
    else:
        razao_progresso = 0.0
        percentagem = 0

    bloco_justificativas = (
        f" <span style='font-size:16px; color:#F59E0B;'>| {q_justificadas} ATESTADOS</span>"
        if q_justificadas > 0
        else ""
    )

    st.markdown(
        f"""
<div style='text-align: center; margin-bottom: 10px;'>
    <h2 style='color: #1E88E5; font-weight: 900; margin-bottom:0;'>{q_presentes} / {total_aptos} PRESENTES {bloco_justificativas}</h2>
    <span style='font-size:13px; color:#64748B;'>*Os atestados médicos não penalizam a barra de presença.</span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.progress(razao_progresso, text=f"Taxa de Presença Útil: {percentagem}%")

    # ── Filtros rápidos da grade ───────────────────────────────────────────────
    _kf_pendentes = f"filtro_pendentes_{_chave_sanit}"
    _kf_presentes = f"filtro_presentes_{_chave_sanit}"

    _kf_prontuario = f"modo_prontuario_{_chave_sanit}"
    _col_fp, _col_fs, _col_fpr, _col_fi = st.columns([3, 3, 3, 2])
    _filtro_pendentes = _col_fp.checkbox(
        "🔴 Ocultar já registrados",
        key=_kf_pendentes,
        help="Esconde alunos já marcados — mostra apenas quem falta registrar",
    )
    _filtro_presentes = _col_fs.checkbox(
        "✅ Somente presentes",
        key=_kf_presentes,
        help="Mostra apenas alunos já marcados como presentes ou justificados",
        disabled=_filtro_pendentes,
    )
    _modo_prontuario = _col_fpr.checkbox(
        "🩺 Abrir prontuário",
        key=_kf_prontuario,
        help="Ativado: clique no aluno abre o prontuário dele. Desativado: clique registra a presença.",
    )
    if _modo_prontuario:
        _col_fi.markdown(
            "<small style='color:#6366F1;font-weight:600;'>🩺 Modo prontuário ativo</small>",
            unsafe_allow_html=True,
        )

    # Conjunto de IDs já marcados (PRESENTE ou JUSTIFICADA)
    _ids_marcados = {
        aid
        for aid, st_bd in presencas_turma_geral.items()
        if st_bd in ("PRESENTE", "JUSTIFICADA") or st_bd is True
    }

    # Aplica filtro apenas no df de renderização; totais sempre refletem todos
    df_render = df_alunos_tab.copy()
    if _filtro_pendentes:
        df_render = df_render[~df_render["id"].isin(_ids_marcados)].reset_index(drop=True)
    elif _filtro_presentes:
        df_render = df_render[df_render["id"].isin(_ids_marcados)].reset_index(drop=True)

    _total_visivel = len(df_render)
    if _filtro_pendentes or _filtro_presentes:
        _rotulo = "pendentes" if _filtro_pendentes else "já registrados"
        _col_fi.markdown(
            f"<small style='color:#64748B;'>👁 Exibindo <b>{_total_visivel}</b> "
            f"de <b>{total_alunos}</b> alunos ({_rotulo})</small>",
            unsafe_allow_html=True,
        )

    # ── LEGENDA DOS ÍCONES ────────────────────────────────────────────────────
    try:
        from database import get_tags_clinicas as _gtc_leg
        _tags_leg = _gtc_leg() or []
    except Exception:
        _tags_leg = []
    if not _tags_leg:
        _tags_leg = [
            {"nome": "Hipertensão/Cardiopatia", "icone": "🫀", "cor": "#DC2626"},
            {"nome": "Artrose/Artrite",          "icone": "🦴", "cor": "#D97706"},
        ]

    _itens_leg = [
        ("✓",  "#22C55E", "Presente"),
        ("X",  "#94A3B8", "Ausente"),
        ("⚕️", "#F59E0B", "Justificada"),
        ("🔒", "#64748B", "Chamada bloqueada"),
        ("🚫", "#EF4444", "LGPD – sem autorização de imagem"),
        ("🏥", "#DC2626", "Atestado médico ativo"),
        ("⚡", "#F59E0B", "Reavaliação pendente"),
    ] + [(t["icone"], t.get("cor", "#6B7280"), t["nome"]) for t in _tags_leg]

    _pils = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:4px;"
        f"background:#F8FAFC;border:1px solid {cor};border-radius:20px;"
        f"padding:2px 8px 2px 6px;font-size:11px;color:#374151;white-space:nowrap;'>"
        f"<span style='font-size:12px;'>{ico}</span>"
        f"<span style='color:#6B7280;'>{label}</span></span>"
        for ico, cor, label in _itens_leg
    )
    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;gap:5px;padding:6px 2px 2px 2px;"
        f"opacity:0.85;'>{_pils}</div>",
        unsafe_allow_html=True,
    )
    # ─────────────────────────────────────────────────────────────────────────

    st.markdown("<br>", unsafe_allow_html=True)

    if df_render.empty:
        _msg = (
            "✅ Todos os alunos já foram registrados!"
            if _filtro_pendentes
            else "Nenhum aluno marcado como presente ainda."
        )
        st.info(_msg)
        return

    # ==============================================================================
    # 🖼️ RENDERIZAÇÃO DOS ALUNOS (8 COLUNAS — fotos 150px)
    # ==============================================================================
    COLS = 8

    for i in range(0, _total_visivel, COLS):
        cols = st.columns(COLS, gap="small")

        for j, (_, row) in enumerate(df_render.iloc[i : i + COLS].iterrows()):
            with cols[j], st.container(key=f"cel_{_chave_sanit}_{row['id']}"):
                # 🚀 INTERPRETAÇÃO DO STATUS
                status_bd = presencas_turma_geral.get(row["id"])

                if status_bd == "JUSTIFICADA":
                    status_atual = "JUSTIFICADA"
                    status_class = "status-justificada"
                    indicador = "⚕️"
                elif status_bd == "PRESENTE" or status_bd is True:
                    status_atual = "PRESENTE"
                    status_class = "status-presente"
                    indicador = "✓"
                else:
                    status_atual = "AUSENTE"
                    status_class = "status-ausente"
                    indicador = "X"

                url_foto = str(row.get("foto_url") or "").strip()
                nome_formatado = str(row["nome"])[:16].strip()

                cadeado_html = (
                    "<div class='lock-badge'>🔒</div>" if bloqueio_ativo else ""
                )

                # 🚫 LGPD — badge superior esquerdo se não autorizou imagem
                _termo_img = row.get("termo_imagem")
                _nao_autoriza = (
                    (_termo_img is False)
                    or (_termo_img == 0)
                    or (str(_termo_img).lower() in ["false", "0", ""])
                )
                lgpd_html = (
                    "<div class='lgpd-proibido' title='LGPD: Não autoriza uso de imagem'>🚫</div>"
                    if _nao_autoriza
                    else ""
                )

                # 🏥 ATESTADO — badge inferior esquerdo + bloqueia chamada
                _atestado_bloq = bool(row.get("atestado_bloqueado"))
                atestado_html = (
                    "<div class='atestado-alerta' title='Atestado médico pendente — Participação bloqueada'>🏥</div>"
                    if _atestado_bloq
                    else ""
                )

                # 🧪 AVALIAÇÃO PENDENTE — badge inferior direito + bloqueia chamada
                _aval_pend = bool(row.get("avaliacao_pendente"))
                aval_pend_html = (
                    "<div style='position:absolute;bottom:-8px;right:-8px;"
                    "background:#FEF3C7;border:2px solid #F59E0B;border-radius:50%;"
                    "width:24px;height:24px;display:flex;align-items:center;"
                    "justify-content:center;box-shadow:0 2px 6px rgba(245,158,11,0.45);"
                    "font-size:13px;z-index:100;' title='Reavaliação pendente — Participação bloqueada'>⚡</div>"
                    if _aval_pend
                    else ""
                )

                # 🏷️ TAGS DE SAÚDE — badges clínicos dinâmicos (carregados do banco)
                _tags_raw_tab = str(row.get("tags_saude") or "")
                _tags_tab = [t.strip() for t in _tags_raw_tab.split(",") if t.strip()]
                saude_html = ""
                if _tags_tab:
                    try:
                        from database import get_tags_clinicas as _gtc_tab

                        _tags_db_tab = _gtc_tab()
                    except Exception:
                        _tags_db_tab = []
                    if not _tags_db_tab:
                        _tags_db_tab = [
                            {
                                "nome": "Hipertensão/Cardiopatia",
                                "icone": "🫀",
                                "cor": "#DC2626",
                            },
                            {
                                "nome": "Artrose/Artrite",
                                "icone": "🦴",
                                "cor": "#D97706",
                            },
                        ]
                    _tags_map_tab = {t["nome"]: t for t in _tags_db_tab}
                    _tops = [6 + i * 48 for i in range(len(_tags_tab))]
                    for _i, _tn in enumerate(_tags_tab[:3]):
                        _td = _tags_map_tab.get(_tn, {})
                        _cor_t = _td.get("cor", "#6B7280")
                        _ico_t = _td.get("icone", "🏷️")
                        _top_t = _tops[_i]
                        saude_html += (
                            f"<div style='position:absolute;top:{_top_t}px;right:-8px;"
                            f"background:#FFF;border:1.5px solid {_cor_t};border-radius:50%;"
                            f"width:22px;height:22px;display:flex;align-items:center;"
                            f"justify-content:center;font-size:13px;z-index:101;"
                            f"box-shadow:0 1px 4px rgba(0,0,0,0.2);' title='{_tn}'>"
                            f"{_ico_t}</div>"
                        )

                # Botão — comportamento bifurcado conforme modo ativo
                _botao_bloqueado = (bloqueio_ativo or _atestado_bloq or _aval_pend) and not _modo_prontuario
                if st.button(
                    " ", key=f"tbt_prod_{row['id']}", use_container_width=True,
                    disabled=_botao_bloqueado,
                ):
                    if _modo_prontuario:
                        # Abre o prontuário do aluno
                        st.session_state.aluno_prontuario = row.to_dict()
                        st.session_state.origem_prontuario = "Frequência"
                        st.session_state.menu_atual = "Portal do Aluno"
                    else:
                        # Registra presença normalmente
                        cycle_presence_btn(
                            row["id"], data_aula, status_atual, row["nome"]
                        )
                    st.rerun()

                if url_foto.startswith("http"):
                    inic_tab = "".join(
                        p[0].upper() for p in str(row["nome"]).split()[:2] if p
                    )
                    avatar_html = (
                        f'<div class="img-container">'
                        f'<img src="{url_foto}" '
                        f"onerror=\"this.parentElement.innerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;width:100%;height:100%;font-weight:900;font-size:44px;color:#fff;background:linear-gradient(135deg,#3B82F6,#06B6D4);\\'>{inic_tab}</div>'\">"
                        f"</div>"
                    )
                else:
                    inic_tab = "".join(
                        p[0].upper() for p in str(row["nome"]).split()[:2] if p
                    )
                    avatar_html = (
                        f'<div style="display:flex;align-items:center;justify-content:center;'
                        f"width:100%;height:100%;font-weight:900;font-size:44px;color:#fff;"
                        f'background:linear-gradient(135deg,#3B82F6,#06B6D4);">{inic_tab}</div>'
                    )

                # 💬 Tooltip — monta lista de condições do aluno
                _tip_itens = []
                if _nao_autoriza:
                    _tip_itens.append("🚫 LGPD")
                if _atestado_bloq:
                    _tip_itens.append("🏥 Atestado ativo")
                if _aval_pend:
                    _tip_itens.append("⚡ Reavaliação")
                if bloqueio_ativo:
                    _tip_itens.append("🔒 Chamada bloqueada")
                for _tn in _tags_tab[:5]:
                    _tip_itens.append(_tn)

                tooltip_html = ""
                if _tip_itens:
                    _tip_txt = ", ".join(_tip_itens)
                    tooltip_html = f'<div class="tooltip-saude">{_tip_txt}</div>'

                cartao_html_seguro = (
                    f'<div class="celula-tablet {status_class}">'
                    f'<div class="avatar-visual">'
                    f"{avatar_html}{cadeado_html}{lgpd_html}{atestado_html}{aval_pend_html}{saude_html}"
                    f"</div>"
                    f'<div class="badge-status">{indicador}</div>'
                    f'<div class="nome-aluno">{nome_formatado}</div>'
                    f"{tooltip_html}"
                    f"</div>"
                )

                st.markdown(cartao_html_seguro, unsafe_allow_html=True)
