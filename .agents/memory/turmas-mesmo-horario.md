---
name: Agrupamento de turmas por horário
description: Como identificar/mesclar turmas que compartilham o mesmo horário na tela de chamada (views/frequencia_view.py).
---

A tabela `turmas` tem uma coluna dedicada `horario` (preenchida via `adicionar_turma`/`atualizar_turma`), separada do campo `nome` (texto livre, ex: "08H - Seg à Sex"). Ao agrupar/mesclar turmas do mesmo horário, prefira comparar por `horario` em vez de regex sobre `nome` — o regex (`0[789]H|1[012]H`) é só um fallback de compatibilidade para quando `horario` está vazio ou o nome não segue o padrão.

**Why:** o nome da turma é texto livre editável pelo admin; a coluna `horario` é a fonte de verdade estruturada. Uma implementação anterior usava só regex sobre o nome, o que quebra silenciosamente se o admin renomear a turma sem o padrão "0XH".

**How to apply:** ver `obter_turmas_mesmo_horario()` em `views/frequencia_view.py` — tenta `horario` primeiro, cai para regex no nome como fallback. Reusar essa função para qualquer nova feature que precise agrupar turmas simultâneas (ex.: chamada mesclada, relatórios por turno).
