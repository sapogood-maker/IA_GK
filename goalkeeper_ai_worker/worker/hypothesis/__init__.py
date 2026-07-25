"""Hypothesis Layer (Sprint W34).

Primeira camada cognitiva: reclassifica `WorkingState` (W33) num
conjunto de POSSIBILIDADES, nunca de conclusões. Uma hipótese nunca
afirma que algo é verdadeiro - só registra "os fatos atuais de
WorkingState sustentam esta possibilidade".

Não implementa: Conviction, Decision, Planning, Rule Engine, Coaching,
Avaliação, Explicabilidade final. Não altera `worker/timeline/`,
`worker/explorers/`, `worker/segments/`, `worker/memory/`,
`worker/perceptual_state/`, `worker/analyzers/`, `worker/domain/` - só
LÊ `WorkingState`, nunca modifica.
"""
