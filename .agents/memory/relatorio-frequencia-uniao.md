---
name: Relatório de frequência — dias de aula = Diário ∪ Frequência
description: Regra durável de como o relatório de período define "dias com aula" e como tratar datas date vs timestamp.
---
Regra: ao montar relatórios de frequência por período, os "dias com aula" de uma turma
são a UNIÃO dos dias do Diário com os dias que têm registro de presença — nunca só o
Diário.

**Why:** lançar presença grava apenas em `frequencia`; criar a linha no `diario_aulas`
é um passo separado e opcional do professor. Se o relatório usa só o Diário como fonte
de "houve aula", presenças lançadas sem diário desaparecem e o período aparece vazio,
mesmo havendo presenças. (Incidente real: dia com presença e sem diário → relatório vazio.)

**How to apply:** qualquer dia com presença conta como aula (anti-furo reverso); alunos
da turma sem registro nesse dia seguem como FALTA. Como `frequencia` não tem coluna de
turma, mapeie aluno→turma pelos alunos para atribuir os dias vindos da presença.

**Armadilha de data (durável):** datas de aula podem vir como date puro (`2026-06-03`)
de uma tabela e como timestamp (`2026-06-03T00:00:00+00:00`) de outra. Sempre normalize
para `str(v)[:10]` antes de comparar, e em filtros de intervalo use limite superior
EXCLUSIVO (`< data_fim + 1 dia`) — `<= 'YYYY-MM-DD'` exclui o timestamp do último dia
por comparação lexicográfica de string.
