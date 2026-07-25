# Sprint W33 — Perceptual State Machine

## Objetivo

Projeção determinística do estado atual observado a partir de `TemporalMemory` (W32):
`WorkingState` responde "qual é o estado atual?", "desde quando?", "qual foi a última
transição?" — nunca "o que deveria acontecer?". Sem hipótese, sem convicção, sem decisão,
sem Rule Engine, sem coaching, sem avaliação.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **Projeção, não máquina de estados clássica** — `build_working_state(memory)` é uma
   função pura que recalcula o `WorkingState` inteiro a cada chamada, do zero. Nenhum
   objeto stateful com `transition_to()`/`on_event()`. Mesma disciplina de
   `build_temporal_memory` (W32).
2. **Representação separada de validação** — `TrackState` nunca carrega um campo de
   "transição anômala". Se uma sequência é estruturalmente legal é uma pergunta
   independente, respondida sob demanda por `transition_validation.py`, nunca embutida na
   construção de `WorkingState`.
3. **`TransitionGraph`** — abstração de domínio (`is_legal(from, to)`) em vez de tabelas
   globais soltas, reutilizada por `MotionState` e `PresenceState`.

## Arquivos criados (zero arquivos existentes alterados)

```
worker/perceptual_state/
├── __init__.py
├── transition_graph.py       # TransitionGraph (dataclass, frozen)
├── motion_state.py               # MotionState (Enum) + MOTION_TRANSITION_GRAPH
├── presence_state.py                 # PresenceState (Enum) + PRESENCE_TRANSITION_GRAPH
├── state_transition.py                   # StateTransition (dataclass, frozen)
├── track_state.py                            # TrackState (dataclass, frozen) - só representação
├── entity_state.py                                # EntityState (dataclass, frozen)
├── working_state.py                                   # WorkingState (dataclass, frozen) - raiz
├── builder.py                                             # build_working_state(memory)
└── transition_validation.py                                   # TransitionValidationResult +
                                                                   validate_motion_transitions()

tests/perceptual_state/  (42 testes novos)
├── test_transition_graph.py, test_motion_state.py, test_presence_state.py
├── test_state_transition.py
├── test_track_state.py, test_entity_state.py, test_working_state.py
├── test_builder.py
└── test_transition_validation.py
```

Nenhum arquivo de `worker/timeline/` (incl. `enrichment/`), `worker/explorers/`,
`worker/segments/`, `worker/memory/`, `worker/analyzers/`, `worker/inference/`,
`worker/domain/` foi alterado.

## Modelo: dois eixos independentes

- **`MotionState`** (`UNKNOWN`/`MOVING`/`STOPPED`) — reaproveita o vocabulário já
  estabelecido em W28/W31/W32, agora como `Enum` + `TransitionGraph` com as 4 transições
  legítimas (`UNKNOWN→MOVING`, `UNKNOWN→STOPPED`, `MOVING→STOPPED`, `STOPPED→MOVING`).
- **`PresenceState`** (`PRESENT`/`ENDED`) — novo, deliberadamente simples: só 2 valores,
  porque `TemporalMemory` não expõe nenhum sinal de "perdido no meio do vídeo"
  (`content_events.py` exclui `TrackLost`/`OcclusionDetected` de `last_relevant_event`).
  `PRESENT` = `last_seen_frame == observed_at_frame` (comparação por frame, não timestamp
  — `frame_index` é sempre não-nulo no schema de `Event`, `timestamp_seconds` é opcional).
  `ENDED→PRESENT` não existe no grafo desta sprint (não por impossibilidade física —
  `recovery_count` prova que tracks reaparecem — mas porque `TemporalMemory` não guarda
  timestamps intermediários suficientes para reconstruir a série completa de
  presença/ausência).

Duas dimensões pequenas e ortogonais em vez de uma cadeia linear única evita o "enum
gigante" que o pedido original pedia para não ter.

## Sem Registry/Factory

Mesma decisão e mesma razão da W32: `build_working_state` é um único algoritmo de
reclassificação, sem implementações alternativas — nenhuma abstração adicional
introduzida.

## Testes

42 testes novos, cobrindo: `TransitionGraph.is_legal()` isolado; enums e seus grafos;
`StateTransition`; imutabilidade e serialização de `TrackState`/`EntityState`/
`WorkingState` (incluindo testes que **provam a ausência** de qualquer campo de
julgamento — `test_never_has_a_validation_field`, `test_never_has_a_dominant_state_field`);
`build_working_state` com 1 e 3+ estados visitados, `PresenceState` PRESENT vs ENDED,
agregação de `EntityState`, determinismo; `transition_validation.py` com sequência válida,
sequência sintética inválida, e prova de que rodar/não rodar a validação nunca afeta
`WorkingState` (`test_validation_never_affects_working_state_construction`).

