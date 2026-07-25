"""Temporal Memory (Sprint W32) - projecao agregada da Perception
Timeline (W28), consultas (W29), Play Segmentation (W30) e Enrichment
(W31).

Nao e cognicao: so organiza o historico ja existente (duracao, contagem,
sequencia de estados, ultimo evento) - nunca julga, decide ou avalia
qualidade. `build_temporal_memory(events)` e uma unica passagem O(n)
sobre uma sequencia de eventos ja cronologica (a Timeline inteira ou os
eventos de um unico PlaySegment - a funcao nao sabe nem precisa saber
qual dos dois), produzindo um objeto imutavel, reconstruivel e
deterministico: TemporalMemory, com TrackMemory (por track_id) e
EntityMemory (por rotulo normalizado) dentro.

Pacote proprio (nao aninhado em worker/timeline/) - sintetiza tres
fontes (Timeline, PlaySegment, Enrichment), nao e extensao natural de
nenhuma delas isoladamente. Nenhum arquivo de worker/timeline/,
worker/explorers/, worker/segments/, worker/analyzers/, worker/inference/,
worker/domain/ e alterado. Ver PERCEPTION_ENGINE_ARCHITECTURE.md e o
documento arquitetural da Sprint W32.
"""
