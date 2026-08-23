---
name: Minimização de dados na revisão clínica
description: Regra de privacidade para listas e detalhes da fila clínica.
---

Listagens da fila clínica e de fontes legadas devem carregar somente metadados paginados e referências protegidas. Observações e textos clínicos só podem ser lidos individualmente após uma ação explícita do administrador autorizado.

**Why:** Ocultar o texto na interface não basta se o backend já o carregou em massa; isso amplia desnecessariamente a exposição de conteúdo clínico sensível.

**How to apply:** Em qualquer evolução da fila, use projeções mínimas e paginação no servidor para grades. Separe funções de resumo das funções de detalhe e nunca inclua texto legado, observações ou valores de auditoria em respostas de lista.