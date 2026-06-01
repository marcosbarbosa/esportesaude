# ==============================================================================
# 📄 utils/email_relatorio_config.py
# ⚙️  Config do módulo Email BI — leitura/gravação via configuracoes_sistema
# ==============================================================================

import json
import streamlit as st

_CHAVES = [
    "ebi_emails_destino",
    "ebi_email_remetente",
    "ebi_email_senha_app",
    "ebi_habilitado",
    "ebi_frequencia",
    "ebi_dia_semana",
    "ebi_dia_mes",
    "ebi_proximo_envio",
    "ebi_ultimo_envio",
    "ebi_mod_executivo",
    "ebi_mod_evasao",
    "ebi_mod_auditoria",
    "ebi_mod_novos_cadastros",
    "ebi_mod_frequencia_turma",
    "ebi_mod_dias_sem_registro",
    "ebi_mod_aniversariantes",
    "ebi_mod_presencas_mes",
    "ebi_assunto_extra",
    "ebi_base_url",
]


@st.cache_data(ttl=60, show_spinner=False)
def _ler_cfg_ebi() -> dict:
    from database import supabase
    try:
        res = (
            supabase.table("configuracoes_sistema")
            .select("chave,valor")
            .in_("chave", _CHAVES)
            .execute()
        )
        return {r["chave"]: r["valor"] for r in (res.data or [])}
    except Exception:
        return {}


def _salvar(chave: str, valor: str) -> None:
    from database import supabase
    try:
        supabase.table("configuracoes_sistema").upsert(
            {"chave": chave, "valor": str(valor)}, on_conflict="chave"
        ).execute()
        _ler_cfg_ebi.clear()
    except Exception as e:
        st.error(f"Erro ao salvar '{chave}': {e}")


def salvar_config_ebi(dados: dict) -> None:
    for chave, valor in dados.items():
        _salvar(chave, str(valor))


def _parse_emails(raw: str) -> list:
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [e.strip() for e in val if e.strip()]
    except Exception:
        pass
    return [e.strip() for e in raw.split(",") if e.strip()]


def get_config_ebi() -> dict:
    cfg = _ler_cfg_ebi()
    return {
        "emails_destino":        _parse_emails(cfg.get("ebi_emails_destino", "[]")),
        "email_remetente":       cfg.get("ebi_email_remetente", ""),
        "email_senha_app":       cfg.get("ebi_email_senha_app", ""),
        "habilitado":            cfg.get("ebi_habilitado", "0") == "1",
        "frequencia":            cfg.get("ebi_frequencia", "semanal"),
        "dia_semana":            int(cfg.get("ebi_dia_semana", "4") or "4"),
        "dia_mes":               int(cfg.get("ebi_dia_mes", "1") or "1"),
        "proximo_envio":         cfg.get("ebi_proximo_envio", ""),
        "ultimo_envio":          cfg.get("ebi_ultimo_envio", ""),
        "mod_executivo":         cfg.get("ebi_mod_executivo", "1") == "1",
        "mod_evasao":            cfg.get("ebi_mod_evasao", "1") == "1",
        "mod_auditoria":         cfg.get("ebi_mod_auditoria", "1") == "1",
        "mod_novos_cadastros":   cfg.get("ebi_mod_novos_cadastros", "1") == "1",
        "mod_frequencia_turma":  cfg.get("ebi_mod_frequencia_turma", "1") == "1",
        "mod_dias_sem_registro": cfg.get("ebi_mod_dias_sem_registro", "1") == "1",
        "mod_aniversariantes":   cfg.get("ebi_mod_aniversariantes", "1") == "1",
        "mod_presencas_mes":     cfg.get("ebi_mod_presencas_mes", "1") == "1",
        "assunto_extra":         cfg.get("ebi_assunto_extra", ""),
        "base_url":              cfg.get("ebi_base_url", ""),
    }


def calcular_proximo_envio(cfg: dict) -> "datetime.date":
    import datetime
    hoje = datetime.date.today()
    freq = cfg.get("frequencia", "semanal")

    if freq in ("semanal", "quinzenal"):
        dia_alvo = cfg.get("dia_semana", 4)
        dias_ate = (dia_alvo - hoje.weekday()) % 7
        if dias_ate == 0:
            dias_ate = 7
        proximo = hoje + datetime.timedelta(days=dias_ate)
        if freq == "quinzenal":
            # Ancora a cadência de 14 dias no último envio realizado.
            # Se a próxima ocorrência do dia-alvo cair a menos de 11 dias
            # do último envio, empurra +7 para manter o intervalo quinzenal.
            ultimo = cfg.get("ultimo_envio", "")
            if ultimo:
                try:
                    d_ult = datetime.date.fromisoformat(str(ultimo)[:10])
                    if (proximo - d_ult).days < 11:
                        proximo += datetime.timedelta(days=7)
                except Exception:
                    pass
        return proximo

    # mensal
    dia_mes = max(1, min(28, cfg.get("dia_mes", 1)))
    proximo = hoje.replace(day=dia_mes)
    if proximo <= hoje:
        mes = hoje.month + 1
        ano = hoje.year
        if mes > 12:
            mes = 1
            ano += 1
        proximo = proximo.replace(year=ano, month=mes)
    return proximo


def verificar_e_marcar_envio_realizado(cfg: dict) -> None:
    import datetime
    agora = datetime.datetime.now()
    # Ancora o cálculo do próximo envio no momento atual (este envio),
    # não no último envio anterior — essencial para a cadência quinzenal.
    cfg_atualizado = {**cfg, "ultimo_envio": agora.date().isoformat()}
    proximo = calcular_proximo_envio(cfg_atualizado)
    salvar_config_ebi({
        "ebi_ultimo_envio":  agora.isoformat(timespec="seconds"),
        "ebi_proximo_envio": str(proximo),
    })
