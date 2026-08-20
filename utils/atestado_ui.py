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


def _converter_para_data(valor):
    """Converte valores comuns do Supabase/Pandas para date, sem lançar exceção."""
    if valor is None:
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() in ("none", "nan", "nat", "null"):
        return None
    try:
        return datetime.date.fromisoformat(texto[:10])
    except (TypeError, ValueError):
        return None


def _registros_para_lista(registros):
    """Aceita DataFrame, lista de dicts ou um dict e devolve lista de dicts."""
    if registros is None:
        return []
    if hasattr(registros, "to_dict"):
        try:
            return registros.to_dict("records")
        except (TypeError, ValueError):
            return []
    if isinstance(registros, dict):
        return [registros]
    try:
        return [registro for registro in registros if isinstance(registro, dict)]
    except TypeError:
        return []


def status_atestado(registros=None, bloqueado_manual=False, hoje=None):
    """Calcula a situação canônica do atestado de aptidão de um aluno.

    A fonte é sempre o último registro de ``aptidao_fisica`` pela data do
    atestado (``data_registro``), nunca uma data calculada ou outro tipo de
    documento. O retorno é estável para ser usado em DataFrames, prontuário,
    dossiê, tela inicial e chamada diária.

    ``bloqueado_manual`` é uma trava administrativa independente da validade:
    ela bloqueia a participação, mas não muda nem apaga a data do atestado.
    """
    hoje = hoje or datetime.date.today()
    todos = _registros_para_lista(registros)
    aptidoes = [
        registro for registro in todos
        if str(registro.get("tipo_atestado") or "").strip() == "aptidao_fisica"
    ]

    if not aptidoes:
        return {
            "status_atestado": "SEM_REGISTRO",
            "rotulo_atestado": "Sem atestado de aptidão registrado",
            "data_vencimento_atestado": None,
            "data_vencimento_formatada": "—",
            "atestado_dias_restantes": None,
            "atestado_icone": "📋",
            "atestado_cor": "#64748B",
            "atestado_fundo": "#F1F5F9",
            "atestado_bloqueado_manual": bool(bloqueado_manual),
        }

    # "data_registro" é a data informada no cadastro do documento. Em empate,
    # a maior validade vence somente para manter o resultado determinístico.
    def _chave_ordenacao(registro):
        return (
            _converter_para_data(registro.get("data_registro")) or datetime.date.min,
            _converter_para_data(registro.get("data_vencimento")) or datetime.date.min,
            str(registro.get("id") or ""),
        )

    atual = max(aptidoes, key=_chave_ordenacao)
    vencimento = _converter_para_data(atual.get("data_vencimento"))
    base = {
        "data_vencimento_atestado": vencimento.isoformat() if vencimento else None,
        "data_vencimento_formatada": vencimento.strftime("%d/%m/%Y") if vencimento else "—",
        "atestado_bloqueado_manual": bool(bloqueado_manual),
    }

    if not vencimento:
        return {
            **base,
            "status_atestado": "SEM_VALIDIDADE",
            "rotulo_atestado": "Atestado sem data de validade",
            "atestado_dias_restantes": None,
            "atestado_icone": "⚠️",
            "atestado_cor": "#92400E",
            "atestado_fundo": "#FEF3C7",
        }

    dias = (vencimento - hoje).days
    if dias < 0:
        return {
            **base,
            "status_atestado": "VENCIDO",
            "rotulo_atestado": f"Vencido há {abs(dias)} dia(s)",
            "atestado_dias_restantes": dias,
            "atestado_icone": "⛔",
            "atestado_cor": "#991B1B",
            "atestado_fundo": "#FEE2E2",
        }
    if dias <= 30:
        return {
            **base,
            "status_atestado": "A_VENCER",
            "rotulo_atestado": (
                "Vence hoje" if dias == 0 else f"Vence em {dias} dia(s)"
            ),
            "atestado_dias_restantes": dias,
            "atestado_icone": "⚠️",
            "atestado_cor": "#92400E",
            "atestado_fundo": "#FEF3C7",
        }
    return {
        **base,
        "status_atestado": "VALIDO",
        "rotulo_atestado": f"Válido por mais {dias} dia(s)",
        "atestado_dias_restantes": dias,
        "atestado_icone": "✅",
        "atestado_cor": "#166534",
        "atestado_fundo": "#D1FAE5",
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
