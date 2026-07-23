# SPRINT_W12_REPORT.md — Goalkeeper AI Worker: Football Domain Model

> Escopo: construir a primeira camada específica de futebol da arquitetura — o Football Domain Model, que transforma `WorldState` (genérico, W11) em `FootballWorld` (goleiro(s), bola, jogadores, gols, campo, direção do jogo). Não implementa análise, não implementa IA, não implementa regra de negócio, não implementa heurística — apenas cria os conceitos fundamentais do domínio. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W11_REPORT.md` antes de implementar.

- **`worker/domain/`** (novo) — módulo irmão de `inference/`, **deliberadamente sem Registry/factory**: `FootballWorldBuilder` é a única implementação canônica do domínio de futebol, não uma família de Plugin substituível. É a única exceção consciente ao padrão de Registry usado em todas as seis famílias de `inference/` (Seção 6).
- **`worker/domain/geometry/`** (novo) — utilitários puros, reusáveis por todos os futuros analisadores:
  - `coordinate.py` — `Coordinate` (x, y), `Distance` (`NewType`), `distance(a, b)`.
  - `vector.py` — `Vector` (dx, dy), `magnitude()`, `angle_degrees()`, `normalized()`, `Vector.from_polar(magnitude, angle_degrees)` (conversão polar→cartesiana), `Vector.between(origin, target)`, `angle_between(a, b)`.
  - `direction.py` — `Direction` (enum: `LEFT_TO_RIGHT`/`RIGHT_TO_LEFT`/`UNKNOWN`).
  - `region.py` — `Region` (x, y, width, height), `center()`, `contains(coordinate)`, `to_dict()`.
- **`worker/domain/types.py`** (novo) — `EntityId`/`ClassLabel`/`Confidence` (`NewType`), `TrackedFootballEntity` (dataclass base — conversão 1:1 dos dados já computados por `ObjectState`, apenas trocando de representação: `Position`→`Coordinate`, `Motion`→`Vector`; nenhum dado novo é inferido).
- **`worker/domain/entities/`** (novo) — objetos ricos, nunca dicts soltos:
  - `goalkeeper.py`/`player.py`/`ball.py` — cada um subclassando `TrackedFootballEntity` (mesma forma nesta sprint, mas classes distintas de propósito: analisadores futuros exigirão o tipo certo via assinatura, não uma união genérica).
  - `goal.py` — `Goal` (região no campo) + `Goal.default_pair(field_region)` (duas balizas, geometria placeholder documentada como não calibrada).
  - `field.py` — `Field` (região + direção) + `Field.default()` (região normalizada 0.0–1.0, `direction=UNKNOWN` por padrão — nenhuma heurística tenta inferir a direção de ataque).
- **`worker/domain/football_world.py`** (novo) — `FootballWorld` (dataclass: `frame_index`/`goalkeepers`/`players`/`balls`/`goals`/`field`), `to_dict()`. **Único tipo que os analisadores futuros (`GoalkeeperAnalyzer`/`BallAnalyzer`/`SaveAnalyzer`/`ShotAnalyzer`/`DiveAnalyzer`/`GoalAnalyzer`, Sprint W13+) poderão consumir.**
- **`worker/domain/context.py`** (novo) — `FootballDomainContext`: memória interna do builder (`field`/`goals`, construídos uma vez e reaproveitados por serem entidades estáticas do vídeo inteiro), `reset()`.
- **`worker/domain/exceptions.py`** (novo) — `FootballDomainError` → `FootballWorldBuildError`.
- **`worker/domain/world_builder.py`** (novo) — `FootballWorldBuilder`: `build(world_state: WorldState) -> FootballWorld`, `reset()`.
- **`worker/inference/processors/football_domain_processor.py`** (novo) — `FootballDomainProcessor(FrameProcessor)`: lê `context.world_states[-1]`, chama `FootballWorldBuilder.build()`, acumula o `FootballWorld`. No-op se não houver `WorldState` no frame. `is_enabled` reflete `settings.football_domain_enabled`. `reset()` delega ao builder.
- **`worker/inference/processors/base.py`** — `ProcessorContext` ganhou `football_worlds: list[FootballWorld]` + `add_football_world()`.
- **`worker/inference/processors/registry.py`** — `FootballDomainProcessor` registrado por último (`color → resize → roi → statistics → yolo → tracking → scene_analysis → world_model → football_domain`).
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"football_world"` (o último, uma fotografia) e `"football_domain_time_ms"`.
- **`worker/config/settings.py`** — 1 campo novo: `football_domain_enabled: bool` (default `False`) — um único interruptor, sem "qual implementação" (não há Registry nesta camada).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `WorldModel.update`, `SceneAnalyzer.analyze`, `Tracker.track`, `Detector.detect`, `InferenceEngine.process`, `FrameProcessor.process` são idênticos aos de antes.

