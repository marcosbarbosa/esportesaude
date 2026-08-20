import datetime as dt
from pathlib import Path

from utils.mensagens_frequencia import (
    dias_sem_presenca,
    ids_assiduidade_destaque,
    recomendar_mensagem_frequencia,
)


HOJE = dt.date(2026, 8, 20)


def test_classifica_alerta_risco_e_evasao_sem_presenca():
    assert dias_sem_presenca("2026-08-15", HOJE) == 5
    assert recomendar_mensagem_frequencia("a", "2026-08-04", set(), HOJE).gatilho == "evasao_60"
    assert recomendar_mensagem_frequencia("a", "2026-07-19", set(), HOJE).gatilho == "evasao_80"
    assert recomendar_mensagem_frequencia("a", None, set(), HOJE).gatilho == "evasao_nunca"


def test_nao_sugere_mensagem_para_ausencia_curta():
    assert recomendar_mensagem_frequencia("a", "2026-08-06", set(), HOJE) is None


def test_presenca_historica_antiga_e_risco_critico_nao_evasao_nunca():
    recomendacao = recomendar_mensagem_frequencia("a", "2026-02-19", set(), HOJE)
    assert recomendacao.gatilho == "evasao_80"
    assert recomendacao.rotulo == "Risco crítico de ausência"


def test_destaque_e_justo_por_turma_e_exige_presenca_recente():
    alunos = [
        {"id": "a", "turma": "Manhã", "total_presencas_hist": 30, "ultima_presenca": "2026-08-19"},
        {"id": "b", "turma": "Manhã", "total_presencas_hist": 20, "ultima_presenca": "2026-08-19"},
        {"id": "c", "turma": "Manhã", "total_presencas_hist": 11, "ultima_presenca": "2026-08-19"},
        {"id": "d", "turma": "Tarde", "total_presencas_hist": 50, "ultima_presenca": "2026-07-01"},
        {"id": "e", "turma": "Tarde", "total_presencas_hist": 15, "ultima_presenca": "2026-08-20"},
    ]
    destaques = ids_assiduidade_destaque(alunos, HOJE)

    # A aluna "d" tem mais presenças acumuladas, mas está ausente. Ela não
    # bloqueia o elogio para "e", que lidera entre as pessoas presentes.
    assert destaques == {"a", "e"}
    assert recomendar_mensagem_frequencia("a", "2026-08-19", destaques, HOJE).gatilho == "assiduo_top"
    assert recomendar_mensagem_frequencia("e", "2026-08-20", destaques, HOJE).gatilho == "assiduo_top"
    assert recomendar_mensagem_frequencia("d", "2026-07-01", destaques, HOJE).gatilho == "evasao_80"


def test_nao_elogia_turma_sem_volume_minimo_de_presencas():
    alunos = [
        {"id": "a", "turma": "Noite", "total_presencas_hist": 4, "ultima_presenca": "2026-08-20"},
        {"id": "b", "turma": "Noite", "total_presencas_hist": 3, "ultima_presenca": "2026-08-20"},
    ]
    assert ids_assiduidade_destaque(alunos, HOJE) == set()


def test_migration_cria_modelo_editavel_sem_sobrescrever_personalizacao():
    migration = Path("migrations/006_seed_template_assiduidade.sql").read_text(encoding="utf-8")
    assert "assiduo_top" in migration
    assert "Elogio de Assiduidade" in migration
    assert "{nome}" in migration
    assert "WHERE NOT EXISTS" in migration