# ==============================================================================
# 📄 Arquivo: gerador_pdf.py
# 📏 Mudança: Fix do ValueError do Pandas (DataFrame Ambiguous Truth Value)
# 📅 Versão: 7.3 (PRO Elite - Dossiê Clínico Completo & Pandas Blindado)
# ==============================================================================

import os
import requests
import tempfile
import datetime
import pandas as pd
from PIL import Image
import io
import re
from fpdf import FPDF
from database import (
    get_alunos_por_turma,
    get_presencas_dia,
    get_diario_dia,
    get_midias_diario,
)


class PDF(FPDF):
    def footer(self):
        try:
            from utils.identidade import get_config as _gci
            _c = _gci()
            l1 = limpar_texto(
                f"{_c.get('nome_organizacao','Instituto Muda Brasil')} | "
                f"{_c.get('titulo_projeto','ESPORTE E SAUDE NA COMUNIDADE FASE 2')}"
            )
            l2_parts = []
            if _c.get("cnpj"):
                l2_parts.append(f"CNPJ: {_c['cnpj']}")
            if _c.get("endereco"):
                l2_parts.append(_c["endereco"])
            if _c.get("site"):
                l2_parts.append(_c["site"])
            l2 = limpar_texto(" | ".join(l2_parts))
        except Exception:
            l1 = "Instituto Muda Brasil | ESPORTE E SAUDE NA COMUNIDADE FASE 2"
            l2 = "CNPJ: 08.817.519/0001-79 | R. Sapoti, 20 - Campo Belo - Sao Paulo - SP"
        self.set_y(-20)
        self.set_font("Arial", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 4, l1, align="C", ln=1)
        self.cell(0, 4, l2, align="C", ln=1)


def baixar_imagem_temp(url):
    if not url or not isinstance(url, str):
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url.strip(), headers=headers, timeout=15)
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(tmp.name, format="JPEG", quality=85)
            return tmp.name
    except:
        pass
    return None


def baixar_imagem_supabase(url):
    """
    Baixa imagem via httpx (mesmo stack de rede do supabase-py — contorna restrição DNS do sandbox).
    """
    if not url or not isinstance(url, str):
        return None
    try:
        import httpx
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get(url.strip())
            if r.status_code == 200:
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                img.save(tmp.name, format="JPEG", quality=85)
                return tmp.name
    except Exception:
        pass
    return None


# Códigos curtos para legenda de IMC no PDF (cabe em 18mm de coluna)
_IMC_CODES = {
    "Baixo peso":    "BP",
    "Normal":        "N",
    "Sobrepeso":     "SP",
    "Obesidade I":   "O1",
    "Obesidade II":  "O2",
    "Obesidade III": "O3",
}


def limpar_texto(texto):
    if not texto:
        return ""
    # Remove caracteres especiais ou emojis que o FPDF não suporta nativamente (latin-1)
    return str(texto).encode("latin-1", "replace").decode("latin-1")


def _cabecalho_padrao(pdf, subtitulo=""):
    """
    Cabeçalho padrão FPDF: logo_secundaria à esquerda, logo_principal à direita,
    título e subtítulo centralizados — lido do identidade.json.
    Devolve a coordenada Y após o cabeçalho.
    """
    try:
        from utils.identidade import get_config as _gci
        cfg = _gci()
    except Exception:
        cfg = {}

    titulo   = cfg.get("titulo_projeto",  "ESPORTE E SAUDE NA COMUNIDADE - FASE 2")
    sub      = subtitulo or cfg.get("subtitulo_projeto", "")
    logo_esq = cfg.get("logo_secundaria", "logo-secretaria.png")   # esquerda
    logo_dir = cfg.get("logo_principal",  "logo-imbra.png")        # direita
    logo_w   = 28  # largura de cada logo em mm

    # ── logo esquerda ─────────────────────────────────────────────────────
    for path in [logo_esq, logo_esq.replace(".png", ".jpg"), logo_esq.replace(".jpg", ".png")]:
        if path and os.path.exists(path):
            try:
                pdf.image(path, x=8, y=7, w=logo_w)
            except Exception:
                pass
            break

    # ── logo direita ──────────────────────────────────────────────────────
    for path in [logo_dir, logo_dir.replace(".png", ".jpg"), logo_dir.replace(".jpg", ".png")]:
        if path and os.path.exists(path):
            try:
                pdf.image(path, x=174, y=7, w=logo_w)
            except Exception:
                pass
            break

    # ── título centralizado (entre x=40 e x=170, largura=130 mm) ─────────
    pdf.set_xy(40, 11)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(10, 37, 64)
    pdf.multi_cell(130, 6, limpar_texto(titulo), align="C")

    if sub:
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.set_x(40)
        pdf.multi_cell(130, 5, limpar_texto(sub), align="C")

    # ── linha separadora azul ─────────────────────────────────────────────
    y_sep = max(pdf.get_y() + 2, 36)
    pdf.set_draw_color(0, 86, 179)
    pdf.set_line_width(0.6)
    pdf.line(8, y_sep, 202, y_sep)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.2)
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(y_sep + 4)
    return pdf.get_y()


def formatar_link_whatsapp(telefone_bruto):
    """Limpa o telefone e gera o link da API do WhatsApp"""
    if not telefone_bruto or pd.isna(telefone_bruto):
        return "-", ""

    numeros = re.sub(r'\D', '', str(telefone_bruto))

    if len(numeros) < 10:
        return "-", ""

    if len(numeros) <= 11:
        numeros = "55" + numeros

    link = f"https://wa.me/{numeros}"

    ddd = numeros[2:4]
    num = numeros[4:]
    if len(num) == 9:
        display = f"({ddd}) {num[:5]}-{num[5:]}"
    else:
        display = f"({ddd}) {num[:4]}-{num[4:]}"

    return display, link

# ==============================================================================
# 1. RELATÓRIO: DOSSIÊ DE AULA (TURMA)
# ==============================================================================
def criar_documento_pdf(data_aula, turma):
    pdf = PDF()
    pdf.add_page()
    _cabecalho_padrao(pdf)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, limpar_texto("DOSSIE OFICIAL DE AULA"), align="C", ln=1)
    pdf.ln(3)

    pdf.cell(15, 6, "Turma: ")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 6, limpar_texto(turma), ln=1)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(32, 6, "Data da Aula: ")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 6, f"{data_aula.strftime('%d/%m/%Y')}", ln=1)
    pdf.ln(5)

    diario = get_diario_dia(data_aula, turma)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, limpar_texto("1. Objetivo da Sessão"), ln=1)
    pdf.set_font("Arial", "", 12)
    obj_texto = diario["objetivo_geral"] if diario and diario.get("objetivo_geral") else "Nenhum objetivo tecnico."
    pdf.multi_cell(0, 6, limpar_texto(obj_texto), align="J")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, limpar_texto("2. Exercícios Executados na Prática"), ln=1)
    pdf.set_font("Arial", "", 12)
    exe_texto = diario.get("exercicios_executados", "") if diario else ""
    if not exe_texto:
        exe_texto = "Nenhum exercício especificado."
    pdf.multi_cell(0, 6, limpar_texto(exe_texto), align="J")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, limpar_texto("3. Registo de Frequência"), ln=1)
    df_alunos = get_alunos_por_turma(turma)
    if not df_alunos.empty:
        ids_turma = df_alunos["id"].tolist()
        presencas = get_presencas_dia(data_aula, ids_turma)
        presentes = [r["nome"] for _, r in df_alunos.iterrows() if presencas.get(r["id"], False)]
        ausentes = [r["nome"] for _, r in df_alunos.iterrows() if not presencas.get(r["id"], False)]

        pdf.set_font("Arial", "B", 12)
        pdf.write(6, f"Presentes ({len(presentes)}): ")
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 6, limpar_texto("; ".join([f"{i + 1}. {n}" for i, n in enumerate(presentes)])), align="J")
        pdf.ln(2)

        pdf.set_font("Arial", "B", 12)
        pdf.write(6, f"Ausentes ({len(ausentes)}): ")
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 6, limpar_texto("; ".join([f"{i + 1}. {n}" for i, n in enumerate(ausentes)])), align="J")
        pdf.ln(5)
    else:
        pdf.cell(0, 6, "Nenhum aluno cadastrado.", ln=1)
        pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, limpar_texto("4. Evidências Fotográficas"), ln=1)

    if diario:
        todas_fotos = []
        if diario.get("url_foto_grupo"):
            todas_fotos.append({"url": diario["url_foto_grupo"], "desc": "Grupo"})
        midias = get_midias_diario(diario.get("id"))
        if midias:
            for m in midias:
                if m.get("url_midia"):
                    todas_fotos.append({"url": m["url_midia"], "desc": m.get("descricao_objetivo", "Exercicio")})

        y_atual = pdf.get_y()
        for i, foto in enumerate(todas_fotos):
            if i % 2 == 0:
                if y_atual > 220:
                    pdf.add_page()
                    y_atual = pdf.get_y() + 5
                x_pos = 15
            else:
                x_pos = 110

            tmp = baixar_imagem_temp(foto["url"])
            if tmp:
                try:
                    pdf.image(tmp, x=x_pos, y=y_atual, w=85, h=60)
                    pdf.set_xy(x_pos, y_atual + 62)
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(85, 5, limpar_texto(foto["desc"]), align="C")
                except: pass
                finally:
                    try: os.remove(tmp)
                    except: pass
            if i % 2 != 0:
                y_atual += 75

    saida = pdf.output(dest="S")
    if isinstance(saida, str):
        return saida.encode("latin1")
    return bytes(saida)

