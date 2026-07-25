"""Conviction Layer (Sprint W35).

Primeira camada com memória própria: compara `HypothesisSet`s (W34)
sucessivos ao longo do tempo e mantém crenças sobre a persistência de
cada hipótese - nasce, fortalece, persiste, enfraquece ou desaparece.

Conviction nunca lê `Timeline`, `Event`, `TemporalMemory` ou
`WorkingState` - consome EXCLUSIVAMENTE `HypothesisSet`. Não implementa
Decision, Planning, Coaching, Rule Engine, Evaluation, Explainability ou
Prompt generation. O estado interno representa apenas o histórico das
HIPÓTESES, nunca de eventos.
"""
