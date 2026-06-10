"""
Helpers de UI compartilhados para o Histórico de Atestados.
Usado por prontuario_view.py e prontuario_ficha.py.
"""
import datetime

TIPOS_ATESTADO = {
    "🏋️ Aptidão Física (obrigatório para aulas)": "aptidao_fisica",
    "🩺 Condição Clínica / Doença":               "condicao_clinica",
    "🏥 Pós-Cirúrgico / Recuperação":             "pos_cirurgico",
    "⚠️ Restrição de Atividade":                  "restricao_atividade",
    "📋 Outro / Geral":                            "outro",
}

TIPOS_LABEL = {v: k for k, v in TIPOS_ATESTADO.items()}

_TIPO_BADGE_STYLE = {
    "aptidao_fisica":       ("#1e3a5f", "#8eb4e3"),
    "condicao_clinica":     ("#3a2d00", "#f0c040"),
    "pos_cirurgico":        ("#3a1800", "#f09040"),
    "restricao_atividade":  ("#3a0000", "#f06060"),
    "outro":                ("#2a2a2a", "#aaaaaa"),
}


def tipo_badge_html(tipo: str) -> str:
    label = TIPOS_LABEL.get(tipo, TIPOS_LABEL.get("outro", "📋 Outro / Geral"))
    bg, fg = _TIPO_BADGE_STYLE.get(tipo, _TIPO_BADGE_STYLE["outro"])
    return (
        f"<span style='background:{bg};color:{fg};"
        f"padding:2px 10px;border-radius:12px;font-size:.78em'>{label}</span>"
    )


def validade_badge_html(data_venc) -> str:
    if not data_venc or str(data_venc).strip() in ("", "None", "nan"):
        return "<span style='color:#777;font-size:.8em'>sem prazo</span>"
    hoje = datetime.date.today()
    if isinstance(data_venc, str):
        try:
            data_venc = datetime.date.fromisoformat(str(data_venc)[:10])
        except Exception:
            return ""
    dias = (data_venc - hoje).days
    dt_str = data_venc.strftime("%d/%m/%Y")
    if dias < 0:
        return (
            f"<span style='background:#5a0000;color:#ff8080;"
            f"padding:2px 8px;border-radius:10px;font-size:.78em'>"
            f"⛔ Vencido em {dt_str}</span>"
        )
    if dias <= 7:
        return (
            f"<span style='background:#5a2e00;color:#ffb060;"
            f"padding:2px 8px;border-radius:10px;font-size:.78em'>"
            f"⚠️ Vence em {dias}d ({dt_str})</span>"
        )
    if dias <= 30:
        return (
            f"<span style='background:#3a3a00;color:#f0e060;"
            f"padding:2px 8px;border-radius:10px;font-size:.78em'>"
            f"⏳ Vence em {dias}d ({dt_str})</span>"
        )
    return (
        f"<span style='background:#003a10;color:#60e080;"
        f"padding:2px 8px;border-radius:10px;font-size:.78em'>"
        f"✅ Válido até {dt_str}</span>"
    )
