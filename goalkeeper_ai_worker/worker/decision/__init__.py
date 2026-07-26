"""Decision Layer (Sprint W37).

Reclassificação determinística de `PlanningSet` (W36) que escolhe, para
cada sujeito (track ou entidade) com pelo menos um plano ainda válido,
qual único plano deveria ser executado. Nunca cria planos, hipóteses ou
convicções novas; nunca executa; nunca avalia resultado; nunca gera
texto em linguagem natural.

Decision consome EXCLUSIVAMENTE `PlanningSet` - nenhum código aqui
importa `worker.conviction`, `worker.hypothesis`, `worker.perceptual_state`
ou camadas inferiores. Zero mudança em `worker/planning/` (W36) - nenhum
campo novo foi adicionado lá para "facilitar" esta camada. Nenhum
critério de desempate incorpora conhecimento semântico sobre o
significado de um `PlanType` - só critérios estruturais e
determinísticos, mantendo o núcleo cognitivo reutilizável para
qualquer domínio futuro."""