# ==============================================================================
# 2. RELATÓRIO: DOSSIÊ CLÍNICO INDIVIDUAL DO ALUNO (v2 — Análise de Risco 60+)
# ==============================================================================
def criar_documento_aluno_pdf(aluno_data, avaliacoes, historico, estatisticas):
    """
    Dossie Clinico v2 — 6 secoes:
      1. Perfil Pessoal e Biometrico (com IMC + fatores de risco)
      2. Historico Clinico Completo (todas as medicoes)
      3. Frequencia — grafico de barras por mes (FPDF nativo)
      4. Diario de Aulas com Sinais de Risco (ombro/joelho/lombar)
      5. Analise de Risco Consolidada + Recomendacoes
      6. Resumo Executivo
    """
    import unicodedata
    from collections import defaultdict

    # ── Normalização de tipos ─────────────────────────────────────────────────
    if isinstance(avaliacoes, pd.DataFrame):
        avaliacoes = avaliacoes.to_dict("records")
    if isinstance(historico, pd.DataFrame):
        historico = historico.to_dict("records")
    avaliacoes = avaliacoes or []
    historico  = historico  or []

    # ── Palavras-chave de risco ───────────────────────────────────────────────
    _KW_OMBRO_ALTO = [
        "elevacao lateral", "elevacao frontal", "elevacao", "acima da cabeca",
        "acima do ombro", "desenvolvimento", "press militar", "ombro acima",
        "bastao acima", "remada alta", "frontal acima", "lateral acima",
    ]
    _KW_OMBRO_MOD = [
        "remada", "elastico", "haltere", "halter", "supino",
        "rosca", "triceps", "biceps", "puxada", "ombro",
    ]
    _KW_JOELHO = [
        "agachamento profundo", "agachamento", "salto", "corrida", "impacto",
        "flexao profunda", "pliometria", "step", "leg press", "extensao joelho",
    ]
    _KW_LOMBAR = [
        "flexao de tronco", "inclinacao", "dead lift", "peso morto",
        "hiperextensao", "abdominal dinamico", "prancha dinamica",
    ]
    _COR_RISCO  = {
        "OMBRO-ALTO": (180, 0,   0),
        "OMBRO-MOD":  (200, 100, 0),
        "JOELHO":     (140, 0,   140),
        "LOMBAR":     (100, 80,  0),
    }
    _LABEL_RISCO = {
        "OMBRO-ALTO": "[RISCO ALTO - OMBRO]",
        "OMBRO-MOD":  "[RISCO MODERADO - OMBRO]",
        "JOELHO":     "[ATENCAO - JOELHO]",
        "LOMBAR":     "[ATENCAO - LOMBAR]",
    }

    def _normalizar(txt):
        return "".join(
            c for c in unicodedata.normalize("NFKD", str(txt).lower())
            if not unicodedata.combining(c)
        )

    def _risco_exercicio(texto):
        """Retorna lista de (codigo, descricao) de alertas para o texto de exercicios."""
        if not texto:
            return []
        t = _normalizar(texto)
        alertas = []
        for kw in _KW_OMBRO_ALTO:
            if kw in t:
                alertas.append(("OMBRO-ALTO", "Exercicio acima da linha do ombro: " + kw.title()))
                break
        for kw in _KW_OMBRO_MOD:
            if kw in t and not any(a[0] == "OMBRO-ALTO" for a in alertas):
                alertas.append(("OMBRO-MOD", "Exercicio com solicitacao do ombro: " + kw.title()))
                break
        for kw in _KW_JOELHO:
            if kw in t:
                alertas.append(("JOELHO", "Exercicio de impacto/flexao no joelho: " + kw.title()))
                break
        for kw in _KW_LOMBAR:
            if kw in t:
                alertas.append(("LOMBAR", "Exercicio com carga na lombar: " + kw.title()))
                break
        return alertas

    def _imc_class(imc):
        if imc < 22:  return "Baixo peso (< 22)"
        if imc < 27:  return "Normal (22-27)"
        if imc < 30:  return "Sobrepeso (27-30)"
        if imc < 35:  return "Obesidade I (30-35)"
        return "Obesidade II/III (>= 35)"

    def _safe_float(v, default=0.0):
        try:
            import math
            f = float(v)
            return default if (math.isnan(f) or math.isinf(f)) else f
        except Exception:
            return default

    def _safe_str(v, default="Nao informado"):
        s = str(v).strip() if v is not None else ""
        return s if s and s.lower() not in ("nan", "none", "null", "") else default

    def _dt_str(v):
        if isinstance(v, (datetime.date, datetime.datetime)):
            return v.strftime("%d/%m/%Y")
        if isinstance(v, str) and len(v) >= 10:
            try:
                return datetime.datetime.strptime(v[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                pass
        return str(v)

    def _secao(pdf, numero, titulo):
        if pdf.get_y() > 255:
            pdf.add_page()
        pdf.ln(4)
        pdf.set_fill_color(10, 37, 64)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, limpar_texto(f"  {numero}. {titulo}"), ln=1, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    def _kv(pdf, chave, valor, negrito_valor=False, cor_valor=None):
        pdf.set_font("Arial", "B", 10)
        pdf.write(5, limpar_texto(chave + ": "))
        pdf.set_font("Arial", "B" if negrito_valor else "", 10)
        if cor_valor:
            pdf.set_text_color(*cor_valor)
        pdf.multi_cell(0, 5, limpar_texto(str(valor)))
        pdf.set_text_color(0, 0, 0)

    # ── Construção do PDF ─────────────────────────────────────────────────────
    pdf = PDF()
    pdf.add_page()
    _cabecalho_padrao(pdf)

    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(10, 37, 64)
    pdf.cell(0, 8, limpar_texto("DOSSIE CLINICO E DESPORTIVO DO ALUNO"), align="C", ln=1)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5,
             limpar_texto(f"Gerado em: {datetime.date.today().strftime('%d/%m/%Y')}  |  Sistema IMBRA — Esporte e Saude 60+"),
             align="C", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. PERFIL PESSOAL E BIOMÉTRICO
    # ══════════════════════════════════════════════════════════════════════════
    _secao(pdf, 1, "Perfil Pessoal e Biometrico")

    y_foto = pdf.get_y()
    foto_url = aluno_data.get("foto_url")
    if pd.notna(foto_url) and str(foto_url).strip() not in ("", "nan", "none", "null"):
        foto_tmp = baixar_imagem_supabase(str(foto_url)) or baixar_imagem_temp(str(foto_url))
        if foto_tmp:
            try:
                pdf.image(foto_tmp, x=163, y=y_foto, w=35, h=35)
                pdf.rect(163, y_foto, 35, 35)
            except Exception:
                pass
            finally:
                try:
                    os.remove(foto_tmp)
                except Exception:
                    pass

    # ── Dados básicos ─────────────────────────────────────────────────────────
    nasc = aluno_data.get("data_nascimento")
    nasc_str, idade = "Nao informado", None
    if pd.notna(nasc) and str(nasc).strip():
        try:
            dt_nasc = pd.to_datetime(nasc).date()
            hoje = datetime.date.today()
            idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
            nasc_str = f"{dt_nasc.strftime('%d/%m/%Y')} ({idade} anos)"
        except Exception:
            pass

    peso   = _safe_float(aluno_data.get("peso"))
    altura = _safe_float(aluno_data.get("altura"))
    imc_str, imc_class_str = "Nao calculado", ""
    if peso > 0 and altura > 0.5:
        imc = peso / (altura ** 2)
        imc_str       = f"{imc:.1f} kg/m²"
        imc_class_str = _imc_class(imc)

    pres_total = estatisticas.get("presentes", 0)  if estatisticas else 0
    faltas     = estatisticas.get("faltas",    0)   if estatisticas else 0
    pct        = estatisticas.get("percentual", 0.0) if estatisticas else 0.0

    _kv(pdf, "Nome",   aluno_data.get("nome", "Nao informado"))
    _kv(pdf, "Turma",  aluno_data.get("turma", "Nao informado"))
    _kv(pdf, "Nascimento", nasc_str)
    _kv(pdf, "Peso",   f"{peso:.1f} kg" if peso > 0 else "Nao informado")
    _kv(pdf, "Altura", f"{altura:.2f} m" if altura > 0.5 else "Nao informado")
    _kv(pdf, "IMC",    f"{imc_str}  [{imc_class_str}]" if imc_class_str else imc_str,
        cor_valor=(34, 100, 34) if imc_class_str == "Normal (22-27)" else (180, 80, 0))
    _kv(pdf, "Frequencia", f"{pres_total} presencas | {faltas} faltas | {pct:.1f}%",
        cor_valor=(34, 139, 34) if pct >= 75 else (180, 0, 0))

    # ── Fatores de risco da última avaliação ──────────────────────────────────
    if avaliacoes:
        ultima = avaliacoes[0]
        cir   = _safe_str(ultima.get("cirurgias") or ultima.get("cirurgias_lesoes"))
        meds  = _safe_str(ultima.get("medicamentos") or ultima.get("observacoes"))
        dor_u = int(_safe_float(ultima.get("dor_nivel") or ultima.get("nivel_dor")))
        qued  = int(_safe_float(ultima.get("quedas_6m")))
        pdf.ln(1)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(255, 245, 220)
        pdf.cell(0, 6, limpar_texto("  Fatores de Risco (ultima avaliacao)"), ln=1, fill=True)
        pdf.ln(1)
        dor_cor = (34, 139, 34) if dor_u <= 3 else ((220, 120, 0) if dor_u <= 6 else (180, 0, 0))
        _kv(pdf, "Nivel de Dor atual", f"{dor_u}/10", cor_valor=dor_cor)
        _kv(pdf, "Quedas (ult. 6 meses)", f"{qued} queda(s)",
            cor_valor=(180, 0, 0) if qued > 0 else (34, 139, 34))
        _kv(pdf, "Cirurgias / Lesoes", cir)
        _kv(pdf, "Medicamentos / Obs.", meds)

    if pdf.get_y() < y_foto + 40:
        pdf.set_y(y_foto + 42)

    # ══════════════════════════════════════════════════════════════════════════
    # 2. HISTÓRICO CLÍNICO COMPLETO
    # ══════════════════════════════════════════════════════════════════════════
    _secao(pdf, 2, "Historico Clinico Completo — Todas as Medicoes")

    if avaliacoes:
        for idx, av in enumerate(avaliacoes):
            if pdf.get_y() > 245:
                pdf.add_page()

            dt_av = _dt_str(av.get("data_avaliacao", ""))

            pdf.set_fill_color(220, 235, 255)
            pdf.set_font("Arial", "B", 10)
            pdf.set_text_color(10, 37, 64)
            pdf.cell(0, 6, limpar_texto(f"  Avaliacao #{idx + 1}  —  {dt_av}"), ln=1, fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

            dor  = int(_safe_float(av.get("dor_nivel")  or av.get("nivel_dor")))
            tug1 = _safe_float(av.get("tug_simples")    or av.get("tug_segundos"))
            tug2 = _safe_float(av.get("tug_cog_animais"))
            tug3 = _safe_float(av.get("tug_cog_perguntas"))
            qued = int(_safe_float(av.get("quedas_6m")))
            f_d  = int(_safe_float(av.get("forca_dir")  or av.get("simetria_dir")))
            f_e  = int(_safe_float(av.get("forca_esq")  or av.get("simetria_esq")))
            mob_d   = _safe_str(av.get("mobilidade_pes_dir"), "—")
            mob_e   = _safe_str(av.get("mobilidade_pes_esq"), "—")
            borg    = _safe_str(av.get("borg"),    "—")
            bristol = _safe_str(av.get("bristol"), "—")
            urina   = _safe_str(av.get("urina"),   "—")
            cir  = _safe_str(av.get("cirurgias")    or av.get("cirurgias_lesoes"))
            meds = _safe_str(av.get("medicamentos") or av.get("observacoes"))

            dor_cor = (34, 139, 34) if dor <= 3 else ((220, 120, 0) if dor <= 6 else (180, 0, 0))

            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Dor: ")
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(*dor_cor)
            pdf.write(5, f"{dor}/10")
            pdf.set_text_color(0, 0, 0)
            pdf.write(5, f"   |   Quedas 6m: {qued}")
            pdf.ln(5)

            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "TUG Simples: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{tug1:.1f}s   ")
            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Cog. Animais: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{tug2:.1f}s   ")
            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Cog. Perguntas: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{tug3:.1f}s")
            pdf.ln(5)

            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Forca Direita: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{f_d} reps   ")
            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Forca Esquerda: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{f_e} reps")
            pdf.ln(5)

            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Mobilidade D: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{mob_d}   ")
            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Mobilidade E: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{mob_e}")
            pdf.ln(5)

            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Borg: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{borg}   ")
            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Bristol: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{bristol}   ")
            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Urina: ")
            pdf.set_font("Arial", "", 9)
            pdf.write(5, f"{urina}")
            pdf.ln(5)

            if cir != "Nao informado":
                pdf.set_font("Arial", "B", 9)
                pdf.write(5, "Cirurgias/Lesoes: ")
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(0, 5, limpar_texto(cir))
            if meds != "Nao informado":
                pdf.set_font("Arial", "B", 9)
                pdf.write(5, "Medicamentos/Obs: ")
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(0, 5, limpar_texto(meds))
            pdf.ln(2)
    else:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpar_texto("Nenhuma avaliacao clinica registrada."), ln=1)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. FREQUÊNCIA — GRÁFICO DE BARRAS POR MÊS (FPDF nativo)
    # ══════════════════════════════════════════════════════════════════════════
    _secao(pdf, 3, "Frequencia — Grafico de Presencas por Mes")

    meses_cnt = defaultdict(int)
    for h in historico:
        try:
            dt = h.get("data_aula", "")
            if isinstance(dt, (datetime.date, datetime.datetime)):
                chave = dt.strftime("%m/%Y")
            else:
                chave = datetime.datetime.strptime(str(dt)[:10], "%Y-%m-%d").strftime("%m/%Y")
            meses_cnt[chave] += 1
        except Exception:
            continue

    if meses_cnt:
        meses_ord = sorted(
            meses_cnt.keys(),
            key=lambda x: datetime.datetime.strptime(x, "%m/%Y")
        )
        max_qtd  = max(meses_cnt.values()) or 1
        bar_maxw = 120
        bar_h    = 6
        x_label  = 10
        x_bar    = 50

        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 5, limpar_texto(
            f"Total: {pres_total} presencas  |  {faltas} faltas  |  Assiduidade: {pct:.1f}%"
        ), ln=1)
        pdf.ln(2)

        for mes in meses_ord:
            qtd   = meses_cnt[mes]
            bar_w = max(1, int((qtd / max_qtd) * bar_maxw))
            if pdf.get_y() > 272:
                pdf.add_page()
            y_b = pdf.get_y()
            pdf.set_font("Arial", "", 8)
            pdf.set_xy(x_label, y_b)
            pdf.cell(38, bar_h, limpar_texto(mes), align="R")
            # Barra preenchida (azul IMBRA)
            pdf.set_fill_color(30, 136, 229)
            pdf.rect(x_bar, y_b + 1, bar_w, bar_h - 2, style="F")
            # Contorno total
            pdf.set_draw_color(100, 149, 200)
            pdf.rect(x_bar, y_b + 1, bar_maxw, bar_h - 2)
            pdf.set_draw_color(0, 0, 0)
            # Quantidade
            pdf.set_xy(x_bar + bar_maxw + 3, y_b)
            pdf.set_font("Arial", "B", 8)
            pdf.cell(15, bar_h, f"{qtd}x", align="L")
            pdf.set_y(y_b + bar_h)
        pdf.ln(3)
    else:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpar_texto("Nenhuma presenca registrada para gerar grafico."), ln=1)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. DIÁRIO DE AULAS COM SINAIS DE RISCO CLÍNICO
    # ══════════════════════════════════════════════════════════════════════════
    _secao(pdf, 4, "Diario de Aulas com Sinais de Risco Clinico")

    alertas_globais = []

    if historico:
        for h in historico:
            if pdf.get_y() > 248:
                pdf.add_page()

            dt_h    = _dt_str(h.get("data_aula", ""))
            obj     = _safe_str(h.get("objetivo_geral"),         "Sem objetivo registrado")
            exc     = _safe_str(h.get("exercicios_executados"),  "")
            foco    = _safe_str(h.get("foco_clinico_social"),    "")
            relatos = _safe_str(h.get("relatos_melhora"),        "")

            alertas = _risco_exercicio(exc)
            alertas_globais.extend([(dt_h, a) for a in alertas])

            # Cabeçalho da aula — cor conforme risco
            fill_r = (255, 230, 230) if any(a[0] == "OMBRO-ALTO" for a in alertas) else \
                     (255, 245, 220) if alertas else (235, 245, 255)
            pdf.set_fill_color(*fill_r)
            pdf.set_font("Arial", "B", 10)
            pdf.set_text_color(30, 136, 229)
            pdf.cell(0, 6, limpar_texto(f"  Aula de {dt_h}"), ln=1, fill=True)
            pdf.set_text_color(0, 0, 0)

            pdf.set_font("Arial", "B", 9)
            pdf.write(5, "Objetivo: ")
            pdf.set_font("Arial", "", 9)
            pdf.multi_cell(0, 5, limpar_texto(obj))

            if exc and exc != "Nao informado":
                pdf.set_font("Arial", "B", 9)
                pdf.write(5, limpar_texto("Exercicios: "))
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(0, 5, limpar_texto(exc))

            for codigo, descricao in alertas:
                pdf.set_font("Arial", "B", 9)
                pdf.set_text_color(*_COR_RISCO.get(codigo, (150, 0, 0)))
                pdf.write(5, limpar_texto(f"  {_LABEL_RISCO.get(codigo, '[RISCO]')} "))
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(0, 5, limpar_texto(descricao))
                pdf.set_text_color(0, 0, 0)

            if foco and foco != "Nao informado":
                pdf.set_font("Arial", "B", 9)
                pdf.write(5, "Foco Clinico: ")
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(0, 5, limpar_texto(foco))

            if relatos and relatos != "Nao informado":
                pdf.set_font("Arial", "B", 9)
                pdf.write(5, "Relatos de Melhora: ")
                pdf.set_font("Arial", "I", 9)
                pdf.multi_cell(0, 5, limpar_texto(relatos))
                pdf.set_font("Arial", "", 9)

            pdf.ln(2)
    else:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpar_texto("Nenhuma participacao com diario registrada."), ln=1)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. ANÁLISE DE RISCO CONSOLIDADA
    # ══════════════════════════════════════════════════════════════════════════
    _secao(pdf, 5, "Analise de Risco Consolidada e Recomendacoes")

    codigos_encontrados = {a[0] for _, a in alertas_globais}

    if alertas_globais:
        grupos = defaultdict(list)
        for dt_h, (codigo, descricao) in alertas_globais:
            grupos[codigo].append((dt_h, descricao))

        for cod in ["OMBRO-ALTO", "OMBRO-MOD", "JOELHO", "LOMBAR"]:
            if cod not in grupos:
                continue
            registros = grupos[cod]
            if pdf.get_y() > 255:
                pdf.add_page()
            pdf.set_font("Arial", "B", 10)
            pdf.set_text_color(*_COR_RISCO.get(cod, (0, 0, 0)))
            pdf.cell(0, 6,
                     limpar_texto(f"{_LABEL_RISCO.get(cod, cod)}  —  {len(registros)} ocorrencia(s)"),
                     ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "", 9)
            for dt_h, desc in registros[:8]:
                pdf.cell(0, 5, limpar_texto(f"    . {dt_h}: {desc}"), ln=1)
            if len(registros) > 8:
                pdf.cell(0, 5, limpar_texto(f"    ... e mais {len(registros) - 8} ocorrencia(s)"), ln=1)
            pdf.ln(2)

        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(10, 37, 64)
        pdf.cell(0, 6, limpar_texto("Recomendacoes clinicas:"), ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 9)

        if "OMBRO-ALTO" in codigos_encontrados:
            pdf.multi_cell(0, 5, limpar_texto(
                "  [OMBRO] PRIORITARIO: Evitar exercicios acima da linha do ombro. "
                "Substituir por movimentos com abducao/flexao abaixo de 90 graus. "
                "Verificar laudo ortopedico antes de retomada."
            ))
        if "OMBRO-MOD" in codigos_encontrados:
            pdf.multi_cell(0, 5, limpar_texto(
                "  [OMBRO] Monitorar queixas durante remadas e exercicios com halteres. "
                "Reduzir carga e amplitude ao menor sinal de dor."
            ))
        if "JOELHO" in codigos_encontrados:
            pdf.multi_cell(0, 5, limpar_texto(
                "  [JOELHO] Evitar agachamentos profundos e impacto. "
                "Priorizar fortalecimento isometrico e amplitude parcial."
            ))
        if "LOMBAR" in codigos_encontrados:
            pdf.multi_cell(0, 5, limpar_texto(
                "  [LOMBAR] Manter coluna em posicao neutra. "
                "Evitar flexao forcada de tronco com carga."
            ))
    else:
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(34, 139, 34)
        pdf.cell(0, 6, limpar_texto(
            "Nenhum exercicio de risco identificado no historico registrado."
        ), ln=1)
        pdf.set_text_color(0, 0, 0)

    # ══════════════════════════════════════════════════════════════════════════
    # 6. RESUMO EXECUTIVO
    # ══════════════════════════════════════════════════════════════════════════
    _secao(pdf, 6, "Resumo Executivo — Perfil Funcional e Proxima Fase")

    # IMC
    _kv(pdf, "IMC",
        f"{imc_str}  —  {imc_class_str}" if imc_class_str else "Nao calculado (peso/altura ausentes)",
        cor_valor=(34, 100, 34) if imc_class_str == "Normal (22-27)" else (180, 80, 0))

    # Frequência
    freq_class = ("Excelente (>= 80%)" if pct >= 80
                  else ("Regular (50-79%)" if pct >= 50 else "Baixa (< 50%)"))
    freq_cor   = (34, 139, 34) if pct >= 80 else ((220, 120, 0) if pct >= 50 else (180, 0, 0))
    _kv(pdf, "Assiduidade",
        f"{pct:.1f}%  —  {freq_class}  ({pres_total} presencas / {faltas} faltas)",
        cor_valor=freq_cor)

    # Tendência de dor
    if len(avaliacoes) >= 2:
        dor_ini = _safe_float(avaliacoes[-1].get("dor_nivel") or avaliacoes[-1].get("nivel_dor"))
        dor_fin = _safe_float(avaliacoes[0].get("dor_nivel")  or avaliacoes[0].get("nivel_dor"))
        if dor_fin < dor_ini:
            tend, t_cor = f"Melhora ({dor_ini:.0f}/10 -> {dor_fin:.0f}/10)", (34, 139, 34)
        elif dor_fin > dor_ini:
            tend, t_cor = f"Piora ({dor_ini:.0f}/10 -> {dor_fin:.0f}/10)", (180, 0, 0)
        else:
            tend, t_cor = f"Estavel ({dor_fin:.0f}/10)", (100, 100, 100)
        _kv(pdf, "Tendencia de Dor", tend, cor_valor=t_cor)

    # Riscos
    if codigos_encontrados:
        _kv(pdf, "Riscos Identificados",
            ", ".join(_LABEL_RISCO.get(c, c) for c in codigos_encontrados),
            cor_valor=(180, 0, 0))
    else:
        _kv(pdf, "Riscos Identificados", "Nenhum critico identificado no historico",
            cor_valor=(34, 139, 34))

    # Recomendações finais
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(10, 37, 64)
    pdf.cell(0, 6, limpar_texto("Recomendacoes para a proxima fase:"), ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)

    recs = [
        "Monitorar nivel de dor no inicio e fim de cada aula (escala 0-10).",
        "Registrar queixas e relatos de melhora no diario de bordo de cada sessao.",
        "Manter frequencia acima de 75% para garantir progressao funcional continua.",
    ]
    if "OMBRO-ALTO" in codigos_encontrados:
        recs.insert(0, "PRIORITARIO: Revisar protocolo — exercicios acima do ombro identificados. Consultar laudo ortopedico.")
    if "OMBRO-MOD" in codigos_encontrados or "OMBRO-ALTO" in codigos_encontrados:
        recs.append("Considerar encaminhamento para fisioterapia de ombro se dor persistir acima de 4/10.")
    if pct < 75:
        recs.append("Investigar motivos das faltas — considerar ligacao de acolhimento ou atendimento individual.")
    if len(avaliacoes) == 0:
        recs.append("Realizar avaliacao clinica inicial completa (medicao, TUG, forca, biofeedback).")
    elif len(avaliacoes) == 1:
        recs.append("Repetir avaliacao clinica para iniciar acompanhamento de evolucao.")

    for i, rec in enumerate(recs, 1):
        pdf.multi_cell(0, 5, limpar_texto(f"  {i}. {rec}"))

    pdf.ln(5)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 5, limpar_texto(
        "Este dossie foi gerado automaticamente pelo sistema IMBRA com base nos dados clinicos e de frequencia "
        "registrados pelos profissionais responsaveis. Nao substitui avaliacao medica presencial."
    ))

    saida = pdf.output(dest="S")
    if isinstance(saida, str):
        return saida.encode("latin1")
    return bytes(saida)

