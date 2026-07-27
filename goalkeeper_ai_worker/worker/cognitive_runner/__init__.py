"""cognitive_runner: orquestra o Cognitive Core (v1.0, congelado) sobre
um `event_timeline` real - Phase 2, G2A.

Não é uma camada do núcleo - é a COLA que invoca, na ordem certa, as
funções puras já existentes de `worker.explorers`, `worker.segments`,
`worker.timeline.enrichment`, `worker.memory`, `worker.perceptual_state`,
`worker.hypothesis`, `worker.conviction`, `worker.planning`,
`worker.decision` e `worker.evaluation`. Nenhuma lógica é duplicada ou
reimplementada; nenhuma dataclass nova "tipo Core" é criada - o
resultado é sempre `list[dict]` simples.

Nome deliberadamente neutro (não "goalkeeper_*"): este código não
contém nada específico de futebol/goleiro - seria idêntico para
qualquer outro domínio que reutilize o mesmo núcleo.

Nesta sprint (G2A), `run_cognitive_core()` é standalone - não está
integrada a nenhuma Stage nem ao `WorkerOrchestrator` (isso é escopo de
uma sprint futura)."""
