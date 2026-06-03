---
name: Relatório de frequência — dias de aula = Diário ∪ Frequência
description: Por que o relatório de período não pode depender só de diario_aulas; regra de união e normalização de datas.
---
O relatório de período (`get_relatorio_periodo` em `database.py`, aba "Plan. Frequência")
deve derivar os dias de aula da **UNIÃO** de `diario_aulas` e `frequencia` — nunca só
do `diario_aulas`.

**Why:** lançar presença (`_gravar_lote` em `views/conferencia_facial_view.py`) grava
em `frequencia` mas NÃO cria linha em `diario_aulas`. Se o relatório usa só o Diário
como fonte de "dias com aula", presenças lançadas sem diário ficam invisíveis e o
relatório retorna vazio ("Não foram encontradas aulas no Diário para este período")
mesmo havendo presenças no dia. Confirmado em produção (03/06/2026): frequência tinha
o dia, diário não.

**How to apply:** ao calcular dias de aula por turma, faça `set(dias do diário) ∪
set(dias de frequência dos alunos da turma)`. `frequencia` não tem coluna `turma` →
mapear `aluno_id → turma` pelos alunos carregados. Qualquer dia com presença conta como
aula (anti-furo reverso); alunos da turma sem registro nesse dia continuam FALTA.

**Datas (armadilha):** `diario_aulas.data_aula` pode ser timestamp
(`2026-06-03T00:00:00+00:00`) e `frequencia.data_aula` date puro (`2026-06-03`).
Sempre normalizar com `str(v)[:10]` antes de comparar/igualar, e no filtro de intervalo
use limite superior exclusivo (`.lt(data_fim + 1 dia)`) — `.lte("...","2026-06-03")`
exclui lexicograficamente o timestamp do último dia.
