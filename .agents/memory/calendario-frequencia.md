---
name: Calendário institucional na frequência
description: Regra institucional que define quais datas podem entrar na contagem de aulas.
---

Datas marcadas como **sem aula** no Calendário Institucional nunca entram na
contagem de aulas, na sequência anual, no progresso mensal ou nos indicadores
de frequência, mesmo que existam lançamentos históricos de presença, falta ou
justificativa.

**Why:** A base pode conter lançamentos feitos antes de uma data ser declarada
sem aula; tratá-los como sessão realizada gera totais conflitantes entre telas e
relatórios.

**How to apply:** Toda nova métrica ou exportação que conte aulas deve partir da
mesma lista de datas válidas, filtrada pelo Calendário Institucional, e nunca
de datas distintas brutas da tabela de frequência.