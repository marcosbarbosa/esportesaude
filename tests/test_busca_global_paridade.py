"""Paridade de TODOS os caminhos de busca de aluno por nome.

`tests/test_busca_paridade.py` já garante que os dois caminhos INTERNOS de
`buscar_alunos_geral` (server-side vs. Python) tragam os mesmos alunos. Este
teste fecha o cerco sobre os OUTROS pontos que buscam aluno por nome com a
mesma normalização fonética por conta própria:

  • `utils.busca_aluno.filtrar_alunos_df` — filtro de DataFrame usado em vários
    módulos (frequência, emergência, ficha, etc.).
  • A "Busca Global" da Frequência (`views.frequencia_view`), que baixa a base
    via caches LOCAIS próprios (`obter_todos_alunos_com_inativos_cache`) e depois
    aplica `filtrar_alunos_df`.

Se `normalizar_fonetica` (ou o filtro) mudar e algum desses caminhos divergir,
alunos somem da tela sem ninguém perceber. Estes testes são a rede de segurança.

O último teste cobre o ponto cego conhecido: os caches LOCAIS da Busca Global
NÃO são limpos por `database._inv_alunos()`. Depois de uma mutação de aluno eles
ficam desatualizados e "escondem" o aluno até que `_limpar_cache_busca_global()`
seja chamado — exatamente o que a Frequência faz após transferir/reativar.

O cliente Supabase é totalmente substituído pelo mesmo fake em memória de
`test_busca_paridade.py`, então o teste roda sem banco real.

Execução (sem depender de pytest):
    .pythonlibs/bin/python3.11 tests/test_busca_global_paridade.py

Também funciona sob pytest, se instalado:
    pytest tests/test_busca_global_paridade.py
"""

import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))  # raiz do projeto
sys.path.insert(0, _AQUI)                    # para importar o teste irmão

import database as db
import views.frequencia_view as fv
from utils.busca_aluno import filtrar_alunos_df
from utils.texto import normalizar_fonetica

# Reaproveita o fake do Supabase e o dataset do teste irmão (mesma invariante:
# `nome_fonetica` == normalizar_fonetica(nome)).
from test_busca_paridade import ALUNOS, _FakeSupabase


# Termos com comprimento fonético >= 3 (a Busca Global só ativa nesse caso) e
# que exercitam acento, sem acento, caixa variada, fonética, substring e os
# curingas de ILIKE (que devem ser tratados como literais).
TERMOS = [
    "joão",
    "JOAO",
    "Joao",
    "sophia",     # fonético: casa "Sofia" e "Sophia"
    "sofia",
    "conceicao",  # sem acento/cedilha contra "Conceição"
    "silva",
    "ana",
    "for",        # substring
    "50%",        # curinga % literal
    "a_b",        # curinga _ literal
    "c\\d",       # curinga \ literal
    "ricardo",
    "zzz",        # sem resultado
]


def _ids(df):
    if df is None or df.empty or "id" not in df.columns:
        return set()
    return set(df["id"].tolist())


def _reset(rows, server_side):
    """Aponta `database` para o fake e zera TODOS os caches (db + frequência)."""
    db.supabase = _FakeSupabase(rows)
    db._coluna_fonetica_pronta = lambda *a, **k: server_side
    db.buscar_alunos_geral.clear()
    db._carregar_base_alunos.clear()
    fv.obter_todos_alunos_cache.clear()
    fv.obter_todos_alunos_com_inativos_cache.clear()


def _ref(termo, incluir_inativos):
    """Conjunto de referência: a busca canônica `buscar_alunos_geral`."""
    return _ids(db.buscar_alunos_geral(termo, incluir_inativos=incluir_inativos))


def _busca_global(termo):
    """Replica fielmente a Busca Global da Frequência (sempre com inativos)."""
    base = fv.obter_todos_alunos_com_inativos_cache()
    return _ids(filtrar_alunos_df(base, termo, cols=["nome"], min_len=3))


def _filtrar_direto(termo, incluir_inativos):
    """`filtrar_alunos_df` aplicado sobre a base completa de `buscar_alunos_geral`."""
    base = db.buscar_alunos_geral("", incluir_inativos=incluir_inativos)
    return _ids(filtrar_alunos_df(base, termo, cols=["nome"], min_len=3))


