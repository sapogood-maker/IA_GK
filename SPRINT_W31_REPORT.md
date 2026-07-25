# Sprint W31 — Perception Enrichment

## Objetivo

Camada de enriquecimento perceptivo entre a Perception Timeline (W28) e qualquer
inteligência futura: transformar eventos básicos em eventos perceptivos DERIVADOS
(transições de estado, padrões de frequência, correlações dentro do mesmo frame) — ainda
Percepção, não Cognição. Sem novo modelo, Detector, Analyzer, State Machine ou memória.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **Subpacote de `worker/timeline/`, não um 4º pacote irmão** — `worker/timeline/enrichment/`
   vive dentro da própria árvore da Timeline, sem tocar em nenhum dos 4 arquivos já
   existentes ali (`event.py`, `event_types.py`, `timeline.py`, `builder.py`).
2. **`Provenance`** — `source_event_ids: tuple[str, ...]` guarda TODOS os eventos de
   origem; `primary_parent_id` faz a ponte com `Event.parent_event_id` (schema da W28,
   intocado). `TrackRecoveryConfidenceEnricher` já usa 2 origens reais (o `TrackRecovered`
   + o `ObjectDetected` correlacionado) — primeira prova concreta do mecanismo.
3. **Densidade validada contra dado real** — ver Seção "Validação" abaixo.

## Arquivos criados (zero arquivos existentes alterados)

```
worker/timeline/enrichment/
├── __init__.py
├── event_types.py           # MotionStarted/Stopped, ObjectStationary, TrackStable/
│                              Unstable, TrackRecoveredWithConfidence, BallMotion*,
│                              GoalkeeperMovement*
├── provenance.py              # Provenance
├── entity_normalization.py      # normalize_entity_label ("sports ball" -> "ball")
├── enricher.py                    # Enricher (ABC)
├── registry.py                       # register_enricher/get_enricher_class/available_enrichers
├── factory.py                           # create_enricher(name, **params)
├── enrichers/
│   ├── motion_transitions.py             # MotionTransitionEnricher (Nivel 1)
│   ├── track_stability.py                 # TrackStabilityEnricher (Nivel 1)
│   ├── track_recovery.py                   # TrackRecoveryConfidenceEnricher (Nivel 1)
│   └── entity_correlation.py                # EntityCorrelationEnricher (Nivel 2 -
│                                              interface, NotImplementedError)
└── pipeline.py                                  # EnrichmentPipeline

tests/timeline/enrichment/  (52 testes novos)
├── test_provenance.py, test_entity_normalization.py
├── test_event_types_do_not_collide.py
├── test_motion_transitions.py, test_track_stability.py, test_track_recovery.py
├── test_entity_correlation.py, test_factory.py, test_pipeline.py
```

Nenhum arquivo de `worker/timeline/` (os 4 já existentes), `worker/explorers/`,
`worker/segments/`, `worker/inference/`, `worker/analyzers/`, `worker/domain/`,
`basic_vision_engine.py` foi alterado.

## Princípios obrigatórios — como cada um foi cumprido

- **Pipeline/PerceptionTimeline/Event intocados**: confirmado por diff — zero linhas
  alteradas fora de `worker/timeline/enrichment/`.
- **Enrichers só sob demanda**: nenhuma integração a `BasicVisionEngine`/`artifact.json`
  (mesmo espírito de W29/W30 — quarta vez consecutiva).
- **Independência entre Enrichers + mesma entrada original + sem encadeamento**:
  `EnrichmentPipeline.run()` chama `enricher.enrich(events)` para cada Enricher usando
  sempre o `events` original recebido — testado explicitamente
  (`test_each_enricher_receives_the_same_original_input`,
  `test_enrichers_never_see_each_others_derived_output`, com Enrichers stub gravando o
  que receberam e provando identidade de objeto, não só igualdade de valor).
- **Determinismo absoluto**: testado em unidade (`test_determinism_same_input_produces_same_output`)
  e validado contra o artifact real (2 execuções idênticas, ignorando `event_id`/uuid —
  ver Validação).