## Validação contra o artifact real (job `b07f0dc6`, mesmos dados de W28-W32)

Mesmos 34.095 eventos brutos + 279 derivados (W31) = **34.374 eventos** usados em W32.

| Métrica | Valor |
|---|---|
| `TrackState` produzidos | **48** (bate com os 48 `TrackMemory`) |
| `EntityState` produzidos | **8** |
| `observed_at_frame` / `observed_at_timestamp` | 568 / 18,93s |
| Tamanho serializado — `TemporalMemory` | 31.394 bytes |
| Tamanho serializado — `WorkingState` | 23.468 bytes |
| Redução adicional sobre `TemporalMemory` | **1,34x menor** |
| Determinismo (2 chamadas idênticas) | **Confirmado** |

`track_id=1` (o mesmo "person" já analisado desde W28): `motion_state=STOPPED`,
`motion_transition_count=144`, `recovery_count=2` — idêntico ao já medido em W32.

### Achado honesto: a validação de transições encontrou algo real

Ao contrário do que o documento arquitetural previa na Seção 12 ("provavelmente
`is_valid=True` em todos os tracks hoje, o módulo é uma rede de segurança dormente"),
`validate_motion_transitions` rodada sobre os 48 `TrackMemory` reais encontrou **8 tracks
estruturalmente inválidos** — todos de `entity="ball"` (track_ids 64, 126, 139, 180, 198,
230, 263, 272), com pares consecutivos repetidos (ex.: `("stopped", "stopped")`,
`("moving", "moving")`).

**Causa raiz identificada**: a validação (seguindo a própria seção 11 do documento
aprovado) roda `MotionTransitionEnricher()` (sem filtro, todas as entidades) **e**
`MotionTransitionEnricher(entity_filter="ball")` **juntos** — para tracks de bola, os dois
Enrichers produzem dois eventos derivados distintos (`event_id` diferentes) para a MESMA
transição de movimento real. A deduplicação de W32 (`parent_event_id`) só resolve
bruto-vs-derivado, não derivado-vs-derivado de dois Enrichers sobrepostos — então
`states_visited` acumula o mesmo estado-alvo duas vezes seguidas para a bola.

Isto **não é um bug da W33**: `TrackState`/`build_working_state` não são afetados (eles
usam `current_motion_state`/`motion_transition_count` já resumidos por W32, não
`states_visited` bruto) — `track_id=1` (person) segue com os números exatos já
conhecidos. É uma característica pré-existente da combinação de dois Enrichers da W31,
invisível até agora porque nenhuma camada anterior verificava a legalidade estrutural de
`states_visited`. O valor do módulo de validação, previsto no documento como hipotético,
**se confirmou na prática**: ele detectou algo real que nenhuma sprint anterior via.
Nenhuma mudança foi feita em `worker/timeline/enrichment/` ou `worker/memory/` para
corrigir isso — fica registrado como item de roadmap (ver abaixo).

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente. Suíte completa: **710 passed** (668 da
baseline W32 + 42 novos), mesmos 26 failed / 16 errors pré-existentes em
`tests/infrastructure/` (exigem Redis/backend reais, não relacionados a
`perceptual_state`) — sem regressão.

## Impacto esperado nas futuras camadas cognitivas

`WorkingState` é o "estado atual" que uma futura Hypothesis Layer consultaria para propor
hipóteses condicionadas ao estado (ex.: `motion_state == STOPPED` e
`motion_state_duration_seconds` grande → hipótese X) — a Hypothesis Layer decide o QUE
inferir; W33 garante que o fato-base é confiável e determinístico. Uma futura Conviction
Layer usaria `recovery_count` e o resultado de `validate_motion_transitions` como sinais de
confiabilidade do rastreamento antes de "confiar" numa hipótese. Nenhuma dessas camadas foi
implementada aqui.

## Próximos passos

- Hypothesis Layer e Conviction Layer (fora de escopo, consumiriam `WorkingState`).
- Deduplicar eventos derivados de Enrichers sobrepostos (ex.: `MotionTransitionEnricher()`
  genérico + `MotionTransitionEnricher(entity_filter="ball")` juntos) por conteúdo, não só
  por `parent_event_id` — reabriria `worker/timeline/enrichment/`, precisaria de aprovação
  explícita.
- Estender `TrackMemory` (W32) com um sinal de presença mais rico (períodos de
  perda/recuperação com timestamps), se uma camada cognitiva futura precisar de "quantas
  vezes e quando esteve perdido", não só `recovery_count`.
- Nomenclatura (observação do usuário, sem impacto nesta sprint): `worker/perceptual_state/`
  poderia evoluir para `worker/state/`, abrigando `WorkingState`/`BeliefState`/
  `DecisionState` sob o mesmo domínio quando as camadas futuras existirem.
