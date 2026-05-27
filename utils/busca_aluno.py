# ==============================================================================
# 📄 utils/busca_aluno.py — Biblioteca Central de Busca de Alunos
# ⚙️ Expõe widget de busca (st_keyup / text_input) e filtro de DataFrame
#    padronizados para uso em todos os módulos do sistema.
#    Uso em: main.py, frequencia_view, tab_emergencia, ficha_aluno_view, etc.
# ==============================================================================
import streamlit as st
import pandas as pd
from utils.texto import normalizar_fonetica

try:
    from st_keyup import st_keyup as _st_keyup
    _HAS_KEYUP = True
except ImportError:
    _HAS_KEYUP = False


def busca_aluno_widget(
    key: str,
    *,
    container=None,
    placeholder: str = "🔍 Digite pelo menos 3 letras...",
    label: str = "Buscar:",
    debounce: int = 300,
    label_visibility: str = "collapsed",
) -> str:
    """Renderiza o campo de busca de aluno (st_keyup com fallback text_input).

    Parâmetros
    ----------
    key : str
        Chave única Streamlit para o widget (obrigatório para evitar conflitos).
    container : coluna/container Streamlit | None
        Se fornecido, o widget é renderizado dentro desse container.
    placeholder : str  Texto exibido no campo vazio.
    label : str        Label do campo.
    debounce : int     Debounce em ms (apenas com st_keyup).
    label_visibility   "collapsed" | "visible" | "hidden"

    Retorna
    -------
    str : valor atual do campo (pode ser vazio "").
    """
    def _render():
        if _HAS_KEYUP:
            return _st_keyup(
                label,
                placeholder=placeholder,
                debounce=debounce,
                key=key,
                label_visibility=label_visibility,
            )
        return st.text_input(
            label,
            placeholder=placeholder,
            key=key,
            label_visibility=label_visibility,
        )

    if container is not None:
        with container:
            return _render()
    return _render()


def filtrar_alunos_df(
    df: pd.DataFrame,
    termo: str,
    cols: tuple | list = ("nome", "turma"),
    min_len: int = 3,
) -> pd.DataFrame:
    """Filtra um DataFrame de alunos pelo termo digitado.

    Usa normalização fonética para tolerar acentos e pequenos erros.
    Retorna o df original sem filtro se o termo for menor que min_len.

    Parâmetros
    ----------
    df : pd.DataFrame   DataFrame a filtrar.
    termo : str         Texto digitado pelo usuário.
    cols : tuple/list   Colunas a pesquisar (OR entre elas).
    min_len : int       Mínimo de caracteres para ativar o filtro (padrão 3).
    """
    if not termo or len(termo.strip()) < min_len:
        return df
    t = normalizar_fonetica(termo.strip())
    mask = pd.Series(False, index=df.index)
    for col in cols:
        if col in df.columns:
            mask |= df[col].fillna("").apply(normalizar_fonetica).str.contains(t, na=False)
    return df[mask]
