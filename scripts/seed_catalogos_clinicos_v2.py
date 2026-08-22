#!/usr/bin/env python3
"""Complementa os catálogos clínicos do IMBRA sem tocar em alunos.

Pré-requisitos:
    - migrations/006_catalogos_clinicos.sql aplicada;
    - migrations/007_complemento_catalogos_clinicos.sql aplicada;
    - SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY disponíveis no ambiente seguro.

O seed é idempotente: insere códigos ausentes e somente completa metadados que
estejam vazios. Nunca altera alunos, tags_saude, problemas_saude ou
restricoes_fisicas.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from supabase import Client, create_client


CONDICOES: list[dict[str, Any]] = [
    {
        "codigo": "ARTROSE",
        "nome_padrao": "Artrose",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Condição articular",
        "descricao_operacional": "Condição articular que requer adaptação conforme dor, capacidade e orientação profissional.",
    },
    {
        "codigo": "ARTRITE",
        "nome_padrao": "Artrite",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Condição articular",
        "descricao_operacional": "Condição articular registrada para orientar acompanhamento e adaptação individual.",
    },
    {
        "codigo": "CONDROMALACIA",
        "nome_padrao": "Condromalácia",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Condição articular",
        "descricao_operacional": "Alteração articular a ser acompanhada conforme sintomas, orientação validada e capacidade funcional.",
    },
    {
        "codigo": "LOMBALGIA",
        "nome_padrao": "Lombalgia",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Coluna vertebral",
        "descricao_operacional": "Dor ou desconforto lombar registrado; não representa diagnóstico automático.",
    },
    {
        "codigo": "HERNIA_DE_DISCO",
        "nome_padrao": "Hérnia de disco",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Coluna vertebral",
        "descricao_operacional": "Condição de coluna que exige registro da orientação profissional e das adaptações validadas.",
    },
    {
        "codigo": "OSTEOPOROSE",
        "nome_padrao": "Osteoporose",
        "categoria": "MUSCULOESQUELETICA",
        "grupo": "Saúde óssea",
        "descricao_operacional": "Condição de saúde óssea que requer orientação individual registrada quando houver risco ou restrição.",
    },
    {
        "codigo": "HIPERTENSAO_ARTERIAL",
        "nome_padrao": "Hipertensão arterial",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Hipertensão",
        "descricao_operacional": "Condição cardiovascular distinta de cardiopatia; registrar apenas orientações validadas.",
    },
    {
        "codigo": "CARDIOPATIA_NAO_ESPECIFICADA",
        "nome_padrao": "Cardiopatia não especificada",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Classificação inicial provisória quando há relato cardíaco sem condição específica confirmada.",
    },
    {
        "codigo": "DOENCA_ARTERIAL_CORONARIANA",
        "nome_padrao": "Doença arterial coronariana / doença isquêmica do coração",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Condição cardíaca específica; requer fonte e orientação validadas antes de qualquer adaptação individual.",
    },
    {
        "codigo": "HISTORICO_INFARTO_AGUDO_MIOCARDIO",
        "nome_padrao": "Histórico de infarto agudo do miocárdio",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Histórico cardiovascular",
        "descricao_operacional": "Evento histórico, não diagnóstico ativo automático; registrar data e orientação disponível.",
    },
    {
        "codigo": "INSUFICIENCIA_CARDIACA",
        "nome_padrao": "Insuficiência cardíaca",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Condição cardíaca que requer origem da informação e orientação individual validada.",
    },
    {
        "codigo": "ARRITMIA_CARDIACA",
        "nome_padrao": "Arritmia cardíaca",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Condição cardíaca específica; não gerar prescrição automática a partir deste cadastro.",
    },
    {
        "codigo": "CARDIOMIOPATIA",
        "nome_padrao": "Cardiomiopatia",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Condição cardíaca específica que requer validação de fonte e orientação individual.",
    },
    {
        "codigo": "VALVOPATIA_CARDIACA",
        "nome_padrao": "Valvopatia cardíaca",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Condição cardíaca específica que requer validação de fonte e orientação individual.",
    },
    {
        "codigo": "OUTRA_CONDICAO_CARDIACA_ESPECIFICADA",
        "nome_padrao": "Outra condição cardíaca especificada",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Doença cardíaca / cardiopatia",
        "descricao_operacional": "Usar somente quando a condição foi descrita e não possui opção específica no catálogo.",
    },
    {
        "codigo": "MARCAPASSO",
        "nome_padrao": "Marca-passo",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Dispositivo cardíaco implantado",
        "descricao_operacional": "Dispositivo cardíaco implantado, não uma doença; registrar orientações validadas separadamente.",
    },
    {
        "codigo": "DESFIBRILADOR_IMPLANTAVEL",
        "nome_padrao": "Desfibrilador implantável",
        "categoria": "CARDIOVASCULAR",
        "grupo": "Dispositivo cardíaco implantado",
        "descricao_operacional": "Dispositivo cardíaco implantado, não uma doença; registrar orientações validadas separadamente.",
    },
    {
        "codigo": "DIABETES_MELLITUS_TIPO_2",
        "nome_padrao": "Diabetes mellitus tipo 2",
        "categoria": "METABOLICA",
        "grupo": "Diabetes",
        "descricao_operacional": "Condição metabólica que pode exigir atenção a orientações individuais validadas.",
    },
    {
        "codigo": "RISCO_DE_QUEDA",
        "nome_padrao": "Risco de queda",
        "categoria": "RISCO_FUNCIONAL",
        "grupo": "Risco funcional",
        "descricao_operacional": "Risco funcional; não é patologia e deve ter fonte, contexto e revisão registrados.",
    },
    {
        "codigo": "PARKINSON",
        "nome_padrao": "Parkinson",
        "categoria": "NEUROLOGICA",
        "grupo": "Doença neurológica",
        "descricao_operacional": "Condição neurológica que pode demandar adaptações individualmente validadas.",
    },
    {
        "codigo": "DPOC_ASMA",
        "nome_padrao": "DPOC / Asma",
        "categoria": "OUTRA",
        "grupo": "Condição respiratória",
        "descricao_operacional": "Condição respiratória que requer fonte e orientações individuais quando disponíveis.",
    },
    {
        "codigo": "FIBROMIALGIA",
        "nome_padrao": "Fibromialgia",
        "categoria": "OUTRA",
        "grupo": "Dor crônica",
        "descricao_operacional": "Condição de dor crônica; registrar resposta funcional e orientações individualizadas sem presumir incapacidade.",
    },
    {
        "codigo": "HIPOTIREOIDISMO",
        "nome_padrao": "Hipotireoidismo",
        "categoria": "METABOLICA",
        "grupo": "Condição endócrina",
        "descricao_operacional": "Condição endócrina registrada para acompanhamento, sem prescrição automática.",
    },
]

RESTRICOES: list[dict[str, Any]] = [
    {
        "codigo": "EVITAR_IMPACTO",
        "nome_padrao": "Evitar impacto",
        "categoria_movimento": "Impacto",
        "descricao_simples_para_aluno": "Prefira movimentos com menor impacto, conforme orientação recebida.",
        "nivel_padrao_sugerido": "EVITAR",
    },
    {
        "codigo": "EVITAR_SALTOS",
        "nome_padrao": "Evitar saltos",
        "categoria_movimento": "Impacto",
        "descricao_simples_para_aluno": "Evite saltos enquanto esta orientação estiver ativa.",
        "nivel_padrao_sugerido": "EVITAR",
    },
    {
        "codigo": "REDUZIR_AMPLITUDE",
        "nome_padrao": "Reduzir amplitude do movimento",
        "categoria_movimento": "Amplitude",
        "descricao_simples_para_aluno": "Faça o movimento em uma amplitude confortável e orientada.",
        "nivel_padrao_sugerido": "REDUZIR",
    },
    {
        "codigo": "EVITAR_AGACHAMENTO_PROFUNDO",
        "nome_padrao": "Evitar agachamento profundo",
        "categoria_movimento": "Joelho e quadril",
        "descricao_simples_para_aluno": "Evite descer além da amplitude orientada.",
        "nivel_padrao_sugerido": "EVITAR",
    },
    {
        "codigo": "EVITAR_CARGA_ACIMA_CABECA",
        "nome_padrao": "Evitar carga acima da cabeça",
        "categoria_movimento": "Ombro",
        "descricao_simples_para_aluno": "Evite elevar carga acima da cabeça enquanto esta orientação estiver ativa.",
        "nivel_padrao_sugerido": "EVITAR",
    },
    {
        "codigo": "MANTER_INTENSIDADE_LEVE_MODERADA",
        "nome_padrao": "Manter intensidade leve a moderada",
        "categoria_movimento": "Intensidade",
        "descricao_simples_para_aluno": "Mantenha o esforço dentro da intensidade orientada.",
        "nivel_padrao_sugerido": "MONITORAR",
    },
    {
        "codigo": "EVITAR_MANOBRA_VALSALVA",
        "nome_padrao": "Evitar manobra de Valsalva",
        "categoria_movimento": "Respiração e esforço",
        "descricao_simples_para_aluno": "Não prenda a respiração durante o esforço.",
        "nivel_padrao_sugerido": "EVITAR",
    },
    {
        "codigo": "EVITAR_ROTACAO_BRUSCA_COLUNA",
        "nome_padrao": "Evitar rotação brusca da coluna",
        "categoria_movimento": "Coluna vertebral",
        "descricao_simples_para_aluno": "Faça rotações lentas e dentro do movimento orientado.",
        "nivel_padrao_sugerido": "EVITAR",
    },
]

ADAPTACOES: list[dict[str, Any]] = [
    {
        "codigo": "CADEIRA_ALTA_COM_APOIO",
        "nome_padrao": "Cadeira alta com apoio",
        "categoria_adaptacao": "Apoio e mobiliário",
        "descricao_operacional": "Usar cadeira firme e mais alta para facilitar sentar e levantar com segurança.",
        "descricao_simples_para_aluno": "Use uma cadeira alta e firme como apoio.",
    },
    {
        "codigo": "EXERCICIO_SENTADO",
        "nome_padrao": "Exercício sentado",
        "categoria_adaptacao": "Posicionamento",
        "descricao_operacional": "Executar o exercício sentado quando esta adaptação estiver validada.",
        "descricao_simples_para_aluno": "Faça o exercício sentado.",
    },
    {
        "codigo": "REDUCAO_DE_CARGA",
        "nome_padrao": "Redução de carga",
        "categoria_adaptacao": "Carga",
        "descricao_operacional": "Usar resistência ou carga menor dentro da orientação validada.",
        "descricao_simples_para_aluno": "Use uma carga mais leve.",
    },
    {
        "codigo": "SUPERVISAO_PROXIMA",
        "nome_padrao": "Supervisão próxima",
        "categoria_adaptacao": "Acompanhamento",
        "descricao_operacional": "Manter acompanhamento próximo do professor durante a atividade orientada.",
        "descricao_simples_para_aluno": "Realize a atividade próximo ao professor.",
    },
    {
        "codigo": "APOIO_FIXO_PROXIMO",
        "nome_padrao": "Apoio fixo próximo",
        "categoria_adaptacao": "Equilíbrio",
        "descricao_operacional": "Disponibilizar apoio firme e estável ao alcance durante atividades validadas.",
        "descricao_simples_para_aluno": "Mantenha um apoio firme por perto.",
    },
    {
        "codigo": "PAUSAS_PROGRAMADAS",
        "nome_padrao": "Pausas programadas",
        "categoria_adaptacao": "Ritmo",
        "descricao_operacional": "Organizar pausas conforme a orientação individual validada.",
        "descricao_simples_para_aluno": "Faça pausas nos momentos combinados.",
    },
    {
        "codigo": "AMPLITUDE_SEM_DOR",
        "nome_padrao": "Amplitude confortável sem dor",
        "categoria_adaptacao": "Amplitude",
        "descricao_operacional": "Executar somente na amplitude confortável prevista na orientação individual.",
        "descricao_simples_para_aluno": "Faça o movimento sem ultrapassar o desconforto orientado.",
    },
]


def _cliente() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError(
            "Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no backend seguro. "
            "O seed não aceita chave anon porque as tabelas clínicas usam RLS."
        )
    return create_client(url, key)


def _inserir_ou_complementar(
    client: Client,
    tabela: str,
    registros: list[dict[str, Any]],
    dry_run: bool,
) -> tuple[int, int, int]:
    """Insere ausentes e completa apenas metadados vazios de registros existentes."""
    inseridos = complementados = preservados = 0
    for registro in registros:
        existente = (
            client.table(tabela)
            .select("*")
            .eq("codigo", registro["codigo"])
            .limit(1)
            .execute()
        )
        atual = existente.data[0] if existente.data else None
        if not atual:
            if dry_run:
                print(f"[dry-run] inseriria: {tabela}.{registro['codigo']}")
                inseridos += 1
            else:
                resposta = (
                    client.table(tabela)
                    .upsert(
                        {**registro, "ativo": True},
                        on_conflict="codigo",
                        ignore_duplicates=True,
                    )
                    .execute()
                )
                if resposta.data:
                    inseridos += 1
                else:
                    preservados += 1
            continue

        complementos = {
            campo: valor
            for campo, valor in registro.items()
            if campo not in {"codigo", "nome_padrao", "categoria", "grupo"}
            and atual.get(campo) is None
        }
        if complementos:
            if dry_run:
                print(
                    f"[dry-run] complementaria: {tabela}.{registro['codigo']} "
                    f"→ {sorted(complementos)}"
                )
                complementados += 1
            else:
                alterou = False
                for campo, valor in complementos.items():
                    resposta = (
                        client.table(tabela)
                        .update({campo: valor})
                        .eq("id", atual["id"])
                        .is_(campo, "null")
                        .execute()
                    )
                    alterou = alterou or bool(resposta.data)
                if alterou:
                    complementados += 1
                else:
                    preservados += 1
        else:
            if dry_run:
                print(f"[dry-run] preservaria: {tabela}.{registro['codigo']}")
            preservados += 1
    return inseridos, complementados, preservados


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed v2 idempotente dos catálogos clínicos do IMBRA."
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
                *_inserir_ou_complementar(
                    client, "catalogo_condicoes_clinicas", CONDICOES, args.dry_run
                ),
            ),
            (
                "Restrições de movimento",
                *_inserir_ou_complementar(
                    client, "catalogo_restricoes_movimento", RESTRICOES, args.dry_run
                ),
            ),
            (
                "Adaptações recomendadas",
                *_inserir_ou_complementar(
                    client, "catalogo_adaptacoes", ADAPTACOES, args.dry_run
                ),
            ),
        ]
    except Exception as exc:
        print(f"Erro ao executar seed v2: {exc}", file=sys.stderr)
        return 1

    print("Seed v2 de catálogos clínicos concluído.")
    for nome, inseridos, complementados, preservados in resultados:
        print(
            f"- {nome}: {inseridos} inserido(s), "
            f"{complementados} complementado(s), {preservados} preservado(s)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())