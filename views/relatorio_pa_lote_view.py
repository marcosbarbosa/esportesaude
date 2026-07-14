# ==============================================================================
# 📄 Arquivo: views/relatorio_pa_lote_view.py
# 🏷️ VERSÃO: 2.0 — Coleta em Lote PA — Multi-turma, pré-preenchida, agrupada
# ⚙️ FUNÇÃO: Formulário imprimível para coleta manual de PA.
#            Suporte a todas as turmas / uma turma / turmas selecionadas,
#            ordenação alfabética, agrupamento por turma com numeração reiniciada.
# ==============================================================================
import streamlit as st
from streamlit.components.v1 import html as _html_v1
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
        return str(hoje.year - dn.year - ((hoje.month, hoje.day) < (dn.month, dn.day)))
    except Exception:
        return ""


def _carregar_alunos_turma(turma_nome: str) -> list:
    """Retorna lista de dicts {nome, matricula, idade, turma} da turma."""
    try:
        df = get_alunos_por_turma(turma_nome)
        if df.empty:
            return []
        alunos = []
        for _, row in df.sort_values("nome").iterrows():
            alunos.append({
                "nome":      row.get("nome", ""),
                "matricula": str(row.get("id", "")),
                "idade":     _calcular_idade(row.get("data_nascimento", "")),
                "turma":     turma_nome,
            })
        return alunos
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# CSS COMPARTILHADO
# ──────────────────────────────────────────────────────────────────────────────
_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 9pt;
  color: #1e293b;
  background: #fff;
}
.btn-imprimir {
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
}
.btn-imprimir:hover { background: #1e40af; }
.pagina {
  width: 277mm;
  margin: 0 auto;
  padding: 4mm 0;
}
.cabec-table {
  width: 100%;
  border-collapse: collapse;
  border-bottom: 3px solid #0056b3;
  margin-bottom: 8px;
}
.cabec-table td { border: none; padding: 4px 6px; vertical-align: middle; }
.campos-contexto {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 0;
  margin-bottom: 6px;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 7px 10px;
  background: #F8FAFC;
}
.campo-linha { display: flex; gap: 10px; width: 100%; }
.tabela-pa {
  width: 100%;
  border-collapse: collapse;
  margin-top: 6px;
  table-layout: fixed;
}
.tabela-pa th {
  background: #0056b3;
  color: #fff;
  font-size: 6.5pt;
  font-weight: 800;
  text-align: center;
  padding: 4px 3px;
  border: 1px solid #0041a0;
  text-transform: uppercase;
  letter-spacing: .3px;
  vertical-align: middle;
}
.tabela-pa td {
  height: 11mm;
  border: 1px solid #CBD5E1;
  font-size: 8pt;
  padding: 2px 4px;
  vertical-align: middle;
}
.tabela-pa tr:nth-child(even) td { background: #F8FAFC; }
.turma-header td {
  background: #E0F2FE !important;
  border-top: 2px solid #0284C7 !important;
  border-bottom: 1px solid #7DD3FC !important;
  padding: 4px 8px !important;
  font-size: 8pt !important;
  font-weight: 800 !important;
  color: #0C4A6E !important;
  letter-spacing: .2px !important;
  height: auto !important;
  page-break-after: avoid !important;
}
.legenda-box {
  margin-top: 6px;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 5px 10px;
  background: #F8FAFC;
}
.legenda-titulo {
  font-size: 7pt;
  font-weight: 800;
  color: #0056b3;
  text-transform: uppercase;
  letter-spacing: .4px;
  margin-bottom: 3px;
  border-bottom: 1px solid #E2E8F0;
  padding-bottom: 2px;
}
.legenda-itens { display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-start; }
.legenda-item { display: flex; align-items: flex-start; gap: 5px; font-size: 7pt; }
.legenda-cor {
  width: 12px; height: 12px; border-radius: 3px;
  border: 1px solid rgba(0,0,0,.15); flex-shrink: 0; margin-top: 1px;
}
.legenda-rotulo {
  display: inline-block;
  border: 1.5px solid currentColor;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 6pt;
  font-weight: 800;
  letter-spacing: .4px;
}
.edu-box {
  margin-top: 6px;
  border: 1px solid #CBD5E1;
  border-left: 4px solid #0056b3;
  border-radius: 4px;
  padding: 5px 10px;
  background: #EFF6FF;
}
.edu-titulo {
  font-size: 6.5pt;
  font-weight: 800;
  color: #0056b3;
  text-transform: uppercase;
  letter-spacing: .3px;
  margin-bottom: 2px;
}
.edu-itens { display: flex; gap: 10px; flex-wrap: wrap; }
.edu-item {
  font-size: 6.5pt;
  color: #334155;
  display: flex;
  align-items: flex-start;
  gap: 3px;
}
.rodape-inst {
  margin-top: 8px;
  text-align: center;
  font-size: 6pt;
  color: #94A3B8;
  border-top: 1px solid #E2E8F0;
  padding-top: 4px;
}
.assinatura-folha {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 30px;
}
.assinatura-campo { text-align: center; font-size: 7pt; }
.assinatura-linha {
  border-bottom: 1.5px solid #334155;
  width: 160px;
  margin-bottom: 2px;
  height: 18px;
}
@media print {
  @page { size: A4 landscape; margin: 8mm 10mm 10mm 10mm; }
  body { background: #fff !important; font-size: 8pt; }
  .btn-imprimir { display: none !important; }
  .pagina { width: 100%; margin: 0; padding: 0; }
  .tabela-pa thead { display: table-header-group; }
  .tabela-pa tr { page-break-inside: avoid; }
  .turma-header { page-break-after: avoid; }
  .legenda-box, .edu-box { page-break-inside: avoid; }
}
"""

_LEGENDA_HTML = """
<div class="legenda-box">
  <div class="legenda-titulo">Legenda — Classificação da Pressão Arterial (AHA)</div>
  <div class="legenda-itens">
    <div class="legenda-item">
      <div class="legenda-cor" style="background:#BFDBFE;border-color:#1D4ED8;"></div>
      <div><strong style="color:#1D4ED8;">Normal</strong><br>
        <span style="font-size:6pt;color:#475569;">Sist. &lt;120 <em>e</em> Diast. &lt;80</span><br>
        <span class="legenda-rotulo" style="color:#1D4ED8;">[NORMAL]</span></div>
    </div>
    <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
      <div class="legenda-cor" style="background:#FDE68A;border-color:#D97706;"></div>
      <div><strong style="color:#D97706;">Elevada</strong><br>
        <span style="font-size:6pt;color:#475569;">Sist. 120–129 <em>e</em> Diast. &lt;80</span><br>
        <span class="legenda-rotulo" style="color:#D97706;">[ATENÇÃO]</span></div>
    </div>
    <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
      <div class="legenda-cor" style="background:#FDBA74;border-color:#EA580C;"></div>
      <div><strong style="color:#EA580C;">Estágio 1</strong><br>
        <span style="font-size:6pt;color:#475569;">Sist. 130–139 <em>ou</em> Diast. 80–89</span><br>
        <span class="legenda-rotulo" style="color:#EA580C;">[ALTERADA]</span></div>
    </div>
    <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
      <div class="legenda-cor" style="background:#FECACA;border-color:#B91C1C;"></div>
      <div><strong style="color:#B91C1C;">Estágio 2</strong><br>
        <span style="font-size:6pt;color:#475569;">Sist. &ge;140 <em>ou</em> Diast. &ge;90</span><br>
        <span class="legenda-rotulo" style="color:#B91C1C;">[ALTA]</span></div>
    </div>
    <div class="legenda-item" style="border-left:1px solid #E2E8F0;padding-left:8px;">
      <div class="legenda-cor" style="background:#7F0000;border-color:#450A0A;"></div>
      <div><strong style="color:#7F0000;">Crise</strong><br>
        <span style="font-size:6pt;color:#475569;">Sist. &gt;180 <em>e/ou</em> Diast. &gt;120</span><br>
        <span class="legenda-rotulo" style="color:#7F0000;">[CRÍTICA]</span></div>
    </div>
    <div style="margin-left:auto;font-size:6pt;color:#64748B;align-self:center;
                text-align:right;line-height:1.5;">
      Prevalece sempre<br>a categoria mais grave.
    </div>
  </div>
</div>"""

_EDU_HTML = """
<div class="edu-box">
  <div class="edu-titulo">Instruções para Coleta Correta</div>
  <div class="edu-itens">
    <div class="edu-item">&#x1FA91; <span>Aluno sentado,<br>costas apoiadas</span></div>
    <div class="edu-item">&#x1F4AA; <span>Braco apoiado ao<br>nivel do coracao</span></div>
    <div class="edu-item">&#x23F1; <span>5 min de repouso<br>antes da medicao</span></div>
    <div class="edu-item">&#x1F910; <span>Sem falar durante<br>a afericao</span></div>
    <div class="edu-item">&#x2615; <span>Evitar cafe, cigarro<br>e alcool por 30 min</span></div>
    <div class="edu-item">&#x1F3C3; <span>Evitar exercicio<br>por 30 min antes</span></div>
    <div class="edu-item">&#x1F501; <span>Repetir se valor<br>muito alterado</span></div>
    <div class="edu-item">&#x2194; <span>Registrar o braco<br>usado (D ou E)</span></div>
  </div>
</div>"""


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DO HTML — COLGROUP E CABEÇALHO DA TABELA
# ──────────────────────────────────────────────────────────────────────────────
def _colgroup_e_thead(multi_turma: bool) -> str:
    if multi_turma:
        # 13 colunas — inclui Turma
        return """
    <colgroup>
      <col style="width:3%">    <!-- N -->
      <col style="width:15%">   <!-- Nome -->
      <col style="width:6%">    <!-- Matrícula -->
      <col style="width:4%">    <!-- Idade -->
      <col style="width:8%">    <!-- Turma -->
      <col style="width:5%">    <!-- SIS -->
      <col style="width:5%">    <!-- DIA -->
      <col style="width:4.5%">  <!-- Pulso -->
      <col style="width:5%">    <!-- Hora -->
      <col style="width:10%">   <!-- Sint. -->
      <col style="width:9%">    <!-- Classif. -->
      <col style="width:13%">   <!-- Obs. -->
      <col style="width:7.5%">  <!-- Rubrica -->
    </colgroup>
    <thead>
      <tr>
        <th>N°</th>
        <th style="text-align:left;padding-left:5px;">Nome do Aluno</th>
        <th>Matrícula</th>
        <th>Idade</th>
        <th>Turma</th>
        <th>SIS<br>(mmHg)</th>
        <th>DIA<br>(mmHg)</th>
        <th>Pulso<br>(bpm)</th>
        <th>Hora da<br>Medição</th>
        <th style="text-align:left;padding-left:4px;">Sintomas</th>
        <th>Classif.<br>Manual</th>
        <th style="text-align:left;padding-left:4px;">Observações</th>
        <th>Assinatura /<br>Rubrica</th>
      </tr>
    </thead>"""
    else:
        # 12 colunas — sem Turma (economiza espaço)
        return """
    <colgroup>
      <col style="width:3%">    <!-- N -->
      <col style="width:17%">   <!-- Nome -->
      <col style="width:6.5%">  <!-- Matrícula -->
      <col style="width:4%">    <!-- Idade -->
      <col style="width:5.5%">  <!-- SIS -->
      <col style="width:5.5%">  <!-- DIA -->
      <col style="width:5%">    <!-- Pulso -->
      <col style="width:5%">    <!-- Hora -->
      <col style="width:13%">   <!-- Sint. -->
      <col style="width:11%">   <!-- Classif. -->
      <col style="width:15.5%"> <!-- Obs. -->
      <col style="width:9%">    <!-- Rubrica -->
    </colgroup>
    <thead>
      <tr>
        <th>N°</th>
        <th style="text-align:left;padding-left:5px;">Nome do Aluno</th>
        <th>Matrícula /<br>ID</th>
        <th>Idade</th>
        <th>SIS<br>(mmHg)</th>
        <th>DIA<br>(mmHg)</th>
        <th>Pulso<br>(bpm)</th>
        <th>Hora da<br>Medição</th>
        <th style="text-align:left;padding-left:4px;">Sintomas Relatados</th>
        <th>Classificação<br>Manual</th>
        <th style="text-align:left;padding-left:4px;">Observações</th>
        <th>Assinatura /<br>Rubrica</th>
      </tr>
    </thead>"""


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DE LINHAS DA TABELA
# ──────────────────────────────────────────────────────────────────────────────
def _gerar_linhas_multi(grupos: list) -> str:
    """
    Grupos: [{"turma": str, "alunos": [{"nome","matricula","idade","turma"}]}]
    Numeração reinicia em 1 a cada bloco de turma.
    Linha separadora de turma aparece antes de cada grupo.
    """
    n_cols = 13  # com coluna Turma
    html   = ""
    for grupo in grupos:
        nome_turma = grupo["turma"]
        alunos     = grupo["alunos"]

        # ── Linha de cabeçalho do bloco ──────────────────────────────────────
        total = len(alunos)
        html += f"""
<tr class="turma-header">
  <td colspan="{n_cols}">
    &#9660; &nbsp; {nome_turma}
    <span style="font-weight:400;margin-left:8px;font-size:7pt;color:#475569;">
      — {total} aluno{"s" if total != 1 else ""}
    </span>
  </td>
</tr>"""

        # ── Linhas dos alunos ─────────────────────────────────────────────────
        for i, al in enumerate(alunos, 1):
            bg = "background:#F8FAFC;" if i % 2 == 0 else ""
            turma_cell = (
                f'<span style="font-size:6.5pt;color:#475569;">{al.get("turma","")}</span>'
            )
            html += f"""
<tr style="{bg}">
  <td style="text-align:center;font-weight:700;color:#0056b3;">{i}</td>
  <td style="font-weight:600;">{al.get("nome","")}</td>
  <td style="text-align:center;font-size:7.5pt;">{al.get("matricula","")}</td>
  <td style="text-align:center;">{al.get("idade","")}</td>
  <td style="text-align:center;">{turma_cell}</td>
  <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
</tr>"""
    return html


def _gerar_linhas_simples(alunos: list) -> str:
    """Numeração contínua, sem coluna de turma."""
    html = ""
    for i, al in enumerate(alunos, 1):
        bg = "background:#F8FAFC;" if i % 2 == 0 else ""
        html += f"""
<tr style="{bg}">
  <td style="text-align:center;font-weight:700;color:#0056b3;">{i}</td>
  <td style="font-weight:600;">{al.get("nome","")}</td>
  <td style="text-align:center;font-size:7.5pt;">{al.get("matricula","")}</td>
  <td style="text-align:center;">{al.get("idade","")}</td>
  <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
</tr>"""
    return html


def _gerar_linhas_vazias(n: int) -> str:
    html = ""
    for i in range(1, n + 1):
        bg = "background:#F8FAFC;" if i % 2 == 0 else ""
        html += f"""
<tr style="{bg}">
  <td style="text-align:center;font-weight:700;color:#94A3B8;">{i}</td>
  <td></td><td></td><td></td>
  <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
</tr>"""
    return html


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DO HTML COMPLETO
# ──────────────────────────────────────────────────────────────────────────────
def gerar_html_formulario(
    grupos: list,          # [{"turma": str, "alunos": list}] — vazio → em branco
    professor:   str = "",
    local:       str = "",
    modalidade:  str = "",
    momento:     str = "",
    data_coleta: str = "",
    hora_coleta: str = "",
    obs_gerais:  str = "",
    n_linhas_vazias: int = 20,
    filtro_label:    str = "",   # texto exibido no cabeçalho
) -> str:
    """
    Retorna HTML completo do formulário de coleta em lote.
    - grupos vazio  → versão em branco (n_linhas_vazias linhas)
    - 1 grupo       → numeração contínua, SEM coluna Turma
    - 2+ grupos     → blocos por turma, numeração reinicia, COM coluna Turma
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
    img_p = _img_tag(logo_p_b64,  nome_org,              120, 56)
    img_s = _img_tag(logo_s_b64, "Parceiro Institucional", 140, 56)

    agora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")

    rodape_partes = [p for p in [
        nome_org,
        f"CNPJ: {cnpj}" if cnpj else "",
        site, instagram, endereco,
    ] if p]
    rodape_linha = " &nbsp;|&nbsp; ".join(rodape_partes)

    # ── Determinar modo ───────────────────────────────────────────────────────
    multi_turma = len(grupos) > 1
    tem_alunos  = len(grupos) > 0

    if not tem_alunos:
        # Em branco
        linhas_html  = _gerar_linhas_vazias(n_linhas_vazias)
        versao_badge = (
            '<span style="background:#475569;color:#fff;font-size:7pt;font-weight:800;'
            'padding:2px 8px;border-radius:10px;">EM BRANCO</span>'
        )
    elif multi_turma:
        # Multi-turma: bloco por turma, numera do zero em cada bloco
        linhas_html  = _gerar_linhas_multi(grupos)
        n_total      = sum(len(g["alunos"]) for g in grupos)
        versao_badge = (
            f'<span style="background:#0284C7;color:#fff;font-size:7pt;font-weight:800;'
            f'padding:2px 8px;border-radius:10px;">'
            f'PRÉ-PREENCHIDO · {n_total} alunos · {len(grupos)} turmas</span>'
        )
    else:
        # Uma turma: numeração contínua, sem coluna Turma
        alunos_un    = grupos[0]["alunos"]
        linhas_html  = _gerar_linhas_simples(alunos_un)
        versao_badge = (
            f'<span style="background:#1D4ED8;color:#fff;font-size:7pt;font-weight:800;'
            f'padding:2px 8px;border-radius:10px;">'
            f'PRÉ-PREENCHIDO · {len(alunos_un)} alunos</span>'
        )

    colgroup_thead = _colgroup_e_thead(multi_turma)

    # ── Campo de turma no contexto ────────────────────────────────────────────
    turma_ctx = filtro_label or (grupos[0]["turma"] if len(grupos) == 1 else "")
    momento_str = momento or (
        "( ) Antes da aula &nbsp;&nbsp;&nbsp; ( ) Depois da aula"
        " &nbsp;&nbsp;&nbsp; ( ) Em repouso"
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Coleta PA em Lote</title>
<style>{_CSS}</style>
</head>
<body>

<button class="btn-imprimir" onclick="window.print()">&#x1F5A8;&nbsp; Imprimir / Salvar PDF</button>

<div class="pagina">

  <!-- CABEÇALHO INSTITUCIONAL -->
  <table class="cabec-table">
    <tr>
      <td style="width:20%;text-align:left;">{img_s}</td>
      <td style="width:60%;text-align:center;">
        <p style="font-size:9.5pt;font-weight:900;color:#0A2540;text-transform:uppercase;
                  letter-spacing:-.2px;margin:0;">{titulo}</p>
        <p style="font-size:8.5pt;color:#475569;font-weight:600;margin:2px 0 0;">{subtit}</p>
        <p style="font-size:9pt;font-weight:800;color:#0056b3;margin:3px 0 0;">
          Coleta em Lote — Pressão Arterial dos Alunos
        </p>
        <p style="font-size:7.5pt;color:#64748B;margin:2px 0 0;">
          Formulário para coleta manual e posterior lançamento no prontuário do aluno
          &nbsp;|&nbsp; {versao_badge}
        </p>
        <p style="font-size:6.5pt;color:#94A3B8;margin:1px 0 0;">Emitido em: {agora}
          {"&nbsp;|&nbsp; Filtro: <strong>" + filtro_label + "</strong>" if filtro_label else ""}
        </p>
      </td>
      <td style="width:20%;text-align:right;">{img_p}</td>
    </tr>
  </table>

  <!-- CAMPOS DE CONTEXTO -->
  <div class="campos-contexto">
    <div class="campo-linha">
      {_campo_info("Data da Coleta",        data_coleta,        "100px")}
      {_campo_info("Horário",               hora_coleta,        "70px")}
      {_campo_info("Professor Responsável", professor,          "170px")}
      {_campo_info("Turma / Filtro",        turma_ctx,          "130px")}
      {_campo_info("Modalidade / Aula",     modalidade,         "130px")}
      {_campo_info("Unidade / Local",       local,              "150px")}
    </div>
    <div class="campo-linha" style="margin-top:5px;">
      {_campo_info("Momento da Coleta", momento_str, "250px")}
      {_campo_info("Observações Gerais", obs_gerais, "auto")}
    </div>
  </div>

  <!-- TABELA PRINCIPAL -->
  <table class="tabela-pa">
    {colgroup_thead}
    <tbody>
      {linhas_html}
    </tbody>
  </table>

  {_LEGENDA_HTML}
  {_EDU_HTML}

  <!-- ASSINATURAS -->
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

  <!-- RODAPÉ INSTITUCIONAL -->
  <div class="rodape-inst">
    {rodape_linha}
    &nbsp;|&nbsp; Emitido em {agora}
    &nbsp;|&nbsp; Coleta em Lote — Pressão Arterial
  </div>

</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# TELA STREAMLIT
# ──────────────────────────────────────────────────────────────────────────────
def tela_relatorio_pa_lote():
    """Interface para geração do formulário de coleta em lote de PA."""

    st.markdown("""
    <div style='background:linear-gradient(135deg,#EFF6FF,#DBEAFE);padding:18px 20px;
                border-radius:12px;border-left:6px solid #1D4ED8;margin-bottom:16px;'>
      <h3 style='margin:0 0 4px;color:#1e3a8a;'>🩺 Coleta em Lote — Pressão Arterial</h3>
      <p style='margin:0;color:#475569;font-size:13px;'>
        Gera formulário imprimível para aferição de PA em papel durante a aula.
        Suporta todas as turmas, uma turma ou turmas selecionadas.
      </p>
    </div>""", unsafe_allow_html=True)

    # ── Carregar turmas ────────────────────────────────────────────────────────
    turmas_df    = get_todas_turmas(ativas_apenas=True)
    turmas_lista = sorted(turmas_df["nome"].tolist()) if not turmas_df.empty else []

    with st.container(border=True):
        st.markdown("#### ⚙️ Configurar Formulário")

        # ── Abrangência ────────────────────────────────────────────────────────
        abrangencia = st.radio(
            "Abrangência do relatório",
            [
                "📋 Pré-preenchido — todas as turmas",
                "📋 Pré-preenchido — uma turma",
                "📋 Pré-preenchido — turmas selecionadas",
                "📄 Em branco (linhas vazias)",
            ],
            horizontal=True,
            key="pa_lote_abrang",
        )

        turmas_selecionadas = []

        if "uma turma" in abrangencia:
            if turmas_lista:
                turma_unica = st.selectbox(
                    "Selecione a turma", turmas_lista, key="pa_lote_turma_unica"
                )
                turmas_selecionadas = [turma_unica]
            else:
                st.warning("Nenhuma turma ativa encontrada no sistema.")

        elif "turmas selecionadas" in abrangencia:
            if turmas_lista:
                turmas_selecionadas = st.multiselect(
                    "Selecione as turmas",
                    turmas_lista,
                    key="pa_lote_turmas_multi",
                    placeholder="Escolha uma ou mais turmas…",
                )
                if not turmas_selecionadas:
                    st.info("Selecione ao menos uma turma.")
            else:
                st.warning("Nenhuma turma ativa encontrada no sistema.")

        elif "todas as turmas" in abrangencia:
            turmas_selecionadas = turmas_lista
            if turmas_lista:
                st.caption(
                    f"✅ Serão incluídas **{len(turmas_lista)} turmas** ativas: "
                    + ", ".join(turmas_lista)
                )
            else:
                st.warning("Nenhuma turma ativa encontrada.")

        # ── Linhas em branco ────────────────────────────────────────────────────
        n_linhas = 20
        if "Em branco" in abrangencia:
            n_linhas = st.select_slider(
                "Número de linhas em branco",
                options=[10, 15, 20, 25, 30, 35, 40],
                value=20,
                key="pa_lote_nlinhas",
            )

        st.divider()

        # ── Campos de contexto ─────────────────────────────────────────────────
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        data_coleta = r1c1.date_input(
            "Data da coleta", datetime.date.today(),
            format="DD/MM/YYYY", key="pa_lote_data",
        )
        hora_coleta = r1c2.text_input(
            "Horário da coleta", placeholder="08:30", key="pa_lote_hora",
        )
        professor = r1c3.text_input(
            "Professor responsável", key="pa_lote_prof",
        )
        local_str = r1c4.text_input(
            "Unidade / Local", key="pa_lote_local",
        )

        r2c1, r2c2, r2c3 = st.columns([1.2, 1.2, 2])
        modalidade = r2c1.text_input(
            "Modalidade / Aula", placeholder="Ex: Pilates, Musculação…",
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

    # ── Botão de geração ───────────────────────────────────────────────────────
    gerar_ok = st.button(
        "🖨️ Gerar Formulário de Impressão",
        type="primary",
        use_container_width=True,
        key="pa_lote_gerar",
    )

    if gerar_ok:
        grupos     = []
        filtro_lbl = ""

        if "Em branco" in abrangencia:
            grupos     = []
            filtro_lbl = "Em branco"

        else:
            if not turmas_selecionadas:
                st.warning("Selecione ao menos uma turma antes de gerar o formulário.")
                return

            with st.spinner("Carregando alunos do sistema…"):
                for t in turmas_selecionadas:
                    alunos_t = _carregar_alunos_turma(t)
                    if alunos_t:
                        grupos.append({"turma": t, "alunos": alunos_t})

            if not grupos:
                st.warning("Nenhum aluno ativo encontrado nas turmas selecionadas.")
                return

            total_al = sum(len(g["alunos"]) for g in grupos)
            turmas_c_alunos = [g["turma"] for g in grupos]

            if "todas as turmas" in abrangencia:
                filtro_lbl = f"Todas as turmas ({len(grupos)} turmas, {total_al} alunos)"
            elif "uma turma" in abrangencia:
                filtro_lbl = turmas_selecionadas[0]
            else:
                nomes = " + ".join(turmas_c_alunos)
                filtro_lbl = f"Turmas: {nomes}"

            sem_alunos = [t for t in turmas_selecionadas if t not in turmas_c_alunos]
            if sem_alunos:
                st.warning(
                    f"⚠️ As seguintes turmas não têm alunos ativos e foram ignoradas: "
                    + ", ".join(sem_alunos)
                )

            n_turmas_final = len(grupos)
            st.success(
                f"✅ {total_al} aluno(s) carregado(s) de {n_turmas_final} turma(s)."
            )

        html_form = gerar_html_formulario(
            grupos          = grupos,
            professor       = professor,
            local           = local_str,
            modalidade      = modalidade,
            momento         = momento_str,
            data_coleta     = data_coleta.strftime("%d/%m/%Y"),
            hora_coleta     = hora_coleta,
            obs_gerais      = obs_gerais,
            n_linhas_vazias = int(n_linhas),
            filtro_label    = filtro_lbl,
        )

        st.session_state["pa_lote_html"]   = html_form
        st.session_state["pa_lote_gerado"] = True

    # ── Exibição do formulário ─────────────────────────────────────────────────
    if st.session_state.get("pa_lote_gerado") and st.session_state.get("pa_lote_html"):
        st.divider()
        st.info(
            "💡 Clique em **Imprimir / Salvar PDF** dentro do formulário. "
            "Na janela de impressão: **Orientação Paisagem (A4)**, margens 10 mm, "
            "desmarque 'Cabeçalhos e rodapés do navegador'.",
            icon="🖨️",
        )
        _html_v1(
            st.session_state["pa_lote_html"],
            height=860,
            scrolling=True,
        )
