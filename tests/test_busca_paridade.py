"""Paridade entre os dois caminhos de busca de alunos por nome em `database.py`.

Garante que `buscar_alunos_geral` retorne EXATAMENTE o mesmo conjunto de alunos
no caminho server-side (filtro por `nome_fonetica` via ILIKE no banco) e no
caminho de fallback (base baixada e filtrada em Python). Uma divergência futura
(ex.: mudança em `normalizar_fonetica` ou no escape de ILIKE) faria a busca
rápida "esconder" alunos sem ninguém perceber — este teste é a rede de segurança.

O cliente Supabase é totalmente substituído por um fake em memória, então o
teste roda de forma confiável mesmo sem banco e mesmo que a coluna persistida
`nome_fonetica` ainda não exista no Supabase de produção.

Execução (sem depender de pytest):
    .pythonlibs/bin/python3.11 tests/test_busca_paridade.py

Também funciona sob pytest, se instalado:
    pytest tests/test_busca_paridade.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
from utils.texto import normalizar_fonetica


# ─────────────────────────────────────────────────────────────────────────────
# Fake do cliente Supabase: implementa a semântica REAL de ILIKE do PostgreSQL
# (incluindo escape por barra invertida) para que o teste valide `_escape_like`.
# ─────────────────────────────────────────────────────────────────────────────
def _like_para_regex(padrao: str) -> "re.Pattern":
    """Traduz um padrão LIKE/ILIKE do PostgreSQL para regex ancorado.

    `%` casa qualquer sequência, `_` casa um caractere e `\\` escapa o próximo
    caractere (escape padrão do PostgreSQL). Tudo o mais é literal. ILIKE é
    case-insensitive."""
    saida = []
    i = 0
    while i < len(padrao):
        c = padrao[i]
        if c == "\\":
            i += 1
            saida.append(re.escape(padrao[i]) if i < len(padrao) else re.escape("\\"))
        elif c == "%":
            saida.append(".*")
        elif c == "_":
            saida.append(".")
        else:
            saida.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(saida) + "$", re.IGNORECASE | re.DOTALL)


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *a, **k):
        return self

    def neq(self, col, val):
        return _FakeQuery([r for r in self.rows if r.get(col) != val])

    def eq(self, col, val):
        return _FakeQuery([r for r in self.rows if r.get(col) == val])

    def is_(self, col, val):
        if val == "null":
            return _FakeQuery([r for r in self.rows if r.get(col) is None])
        return self

    def ilike(self, col, padrao):
        rx = _like_para_regex(padrao)
        return _FakeQuery([
            r for r in self.rows
            if r.get(col) is not None and rx.match(r.get(col))
        ])

    def order(self, col, **k):
        return _FakeQuery(sorted(self.rows, key=lambda r: (r.get(col) is None, r.get(col) or "")))

    def limit(self, n):
        return _FakeQuery(self.rows[:n])

    def range(self, inicio, fim):
        return _FakeQuery(self.rows[inicio:fim + 1])

    def execute(self):
        return _FakeResp(self.rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def from_(self, _tabela):
        return _FakeQuery(self.rows)


# ─────────────────────────────────────────────────────────────────────────────
# Dataset em memória. `nome_fonetica` é mantido em sincronia com `nome` (mesma
# invariante que `backfill_nome_fonetica` garante em produção).
# ─────────────────────────────────────────────────────────────────────────────
def _aluno(id_, nome, status="Ativo"):
    return {
        "id": id_,
        "nome": nome,
        "nome_fonetica": normalizar_fonetica(nome),
        "status": status,
    }


ALUNOS = [
    _aluno("1", "João Silva"),
    _aluno("2", "Joao Pereira"),          # sem acento
    _aluno("3", "Sofia Santos"),
    _aluno("4", "Sophia Almeida"),        # ph -> f  (== sofia)
    _aluno("5", "Maria Conceição"),
    _aluno("6", "Ana 50% Forte"),         # curinga literal %
    _aluno("7", "Ana 5012 Forte"),        # isca: casaria se % virasse curinga
    _aluno("8", "Carlos a_b Teste"),      # curinga literal _
    _aluno("9", "Carlos aXb Teste"),      # isca: casaria se _ virasse curinga
    _aluno("10", "Beatriz c\\d Lima"),    # curinga literal \
    _aluno("11", "Beatriz cXd Lima"),     # isca para a barra invertida
    _aluno("12", "Ricardo Inativo", status="Inativo"),
    _aluno("13", "Ricardo Ativo"),
]


# Termos de busca: acento, sem acento, caixa variada, fonético, substring,
# curingas de ILIKE e termo sem resultado.
TERMOS = [
    "",            # sem filtro -> base inteira
    "joão",
    "JOAO",
    "Joao",
    "sophia",      # fonético: deve casar "Sofia" e "Sophia"
    "sofia",
    "conceicao",   # sem acento/cedilha contra "Conceição"
    "silva",
    "ana",
    "for",         # substring
    "50%",         # curinga % deve ser literal
    "a_b",         # curinga _ deve ser literal
    "c\\d",        # curinga \ deve ser literal
    "ricardo",
    "zzz",         # sem resultado
]


def _ids(df):
    if df is None or df.empty or "id" not in df.columns:
        return set()
    return set(df["id"].tolist())


def _resultado(termo, incluir_inativos, server_side):
    """Roda `buscar_alunos_geral` forçando um dos dois caminhos."""
    db.supabase = _FakeSupabase(ALUNOS)
    db._coluna_fonetica_pronta = lambda *a, **k: server_side
    db.buscar_alunos_geral.clear()
    db._carregar_base_alunos.clear()
    return db.buscar_alunos_geral(termo, incluir_inativos=incluir_inativos)


# ─────────────────────────────────────────────────────────────────────────────
# Testes
# ─────────────────────────────────────────────────────────────────────────────
def test_paridade_server_side_vs_python():
    """Para cada termo e cada escopo, os dois caminhos devem trazer IDs idênticos."""
    for incluir_inativos in (False, True):
        for termo in TERMOS:
            ids_srv = _ids(_resultado(termo, incluir_inativos, server_side=True))
            ids_py = _ids(_resultado(termo, incluir_inativos, server_side=False))
            assert ids_srv == ids_py, (
                f"Divergência para termo={termo!r} incluir_inativos={incluir_inativos}: "
                f"server-side={sorted(ids_srv)} python={sorted(ids_py)}"
            )


def test_curingas_ilike_sao_literais():
    """`_escape_like` deve tornar %, _ e \\ literais: o alvo casa, a isca não."""
    casos = [
        ("50%", "6", "7"),     # "Ana 50% Forte" casa; "Ana 5012 Forte" não
        ("a_b", "8", "9"),     # "Carlos a_b Teste" casa; "Carlos aXb Teste" não
        ("c\\d", "10", "11"),  # "Beatriz c\\d Lima" casa; "Beatriz cXd Lima" não
    ]
    for termo, alvo_id, isca_id in casos:
        ids = _ids(_resultado(termo, incluir_inativos=False, server_side=True))
        assert alvo_id in ids, f"termo={termo!r} deveria casar o aluno {alvo_id}: {sorted(ids)}"
        assert isca_id not in ids, (
            f"termo={termo!r} não deveria casar a isca {isca_id} "
            f"(curinga tratado como literal falhou): {sorted(ids)}"
        )


def test_escape_like_unitario():
    """Confirma diretamente o escape dos três curingas."""
    assert db._escape_like("50%") == "50\\%"
    assert db._escape_like("a_b") == "a\\_b"
    assert db._escape_like("c\\d") == "c\\\\d"
    # Sem curingas, a string permanece intacta.
    assert db._escape_like("joao") == "joao"


def test_busca_fonetica_encontra_grafias_variadas():
    """Sanidade: a busca não está silenciosamente vazia e cobre fonética/acento."""
    ids = _ids(_resultado("sophia", incluir_inativos=False, server_side=True))
    assert ids == {"3", "4"}, f"esperado Sofia e Sophia: {sorted(ids)}"

    ids_acento = _ids(_resultado("joão", incluir_inativos=False, server_side=True))
    assert ids_acento == {"1", "2"}, f"esperado João e Joao: {sorted(ids_acento)}"


def test_escopo_inativos():
    """Inativos só aparecem quando incluir_inativos=True (nos dois caminhos)."""
    for server_side in (True, False):
        sem = _ids(_resultado("ricardo", incluir_inativos=False, server_side=server_side))
        com = _ids(_resultado("ricardo", incluir_inativos=True, server_side=server_side))
        assert "12" not in sem, f"inativo vazou (server_side={server_side}): {sorted(sem)}"
        assert "12" in com, f"inativo deveria aparecer (server_side={server_side}): {sorted(com)}"
        assert "13" in sem and "13" in com


def _main():
    testes = [
        test_paridade_server_side_vs_python,
        test_curingas_ilike_sao_literais,
        test_escape_like_unitario,
        test_busca_fonetica_encontra_grafias_variadas,
        test_escopo_inativos,
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
