---
name: Cadastro de aluno x uploads de documentos
description: Regra de produto — salvar o pré-cadastro nunca pode depender do sucesso dos uploads
---

# Salvar cadastro nunca depende de upload

**Regra:** nos formulários de inscrição (operador e público), gravar o registro
em `pre_cadastros` deve sempre acontecer mesmo que os uploads de documentos
(RG, receituário, atestado) falhem. Documentos que falham/não foram anexados
viram "pendentes" e são apenas avisados ao usuário, nunca bloqueiam o save.

**Why:** falha (ou lentidão → desconexão de WebSocket) no upload acionava
`st.stop()` e o operador perdia tudo o que digitou, tendo que relançar.
O cliente pediu explicitamente para salvar os dados independente dos uploads.

**How to apply:** mantenha validação de campos obrigatórios + consentimento
LGPD (são checkbox/texto, não perdem dados pois o form persiste). Para uploads,
acumule falhas numa lista e siga com o insert. Não reintroduza gate de
atestado obrigatório no submit. `upload_midia` tem retry para falhas
transitórias — não confundir "upload opcional" com "upload sem retry".