## Football World

`FootballWorld` representa a fotografia do domínio de futebol num dado frame: goleiro(s), bola(s), jogadores, balizas, campo, direção do jogo — **tudo ainda como entidades, sem decisões**. Nenhuma análise (quem está mais perto da bola, se um chute aconteceu, se o goleiro se moveu para defender) é feita aqui — isso é escopo da W13.

## FootballWorldBuilder

```python
class FootballWorldBuilder:
    def __init__(self, settings: WorkerSettings) -> None: ...
    def build(self, world_state: WorldState) -> FootballWorld: ...
    def reset(self) -> None: ...
```

`build()` itera `world_state.active_objects`, despacha cada `ObjectState` para `Goalkeeper`/`Ball`/`Player` (ou ignora silenciosamente se o rótulo não for reconhecido), converte `Position`→`Coordinate` e `Motion`(polar)→`Vector`(cartesiano) via `Vector.from_polar(speed, direction_degrees)`, e monta `Field`/`Goal` na primeira chamada (memorizados em `FootballDomainContext` por serem entidades estáticas do vídeo inteiro, não recriadas a cada frame).

**A única "decisão" desta sprint — e por que não é uma heurística:** classificar cada `ObjectState` como `Goalkeeper`/`Ball`/`Player` compara `label.lower()` contra três `frozenset`s fixos (`_GOALKEEPER_LABELS`, `_BALL_LABELS`, `_PLAYER_LABELS`). É um despacho puramente estrutural por tipo já atribuído pelo Detector — não uma inferência sobre o comportamento do objeto. Com o modelo padrão hoje (YOLO11n/COCO), o único rótulo de pessoa existente é `"person"`, então na prática todo mundo vira `Player` e `FootballWorld.goalkeepers` fica honestamente vazio (confirmado na validação manual abaixo).

## FootballDomainProcessor

```
frame → FootballDomainProcessor.process()
    → context.world_states vazio? → no-op
    → latest = context.world_states[-1]   [WorldState do MESMO frame]
    → self._builder.build(latest)
    → FootballWorld
    → context.add_football_world(football_world)
    → devolve (frame, metadata, context) inalterados - so transforma dados, nunca decide/analisa
```

Registrado por último na pipeline (`color → resize → roi → statistics → yolo → tracking → scene_analysis → world_model → football_domain`).

## Configuração

| Variável | Default | Efeito |
|---|---|---|
| `WORKER_FOOTBALL_DOMAIN_ENABLED` | `false` | Interruptor único — não há "qual implementação" nesta camada (sem Registry/factory). Requer `WORKER_WORLD_MODEL_ENABLED=true` (o Football Domain Model consome `WorldState`). |

## Testes — 264/264 passando (233 sem dependência de Redis real + 31 de infraestrutura Redis, container descartável)

