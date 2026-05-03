# ==============================================================================
# 📄 utils/texto.py — Utilitários de Texto Partilhados
# ⚙️ Elimina duplicidade de remover_acentos, normalizar_fonetica e whatsapp
#    Usado por: frequencia_view, prontuario_dashboard, ficha_aluno_view,
#               tab_niver, tab_emergencia, radar_acolhimento_view
# ==============================================================================

import re
import unicodedata
import pandas as pd


def remover_acentos(texto) -> str:
    """Remove acentos e normaliza para lowercase. Aceita str ou NaN."""
    if pd.isna(texto) or not isinstance(texto, str):
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).lower()


def normalizar_fonetica(texto) -> str:
    """Normaliza para busca fonética tolerante a erros ortográficos."""
    if not texto or not isinstance(texto, str):
        return ""
    t = remover_acentos(texto)
    t = (
        t.replace("ct", "t")
         .replace("ph", "f")
         .replace("th", "t")
         .replace("y", "i")
         .replace("ll", "l")
         .replace("nn", "n")
    )
    return t.strip()


def formatar_whatsapp_numero(numero) -> str | None:
    """Retorna apenas os dígitos com código do país (+55) ou None.
    Use para construir URLs personalizadas (ex: com ?text=...).
    """
    if not numero or pd.isna(numero):
        return None
    limpo = re.sub(r"\D", "", str(numero))
    if not limpo:
        return None
    if len(limpo) >= 10:
        if len(limpo) <= 11:
            limpo = "55" + limpo
        return limpo
    return None


def formatar_whatsapp_link(numero) -> str | None:
    """Retorna URL completa https://wa.me/55... ou None.
    Use para links directos sem parâmetros adicionais.
    """
    digits = formatar_whatsapp_numero(numero)
    return f"https://wa.me/{digits}" if digits else None
