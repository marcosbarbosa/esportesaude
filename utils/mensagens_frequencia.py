"""Regras puras para recomendações manuais de mensagem por frequência.

O módulo não envia mensagens. Ele apenas classifica o contexto do aluno para
que a interface possa oferecer um link de WhatsApp com o texto configurado
pela gestão.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class RecomendacaoFrequencia:
    """Modelo de mensagem sugerido para uma situação de frequência."""

    gatilho: str
    rotulo: str
    cor: str


def _data_segura(valor: Any) -> dt.date | None:
    """Converte date, datetime, Timestamp ou ISO para data; inválidos são nulos."""
    if valor is None or str(valor).strip().lower() in {"", "nat", "none"}:
        return None
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    if hasattr(valor, "to_pydatetime"):
        try:
            return valor.to_pydatetime().date()
        except Exception:
            return None
    try:
        return dt.date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError):
        return None


def dias_sem_presenca(ultima_presenca: Any, hoje: dt.date | None = None) -> int | None:
    """Retorna dias desde a última presença, ou None quando ela não existe."""
    data_presenca = _data_segura(ultima_presenca)
    if data_presenca is None:
        return None
    hoje = hoje or dt.date.today()
    return max(0, (hoje - data_presenca).days)


def ids_assiduidade_destaque(
    alunos: Iterable[dict[str, Any]],
    hoje: dt.date | None = None,
    fracao_top: float = 0.10,
    minimo_presencas: int = 10,
    max_dias_sem_presenca: int = 7,
) -> set[str]:
    """Seleciona os alunos mais assíduos por turma que continuam presentes.

    A comparação é feita dentro da própria turma. O corte usa os 10% com maior
    número de presenças do ano (incluindo empates) e exige presença recente,
    evitando elogiar alguém que está atualmente ausente.
    """
    hoje = hoje or dt.date.today()
    por_turma: dict[str, list[tuple[str, int, int | None]]] = {}

    for aluno in alunos:
        aluno_id = str(aluno.get("id") or "").strip()
        turma = str(aluno.get("turma") or "").strip()
        if not aluno_id or not turma:
            continue
        try:
            presencas = int(aluno.get("total_presencas_hist") or 0)
        except (TypeError, ValueError):
            presencas = 0
        por_turma.setdefault(turma, []).append(
            (aluno_id, max(0, presencas), dias_sem_presenca(aluno.get("ultima_presenca"), hoje))
        )

    destaques: set[str] = set()
    for alunos_turma in por_turma.values():
        alunos_recentes = [
            aluno for aluno in alunos_turma
            if aluno[2] is not None and aluno[2] <= max_dias_sem_presenca
        ]
        if not alunos_recentes:
            continue
        quantidade_top = max(1, math.ceil(len(alunos_recentes) * fracao_top))
        ranking = sorted(alunos_recentes, key=lambda item: item[1], reverse=True)
        corte = ranking[quantidade_top - 1][1]
        if corte < minimo_presencas:
            continue
        for aluno_id, presencas, dias_ausente in ranking:
            if (
                presencas >= corte
                and presencas >= minimo_presencas
                and dias_ausente is not None
                and dias_ausente <= max_dias_sem_presenca
            ):
                destaques.add(aluno_id)
    return destaques


def recomendar_mensagem_frequencia(
    aluno_id: Any,
    ultima_presenca: Any,
    ids_destaque: set[str],
    hoje: dt.date | None = None,
) -> RecomendacaoFrequencia | None:
    """Indica o gatilho de CRM para a prioridade de frequência do aluno.

    Ausência tem prioridade sobre elogio: uma pessoa ausente não recebe
    parabéns, ainda que possua muitas presenças acumuladas no ano.
    """
    dias_ausente = dias_sem_presenca(ultima_presenca, hoje)
    if dias_ausente is None:
        return RecomendacaoFrequencia("evasao_nunca", "Evasão: nunca frequentou", "#DC2626")
    if dias_ausente > 30:
        return RecomendacaoFrequencia("evasao_80", "Risco crítico de ausência", "#DC2626")
    if dias_ausente > 14:
        return RecomendacaoFrequencia("evasao_60", "Alerta de faltas", "#D97706")
    if str(aluno_id) in ids_destaque:
        return RecomendacaoFrequencia("assiduo_top", "Elogio de assiduidade", "#059669")
    return None