# ==============================================================================
# 3. RELATÓRIO: GERENCIAL (CRM)
# ==============================================================================
def criar_relatorio_gerencial_pdf(df_alunos, titulo_relatorio="Relatório Gerencial"):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    total_alunos = len(df_alunos)

    _cabecalho_padrao(pdf)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 8, txt=limpar_texto(titulo_relatorio), ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(190, 6, txt=f"Gerado em: {datetime.date.today().strftime('%d/%m/%Y')}   |   Total de Alunos: {total_alunos}", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(30, 136, 229) 
    pdf.set_text_color(255, 255, 255)

    pdf.cell(55, 8, "Nome do Aluno", border=1, fill=True)
    pdf.cell(30, 8, "Turma", border=1, align="C", fill=True)
    pdf.cell(25, 8, limpar_texto("Última Medição"), border=1, align="C", fill=True)
    pdf.cell(25, 8, "Dias Decorridos", border=1, align="C", fill=True)
    pdf.cell(20, 8, "Aulas", border=1, align="C", fill=True) 
    pdf.cell(35, 8, "WhatsApp (Clique)", border=1, align="C", fill=True) 
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(15, 23, 42)

    for i, (_, row) in enumerate(df_alunos.iterrows()):
        nome_str = str(row.get("nome", "Não informado"))
        nome_numerado = f"{i + 1}. {nome_str}"
        nome = nome_numerado[:35]

        turma = str(row.get("turma", ""))[:15]

        dt_av = row.get("data_avaliacao")
        if pd.isna(dt_av):
            data_str = limpar_texto("Sem medição")
            dias_str = "-"
            dias_passados = 0
        else:
            data_str = dt_av.strftime("%d/%m/%Y")
            dias_passados = int(row.get("dias_passados", 0))
            dias_str = f"{dias_passados} dias"

        presencas = int(row.get("total_presencas", 0)) if pd.notna(row.get("total_presencas")) else 0
        aulas_str = f"{presencas} aulas"

        telefone_bruto = row.get("telefone") or row.get("celular") or row.get("whatsapp") or row.get("contato") or ""
        whats_display, whats_link = formatar_link_whatsapp(telefone_bruto)

        pdf.cell(55, 8, limpar_texto(nome), border=1)
        pdf.set_text_color(15, 23, 42) 
        pdf.cell(30, 8, limpar_texto(turma), border=1, align="C")
        pdf.cell(25, 8, data_str, border=1, align="C")

        if not pd.isna(dt_av) and dias_passados >= 90:
            pdf.set_text_color(185, 28, 28)
        pdf.cell(25, 8, dias_str, border=1, align="C")
        pdf.set_text_color(15, 23, 42) 

        pdf.cell(20, 8, aulas_str, border=1, align="C")

        if whats_link:
            pdf.set_text_color(30, 136, 229) 
            pdf.set_font("Arial", "U", 8)    
            pdf.cell(35, 8, whats_display, border=1, align="C", link=whats_link)
            pdf.set_font("Arial", "", 8)     
            pdf.set_text_color(15, 23, 42)   
        else:
            pdf.cell(35, 8, "-", border=1, align="C")

        pdf.ln()

    saida = pdf.output(dest="S")
    if isinstance(saida, str):
        return saida.encode("latin1")
    return bytes(saida)

# ==============================================================================
# 4. RELATÓRIO: DOSSIÊ DA TURMA POR PERÍODO (Com Evasão/Assiduidade)
# ==============================================================================
def criar_dossie_turma_periodo_pdf(turma, data_inicio, data_fim, diarios, df_estatisticas):
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    # --- CABEÇALHO ---
    _cabecalho_padrao(pdf)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 8, txt=limpar_texto("DOSSIE DA TURMA POR PERIODO"), ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 116, 139)
    periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
    pdf.cell(190, 6, txt=limpar_texto(f"Turma: {turma}   |   Periodo: {periodo_str}"), ln=True, align="C")
    pdf.ln(5)

    # --- 1. DIÁRIOS DE BORDO ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, limpar_texto(" 1. Diários de Bordo (Conteúdo Programático)"), ln=1, fill=True)
    pdf.ln(4)

    # 🚀 FIX PANDAS
    if isinstance(diarios, pd.DataFrame):
        diarios = diarios.to_dict('records')

    if diarios and len(diarios) > 0:
        for d in diarios:
            data_aula = d.get("data_aula")
            if isinstance(data_aula, datetime.date) or isinstance(data_aula, datetime.datetime):
                data_aula = data_aula.strftime("%d/%m/%Y")
            elif isinstance(data_aula, str) and "-" in data_aula:
                # Converte de YYYY-MM-DD para DD/MM/YYYY caso venha como string do banco
                try: data_aula = datetime.datetime.strptime(data_aula, "%Y-%m-%d").strftime("%d/%m/%Y")
                except: pass

            # Quebra de página de segurança se estiver muito perto do rodapé
            if pdf.get_y() > 250:
                pdf.add_page()

            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(30, 136, 229)
            pdf.cell(0, 6, limpar_texto(f"▶ Aula de {data_aula}:"), ln=1)
            pdf.set_text_color(0, 0, 0)

            obj = d.get("objetivo_geral")
            exe = d.get("exercicios_executados")

            pdf.set_font("Arial", "B", 10)
            pdf.write(5, "Objetivo: ")
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, limpar_texto(obj if obj else "Não informado."))

            pdf.set_font("Arial", "B", 10)
            pdf.write(5, limpar_texto("Exercícios: "))
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, limpar_texto(exe if exe else "Não informado."))
            pdf.ln(4)
    else:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpar_texto("Nenhum diário registrado neste período."), ln=1)

    pdf.ln(5)

    # --- 2. RELATÓRIO DE EVASÃO E ASSIDUIDADE ---
    # Forçamos uma nova página se não houver espaço suficiente para a tabela
    if pdf.get_y() > 200:
        pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, limpar_texto(" 2. Relatório de Evasão e Assiduidade"), ln=1, fill=True)
    pdf.ln(4)

    if not df_estatisticas.empty:
        # Cabeçalho da Tabela
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(30, 136, 229)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(85, 8, "Nome do Aluno", border=1, fill=True)
        pdf.cell(25, 8, limpar_texto("Presenças"), border=1, align="C", fill=True)
        pdf.cell(25, 8, "Faltas", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Total Aulas", border=1, align="C", fill=True)
        pdf.cell(30, 8, limpar_texto("Taxa (%)"), border=1, align="C", fill=True)
        pdf.ln()

        # Linhas da Tabela
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(0, 0, 0)

        # Ordenar por nome antes de imprimir
        df_estatisticas = df_estatisticas.sort_values(by="nome")

        for _, row in df_estatisticas.iterrows():
            nome = str(row.get('nome', ''))[:45]
            presencas = int(row.get('presencas', 0))
            faltas = int(row.get('faltas', 0))
            total = presencas + faltas
            taxa = f"{(presencas/total * 100):.1f}%" if total > 0 else "0.0%"

            pdf.cell(85, 8, limpar_texto(nome), border=1)

            pdf.cell(25, 8, str(presencas), border=1, align="C")

            # Destacar faltas em vermelho se houver
            if faltas > 0: pdf.set_text_color(185, 28, 28)
            pdf.cell(25, 8, str(faltas), border=1, align="C")
            pdf.set_text_color(0, 0, 0) # Volta pro preto

            pdf.cell(25, 8, str(total), border=1, align="C")
            pdf.cell(30, 8, taxa, border=1, align="C")
            pdf.ln()
    else:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpar_texto("Sem dados de frequência para esta turma no período."), ln=1)

    saida = pdf.output(dest="S")
    if isinstance(saida, str):
        return saida.encode("latin1")
    return bytes(saida)

