# ==============================================================================
# 📄 ARQUIVO: utils/moderacao.py
# ⚙️ FUNÇÃO: Filtro de conteúdo ofensivo para comentários da pesquisa.
#            Bloqueia salvamento e exibição de textos com palavrões,
#            difamação e linguagem de baixo calão.
# ==============================================================================

import re

# Palavras e radicais ofensivos em português brasileiro
_TERMOS_OFENSIVOS = [
    # Palavrões diretos
    r"\bporra\b", r"\bmerda\b", r"\bfoda\b", r"\bfoder\b", r"\bfodas\b",
    r"\bputa\b", r"\bputas\b", r"\bputo\b", r"\bputos\b",
    r"\bviado\b", r"\bviadagem\b", r"\bviadinho\b",
    r"\bsacana\b", r"\bsacanas\b",
    r"\bbosta\b", r"\bsaco\b", r"\bsacos\b",
    r"\bcaralho\b", r"\bpau\b",
    r"\bcuzao\b", r"\bcuz[aã]o\b", r"\bcú\b", r"\bcu\b",
    r"\bdesgraça\b", r"\bdesgraçado\b", r"\bdesgraçada\b",
    r"\bbabaca\b", r"\bidiota\b", r"\bistupid[ao]\b",
    r"\bimbecil\b", r"\bburro\b", r"\bbesta\b",
    r"\bvagabund[ao]\b", r"\bvagabunda\b",
    r"\bcretino\b", r"\bcretina\b",
    r"\blixo\b", r"\blix[ao]\b",
    r"\bporcaria\b",
    r"\bastúcia\b",
    r"\bprostituição\b", r"\bprostituta\b",
    r"\bcorno\b", r"\bcorna\b",
    r"\bfela[çc]ão\b", r"\bpunheta\b", r"\bmasturbação\b",
    r"\btesão\b", r"\bpau\s+duro\b",
    r"\bsexo\b", r"\bsexual\b",
    r"\bfazendo\s+sex[uo]\b",
    # Difamação / ataques pessoais
    r"\bladr[aã]o\b", r"\bladrões\b",
    r"\bestuprador\b", r"\bcriminoso\b",
    r"\basso\b",
    # Variantes com escrita alternativa comuns em redes sociais
    r"\bpqp\b", r"\bvtc\b", r"\bvtnc\b", r"\bfds\b",
    r"\bkct\b", r"\bkrl\b",
]

_PATTERN = re.compile("|".join(_TERMOS_OFENSIVOS), re.IGNORECASE | re.UNICODE)


def contem_conteudo_ofensivo(texto: str) -> bool:
    """
    Retorna True se o texto contiver palavrões, difamação ou linguagem
    de baixo calão. Case-insensitive, ignora acentuação parcial.
    """
    if not texto or not str(texto).strip():
        return False
    # Normaliza espaços extras
    t = " ".join(str(texto).split())
    return bool(_PATTERN.search(t))


def sanitizar_comentario(texto: str) -> tuple[bool, str]:
    """
    Retorna (bloqueado: bool, mensagem: str).
    Se bloqueado=True, o comentário não deve ser salvo nem exibido.
    """
    if not texto or not str(texto).strip():
        return False, ""
    if contem_conteudo_ofensivo(texto):
        return True, (
            "⚠️ Seu comentário contém linguagem inadequada e não pode ser enviado. "
            "Por favor, reescreva de forma respeitosa."
        )
    return False, ""
