---
name: Dias sem aula vs feriados nacionais
description: Por que dias do Calendário Institucional registrados pelo usuário não podem ser intersectados com dias úteis na Prestação de Contas.
---

# Dias do Calendário Institucional na Prestação de Contas

A lista "Dias SEM AULA registrados no Calendário Institucional" (tabela `dias_sem_aula`)
deve exibir **todos** os dias que o operador registrou no período, sem filtrar por
"dia útil".

**Why:** o cálculo de dias úteis remove fins de semana E feriados nacionais
(`_feriados_nacionais_br`, que inclui Corpus Christi = Páscoa+60). Se a lista de
dias-sem-aula for intersectada com esse conjunto de dias úteis, um dia registrado
manualmente que caia em feriado nacional (ex.: 04/06/2026 = Corpus Christi) some do
relatório, mesmo tendo sido cadastrado de propósito.

**How to apply:** a lista de dias-sem-aula vem direto de `get_dias_sem_aula(ini, fim)`
(já filtrado por período via gte/lte). Use o conjunto completo; só o cálculo de
"dias úteis sem frequência" (alerta) deve usar o range de dias úteis.
