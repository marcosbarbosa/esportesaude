# ==============================================================================
# 📄 utils/email_relatorio.py
# ⚙️  Motor de geração do Email BI Gerencial — HTML + envio via Gmail SMTP
# ==============================================================================

import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


_COR_HEADER   = "#0A2540"
_COR_VERDE    = "#16A34A"
_COR_AMARELO  = "#D97706"
_COR_VERMELHO = "#DC2626"
_COR_AZUL     = "#1D4ED8"


def _section(titulo: str, cor: str, conteudo_html: str) -> str:
    return f"""
    <div style="margin-bottom:24px;">
      <div style="background:{cor};padding:10px 16px;border-radius:8px 8px 0 0;">
        <h3 style="color:white;margin:0;font-size:14px;">{titulo}</h3>
      </div>
      <div style="background:#F8FAFC;padding:16px;border:1px solid #E2E8F0;
                  border-top:none;border-radius:0 0 8px 8px;">
        {conteudo_html}
      </div>
    </div>"""


def _kpi(label: str, valor: str, cor: str = "#0A2540") -> str:
    return f"""
    <div style="display:inline-block;background:white;border:1px solid #E2E8F0;
                border-radius:8px;padding:12px 20px;margin:6px;text-align:center;
                min-width:100px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
      <div style="font-size:22px;font-weight:900;color:{cor};">{valor}</div>
      <div style="font-size:11px;color:#64748B;margin-top:2px;">{label}</div>
    </div>"""


def _tabela(cabecalhos: list, linhas: list, cores_alt: tuple = ("#FFFFFF", "#F8FAFC")) -> str:
    ths = "".join(
        f"<th style='padding:8px 12px;color:white;font-size:11px;text-align:left;"
        f"background:{_COR_HEADER};'>{h}</th>" for h in cabecalhos
    )
    trs = ""
    for i, linha in enumerate(linhas):
        bg = cores_alt[i % 2]
        tds = "".join(
            f"<td style='padding:7px 12px;font-size:12px;border-bottom:1px solid #E2E8F0;"
            f"color:#1E293B;'>{c}</td>" for c in linha
        )
        trs += f"<tr style='background:{bg};'>{tds}</tr>"
    return (
        f"<table style='width:100%;border-collapse:collapse;border-radius:8px;"
        f"overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);'>"
        f"<thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>"
    )


def _btn(url: str, label: str, cor: str = "#1D4ED8") -> str:
    """Botão de ação que abre uma tela do sistema. Se não houver URL, mostra '—'."""
    if not url:
        return '<span style="color:#94A3B8;font-size:11px;">—</span>'
    return (
        f'<a href="{url}" style="background:{cor};color:white;padding:5px 12px;'
        f'border-radius:6px;text-decoration:none;font-size:11px;font-weight:700;'
        f'display:inline-block;white-space:nowrap;">{label}</a>'
    )


def _link_freq(base_url: str, data_iso: str) -> str:
    return f"{base_url}/?ir=freq&d={data_iso}" if base_url else ""


def _link_ficha(base_url: str, aluno_id: str) -> str:
    return f"{base_url}/?ir=ficha&id={aluno_id}" if base_url else ""


def _link_triagem(base_url: str) -> str:
    return f"{base_url}/?ir=triagem" if base_url else ""


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULOS DE CONTEÚDO
# ──────────────────────────────────────────────────────────────────────────────