# ==============================================================================
# 🚀 NOVO: LISTA DE AÇÃO INTERATIVA (PDF CLICÁVEL PARA WHATSAPP)
# ==============================================================================
import re

def criar_lista_acao_evasao_pdf(df, categoria, data_inicio, data_fim, turma):
    from fpdf import FPDF

    # Herda a classe PDF para manter o cabeçalho e rodapé do Instituto
    pdf = PDF()
    pdf.add_page()

    # Título do Relatório
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(30, 136, 229) # Azul
    pdf.cell(0, 8, "LISTA DE AÇÃO - RISCO DE EVASÃO", align="C", ln=1)

    # Subtítulo (Métricas)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(185, 28, 28) # Vermelho Alerta
    pdf.cell(0, 6, f"Categoria Foco: {categoria} ({len(df)} alunos)", align="C", ln=1)

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 100, 100)
    periodo = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
    pdf.cell(0, 5, f"Turma: {turma} | Período: {periodo}", align="C", ln=1)
    pdf.ln(5)

    # Cabeçalho da Tabela
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(10, 37, 64)

    pdf.cell(75, 8, "Nome do Aluno", border=1, align="L", fill=True)
    pdf.cell(35, 8, "Turma", border=1, align="C", fill=True)
    pdf.cell(25, 8, "Ausência", border=1, align="C", fill=True)
    pdf.cell(55, 8, "Ação (Clique para falar)", border=1, align="C", fill=True)
    pdf.ln()

    # Preenchimento Dinâmico e Links do WhatsApp
    pdf.set_font("Arial", "", 9)

    for _, row in df.iterrows():
        nome = str(row.get('Nome do Aluno', ''))[:35]
        turma_abrev = str(row.get('Turma', ''))[:10]
        faltas = f"{row.get('% Faltas', 0):.1f}%"

        # Limpeza do número para criar a URL do WhatsApp
        whats_raw = str(row.get('WhatsApp', ''))
        whats_limpo = re.sub(r'\D', '', whats_raw)

        pdf.set_text_color(0, 0, 0)
        pdf.cell(75, 8, nome, border=1)
        pdf.cell(35, 8, turma_abrev, border=1, align="C")

        pdf.set_text_color(185, 28, 28) # Faltas em Vermelho
        pdf.cell(25, 8, faltas, border=1, align="C")

        # 🚀 A MÁGICA: O LINK CLICÁVEL NO PDF
        if len(whats_limpo) >= 10:
            if len(whats_limpo) <= 11: whats_limpo = "55" + whats_limpo
            link_whatsapp = f"https://wa.me/{whats_limpo}"

            pdf.set_text_color(37, 211, 102) # Verde WhatsApp
            pdf.set_font("Arial", "B", 9)
            pdf.cell(55, 8, "Chamar no WhatsApp >", border=1, align="C", link=link_whatsapp)
            pdf.set_font("Arial", "", 9)
        else:
            pdf.set_text_color(150, 150, 150)
            pdf.cell(55, 8, "Sem número válido", border=1, align="C")

        pdf.ln()

    # Saída do PDF (compatível com PyFPDF e FPDF2)
    try:
        return pdf.output(dest='S').encode('latin-1')
    except:
        return bytes(pdf.output())


