# ==============================================================================
# Arquivo: views/utils_docs.py
# Função:  Utilitários compartilhados para exibição de documentos com rotação.
#          Importado por prontuario_ficha, prontuario_view e triagem_view.
# ==============================================================================
import io
import requests
import streamlit as st
from PIL import Image
from urllib.parse import urlparse

_EXTS_IMAGEM = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}


def url_eh_imagem(url: str) -> bool:
    """Detecta imagem pela extensão do path, ignorando query-strings (?token=...)."""
    if not url or not isinstance(url, str):
        return False
    path = urlparse(url.strip()).path.lower()
    return any(path.endswith(ext) for ext in _EXTS_IMAGEM)


def renderizar_documento_com_rotacao(url_documento: str, chave_unica: str):
    """
    Exibe um documento armazenado em URL:
    - PDF / tipo desconhecido → link clicável para visualização.
    - Imagem (jpg, png…)     → visualização com botões ↺ ↻ de rotação interativa.

    O estado de rotação é isolado por chave_unica no st.session_state,
    permitindo múltiplos documentos na mesma página sem interferência.
    """
    if not url_documento or not isinstance(url_documento, str):
        return

    url_limpa = url_documento.strip()

    if not url_eh_imagem(url_limpa):
        st.markdown(
            f"📄 **[Clique aqui para visualizar o documento original]({url_limpa})**"
        )
        return

    chave_ang = f"rotacao_doc_{chave_unica}"
    if chave_ang not in st.session_state:
        st.session_state[chave_ang] = 0

    try:
        resposta = requests.get(url_limpa, timeout=10)
        resposta.raise_for_status()
        imagem = Image.open(io.BytesIO(resposta.content))

        angulo = st.session_state[chave_ang] % 360
        if angulo != 0:
            imagem = imagem.rotate(angulo, expand=True)

        st.image(imagem, use_container_width=True)
        st.link_button("Ver Original ↗", url_limpa, use_container_width=True)

        c_esq, c_dir = st.columns(2)
        if c_esq.button(
            "↺ Esquerda", key=f"rot_esq_{chave_unica}", use_container_width=True
        ):
            st.session_state[chave_ang] = (st.session_state[chave_ang] + 90) % 360
            st.rerun()
        if c_dir.button(
            "↻ Direita", key=f"rot_dir_{chave_unica}", use_container_width=True
        ):
            st.session_state[chave_ang] = (st.session_state[chave_ang] - 90) % 360
            st.rerun()

    except Exception as e:
        st.warning(f"Não foi possível carregar a imagem para rotação: {e}")
        st.image(url_limpa, use_container_width=True)
