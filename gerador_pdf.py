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
# 2. RELATÓRIO: DOSSIÊ DO ALUNO (INDIVIDUAL)
# ==============================================================================
def criar_documento_aluno_pdf(aluno_data, avaliacoes, historico, estatisticas):
    pdf = PDF()
    pdf.add_page()

    # --- CABEÇALHO ---
    _cabecalho_padrao(pdf)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, limpar_texto("DOSSIE CLINICO E DESPORTIVO DO ALUNO"), align="C", ln=1)
    pdf.ln(4)

    # --- 1. PERFIL PESSOAL ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, limpar_texto(" 1. Perfil Pessoal e Biométrico"), ln=1, fill=True)
    pdf.ln(4)

    y_atual = pdf.get_y()

    url_foto = aluno_data.get("url_foto")
    if pd.notna(url_foto):
        tmp = baixar_imagem_temp(url_foto)
        if tmp:
            pdf.image(tmp, x=160, y=y_atual, w=35, h=35)
            pdf.rect(160, y_atual, 35, 35)

    pdf.set_xy(10, y_atual)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(15, 6, "Nome: ")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, limpar_texto(aluno_data.get("nome", "")), ln=1)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(16, 6, "Turma: ")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, limpar_texto(aluno_data.get("turma", "")), ln=1)

    nasc = aluno_data.get("data_nascimento")
    nasc_str = "Nao informado"
    if pd.notna(nasc) and str(nasc).strip():
        try:
            dt_nasc = pd.to_datetime(nasc).date()
            idade = datetime.date.today().year - dt_nasc.year
            nasc_str = f"{dt_nasc.strftime('%d/%m/%Y')} ({idade} anos)"
        except: pass

    pdf.set_font("Arial", "B", 11)
    pdf.cell(28, 6, "Nascimento: ")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, limpar_texto(nasc_str), ln=1)

    peso = aluno_data.get("peso", "N/A")
    altura = aluno_data.get("altura", "N/A")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(13, 6, "Peso: ")
    pdf.set_font("Arial", "", 11)
    pdf.cell(25, 6, f"{peso} kg")

    pdf.set_font("Arial", "B", 11)
    pdf.cell(15, 6, "Altura: ")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"{altura} m", ln=1)

    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(30, 136, 229)
    pdf.cell(42, 6, limpar_texto("Total de Presenças: "))
    pdf.set_font("Arial", "B", 12)
    presencas = estatisticas.get("presentes", 0) if estatisticas else 0
    pdf.cell(0, 6, limpar_texto(f"{presencas} aulas concluidas"), ln=1)
    pdf.set_text_color(0, 0, 0)

    if pdf.get_y() < y_atual + 40:
        pdf.set_y(y_atual + 45)
    else:
        pdf.ln(5)

    # --- 2. HISTÓRICO CLÍNICO E BIOFEEDBACK (NOVO) ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, limpar_texto(" 2. Histórico Clínico e Biofeedback"), ln=1, fill=True)
    pdf.ln(4)

    # 🚀 FIX PANDAS: Converte o DataFrame para lista de dicionários com segurança
    if isinstance(avaliacoes, pd.DataFrame):
        avaliacoes = avaliacoes.to_dict('records')

    if avaliacoes and len(avaliacoes) > 0:
        for av in avaliacoes:
            dt_av = av.get("data_avaliacao", "Data não informada")
            if isinstance(dt_av, datetime.date) or isinstance(dt_av, datetime.datetime):
                dt_av = dt_av.strftime("%d/%m/%Y")

            dor = av.get("nivel_dor", "N/A")
            tug = av.get("tug", "N/A")
            simetria = av.get("simetria_forca", "N/A")

            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, limpar_texto(f"Data da Avaliação: {dt_av}"), ln=1)

            pdf.set_font("Arial", "", 11)
            texto_bio = f"Nível de Dor: {dor}/10   |   Equilíbrio (TUG): {tug}s   |   Simetria: {simetria}"
            pdf.multi_cell(0, 6, limpar_texto(texto_bio), align="L")
            pdf.ln(3)
    else:
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, limpar_texto("Nenhuma avaliação clínica registada."), ln=1)
        pdf.ln(2)

    # --- 3. DIÁRIO DE BORDO (AULAS) ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, limpar_texto(" 3. Diário de Bordo (Aulas e Exercícios)"), ln=1, fill=True)
    pdf.ln(4)

    # 🚀 FIX PANDAS: Converte o DataFrame para lista de dicionários com segurança
    if isinstance(historico, pd.DataFrame):
        historico = historico.to_dict('records')

    if historico and len(historico) > 0:
        for h in historico:
            data_aula = h.get('data_aula', '')
            if isinstance(data_aula, datetime.date) or isinstance(data_aula, datetime.datetime):
                data_aula = data_aula.strftime("%d/%m/%Y")

            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(30, 136, 229) # Azulzinho para a data
            pdf.cell(0, 8, limpar_texto(f"Aula de {data_aula}:"), ln=1)
            pdf.set_text_color(0, 0, 0)

            pdf.set_font("Arial", "", 11)
            obj = h.get("objetivo_geral")
            exc = h.get("exercicios_executados")

            if obj:
                pdf.set_font("Arial", "B", 11)
                pdf.write(6, "Objetivo: ")
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 6, limpar_texto(obj), align="J")

            if exc:
                pdf.set_font("Arial", "B", 11)
                pdf.write(6, limpar_texto("Exercícios: "))
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 6, limpar_texto(exc), align="J")

            pdf.ln(4)
    else:
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, limpar_texto("Nenhuma participação com diário registada."), ln=1)

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