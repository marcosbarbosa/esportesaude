"""Funções puras para a contagem institucional de aulas.

Uma aula lançada é uma data que possui ao menos um status de frequência válido.
Datas registradas como ``sem aula`` no Calendário Institucional não entram na
contagem, mesmo que tenham lançamentos históricos.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Iterable


STATUS_FREQUENCIA_VALIDOS = frozenset({"PRESENTE", "FALTA", "JUSTIFICADA"})


def _normalizar_data(valor: object) -> str | None:
    texto = str(valor or "").strip()[:10]
    try:
        return dt.date.fromisoformat(texto).isoformat()
    except (TypeError, ValueError):
        return None


def filtrar_datas_aulas_validas(
    lancamentos: Iterable[dict],
    dias_sem_aula: Iterable[dt.date | str],
) -> tuple[str, ...]:
    """Retorna datas únicas de aula, em ordem, respeitando o calendário."""
    bloqueadas = {
        data
        for item in dias_sem_aula
        if (data := _normalizar_data(item)) is not None
    }
    datas = {
        data
        for registro in lancamentos
        if registro.get("status") in STATUS_FREQUENCIA_VALIDOS
        and (data := _normalizar_data(registro.get("data_aula"))) is not None
        and data not in bloqueadas
    }
    return tuple(sorted(datas))


def sequenciar_datas_aulas(datas: Iterable[str]) -> tuple[tuple[str, int], ...]:
    """Numera cronologicamente datas já consideradas válidas."""
    return tuple((data, indice) for indice, data in enumerate(sorted(set(datas)), start=1))


def contar_aulas_por_mes(datas: Iterable[str]) -> dict[int, int]:
    """Agrupa datas válidas por mês, preservando apenas dados ISO válidos."""
    resultado: defaultdict[int, int] = defaultdict(int)
    for data in sorted(set(datas)):
        try:
            resultado[int(data[5:7])] += 1
        except (TypeError, ValueError):
            continue
    return dict(resultado)