## Nível 1 implementado / Nível 2 só interface

- `MotionTransitionEnricher`: `MotionStarted`/`MotionStopped` (transição de `motion_state`),
  `ObjectStationary` (parado por `>= min_stationary_seconds`, com fechamento correto mesmo
  quando o track nunca volta a se mover até o fim da janela). Parametrizável por
  `entity_filter` — a MESMA classe produz `BallMotionStarted`/`Stopped` ou
  `GoalkeeperMovementStarted`/`Stopped`, não subclasses separadas.
- `TrackStabilityEnricher`: `TrackUnstable` (N disrupções numa janela deslizante),
  `TrackStable` (período limpo desde a última disrupção ou desde o início do track).
- `TrackRecoveryConfidenceEnricher`: `TrackRecoveredWithConfidence`, correlacionando
  `TrackRecovered` com `ObjectDetected` do MESMO frame — primeiro uso real de `Provenance`
  com 2 origens.
- `EntityCorrelationEnricher` (Nível 2): registrado para descoberta
  (`available_enrichers()`), mas `.enrich()` levanta `NotImplementedError` — confirmado por
  teste. Nenhuma lógica de correlação entre múltiplos frames implementada, como definido.

## Validação contra o artifact real (job `b07f0dc6`, W28/W30)

Composição não-redundante: `MotionTransitionEnricher()` genérico + `MotionTransitionEnricher(entity_filter="ball")`
+ `TrackStabilityEnricher()` + `TrackRecoveryConfidenceEnricher()`.

| | Valor estimado (documento) | Valor real (medido) |
|---|---|---|
| Densidade da Timeline base | ~107.900 eventos/min | **107.858 eventos/min** (34.095 eventos / 18,97s) |
| Eventos de enriquecimento | ~320 eventos (~1.015/min, ~1%) | **279 eventos (883/min, 0,82%)** |

A estimativa do documento (baseada nas contagens reais de `ObjectMoving`/`ObjectStopped`/
`TrackRecovered`/tracks) bateu na ordem de grandeza certa. Distribuição real por tipo:

```
MotionStopped: 81                 TrackUnstable: 27
MotionStarted: 79                 ObjectStationary: 14
TrackRecoveredWithConfidence: 63  BallMotionStopped: 8
                                   BallMotionStarted: 5
                                   TrackStable: 2
```

**Confirma a propriedade central do desenho**: eventos disparados por TRANSIÇÃO ficam ~2
ordens de grandeza abaixo da densidade da Timeline base (0,82%, não 100%) — o mecanismo de
contenção de crescimento (Seção 10-A do documento) funciona na prática, não só na teoria.

**Determinismo**: confirmado via 2 execuções do `EnrichmentPipeline` sobre o mesmo
`events` real — saída idêntica campo a campo (ignorando `event_id`, que é um uuid novo por
execução, propriedade já esperada desde a W28). Tempo de execução: ~16ms para os 34.095
eventos de entrada.

## Testes

52 testes novos, todos passando isoladamente. Suíte completa do Worker sem regressão nova
(632 passaram = 580 anteriores + 52 novos; mesmas 26 falhas/16 erros pré-existentes,
verificados sem nenhuma menção a enrichment/enricher/provenance).

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente do Worker. `PERCEPTION_ENGINE_ARCHITECTURE.md`
e o documento arquitetural da própria W31 documentam o raciocínio completo.

## Próximos passos

- Nível 2 (`entity_correlation.py`) fica para uma sprint futura, com estratégia explícita
  de desambiguação para múltiplas detecções do mesmo rótulo por frame.
- `BallMotionStrategy`/`TrackContinuityStrategy` (novas `SegmentStrategy`, W30) podem
  consumir `BallMotionStarted`/`Stopped` como critério de conteúdo — candidato a testar se
  resolve o achado do "segmento único" da W30 (hipótese registrada no documento
  arquitetural, ainda não testada).
- Decisão em aberto: estender o CLI da W29/W30 com `--enrich`.
