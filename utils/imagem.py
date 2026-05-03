# ==============================================================================
# 📄 utils/imagem.py — Utilitários de Imagem Partilhados
# ⚙️ Elimina duplicidade de get_base64_image (4 cópias nas views)
#    Usado por: relatorio_view, relatorio_satisfacao_view, validador_view,
#               ficha_aluno_view
# ==============================================================================

import base64
import io
import requests


def get_base64_image(image_path: str) -> str | None:
    """Lê imagem local e converte para data URL Base64 (PNG).
    Compatível com HTML inline, Word embedding e Excel charts.
    """
    try:
        with open(image_path, "rb") as img_file:
            return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode()}"
    except Exception:
        return None


def baixar_imagem_http(url: str) -> io.BytesIO | None:
    """Faz download de imagem via HTTP e retorna BytesIO pronto para uso.
    Compatível com python-docx (add_picture) e PIL (Image.open).
    """
    if not url or not isinstance(url, str):
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url.strip(), headers=headers, timeout=15)
        if resp.status_code == 200:
            return io.BytesIO(resp.content)
    except Exception:
        pass
    return None
