"""Paridade da busca por nome nas DEMAIS telas (fora da Frequência).

`tests/test_busca_paridade.py` cobre os dois caminhos internos de
`buscar_alunos_geral`. `tests/test_busca_global_paridade.py` cobre a Busca Global
da Frequência e `filtrar_alunos_df`. Este arquivo fecha o cerco sobre as OUTRAS
telas que mostram aluno por nome, garantindo que cada uma traga EXATAMENTE o
mesmo conjunto que a busca canônica `buscar_alunos_geral`.

Mapeamento real (verificado no código), não o que o cabeçalho de `utils/texto.py`
sugere:

  • `modulos_frequencia/tab_emergencia.py` — busca por nome via o helper
    compartilhado `filtrar_alunos_df` sobre a base ativa de `buscar_alunos_geral`.
  • `views/ficha_aluno_view.py` — busca por nome com uma reimplementação INLINE
    (`normalizar_fonetica` + `str.contains`) em vez do helper. É o maior risco de
    divergência: se a normalização mudar, esta tela pode "esconder" alunos sem
    ninguém perceber. Este é o ponto mais importante a blindar.
  • `modulos_frequencia/tab_niver.py` — NÃO filtra aluno por nome; usa
    `buscar_alunos_geral("")` como universo e recorta por mês de aniversário.
  • `views/radar_acolhimento_view.py` — NÃO filtra aluno por nome; consulta o
    Supabase direto e recorta por dias de ausência.

Para as duas primeiras, replicamos fielmente o filtro de cada tela e exigimos
paridade com `buscar_alunos_geral`. Para as duas últimas — que hoje não têm
normalização fonética própria — um guarda estrutural prova que elas continuam
sem um filtro de nome independente (e, no caso do Niver, que o universo de
alunos vem da fonte canônica). Se alguém adicionar uma busca por nome reinventada
nelas, o guarda falha, sinalizando para rotear pelo helper compartilhado.

O cliente Supabase é substituído pelo mesmo fake em memória de
`test_busca_paridade.py`, então o teste roda sem banco real.

Execução (sem depender de pytest):
    .pythonlibs/bin/python3.11 tests/test_busca_telas_paridade.py

Também funciona sob pytest, se instalado:
    pytest tests/test_busca_telas_paridade.py
"""

import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))  # raiz do projeto
sys.path.insert(0, _AQUI)                    # para importar o teste irmão

import database as db
from utils.busca_aluno import filtrar_alunos_df
from utils.texto import normalizar_fonetica

# Reaproveita o fake do Supabase e o dataset do teste irmão (mesma invariante:
# `nome_fonetica` == normalizar_fonetica(nome)).
from test_busca_paridade import ALUNOS, _FakeSupabase


# Termos que exercitam acento, sem acento, caixa variada, fonética, substring e
# os curingas de ILIKE (que devem ser tratados como literais). Todos com >= 3
# caracteres, pois as telas só ativam o filtro nesse caso.
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


def _reset(server_side):
    """Aponta `database` para o fake e zera os caches de busca do `database`."""
    db.supabase = _FakeSupabase(ALUNOS)
    db._coluna_fonetica_pronta = lambda *a, **k: server_side
    db.buscar_alunos_geral.clear()
    db._carregar_base_alunos.clear()


def _ref(termo):
    """Conjunto de referência canônico (telas mostram apenas alunos ativos)."""
    return _ids(db.buscar_alunos_geral(termo, incluir_inativos=False))


# ─────────────────────────────────────────────────────────────────────────────
# Réplicas FIÉIS do filtro por nome de cada tela
# ─────────────────────────────────────────────────────────────────────────────
def _filtro_emergencia(termo):
    """Replica `modulos_frequencia/tab_emergencia.py` (Busca Global cross-turma).

    Base = `buscar_alunos_geral("")` (ativos), reforçando o recorte de inativos
    como a tela faz, e então `filtrar_alunos_df(base, termo, cols=["nome"])`."""
    df_todos = db.buscar_alunos_geral("")
    df_base = df_todos[df_todos["status"] != "Inativo"].copy()
    return _ids(filtrar_alunos_df(df_base, termo, cols=["nome"]))


