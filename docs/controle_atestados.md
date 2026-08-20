# Controle de Atestados

Este documento define o contrato único para registrar, interpretar e exibir
atestados no sistema. Ele existe para impedir que telas diferentes cheguem a
datas ou situações diferentes para o mesmo aluno.

> **Regra inegociável:** qualquer tela deve consumir `status_atestado()` e/ou
> as colunas canônicas do DataFrame. Não criar cálculos locais de vencimento,
> filtros por data ou novos “semáforos” de atestado.

## 1. Tabela `atestados_temporarios`

Campos utilizados pelo sistema:

| Campo | Uso | Obrigatório |
|---|---|---|
| `id` | Identificador do registro | Sim |
| `aluno_id` | Referência ao aluno em `alunos.id` | Sim |
| `tipo_atestado` | Tipo do documento; `aptidao_fisica` é o único que compõe a validade de aptidão | Sim |
| `data_registro` | Data informada no cadastro do documento; define qual é o registro de aptidão vigente | Sim |
| `data_vencimento` | Validade do documento; obrigatória para `aptidao_fisica` | Sim para aptidão |
| `motivo` | Observação clínica/administrativa | Sim |
| `url_documento` | Arquivo anexado, quando houver | Não |

Tipos aceitos atualmente:

- `aptidao_fisica`
- `condicao_clinica`
- `pos_cirurgico`
- `restricao_atividade`
- `outro`

### Regra de cadastro

Para `aptidao_fisica`, o formulário deve exigir `data_vencimento`. Não usar
uma data calculada no front-end como substituta. O registro mais recente é
definido por `data_registro`; em empate, a maior data de vencimento é usada
apenas para tornar o resultado determinístico.

### Inscrição e pré-cadastro

Nos formulários de inscrição, a pessoa pode informar a data de validade
**somente se ela estiver escrita no documento**. Não há mais cálculo de
“emissão + 1 ano”. Na aprovação:

- o anexo é migrado para `atestados_temporarios`;
- a validade declarada é preservada exatamente como foi informada;
- quando não houver validade declarada, o registro oficial fica
  `SEM_VALIDIDADE`, visível para a equipe conferir no prontuário.

## 2. Função `status_atestado`

**Local:** `utils/atestado_ui.py`

```python
status_atestado(registros, bloqueado_manual=False, hoje=None) -> dict
```

A função aceita uma lista de dicionários ou DataFrame do histórico de
atestados e retorna o status canônico do **atestado de aptidão**.

Campos de retorno:

| Coluna/chave | Descrição |
|---|---|
| `status_atestado` | `SEM_REGISTRO`, `SEM_VALIDIDADE`, `VENCIDO`, `A_VENCER` ou `VALIDO` |
| `rotulo_atestado` | Texto humano da situação |
| `data_vencimento_atestado` | Data ISO (`AAAA-MM-DD`) ou `None` |
| `data_vencimento_formatada` | Data para exibir (`DD/MM/AAAA`) ou `—` |
| `atestado_dias_restantes` | Dias até o vencimento; negativo quando vencido |
| `atestado_icone`, `atestado_cor`, `atestado_fundo` | Metadados visuais padronizados |
| `atestado_bloqueado_manual` | Flag administrativa independente da validade |

Estados de validade:

| Estado | Condição |
|---|---|
| `SEM_REGISTRO` | Não existe atestado do tipo `aptidao_fisica` |
| `SEM_VALIDIDADE` | O último atestado de aptidão não possui data de vencimento válida |
| `VENCIDO` | `data_vencimento < hoje` |
| `A_VENCER` | Vence hoje ou nos próximos 30 dias |
| `VALIDO` | Vence em mais de 30 dias |

## 3. Regras de bloqueio

`alunos.atestado_bloqueado` é uma trava **manual** de participação. Ela deve
ser usada quando a equipe precisa impedir a chamada independentemente do prazo
do documento (por exemplo, documento pendente, restrição clínica ou conferência
administrativa).

