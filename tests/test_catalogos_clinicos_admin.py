"""Testes da camada backend dos catálogos clínicos administrativos."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import re
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from utils import catalogos_clinicos_admin as admin


class _Resposta:
    def __init__(self, data):
        self.data = data


class _ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.filtros = {}
        self.payload = None
        self.faixa = None
        self.limite = None
        self.ordens = []
        self.cursor = None

    def select(self, *_args):
        self.acao = "select"
        return self

    def order(self, campo, desc=False, **_kwargs):
        self.ordens.append((campo, desc))
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def in_(self, campo, valores):
        self.filtros[campo] = tuple(valores)
        return self

    def limit(self, quantidade):
        self.limite = quantidade
        return self

    def range(self, inicio, fim):
        self.faixa = (inicio, fim)
        return self

    def or_(self, expressao):
        correspondencia = re.fullmatch(
            r"criado_em\.lt\.(.*),and\(criado_em\.eq\.(.*),id\.lt\.(.*)\)",
            expressao,
        )
        assert correspondencia
        criado_lt, criado_eq, id_lt = correspondencia.groups()
        assert criado_lt == criado_eq
        self.cursor = (criado_lt, id_lt)
        return self

    def insert(self, payload):
        self.acao = "insert"
        self.payload = deepcopy(payload)
        return self

    def update(self, payload):
        self.acao = "update"
        self.payload = deepcopy(payload)
        return self

    def execute(self):
        registros = self.banco.setdefault(self.tabela, [])
        if self.acao == "select":
            resultado = [
                deepcopy(item)
                for item in registros
                if all(
                    item.get(campo) in valor
                    if isinstance(valor, tuple)
                    else item.get(campo) == valor
                    for campo, valor in self.filtros.items()
                )
            ]
            for campo, desc in reversed(self.ordens):
                resultado.sort(
                    key=lambda item: str(item.get(campo) or ""),
                    reverse=desc,
                )
            if self.cursor:
                criado_em, item_id = self.cursor
                resultado = [
                    item
                    for item in resultado
                    if (
                        str(item.get("criado_em") or "") < criado_em
                        or (
                            str(item.get("criado_em") or "") == criado_em
                            and str(item.get("id") or "") < item_id
                        )
                    )
                ]
            if self.faixa:
                inicio, fim = self.faixa
                resultado = resultado[inicio : fim + 1]
            if self.limite is not None:
                resultado = resultado[: self.limite]
            return _Resposta(resultado)
        if self.acao == "insert":
            item = {"id": f"{self.tabela}-{len(registros) + 1}", **self.payload}
            registros.append(item)
            return _Resposta([deepcopy(item)])

        resultado = []
        for item in registros:
            if all(
                item.get(campo) in valor
                if isinstance(valor, tuple)
                else item.get(campo) == valor
                for campo, valor in self.filtros.items()
            ):
                item.update(self.payload)
                resultado.append(deepcopy(item))
        return _Resposta(resultado)


class _ClienteFalso:
    def __init__(self, banco=None):
        self.banco = banco if banco is not None else {}

    def table(self, tabela):
        return _ConsultaFalsa(self.banco, tabela)


@pytest.fixture
def sessao_autorizada(monkeypatch):
    streamlit_falso = SimpleNamespace(
        session_state={
            "usuario_logado": True,
            "perfil": "SuperAdmin",
            "usuario_email": admin.ADMIN_MASTER,
        },
        secrets={},
    )
    monkeypatch.setattr(admin, "st", streamlit_falso)
    return streamlit_falso


def test_bloqueia_usuario_sem_perfil_antes_de_criar_cliente(monkeypatch):
    monkeypatch.setattr(
        admin,
        "st",
        SimpleNamespace(
            session_state={"usuario_logado": True, "perfil": "Operador"},
            secrets={},
        ),
    )
    monkeypatch.setattr(
        admin,
        "_criar_cliente_administrativo",
        lambda *_args: pytest.fail("o cliente não deveria ser criado"),
    )

    with pytest.raises(admin.CatalogoClinicoAcessoNegado):
        admin._cliente_administrativo()


def test_secret_ausente_retorna_erro_sanitizado(
    sessao_autorizada, monkeypatch
):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(admin.CatalogoClinicoErro) as erro:
        admin._cliente_administrativo()

    mensagem = str(erro.value)
    assert "SUPABASE" not in mensagem
    assert "chave" not in mensagem.lower()
    assert "URL" not in mensagem


def test_usa_variaveis_de_ambiente_como_fallback_seguro(
    sessao_autorizada, monkeypatch
):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase-fallback.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-fallback")
    cliente = object()
    argumentos = []
    monkeypatch.setattr(
        admin,
        "_criar_cliente_administrativo",
        lambda url, key: argumentos.append((url, key)) or cliente,
    )

    assert admin._cliente_administrativo() is cliente
    assert argumentos == [
        ("https://supabase-fallback.invalid", "service-role-fallback")
    ]


def test_st_secrets_tem_precedencia_sobre_variaveis_de_ambiente(
    sessao_autorizada, monkeypatch
):
    sessao_autorizada.secrets = {
        "SUPABASE_URL": "https://supabase-secrets.invalid",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-secrets",
    }
    monkeypatch.setenv("SUPABASE_URL", "https://supabase-ambiente.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-ambiente")
    argumentos = []
    monkeypatch.setattr(
        admin,
        "_criar_cliente_administrativo",
        lambda url, key: argumentos.append((url, key)) or object(),
    )

    admin._cliente_administrativo()

    assert argumentos == [
        ("https://supabase-secrets.invalid", "service-role-secrets")
    ]


def test_falha_ao_inicializar_cliente_retorna_erro_sanitizado(
    sessao_autorizada, monkeypatch
):
    sessao_autorizada.secrets = {
        "SUPABASE_URL": "https://supabase-secrets.invalid",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-secrets",
    }

    def falhar_cliente(*_args):
        raise RuntimeError("token-interno-que-nao-pode-vazar")

    monkeypatch.setattr(admin, "_criar_cliente_administrativo", falhar_cliente)

    with pytest.raises(admin.CatalogoClinicoErro) as erro:
        admin._cliente_administrativo()

    assert "token-interno" not in str(erro.value)
    assert "serviço administrativo" in str(erro.value)


def test_diagnostico_informa_apenas_estados_seguros(
    sessao_autorizada, monkeypatch
):
    sessao_autorizada.secrets = {
        "SUPABASE_URL": "https://supabase-secrets.invalid",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-secrets",
    }
    monkeypatch.setattr(
        admin,
        "_criar_cliente_administrativo",
        lambda *_args: _ClienteFalso(),
    )

    diagnostico = admin.diagnosticar_backend_catalogos_clinicos()

    assert diagnostico["supabase_url_configurada"] is True
    assert diagnostico["service_role_configurada"] is True
    assert diagnostico["sessao_autenticada"] is True
    assert diagnostico["perfil_superadmin"] is True
    assert diagnostico["email_admin_master"] is True
    assert diagnostico["perfil_autorizado"] is True
    assert diagnostico["fonte_supabase_url"] == "st.secrets"
    assert diagnostico["fonte_service_role"] == "st.secrets"
    assert diagnostico["import_supabase_disponivel"] is True
    assert diagnostico["etapa_cliente_administrativo"] == "inicializado"
    assert diagnostico["cliente_administrativo_inicializado"] is True
    assert diagnostico["tabelas"] == {
        "catalogo_condicoes_clinicas": True,
        "catalogo_restricoes_movimento": True,
        "catalogo_adaptacoes": True,
        "historico_revisoes_clinicas": True,
    }
    assert "service-role-secrets" not in str(diagnostico)
    assert "supabase-secrets.invalid" not in str(diagnostico)


def test_normaliza_codigo_e_valida_intervalo():
    assert admin.normalizar_codigo("  Cardiopatia não especificada ") == (
        "CARDIOPATIA_NAO_ESPECIFICADA"
    )
    with pytest.raises(admin.CatalogoClinicoErro):
        admin._validar_payload(
            "condicoes",
            {
                "codigo": "TESTE",
                "nome_padrao": "Teste",
                "categoria": "OUTRA",
                "grupo": "Grupo",
                "exige_revisao_periodica": True,
                "intervalo_revisao_dias": 0,
            },
            incluir_codigo=True,
        )


def test_cria_item_e_audita_sem_tocar_tabelas_de_alunos(sessao_autorizada, monkeypatch):
    cliente = _ClienteFalso()
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    item = admin.criar_item_catalogo(
        "condicoes",
        {
            "codigo": "nova condição",
            "nome_padrao": "Nova condição",
            "categoria": "OUTRA",
            "grupo": "Teste",
            "descricao_operacional": "Descrição",
            "exige_revisao_periodica": False,
        },
    )

    assert item["codigo"] == "NOVA_CONDICAO"
    assert cliente.banco["catalogo_condicoes_clinicas"][0]["ativo"] is True
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["entidade"] == "CATALOGO_CONDICAO"
    assert auditoria["acao"] == "CRIACAO"
    assert auditoria["operador"] == admin.ADMIN_MASTER
    assert auditoria["valor_novo"]["_controle_auditoria_catalogo"]["status"] == (
        "CONCLUIDA"
    )
    assert all(not nome.startswith("aluno_") for nome in cliente.banco)


def test_edita_metadados_sem_alterar_codigo_e_audita(sessao_autorizada, monkeypatch):
    banco = {
        "catalogo_restricoes_movimento": [
            {
                "id": "restricao-1",
                "codigo": "EVITAR_IMPACTO",
                "nome_padrao": "Evitar impacto",
                "categoria_movimento": "Impacto",
                "exige_validacao_clinica": True,
                "ativo": True,
            }
        ]
    }
    cliente = _ClienteFalso(banco)
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    item = admin.atualizar_item_catalogo(
        "restricoes",
        "restricao-1",
        {
            "codigo": "CODIGO_NOVO_IGNORADO",
            "nome_padrao": "Evitar impacto alto",
            "categoria_movimento": "Impacto",
            "descricao_simples_para_aluno": "Use movimentos sem impacto.",
            "exige_validacao_clinica": True,
            "nivel_padrao_sugerido": "EVITAR",
        },
    )

    assert item["codigo"] == "EVITAR_IMPACTO"
    assert item["nome_padrao"] == "Evitar impacto alto"
    assert cliente.banco["historico_revisoes_clinicas"][0]["acao"] == "ATUALIZACAO"
    assert cliente.banco["historico_revisoes_clinicas"][0]["valor_anterior"]["codigo"] == (
        "EVITAR_IMPACTO"
    )


def test_inativa_item_sem_exclusao_fisica_e_audita(sessao_autorizada, monkeypatch):
    banco = {
        "catalogo_adaptacoes": [
            {
                "id": "adaptacao-1",
                "codigo": "EXERCICIO_SENTADO",
                "nome_padrao": "Exercício sentado",
                "ativo": True,
            }
        ]
    }
    cliente = _ClienteFalso(banco)
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    item = admin.alterar_ativo_item_catalogo("adaptacoes", "adaptacao-1", False)

    assert item["ativo"] is False
    assert len(cliente.banco["catalogo_adaptacoes"]) == 1
    assert cliente.banco["historico_revisoes_clinicas"][0]["acao"] == "INATIVACAO"


def test_falha_na_reserva_de_auditoria_impede_mutacao(sessao_autorizada, monkeypatch):
    class ConsultaComFalhaNaAuditoria(_ConsultaFalsa):
        def execute(self):
            if self.tabela == "historico_revisoes_clinicas" and self.acao == "insert":
                raise RuntimeError("falha de auditoria")
            return super().execute()

    class ClienteComFalhaNaAuditoria(_ClienteFalso):
        def table(self, tabela):
            return ConsultaComFalhaNaAuditoria(self.banco, tabela)

    cliente = ClienteComFalhaNaAuditoria()
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    with pytest.raises(admin.CatalogoClinicoErro):
        admin.criar_item_catalogo(
            "adaptacoes",
            {
                "codigo": "TESTE_AUDITORIA",
                "nome_padrao": "Teste de auditoria",
                "categoria_adaptacao": "Teste",
            },
        )

    assert cliente.banco.get("catalogo_adaptacoes", []) == []


def test_falha_ao_finalizar_mantem_reserva_pendente(
    sessao_autorizada, monkeypatch
):
    class ConsultaComFalhaNaFinalizacao(_ConsultaFalsa):
        def execute(self):
            if self.tabela == "historico_revisoes_clinicas" and self.acao == "update":
                raise RuntimeError("falha após mutação")
            return super().execute()

    class ClienteComFalhaNaFinalizacao(_ClienteFalso):
        def table(self, tabela):
            return ConsultaComFalhaNaFinalizacao(self.banco, tabela)

    cliente = ClienteComFalhaNaFinalizacao()
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    with pytest.raises(admin.CatalogoClinicoErro):
        admin.criar_item_catalogo(
            "adaptacoes",
            {
                "codigo": "TESTE_PENDENTE",
                "nome_padrao": "Teste pendente",
                "categoria_adaptacao": "Teste",
            },
        )

    assert len(cliente.banco["catalogo_adaptacoes"]) == 1
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_novo"]["_controle_auditoria_catalogo"]["status"] == (
        "PENDENTE"
    )

    cliente_sem_falha = _ClienteFalso(cliente.banco)
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente_sem_falha)
    resultado = admin.reconciliar_auditorias_pendentes()

    assert resultado == {"encontradas": 1, "reconciliadas": 1, "pendentes": 0}
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_novo"]["_controle_auditoria_catalogo"]["status"] == (
        "CONCLUIDA_RECONCILIADA"
    )


def test_reconcilia_pendencia_alem_da_primeira_pagina(
    sessao_autorizada, monkeypatch
):
    entidade = "CATALOGO_ADAPTACAO"
    inicio = datetime(2026, 1, 1, tzinfo=UTC)
    historicos = [
        {
            "id": f"historico-{indice}",
            "criado_em": (inicio + timedelta(seconds=indice)).isoformat(),
            "entidade": entidade,
            "registro_id": f"registro-{indice}",
            "acao": "ATUALIZACAO",
            "valor_anterior": {},
            "valor_novo": {
                "_controle_auditoria_catalogo": {"status": "CONCLUIDA"}
            },
        }
        for indice in range(1005)
    ]
    historicos[-1] = {
        "id": "historico-pendente-antigo",
        "criado_em": (inicio - timedelta(seconds=1)).isoformat(),
        "entidade": entidade,
        "registro_id": "adaptacao-antiga",
        "acao": "ATUALIZACAO",
        "valor_anterior": {"nome_padrao": "Nome anterior"},
        "valor_novo": {
            "id": "adaptacao-antiga",
            "codigo": "ADAPTACAO_ANTIGA",
            "nome_padrao": "Nome atual",
            "ativo": True,
            "_controle_auditoria_catalogo": {"status": "PENDENTE"},
        },
    }
    banco = {
        "historico_revisoes_clinicas": historicos,
        "catalogo_adaptacoes": [
            {
                "id": "adaptacao-antiga",
                "codigo": "ADAPTACAO_ANTIGA",
                "nome_padrao": "Nome atual",
                "ativo": True,
            }
        ],
    }
    cliente = _ClienteFalso(banco)
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    resultado = admin.reconciliar_auditorias_pendentes()

    assert resultado == {"encontradas": 1, "reconciliadas": 1, "pendentes": 0}
    pendente = next(
        item
        for item in banco["historico_revisoes_clinicas"]
        if item["id"] == "historico-pendente-antigo"
    )
    assert pendente["valor_novo"]["_controle_auditoria_catalogo"]["status"] == (
        "CONCLUIDA_RECONCILIADA"
    )


def test_historico_anterior_nao_comprova_pendencia_ambigua(
    sessao_autorizada, monkeypatch
):
    previsto = {
        "id": "adaptacao-ambigua",
        "codigo": "ADAPTACAO_AMBIGUA",
        "nome_padrao": "Nome pretendido",
        "ativo": True,
    }
    banco = {
        "historico_revisoes_clinicas": [
            {
                "id": "historico-antigo",
                "criado_em": "2026-01-01T10:00:00+00:00",
                "entidade": "CATALOGO_ADAPTACAO",
                "registro_id": "adaptacao-ambigua",
                "acao": "ATUALIZACAO",
                "valor_anterior": previsto,
                "valor_novo": {
                    "nome_padrao": "Outro nome",
                    "_controle_auditoria_catalogo": {"status": "CONCLUIDA"},
                },
            },
            {
                "id": "historico-pendente",
                "criado_em": "2026-01-02T10:00:00+00:00",
                "entidade": "CATALOGO_ADAPTACAO",
                "registro_id": "adaptacao-ambigua",
                "acao": "ATUALIZACAO",
                "valor_anterior": {"nome_padrao": "Anterior"},
                "valor_novo": {
                    **previsto,
                    "_controle_auditoria_catalogo": {"status": "PENDENTE"},
                },
            },
        ],
        "catalogo_adaptacoes": [
            {
                "id": "adaptacao-ambigua",
                "codigo": "ADAPTACAO_AMBIGUA",
                "nome_padrao": "Valor diferente",
                "ativo": True,
            }
        ],
    }
    cliente = _ClienteFalso(banco)
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    resultado = admin.reconciliar_auditorias_pendentes()

    assert resultado == {"encontradas": 1, "reconciliadas": 0, "pendentes": 1}
    pendente = banco["historico_revisoes_clinicas"][1]
    assert pendente["valor_novo"]["_controle_auditoria_catalogo"]["status"] == (
        "PENDENTE"
    )


def test_cursor_nao_pula_pendencia_quando_nova_auditoria_e_inserida(
    sessao_autorizada, monkeypatch
):
    inicio = datetime(2026, 1, 1, tzinfo=UTC)
    historicos = [
        {
            "id": f"historico-{indice:04d}",
            "criado_em": (inicio + timedelta(seconds=indice)).isoformat(),
            "entidade": "CATALOGO_ADAPTACAO",
            "registro_id": f"registro-{indice}",
            "acao": "ATUALIZACAO",
            "valor_anterior": {},
            "valor_novo": {
                "_controle_auditoria_catalogo": {"status": "CONCLUIDA"}
            },
        }
        for indice in range(1000)
    ]
    historicos.append(
        {
            "id": "historico-pendente-cursor",
            "criado_em": (inicio - timedelta(seconds=1)).isoformat(),
            "entidade": "CATALOGO_ADAPTACAO",
            "registro_id": "adaptacao-cursor",
            "acao": "ATUALIZACAO",
            "valor_anterior": {},
            "valor_novo": {
                "id": "adaptacao-cursor",
                "codigo": "ADAPTACAO_CURSOR",
                "nome_padrao": "Adaptação cursor",
                "ativo": True,
                "_controle_auditoria_catalogo": {"status": "PENDENTE"},
            },
        }
    )
    banco = {
        "historico_revisoes_clinicas": historicos,
        "catalogo_adaptacoes": [
            {
                "id": "adaptacao-cursor",
                "codigo": "ADAPTACAO_CURSOR",
                "nome_padrao": "Adaptação cursor",
                "ativo": True,
            }
        ],
    }

    class ClienteQueInjetaAuditoria(_ClienteFalso):
        def __init__(self, banco):
            super().__init__(banco)
            self.paginas_historico = 0

        def table(self, tabela):
            if tabela == "historico_revisoes_clinicas":
                self.paginas_historico += 1
                if self.paginas_historico == 2:
                    self.banco[tabela].append(
                        {
                            "id": "historico-novo-durante-paginacao",
                            "criado_em": (
                                inicio + timedelta(days=1)
                            ).isoformat(),
                            "entidade": "CATALOGO_ADAPTACAO",
                            "registro_id": "registro-novo",
                            "acao": "ATUALIZACAO",
                            "valor_anterior": {},
                            "valor_novo": {
                                "_controle_auditoria_catalogo": {
                                    "status": "CONCLUIDA"
                                }
                            },
                        }
                    )
            return super().table(tabela)

    cliente = ClienteQueInjetaAuditoria(banco)
    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: cliente)

    resultado = admin.reconciliar_auditorias_pendentes()

    assert resultado == {"encontradas": 1, "reconciliadas": 1, "pendentes": 0}


def test_erro_do_fornecedor_e_sanitizado(sessao_autorizada, monkeypatch):
    class ClienteComFalha:
        def table(self, _tabela):
            raise RuntimeError("https://supabase.exemplo/token-secreto")

    monkeypatch.setattr(admin, "_cliente_administrativo", lambda: ClienteComFalha())

    with pytest.raises(admin.CatalogoClinicoErro) as erro:
        admin.listar_itens_catalogo("condicoes")

    mensagem = str(erro.value)
    assert "supabase.exemplo" not in mensagem
    assert "token-secreto" not in mensagem


def test_view_autorizada_renderiza_tres_catalogos_sem_acesso_real():
    app = AppTest.from_string(
        """
