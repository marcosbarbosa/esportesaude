"""Regressões da data configurável de início do ano letivo.

Executar:
    uv run --no-sync python tests/test_inicio_ano_letivo.py
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows, cortes):
        self.rows = list(rows)
        self.cortes = cortes

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, coluna, valor):
        self.rows = [r for r in self.rows if r.get(coluna) == valor]
        return self

    def gte(self, coluna, valor):
        if coluna == "data_aula":
            self.cortes.append(str(valor))
        self.rows = [r for r in self.rows if str(r.get(coluna, "")) >= str(valor)]
        return self

    def lte(self, coluna, valor):
        self.rows = [r for r in self.rows if str(r.get(coluna, "")) <= str(valor)]
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, inicio, fim):
        self.rows = self.rows[inicio:fim + 1]
        return self

    def execute(self):
        return _FakeResp(self.rows)


class _FakeSupabase:
    def __init__(self, rows, cortes):
        self.rows = rows
        self.cortes = cortes

    def from_(self, tabela):
        assert tabela == "frequencia"
        return _FakeQuery(self.rows, self.cortes)


REGISTROS = [
    {"aluno_id": "a", "data_aula": "2026-01-20", "status": "PRESENTE"},
    {"aluno_id": "a", "data_aula": "2026-02-03", "status": "PRESENTE"},
    {"aluno_id": "a", "data_aula": "2026-02-04", "status": "PRESENTE"},
    {"aluno_id": "b", "data_aula": "2026-02-04", "status": "PRESENTE"},
]


def _limpar_caches():
    for funcao in (
        db.load_total_presencas_todos,
        db.bi_presencas_por_mes,
        db.get_datas_aulas_validas,
        db.get_aulas_por_mes_no_ano,
        db.get_datas_letivas_detalhadas_no_ano,
        db.get_numero_aula_no_ano,
    ):
        funcao.clear()


def test_fallbacks_da_configuracao():
    original = db.get_config_valor
    referencia = dt.date(2026, 8, 20)
    try:
        db.get_config_valor = lambda *_args, **_kwargs: "2026-02-03"
        assert db.get_inicio_ano_letivo(referencia) == dt.date(2026, 2, 3)

        db.get_config_valor = lambda *_args, **_kwargs: "valor-inválido"
        assert db.get_inicio_ano_letivo(referencia) == dt.date(2026, 1, 1)

        db.get_config_valor = lambda *_args, **_kwargs: "2025-02-03"
        assert db.get_inicio_ano_letivo(referencia) == dt.date(2026, 1, 1)
    finally:
        db.get_config_valor = original


def test_contadores_usam_corte_configurado_e_cache_pode_ser_invalidado():
    original_config = db.get_config_valor
    original_supabase = db.supabase
    cortes = []
    try:
        db.supabase = _FakeSupabase(REGISTROS, cortes)
        db.get_config_valor = lambda *_args, **_kwargs: "2026-02-03"
        _limpar_caches()

        totais = db.load_total_presencas_todos().set_index("id")[
            "total_presencas_hist"
        ].to_dict()
        assert totais == {"a": 2, "b": 1}
        assert cortes[-1] == "2026-02-03"

        resumo_bi = db.bi_presencas_por_mes()
        assert resumo_bi["total_ano"] == 3
        assert resumo_bi["por_mes"][0] == ("Fev/26", 3)
        assert all(qtd == 0 for _, qtd in resumo_bi["por_mes"][1:])
        assert resumo_bi["inicio_ano_letivo"] == "2026-02-03"
        assert cortes[-1] == "2026-02-03"

        assert db.get_numero_aula_no_ano("2026-02-04") == 2
        assert db.get_aulas_por_mes_no_ano(2026) == {2: 2}
        detalhes = db.get_datas_letivas_detalhadas_no_ano(2026)
        assert detalhes[2] == [
            ("2026-02-03", 1),
            ("2026-02-04", 2),
        ]

        db.get_config_valor = lambda *_args, **_kwargs: "2026-03-01"
        _limpar_caches()
        db.load_total_presencas_todos()
        assert cortes[-1] == "2026-03-01"
    finally:
        db.get_config_valor = original_config
        db.supabase = original_supabase
        _limpar_caches()


def _main():
    testes = [
        test_fallbacks_da_configuracao,
        test_contadores_usam_corte_configurado_e_cache_pode_ser_invalidado,
    ]
    falhas = 0
    for teste in testes:
        try:
            teste()
            print(f"PASS  {teste.__name__}")
        except AssertionError as erro:
            falhas += 1
            print(f"FAIL  {teste.__name__}\n      {erro}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(_main())