# ==============================================================================
# RELATÓRIO: PRESTAÇÃO DE CONTAS DIÁRIA — Lista de Presença por Dia
# ==============================================================================
def _pagina_prestacao_diaria(pdf: FPDF, data_fmt: str, nomes: list):
    """Renderiza uma página completa de presença para um único dia."""
    _cabecalho_padrao(pdf, subtitulo="PLANILHA DE FREQUENCIA DIARIA")

    # Faixa azul com data
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, limpar_texto(f"  Lista de Presenca  -  {data_fmt}"), fill=True, ln=1)
    pdf.ln(2)

    # Sub-header totalizador
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 6, limpar_texto(f"Total de alunos presentes: {len(nomes)}"), ln=1)
    pdf.ln(3)

    # Cabeçalho da tabela
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(14, 7, "#", border=1, fill=True, align="C")
    pdf.cell(176, 7, limpar_texto("NOME DO ALUNO"), border=1, fill=True, align="L")
    pdf.ln()

    # Linhas de dados
    pdf.set_text_color(0, 0, 0)
    for i, nome in enumerate(nomes, 1):
        if i % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(14, 6.5, str(i), border=1, fill=True, align="C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(176, 6.5, limpar_texto(nome.upper()), border=1, fill=True, align="L")
        pdf.ln()


def criar_prestacao_diaria_pdf(data_fmt: str, nomes: list) -> bytes:
    """
    Gera PDF de um único dia (mantido para compatibilidade retroativa).
    """
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    _pagina_prestacao_diaria(pdf, data_fmt, nomes)
    try:
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return bytes(pdf.output())


def _grafico_linha_presencas(pdf: FPDF, serie: list, x: float, y: float,
                             w: float, h: float):
    """
    Desenha um gráfico de LINHAS (vetorial) com a variação do nº de presenças
    ao longo dos dias do período. serie: [{'data': 'DD/MM', 'valor': int}, ...]
    """
    import math
    if not serie:
        return
    valores = [max(0, int(p.get("valor", 0) or 0)) for p in serie]
    rotulos = [limpar_texto(p.get("data", "")) for p in serie]
    n = len(valores)
    vmax = max(valores) if valores else 0
    passo = max(1, int(math.ceil((vmax if vmax > 0 else 1) / 4.0)))
    topo = passo * 4

    pad_l, pad_r, pad_t, pad_b = 13.0, 3.0, 4.0, 9.0
    px, py = x + pad_l, y + pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b

    # moldura
    pdf.set_draw_color(220, 226, 232)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, w, h)

    # gridlines horizontais + rótulos do eixo Y
    pdf.set_font("Arial", "", 6)
    pdf.set_text_color(130, 140, 150)
    for k in range(5):
        val = topo * k / 4.0
        gy = py + ph - (val / topo) * ph
        pdf.set_draw_color(238, 240, 243)
        pdf.line(px, gy, px + pw, gy)
        pdf.set_xy(x, gy - 1.6)
        pdf.cell(pad_l - 2.0, 3.2, str(int(round(val))), align="R")

    # coordenadas dos pontos
    if n == 1:
        xs = [px + pw / 2.0]
    else:
        xs = [px + pw * i / (n - 1) for i in range(n)]
    ys = [py + ph - (v / topo) * ph for v in valores]

    # área sob a linha (preenchimento suave translúcido)
    if n >= 2:
        try:
            pts = [(xs[0], py + ph)] + list(zip(xs, ys)) + [(xs[-1], py + ph)]
            pdf.set_fill_color(191, 219, 254)
            with pdf.local_context(fill_opacity=0.35):
                pdf.polygon(pts, style="F")
        except Exception:
            pass

    # linha principal
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.6)
    for i in range(n - 1):
        pdf.line(xs[i], ys[i], xs[i + 1], ys[i + 1])

    # marcadores + rótulo de valor (só quando há poucos pontos)
    pdf.set_fill_color(37, 99, 235)
    mostra_valor = n <= 18
    for i in range(n):
        r = 0.85
        pdf.ellipse(xs[i] - r, ys[i] - r, 2 * r, 2 * r, style="F")
        if mostra_valor:
            pdf.set_font("Arial", "B", 5.5)
            pdf.set_text_color(30, 58, 95)
            pdf.set_xy(xs[i] - 6, ys[i] - 4.4)
            pdf.cell(12, 3, str(valores[i]), align="C")

    # rótulos do eixo X (subamostrados para não poluir)
    pdf.set_font("Arial", "", 5.5)
    pdf.set_text_color(130, 140, 150)
    step = max(1, int(math.ceil(n / 12.0)))
    for i in range(n):
        if i % step != 0 and i != n - 1:
            continue
        pdf.set_xy(xs[i] - 8, py + ph + 1.5)
        pdf.cell(16, 3, rotulos[i], align="C")

    pdf.set_line_width(0.2)
    pdf.set_text_color(0, 0, 0)


def _grid_totais(pdf: FPDF, titulo: str, itens: list, cor: tuple, cols: int = 6):
    """
    Renderiza um grid compacto de mini-totalizadores (várias colunas), usado
    para os totais semanais e mensais de presenças na capa.
    itens: [{'label': str, 'valor': int}, ...]
    """
    if not itens:
        return
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*cor)
    pdf.cell(0, 7, limpar_texto(titulo), ln=1)
    pdf.set_text_color(0, 0, 0)

    gap = 3.0
    full = pdf.w - pdf.l_margin - pdf.r_margin
    cell_w = (full - gap * (cols - 1)) / cols
    cell_h = 13.0
    x_start = pdf.l_margin
    row_y = pdf.get_y()

    for idx, it in enumerate(itens):
        col = idx % cols
        if col == 0:
            if pdf.get_y() + cell_h > (pdf.h - 22):
                pdf.add_page()
            row_y = pdf.get_y()
        x = x_start + col * (cell_w + gap)

        pdf.set_fill_color(246, 249, 252)
        pdf.set_draw_color(*cor)
        pdf.set_line_width(0.2)
        pdf.rect(x, row_y, cell_w, cell_h, style="DF")

        pdf.set_xy(x, row_y + 1.6)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*cor)
        pdf.cell(cell_w, 6, limpar_texto(str(it.get("valor", 0))), align="C")

        pdf.set_xy(x, row_y + 7.8)
        pdf.set_font("Arial", "", 6.5)
        pdf.set_text_color(90, 100, 110)
        pdf.cell(cell_w, 4, limpar_texto(str(it.get("label", ""))), align="C")

        if col == cols - 1 or idx == len(itens) - 1:
            pdf.set_y(row_y + cell_h + gap)

    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)
    pdf.ln(2)


