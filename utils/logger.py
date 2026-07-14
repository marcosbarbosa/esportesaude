# ==============================================================================
# 📄 utils/logger.py — Logging estruturado e centralizado do IMBRA
# Uso mínimo: loga apenas operações lentas (>1s) e exceções críticas.
# Evita I/O excessivo — não loga operações rápidas ou dados sensíveis.
# ==============================================================================
import logging
import time
from contextlib import contextmanager


def configurar_logging(level: int = logging.INFO) -> None:
    """Configura o logger 'imbra' sem tocar nos handlers do Streamlit.

    Usa APENAS o logger nomeado 'imbra' para não remover os handlers internos
    do Streamlit (que também ficam no root logger). force=True foi removido.
    """
    logger = logging.getLogger("imbra")
    if not logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(_handler)
    logger.setLevel(level)
    logger.propagate = False
    # Silenciar loggers verbose de dependências
    for _lib in ("httpx", "urllib3", "httpcore", "hpack", "h2", "h11"):
        logging.getLogger(_lib).setLevel(logging.WARNING)


def get_logger(nome: str = "imbra") -> logging.Logger:
    """Retorna um logger nomeado (ex: get_logger(__name__))."""
    return logging.getLogger(nome)


@contextmanager
def cronometrar(operacao: str, registros: int | None = None,
                logger: logging.Logger | None = None):
    """Context manager de timing cirúrgico para operações críticas.

    - Não loga nada se a operação for rápida (<1 s).
    - INFO  se entre 1s e 5s.
    - WARNING se >5s (sinal de gargalo).
    - ERROR com mensagem curta se lançar exceção (sem stack trace completo
      para evitar dados sensíveis nos logs do Render).

    Exemplo:
        with cronometrar("load_frequencia", registros=len(df)):
            df = load_frequencia_ultima_presenca()
    """
    _log = logger or get_logger("imbra")
    t0 = time.monotonic()
    try:
        yield
    except Exception as exc:
        ms = (time.monotonic() - t0) * 1000
        _log.error("[%s] FALHA em %.0f ms — %s: %s",
                   operacao, ms, type(exc).__name__, exc)
        raise
    else:
        ms = (time.monotonic() - t0) * 1000
        extra = f" | {registros} regs" if registros is not None else ""
        if ms >= 5000:
            _log.warning("[%s] LENTO %.0f ms%s", operacao, ms, extra)
        elif ms >= 1000:
            _log.info("[%s] %.0f ms%s", operacao, ms, extra)
