import datetime as dt

from utils.calendario_aulas import (
    contar_aulas_por_mes,
    filtrar_datas_aulas_validas,
    sequenciar_datas_aulas,
)


def test_data_sem_aula_nao_entra_na_contagem_mesmo_com_faltas():
    lancamentos = [
        {"data_aula": "2026-04-01", "status": "PRESENTE"},
        {"data_aula": "2026-04-02", "status": "FALTA"},
        {"data_aula": "2026-04-02", "status": "PRESENTE"},
        {"data_aula": "2026-04-02", "status": "FALTA"},
        {"data_aula": "2026-04-03", "status": "JUSTIFICADA"},
    ]

    datas = filtrar_datas_aulas_validas(lancamentos, {dt.date(2026, 4, 2)})

    assert datas == ("2026-04-01", "2026-04-03")


def test_sequencia_anual_e_progresso_mensal_usam_somente_datas_validas():
    datas = ("2026-01-30", "2026-02-02", "2026-02-05")

    assert sequenciar_datas_aulas(datas) == (
        ("2026-01-30", 1),
        ("2026-02-02", 2),
        ("2026-02-05", 3),
    )
    assert contar_aulas_por_mes(datas) == {1: 1, 2: 2}


def test_limpar_cache_de_contagem_limpa_todas_as_visoes():
    import database

    class CacheSpy:
        def __init__(self):
            self.calls = 0

        def clear(self):
            self.calls += 1

    nomes = (
        "get_datas_aulas_validas",
        "get_datas_letivas_detalhadas_no_ano",
        "get_aulas_por_mes_no_ano",
        "get_numero_aula_no_ano",
    )
    originais = {nome: getattr(database, nome) for nome in nomes}
    spies = {nome: CacheSpy() for nome in nomes}
    try:
        for nome, spy in spies.items():
            setattr(database, nome, spy)
        database.limpar_cache_contagem_aulas()
        assert all(spy.calls == 1 for spy in spies.values())
    finally:
        for nome, original in originais.items():
            setattr(database, nome, original)


def test_mutacao_de_frequencia_limpa_contagem_canonica():
    import database

    calls = []
    original = database.limpar_cache_contagem_aulas
    try:
        database.limpar_cache_contagem_aulas = lambda: calls.append("limpo")
        database._inv_frequencia()
        assert calls == ["limpo"]
    finally:
        database.limpar_cache_contagem_aulas = original


def test_mutacoes_do_calendario_limpam_contagem_canonica():
    import database

    class Resposta:
        data = []

    class ConsultaFalsa:
        def __init__(self, falhar_insert=False):
            self.falhar_insert = falhar_insert
            self.acao = None

        def insert(self, _payload):
            self.acao = "insert"
            return self

        def update(self, _payload):
            self.acao = "update"
            return self

        def delete(self):
            self.acao = "delete"
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            if self.acao == "insert" and self.falhar_insert:
                raise RuntimeError("duplicada")
            return Resposta()

    class SupabaseFalso:
        def __init__(self, falhar_insert=False):
            self.falhar_insert = falhar_insert

        def from_(self, _tabela):
            return ConsultaFalsa(self.falhar_insert)

    original_supabase = database.supabase
    original_limpar = database.limpar_cache_contagem_aulas
    calls = []
    try:
        database.limpar_cache_contagem_aulas = lambda: calls.append("limpo")
        database.supabase = SupabaseFalso()
        assert database.registrar_dia_sem_aula("2026-04-02")
        database.supabase = SupabaseFalso(falhar_insert=True)
        assert database.registrar_dia_sem_aula("2026-04-02")
        database.supabase = SupabaseFalso()
        assert database.remover_dia_sem_aula("2026-04-02")
        assert calls == ["limpo", "limpo", "limpo"]
    finally:
        database.supabase = original_supabase
        database.limpar_cache_contagem_aulas = original_limpar


def test_media_semanal_do_bi_ignora_segunda_sem_aula():
    import pandas as pd
    from views.bi_dashboard_view import _calcular_media_semana

    # 13/04 seria outra segunda, mas está bloqueado pelo Calendário Institucional
    # e já foi removido do dataframe de presenças antes do cálculo.
    presencas_validas = pd.DataFrame(
        [{"data_aula": "2026-04-06", "aluno_id": "aluno-1"}]
    )

    media = _calcular_media_semana(presencas_validas, {"2026-04-06"})

    segunda = float(media.loc[media["dia"] == "Segunda", "media"].iloc[0])
    assert segunda == 1.0