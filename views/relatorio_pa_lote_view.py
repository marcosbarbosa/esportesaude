# ==============================================================================
# 📄 Arquivo: views/relatorio_pa_lote_view.py
# 🏷️ VERSÃO: 1.0 — Formulário de Coleta em Lote — Pressão Arterial
# ⚙️ FUNÇÃO: Gera formulário imprimível para coleta manual de PA de vários
#            alunos ao mesmo tempo. Duas versões: em branco e pré-preenchida.
# ==============================================================================
import streamlit as st
import streamlit.components.v1 as components
import datetime

from utils.identidade import get_config, get_logo_b64
from database import get_todas_turmas, get_alunos_por_turma


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def _img_tag(b64: str, alt: str, max_w: int = 120, max_h: int = 60) -> str:
    if not b64:
        return f'<span style="font-size:8pt;color:#888;">{alt}</span>'
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="max-width:{max_w}px;max-height:{max_h}px;object-fit:contain;" alt="{alt}">'
    )


def _campo_info(label: str, valor: str = "", largura: str = "auto") -> str:
    """Retorna bloco HTML de campo com linha para preenchimento manual."""
    return f"""
<div style="min-width:{largura};flex:1;padding:0 6px 0 0;">
  <div style="font-size:7pt;font-weight:700;color:#475569;text-transform:uppercase;
              letter-spacing:.3px;margin-bottom:1px;">{label}</div>
  <div style="font-size:9.5pt;color:#1e293b;border-bottom:1.5px solid #334155;
              padding-bottom:2px;min-height:18px;font-weight:600;">{valor}</div>
</div>"""