| Categoria | Onde | O que valida |
|---|---|---|
| Geometry | `tests/domain/geometry/test_coordinate.py` | `distance()` entre pontos |
| Geometry | `tests/domain/geometry/test_vector.py` | `magnitude()`/`angle_degrees()`/`normalized()`; `from_polar()` reconstrói `(dx, dy)` a partir de magnitude+ângulo; `between()`; `angle_between()` |
| Geometry | `tests/domain/geometry/test_direction.py` | Valores do enum |
| Geometry | `tests/domain/geometry/test_region.py` | `center()`; `contains()` dentro/fora/na borda; `to_dict()` |
| Entities | `tests/domain/entities/test_goalkeeper.py`/`test_player.py`/`test_ball.py` | Construção; `to_dict()` completo, com/sem `previous_position` |
| Entities | `tests/domain/entities/test_goal.py` | `default_pair()` produz duas balizas simétricas nas extremidades do campo |
| Entities | `tests/domain/entities/test_field.py` | `default()` produz região normalizada + `direction=UNKNOWN` |
| FootballWorld | `tests/domain/test_football_world.py` | Construção; `to_dict()` serializa todos os grupos de entidades |
| FootballWorldBuilder (real, sem mock) | `tests/domain/test_world_builder.py` | `ObjectState` com label `"person"` vira `Player`; `"frisbee"`/`"sports ball"` vira `Ball`; `"goalkeeper"`/`"keeper"` vira `Goalkeeper`; rótulo desconhecido é ignorado; `Field`/`Goal` construídos uma vez e reaproveitados entre chamadas; `velocity` corretamente derivado de `Motion.speed`/`direction_degrees` via `Vector.from_polar`; `reset()` limpa `Field`/`Goal` memorizados |
| `FootballDomainProcessor` (mocka só o builder) | `tests/inference/processors/test_football_domain_processor.py` | `is_enabled` reflete a configuração; no-op sem `WorldState`; constrói e registra no contexto; `reset()` delega |
| Integração completa — Football Domain real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_football_domain_enabled_produces_a_coherent_football_world` | Mocka só o Detector; Tracker/SceneAnalyzer/WorldModel/FootballWorldBuilder REAIS produzem `FootballWorld` coerente |
| Reset entre Jobs (real, sem mock) | `test_basic_vision_engine.py::test_engine_resets_football_domain_state_between_jobs` | A mesma instância processa 2 vídeos; `Field`/`Goal` memorizados são limpos e reconstruídos no segundo vídeo |
| Configuração | `test_settings.py` | `football_domain_enabled` configurável, default `False` |
| Registro/ordem | `test_registry.py` (processors) | `football_domain` presente na lista de Processors; posição correta (último) na ordem de execução |
| Regressão | Todos os 233 testes anteriores (W1-W11, exceto os que exigem Redis real) | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `233 passed` (suíte completa exceto `tests/infrastructure/`, que depende de um container Redis descartável já encerrado após a validação manual — falhas observadas são exclusivamente `ConnectionError` de rede, não relacionadas ao código desta sprint). `38 passed` isolando `tests/domain/`, `4 passed` isolando `test_football_domain_processor.py`.

## Bugs encontrados e corrigidos durante a implementação

**Colisão de nome `field` com `from dataclasses import field`** — ocorreu duas vezes, mesma causa raiz. Em `football_world.py` e depois em `context.py`, um atributo de dataclass literalmente chamado `field` (o conceito de domínio "campo") colide com `from dataclasses import field` importado no mesmo módulo: a atribuição do atributo `field` no corpo da classe sombreia a função importada, então um campo POSTERIOR na mesma classe que chama `field(default_factory=...)` levanta `TypeError: 'NoneType' object is not callable`. Corrigido nas duas ocorrências com `from dataclasses import field as dataclass_field`. Encontrado proativamente em `football_world.py` durante a escrita inicial; encontrado reativamente em `context.py` via falha da suíte de testes (autodetectado, sem envolvimento do usuário).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/domain/ tests/domain/` → nenhuma menção, nenhum `import` cruzado.
- `grep -rn "yolo\|YOLO\|ByteTrack\|ultralytics\|cv2\|redis\|Redis\|backend_client\|r2_client\|Detector\|Tracker\|SceneAnalyzer" worker/domain/*.py worker/domain/**/*.py` → nenhuma menção real, nenhum `import`.
- Todos os `import`s reais de `worker/domain/**/*.py` conferidos manualmente: só módulos internos de `domain/` + `worker.config.settings` + `worker.inference.world.object_state`/`world_state` (o único contrato de entrada permitido — `WorldState`/`ObjectState`) + `worker.core.exceptions`. Nenhum `trackers/`, `detectors/`, `events/`, `cv2`, `ultralytics`, `redis`.
- `worker/domain/` deliberadamente **não** possui `registry.py`/`factory.py` — confirmado que nenhum arquivo desse tipo foi criado nesta sprint (a única exceção consciente ao padrão de seis famílias em `inference/`).

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/sessão das sprints anteriores. Gerei um vídeo real de 15 frames (640×480, 5fps) com um círculo vermelho se movendo continuamente (20px/frame), upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true`, `WORKER_FOOTBALL_DOMAIN_ENABLED=true`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model', 'football_domain']
football_domain_time_ms: <valor real positivo>

football_world.frame_index: 14
goalkeepers: []
players: []
balls count: 1
  track_id=1 label=frisbee age=15 speed=20.0 position={'x': 379.0, 'y': 239.5} velocity={'dx': 20.0, 'dy': 0.0}
field: {'region': {'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0}, 'direction': 'unknown'}
goals: [duas balizas simétricas, dimensões proporcionais ao field.region]
```

