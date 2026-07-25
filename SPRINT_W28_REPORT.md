# Sprint W28 — Perception Engine: Event Timeline (fundação temporal)

## Objetivo

Primeira sprint da evolução "Perception Engine" (`PERCEPTION_ENGINE_ARCHITECTURE.md`,
documento oficial de arquitetura). Criar a infraestrutura temporal — uma sequência
imutável e append-only de fatos de percepção (`Event`s) — sem tocar em cognição, memória,
state machine, play segmentation ou coaching (fora de escopo, por instrução explícita).

## Decisão de desenho

`ProcessorContext` (`worker/inference/processors/base.py`) já acumula, frame a frame, todo
o dado necessário (`detections`, `scene_analysis_results`, `analysis_results` — inclusive de
TODOS os frames, não só o último). A Event Timeline é, portanto, **inteiramente derivada**:
uma função pura (`build_timeline`) lê o `ProcessorContext` já preenchido, uma única vez,
após o loop de frames de `BasicVisionEngine.process()` terminar. Nenhum
Detector/Tracker/SceneAnalyzer/WorldModel/FootballDomain/Analyzer/Registry/Factory/
Pipeline/Rule Evaluation foi alterado.

## Arquivos criados

```
worker/timeline/
├── __init__.py
├── event_types.py   # constantes de tipo de evento (subconjunto viável, sem inventar
│                     # inteligência nova - ver justificativa no docstring)
├── event.py          # Event (frozen dataclass) - event_id, parent_event_id, imutável
├── timeline.py        # PerceptionTimeline - log append-only, sem update/remove
└── builder.py          # build_timeline() - toda a tradução ProcessorContext -> Events

tests/timeline/
├── __init__.py
├── test_event.py       # imutabilidade, event_id único, parent_event_id, to_dict
├── test_timeline.py     # append/extend/ordenação/API restrita a append+extend+to_dict
└── test_builder.py       # tradução de cada fonte (detections/scene/analyzer), duck-typing
                           # de RuleEvaluated, determinismo
```

## Arquivo alterado (um único)

`worker/inference/basic_vision_engine.py`: um import novo + duas linhas
(`build_timeline(...)` + `payload["event_timeline"] = ...`), no mesmo ponto onde toda
chave de conveniência já existente é escrita. Nenhuma linha existente removida/alterada.

## Revisões incorporadas (pedidas na aprovação do plano)

1. **Nome**: `EventTimeline` → `PerceptionTimeline` (a estrutura deve crescer para carregar
   contexto temporal mais amplo, não só eventos discretos — W29/W32).
2. **Schema**: `event_id` (uuid4, único) e `parent_event_id` (opcional) adicionados.
   Usado de verdade nesta sprint: todo `RuleEvaluated` referencia o `event_id` do
   `AnalyzerFinished` correspondente via `parent_event_id`.
3. **Imutabilidade**: `Event` é `frozen=True` (`FrozenInstanceError` real, testado).
   `PerceptionTimeline` só expõe `append`/`extend`/`to_dict` — testado explicitamente que
   nenhum outro método público existe.

## Tipos de evento implementados

`FrameProcessed`, `ObjectDetected`, `PersonDetected`, `BallDetected` (de
`context.detections`); `TrackStarted`/`TrackUpdated`/`TrackLost`/`TrackRecovered`/
`ObjectEnteredRegion`/`ObjectLeftRegion`/`ObjectStopped`/`ObjectMoving`/`OcclusionDetected`
(adaptados 1:1 de `SceneEventType`, já existente); `AnalyzerStarted`/`AnalyzerFinished`
(sintetizados de `AnalyzerMetadata.processing_time_ms`); `RuleEvaluated` (duck-typing sobre
`rules_evaluated`/`rules_passed`/`rules_failed`, presentes só nos Analyzers de Rule
Evaluation — W23+).

Deliberadamente fora desta sprint: `GoalkeeperCandidateDetected`, `GoalDetected` como tipos
próprios, e `SceneChanged` — decidir essas heurísticas já seria "melhorar a IA" (proibido
nesta sprint); ficam para quando os Analyzers cognitivos passarem a alimentar a Timeline
(W33).

## Testes

- 21 testes novos em `tests/timeline/` — 100% passando, isolados (sem vídeo/YOLO/Redis).
- 1 teste de integração novo em `tests/inference/test_basic_vision_engine.py`
  (`test_engine_produces_a_coherent_event_timeline`) — vídeo real + Tracker/SceneAnalyzer
  reais, confirma que `event_timeline` aparece no artifact SEM que nenhuma chave existente
  mude, e que a Timeline é coerente com `detection_results`/`scene_events` já reportados
  separadamente. Passando isolado e dentro do arquivo completo.

### Suíte completa (`pytest tests/`)

524 passaram, 26 falharam, 16 erros — **nenhuma dessas falhas/erros pertence a
`tests/timeline/` ou ao novo teste de `basic_vision_engine`** (confirmado via grep no
output completo). Investiguei a causa raiz de uma delas
(`tests/infrastructure/test_redis_health.py`) e é um Redis de teste descartável esperado na
porta `6381` (não a `6379` do stack de dev), que não está rodando neste ambiente — nada
relacionado a esta sprint (não toquei em `worker/infrastructure/`).

Validei rigorosamente, via `git stash`/`stash pop`, que **as mesmas 7 falhas em
`test_basic_vision_engine.py`** (um problema de isolamento de teste pré-existente,
dependente de ordem de execução) já ocorrem no commit `d9bbd6d`, antes de qualquer mudança
desta sprint — não é uma regressão introduzida pela W28.

## Compatibilidade

- Todo campo existente do artifact permanece idêntico. `event_timeline` é chave nova.
- Nenhuma assinatura pública mudou (`Detector`, `Tracker`, `SceneAnalyzer`, `WorldModel`,
  `FootballDomainProcessor`, `Analyzer`, `FrameProcessor`, `ProcessorContext`,
  `PipelineProcessor`, `Registry`/`Factory` de cada camada).
- `worker/events/events.py` (Event System de ciclo de vida do Job) não foi tocado.
- Nenhuma variável de ambiente nova.

## Próximos passos (roadmap, não desta sprint)

W29 (Track History completo) e W30 (Play Segmentation) consomem diretamente a
`PerceptionTimeline` criada aqui — nenhuma mudança estrutural adicional deveria ser
necessária nela para isso.
