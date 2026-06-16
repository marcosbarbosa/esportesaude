# ==============================================================================
# 📄 utils/busca_aluno.py — Biblioteca Central de Busca de Alunos
# ⚙️ Expõe widget de busca (st_keyup / text_input), filtro de DataFrame
#    e widget com sugestões em tempo real (autocomplete).
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
    """Renderiza o campo de busca de aluno (st_keyup com fallback text_input)."""
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
    """Filtra um DataFrame de alunos pelo termo digitado com normalização fonética.

    Retorna o df original sem filtro se o termo for menor que min_len.
    """
    if not termo or len(termo.strip()) < min_len:
        return df
    t = normalizar_fonetica(termo.strip())
    mask = pd.Series(False, index=df.index)
    for col in cols:
        if col in df.columns:
            mask |= df[col].fillna("").apply(normalizar_fonetica).str.contains(t, na=False, regex=False)
    return df[mask]


def _rankear_sugestoes(df: pd.DataFrame, termo: str, col_nome: str = "nome") -> pd.DataFrame:
    """Ordena resultados do mais próximo ao mais distante do termo digitado.

    Score 0 = início do primeiro nome bate (ex: "ana" → "ANA PAULA")
    Score 1 = início de qualquer palavra bate (ex: "pau" → "ANA PAULA")
    Score 2 = contém em qualquer posição (match fonético geral)
    """
    t = normalizar_fonetica(termo.strip().lower())

    def _score(nome):
        n = normalizar_fonetica(str(nome).lower())
        palavras = n.split()
        if not palavras:
            return 2
        if palavras[0].startswith(t):
            return 0
        if any(p.startswith(t) for p in palavras):
            return 1
        return 2

    df = df.copy()
    df["_rank_busca"] = df[col_nome].apply(_score)
    return df.sort_values(["_rank_busca", col_nome], ascending=[True, True]).drop(columns=["_rank_busca"])


def busca_com_sugestoes(
    df: pd.DataFrame,
    key: str,
    *,
    max_sugestoes: int = 8,
    placeholder: str = "🔍 Digite pelo menos 3 letras do nome...",
    label: str = "Buscar aluno:",
    label_visibility: str = "collapsed",
    debounce: int = 250,
    col_nome: str = "nome",
    col_turma: str = "turma",
    abrir_callback=None,
) -> tuple[str, dict | None]:
    """Widget de busca com sugestões em tempo real.

    Parâmetros
    ----------
    df : DataFrame com col_nome e col_turma
    key : chave única Streamlit
    max_sugestoes : máx. de sugestões exibidas (padrão 8)
    abrir_callback : função(aluno_dict) chamada ao clicar uma sugestão;
                     se None, armazena em session_state['aluno_prontuario'] e faz st.rerun()

    Retorna
    -------
    (termo: str, aluno_selecionado: dict | None)
    """
    # ── Campo de entrada ──────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .sug-box {
        background: #fff;
        border: 1px solid #BFDBFE;
        border-radius: 10px;
        padding: 4px 6px;
        margin-top: 2px;
        box-shadow: 0 6px 20px rgba(0,86,179,.10);
    }
    [data-testid="stApp"][data-theme="dark"] .sug-box {
        background: #1E293B;
        border-color: #334155;
        box-shadow: 0 6px 20px rgba(0,0,0,.30);
    }
    .sug-box button {
        background: transparent !important;
        border: none !important;
        text-align: left !important;
        border-radius: 7px !important;
        padding: 7px 10px !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        color: #0F172A !important;
        width: 100% !important;
        transition: background .15s !important;
    }
    .sug-box button:hover {
        background: #EFF6FF !important;
        color: #1D4ED8 !important;
    }
    [data-testid="stApp"][data-theme="dark"] .sug-box button {
        color: #E2E8F0 !important;
    }
    [data-testid="stApp"][data-theme="dark"] .sug-box button:hover {
        background: #1E3A5F !important;
        color: #93C5FD !important;
    }
    .sug-label {
        font-size: 10.5px; font-weight: 700; color: #94A3B8;
        text-transform: uppercase; letter-spacing: .5px;
        padding: 4px 10px 2px;
    }
    </style>
    """, unsafe_allow_html=True)

    if _HAS_KEYUP:
        termo = _st_keyup(
            label,
            placeholder=placeholder,
            debounce=debounce,
            key=key,
            label_visibility=label_visibility,
        )
    else:
        termo = st.text_input(
            label,
            placeholder=placeholder,
            key=key,
            label_visibility=label_visibility,
        )

    termo = termo or ""
    termo_limpo = normalizar_fonetica(termo.strip())

    # ── Sugestões (≥ 3 caracteres) ────────────────────────────────────────────
    if len(termo_limpo) >= 3 and not df.empty:
        matches = filtrar_alunos_df(df, termo, cols=[col_nome, col_turma], min_len=3)
        if not matches.empty:
            matches = _rankear_sugestoes(matches, termo, col_nome=col_nome).head(max_sugestoes)

            st.markdown("<div class='sug-box'>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='sug-label'>🔎 {len(matches)} resultado(s) — clique para abrir</div>",
                unsafe_allow_html=True,
            )
            for _, row in matches.iterrows():
                nome_sug  = str(row.get(col_nome, ""))
                turma_sug = str(row.get(col_turma, "") or "—")
                btn_label = f"{nome_sug}  ·  {turma_sug}"
                if st.button(btn_label, key=f"sug_{key}_{row.get('id',nome_sug)}",
                             use_container_width=True):
                    aluno_dict = row.to_dict()
                    if abrir_callback:
                        abrir_callback(aluno_dict)
                    else:
                        st.session_state["aluno_prontuario"] = aluno_dict
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        elif len(termo_limpo) >= 3:
            st.caption(f"🔍 Nenhum aluno encontrado para **'{termo}'**")

    elif 0 < len(termo_limpo) < 3:
        st.caption("⏳ Continue digitando — a busca ativa a partir do 3º caractere.")

    return termo, None