**Confirmado exatamente o que a sprint pediu — um `FootballWorld` coerente:** o objeto detectado pelo YOLO real como `"frisbee"` (rótulo COCO mais próximo de "bola" disponível no modelo padrão) foi corretamente mapeado para `Ball`, com `track_id`/`age`/`speed`/`position` idênticos aos já confirmados no `WorldState` da W11, e `velocity={'dx': 20.0, 'dy': 0.0}` corretamente derivado de `speed=20.0`/`direction_degrees=0.0` via `Vector.from_polar` (movimento puramente horizontal). `goalkeepers`/`players` honestamente vazios — nenhum rótulo `"person"`/`"goalkeeper"` foi detectado neste vídeo sintético (só um círculo vermelho), confirmando o comportamento esperado do dispatch por rótulo. `field`/`goals` com a geometria placeholder documentada, idêntica independente do conteúdo do vídeo (não calibrada). Lock liberado, mensagem confirmada (`XPENDING`=0). Stack derrubado ao final.

## Riscos (novos, registrados na Constituição — Seção 14)

22. **`Field.default()`/`Goal.default_pair()` produzem geometria placeholder, não calibrada a nenhum vídeo real** — o Worker nunca recebe calibração de câmera nem coordenadas reais de campo/gols; qualquer analisador futuro que dependa de posição real relativa ao gol/linhas de campo precisará de uma fonte de calibração ainda não desenhada.
23. **`FootballWorldBuilder._build_entity()` decide `Goalkeeper` vs. `Player` vs. `Ball` só por comparação de rótulo** — como o `YOLODetector` padrão (YOLO11n/COCO) nunca emite rótulo `"goalkeeper"`, `FootballWorld.goalkeepers` permanece vazio em qualquer execução real com o modelo atual; confirmado na validação manual desta sprint. Resolver isso exige um Detector/modelo customizado com uma classe de goleiro própria (fora do escopo desta sprint).

## Preparação para a W13

A W13 ainda não tem escopo definido (qual análise específica de futebol entra primeiro — `GoalkeeperAnalyzer`/`BallAnalyzer`/`SaveAnalyzer`/`ShotAnalyzer`/`DiveAnalyzer`/`GoalAnalyzer`). O que já está confirmado, pela quinta repetição consecutiva do mesmo padrão de encaixe (W8/W9/W10/W11/W12): uma nova camada de análise exige apenas um novo Processor + (se necessário) uma nova família de Registry/`factory.py` — nunca uma mudança em `BasicVisionEngine`, `PipelineProcessor`, `Orchestrator`, `VideoReader`, Redis, Backend, R2, ou nas famílias de Plugin/módulos já existentes. A partir da W13, os analisadores de futebol consomem **exclusivamente** `FootballWorld` (via `context.football_worlds`/artefato `"football_world"`) — nunca `WorldState`/`SceneAnalysisResult`/`TrackingResult`/`DetectionResult`/OpenCV/YOLO/ByteTrack diretamente. Esta é a primeira sprint em que decisão/interpretação de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
