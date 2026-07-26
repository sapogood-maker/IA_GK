# Sprint W40 — Explainability

## Objetivo

Analisar criticamente se uma camada de Explainability deveria existir sobre `DecisionSet`
(W37) + `EvaluationSet` (W39), respondendo "o que foi decidido / por que / como / qual
mecanismo resolveu o vencedor" sem gerar conhecimento novo. **Conclusão: nenhum pacote
novo foi criado.** Aplicando o mesmo rigor que reverteu `ExecutionIntent` na W38 —
desta vez de forma proativa, antes de escrever qualquer dataclass.

## Achado central

Cada uma das quatro perguntas que Explainability deveria responder já aponta direto para
um campo tipado e explícito existente hoje:

| Pergunta | Já responde lendo... |
|---|---|
| "O que foi decidido?" | `TrackDecision.selected_plan_id`/`.plan_type` |
| "Por que foi decidido?" | `TrackDecision.winning_criteria` |
| "Como foi produzida?" | `TrackDecision.winning_criteria` + `.discarded_plan_ids` |
| "Qual mecanismo resolveu?" | `TrackEvaluation.resolution_method` |

Diferente da W39 (onde `ResolutionMethod` precisou ser CALCULADO a partir de uma string
opaca dentro de uma tupla — um parsing real), aqui não sobra nenhuma interpretação a
fazer: toda resposta já é um campo nomeado, pronto para leitura direta.

## Por que uma implementação ingênua repetiria o erro do `ExecutionIntent` (W38)

Uma `TrackExplanation` juntando os campos de `TrackDecision` + `TrackEvaluation` por
`track_id` seria, por definição, uma cópia literal — nenhuma informação nova, nenhuma
redução de acoplamento real (um consumidor já pode ler os dois artefatos pela mesma
chave), e a junção em si é trivial e sempre segura: `EvaluationSet.track_evaluations`
compartilha, por construção, exatamente o mesmo conjunto de chaves que
`DecisionSet.track_decisions` (`evaluate()`, W39, nunca filtra nenhuma decisão). O próprio
critério de aceitação do pedido — "por que Explainability não é apenas uma cópia?" — tem
resposta honesta: **não há como ela ser outra coisa**, dado que o pedido explicitamente
proíbe as únicas coisas (recálculo, inferência, texto livre) que poderiam justificar uma
responsabilidade genuinamente nova.

## Único artefato desta sprint: nota de garantia de junção em `worker/evaluation/`

Nenhum campo, tipo, assinatura ou comportamento mudou. Foi acrescentada uma nota de
documentação (docstring) a `evaluation_set.py` explicitando que
`track_evaluations`/`entity_evaluations` sempre compartilham exatamente o mesmo conjunto
de chaves que `DecisionSet.track_decisions`/`entity_decisions` — tornando explícito, para
quem precisar "explicar" uma decisão no futuro, que basta cruzar os dois artefatos pela
mesma chave, sem necessidade de uma camada de junção. Suíte de testes de
`worker/evaluation/` (21 testes, W39) confirmada intacta após a mudança.

## Riscos identificados

1. Se no futuro for necessário gerar texto em linguagem natural a partir dessas decisões
   (a aplicação mais comum do termo "Explainability" em IA), essa seria uma
   responsabilidade genuinamente nova e distinta — fora do escopo deste pedido, que
   restringe a saída a "forma estruturada". Justificaria uma sprint própria, não uma
   revisão desta conclusão.
2. Um consumidor externo pode preferir, por conveniência, um único artefato "tudo junto"
   em vez de cruzar dois — custo de usabilidade pequeno e aceito conscientemente (mesma
   lógica da W38 sobre `selected_plan_id`/`discarded_plan_ids`).
3. Se `DecisionSet`/`EvaluationSet` deixarem de compartilhar exatamente as mesmas chaves
   no futuro (uma mudança em `evaluate()` que passe a filtrar sujeitos), a garantia de
   junção total documentada nesta sprint deixaria de valer — por isso foi registrada
   explicitamente, para que uma mudança futura não a quebre silenciosamente sem aviso.

## Compatibilidade

Nenhum arquivo de `worker/timeline/`, `worker/explorers/`, `worker/segments/`,
`worker/memory/`, `worker/perceptual_state/`, `worker/hypothesis/`, `worker/conviction/`,
`worker/planning/`, `worker/decision/`, `worker/analyzers/`, `worker/domain/` foi
alterado. Apenas 1 docstring em `worker/evaluation/evaluation_set.py` foi estendida
(nenhuma lógica).

## Impacto esperado no que vem depois

Não há `ExplanationSet` para nenhuma camada futura consumir. Um adaptador externo (fora de
`worker/`) que precise "explicar" uma decisão — painel, log estruturado, relatório — lê
`DecisionSet` e `EvaluationSet` diretamente, pela mesma chave `track_id`/`entity`,
exatamente como já podia antes desta sprint.

## Próximos passos

- Geração de texto em linguagem natural a partir de `DecisionSet`+`EvaluationSet`, se
  algum dia for um requisito explícito e distinto — sprint própria, escopo diferente do
  pedido de W40.
- Revisitar esta conclusão se `DecisionSet`/`EvaluationSet` deixarem de compartilhar
  exatamente as mesmas chaves.
- Um painel externo de observabilidade do núcleo, consumindo `DecisionSet` +
  `EvaluationSet` juntos — fora de `worker/`, não implementado aqui.
