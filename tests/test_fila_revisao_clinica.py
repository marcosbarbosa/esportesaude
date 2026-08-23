"""Testes da fila administrativa de revisão clínica humana."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from utils import catalogos_clinicos_admin as admin_catalogos
from utils import fila_revisao_clinica as fila


class _Resposta:
    def __init__(self, data):
        self.data = data


class _ConsultaFalsa:
    def __init__(self, cliente, tabela):
        self.cliente = cliente
        self.banco = cliente.banco
        self.tabela = tabela
        self.acao = "select"
        self.filtros = {}
        self.payload = None
        self.ordens = []
        self.faixa = None
        self.limite = None
        self.colunas = "*"
        self.filtros_neq = {}
        self.filtros_contains = {}

    def select(self, *args):
        self.acao = "select"
        self.colunas = args[0] if args else "*"
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

    def neq(self, campo, valor):
        self.filtros_neq[campo] = valor
        return self

    def contains(self, campo, valor):
        self.filtros_contains[campo] = deepcopy(valor)
        return self

    def range(self, inicio, fim):
        self.faixa = (inicio, fim)
        return self

    def limit(self, limite):
        self.limite = limite
        return self

    def insert(self, payload):
        self.acao = "insert"
        self.payload = deepcopy(payload)
        return self

    def update(self, payload):
        self.acao = "update"
        self.payload = deepcopy(payload)
        return self

    def _corresponde(self, item):
        def contem(observado, esperado):
            if isinstance(esperado, dict):
                return isinstance(observado, dict) and all(
                    chave in observado and contem(observado[chave], valor)
                    for chave, valor in esperado.items()
                )
            return observado == esperado

        iguais = all(
            item.get(campo) in valor
            if isinstance(valor, tuple)
            else item.get(campo) == valor
            for campo, valor in self.filtros.items()
        )
        diferentes = all(
            item.get(campo) is not None and item.get(campo) != valor
            for campo, valor in self.filtros_neq.items()
        )
        contidos = all(
            contem(item.get(campo), valor)
            for campo, valor in self.filtros_contains.items()
        )
        return iguais and diferentes and contidos

    def execute(self):
        detalhe = (
            deepcopy(self.payload)
            if self.acao != "select"
            else {
                "colunas": self.colunas,
                "faixa": self.faixa,
                "filtros": deepcopy(self.filtros),
            }
        )
        self.cliente.operacoes.append((self.tabela, self.acao, detalhe))
        registros = self.banco.setdefault(self.tabela, [])
        if self.acao == "select":
            resultado = [deepcopy(item) for item in registros if self._corresponde(item)]
            for campo, desc in reversed(self.ordens):
                resultado.sort(
                    key=lambda item: str(item.get(campo) or ""), reverse=desc
                )
            if self.faixa:
                inicio, fim = self.faixa
                resultado = resultado[inicio : fim + 1]
            if self.limite is not None:
                resultado = resultado[: self.limite]
            return _Resposta(resultado)
        if self.acao == "insert":
            item = {
                "id": f"{self.tabela}-{len(registros) + 1}",
                "criado_em": "2026-08-23T10:00:00+00:00",
                "atualizado_em": "2026-08-23T10:00:00+00:00",
                **self.payload,
            }
            registros.append(item)
            return _Resposta([deepcopy(item)])

        atualizados = []
        for item in registros:
            if self._corresponde(item):
                item.update(self.payload)
                if self.tabela != "historico_revisoes_clinicas":
                    item["atualizado_em"] = "2026-08-23T10:01:00+00:00"
                atualizados.append(deepcopy(item))
        return _Resposta(atualizados)


class _ClienteFalso:
    def __init__(self, banco=None):
        self.banco = deepcopy(banco or {})
        self.operacoes = []

    def table(self, tabela):
        return _ConsultaFalsa(self, tabela)


@pytest.fixture
def cliente_autorizado(monkeypatch):
    cliente = _ClienteFalso()
    monkeypatch.setattr(
        fila, "validar_acesso_catalogos_clinicos", lambda: fila.ADMIN_MASTER
        if hasattr(fila, "ADMIN_MASTER")
        else admin_catalogos.ADMIN_MASTER
    )
    monkeypatch.setattr(fila, "_cliente_administrativo", lambda: cliente)
    return cliente


def _autorizar(monkeypatch, cliente):
    monkeypatch.setattr(
        fila,
        "validar_acesso_catalogos_clinicos",
        lambda: admin_catalogos.ADMIN_MASTER,
    )
    monkeypatch.setattr(fila, "_cliente_administrativo", lambda: cliente)


def _banco_condicao():
    return {
        "alunos": [
            {
                "id": "11111111-2222-3333-4444-555555555555",
                "nome": "Nome que não deve sair do serviço",
                "problemas_saude": "Texto legado sem classificação",
                "restricoes_fisicas": "",
                "tags_saude": "",
            }
        ],
        "catalogo_condicoes_clinicas": [
            {
                "id": "catalogo-1",
                "codigo": "ITEM_UM",
                "nome_padrao": "Item um",
                "ativo": True,
            },
            {
                "id": "catalogo-2",
                "codigo": "ITEM_DOIS",
                "nome_padrao": "Item dois",
                "ativo": True,
            },
        ],
    }


def test_bloqueia_acesso_antes_de_obter_cliente(monkeypatch):
    def negar():
        raise admin_catalogos.CatalogoClinicoAcessoNegado("Acesso restrito.")

    monkeypatch.setattr(fila, "validar_acesso_catalogos_clinicos", negar)
    monkeypatch.setattr(
        fila,
        "_cliente_administrativo",
        lambda: pytest.fail("service role não deveria ser obtida"),
    )
    with pytest.raises(admin_catalogos.CatalogoClinicoAcessoNegado):
        fila.listar_fontes_legadas()


def test_correcao_bloqueia_acesso_antes_de_obter_cliente(monkeypatch):
    def negar():
        raise admin_catalogos.CatalogoClinicoAcessoNegado("Acesso restrito.")

    monkeypatch.setattr(fila, "validar_acesso_catalogos_clinicos", negar)
    monkeypatch.setattr(
        fila,
        "_cliente_administrativo",
        lambda: pytest.fail("service role não deveria ser obtida"),
    )
    with pytest.raises(admin_catalogos.CatalogoClinicoAcessoNegado):
        fila.corrigir_item_fila(
            "condicao",
            "vinculo-1",
            "versao-1",
            "catalogo-1",
            "Correção humana.",
        )


def test_lista_legado_sem_nome_e_sem_escrita(monkeypatch):
    cliente = _ClienteFalso(_banco_condicao())
    _autorizar(monkeypatch, cliente)

    fontes = fila.listar_fontes_legadas()

    assert fontes == [
        {
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "referencia_protegida": "ALU-55555555",
            "tipo": "condicao",
            "origem": "REGISTRO_LEGADO",
            "campo_origem": "problemas_saude",
        }
    ]
    assert "nome" not in fontes[0]
    assert all(acao == "select" for _, acao, _ in cliente.operacoes)
    assert cliente.banco["alunos"][0]["problemas_saude"] == (
        "Texto legado sem classificação"
    )
    consultas_alunos = [
        detalhe for tabela, acao, detalhe in cliente.operacoes
        if tabela == "alunos" and acao == "select"
    ]
    assert len(consultas_alunos) == 3
    assert all(item["colunas"] == "id" for item in consultas_alunos)
    assert all(item["faixa"] == (0, 49) for item in consultas_alunos)


def test_texto_legado_so_e_lido_individualmente(monkeypatch):
    cliente = _ClienteFalso(_banco_condicao())
    _autorizar(monkeypatch, cliente)

    texto = fila.obter_texto_fonte_legada(
        "condicao", "11111111-2222-3333-4444-555555555555"
    )

    assert texto == "Texto legado sem classificação"
    consultas = [
        detalhe for tabela, acao, detalhe in cliente.operacoes
        if tabela == "alunos" and acao == "select"
    ]
    assert consultas == [
        {
            "colunas": "id,problemas_saude",
            "faixa": None,
            "filtros": {"id": "11111111-2222-3333-4444-555555555555"},
        }
    ]


def test_cria_candidato_com_escolha_humana_e_auditoria_previa(monkeypatch):
    cliente = _ClienteFalso(_banco_condicao())
    _autorizar(monkeypatch, cliente)

    criado = fila.criar_candidato_de_fonte_legada(
        "condicao",
        "11111111-2222-3333-4444-555555555555",
        "catalogo-2",
        "Seleção feita manualmente.",
    )

    assert criado["condicao_id"] == "catalogo-2"
    assert criado["status_revisao"] == "SUGERIDO_POR_MIGRACAO"
    assert criado["fonte_informacao"] == "REGISTRO_LEGADO"
    assert "Texto legado sem classificação" not in criado["observacao_contextual"]
    assert "ALU-55555555" in criado["observacao_contextual"]
    assert "problemas_saude" in criado["observacao_contextual"]
    assert cliente.banco["alunos"][0]["problemas_saude"] == (
        "Texto legado sem classificação"
    )
    operacoes_de_escrita = [
        (tabela, acao) for tabela, acao, _ in cliente.operacoes
        if acao in {"insert", "update"}
    ]
    assert operacoes_de_escrita[0] == (
        "historico_revisoes_clinicas",
        "insert",
    )
    assert operacoes_de_escrita[1] == (
        "aluno_condicoes_clinicas",
        "insert",
    )
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["acao"] == "REVISAO"
    assert auditoria["entidade"] == "ALUNO_CONDICAO"
    assert auditoria["operador"] == admin_catalogos.ADMIN_MASTER
    assert "Texto legado sem classificação" not in str(auditoria)
    assert auditoria["valor_novo"][
        "_controle_auditoria_fila_clinica"
    ]["status"] == "CONCLUIDA"
    resumo = fila.listar_itens_fila(tipo="condicao")
    assert resumo[0]["responsavel_revisao"] == admin_catalogos.ADMIN_MASTER
    assert resumo[0]["data_revisao"] == "2026-08-23T10:00:00+00:00"
    consultas_auditoria = [
        detalhe for tabela, acao, detalhe in cliente.operacoes
        if tabela == "historico_revisoes_clinicas" and acao == "select"
    ]
    assert consultas_auditoria[-1]["colunas"] == (
        "id,registro_id,operador,criado_em"
    )
    assert consultas_auditoria[-1]["faixa"] == (0, 999)


@pytest.mark.parametrize(
    (
        "tipo",
        "tabela_catalogo",
        "catalogo_id",
        "tabela_vinculo",
        "campo_catalogo",
        "campo_status",
        "status_inicial",
    ),
    (
        (
            "condicao",
            "catalogo_condicoes_clinicas",
            "condicao-ativa",
            "aluno_condicoes_clinicas",
            "condicao_id",
            "status_revisao",
            "SUGERIDO_POR_MIGRACAO",
        ),
        (
            "restricao",
            "catalogo_restricoes_movimento",
            "restricao-ativa",
            "aluno_restricoes_fisicas",
            "restricao_id",
            "status_revisao",
            "SUGERIDO_POR_MIGRACAO",
        ),
        (
            "adaptacao",
            "catalogo_adaptacoes",
            "adaptacao-ativa",
            "aluno_adaptacoes_recomendadas",
            "adaptacao_id",
            "status",
            "PENDENTE",
        ),
    ),
)
def test_cria_e_rejeita_os_tres_tipos_da_fila(
    monkeypatch,
    tipo,
    tabela_catalogo,
    catalogo_id,
    tabela_vinculo,
    campo_catalogo,
    campo_status,
    status_inicial,
):
    aluno_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    banco = {
        "alunos": [
            {
                "id": aluno_id,
                "problemas_saude": "Condição legada",
                "restricoes_fisicas": "Restrição legada",
                "tags_saude": "Adaptação legada",
            }
        ],
        tabela_catalogo: [
            {
                "id": catalogo_id,
                "codigo": "ESCOLHA_HUMANA",
                "nome_padrao": "Escolha humana",
                "ativo": True,
            }
        ],
    }
    cliente = _ClienteFalso(banco)
    _autorizar(monkeypatch, cliente)

    criado = fila.criar_candidato_de_fonte_legada(
        tipo, aluno_id, catalogo_id, "Criado por escolha humana."
    )
    assert criado[campo_catalogo] == catalogo_id
    assert criado[campo_status] == status_inicial

    rejeitado = fila.revisar_item_fila(
        tipo,
        criado["id"],
        criado["atualizado_em"],
        "REJEITADO",
        "Rejeitado após revisão humana.",
    )
    assert rejeitado[campo_status] == "REJEITADO"
    assert cliente.banco[tabela_vinculo][0][campo_status] == "REJEITADO"
    assert cliente.banco["historico_revisoes_clinicas"][-1]["acao"] == "REVISAO"


def test_nao_cria_sem_item_ativo_escolhido(monkeypatch):
    cliente = _ClienteFalso(_banco_condicao())
    _autorizar(monkeypatch, cliente)

    with pytest.raises(fila.FilaRevisaoClinicaErro):
        fila.criar_candidato_de_fonte_legada(
            "condicao",
            "11111111-2222-3333-4444-555555555555",
            "catalogo-inexistente",
        )

    assert cliente.banco.get("aluno_condicoes_clinicas", []) == []
    assert cliente.banco.get("historico_revisoes_clinicas", []) == []


def test_falha_na_reserva_de_auditoria_impede_candidato(monkeypatch):
    class ConsultaFalhaAuditoria(_ConsultaFalsa):
        def execute(self):
            if self.tabela == "historico_revisoes_clinicas" and self.acao == "insert":
                raise RuntimeError("detalhe interno sensível")
            return super().execute()

    class ClienteFalhaAuditoria(_ClienteFalso):
        def table(self, tabela):
            return ConsultaFalhaAuditoria(self, tabela)

    cliente = ClienteFalhaAuditoria(_banco_condicao())
    _autorizar(monkeypatch, cliente)
    with pytest.raises(fila.FilaRevisaoClinicaErro) as erro:
        fila.criar_candidato_de_fonte_legada(
            "condicao",
            "11111111-2222-3333-4444-555555555555",
            "catalogo-1",
        )

    assert "detalhe interno" not in str(erro.value)
    assert cliente.banco.get("aluno_condicoes_clinicas", []) == []


def test_falha_apos_insercao_mantem_auditoria_pendente_e_reconcilia(monkeypatch):
    class ConsultaFalhaFinalizacao(_ConsultaFalsa):
        def execute(self):
            if self.tabela == "historico_revisoes_clinicas" and self.acao == "update":
                raise RuntimeError("falha incerta após mutação")
            return super().execute()

    class ClienteFalhaFinalizacao(_ClienteFalso):
        def table(self, tabela):
            return ConsultaFalhaFinalizacao(self, tabela)

    cliente = ClienteFalhaFinalizacao(_banco_condicao())
    _autorizar(monkeypatch, cliente)

    with pytest.raises(fila.FilaRevisaoClinicaErro) as erro:
        fila.criar_candidato_de_fonte_legada(
            "condicao",
            "11111111-2222-3333-4444-555555555555",
            "catalogo-1",
            "Escolha humana.",
        )

    assert "auditoria pendente" in str(erro.value).lower()
    assert len(cliente.banco["aluno_condicoes_clinicas"]) == 1
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_novo"][
        "_controle_auditoria_fila_clinica"
    ]["status"] == "PENDENTE"

    cliente_recuperado = _ClienteFalso(cliente.banco)
    _autorizar(monkeypatch, cliente_recuperado)
    resultado = fila.reconciliar_auditorias_fila_pendentes()

    assert resultado == {"encontradas": 1, "reconciliadas": 1, "pendentes": 0}
    auditoria = cliente_recuperado.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_novo"][
        "_controle_auditoria_fila_clinica"
    ]["status"] == "CONCLUIDA_RECONCILIADA"


def test_resultado_incerto_da_insercao_nao_declara_falha_sem_mutacao(monkeypatch):
    class ConsultaFalhaInsercao(_ConsultaFalsa):
        def execute(self):
            if self.tabela == "aluno_condicoes_clinicas" and self.acao == "insert":
                raise RuntimeError("resposta perdida após envio")
            return super().execute()

    class ClienteFalhaInsercao(_ClienteFalso):
        def table(self, tabela):
            return ConsultaFalhaInsercao(self, tabela)

    cliente = ClienteFalhaInsercao(_banco_condicao())
    _autorizar(monkeypatch, cliente)

    with pytest.raises(fila.FilaRevisaoClinicaErro) as erro:
        fila.criar_candidato_de_fonte_legada(
            "condicao",
            "11111111-2222-3333-4444-555555555555",
            "catalogo-1",
            "Escolha humana.",
        )

    assert "incerto" in str(erro.value).lower()
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_novo"][
        "_controle_auditoria_fila_clinica"
    ]["status"] == "PENDENTE"
    assert "FALHA_SEM_MUTACAO" not in str(auditoria)


def test_valida_com_cas_responsavel_observacao_e_auditoria(monkeypatch):
    banco = _banco_condicao()
    banco["aluno_condicoes_clinicas"] = [
        {
            "id": "vinculo-1",
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "condicao_id": "catalogo-1",
            "status_revisao": "PENDENTE",
            "fonte_informacao": "REGISTRO_LEGADO",
            "observacao_contextual": "Contexto preservado",
            "ativo": True,
            "atualizado_em": "2026-08-23T09:00:00+00:00",
        }
    ]
    cliente = _ClienteFalso(banco)
    _autorizar(monkeypatch, cliente)

    revisado = fila.revisar_item_fila(
        "condicao",
        "vinculo-1",
        "2026-08-23T09:00:00+00:00",
        "VALIDADO",
        "Validado após conferência humana.",
    )

    assert revisado["status_revisao"] == "VALIDADO"
    assert revisado["responsavel_validacao"] == admin_catalogos.ADMIN_MASTER
    assert "Validado após conferência humana." in revisado["observacao_contextual"]
    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_anterior"]["status_revisao"] == "PENDENTE"
    assert auditoria["valor_novo"]["status_revisao"] == "VALIDADO"
    assert auditoria["acao"] == "REVISAO"


def test_corrige_selecao_e_mantem_pendente(monkeypatch):
    banco = _banco_condicao()
    banco["aluno_condicoes_clinicas"] = [
        {
            "id": "vinculo-1",
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "condicao_id": "catalogo-1",
            "status_revisao": "SUGERIDO_POR_MIGRACAO",
            "observacao_contextual": "Contexto",
            "ativo": True,
            "atualizado_em": "2026-08-23T09:00:00+00:00",
        }
    ]
    cliente = _ClienteFalso(banco)
    _autorizar(monkeypatch, cliente)

    corrigido = fila.corrigir_item_fila(
        "condicao",
        "vinculo-1",
        "2026-08-23T09:00:00+00:00",
        "catalogo-2",
        "Correção humana da associação.",
    )

    assert corrigido["condicao_id"] == "catalogo-2"
    assert corrigido["status_revisao"] == "PENDENTE"
    assert "Correção humana" in corrigido["observacao_contextual"]
    resumo = fila.listar_itens_fila(tipo="condicao")
    assert resumo[0]["responsavel_revisao"] == admin_catalogos.ADMIN_MASTER
    assert resumo[0]["data_revisao"] == "2026-08-23T10:00:00+00:00"


def test_conflito_de_versao_nao_sobrescreve_item(monkeypatch):
    banco = _banco_condicao()
    banco["aluno_condicoes_clinicas"] = [
        {
            "id": "vinculo-1",
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "condicao_id": "catalogo-1",
            "status_revisao": "PENDENTE",
            "ativo": True,
            "atualizado_em": "versao-mais-recente",
        }
    ]
    cliente = _ClienteFalso(banco)
    _autorizar(monkeypatch, cliente)

    with pytest.raises(fila.FilaRevisaoClinicaErro) as erro:
        fila.revisar_item_fila(
            "condicao",
            "vinculo-1",
            "versao-antiga",
            "REJEITADO",
            "Rejeição humana.",
        )

    assert "outra sessão" in str(erro.value)
    assert cliente.banco["aluno_condicoes_clinicas"][0]["status_revisao"] == "PENDENTE"


@pytest.mark.parametrize("resultado_update", ("vazio", "excecao"))
def test_update_incerto_mantem_reserva_pendente(monkeypatch, resultado_update):
    class ConsultaUpdateIncerto(_ConsultaFalsa):
        def execute(self):
            if self.tabela == "aluno_condicoes_clinicas" and self.acao == "update":
                if resultado_update == "excecao":
                    raise RuntimeError("resposta de atualização perdida")
                return _Resposta([])
            return super().execute()

    class ClienteUpdateIncerto(_ClienteFalso):
        def table(self, tabela):
            return ConsultaUpdateIncerto(self, tabela)

    banco = _banco_condicao()
    banco["aluno_condicoes_clinicas"] = [
        {
            "id": "vinculo-incerto",
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "condicao_id": "catalogo-1",
            "status_revisao": "PENDENTE",
            "fonte_informacao": "REGISTRO_LEGADO",
            "observacao_contextual": "Contexto",
            "ativo": True,
            "atualizado_em": "versao-atual",
        }
    ]
    cliente = ClienteUpdateIncerto(banco)
    _autorizar(monkeypatch, cliente)

    with pytest.raises(fila.FilaRevisaoClinicaErro):
        fila.revisar_item_fila(
            "condicao",
            "vinculo-incerto",
            "versao-atual",
            "VALIDADO",
            "Validação humana com resposta incerta.",
        )

    auditoria = cliente.banco["historico_revisoes_clinicas"][0]
    assert auditoria["valor_novo"][
        "_controle_auditoria_fila_clinica"
    ]["status"] == "PENDENTE"
    assert "CANCELADA_POR_CONFLITO" not in str(auditoria)
    assert cliente.banco["aluno_condicoes_clinicas"][0]["status_revisao"] == "PENDENTE"

    cliente_recuperado = _ClienteFalso(cliente.banco)
    _autorizar(monkeypatch, cliente_recuperado)
    resultado = fila.reconciliar_auditorias_fila_pendentes()
    assert resultado == {"encontradas": 1, "reconciliadas": 0, "pendentes": 1}


def test_item_pendente_com_catalogo_inativo_continua_rejeitavel(monkeypatch):
    banco = _banco_condicao()
    banco["catalogo_condicoes_clinicas"][0]["ativo"] = False
    banco["aluno_condicoes_clinicas"] = [
        {
            "id": "vinculo-inativo",
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "condicao_id": "catalogo-1",
            "status_revisao": "PENDENTE",
            "fonte_informacao": "REGISTRO_LEGADO",
            "observacao_contextual": "Contexto",
            "ativo": True,
            "criado_em": "2026-08-23T09:00:00+00:00",
            "atualizado_em": "2026-08-23T09:00:00+00:00",
        }
    ]
    cliente = _ClienteFalso(banco)
    _autorizar(monkeypatch, cliente)

    detalhe = fila.obter_detalhe_item_fila("condicao", "vinculo-inativo")
    assert detalhe["sugestao"].endswith("(inativo)")

    rejeitado = fila.revisar_item_fila(
        "condicao",
        "vinculo-inativo",
        detalhe["atualizado_em"],
        "REJEITADO",
        "Catálogo arquivado; sugestão rejeitada.",
    )
    assert rejeitado["status_revisao"] == "REJEITADO"


def test_lista_fila_sem_nome_do_aluno(monkeypatch):
    banco = _banco_condicao()
    banco["aluno_condicoes_clinicas"] = [
        {
            "id": "vinculo-1",
            "aluno_id": "11111111-2222-3333-4444-555555555555",
            "condicao_id": "catalogo-1",
            "status_revisao": "PENDENTE",
            "fonte_informacao": "REGISTRO_LEGADO",
            "observacao_contextual": "Contexto",
            "ativo": True,
            "criado_em": "2026-08-23T09:00:00+00:00",
            "atualizado_em": "2026-08-23T09:00:00+00:00",
        }
    ]
    cliente = _ClienteFalso(banco)
    _autorizar(monkeypatch, cliente)

    itens = fila.listar_itens_fila(tipo="condicao")

    assert len(itens) == 1
    assert itens[0]["referencia_protegida"] == "ALU-55555555"
    assert "nome" not in itens[0]
    assert "observacao" not in itens[0]
    assert itens[0]["status"] == "PENDENTE"
    consulta_fila = next(
        detalhe for tabela, acao, detalhe in cliente.operacoes
        if tabela == "aluno_condicoes_clinicas" and acao == "select"
    )
    assert consulta_fila["colunas"] != "*"
    assert "observacao" not in consulta_fila["colunas"]
    assert consulta_fila["faixa"] == (0, 24)


def test_view_renderiza_barreira_de_acesso(monkeypatch):
    def negar():
        raise admin_catalogos.CatalogoClinicoAcessoNegado("Área restrita.")

    monkeypatch.setattr(admin_catalogos, "validar_acesso_catalogos_clinicos", negar)
    teste = AppTest.from_string(
        """
from views.fila_revisao_clinica_view import tela_fila_revisao_clinica
tela_fila_revisao_clinica()
"""
    )
    teste.run(timeout=10)

    assert not teste.exception
    assert any("Área restrita" in aviso.value for aviso in teste.warning)