def _pagina_capa_prestacao(pdf: FPDF, resumo: dict):
    """
    Renderiza a CAPA do relatório de Prestação de Contas: totalizadores
    (dias com aula, dias sem aula, total de presenças, média por dia), grids
    de totais semanais/mensais, um gráfico de linhas da variação de presenças
    e a tabela de dias sem aula do Calendário Institucional — para apresentar
    como folha de rosto da prestação de contas.
    """
    _cabecalho_padrao(pdf, subtitulo="PRESTACAO DE CONTAS - RELATORIO DE FREQUENCIA")

    periodo_ini     = resumo.get("periodo_ini", "")
    periodo_fim     = resumo.get("periodo_fim", "")
    total_dias      = resumo.get("total_dias", 0)
    total_presencas = resumo.get("total_presencas", 0)
    media_dia       = resumo.get("media_dia", "0")
    dias_sem_aula   = resumo.get("dias_sem_aula", []) or []

    # ── Título grande ─────────────────────────────────────────────────────
    pdf.ln(4)
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(10, 37, 64)
    pdf.cell(0, 10, limpar_texto("PRESTACAO DE CONTAS"), align="C", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, limpar_texto(f"Periodo: {periodo_ini}  a  {periodo_fim}"), align="C", ln=1)
    pdf.ln(8)

    # ── Cards de totalizadores (4 colunas) ────────────────────────────────
    cards = [
        ("DIAS COM AULA",        str(total_dias),      (30, 58, 95)),
        ("DIAS SEM AULA",        str(len(dias_sem_aula)), (180, 83, 9)),
        ("TOTAL DE PRESENCAS",   str(total_presencas), (22, 101, 52)),
        ("MEDIA POR DIA",        str(media_dia),       (109, 40, 173)),
    ]
    card_w  = 45
    gap     = 4
    total_w = card_w * 4 + gap * 3
    x0      = (210 - total_w) / 2.0
    y0      = pdf.get_y()
    card_h  = 26
    for i, (label, valor, cor) in enumerate(cards):
        x = x0 + i * (card_w + gap)
        pdf.set_fill_color(*cor)
        pdf.rect(x, y0, card_w, card_h, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(x, y0 + 4)
        pdf.set_font("Arial", "B", 20)
        pdf.cell(card_w, 12, limpar_texto(valor), align="C")
        pdf.set_xy(x, y0 + 16)
        pdf.set_font("Arial", "B", 7)
        pdf.multi_cell(card_w, 4, limpar_texto(label), align="C")
    pdf.set_y(y0 + card_h + 10)
    pdf.set_text_color(0, 0, 0)

    serie_diaria  = resumo.get("serie_diaria", []) or []
    totais_semana = resumo.get("totais_semana", []) or []
    totais_mes    = resumo.get("totais_mes", []) or []

    # ── Gráfico de linhas: variação de presenças no período ────────────────
    if serie_diaria:
        graf_h = 50.0
        if pdf.get_y() + graf_h + 14 > (pdf.h - 22):
            pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(30, 58, 95)
        pdf.cell(0, 8, limpar_texto("Variacao de presencas no periodo"), ln=1)
        pdf.set_text_color(0, 0, 0)
        gx = pdf.l_margin
        gy = pdf.get_y()
        gw = pdf.w - pdf.l_margin - pdf.r_margin
        _grafico_linha_presencas(pdf, serie_diaria, gx, gy, gw, graf_h)
        pdf.set_y(gy + graf_h + 8)

    # ── Grids de totais semanais e mensais ────────────────────────────────
    if totais_semana:
        _grid_totais(pdf, f"Totais por semana ({len(totais_semana)})",
                     totais_semana, (30, 58, 95), cols=6)
    if totais_mes:
        _grid_totais(pdf, f"Totais por mes ({len(totais_mes)})",
                     totais_mes, (22, 101, 52), cols=6)

    # ── Tabela: dias SEM AULA (Calendário Institucional) ──────────────────
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(0, 8, limpar_texto(
        f"Dias SEM AULA registrados no Calendario Institucional ({len(dias_sem_aula)})"
    ), ln=1)
    pdf.ln(1)

    if dias_sem_aula:
        W_NUM, W_DATA, W_MOT = 14, 70, 106
        LINE_H = 5.5

        def _header_tabela():
            pdf.set_fill_color(22, 163, 74)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(W_NUM, 7, "#", border=1, fill=True, align="C")
            pdf.cell(W_DATA, 7, limpar_texto("DATA"), border=1, fill=True, align="C")
            pdf.cell(W_MOT, 7, limpar_texto("MOTIVO"), border=1, fill=True, align="L")
            pdf.ln()
            pdf.set_text_color(0, 0, 0)

        _header_tabela()
        for i, item in enumerate(dias_sem_aula, 1):
            data_txt = limpar_texto(item.get("data", ""))
            mot_txt  = limpar_texto(item.get("motivo", "") or "-")

            # altura da linha = nº de linhas que o MOTIVO ocupa
            pdf.set_font("Arial", "", 9)
            n_linhas = max(1, len(pdf.multi_cell(W_MOT, LINE_H, mot_txt, split_only=True)))
            row_h = n_linhas * LINE_H

            # quebra de página manual, reimprimindo o cabeçalho da tabela
            if pdf.get_y() + row_h > (pdf.h - 22):
                pdf.add_page()
                _header_tabela()

            if i % 2 == 0:
                pdf.set_fill_color(240, 253, 244)
            else:
                pdf.set_fill_color(255, 255, 255)

            x_ini, y_ini = pdf.get_x(), pdf.get_y()
            pdf.set_font("Arial", "B", 8)
            pdf.cell(W_NUM, row_h, str(i), border=1, fill=True, align="C")
            pdf.set_font("Arial", "", 9)
            pdf.cell(W_DATA, row_h, data_txt, border=1, fill=True, align="C")
            # MOTIVO com quebra automática de texto, alinhado à mesma linha
            pdf.set_xy(x_ini + W_NUM + W_DATA, y_ini)
            pdf.multi_cell(W_MOT, LINE_H, mot_txt, border=1, fill=True, align="L")
            pdf.set_xy(x_ini, y_ini + row_h)
    else:
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 7, limpar_texto("Nenhum dia sem aula registrado no periodo."), ln=1)

    # ── Rodapé de emissão ─────────────────────────────────────────────────
    hoje_fmt = datetime.date.today().strftime("%d/%m/%Y")
    pdf.ln(6)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, limpar_texto(
        f"Emitido em: {hoje_fmt}  |  Sistema IMBRA - Gestao Inteligente MoveRight"
    ), ln=1)
    pdf.set_text_color(0, 0, 0)


def criar_prestacao_periodo_pdf(dias: dict, resumo: dict = None) -> bytes:
    """
    Gera PDF multi-página da Prestação de Contas por Período.
    dias: dict ordenado { 'YYYY-MM-DD': ['Nome1', 'Nome2', ...] }
    resumo (opcional): dados da CAPA (totalizadores + dias sem aula). Quando
      informado, uma folha de rosto é adicionada como primeira página.
    Cada dia ocupa uma nova página com cabeçalho completo.
    Sábados, domingos e feriados já devem ter sido removidos antes de chamar.
    """
    import datetime as _dt
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)

    if resumo:
        pdf.add_page()
        _pagina_capa_prestacao(pdf, resumo)

    for data_iso, nomes in dias.items():
        pdf.add_page()
        try:
            data_fmt = _dt.date.fromisoformat(data_iso).strftime("%d/%m/%Y")
        except Exception:
            data_fmt = data_iso
        _pagina_prestacao_diaria(pdf, data_fmt, nomes)

    try:
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return bytes(pdf.output())


