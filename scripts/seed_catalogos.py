#!/usr/bin/env python3
"""Pré-popula os catálogos clínicos do IMBRA de forma idempotente.

Pré-requisitos:
    1. Executar migrations/006_catalogos_clinicos.sql no Supabase.
    2. Definir as variáveis SUPABASE_URL e SUPABASE_KEY no ambiente.

O script nunca lê, altera ou classifica dados legados dos alunos. Ele atua
somente sobre os três catálogos novos e pode ser executado repetidamente.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from supabase import Client, create_client


CONDICOES: list[dict[str, str]] = [
    {
        "codigo": "ARTROSE",
        "nome_padrao": "Artrose",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Condição articular",
    },
    {
        "codigo": "LOMBALGIA",
        "nome_padrao": "Lombalgia",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Coluna vertebral",
    },
    {
        "codigo": "OSTEOPOROSE",
        "nome_padrao": "Osteoporose",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Saúde óssea",
    },
    {
        "codigo": "HIPERTENSAO_ARTERIAL",
        "nome_padrao": "Hipertensão arterial",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Hipertensão",
    },
    {
        "codigo": "DIABETES_MELLITUS_TIPO_2",
        "nome_padrao": "Diabetes mellitus tipo 2",
        "categoria": "METABOLICA",
        "grupo": "Diabetes",
    },
    {
        "codigo": "RISCO_DE_QUEDA",
        "nome_padrao": "Risco de queda",
        "categoria": "RISCO_FUNCIONAL",
        "grupo": "Risco funcional",
    },
    {
        "codigo": "PARKINSON",
        "nome_padrao": "Parkinson",
        "categoria": "NEUROLOGICA",
        "grupo": "Doença neurológica",
    },
    {
        "codigo": "CARDIOPATIA_NAO_ESPECIFICADA",
        "nome_padrao": "Cardiopatia não especificada",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "DOENCA_ARTERIAL_CORONARIANA",
        "nome_padrao": "Doença arterial coronariana / doença isquêmica do coração",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "HISTORICO_INFARTO_AGUDO_MIOCARDIO",
        "nome_padrao": "Histórico de infarto agudo do miocárdio",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Histórico cardiovascular",
    },
    {
        "codigo": "INSUFICIENCIA_CARDIACA",
        "nome_padrao": "Insuficiência cardíaca",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "ARRITMIA_CARDIACA",
        "nome_padrao": "Arritmia cardíaca",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "CARDIOMIOPATIA",
        "nome_padrao": "Cardiomiopatia",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "VALVOPATIA_CARDIACA",
        "nome_padrao": "Valvopatia cardíaca",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "OUTRA_CONDICAO_CARDIACA_ESPECIFICADA",
        "nome_padrao": "Outra condição cardíaca especificada",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
    },
    {
        "codigo": "MARCAPASSO",
        "nome_padrao": "Marca-passo",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Dispositivo cardíaco implantado",
    },
    {
        "codigo": "DESFIBRILADOR_IMPLANTAVEL",
        "nome_padrao": "Desfibrilador implantável",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Dispositivo cardíaco implantado",
    },
]

RESTRICOES: list[dict[str, str]] = [
    {"codigo": "EVITAR_IMPACTO", "nome_padrao": "Evitar impacto"},
    {"codigo": "EVITAR_SALTOS", "nome_padrao": "Evitar saltos"},
    {"codigo": "REDUZIR_AMPLITUDE", "nome_padrao": "Reduzir amplitude do movimento"},
    {"codigo": "EVITAR_AGACHAMENTO_PROFUNDO", "nome_padrao": "Evitar agachamento profundo"},
    {"codigo": "EVITAR_CARGA_ACIMA_CABECA", "nome_padrao": "Evitar carga acima da cabeça"},
    {
        "codigo": "MANTER_INTENSIDADE_LEVE_MODERADA",
        "nome_padrao": "Manter intensidade leve a moderada",
    },
]

ADAPTACOES: list[dict[str, str]] = [
    {"codigo": "CADEIRA_ALTA_COM_APOIO", "nome_padrao": "Cadeira alta com apoio"},
    {"codigo": "EXERCICIO_SENTADO", "nome_padrao": "Exercício sentado"},
    {"codigo": "REDUCAO_DE_CARGA", "nome_padrao": "Redução de carga"},
    {"codigo": "SUPERVISAO_PROXIMA", "nome_padrao": "Supervisão próxima"},
]


def _cliente() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError(
            "Defina SUPABASE_URL e SUPABASE_KEY no ambiente antes de executar o seed."
        )
    return create_client(url, key)


def _inserir_ausentes_por_codigo(
    client: Client,
    tabela: str,
    registros: list[dict[str, Any]],
    dry_run: bool,
) -> tuple[int, int]:
    """Insere somente códigos ausentes e preserva registros administrados."""
    inseridos = 0
    preservados = 0
    for registro in registros:
        codigo = registro["codigo"]
        existente = (
            client.table(tabela)
            .select("id")
            .eq("codigo", codigo)
            .limit(1)
            .execute()
        )
        if dry_run:
            acao = "preservaria" if existente.data else "inseriria"
            print(f"[dry-run] {acao}: {tabela}.{codigo}")
            preservados += int(bool(existente.data))
            inseridos += int(not bool(existente.data))
            continue

        if existente.data:
            preservados += 1
        else:
            client.table(tabela).insert({**registro, "ativo": True}).execute()
            inseridos += 1
    return inseridos, preservados


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed idempotente dos catálogos clínicos do IMBRA."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra as alterações previstas sem gravar no Supabase.",
    )
    args = parser.parse_args()

    try:
        client = _cliente()
        resultados = [
            (
                "Condições clínicas",
                *_inserir_ausentes_por_codigo(
                    client, "catalogo_condicoes_clinicas", CONDICOES, args.dry_run
                ),
            ),
            (
                "Restrições de movimento",
                *_inserir_ausentes_por_codigo(
                    client, "catalogo_restricoes_movimento", RESTRICOES, args.dry_run
                ),
            ),
            (
                "Adaptações recomendadas",
                *_inserir_ausentes_por_codigo(
                    client, "catalogo_adaptacoes", ADAPTACOES, args.dry_run
                ),
            ),
        ]
    except Exception as exc:
        print(f"Erro ao executar seed: {exc}", file=sys.stderr)
        return 1

    print("Seed de catálogos clínicos concluído.")
    for nome, inseridos, preservados in resultados:
        print(f"- {nome}: {inseridos} inserido(s), {preservados} preservado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())