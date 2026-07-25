# Sprint W32 — Temporal Memory

## Objetivo

Projeção agregada da Perception Timeline (W28) + Play Segmentation (W30) + Enrichment
(W31): `TemporalMemory` responde perguntas de HISTÓRICO (duração, contagem, sequência de
estados, último evento) sobre tracks e entidades — nunca julgamento. Sem cognição, sem
decisão, sem Rule Engine, sem State Machine.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **`EventReference`** — `TrackMemory`/`EntityMemory.last_relevant_event` guardam uma
   referência compacta (`event_id`, `event_type`, `timestamp_seconds`), nunca o `Event`
   completo. `TemporalMemory` nunca embute fragmentos do Event Store.
2. **`PlayMemory` registrada como possibilidade arquitetural futura** — não implementada
   (o mesmo `TemporalMemory` aplicado a `segment.events` já cobre o caso de uso atual),
   documentada explicitamente como não descartada.

## Arquivos criados (zero arquivos existentes alterados)

```
worker/memory/
├── __init__.py
├── content_events.py       # CONTENT_EVENT_TYPES - replica os valores do default de
│                             GapStrategy (W30), sem importar sua constante privada
├── event_reference.py         # EventReference (dataclass, frozen)
├── track_memory.py               # TrackMemory (dataclass, frozen)
├── entity_memory.py                 # EntityMemory (dataclass, frozen)
├── temporal_memory.py                  # TemporalMemory (dataclass, frozen) - raiz
└── builder.py                              # build_temporal_memory(events) -> TemporalMemory

tests/memory/  (36 testes novos)
├── test_content_events.py, test_event_reference.py
├── test_track_memory.py, test_entity_memory.py, test_temporal_memory.py
└── test_builder.py
```

Nenhum arquivo de `worker/timeline/` (incl. `enrichment/`), `worker/explorers/`,
`worker/segments/`, `worker/analyzers/`, `worker/inference/`, `worker/domain/` foi alterado.

## Decisões de implementação (refinamentos sobre o documento)

- **Sem Registry/Factory** (decisão explícita do documento, seção 4): `build_temporal_memory`
  é uma função pura, único algoritmo de agregação.
- **`EntityMemory` computada em duas etapas**, não estritamente "em paralelo" como o
  documento descrevia: `track_ids`/timestamps/`last_relevant_event` são atualizados durante
  a MESMA passagem sobre `events` (barato, "último vence" funciona de graça porque `events`
  já é cronológico); `combined_motion_state_durations`/`total_recovery_count` são somados a
  partir dos `TrackMemory` já finalizados (O(número de tracks), não O(eventos)) — evita
  duplicar a lógica de deduplicação bruto/derivado uma segunda vez, mantendo o mesmo
  resultado e o mesmo O(n) geral.
- **Deduplicação bruto/derivado via `parent_event_id`**: antes da passagem principal, uma
  varredura coleta o conjunto de `event_id`s brutos que já têm um evento derivado (W31)
  apontando para eles; esses brutos são ignorados para contagem/duração (nunca conta a
  mesma transição duas vezes) — testado explicitamente (`test_mixed_raw_and_derived_does_not_double_count`,
  `test_recovery_count_via_derived_does_not_double_count_raw`).
- `build_temporal_memory` funciona com **eventos só brutos (W28)**, **só derivados**, ou
  **mistura dos dois** — não exige que a Enrichment tenha rodado.

## Testes

36 testes novos, cobrindo: transições únicas/múltiplas com soma correta de duração,
`states_visited` ordenado, deduplicação bruto/derivado (2 cenários dedicados), contagem de
recuperação via ambos os caminhos, `last_relevant_event` correto (incluindo eventos fora de
`CONTENT_EVENT_TYPES` não atualizando), múltiplos tracks/entidades independentes,
agregação de `EntityMemory` com normalização de rótulo (`"sports ball"` e `"ball"` caindo
na mesma entidade), `frame_range`/`time_range_seconds` cobrindo todos os eventos (não só os
de track), determinismo, e checagem cruzada com `PlaySegment.track_ids`.

## Validação contra o artifact real (job `b07f0dc6`, W28/W30/W31)

Entrada: 34.095 eventos brutos + 279 derivados (W31, composição não-redundante) = **34.374
eventos**.

| Métrica | Valor |
|---|---|
| `TrackMemory` produzidas | **48** (bate exatamente com os 48 `track_id` já conhecidos desde a W28/W30) |
| `EntityMemory` produzidas | **8** (`ball`, `person`, + 6 rótulos de ruído do COCO genérico: `backpack`, `baseball glove`, `bench`, `chair`, `clock`, `skateboard`) |
| Tamanho serializado — eventos de entrada | 12.583.414 bytes |
| Tamanho serializado — `TemporalMemory` | 31.394 bytes |
| **Razão de compressão** | **400,8x menor** |
| Determinismo (2 chamadas idênticas) | **Confirmado** |

Exemplo real (`track_id=1`, o "person" presente do frame 0 ao 568 — mesmo track já
analisado nas sprints anteriores): 144 transições de `motion_state` na passagem completa
do vídeo, 9,7s em `moving` + 8,7s em `stopped` (soma ≈ 18,4s dos 18,93s totais — a
diferença é o tempo antes da primeira transição registrada), `recovery_count=2`.
`EntityMemory["person"]` agrega 11 `track_id` diferentes (o mesmo "goleiro"/pessoa
observado perdeu e recuperou identidade várias vezes ao longo do vídeo — confirma
concretamente a razão de `EntityMemory` existir, descrita no documento arquitetural).

**Nota honesta**: `time_range_seconds` do vídeo mostrou um início ligeiramente negativo
(`-0.016s`) — já esperado e documentado desde a validação da W29/W31: `AnalyzerStarted`
(W28) calcula seu timestamp como `finished_ts - processing_time_ms/1000`, o que pode ir
levemente negativo no primeiro frame. Não é um bug introduzido pela W32.

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente. Suíte completa sem regressão (mesma
verificação de contagem já usada em W28-W31).

## Impacto esperado nas futuras camadas cognitivas

`TemporalMemory` é a matéria-prima direta que uma futura State Machine consultaria para
decidir guardas de transição (ex.: `track_memory.motion_transition_count > 0`), e que uma
futura camada de Coaching consultaria via `entity_memory.combined_motion_state_durations`
— sempre como fato de entrada, nunca como conclusão. Nenhuma dessas camadas foi
implementada aqui.

## Próximos passos

- State Machine e Goal Evaluation/Coaching (fora de escopo, consumiriam `TemporalMemory`).
- `PlayMemory` como classe própria, se uma camada cognitiva futura precisar comparar
  memória entre jogadas (possibilidade arquitetural registrada, não descartada).
- Lookup de `Event` completo por `event_id` em `TimelineExplorer` (W29), para resolver
  `EventReference` de volta ao evento inteiro quando necessário.