def _bloco_executivo() -> str:
    try:
        from database import bi_resumo_studio
        d = bi_resumo_studio() or {}
        ativos    = d.get("total_ativos", "—")
        inativos  = d.get("total_inativos", "—")
        taxa      = d.get("taxa_presenca_30", "—")
        risco_v   = d.get("risco_vermelho", 0)
        risco_a   = d.get("risco_amarelo", 0)
        sem_pres  = d.get("sem_presenca_15", "—")
        if isinstance(taxa, (int, float)):
            taxa = f"{taxa:.1f}%"
        try:
            cor_risco = _COR_VERMELHO if int(risco_v or 0) > 5 else _COR_AMARELO
        except Exception:
            cor_risco = _COR_AMARELO

        # Média de alunos presentes por dia de aula
        try:
            from database import bi_media_alunos_dia
            m = bi_media_alunos_dia() or {}
            mp = m.get("media_periodo", 0)
            mm = m.get("media_mes", 0)
            media_per = f"{mp:.1f}".replace(".", ",") if isinstance(mp, (int, float)) else str(mp)
            media_mes = f"{mm:.1f}".replace(".", ",") if isinstance(mm, (int, float)) else str(mm)
        except Exception:
            media_per = media_mes = "—"

        kpis = (
            _kpi("Alunos Ativos", str(ativos), _COR_AZUL) +
            _kpi("Inativos", str(inativos), "#64748B") +
            _kpi("Freq. 30 dias", str(taxa), _COR_VERDE) +
            _kpi("Média/dia (período)", media_per, "#0891B2") +
            _kpi("Média/dia (mês)", media_mes, "#0891B2") +
            _kpi("Risco 🔴", str(risco_v), cor_risco) +
            _kpi("Risco 🟡", str(risco_a), _COR_AMARELO) +
            _kpi("Sem aula 15d", str(sem_pres), "#64748B")
        )
        return _section("📊 Painel Executivo", _COR_AZUL,
                        f"<div style='text-align:center;'>{kpis}</div>")
    except Exception as e:
        return _section("📊 Painel Executivo", _COR_AZUL,
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_presencas_mes() -> str:
    try:
        from database import bi_presencas_por_mes
        d = bi_presencas_por_mes() or {}
        total   = d.get("total_ano", 0)
        por_mes = d.get("por_mes", [])
        ano     = d.get("ano", "")

        kpi = _kpi(f"Total no ano {ano}", f"{total:,}".replace(",", "."), _COR_VERDE)

        if por_mes:
            total_seguro = total if total > 0 else 1
            linhas = []
            for nome_mes, qtd in por_mes:
                pct = qtd / total_seguro * 100
                qtd_fmt = f"{qtd:,}".replace(",", ".")
                linhas.append([
                    nome_mes,
                    f"<span style='font-weight:700;color:#0A2540;'>{qtd_fmt}</span>",
                    f"<span style='color:#64748B;'>{pct:.1f}%</span>",
                ])
            tabela = _tabela(["Mês", "Total de presenças", "% do ano"], linhas)
        else:
            tabela = ("<p style='color:#94A3B8;font-size:12px;'>"
                      "Sem presenças registradas neste ano.</p>")

        conteudo = (f"<div style='text-align:center;margin-bottom:14px;'>{kpi}</div>"
                    + tabela)
        return _section(f"📈 Presenças no Ano ({ano})", _COR_VERDE, conteudo)
    except Exception as e:
        return _section("📈 Presenças no Ano", _COR_VERDE,
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_evasao(base_url: str = "") -> str:
    try:
        from database import bi_alunos_risco_abandono
        df = bi_alunos_risco_abandono(dias=30)
        if df is None or len(df) == 0:
            return _section("⚠️ Risco de Evasão", _COR_AMARELO,
                            "<p style='color:#16A34A;font-size:12px;'>✅ Nenhum aluno em risco de evasão nos últimos 30 dias.</p>")
        from utils.texto import formatar_whatsapp_numero
        if "dias_ausente" in df.columns:
            df = df.sort_values("dias_ausente", ascending=False)
        total = len(df)
        linhas = []
        for _, a in df.head(20).iterrows():
            nome     = str(a.get("nome", "—")).upper()
            turma    = str(a.get("turma", "—") or "—")
            dias_out = a.get("dias_ausente", "?")
            ultima   = str(a.get("ultima_presenca", "—") or "—")[:10]
            wap      = str(a.get("whatsapp", "") or "")
            num      = formatar_whatsapp_numero(wap) if wap else None
            contato  = (
                f'<a href="https://wa.me/{num}" style="color:#16A34A;font-size:11px;font-weight:700;">📲 WhatsApp</a>'
                if num else '<span style="color:#94A3B8;font-size:11px;">—</span>'
            )
            ficha = _btn(_link_ficha(base_url, str(a.get("id", ""))), "👤 Abrir ficha", _COR_AZUL)
            try:
                cor_dias = _COR_VERMELHO if int(dias_out or 0) >= 30 else _COR_AMARELO
            except Exception:
                cor_dias = _COR_AMARELO
            linhas.append([
                nome, turma,
                f"<span style='color:{cor_dias};font-weight:700;'>{dias_out} dias</span>",
                ultima, contato, ficha
            ])
        tabela = _tabela(["Aluno", "Turma", "Ausente há", "Última Presença", "Contato", "Resolver"], linhas)
        aviso  = (f"<p style='color:{_COR_VERMELHO};font-size:12px;font-weight:700;"
                  f"margin-bottom:10px;'>⚠️ {total} aluno(s) sem presença nos últimos 30 dias</p>")
        return _section("⚠️ Risco de Evasão", _COR_AMARELO, aviso + tabela)
    except Exception as e:
        return _section("⚠️ Risco de Evasão", _COR_AMARELO,
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_auditoria(base_url: str = "") -> str:
    try:
        from database import supabase
        res = supabase.from_("alunos").select(
            "id,nome,turma,url_foto,cpf,data_nascimento,status"
        ).eq("status", "Ativo").execute()
        alunos = res.data or []
        problemas = []
        for a in alunos:
            issues = []
            if not a.get("url_foto"):
                issues.append("sem foto")
            if not a.get("cpf"):
                issues.append("sem CPF")
            if not a.get("data_nascimento"):
                issues.append("sem data de nascimento")
            if issues:
                problemas.append([
                    str(a.get("nome", "—")).upper(),
                    str(a.get("turma", "—") or "—"),
                    ", ".join(issues),
                    _btn(_link_ficha(base_url, str(a.get("id", ""))), "📝 Completar ficha", _COR_AZUL),
                ])
        if not problemas:
            return _section("📋 Auditoria de Cadastros", _COR_VERDE,
                            "<p style='color:#16A34A;font-size:12px;'>✅ Todos os cadastros ativos estão completos.</p>")
        tabela = _tabela(["Aluno", "Turma", "Pendências", "Resolver"], problemas[:25])
        aviso  = (f"<p style='color:{_COR_VERMELHO};font-size:12px;font-weight:700;"
                  f"margin-bottom:10px;'>📋 {len(problemas)} cadastro(s) com dados incompletos</p>")
        return _section("📋 Auditoria de Cadastros", _COR_VERDE, aviso + tabela)
    except Exception as e:
        return _section("📋 Auditoria de Cadastros", _COR_VERDE,
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_novos_cadastros(base_url: str = "") -> str:
    try:
        from database import supabase
        res = (
            supabase.from_("pre_cadastros")
            .select("*")
            .in_("status", ["Pendente", "Lista de Espera"])
            .execute()
        )
        pendentes = res.data or []
    except Exception as e:
        return _section("📥 Novos Cadastros (Aprovação)", "#7C3AED",
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")
    try:
        if not pendentes:
            return _section("📥 Novos Cadastros (Aprovação)", _COR_VERDE,
                            "<p style='color:#16A34A;font-size:12px;'>✅ Nenhuma inscrição nova aguardando aprovação.</p>")
        linhas = []
        for p in pendentes:
            faltas = []
            if not p.get("url_foto"):
                faltas.append("foto")
            if not p.get("url_rg"):
                faltas.append("RG")
            if not p.get("url_atestado_medico"):
                faltas.append("atestado")
            if faltas:
                pend_str = (f"<span style='color:{_COR_VERMELHO};font-weight:700;'>"
                            f"{', '.join(faltas)}</span>")
            else:
                pend_str = "<span style='color:#16A34A;font-weight:700;'>documentos completos</span>"
            status_p = str(p.get("status", "Pendente") or "Pendente")
            linhas.append([
                str(p.get("nome", "—")).upper(),
                status_p,
                pend_str,
                _btn(_link_triagem(base_url), "✅ Triar / Aprovar", _COR_VERDE),
            ])
        aviso = (f"<p style='color:{_COR_VERMELHO};font-size:12px;font-weight:700;"
                 f"margin-bottom:10px;'>📥 {len(pendentes)} inscrição(ões) nova(s) aguardando triagem/aprovação</p>")
        tabela = _tabela(["Aluno", "Situação", "Documentos pendentes", "Resolver"], linhas)
        return _section("📥 Novos Cadastros (Aprovação)", "#7C3AED", aviso + tabela)
    except Exception as e:
        return _section("📥 Novos Cadastros (Aprovação)", "#7C3AED",
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_frequencia_turma() -> str:
    try:
        from database import bi_frequencia_turmas
        df = bi_frequencia_turmas(dias=30)
        if df is None or len(df) == 0:
            return _section("🏆 Frequência por Turma (30 dias)", _COR_AZUL,
                            "<p style='color:#94A3B8;font-size:12px;'>Sem dados de frequência.</p>")
        linhas = []
        for i, (_, t) in enumerate(df.iterrows(), 1):
            nome_t = str(t.get("turma", "—"))
            taxa   = t.get("taxa_presenca", 0)
            if isinstance(taxa, (int, float)):
                cor_taxa = _COR_VERDE if taxa >= 70 else (_COR_AMARELO if taxa >= 50 else _COR_VERMELHO)
                taxa_str = f"<span style='color:{cor_taxa};font-weight:700;'>{taxa:.1f}%</span>"
            else:
                taxa_str = str(taxa)
            linhas.append([f"#{i}", nome_t, taxa_str])
        tabela = _tabela(["#", "Turma", "Taxa de Presença"], linhas)
        return _section("🏆 Frequência por Turma (30 dias)", _COR_AZUL, tabela)
    except Exception as e:
        return _section("🏆 Frequência por Turma (30 dias)", _COR_AZUL,
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_dias_sem_registro(base_url: str = "") -> str:
    try:
        import datetime as _dt
        from database import get_presentes_periodo_todos, get_dias_sem_aula
        from views.relatorio_view import _feriados_nacionais_br

        hoje = _dt.date.today()
        seg  = hoje - _dt.timedelta(days=hoje.weekday())
        if hoje.weekday() == 0:
            seg = hoje - _dt.timedelta(days=7)
        sex = seg + _dt.timedelta(days=4)
        fim = min(sex, hoje - _dt.timedelta(days=1))
        if fim < seg:
            fim = seg

        feriados = _feriados_nacionais_br({seg.year, fim.year})
        sem_aula = get_dias_sem_aula(str(seg), str(fim))

        dias_uteis = [
            seg + _dt.timedelta(days=i)
            for i in range((fim - seg).days + 1)
            if (seg + _dt.timedelta(days=i)).weekday() < 5
            and (seg + _dt.timedelta(days=i)) not in feriados
            and (seg + _dt.timedelta(days=i)) not in sem_aula
        ]
        if not dias_uteis:
            return _section("📅 Dias sem Registro (semana)", "#64748B",
                            "<p style='color:#94A3B8;font-size:12px;'>Nenhum dia útil para verificar.</p>")

        por_dia  = get_presentes_periodo_todos(str(seg), str(fim))
        com_freq = {_dt.date.fromisoformat(k) for k in por_dia}
        pendentes = [d for d in dias_uteis if d not in com_freq]

        if not pendentes:
            return _section("📅 Dias sem Registro (semana)", _COR_VERDE,
                            "<p style='color:#16A34A;font-size:12px;'>✅ Todos os dias úteis da semana têm frequência registrada.</p>")

        dias_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        linhas  = [
            [
                d.strftime("%d/%m/%Y"),
                dias_pt[d.weekday()],
                "Sem frequência lançada",
                _btn(_link_freq(base_url, d.isoformat()), "📊 Lançar frequência", _COR_VERMELHO),
            ]
            for d in pendentes
        ]
        tabela  = _tabela(["Data", "Dia", "Situação", "Resolver"], linhas)
        aviso   = (f"<p style='color:{_COR_VERMELHO};font-size:12px;font-weight:700;"
                   f"margin-bottom:10px;'>⚠️ {len(pendentes)} dia(s) sem frequência registrada esta semana</p>")
        return _section("📅 Dias sem Registro (semana)", _COR_VERMELHO, aviso + tabela)
    except Exception as e:
        return _section("📅 Dias sem Registro (semana)", "#64748B",
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


def _bloco_aniversariantes() -> str:
    try:
        import datetime as _dt
        from database import supabase
        from utils.texto import formatar_whatsapp_numero

        hoje  = _dt.date.today()
        seg   = hoje - _dt.timedelta(days=hoje.weekday())
        sex   = seg + _dt.timedelta(days=6)
        meses = {seg.month, sex.month}

        res = supabase.from_("alunos").select(
            "nome,data_nascimento,turma,whatsapp,status"
        ).eq("status", "Ativo").execute()

        aniversariantes = []
        for a in (res.data or []):
            dn = a.get("data_nascimento")
            if not dn:
                continue
            try:
                dt = _dt.date.fromisoformat(str(dn)[:10])
                if dt.month not in meses:
                    continue
                aniv = dt.replace(year=hoje.year)
                if seg <= aniv <= sex:
                    aniversariantes.append({**a, "_aniv": aniv})
            except Exception:
                continue

        if not aniversariantes:
            return _section("🎂 Aniversariantes da Semana", "#7C3AED",
                            "<p style='color:#94A3B8;font-size:12px;'>Nenhum aniversariante esta semana.</p>")

        linhas = []
        for a in sorted(aniversariantes, key=lambda x: x["_aniv"]):
            nome  = str(a.get("nome", "—")).upper()
            turma = str(a.get("turma", "—") or "—")
            data  = a["_aniv"].strftime("%d/%m")
            wap   = str(a.get("whatsapp", "") or "")
            num   = formatar_whatsapp_numero(wap) if wap else None
            contato = (
                f'<a href="https://wa.me/{num}" style="color:#16A34A;font-size:11px;">📲 WhatsApp</a>'
                if num else '<span style="color:#94A3B8;font-size:11px;">—</span>'
            )
            linhas.append([f"🎂 {data}", nome, turma, contato])

        tabela = _tabela(["Data", "Aluno", "Turma", "Contato"], linhas)
        aviso  = (f"<p style='color:#7C3AED;font-size:12px;font-weight:700;"
                  f"margin-bottom:10px;'>🎂 {len(aniversariantes)} aniversariante(s) esta semana</p>")
        return _section("🎂 Aniversariantes da Semana", "#7C3AED", aviso + tabela)
    except Exception as e:
        return _section("🎂 Aniversariantes da Semana", "#7C3AED",
                        f"<p style='color:#94A3B8;font-size:12px;'>Dados indisponíveis: {e}</p>")


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DO HTML COMPLETO
# ──────────────────────────────────────────────────────────────────────────────

def gerar_html_relatorio(cfg: dict, nome_org: str = "Instituto Muda Brasil",
                         base_url: str = "") -> str:
    hoje_fmt = datetime.date.today().strftime("%d/%m/%Y")
    freq_label = {"semanal": "Semanal", "quinzenal": "Quinzenal", "mensal": "Mensal"}.get(
        cfg.get("frequencia", "semanal"), "Periódico"
    )
    base_url = (cfg.get("base_url", "") or base_url or "").rstrip("/")

    blocos = ""
    if cfg.get("mod_executivo"):
        blocos += _bloco_executivo()
    if cfg.get("mod_presencas_mes"):
        blocos += _bloco_presencas_mes()
    if cfg.get("mod_evasao"):
        blocos += _bloco_evasao(base_url)
    if cfg.get("mod_auditoria"):
        blocos += _bloco_auditoria(base_url)
    if cfg.get("mod_novos_cadastros"):
        blocos += _bloco_novos_cadastros(base_url)
    if cfg.get("mod_frequencia_turma"):
        blocos += _bloco_frequencia_turma()
    if cfg.get("mod_dias_sem_registro"):
        blocos += _bloco_dias_sem_registro(base_url)
    if cfg.get("mod_aniversariantes"):
        blocos += _bloco_aniversariantes()

    if not blocos:
        blocos = "<p style='color:#94A3B8;'>Nenhum módulo habilitado para este relatório.</p>"

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Relatório BI — {nome_org}</title>
</head>
<body style="font-family:Arial,Helvetica,sans-serif;color:#1E293B;
             background:#F1F5F9;margin:0;padding:20px;">
  <div style="max-width:680px;margin:0 auto;">

    <div style="background:linear-gradient(135deg,#0A2540,#1a3a5c);
                padding:28px 24px;border-radius:12px 12px 0 0;text-align:center;">
      <h1 style="color:white;margin:0;font-size:20px;letter-spacing:.5px;">
        📊 Relatório Gerencial BI
      </h1>
      <p style="color:rgba(255,255,255,.75);margin:6px 0 0;font-size:13px;">
        {nome_org} &nbsp;·&nbsp; {freq_label} &nbsp;·&nbsp; {hoje_fmt}
      </p>
    </div>

    <div style="background:white;padding:24px;border:1px solid #E2E8F0;
                border-top:none;border-radius:0 0 12px 12px;">
      {blocos}
    </div>

    <p style="text-align:center;color:#94A3B8;font-size:11px;margin-top:16px;">
      Gerado automaticamente pelo Sistema de Gestão IMBRA · MoveRight<br>
      Este e-mail é destinado exclusivamente à equipe de gestão.
    </p>
  </div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# ENVIO VIA GMAIL SMTP
# ──────────────────────────────────────────────────────────────────────────────

def enviar_relatorio_bi(cfg: dict, nome_org: str = "Instituto Muda Brasil",
                        base_url: str = "") -> tuple:
    emails    = cfg.get("emails_destino", [])
    remetente = cfg.get("email_remetente", "").strip()
    senha     = cfg.get("email_senha_app", "").strip()

    if not emails:
        return False, "Nenhum e-mail de destino configurado."
    if not remetente or not senha:
        return False, "Remetente ou senha de app Gmail não configurados."

    hoje_fmt   = datetime.date.today().strftime("%d/%m/%Y")
    freq_label = {"semanal": "Semanal", "quinzenal": "Quinzenal", "mensal": "Mensal"}.get(
        cfg.get("frequencia", "semanal"), "Periódico"
    )
    extra    = cfg.get("assunto_extra", "").strip()
    assunto  = f"📊 Relatório BI {freq_label} — {hoje_fmt}"
    if extra:
        assunto += f" | {extra}"

    try:
        html_body = gerar_html_relatorio(cfg, nome_org, base_url)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"]    = remetente
        msg["To"]      = ", ".join(emails)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, emails, msg.as_string())

        return True, f"Relatório enviado para: {', '.join(emails)}"
    except Exception as e:
        return False, f"Erro ao enviar: {e}"
