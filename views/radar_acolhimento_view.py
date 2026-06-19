# ==============================================================================
# 📄 Arquivo: views/radar_acolhimento_view.py
# 🏷️ VERSÃO: 8.1 (PRO Elite - Integração Direta com Prontuário)
# ⚙️ FUNÇÃO: Radar de Evasão proativo com filtros avançados, UI Premium e Acesso à Ficha.
# ==============================================================================

import streamlit as st
import pandas as pd
import urllib.parse
import datetime
from database import supabase, buscar_aluno_por_id
from fpdf import FPDF
from utils.texto import formatar_whatsapp_numero as limpar_whatsapp_link


# ==============================================================================
# 🛠️ FUNÇÕES DE APOIO E CÁLCULO
# ==============================================================================


def calcular_dias_uteis_ausente(ultima_data, data_final):
    """Conta estritamente os dias úteis entre a última presença e hoje."""
    if pd.isna(ultima_data) or not ultima_data:
        return 9999  # Código 9999 = Nunca compareceu

    dias_uteis = 0
    dia_atual = ultima_data + datetime.timedelta(days=1)

    while dia_atual <= data_final:
        if dia_atual.weekday() < 5:
            dias_uteis += 1
        dia_atual += datetime.timedelta(days=1)

    return dias_uteis


# ==============================================================================
# 🖨️ FUNÇÃO GERADORA DE PDF — xhtml2pdf com logos, timestamp e fotos
# ==============================================================================
import re as _re
from urllib.parse import quote as _url_quote


def _limpar_whats(raw) -> str | None:
    """Devolve número somente dígitos com DDI 55 (ex: 5511999991234), ou None."""
    if not raw or str(raw).strip() in ("-", "", "None", "nan"):
        return None
    digits = _re.sub(r"\D", "", str(raw))
    if len(digits) < 8:
        return None
    if not digits.startswith("55"):
        digits = "55" + digits
    return digits


def _link_whats(numero: str, nome: str, dias: int) -> str:
    """
    Retorna HTML <a href='wa.me/...'> com mensagem de acolhimento adequada.
    - dias >= 30 → mensagem de preocupacao (ausencia longa)
    - dias <  30 → mensagem de encorajamento (ausencia moderada)
    """
    primeiro = nome.split()[0].capitalize()
    if dias != 9999 and dias >= 30:
        msg = (
            f"Ola {primeiro}! Aqui e a equipe do Instituto Muda Brasil. "
            "Notamos que faz algum tempo que voce nao aparece nas aulas e "
            "queremos saber como voce esta. "
            "Estamos aqui para apoiar voce no que for preciso para retomar "
            "sua jornada de saude e bem-estar. Podemos conversar?"
        )
    else:
        msg = (
            f"Ola {primeiro}! Aqui e a equipe do Instituto Muda Brasil. "
            "Sentimos sua falta nas aulas! "
            "Gostaríamos de saber como voce esta e se podemos ajudar de "
            "alguma forma para que retome sua rotina conosco. "
            "Estamos aqui para voce!"
        )
    url   = f"https://wa.me/{numero}?text={_url_quote(msg)}"
    label = numero[2:]  # exibe sem o +55
    return (
        f'<a href="{url}" '
        f'style="color:#25D366;font-weight:700;text-decoration:underline;">'
        f'{label}</a>'
    )


def _fetch_foto_base64(url) -> str | None:
    """Tenta buscar a foto do aluno e devolvê-la como data URL base64.
    Retorna None em caso de falha (sem foto, URL inválida, timeout)."""
    if not url or (isinstance(url, float) and pd.isna(url)):
        return None
    import urllib.request as _ur
    import base64 as _b64
    try:
        req = _ur.Request(str(url).strip(), headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=4) as resp:
            raw = resp.read()
        ext = "jpeg" if any(x in str(url).lower() for x in ("jpg", "jpeg")) else "png"
        return f"data:image/{ext};base64,{_b64.b64encode(raw).decode()}"
    except Exception:
        return None