def criar_pdf_alerta_frequencia(
    datas_faltantes: list,
    periodo_ini_fmt: str,
    periodo_fim_fmt: str,
) -> bytes:
    """
    Gera PDF de alerta listando dias úteis sem frequência lançada no período.
    datas_faltantes: lista de strings no formato 'DD/MM/YYYY (DiaDaSemana)'
    """
    import datetime as _dt

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    _cabecalho_padrao(pdf, subtitulo="ALERTA — FREQUENCIAS NAO LANCADAS")

    # Faixa de título
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(180, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, limpar_texto(
        f"  Periodo: {periodo_ini_fmt} a {periodo_fim_fmt}"
        f"  |  {len(datas_faltantes)} dia(s) sem frequencia"
    ), fill=True, ln=1)
    pdf.ln(3)

    # Aviso descritivo
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(120, 0, 0)
    pdf.multi_cell(0, 5, limpar_texto(
        "Os dias listados abaixo sao dias uteis (segunda a sexta, excluindo feriados nacionais) "
        "nos quais nenhuma frequencia foi registrada no sistema. "
        "Verificar se houve aula e corrigir se necessario."
    ))
    pdf.ln(4)

    # Cabeçalho da tabela
    pdf.set_fill_color(180, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(14, 7, "#", border=1, fill=True, align="C")
    pdf.cell(90, 7, limpar_texto("DATA"), border=1, fill=True, align="C")
    pdf.cell(86, 7, limpar_texto("SITUACAO"), border=1, fill=True, align="L")
    pdf.ln()

    # Linhas
    pdf.set_text_color(0, 0, 0)
    for i, item in enumerate(datas_faltantes, 1):
        if i % 2 == 0:
            pdf.set_fill_color(255, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(14, 6.5, str(i), border=1, fill=True, align="C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(90, 6.5, limpar_texto(item), border=1, fill=True, align="C")
        pdf.cell(86, 6.5, limpar_texto("Sem frequencia lancada"), border=1, fill=True, align="L")
        pdf.ln()

    # Rodapé informativo
    hoje_fmt = _dt.date.today().strftime("%d/%m/%Y")
    pdf.ln(4)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, limpar_texto(f"Emitido em: {hoje_fmt}  |  Sistema IMBRA — Gestao Inteligente MoveRight"), ln=1)

    try:
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return bytes(pdf.output())


# ==============================================================================
# 8. RELATÓRIO: MONITORAMENTO CLÍNICO (B.I. DA SAÚDE)  — versão PRIME
# ==============================================================================
def gerar_pdf_monitoramento_clinico(df, turma_filtro="Todas as Turmas"):
    """
    PDF prime do Monitoramento Clínico — A4 Paisagem (FPDF).
    Usa multi_cell com altura variável por linha para não truncar nenhum texto.
    Cores de alerta idênticas ao preview da tela.
    """

    # ── widths (paisagem A4 útil ≈ 277 mm com margens 10+10) ──────────────
    COLUNAS = [
        ("!",                   5),
        ("Nome",               44),
        ("Turma",              20),
        ("Patologias / Saude", 52),
        ("Restricoes",         27),
        ("Alergias",           20),
        ("Incomodos",          21),
        ("Medicamentos",       29),
        ("Ct. Emergencia",     41),
        ("Borg",               18),
    ]
    # Total: 5+44+20+52+27+20+21+29+41+18 = 277 mm (A4 landscape útil)
    CHAVES = ["🔴","Nome","Turma","Patologias","Restrições","Alergias","Incômodos","Medicamentos","Ct. Emergência","Borg/Risco"]
    TOTAL_W = sum(w for _, w in COLUNAS)   # 277 mm

    def _linhas(pdf, texto, largura, fonte_sz=7):
        """Quantas linhas o texto ocupa em determinada largura."""
        pdf.set_font("Arial", "", fonte_sz)
        return max(1, len(pdf.multi_cell(largura, 4.5, texto, split_only=True)))

    def _altura_linha(pdf, valores, fonte_sz=7):
        """Retorna a altura necessária para a linha mais alta da row."""
        max_linhas = 1
        for i, ((_, w), txt) in enumerate(zip(COLUNAS, valores)):
            n = _linhas(pdf, txt, w - 1, fonte_sz)
            if n > max_linhas:
                max_linhas = n
        return max_linhas * 4.5

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    # ── Cabeçalho padrão ──────────────────────────────────────────────────
    _cabecalho_padrao(pdf, subtitulo="Monitoramento Clinico — B.I. da Saude")

    # ── Metadados ─────────────────────────────────────────────────────────
    hoje_str = datetime.date.today().strftime("%d/%m/%Y")
    hora_str = datetime.datetime.now().strftime("%H:%M")
    total_alertas  = int((df.get("🔴", pd.Series()) == "🔴").sum())
    total_borg_alt = int((df.get("Borg/Risco", pd.Series()).fillna(0).astype(int) >= 7).sum())

    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(153, 27, 27)
    pdf.cell(0, 5, limpar_texto(
        f"CONFIDENCIAL — Restrito a equipe tecnica  |  Emitido: {hoje_str} as {hora_str}"
        f"  |  Turma: {turma_filtro}  |  Alunos: {len(df)}"
        f"  |  Alertas clinicos: {total_alertas}  |  Borg >= 7: {total_borg_alt}"
    ), ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)

    # ── Legenda de cores (linha compacta) ─────────────────────────────────
    pdf.set_font("Arial", "", 7)
    pdf.set_fill_color(254, 226, 226); pdf.cell(4, 3.5, "", border=1, fill=True)
    pdf.cell(1, 3.5, ""); pdf.cell(46, 3.5, limpar_texto("Alerta clinico (palavras-chave criticas)"))
    pdf.set_fill_color(254, 243, 199); pdf.cell(4, 3.5, "", border=1, fill=True)
    pdf.cell(1, 3.5, ""); pdf.cell(46, 3.5, limpar_texto("Borg >= 7 (esforco percebido alto)"))
    pdf.set_fill_color(230, 255, 237); pdf.cell(4, 3.5, "", border=1, fill=True)
    pdf.cell(1, 3.5, ""); pdf.cell(0,  3.5, limpar_texto("Sem alerta"), ln=1)
    pdf.ln(1.5)

    # ── Cabeçalho da tabela ───────────────────────────────────────────────
    pdf.set_font("Arial", "B", 7.5)
    pdf.set_fill_color(10, 37, 64)
    pdf.set_text_color(255, 255, 255)
    for label, w in COLUNAS:
        pdf.cell(w, 6, limpar_texto(label), border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # ── Linhas de dados com multi_cell ────────────────────────────────────
    zebra = False
    for _, row in df.iterrows():
        tem_alerta = str(row.get("🔴", "")) == "🔴"
        borg_val   = int(row.get("Borg/Risco", 0) or 0)
        borg_alto  = borg_val >= 7

        # Prepara textos
        valores = []
        for ch in CHAVES:
            v = str(row.get(ch, "") or "").strip()
            if ch == "🔴":
                v = "!!!" if tem_alerta else ""
            elif ch == "Borg/Risco":
                v = str(borg_val) if borg_val > 0 else "-"
            valores.append(limpar_texto(v))

        # Altura da linha
        h_linha = _altura_linha(pdf, valores, fonte_sz=7)
        h_linha = max(h_linha, 4.5)

        # Quebra de página antecipada
        if pdf.get_y() + h_linha > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font("Arial", "B", 7.5)
            pdf.set_fill_color(10, 37, 64)
            pdf.set_text_color(255, 255, 255)
            for label, w in COLUNAS:
                pdf.cell(w, 6, limpar_texto(label), border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_text_color(0, 0, 0)
            zebra = False

        # Cor de fundo
        if tem_alerta:
            pdf.set_fill_color(254, 226, 226)
        elif borg_alto:
            pdf.set_fill_color(254, 243, 199)
        elif zebra:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        zebra = not zebra
        fill = True

        x_ini = pdf.get_x()
        y_ini = pdf.get_y()

        # Desenha células com multi_cell simulado via get_x/set_xy
        for i, ((_, w), texto) in enumerate(zip(COLUNAS, valores)):
            align = "C" if i in (0, 9) else "L"  # 0=!, 9=Borg
            pdf.set_xy(x_ini, y_ini)
            pdf.rect(x_ini, y_ini, w, h_linha, style="D" if not fill else "FD")
            if align == "C" or len(texto) <= max(1, int(w / 2.2)):
                # texto curto: centraliza verticalmente
                pdf.set_xy(x_ini + 1, y_ini + (h_linha - 4) / 2)
                pdf.set_font("Arial", "", 7)
                pdf.cell(w - 2, 4, texto[:max(1, int(w / 1.9))], align=align)
            else:
                # texto longo: multi_cell alinhado ao topo
                pdf.set_xy(x_ini + 1, y_ini + 0.5)
                pdf.set_font("Arial", "", 6.5)
                pdf.multi_cell(w - 2, 4, texto, align="L")
            x_ini += w

        pdf.set_xy(pdf.l_margin, y_ini + h_linha)

    # ── Rodapé de totalizadores ───────────────────────────────────────────
    pdf.ln(2)
    pdf.set_draw_color(0, 86, 179)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + TOTAL_W, pdf.get_y())
    pdf.set_line_width(0.2); pdf.set_draw_color(0,0,0)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(153, 27, 27)
    pdf.cell(0, 5, limpar_texto(
        f"Resumo: {len(df)} alunos monitorados  |  "
        f"{total_alertas} com alerta clinico  |  "
        f"{total_borg_alt} com Borg >= 7"
    ), ln=1)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Arial", "I", 6.5)
    pdf.cell(0, 4, limpar_texto(
        "Documento confidencial — uso restrito a equipe tecnica. "
        "Proibida reproducao ou divulgacao sem autorizacao da coordenacao."
    ), ln=1)

    # ── Saída ─────────────────────────────────────────────────────────────
    try:
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return bytes(pdf.output())


# ==============================================================================
# 🧬 PDF: PATOLOGIAS — ANAMNESE CLÍNICA (A4 Paisagem)
# Inclui Peso / Altura / IMC e última PA de cada aluno.
# ==============================================================================

def gerar_pdf_patologias(df, turma_filtro="Todas as Turmas"):
    """
    PDF Patologias — Anamnese Clínica (A4 Paisagem, 277 mm úteis).
    Colunas: Foto · ! · Nome · Turma · Borg · Patologias · Restrições ·
             Alergias · Medicamentos · Peso/Alt/IMC · PA/Cls · Ct.Emergência
    """

    # (col_label, width_mm, col_key_or_None)
    # width total: 9+5+37+8+9+46+21+17+22+18+16+69 = 277 mm
    COLUNAS = [
        ("Foto",           9,  "Foto"),
        ("!",              5,  "🔴"),
        ("Nome",          35,  "Nome"),
        ("Turma",          8,  "Turma"),
        ("Borg",           9,  "Borg/Risco"),
        ("Peso/Alt/IMC",  18,  None),
        ("PA / Cls",      16,  None),
        ("Patologias",    48,  "Patologias"),
        ("Restricoes",    21,  "Restrições"),
        ("Alergias",      17,  "Alergias"),
        ("Medicamentos",  22,  "Medicamentos"),
        ("Ct. Emergencia",69,  "Ct. Emergência"),
    ]
    # Total: 9+5+35+8+9+18+16+48+21+17+22+69 = 277 mm

    TOTAL_W = sum(w for _, w, _ in COLUNAS)
    # Índice da coluna Foto (posição 0) para tratamento especial
    FOTO_IDX = 0
    FOTO_W   = COLUNAS[FOTO_IDX][1]   # 9 mm
    MIN_H    = 9.5                     # altura mínima de linha (acomoda foto 8x8)

    def _linhas(pdf, texto, largura, fonte_sz=7):
        pdf.set_font("Arial", "", fonte_sz)
        return max(1, len(pdf.multi_cell(largura, 4.5, texto, split_only=True)))

    def _altura_linha(pdf, textos_sem_foto, fonte_sz=7):
        """textos_sem_foto já exclui a coluna Foto."""
        max_n = 1
        for (_, w, _), txt in zip(COLUNAS[1:], textos_sem_foto):
            n = _linhas(pdf, txt, w - 1, fonte_sz)
            if n > max_n:
                max_n = n
        return max(max_n * 4.5, MIN_H)

    def _cabecalho_tabela(pdf):
        pdf.set_font("Arial", "B", 7.5)
        pdf.set_fill_color(127, 29, 29)
        pdf.set_text_color(255, 255, 255)
        for label, w, _ in COLUNAS:
            pdf.cell(w, 6, limpar_texto(label), border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

    # ── Pré-baixa fotos únicas ──────────────────────────────────────────────
    # Base URL do Supabase para montar URLs relativas (ex: "avatars/foto.jpg")
    try:
        from database import supabase as _supa_pdf
        _supa_base = getattr(_supa_pdf, "supabase_url", "") or ""
    except Exception:
        _supa_base = ""
    _BUCKET_PREFIX = "/storage/v1/object/public/"

    def _normalizar_foto_url(raw: str) -> str:
        """Garante URL completa; se for caminho relativo, monta com base do Supabase."""
        raw = str(raw or "").strip()
        if not raw:
            return ""
        if raw.startswith("http"):
            return raw
        # caminho relativo: ex "fotos-alunos/photo.jpg" ou "photo.jpg"
        if _supa_base:
            return f"{_supa_base.rstrip('/')}{_BUCKET_PREFIX}{raw.lstrip('/')}"
        return ""

    foto_cache = {}   # url_completa -> temp_path | None
    if "Foto" in df.columns:
        urls_unicas = [
            _normalizar_foto_url(str(u))
            for u in df["Foto"].dropna().unique()
        ]
        urls_unicas = [u for u in urls_unicas if u]

        def _dl_foto(u_full: str):
            return u_full, baixar_imagem_supabase(u_full) or baixar_imagem_temp(u_full)

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as _pool:
            for u_full, path in _pool.map(_dl_foto, urls_unicas):
                foto_cache[u_full] = path

    # ── Cabeçalho específico para paisagem A4 (297 mm) ────────────────────
    def _cab_paisagem(pdf):
        try:
            from utils.identidade import get_config as _gci
            cfg = _gci()
        except Exception:
            cfg = {}
        titulo   = limpar_texto(cfg.get("titulo_projeto", "ESPORTE E SAUDE NA COMUNIDADE - FASE 2"))
        logo_esq = cfg.get("logo_secundaria", "logo-secretaria.png")
        logo_dir = cfg.get("logo_principal",  "logo-imbra.png")
        logo_w   = 28
        # Logos: margem esq=10, margem dir=10 → página 297 mm
        for path in [logo_esq, logo_esq.replace(".png",".jpg")]:
            if path and os.path.exists(path):
                try: pdf.image(path, x=10, y=5, w=logo_w)
                except Exception: pass
                break
        for path in [logo_dir, logo_dir.replace(".png",".jpg")]:
            if path and os.path.exists(path):
                try: pdf.image(path, x=259, y=5, w=logo_w)
                except Exception: pass
                break
        # Título centralizado entre os logos (x=42 a x=257, largura=215)
        pdf.set_xy(42, 9)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(10, 37, 64)
        pdf.multi_cell(215, 6, titulo, align="C")
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.set_x(42)
        pdf.multi_cell(215, 5, "Patologias - Anamnese Clinica", align="C")
        # Linha separadora
        y_sep = max(pdf.get_y() + 2, 36)
        pdf.set_draw_color(0, 86, 179)
        pdf.set_line_width(0.6)
        pdf.line(10, y_sep, 287, y_sep)
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.2)
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(y_sep + 4)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    _cab_paisagem(pdf)

    hoje_str  = datetime.date.today().strftime("%d/%m/%Y")
    hora_str  = datetime.datetime.now().strftime("%H:%M")
    n_alertas = int((df.get("🔴", pd.Series()) == "🔴").sum())
    n_borg7   = int((df.get("Borg/Risco", pd.Series()).fillna(0).astype(int) >= 7).sum())

    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(153, 27, 27)
    pdf.cell(0, 5, limpar_texto(
        f"CONFIDENCIAL | Emitido: {hoje_str} as {hora_str}"
        f" | Turma: {turma_filtro} | Alunos: {len(df)}"
        f" | Alertas: {n_alertas} | Borg>=7: {n_borg7}"
    ), ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)

    # Legenda de cores + IMC (mesma linha)
    pdf.set_font("Arial", "", 7)
    pdf.set_fill_color(254, 226, 226); pdf.cell(4, 3.5, "", border=1, fill=True)
    pdf.cell(1, 3.5, ""); pdf.cell(30, 3.5, limpar_texto("Alerta clinico"))
    pdf.set_fill_color(254, 243, 199); pdf.cell(4, 3.5, "", border=1, fill=True)
    pdf.cell(1, 3.5, ""); pdf.cell(25, 3.5, limpar_texto("Borg >= 7"))
    pdf.set_fill_color(230, 255, 237); pdf.cell(4, 3.5, "", border=1, fill=True)
    pdf.cell(1, 3.5, ""); pdf.cell(22, 3.5, limpar_texto("Sem alerta"))
    # Legenda IMC inline
    pdf.set_text_color(30, 64, 175)
    pdf.set_font("Arial", "B", 6.5)
    pdf.cell(10, 3.5, "IMC:")
    pdf.set_font("Arial", "", 6.5)
    pdf.cell(0, 3.5,
        limpar_texto("BP=Baixo Peso  N=Normal  SP=Sobrepeso  O1=Ob.I  O2=Ob.II  O3=Ob.III"),
        ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1.5)

    _cabecalho_tabela(pdf)

    # ── Linhas de dados ────────────────────────────────────────────────────
    zebra = False
    for _, row in df.iterrows():
        tem_alerta = str(row.get("🔴", "")) == "🔴"
        borg_val   = int(row.get("Borg/Risco", 0) or 0)
        borg_alto  = borg_val >= 7
        foto_url  = _normalizar_foto_url(str(row.get("Foto", "") or ""))
        foto_path = foto_cache.get(foto_url) if foto_url else None

        # Peso / Altura / IMC  (3 linhas — IMC com código curto ex: "25.0 SP")
        import re as _re
        peso_s   = str(row.get("Peso (kg)", "") or "").strip().replace("—", "-")
        altura_s = str(row.get("Altura (m)", "") or "").strip().replace("—", "-")
        imc_s    = str(row.get("IMC", "") or "").strip()   # ex: "25.0 — Sobrepeso"
        _linhas_pai = []
        if peso_s not in ("", "-"):
            _linhas_pai.append(f"{peso_s} kg")
        if altura_s not in ("", "-"):
            _linhas_pai.append(f"{altura_s} m")
        if imc_s and imc_s not in ("-", "—"):
            # extrai número e categoria; usa código curto para caber em 18mm
            _imc_parts = _re.split(r'\s*[—–\-]+\s*', imc_s, maxsplit=1)
            _imc_num   = _imc_parts[0].strip() if _imc_parts else ""
            _imc_cat   = _imc_parts[1].strip() if len(_imc_parts) > 1 else ""
            _imc_code  = _IMC_CODES.get(_imc_cat, _imc_cat[:4] if _imc_cat else "")
            if _imc_num:
                _linhas_pai.append(f"{_imc_num} {_imc_code}".strip())
        pai_txt = "\n".join(_linhas_pai) if _linhas_pai else "-"

        # PA / Classe  (2 linhas: "131/87 / Est.1")
        pa_s  = str(row.get("PA Sis/Dia", "") or "").strip().replace("—", "-")
        cls_s = str(row.get("PA Classe",  "") or "").strip().replace("—", "-")
        if pa_s and pa_s not in ("-", ""):
            pa_txt = pa_s + (f"\n{cls_s}" if cls_s and cls_s not in ("-", "") else "")
        else:
            pa_txt = "-"

        # Textos para as colunas NÃO-foto (mesma ordem que COLUNAS[1:])
        textos = [
            "!!!" if tem_alerta else "",                              # !
            limpar_texto(str(row.get("Nome", "") or "")),             # Nome
            limpar_texto(str(row.get("Turma", "") or "")),            # Turma
            str(borg_val) if borg_val > 0 else "-",                  # Borg
            limpar_texto(pai_txt),                                    # Peso/Alt/IMC
            limpar_texto(pa_txt),                                     # PA/Cls
            limpar_texto(str(row.get("Patologias", "") or "")),       # Patologias
            limpar_texto(str(row.get("Restrições", "") or "")),       # Restrições
            limpar_texto(str(row.get("Alergias", "") or "")),         # Alergias
            limpar_texto(str(row.get("Medicamentos", "") or "")),     # Medicamentos
            limpar_texto(str(row.get("Ct. Emergência", "") or "")),   # Ct. Emergência
        ]

        h_linha = _altura_linha(pdf, textos)

        # Quebra de página
        if pdf.get_y() + h_linha > pdf.page_break_trigger:
            pdf.add_page()
            _cabecalho_tabela(pdf)
            zebra = False

        # Cor de fundo da linha
        if tem_alerta:
            fill_r, fill_g, fill_b = 254, 226, 226
        elif borg_alto:
            fill_r, fill_g, fill_b = 254, 243, 199
        elif zebra:
            fill_r, fill_g, fill_b = 245, 247, 250
        else:
            fill_r, fill_g, fill_b = 255, 255, 255
        zebra = not zebra
        pdf.set_fill_color(fill_r, fill_g, fill_b)

        x_ini = pdf.l_margin
        y_ini = pdf.get_y()

        # ── Coluna Foto (índice 0) — tratamento especial ──────────────────
        pdf.set_xy(x_ini, y_ini)
        pdf.rect(x_ini, y_ini, FOTO_W, h_linha, style="FD")
        if foto_path:
            try:
                img_sz = min(FOTO_W - 1.5, h_linha - 1.5)
                ix = x_ini + (FOTO_W - img_sz) / 2
                iy = y_ini + (h_linha - img_sz) / 2
                pdf.image(foto_path, x=ix, y=iy, w=img_sz, h=img_sz)
            except Exception:
                pass
        x_ini += FOTO_W

        # ── Demais colunas ────────────────────────────────────────────────
        for ci, ((_, w, _), texto) in enumerate(zip(COLUNAS[1:], textos)):
            # ci=0→!, ci=1→Nome, ci=2→Turma, ci=3→Borg, ci=4→Peso/Alt/IMC, ci=5→PA/Cls
            centrar   = ci in (0, 3, 4, 5)   # !, Borg, Peso/Alt/IMC e PA/Cls centralizados
            multiline = "\n" in texto
            pdf.set_xy(x_ini, y_ini)
            pdf.set_fill_color(fill_r, fill_g, fill_b)
            pdf.rect(x_ini, y_ini, w, h_linha, style="FD")
            if multiline:
                # multi_cell para conteúdo em linhas (Peso/Alt/IMC, PA/Cls)
                n_linhas  = texto.count("\n") + 1
                h_lin     = max(3.5, h_linha / n_linhas)
                pdf.set_font("Arial", "", 6.5)
                pdf.set_xy(x_ini + 1, y_ini + (h_linha - h_lin * n_linhas) / 2)
                pdf.multi_cell(w - 2, h_lin, texto,
                               align="C" if centrar else "L")
            elif centrar or len(texto) <= max(1, int(w / 2.2)):
                pdf.set_xy(x_ini + 1, y_ini + (h_linha - 4) / 2)
                pdf.set_font("Arial", "", 7)
                pdf.cell(w - 2, 4, texto[:max(1, int(w / 1.9))],
                         align="C" if centrar else "L")
            else:
                pdf.set_xy(x_ini + 1, y_ini + 0.5)
                pdf.set_font("Arial", "", 6.5)
                pdf.multi_cell(w - 2, 4, texto, align="L")
            x_ini += w

        pdf.set_xy(pdf.l_margin, y_ini + h_linha)

    # ── Rodapé do relatório ────────────────────────────────────────────────
    pdf.ln(2)
    pdf.set_draw_color(153, 27, 27)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + TOTAL_W, pdf.get_y())
    pdf.set_line_width(0.2); pdf.set_draw_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(153, 27, 27)
    pdf.cell(0, 5, limpar_texto(
        f"Resumo: {len(df)} alunos | {n_alertas} alertas clinicos | {n_borg7} com Borg >= 7"
    ), ln=1)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Arial", "I", 6.5)
    pdf.cell(0, 4, limpar_texto(
        "Documento confidencial - uso restrito a equipe tecnica. "
        "Proibida reproducao ou divulgacao sem autorizacao da coordenacao."
    ), ln=1)

    # Limpa arquivos temporários de fotos
    for tmp in foto_cache.values():
        if tmp:
            try:
                os.remove(tmp)
            except Exception:
                pass

    try:
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return bytes(pdf.output())