- O bloqueio manual **não altera** `data_vencimento_atestado`.
- A validade vencida gera alerta visual e contato de renovação; ela não ativa
  automaticamente o bloqueio manual sem uma decisão explícita da equipe.
- A chamada diária usa `atestado_bloqueado` para sinalizar/travar a
  participação e usa as colunas de `status_atestado` para mostrar a data.
- O prontuário e o dossiê devem sempre mostrar a validade e, quando existir,
  o bloqueio manual como uma informação adicional.

## 4. Estrutura da coluna no Painel de Alunos

A coluna **Atestado** da tela inicial recebe o DataFrame produzido por
`database.load_atestados_vencimento()`. Ela deve usar somente:

```text
status_atestado
data_vencimento_atestado
data_vencimento_formatada
atestado_dias_restantes
rotulo_atestado
atestado_icone
atestado_cor
atestado_fundo
```

Regras de exibição:

1. Sempre exibir `data_vencimento_formatada` em `DD/MM/AAAA`; nunca encurtar
   para ano de dois dígitos.
2. Exibir `rotulo_atestado` abaixo da data.
3. Quando houver `atestado_bloqueado`, acrescentar “Bloqueio manual” sem
   substituir a data ou o status de validade.
4. Links de WhatsApp de renovação só são mostrados para `VENCIDO` e
   `A_VENCER`.

O botão **Processar em Lote** persiste a mesma estrutura em
`atestados_recs` do snapshot. Para que uma data recém-cadastrada seja visível
de imediato, a tela inicial prefere o DataFrame ao vivo, que é cacheado e
invalidado após incluir ou excluir um atestado.

## 5. Uso obrigatório em mudanças futuras

Antes de alterar qualquer fluxo abaixo, reutilize `status_atestado()` ou o
DataFrame de `load_atestados_vencimento()`:

- **Cadastro de alunos:** ao criar/importar documento de aptidão, gravar
  `tipo_atestado`, `data_registro` e `data_vencimento`; não escrever uma
  segunda data de validade em `alunos`.
- **Prontuário e dossiê:** mostrar o resultado de `status_atestado()` e a
  data formatada; o dossiê pode listar o histórico, mas o resumo de validade
  deve vir da função canônica.
- **Tela inicial:** manter a coluna `Atestado` baseada somente nas colunas
  listadas na seção 4.
- **Chamada diária:** receber as mesmas colunas no DataFrame de alunos e
  mostrar a data no cartão; não calcular dias restantes no módulo da chamada.

## 6. Roteiro de testes

Execute estes cenários após qualquer mudança relacionada a cadastro,
prontuário, dossiê, tela inicial ou chamada:

1. **Cadastro válido:** registrar aptidão com vencimento em mais de 30 dias.
   Confirmar `VALIDO` e a mesma data `DD/MM/AAAA` na tela inicial, prontuário,
   dossiê e chamada diária.
2. **A vencer:** registrar aptidão com vencimento entre hoje e 30 dias.
   Confirmar `A_VENCER`, cor de aviso e link de renovação na tela inicial.
3. **Vencido:** registrar aptidão com data anterior a hoje. Confirmar
   `VENCIDO`, data preservada e alerta em todas as telas.
4. **Sem validade:** tentar registrar aptidão sem data. O formulário deve
   impedir o salvamento. Para dados legados sem data, conferir
   `SEM_VALIDIDADE` e `—` como data.
5. **Histórico:** cadastrar duas aptidões com datas de registro diferentes.
   Confirmar que a de maior `data_registro` é a vigente, mesmo que a antiga
   possua outra validade.
6. **Bloqueio manual:** bloquear um aluno com atestado válido. Confirmar que
   a data continua visível e que a chamada mostra o bloqueio.
7. **Desbloqueio:** liberar o aluno e confirmar que a validade permanece
   inalterada.
8. **Remoção:** excluir o atestado vigente. Confirmar atualização sem esperar
   o TTL de cache e, em seguida, executar **Processar em Lote** para atualizar
   o snapshot.
9. **Volume:** com mais de 1.000 registros de atestado, validar que o
   carregador paginado mantém todos os alunos e não perde validade.