import streamlit as st
from views import catalogos_clinicos_admin_view as view

st.session_state["usuario_logado"] = True
st.session_state["perfil"] = "SuperAdmin"
st.session_state["usuario_email"] = "admin@example.invalid"

view.validar_acesso_catalogos_clinicos = lambda: "admin@example.invalid"
view.reconciliar_auditorias_pendentes = lambda: {
    "encontradas": 0,
    "reconciliadas": 0,
    "pendentes": 0,
}
view.diagnosticar_backend_catalogos_clinicos = lambda: {
    "supabase_url_configurada": True,
    "service_role_configurada": True,
    "sessao_autenticada": True,
    "perfil_superadmin": True,
    "email_admin_master": True,
    "perfil_autorizado": True,
    "fonte_supabase_url": "os.environ",
    "fonte_service_role": "os.environ",
    "import_supabase_disponivel": True,
    "etapa_cliente_administrativo": "inicializado",
    "cliente_administrativo_inicializado": True,
    "tabelas": {
        "catalogo_condicoes_clinicas": True,
        "catalogo_restricoes_movimento": True,
        "catalogo_adaptacoes": True,
        "historico_revisoes_clinicas": True,
    },
}
view.listar_itens_catalogo = lambda tipo, busca="", status="Todos": []
view.tela_catalogos_clinicos_admin()
"""
    ).run(timeout=20)

    assert not app.exception
    assert [titulo.value for titulo in app.title] == [
        "Catálogos Clínicos e Segurança"
    ]
    assert [aba.label for aba in app.tabs] == [
        "Condições clínicas",
        "Restrições de movimento",
        "Adaptações recomendadas",
    ]
    assert app.expander[0].label == "Diagnóstico seguro do backend"
    assert [botao.label for botao in app.button] == [
        "Cadastrar condição clínica",
        "Cadastrar restrição de movimento",
        "Cadastrar adaptação recomendada",
    ]