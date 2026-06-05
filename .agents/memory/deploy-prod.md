---
name: Deploy de produção (Render)
description: Como/onde as mudanças aparecem em produção.
---

Produção roda em esportesaude.onrender.com e é **stale**: alterações no código só
aparecem após republicar manualmente. Não confunda "não vejo a mudança em prod"
com bug — verifique primeiro se foi republicado.

**Why:** evita retrabalho investigando "regressões" que na verdade são só falta de
deploy.