def gerar_pdf_atrasados(lista_alunos):
    """
    Gera PDF do Radar de Evasão com xhtml2pdf.
    Inclui: cabeçalho institucional com logos, data/hora de impressão,
    mini-foto de cada aluno (90 % da célula) e rodapé.
    Regras xhtml2pdf: sem emojis no HTML, sem display:table-cell.
    """
    import io

    try:
        from xhtml2pdf import pisa
        from utils.identidade import get_config, get_logo_b64

        cfg      = get_config()
        titulo   = cfg.get("titulo_projeto", "")
        subtit   = cfg.get("subtitulo_projeto", "")
        nome_org = cfg.get("nome_organizacao", "")
        cnpj     = cfg.get("cnpj", "")
        site     = cfg.get("site", "")
        insta    = cfg.get("instagram", "")
        endereco = cfg.get("endereco", "")

        logo_p = get_logo_b64(cfg.get("logo_principal", ""))
        logo_s = get_logo_b64(cfg.get("logo_secundaria", ""))
        img_p  = (
            f'<img src="data:image/png;base64,{logo_p}" '
            f'style="max-width:100px;max-height:70px;" />'
            if logo_p else f"<b>{nome_org}</b>"
        )
        img_s  = (
            f'<img src="data:image/png;base64,{logo_s}" '
            f'style="max-width:120px;max-height:70px;" />'
            if logo_s else ""
        )

        agora      = datetime.datetime.now().strftime("%d/%m/%Y as %H:%M")
        rodape_ln  = " | ".join(
            p for p in [nome_org, f"CNPJ: {cnpj}" if cnpj else "",
                        site, insta, endereco] if p
        )

        # ── Linhas da tabela ──────────────────────────────────────────────────
        linhas = ""
        bg_alt = False
        for aluno in lista_alunos:
            nome     = str(aluno.get("nome", ""))
            turma    = str(aluno.get("turma", "N/A"))
            dias     = aluno.get("dias", 0)
            dias_str = "Sem registro" if dias == 9999 else f"{dias} dias"
            whats    = str(aluno.get("whatsapp") or "-")
            if whats in ("None", "nan"):
                whats = "-"

            num_limpo  = _limpar_whats(whats)
            whats_cell = (
                _link_whats(num_limpo, nome, dias)
                if num_limpo
                else f'<span style="color:#94A3B8;">-</span>'
            )

            data_url = _fetch_foto_base64(aluno.get("foto_url"))
            if data_url:
                foto_html = (
                    f'<img src="{data_url}" '
                    f'style="width:90%;height:auto;" />'
                )
            else:
                inicial   = nome[0].upper() if nome else "?"
                foto_html = (
                    f'<div style="width:90%;padding:8px 0;background:#E2E8F0;'
                    f'text-align:center;font-weight:900;font-size:12pt;">'
                    f'{inicial}</div>'
                )

            bg       = "background:#F8FAFC;" if bg_alt else ""
            bg_alt   = not bg_alt
            cor_dias = "#DC2626" if dias != 9999 and dias >= 14 else "#F59E0B"

            linhas += f"""
  <tr style="{bg}">
    <td style="width:9%;text-align:center;vertical-align:middle;padding:3px;">{foto_html}</td>
    <td style="width:37%;vertical-align:middle;padding:4px 6px;font-size:9pt;">{nome}</td>
    <td style="width:28%;vertical-align:middle;padding:4px 6px;font-size:8.5pt;color:#475569;">{turma}</td>
    <td style="width:13%;text-align:center;vertical-align:middle;padding:4px;font-size:9pt;font-weight:700;color:{cor_dias};">{dias_str}</td>
    <td style="width:13%;text-align:center;vertical-align:middle;padding:4px;font-size:8pt;">{whats_cell}</td>
  </tr>"""

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"/>
<style>
  body  {{ font-family: Arial, sans-serif; font-size: 9.5pt; color: #1e293b; margin: 18px 28px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
  th    {{ background: #0056b3; color: #fff; padding: 5px 8px;
           text-align: left; font-size: 8.5pt; }}
  td    {{ padding: 4px 7px; border-bottom: 1px solid #E2E8F0; vertical-align: middle; }}
  h2    {{ color: #0056b3; font-size: 10pt; border-bottom: 2px solid #0056b3;
           padding-bottom: 3px; margin-top: 14px; margin-bottom: 5px; }}
  .rod  {{ margin-top: 24px; text-align: center; font-size: 7.5pt; color: #94A3B8;
           border-top: 1px solid #E2E8F0; padding-top: 6px; }}
</style>
</head><body>

<!-- Cabecalho institucional -->
<table style="border-bottom:3px solid #0056b3;margin-bottom:14px;">
  <tr>
    <td style="width:22%;text-align:left;border-bottom:0;">{img_s}</td>
    <td style="width:56%;text-align:center;border-bottom:0;">
      <p style="margin:0;font-size:10pt;font-weight:900;color:#0A2540;">{titulo}</p>
      <p style="margin:2px 0 0;font-size:8.5pt;color:#475569;">{subtit}</p>
      <p style="margin:4px 0 0;font-size:9.5pt;font-weight:700;color:#0056b3;">
        Radar de Acolhimento e Prevencao de Evasao
      </p>
      <p style="margin:3px 0 0;font-size:7.5pt;color:#94A3B8;">Gerado em: {agora}</p>
    </td>
    <td style="width:22%;text-align:right;border-bottom:0;">{img_p}</td>
  </tr>
</table>

<!-- Tabela de alunos -->
<table>
  <thead>
    <tr>
      <th style="width:9%;">Foto</th>
      <th style="width:37%;">Nome do Aluno</th>
      <th style="width:28%;">Turma</th>
      <th style="width:13%;text-align:center;">Ausencias</th>
      <th style="width:13%;text-align:center;">WhatsApp</th>
    </tr>
  </thead>
  <tbody>
    {linhas}
  </tbody>
</table>

<div class="rod">{rodape_ln}</div>

</body></html>"""

        buf    = io.BytesIO()
        result = pisa.CreatePDF(html.encode("utf-8"), dest=buf)
        if not result.err:
            return buf.getvalue() or None

    except Exception:
        pass

    # ── Fallback FPDF (sem fotos) se xhtml2pdf falhar ────────────────────────
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial", size=14, style="B")
    pdf.cell(190, 10, "Radar de Acolhimento e Prevencao de Evasao", ln=True, align="C")
    pdf.set_font("Arial", size=9)
    pdf.cell(190, 8,
             f"Gerado em: {datetime.datetime.now().strftime('%d/%m/%Y as %H:%M')}",
             ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", size=9, style="B")
    pdf.cell(80, 8, "Nome do Aluno", border=1)
    pdf.cell(45, 8, "Turma",         border=1)
    pdf.cell(25, 8, "Ausencias",     border=1, align="C")
    pdf.cell(40, 8, "WhatsApp",      border=1, align="C")
    pdf.ln()
    pdf.set_font("Arial", size=8)
    for aluno in lista_alunos:
        dias_str = ("S/ Registo" if aluno["dias"] == 9999
                    else f"{aluno['dias']} dias")
        pdf.cell(80, 8, str(aluno.get("nome", ""))[:32],  border=1)
        pdf.cell(45, 8, str(aluno.get("turma", ""))[:20], border=1)
        pdf.cell(25, 8, dias_str, border=1, align="C")
        pdf.cell(40, 8, str(aluno.get("whatsapp", "-")),  border=1, align="C")
        pdf.ln()
    resultado = pdf.output(dest="S")
    return resultado.encode("latin1") if isinstance(resultado, str) else bytes(resultado)


# ==============================================================================
# 🖥️ TELA PRINCIPAL (FRONT-END)
# ==============================================================================
def tela_radar_acolhimento():
    # 1. 🚀 INICIALIZAÇÃO DE ESTADO (Agora com a memória da Ordem)
    if "dias_busca_radar" not in st.session_state:
        st.session_state.dias_busca_radar = 7
    if "ocultar_novatos" not in st.session_state:
        st.session_state.ocultar_novatos = True
    if "ordem_evasao" not in st.session_state:
        st.session_state.ordem_evasao = "🚨 Maior Evasão (Decrescente)"

    st.markdown("### 💙 Radar de Acolhimento e Prevenção de Evasão")
    st.write(
        "Lista automática de alunos ordenados pelos mais faltosos. O cálculo ignora sábados e domingos."
    )

    # ==========================================================================
    # 🎛️ BARRA DE FILTRO (NOVA ESTRUTURA COM SELECTBOX)
    # ==========================================================================
    with st.container(border=True):
        st.markdown("**⚙️ Configurações de Busca**")

        ocultar = st.checkbox(
            "🎒 Ocultar alunos que NUNCA vieram (Focar apenas em Evasão Real)",
            value=st.session_state.ocultar_novatos,
        )

        st.write("")

        # 2. 🚀 REDESENHO DAS COLUNAS: Inserimos um espaço para a ordem
        c_dias, c_ordem, c_btn = st.columns(
            [1.5, 1.5, 1.5], vertical_alignment="bottom"
        )

        with c_dias:
            novos_dias = st.number_input(
                "Avisar a partir de (Dias):",
                min_value=1,
                value=st.session_state.dias_busca_radar,
                step=1,
            )

        with c_ordem:
            # Opções de ordenação amigáveis
            opcoes_ordem = [
                "🚨 Maior Evasão (Decrescente)",
                "📉 Menor Evasão (Crescente)",
            ]

            # Garante que a caixa seleciona o que já estava na memória
            index_atual = (
                opcoes_ordem.index(st.session_state.ordem_evasao)
                if st.session_state.ordem_evasao in opcoes_ordem
                else 0
            )

            nova_ordem = st.selectbox(
                "Ordem da Lista:", opcoes_ordem, index=index_atual
            )

        with c_btn:
            if st.button(
                "🔍 ATUALIZAR LISTA", type="primary", use_container_width=True
            ):
                # 3. 🚀 SALVA TODAS AS PREFERÊNCIAS NA MEMÓRIA
                st.session_state.dias_busca_radar = novos_dias
                st.session_state.ocultar_novatos = ocultar
                st.session_state.ordem_evasao = nova_ordem
                st.rerun()

    # ==========================================================================
    # 💾 MOTOR DE BANCO DE DADOS
    # ==========================================================================
    try:
        res_alunos = (
            supabase.table("alunos")
            .select("id, nome, whatsapp, turma, foto_url")
            .eq("status", "Ativo")
            .execute()
        )
        df_alunos = pd.DataFrame(res_alunos.data)

        if df_alunos.empty:
            st.info("Nenhum aluno ativo encontrado para análise.")
            return

        # ── Busca paginada para superar o limite de 1000 linhas do Supabase ──
        # Sem paginação, registros recentes (>1000º) não chegam e alunos que
        # compareceram esta semana aparecem erroneamente como em evasão.
        todos_freq: list = []
        offset_freq = 0
        PAGE_F = 1000
        for _ in range(100):          # guarda: máximo 100.000 registros
            lote_r = (
                supabase.table("frequencia")
                .select("aluno_id, data_aula")
                .eq("status", "PRESENTE")
                .order("data_aula")
                .range(offset_freq, offset_freq + PAGE_F - 1)
                .execute()
            )
            lote = lote_r.data or []
            todos_freq.extend(lote)
            if len(lote) < PAGE_F:
                break
            offset_freq += PAGE_F

        df_freq = pd.DataFrame(todos_freq)

        mapa_ultimas_datas = {}
        if not df_freq.empty:
            # Regra: nunca usar pd.to_datetime direto em data_aula —
            # Supabase pode devolver "YYYY-MM-DDTHH:MM:SS+00:00"; str[:10] normaliza.
            df_freq["data_aula"] = pd.to_datetime(
                df_freq["data_aula"].astype(str).str[:10]
            ).dt.date
            mapa_ultimas_datas = (
                df_freq.groupby("aluno_id")["data_aula"].max().to_dict()
            )

        hoje = datetime.date.today()
        lista_final_evasao = []

        for _, aluno in df_alunos.iterrows():
            aluno_id = str(aluno["id"])
            ultima_presenca = mapa_ultimas_datas.get(aluno_id, None)
            dias_calculados = calcular_dias_uteis_ausente(ultima_presenca, hoje)

            if st.session_state.ocultar_novatos and dias_calculados == 9999:
                continue

            if dias_calculados >= st.session_state.dias_busca_radar:
                foto = aluno.get("foto_url")
                if pd.isna(foto) or not foto:
                    foto = None

                whats = aluno.get("whatsapp")
                if pd.isna(whats) or not whats:
                    whats = None

                turma_val = aluno.get("turma")
                if pd.isna(turma_val) or not turma_val:
                    turma_val = "N/A"

                lista_final_evasao.append(
                    {
                        "id": aluno_id,
                        "nome": str(aluno["nome"]),
                        "turma": turma_val,
                        "whatsapp": whats,
                        "foto_url": foto,
                        "dias": dias_calculados,
                        "data_ultima": ultima_presenca,
                    }
                )

        # ==========================================================================
        # 4. 🚀 A LÓGICA MÁGICA DE ORDENAÇÃO DINÂMICA
        # ==========================================================================
        # Se a opção escolhida tiver a palavra "Decrescente", o reverse é True. Se não, é False.
        ordem_reversa = (
            True if "Decrescente" in st.session_state.ordem_evasao else False
        )
        lista_final_evasao.sort(key=lambda x: x["dias"], reverse=ordem_reversa)

        # ==========================================================================
        # 🎨 RENDERIZAÇÃO DA TELA (LISTA FINAL E TAGS)
        # ==========================================================================
        if len(lista_final_evasao) == 0:
            st.success("✅ Tudo em ordem! Nenhum aluno atingiu os critérios de filtro.")
        else:
            c_titulo, c_pdf = st.columns([3, 1], vertical_alignment="bottom")
            with c_titulo:
                st.markdown(f"#### 🚨 Alunos identificados pelo Radar:")
            with c_pdf:
                pdf_bytes = gerar_pdf_atrasados(lista_final_evasao)
                st.download_button(
                    label="📄 Baixar Relatório PDF",
                    data=pdf_bytes,
                    file_name=f"Radar_Evasao_{datetime.date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.markdown("---")

            for item in lista_final_evasao:
                nome_curto = str(item["nome"]).split()[0].capitalize()
                numero = limpar_whatsapp_link(item["whatsapp"])

                if item["dias"] == 9999:
                    alerta_visual = (
                        "⚠️ Nenhuma presença registada (Faltoso desde a matrícula)"
                    )
                    tag_html = "<span style='background: #FEF08A; color: #854D0E; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; border: 1px solid #EAB308; margin-left: 8px;'>🆕 NUNCA COMPARECEU</span>"
                else:
                    data_str = item["data_ultima"].strftime("%d/%m/%Y")
                    alerta_visual = f"⚠️ {item['dias']} dias úteis ausente (Última presença: {data_str})"
                    tag_html = "<span style='background: #FECACA; color: #991B1B; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; border: 1px solid #F87171; margin-left: 8px;'>🚨 EVASÃO</span>"

                msg = f"Olá, {nome_curto}! Tudo bem? Sentimos sua falta nas aulas do Instituto Muda Brasil! 💙 Está tudo bem com você? Queríamos saber se está precisando de algo e quando pretende voltar. Sua presença é muito importante para nós! Um grande abraço!"
                link_wa = (
                    f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"
                    if numero
                    else None
                )

                with st.container(border=True):
                    # 🚀 AQUI: Ajuste do grid de colunas para caberem os dois botões
                    col_foto, col_texto, col_acoes = st.columns(
                        [1, 3.5, 2.5], vertical_alignment="center"
                    )

                    with col_foto:
                        if item.get("foto_url"):
                            st.image(item["foto_url"], use_container_width=True)
                        else:
                            st.markdown(
                                "<h1 style='text-align: center; color: #ccc; margin: 0;'>👤</h1>",
                                unsafe_allow_html=True,
                            )

                    with col_texto:
                        st.markdown(
                            f"**{item['nome'].upper()}** {tag_html}",
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"**Turma:** {item['turma']}  \n<span style='color: #EF4444;'>{alerta_visual}</span>",
                            unsafe_allow_html=True,
                        )

                    with col_acoes:
                        # 🚀 AQUI: Subdivisão para os botões "Abrir" e "Acolher" lado a lado
                        cb_abrir, cb_wa = st.columns(2, gap="small")

                        with cb_abrir:
                            if st.button(
                                "🩺 Abrir",
                                key=f"abr_rad_{item['id']}",
                                use_container_width=True,
                            ):
                                # Busca os dados integrais do aluno no banco de dados
                                aluno_completo = buscar_aluno_por_id(item["id"])
                                if aluno_completo:
                                    st.session_state.aluno_prontuario = aluno_completo
                                    st.session_state.origem_prontuario = "Radar de Evasão"
                                    st.session_state.menu_atual = "Portal do Aluno"
                                    st.rerun()

                        with cb_wa:
                            if link_wa:
                                st.link_button(
                                    "💬 Acolher",
                                    link_wa,
                                    type="primary",
                                    use_container_width=True,
                                )
                            else:
                                st.button(
                                    "Sem WA",
                                    disabled=True,
                                    use_container_width=True,
                                    key=f"btn_off_{item['id']}",
                                )

    except Exception as e:
        st.error(f"Erro ao processar radar: {e}")