# ─────────────────────────────────────────────────────────────────────────────
# Testes
# ─────────────────────────────────────────────────────────────────────────────
def test_busca_global_igual_buscar_geral():
    """A Busca Global da Frequência traz os MESMOS alunos que `buscar_alunos_geral`.

    A Busca Global sempre opera sobre a base com inativos, então a referência é
    `buscar_alunos_geral(termo, incluir_inativos=True)`. Validado nos dois
    caminhos internos (server-side e Python)."""
    for server_side in (True, False):
        for termo in TERMOS:
            _reset(ALUNOS, server_side)
            esperado = _ref(termo, incluir_inativos=True)
            _reset(ALUNOS, server_side)
            obtido = _busca_global(termo)
            assert obtido == esperado, (
                f"Busca Global divergiu de buscar_alunos_geral para termo={termo!r} "
                f"(server_side={server_side}): global={sorted(obtido)} "
                f"geral={sorted(esperado)}"
            )


def test_filtrar_alunos_df_igual_buscar_geral():
    """`filtrar_alunos_df` traz os MESMOS alunos que `buscar_alunos_geral`.

    Cobre os dois escopos (só ativos e com inativos) e os dois caminhos internos."""
    for server_side in (True, False):
        for incluir_inativos in (False, True):
            for termo in TERMOS:
                _reset(ALUNOS, server_side)
                esperado = _ref(termo, incluir_inativos)
                _reset(ALUNOS, server_side)
                obtido = _filtrar_direto(termo, incluir_inativos)
                assert obtido == esperado, (
                    f"filtrar_alunos_df divergiu de buscar_alunos_geral para "
                    f"termo={termo!r} incluir_inativos={incluir_inativos} "
                    f"(server_side={server_side}): filtrar={sorted(obtido)} "
                    f"geral={sorted(esperado)}"
                )


def test_busca_global_cache_local_fica_stale_ate_limpar():
    """Ponto cego: o cache LOCAL da Busca Global esconde alunos até o clear próprio.

    `database._inv_alunos()` (chamado após mutações de aluno) NÃO limpa os caches
    de `frequencia_view`. Sem `_limpar_cache_busca_global()`, um aluno recém
    inserido/reativado fica invisível na Busca Global, mesmo já aparecendo em
    `buscar_alunos_geral`. Este teste prova a divergência e que o clear dedicado
    a corrige (regressão se alguém remover a chamada)."""
    rows = [dict(r) for r in ALUNOS]  # cópia mutável
    _reset(rows, server_side=False)

    termo = "zelia"  # nome ainda inexistente na base

    # 1) Aquece o cache local da Busca Global (aluno ainda não existe).
    assert _busca_global(termo) == set()

    # 2) Mutação no "banco": novo aluno entra na base do fake.
    rows.append({
        "id": "99",
        "nome": "Zélia Nova",
        "nome_fonetica": normalizar_fonetica("Zélia Nova"),
        "status": "Ativo",
    })

    # 3) Invalidação no estilo de produção: apenas os caches do `database`.
    db._inv_alunos()

    # A busca canônica JÁ enxerga o novo aluno...
    ref = _ref(termo, incluir_inativos=True)
    assert ref == {"99"}, f"buscar_alunos_geral deveria achar o novo aluno: {sorted(ref)}"

    # ...mas a Busca Global continua com o cache LOCAL desatualizado (escondendo-o).
    assert _busca_global(termo) == set(), (
        "esperava cache local da Busca Global desatualizado escondendo o aluno; "
        "se isto falhar, a relação entre os caches mudou e o teste precisa revisão"
    )

    # 4) O clear dedicado da Frequência restaura a paridade.
    fv._limpar_cache_busca_global()
    assert _busca_global(termo) == ref == {"99"}, (
        "_limpar_cache_busca_global() deveria realinhar a Busca Global com "
        "buscar_alunos_geral"
    )


def _main():
    testes = [
        test_busca_global_igual_buscar_geral,
        test_filtrar_alunos_df_igual_buscar_geral,
        test_busca_global_cache_local_fica_stale_ate_limpar,
    ]
    falhas = 0
    for t in testes:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"FAIL  {t.__name__}\n      {e}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(_main())
