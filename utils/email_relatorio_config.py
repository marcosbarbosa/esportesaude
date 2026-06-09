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
    cfg_atualizado = {**cfg, "ultimo_envio": agora.date().isoformat()}
    proximo = calcular_proximo_envio(cfg_atualizado)
    salvar_config_ebi({
        "ebi_ultimo_envio":  agora.isoformat(timespec="seconds"),
        "ebi_proximo_envio": str(proximo),
    })


# ==============================================================================
# MULTI-SCHEDULE: tabela email_bi_schedules
# ==============================================================================

@st.cache_data(ttl=30, show_spinner=False)
def _ler_schedules() -> list | None:
    """Retorna lista de schedules ou None se a tabela não existe."""
    from database import supabase
    try:
        res = supabase.table("email_bi_schedules").select("*").order("criado_em").execute()
        return res.data or []
    except Exception as e:
        msg = str(e).lower()
        if "relation" in msg or "not found" in msg or "does not exist" in msg or "pgr" in msg:
            return None
        return []


def get_schedules() -> list | None:
    return _ler_schedules()


def salvar_schedule(dados: dict, schedule_id: str | None = None) -> str | None:
    """Cria ou atualiza um pacote. Retorna o ID salvo."""
    import datetime
    from database import supabase
    agora = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload = {
        "nome":            dados.get("nome", "Pacote de Envio"),
        "habilitado":      bool(dados.get("habilitado", False)),
        "frequencia":      dados.get("frequencia", "semanal"),
        "dia_semana":      int(dados.get("dia_semana", 4)),
        "dia_mes":         int(dados.get("dia_mes", 1)),
        "emails_destino":  dados.get("emails_destino", []),
        "modulos":         dados.get("modulos", {}),
        "assunto_extra":   dados.get("assunto_extra", ""),
        "email_remetente": dados.get("email_remetente", ""),
        "email_senha_app": dados.get("email_senha_app", ""),
        "base_url":        dados.get("base_url", ""),
        "proximo_envio":   dados.get("proximo_envio") or None,
        "atualizado_em":   agora,
    }
    try:
        if schedule_id:
            supabase.table("email_bi_schedules").update(payload).eq("id", schedule_id).execute()
            _ler_schedules.clear()
            return schedule_id
        else:
            res = supabase.table("email_bi_schedules").insert(payload).execute()
            _ler_schedules.clear()
            return res.data[0]["id"] if res.data else None
    except Exception as e:
        import streamlit as _st
        _st.error(f"Erro ao salvar pacote: {e}")
        return None


def excluir_schedule(schedule_id: str) -> None:
    from database import supabase
    try:
        supabase.table("email_bi_schedules").delete().eq("id", schedule_id).execute()
    except Exception:
        pass
    _ler_schedules.clear()


def marcar_envio_realizado_schedule(schedule_id: str, cfg: dict) -> None:
    """Incrementa total_envios, registra data no histórico e calcula próximo envio."""
    import datetime, json
    from database import supabase
    agora = datetime.datetime.now()
    try:
        res = (
            supabase.table("email_bi_schedules")
            .select("total_envios,historico_envios")
            .eq("id", schedule_id)
            .execute()
        )
        row = (res.data or [{}])[0]
        total = (row.get("total_envios") or 0) + 1
        historico = row.get("historico_envios") or []
        if isinstance(historico, str):
            try:
                historico = json.loads(historico)
            except Exception:
                historico = []
        historico.append(agora.isoformat(timespec="seconds"))
        historico = historico[-50:]

        cfg_para_calculo = {**cfg, "ultimo_envio": agora.date().isoformat()}
        proximo = calcular_proximo_envio(cfg_para_calculo)

        supabase.table("email_bi_schedules").update({
            "ultimo_envio":    agora.isoformat(timespec="seconds"),
            "proximo_envio":   str(proximo),
            "total_envios":    total,
            "historico_envios": historico,
            "atualizado_em":   agora.isoformat(timespec="seconds"),
        }).eq("id", schedule_id).execute()
    except Exception:
        pass
    _ler_schedules.clear()


def schedule_to_cfg(s: dict) -> dict:
    """Converte uma linha de email_bi_schedules para o dict esperado por enviar_relatorio_bi()."""
    import json
    modulos = s.get("modulos") or {}
    if isinstance(modulos, str):
        try:
            modulos = json.loads(modulos)
        except Exception:
            modulos = {}
    return {
        "emails_destino":        s.get("emails_destino") or [],
        "email_remetente":       s.get("email_remetente", ""),
        "email_senha_app":       s.get("email_senha_app", ""),
        "base_url":              s.get("base_url", ""),
        "assunto_extra":         s.get("assunto_extra", ""),
        "habilitado":            s.get("habilitado", False),
        "frequencia":            s.get("frequencia", "semanal"),
        "dia_semana":            int(s.get("dia_semana") or 4),
        "dia_mes":               int(s.get("dia_mes") or 1),
        "proximo_envio":         s.get("proximo_envio"),
        "ultimo_envio":          s.get("ultimo_envio"),
        "mod_executivo":         bool(modulos.get("executivo", True)),
        "mod_evasao":            bool(modulos.get("evasao", True)),
        "mod_auditoria":         bool(modulos.get("auditoria", True)),
        "mod_novos_cadastros":   bool(modulos.get("novos_cadastros", True)),
        "mod_frequencia_turma":  bool(modulos.get("frequencia_turma", True)),
        "mod_dias_sem_registro": bool(modulos.get("dias_sem_registro", True)),
        "mod_aniversariantes":   bool(modulos.get("aniversariantes", True)),
        "mod_presencas_mes":     bool(modulos.get("presencas_mes", True)),
    }


def migrar_legado_para_schedule() -> bool:
    """
    Migra a config legada (ebi_* em configuracoes_sistema) para a nova tabela.
    Executa apenas uma vez — se a tabela já tiver linhas, retorna False.
    """
    try:
        cfg = get_config_ebi()
        if not cfg.get("email_remetente") and not cfg.get("emails_destino"):
            return False
        dados = {
            "nome":            "Pacote Principal",
            "habilitado":      cfg["habilitado"],
            "frequencia":      cfg["frequencia"],
            "dia_semana":      cfg["dia_semana"],
            "dia_mes":         cfg["dia_mes"],
            "emails_destino":  cfg["emails_destino"],
            "modulos": {
                "executivo":         cfg["mod_executivo"],
                "evasao":            cfg["mod_evasao"],
                "auditoria":         cfg["mod_auditoria"],
                "novos_cadastros":   cfg["mod_novos_cadastros"],
                "frequencia_turma":  cfg["mod_frequencia_turma"],
                "dias_sem_registro": cfg["mod_dias_sem_registro"],
                "aniversariantes":   cfg["mod_aniversariantes"],
                "presencas_mes":     cfg["mod_presencas_mes"],
            },
            "assunto_extra":   cfg["assunto_extra"],
            "email_remetente": cfg["email_remetente"],
            "email_senha_app": cfg["email_senha_app"],
            "base_url":        cfg["base_url"],
            "proximo_envio":   cfg["proximo_envio"] or None,
            "ultimo_envio":    cfg["ultimo_envio"] or None,
        }
        salvar_schedule(dados)
        return True
    except Exception:
        return False
