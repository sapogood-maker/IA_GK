"""Perceptual State Machine (Sprint W33) - projecao determinística de
`TemporalMemory` (W32) em um estado atual observavel: `WorkingState`.

Nao e uma maquina de estados classica (nenhum objeto que "recebe"
eventos e transita a si mesmo) - e uma funcao pura,
`build_working_state(memory) -> WorkingState`, exatamente como
`build_temporal_memory` (W32) ja e para a Timeline. So representa o que
JA e verdade (estado atual, desde quando, ultima transicao, duracao) -
nunca decide, planeja ou avalia qualidade.

Representacao (`WorkingState`/`TrackState`/`EntityState`) e verificacao
(`transition_validation.py`) sao responsabilidades SEPARADAS de
proposito - `build_working_state` nunca valida nada por conta propria.

Pacote proprio, nao aninhado em worker/memory/ - le TemporalMemory
(W32), nunca o modifica. Nenhum arquivo de worker/timeline/ (incl.
enrichment/), worker/explorers/, worker/segments/, worker/memory/,
worker/analyzers/, worker/inference/, worker/domain/ e alterado. Ver
PERCEPTION_ENGINE_ARCHITECTURE.md e o documento arquitetural da Sprint
W33.
"""