def _calcular_idade(data_nascimento) -> str:
    try:
        if not data_nascimento:
            return ""
        if isinstance(data_nascimento, str):
            dn = datetime.date.fromisoformat(data_nascimento[:10])
        else:
            dn = data_nascimento
        hoje = datetime.date.today()
        anos = hoje.year - dn.year - ((hoje.month, hoje.day) < (dn.month, dn.day))
        return str(anos)
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DO HTML COMPLETO
# ──────────────────────────────────────────────────────────────────────────────
def gerar_html_formulario(
    turma: str = "",
    professor: str = "",
    local: str = "",
    modalidade: str = "",
    momento: str = "",
    data_coleta: str = "",
    hora_coleta: str = "",
    obs_gerais: str = "",
    alunos: list | None = None,    # lista de dicts {"nome", "matricula", "idade"}
    n_linhas_vazias: int = 20,
    unidade: str = "",
) -> str:
    """
    Retorna HTML completo do formulário de coleta em lote de PA.

    - Se `alunos` for fornecido e não-vazio → versão pré-preenchida.
    - Caso contrário → versão em branco com `n_linhas_vazias` linhas.
    """
    cfg       = get_config()
    titulo    = cfg.get("titulo_projeto",    "ESPORTE E SAÚDE NA COMUNIDADE")
    subtit    = cfg.get("subtitulo_projeto", "Projeto de Atividade Física, Saúde e Bem-Estar")
    nome_org  = cfg.get("nome_organizacao",  "Instituto Muda Brasil")
    cnpj      = cfg.get("cnpj",              "")
    endereco  = cfg.get("endereco",          "")
    site      = cfg.get("site",              "")
    instagram = cfg.get("instagram",         "")

    logo_p_b64 = get_logo_b64(cfg.get("logo_principal",  "logo-imbra.png"))
    logo_s_b64 = get_logo_b64(cfg.get("logo_secundaria", "logo-secretaria.png"))
    img_p = _img_tag(logo_p_b64,  nome_org,             120, 58)
    img_s = _img_tag(logo_s_b64, "Parceiro Institucional", 140, 58)

    agora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")

    rodape_partes = [p for p in [
        nome_org,
        f"CNPJ: {cnpj}" if cnpj else "",
        site, instagram, endereco,
    ] if p]
    rodape_linha = " &nbsp;|&nbsp; ".join(rodape_partes)

    # ── Linhas da tabela ───────────────────────────────────────────────────────
    if alunos:
        linhas_html = ""
        for i, al in enumerate(alunos, 1):
            bg = "background:#F8FAFC;" if i % 2 == 0 else ""
            linhas_html += f"""
<tr style="{bg}">
  <td style="text-align:center;font-weight:700;">{i}</td>
  <td style="font-weight:600;">{al.get("nome", "")}</td>
  <td style="text-align:center;">{al.get("matricula", "")}</td>
  <td style="text-align:center;">{al.get("idade", "")}</td>
  <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
</tr>"""
    else:
        linhas_html = ""
        for i in range(1, n_linhas_vazias + 1):
            bg = "background:#F8FAFC;" if i % 2 == 0 else ""
            linhas_html += f"""
<tr style="{bg}">
  <td style="text-align:center;font-weight:700;color:#94A3B8;">{i}</td>
  <td></td><td></td><td></td>
  <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
</tr>"""

    versao_badge = (
        '<span style="background:#1D4ED8;color:#fff;font-size:7pt;font-weight:800;'
        'padding:2px 8px;border-radius:10px;letter-spacing:.4px;">PRÉ-PREENCHIDO</span>'
        if alunos else
        '<span style="background:#475569;color:#fff;font-size:7pt;font-weight:800;'
        'padding:2px 8px;border-radius:10px;letter-spacing:.4px;">EM BRANCO</span>'
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Formulário PA em Lote</title>
<style>
/* ── Reset ──────────────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: Arial, Helvetica, sans-serif;
  font-size: 9pt;
  color: #1e293b;
  background: #fff;
}}

/* ── Botão de impressão (oculto na impressão) ────────────────────────────── */
.btn-imprimir {{
  display: block;
  margin: 10px auto 14px;
  padding: 10px 36px;
  background: #1D4ED8;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  letter-spacing: .4px;
}}
.btn-imprimir:hover {{ background: #1e40af; }}

/* ── Estrutura da página ─────────────────────────────────────────────────── */
.pagina {{
  width: 277mm;
  margin: 0 auto;
  padding: 6mm 0;
}}

/* ── Cabeçalho institucional ──────────────────────────────────────────────── */
.cabec-table {{
  width: 100%;
  border-collapse: collapse;
  border-bottom: 3px solid #0056b3;
  margin-bottom: 8px;
}}
.cabec-table td {{ border: none; padding: 4px 6px; vertical-align: middle; }}

/* ── Campos de contexto ──────────────────────────────────────────────────── */
.campos-contexto {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 0;
  margin-bottom: 8px;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 8px 10px;
  background: #F8FAFC;
}}
.campo-linha {{
  display: flex;
  gap: 10px;
  width: 100%;
}}

/* ── Tabela principal ────────────────────────────────────────────────────── */
.tabela-pa {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  table-layout: fixed;
}}
.tabela-pa th {{
  background: #0056b3;
  color: #fff;
  font-size: 7pt;
  font-weight: 800;
  text-align: center;
  padding: 5px 3px;
  border: 1px solid #0041a0;
  text-transform: uppercase;
  letter-spacing: .3px;
  vertical-align: middle;
}}
.tabela-pa td {{
  height: 11.5mm;
  border: 1px solid #CBD5E1;
  font-size: 8.5pt;
  padding: 2px 4px;
  vertical-align: middle;
}}
.tabela-pa tr:nth-child(even) td {{ background: #F8FAFC; }}
.tabela-pa tr:hover td {{ background: #EFF6FF; }}

/* ── Legenda de classificação ────────────────────────────────────────────── */
.legenda-box {{
  margin-top: 8px;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 6px 10px;
  background: #F8FAFC;
}}
.legenda-titulo {{
  font-size: 7.5pt;
  font-weight: 800;
  color: #0056b3;
  text-transform: uppercase;
  letter-spacing: .4px;
  margin-bottom: 4px;
  border-bottom: 1px solid #E2E8F0;
  padding-bottom: 2px;
}}
.legenda-itens {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}}
.legenda-item {{
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 7.5pt;
}}
.legenda-cor {{
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,.15);
  flex-shrink: 0;
}}
.legenda-rotulo {{
  display: inline-block;
  border: 1.5px solid currentColor;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 6.5pt;
  font-weight: 800;
  letter-spacing: .4px;
}}

/* ── Rodapé educativo ────────────────────────────────────────────────────── */
.edu-box {{
  margin-top: 8px;
  border: 1px solid #CBD5E1;
  border-left: 4px solid #0056b3;
  border-radius: 4px;
  padding: 5px 10px;
  background: #EFF6FF;
}}
.edu-titulo {{
  font-size: 7pt;
  font-weight: 800;
  color: #0056b3;
  text-transform: uppercase;
  letter-spacing: .3px;
  margin-bottom: 3px;
}}
.edu-itens {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}}
.edu-item {{
  font-size: 7pt;
  color: #334155;
  display: flex;
  align-items: flex-start;
  gap: 3px;
}}

/* ── Rodapé institucional ─────────────────────────────────────────────────── */
.rodape-inst {{
  margin-top: 10px;
  text-align: center;
  font-size: 6.5pt;
  color: #94A3B8;
  border-top: 1px solid #E2E8F0;
  padding-top: 5px;
}}

/* ── Assinatura da folha ─────────────────────────────────────────────────── */
.assinatura-folha {{
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 30px;
}}
.assinatura-campo {{
  text-align: center;
  font-size: 7.5pt;
}}
.assinatura-linha {{
  border-bottom: 1.5px solid #334155;
  width: 160px;
  margin-bottom: 2px;
  height: 20px;
}}

/* ════════════════════════════════════════════════════════════════════════════
   IMPRESSÃO
   ════════════════════════════════════════════════════════════════════════════ */
@media print {{
  @page {{
    size: A4 landscape;
    margin: 8mm 10mm 10mm 10mm;
  }}
  body {{ background: #fff !important; font-size: 8.5pt; }}
  .btn-imprimir {{ display: none !important; }}
  .pagina {{ width: 100%; margin: 0; padding: 0; }}
  .tabela-pa thead {{ display: table-header-group; }}
  .tabela-pa tr {{ page-break-inside: avoid; }}
  .legenda-box, .edu-box {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>

<button class="btn-imprimir" onclick="window.print()">🖨️ &nbsp; Imprimir / Salvar PDF</button>

<div class="pagina">

  <!-- ══ CABEÇALHO INSTITUCIONAL ══════════════════════════════════════════════ -->
  <table class="cabec-table">
    <tr>
      <td style="width:20%;text-align:left;">{img_s}</td>
      <td style="width:60%;text-align:center;">
        <p style="font-size:9.5pt;font-weight:900;color:#0A2540;text-transform:uppercase;
                  letter-spacing:-.2px;margin:0;">{titulo}</p>
        <p style="font-size:8.5pt;color:#475569;font-weight:600;margin:2px 0 0;">{subtit}</p>
        <p style="font-size:9pt;font-weight:800;color:#0056b3;margin:3px 0 0;">
          Formulário de Coleta em Lote — Pressão Arterial dos Alunos
        </p>
        <p style="font-size:7.5pt;color:#64748B;margin:2px 0 0;">
          Uso em papel para coleta simultânea e posterior lançamento no prontuário do aluno
          &nbsp;|&nbsp; {versao_badge}
        </p>
        <p style="font-size:6.5pt;color:#94A3B8;margin:1px 0 0;">Emitido em: {agora}</p>
      </td>
      <td style="width:20%;text-align:right;">{img_p}</td>
    </tr>
  </table>

  <!-- ══ CAMPOS DE CONTEXTO ════════════════════════════════════════════════════ -->
  <div class="campos-contexto">
    <div class="campo-linha">
      {_campo_info("Data da Coleta",       data_coleta,  "110px")}
      {_campo_info("Horário",              hora_coleta,  "80px")}
      {_campo_info("Professor Responsável", professor,   "180px")}
      {_campo_info("Turma / Grupo",         turma,       "140px")}
      {_campo_info("Modalidade / Aula",     modalidade,  "140px")}
      {_campo_info("Unidade / Local",       local or unidade, "160px")}
    </div>
    <div class="campo-linha" style="margin-top:6px;">
      {_campo_info("Momento da Coleta",  momento or "( ) Antes da aula &nbsp;&nbsp;&nbsp; ( ) Depois da aula &nbsp;&nbsp;&nbsp; ( ) Em repouso", "260px")}
      {_campo_info("Observações Gerais da Turma", obs_gerais, "auto")}
    </div>
  </div>

  <!-- ══ TABELA PRINCIPAL ══════════════════════════════════════════════════════ -->
  <table class="tabela-pa">
    <colgroup>
      <col style="width:3%">   <!-- Nº -->
      <col style="width:17%">  <!-- Nome -->
      <col style="width:6.5%"> <!-- Matrícula -->
      <col style="width:4%">   <!-- Idade -->
      <col style="width:5.5%"> <!-- Sistólica -->
      <col style="width:5.5%"> <!-- Diastólica -->
      <col style="width:5%">   <!-- Pulso -->
      <col style="width:5%">   <!-- Hora -->
      <col style="width:13%">  <!-- Sintomas -->
      <col style="width:11%">  <!-- Classificação -->
      <col style="width:15.5%"><!-- Observações -->
      <col style="width:9%">   <!-- Assinatura -->
    </colgroup>
    <thead>
      <tr>
        <th>Nº</th>
        <th style="text-align:left;padding-left:5px;">Nome do Aluno</th>
        <th>Matrícula<br>/ ID</th>
        <th>Idade</th>
        <th>Sistólica<br>(mmHg)</th>
        <th>Diastólica<br>(mmHg)</th>
        <th>Pulso<br>(bpm)</th>
        <th>Hora da<br>Medição</th>
        <th style="text-align:left;padding-left:5px;">Sintomas Relatados</th>
        <th>Classificação<br>Manual</th>
        <th style="text-align:left;padding-left:5px;">Observações</th>
        <th>Assinatura /<br>Rubrica</th>
      </tr>
    </thead>
    <tbody>
      {linhas_html}
    </tbody>
  </table>

  <!-- ══ LEGENDA DE CLASSIFICAÇÃO ══════════════════════════════════════════════ -->
  <div class="legenda-box">
    <div class="legenda-titulo">🩺 Legenda de Classificação da Pressão Arterial (AHA Guidelines)</div>
    <div class="legenda-itens">

      <div class="legenda-item">
        <div class="legenda-cor" style="background:#BFDBFE;border-color:#1D4ED8;"></div>
        <div>
          <strong style="color:#1D4ED8;">Normal</strong><br>
          <span style="font-size:6.5pt;color:#475569;">Sist. &lt; 120 <em>e</em> Diast. &lt; 80</span><br>
          <span class="legenda-rotulo" style="color:#1D4ED8;">[NORMAL]</span>
        </div>
      </div>

      <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
        <div class="legenda-cor" style="background:#FDE68A;border-color:#D97706;"></div>
        <div>
          <strong style="color:#D97706;">Elevada</strong><br>
          <span style="font-size:6.5pt;color:#475569;">Sist. 120–129 <em>e</em> Diast. &lt; 80</span><br>
          <span class="legenda-rotulo" style="color:#D97706;">[ATENÇÃO]</span>
        </div>
      </div>

      <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
        <div class="legenda-cor" style="background:#FDBA74;border-color:#EA580C;"></div>
        <div>
          <strong style="color:#EA580C;">Estágio 1</strong><br>
          <span style="font-size:6.5pt;color:#475569;">Sist. 130–139 <em>ou</em> Diast. 80–89</span><br>
          <span class="legenda-rotulo" style="color:#EA580C;">[ALTERADA]</span>
        </div>
      </div>

      <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
        <div class="legenda-cor" style="background:#FECACA;border-color:#B91C1C;"></div>
        <div>
          <strong style="color:#B91C1C;">Estágio 2</strong><br>
          <span style="font-size:6.5pt;color:#475569;">Sist. ≥ 140 <em>ou</em> Diast. ≥ 90</span><br>
          <span class="legenda-rotulo" style="color:#B91C1C;">[ALTA]</span>
        </div>
      </div>

      <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
        <div class="legenda-cor" style="background:#7F0000;border-color:#450A0A;"></div>
        <div>
          <strong style="color:#7F0000;">Crise Hipertensiva</strong><br>
          <span style="font-size:6.5pt;color:#475569;">Sist. &gt; 180 <em>e/ou</em> Diast. &gt; 120</span><br>
          <span class="legenda-rotulo" style="color:#7F0000;">[CRÍTICA]</span>
        </div>
      </div>

      <div style="margin-left:auto;font-size:6.5pt;color:#64748B;align-self:center;text-align:right;line-height:1.5;">
        Quando sistólica e diastólica se enquadram<br>
        em categorias diferentes, prevalece a mais grave.
      </div>
    </div>
  </div>

  <!-- ══ BLOCO EDUCATIVO ════════════════════════════════════════════════════════ -->
  <div class="edu-box">
    <div class="edu-titulo">📋 Instruções para Coleta Correta</div>
    <div class="edu-itens">
      <div class="edu-item">🪑 <span>Aluno sentado,<br>costas apoiadas</span></div>
      <div class="edu-item">💪 <span>Braço apoiado ao<br>nível do coração</span></div>
      <div class="edu-item">⏱️ <span>5 min de repouso<br>antes da medição</span></div>
      <div class="edu-item">🤫 <span>Sem falar durante<br>a aferição</span></div>
      <div class="edu-item">☕ <span>Evitar café, cigarro<br>e álcool por 30 min</span></div>
      <div class="edu-item">🏃 <span>Evitar exercício<br>por 30 min antes</span></div>
      <div class="edu-item">🔁 <span>Repetir se valor<br>muito alterado</span></div>
      <div class="edu-item">↔️ <span>Registrar o braço<br>utilizado (D ou E)</span></div>
    </div>
  </div>

  <!-- ══ ASSINATURAS ════════════════════════════════════════════════════════════ -->
  <div class="assinatura-folha">
    <div class="assinatura-campo">
      <div class="assinatura-linha"></div>
      <div>Professor Responsável</div>
    </div>
    <div class="assinatura-campo">
      <div class="assinatura-linha"></div>
      <div>Coordenação / Supervisão</div>
    </div>
  </div>

  <!-- ══ RODAPÉ INSTITUCIONAL ══════════════════════════════════════════════════ -->
  <div class="rodape-inst">
    {rodape_linha}
    &nbsp;|&nbsp; Emitido em {agora}
    &nbsp;|&nbsp; Formulário de Coleta em Lote — Pressão Arterial
  </div>

</div><!-- /pagina -->
</body>
</html>"""
    return html


# ──────────────────────────────────────────────────────────────────────────────
# TELA STREAMLIT
# ──────────────────────────────────────────────────────────────────────────────
def tela_relatorio_pa_lote():
    """Renderiza a interface de geração do formulário de coleta em lote de PA."""

    st.markdown("""
    <div style='background:linear-gradient(135deg,#EFF6FF,#DBEAFE);padding:18px 20px;
                border-radius:12px;border-left:6px solid #1D4ED8;margin-bottom:16px;'>
      <h3 style='margin:0 0 4px;color:#1e3a8a;'>🩺 Formulário de Coleta em Lote — Pressão Arterial</h3>
      <p style='margin:0;color:#475569;font-size:13px;'>
        Gera um formulário imprimível para coletar a PA de vários alunos em papel,
        durante a aula. Depois, os dados são lançados individualmente no prontuário.
      </p>
    </div>""", unsafe_allow_html=True)

    # ── Filtros e configurações ────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### ⚙️ Configurar Formulário")

        col_v, col_t = st.columns([1, 2])
        versao = col_v.radio(
            "Versão do formulário",
            ["📄 Em branco", "📋 Pré-preenchida (com alunos da turma)"],
            key="pa_lote_versao",
            help="Em branco: linhas vazias para qualquer aluno. "
                 "Pré-preenchida: nomes e matrículas já inseridos.",
        )

        turmas_df = get_todas_turmas(ativas_apenas=True)
        turmas_lista = turmas_df["nome"].tolist() if not turmas_df.empty else []

        turma_sel = col_t.selectbox(
            "Turma / Grupo",
            ["(sem turma / livre)"] + turmas_lista,
            key="pa_lote_turma",
        )
        turma_str = "" if turma_sel.startswith("(") else turma_sel

        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        data_coleta = r1c1.date_input(
            "Data da coleta", datetime.date.today(),
            format="DD/MM/YYYY", key="pa_lote_data",
        )
        hora_coleta = r1c2.text_input(
            "Horário", placeholder="08:30", key="pa_lote_hora",
        )
        professor = r1c3.text_input(
            "Professor responsável", key="pa_lote_prof",
        )
        local_str = r1c4.text_input(
            "Unidade / Local", key="pa_lote_local",
        )

        r2c1, r2c2, r2c3 = st.columns([1.2, 1.2, 2])
        modalidade = r2c1.text_input(
            "Modalidade / Aula", placeholder="Ex: Musculação, Pilates…",
            key="pa_lote_modal",
        )
        momento_opts = [
            "(marcar em papel)",
            "Antes da aula",
            "Depois da aula",
            "Em repouso",
        ]
        momento_sel = r2c2.selectbox(
            "Momento da coleta", momento_opts, key="pa_lote_momento",
        )
        momento_str = "" if momento_sel.startswith("(") else momento_sel
        obs_gerais = r2c3.text_input(
            "Observações gerais", key="pa_lote_obs",
        )

        n_linhas = 20
        if versao.startswith("📄"):
            n_linhas = st.select_slider(
                "Número de linhas em branco",
                options=[10, 15, 20, 25, 30, 35, 40],
                value=20,
                key="pa_lote_nlinhas",
            )

    # ── Botão de geração ───────────────────────────────────────────────────────
    if st.button(
        "🖨️ Gerar Formulário de Impressão",
        type="primary",
        use_container_width=True,
        key="pa_lote_gerar",
    ):
        alunos_lista = None

        if versao.startswith("📋") and turma_str:
            with st.spinner(f"Carregando alunos da turma {turma_str}…"):
                df_al = get_alunos_por_turma(turma_str)
            if df_al.empty:
                st.warning(f"Nenhum aluno ativo encontrado na turma **{turma_str}**. "
                           "O formulário será gerado em branco.")
            else:
                alunos_lista = []
                for _, row in df_al.sort_values("nome").iterrows():
                    alunos_lista.append({
                        "nome":      row.get("nome", ""),
                        "matricula": str(row.get("id", "")),
                        "idade":     _calcular_idade(row.get("data_nascimento", "")),
                    })
                st.success(f"✅ {len(alunos_lista)} alunos carregados da turma **{turma_str}**.")

        elif versao.startswith("📋") and not turma_str:
            st.warning("Selecione uma turma para usar a versão pré-preenchida, "
                       "ou escolha a versão em branco.")
            return

        html_form = gerar_html_formulario(
            turma=turma_str,
            professor=professor,
            local=local_str,
            modalidade=modalidade,
            momento=momento_str,
            data_coleta=data_coleta.strftime("%d/%m/%Y"),
            hora_coleta=hora_coleta,
            obs_gerais=obs_gerais,
            alunos=alunos_lista,
            n_linhas_vazias=int(n_linhas),
        )

        st.session_state["pa_lote_html"] = html_form
        st.session_state["pa_lote_gerado"] = True

    # ── Exibição do formulário ─────────────────────────────────────────────────
    if st.session_state.get("pa_lote_gerado") and st.session_state.get("pa_lote_html"):
        st.divider()
        st.info("💡 Clique em **Imprimir / Salvar PDF** dentro do formulário abaixo. "
                "Para salvar como PDF, selecione 'Salvar como PDF' na janela de impressão.",
                icon="🖨️")

        components.html(
            st.session_state["pa_lote_html"],
            height=820,
            scrolling=True,
        )

        st.caption(
            "⚠️ Dica de impressão: use **Orientação Paisagem (A4)** e margens de 10 mm "
            "para melhor aproveitamento. No Chrome/Edge, desmarque 'Cabeçalhos e rodapés do navegador'."
        )
