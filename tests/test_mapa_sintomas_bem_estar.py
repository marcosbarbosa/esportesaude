"""Testes de segurança e compatibilidade do Mapa de Sintomas e Bem-Estar."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database
from views import anamnese_dores_view as mapa_view


class _ConsultaMapa:
    def __init__(self, cliente, tabela):
        self.cliente = cliente
        self.tabela = tabela
        self.colunas = ""
        self.filtros = {}
        self.ordem = None
        self.limite = None
        self.acao = "select"
        self.payload = None

    def select(self, colunas):
        self.colunas = colunas
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = str(valor)
        return self

    def order(self, campo, desc=False):
        self.ordem = (campo, desc)
        return self

    def limit(self, limite):
        self.limite = limite
        return self

    def insert(self, payload):
        self.acao = "insert"
        self.payload = deepcopy(payload)
        return self

    def execute(self):
        if self.acao == "insert":
            self.cliente.inseridos.append(deepcopy(self.payload))
            return SimpleNamespace(data=[deepcopy(self.payload)])

        self.cliente.operacoes.append((self.tabela, self.colunas, deepcopy(self.filtros)))
        solicitadas = {campo.strip() for campo in self.colunas.split(",")}
        if not solicitadas.issubset(self.cliente.colunas):
            raise RuntimeError("coluna indisponível no schema simulado")

        dados = [
            deepcopy(registro)
            for registro in self.cliente.registros
            if all(str(registro.get(campo)) == valor for campo, valor in self.filtros.items())
        ]
        if self.ordem:
            campo, desc = self.ordem
            dados.sort(key=lambda registro: str(registro.get(campo) or ""), reverse=desc)
        if self.limite is not None:
            dados = dados[: self.limite]
        return SimpleNamespace(data=dados)


class _SupabaseMapa:
    def __init__(self, registros, colunas):
        self.registros = registros
        self.colunas = set(colunas)
        self.operacoes = []
        self.inseridos = []

    def from_(self, tabela):
        assert tabela == "anamnese_dores"
        return _ConsultaMapa(self, tabela)

    def table(self, tabela):
        return self.from_(tabela)


def _mapa_atual():
    return {
        "id": "registro-1",
        "aluno_id": "aluno-1",
        "data_avaliacao": "2026-08-23",
        "regioes": ["f_ombro_e", "c_lombar"],
        "intensidade": {"f_ombro_e": "3", "c_lombar": 2},
        "observacoes": "Conteúdo confidencial.",
        "criado_por": "operador-confidencial",
    }


def test_normaliza_regioes_atuais_e_legadas_sem_inferencia():
    assert database.normalizar_regioes_anamnese({"regioes": ["f_ombro_e"]}) == ["f_ombro_e"]
    assert database.normalizar_regioes_anamnese({"regioes": '["c_lombar"]'}) == ["c_lombar"]
    assert database.normalizar_regioes_anamnese({"regiao": "f_joelho_d"}) == ["f_joelho_d"]
    assert database.normalizar_regioes_anamnese({"regioes": [], "regiao": "c_nuca"}) == ["c_nuca"]


def test_historico_legado_usa_projecao_minima_sem_select_asterisco():
    legado = {
        "id": "registro-legado",
        "aluno_id": "aluno-1",
        "data_avaliacao": "2026-01-10",
        "regiao": "c_lombar",
        "intensidade": '{"c_lombar": 2}',
        "observacoes": "Não deve sair na lista.",
        "criado_por": "Não deve sair na lista.",
    }
    cliente = _SupabaseMapa(
        [legado],
        {"id", "aluno_id", "data_avaliacao", "regiao", "intensidade"},
    )
    with patch.object(database, "supabase", cliente):
        historico = database.buscar_historico_dores_restrito("aluno-1")

    assert historico == [{
        "id": "registro-legado",
        "data_avaliacao": "2026-01-10",
        "regioes": ["c_lombar"],
        "intensidade": {"c_lombar": 2},
    }]
    assert all("*" not in colunas for _, colunas, _ in cliente.operacoes)


def test_leitura_legada_do_dossie_preserva_observacao_sem_buscar_autor():
    registro = _mapa_atual()
    cliente = _SupabaseMapa(
        [registro],
        {
            "id",
            "aluno_id",
            "data_avaliacao",
            "regioes",
            "intensidade",
            "observacoes",
        },
    )
    with patch.object(database, "supabase", cliente):
        historico_dossie = database.buscar_historico_dores("aluno-1")

    assert historico_dossie[0]["observacoes"] == "Conteúdo confidencial."
    assert "criado_por" not in historico_dossie[0]
    assert all("criado_por" not in colunas for _, colunas, _ in cliente.operacoes)
    assert all("*" not in colunas for _, colunas, _ in cliente.operacoes)


def test_resumo_e_bi_individual_nao_repassam_observacoes_nem_autor():
    registro = _mapa_atual()
    cliente = _SupabaseMapa(
        [registro],
        {"id", "aluno_id", "data_avaliacao", "regioes", "intensidade"},
    )
    with patch.object(database, "supabase", cliente):
        resumo = database.buscar_ultima_anamnese_dores("aluno-1")
        dados_bi = database.bi_dados_individuais("aluno-1")

    assert resumo == {
        "data_avaliacao": "2026-08-23",
        "regioes": ["f_ombro_e", "c_lombar"],
        "intensidade": {"f_ombro_e": 3, "c_lombar": 2},
    }
    assert "observacoes" not in resumo
    assert "criado_por" not in resumo
    assert dados_bi["dores"] == [resumo]
    assert "observacoes" not in dados_bi["dores"][0]
    assert "criado_por" not in dados_bi["dores"][0]


def test_gravacao_existente_preserva_payload_e_invalida_leituras():
    cliente = _SupabaseMapa([], set())
    with (
        patch.object(database, "supabase", cliente),
        patch.object(database, "_inv_dores") as invalidar,
    ):
        ok, _ = database.salvar_anamnese_dores(
            aluno_id="aluno-1",
            data_avaliacao="2026-08-23",
            regioes=["f_ombro_e", "c_lombar"],
            intensidade={"f_ombro_e": 3, "c_lombar": 2},
            observacoes="Relato autorreferido.",
            criado_por="operador",
        )

    assert ok is True
    assert cliente.inseridos == [{
        "aluno_id": "aluno-1",
        "data_avaliacao": "2026-08-23",
        "regioes": ["f_ombro_e", "c_lombar"],
        "intensidade": {"f_ombro_e": 3, "c_lombar": 2},
        "observacoes": "Relato autorreferido.",
        "criado_por": "operador",
    }]
    invalidar.assert_called_once_with()


def test_invalida_cache_do_bi_geral():
    with patch.object(database.bi_dores_studio, "clear") as limpar_bi_geral:
        database._inv_dores()
    limpar_bi_geral.assert_called_once_with()


def test_bi_geral_normaliza_e_entrega_somente_contagens_agregadas():
    registros = [
        {"regioes": ["f_ombro_e", "c_lombar"]},
        {"regiao": "c_lombar"},
    ]
    cliente = _SupabaseMapa(registros, {"regioes", "regiao"})
    database.bi_dores_studio.clear()
    with patch.object(database, "supabase", cliente):
        resultado = database.bi_dores_studio()
    database.bi_dores_studio.clear()

    assert isinstance(resultado, pd.DataFrame)
    assert resultado.to_dict("records") == [
        {"label": "c_lombar", "count": 2},
        {"label": "f_ombro_e", "count": 1},
    ]
    assert set(resultado.columns) == {"label", "count"}
    assert all("*" not in colunas for _, colunas, _ in cliente.operacoes)


def test_detalhe_confidencial_e_consulta_individual_sem_cache():
    registro = _mapa_atual()
    cliente = _SupabaseMapa(
        [registro],
        {"id", "aluno_id", "observacoes", "criado_por"},
    )
    with patch.object(database, "supabase", cliente):
        detalhe = database.buscar_detalhe_anamnese_dores("aluno-1", "registro-1")

    assert detalhe == {
        "id": "registro-1",
        "observacoes": "Conteúdo confidencial.",
        "criado_por": "operador-confidencial",
    }
    assert not hasattr(database.buscar_historico_dores_restrito, "clear")
    assert not hasattr(database.buscar_historico_dores, "clear")
    assert not hasattr(database.buscar_detalhe_anamnese_dores, "clear")
    assert not hasattr(database.bi_dados_individuais, "clear")


def test_exclusao_fisica_esta_indisponivel_na_interface_e_linguagem_e_nao_diagnostica():
    fonte = Path("views/anamnese_dores_view.py").read_text(encoding="utf-8")
    assert "excluir_anamnese_dores" not in fonte
    assert "Confirmar exclusão" not in fonte
    assert "Registro autorreferido — não constitui diagnóstico." in fonte
    assert mapa_view.LEGENDA_INTENSIDADE[1] == (
        "Amarelo: atenção leve / desconforto leve relatado."
    )
    assert mapa_view.LEGENDA_INTENSIDADE[2] == (
        "Laranja: atenção moderada / requer conversa, cautela ou adaptação."
    )
    assert mapa_view.LEGENDA_INTENSIDADE[3] == (
        "Vermelho: atenção elevada / relato intenso; requer prudência, "
        "pausa ou adaptação da atividade."
    )


def test_mapa_preserva_frente_costas_lateralidade_e_gravacao_usa_lista_de_regioes():
    assert mapa_view.REGIOES["f_ombro_e"]["view"] == "frente"
    assert mapa_view.REGIOES["c_lombar"]["view"] == "costas"
    assert mapa_view.REGIOES["f_ombro_e"]["label"].endswith("Esq.")
    assert mapa_view.REGIOES["f_ombro_d"]["label"].endswith("Dir.")
