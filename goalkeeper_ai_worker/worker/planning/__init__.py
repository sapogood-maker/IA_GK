"""Planning Layer (Sprint W36).

Reclassificação determinística de `ConvictionSet` (W35) num conjunto de
PLANOS POSSÍVEIS - cada um uma categoria de ação que passa a fazer
sentido logicamente, dada uma crença suficientemente sólida. Nunca uma
escolha, execução ou recomendação - isso pertence à futura Decision
Layer.

Planning nunca observa o mundo: consome EXCLUSIVAMENTE `ConvictionSet`.
Nenhum código aqui importa `worker.hypothesis`, `worker.perceptual_state`,
`worker.memory`, `worker.timeline` ou `worker.explorers`. Sem memória
própria - `build_plans` deriva o estado de cada plano inteiramente do
snapshot atual de `ConvictionSet` (que já contém a informação temporal
computada pela Conviction Layer)."""