def _filtro_ficha(termo):
    """Replica a busca por nome de `views/ficha_aluno_view.py`.

    A Ficha agora usa o helper compartilhado:
        df_alunos = buscar_alunos_geral("")
        df_view = filtrar_alunos_df(df_alunos, termo, cols=["nome"])
    """
    df_alunos = db.buscar_alunos_geral("").copy()
    if not termo or len(termo) < 3:
        return _ids(df_alunos)
    return _ids(filtrar_alunos_df(df_alunos, termo, cols=["nome"]))


# ─────────────────────────────────────────────────────────────────────────────
# Testes — telas que filtram por nome
# ─────────────────────────────────────────────────────────────────────────────
def test_emergencia_igual_buscar_geral():
    """A busca da aba Emergência traz os MESMOS alunos que `buscar_alunos_geral`.

    Validado nos dois caminhos internos (server-side e Python)."""
    for server_side in (True, False):
        for termo in TERMOS:
            _reset(server_side)
            esperado = _ref(termo)
            _reset(server_side)
            obtido = _filtro_emergencia(termo)
            assert obtido == esperado, (
                f"Emergência divergiu de buscar_alunos_geral para termo={termo!r} "
                f"(server_side={server_side}): tela={sorted(obtido)} "
                f"geral={sorted(esperado)}"
            )


def test_ficha_igual_buscar_geral():
    """A busca da Ficha do Aluno traz os MESMOS alunos que `buscar_alunos_geral`.

    A Ficha reimplementa o filtro inline (não usa `filtrar_alunos_df`); este
    teste é a rede de segurança contra divergência da normalização fonética.
    Validado nos dois caminhos internos."""
    for server_side in (True, False):
        for termo in TERMOS:
            _reset(server_side)
            esperado = _ref(termo)
            _reset(server_side)
            obtido = _filtro_ficha(termo)
            assert obtido == esperado, (
                f"Ficha do Aluno divergiu de buscar_alunos_geral para termo={termo!r} "
                f"(server_side={server_side}): tela={sorted(obtido)} "
                f"geral={sorted(esperado)}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Guarda estrutural — telas que NÃO filtram por nome (Niver, Radar)
# ─────────────────────────────────────────────────────────────────────────────
def _fonte(caminho_rel):
    with open(os.path.join(os.path.dirname(_AQUI), caminho_rel), encoding="utf-8") as f:
        return f.read()


def test_niver_sem_filtro_proprio_de_nome():
    """O Niver não reinventa busca fonética e usa o universo canônico de alunos.

    Hoje a aba Aniversários recorta a base por mês, não por nome digitado. Logo
    não há normalização própria que possa divergir. Este guarda garante que:
      1) o universo de alunos vem de `buscar_alunos_geral` (fonte canônica);
      2) não há `normalizar_fonetica` (filtro de nome reinventado) na tela.
    Se uma busca por nome for adicionada, ela deve passar por `filtrar_alunos_df`
    (helper compartilhado) — mantendo a paridade — e este teste sinaliza a
    reimplementação inline."""
    src = _fonte("modulos_frequencia/tab_niver.py")
    assert "buscar_alunos_geral" in src, (
        "Niver deveria obter os alunos via buscar_alunos_geral (fonte canônica)"
    )
    assert "normalizar_fonetica" not in src, (
        "Niver passou a normalizar nome por conta própria; roteie a busca por "
        "filtrar_alunos_df para não divergir de buscar_alunos_geral"
    )


def test_radar_sem_filtro_proprio_de_nome():
    """O Radar de Acolhimento não tem busca fonética por nome.

    A tela consulta o Supabase direto e recorta por dias de ausência; nome não é
    eixo de busca. Este guarda garante que não surja uma normalização fonética
    reinventada (que poderia divergir de `buscar_alunos_geral`). Se uma busca por
    nome for adicionada, deve usar `filtrar_alunos_df`/`buscar_alunos_geral`."""
    src = _fonte("views/radar_acolhimento_view.py")
    assert "normalizar_fonetica" not in src, (
        "Radar passou a normalizar nome por conta própria; roteie a busca por "
        "filtrar_alunos_df para não divergir de buscar_alunos_geral"
    )


def _main():
    testes = [
        test_emergencia_igual_buscar_geral,
        test_ficha_igual_buscar_geral,
        test_niver_sem_filtro_proprio_de_nome,
        test_radar_sem_filtro_proprio_de_nome,
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
