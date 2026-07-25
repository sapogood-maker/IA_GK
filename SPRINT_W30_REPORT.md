# Sprint W30 — Play Segmentation

## Objetivo

Camada intermediária entre a Perception Timeline (W28) e qualquer inteligência futura:
agrupar milhares de `Event`s em segmentos de jogada (`PlaySegment`) — L9 de
`PERCEPTION_ENGINE_ARCHITECTURE.md`. Sem memória cognitiva, sem state machine, sem modelo/
Detector/Analyzer novo — puramente estrutural.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **`SegmentStrategy`** — a decisão de ONDE cortar não fica acoplada a "silêncio
   perceptivo". Contrato próprio (`SegmentStrategy.find_boundaries`), com Registry/Factory
   espelhando **byte a byte** o padrão já usado por Detector/Tracker/SceneAnalyzer/
   WorldModel/Analyzer. Só `GapStrategy` implementada nesta sprint; futuras estratégias
   (continuidade de track, continuidade da bola, composta) só implementam o contrato e se
   registram — zero mudança em `PlaySegmenter`/`PlaySegment`.
2. **`PlaySegment` sem `summary`** — estrutura puramente de dados. Geração de texto humano
   vive no CLI (`_describe_segment`, privada), nunca em `PlaySegment` nem em
   `TimelineExplorer` — evita inverter a direção de dependência (W29 nunca passa a
   conhecer W30).
3. **`--segments`/`--max-gap` no CLI da W29** — confirmado pelo usuário.

## Arquivos criados

```
worker/segments/
├── __init__.py
├── play_segment.py     # PlaySegment (dataclass, frozen, sem summary)
├── strategy.py           # SegmentStrategy (ABC)
├── gap_strategy.py         # GapStrategy - unica implementacao
├── registry.py               # register_strategy/get_strategy_class/available_strategies
├── factory.py                   # create_strategy(name, **params)
└── segmenter.py                    # PlaySegmenter(strategy).segment(explorer)

tests/segments/
├── __init__.py
├── test_play_segment.py
├── test_gap_strategy.py
└── test_segmenter.py
```

## Arquivos alterados (2, ambos aditivos)

- `worker/explorers/timeline_explorer.py`: **um método novo**, `by_frame_range(start, end)`
  (mesma família de `by_time_range`, por índice de frame) — usado pelo `PlaySegmenter` em
  vez de reimplementar filtragem.
- `worker/explorers/cli.py`: flags `--segments`/`--max-gap` + função privada
  `_describe_segment` (geração de texto do resumo, fora de `PlaySegment`).

Nenhuma mudança em `worker/timeline/`, `basic_vision_engine.py`, Processors, Analyzers,
Registry/Factory de qualquer camada anterior.

## Algoritmo (`GapStrategy`)

Fecha um segmento quando o gap de tempo entre dois eventos de "conteúdo" consecutivos
(`ObjectDetected`/`TrackStarted`/`TrackUpdated`/`TrackRecovered`) excede `max_gap_seconds`
(default 1.0s, configurável). `FrameProcessed` sozinho nunca decide fronteira. Eventos sem
timestamp nunca cortam ali (mesma filosofia de "não decidir sem dado" já usada em outros
Analyzers).

## Testes

- 22 testes novos (`tests/segments/` + extensões em `tests/explorers/`) — cobrindo timeline
  vazia, segmento único, múltiplos segmentos por gap, eventos sem timestamp, tipos de
  conteúdo customizáveis, `track_ids`/`ball_involved`/`duration` corretos, imutabilidade,
  `to_dict()` sem campo `summary`, e as duas flags novas do CLI.
- Suíte completa sem regressão (56 novos + baseline anterior).

## Validação manual — achado real, não um bug

Rodei `--segments` contra o `artifact.json` real da W28 (job `b07f0dc6`, 34.095 eventos,
569 frames): **um único segmento cobrindo o vídeo inteiro (frames 0-568), mesmo com
`--max-gap 0.2`**. Causa: o YOLO genérico (COCO) detectou pelo menos um objeto em **todos
os 569 frames** desse vídeo (já confirmado na auditoria da camada de IA) — nunca há gap
real entre eventos de conteúdo neste clipe específico. Não é um defeito da `GapStrategy`:
é a limitação já conhecida do detector genérico se refletindo, agora visível, na
segmentação. Fica documentado como acompanhamento para quando o Detector for fine-tunado
(W37 do roadmap) ou quando uma estratégia baseada especificamente em presença/ausência da
bola for adicionada.

## Próximos passos

W31+ (State Machine, rewire de Analyzers cognitivos) pode consumir `PlaySegment` como
unidade de análise em vez de frame isolado — nenhuma mudança estrutural adicional deveria
ser necessária em `worker/segments/` para isso.
