# SPRINT_W13_REPORT.md — Goalkeeper AI Worker: Analyzer API + GoalkeeperPresenceAnalyzer

> Escopo: construir a infraestrutura da Analyzer API — a primeira camada que RESPONDE perguntas sobre o domínio de futebol — e um primeiro Analyzer extremamente simples e determinístico, `GoalkeeperPresenceAnalyzer`. Ainda **sem** Save/Shot/Dive/Goal Analyzer, pose estimation, MediaPipe ou classificação de desempenho. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W12_REPORT.md` antes de implementar.

- **`worker/analyzers/`** (novo) — pacote de topo, **irmão de `worker/domain/` e de `inference/`**, não um submódulo de nenhum dos dois:
  - **`base.py`** — `Analyzer` (ABC): contrato único `analyze(football_world: FootballWorld) -> AnalysisResult` + `reset()` (concreto, default no-op). `Analyzer` conhece apenas `FootballWorld` — nunca `WorldState`, `SceneAnalysisResult`, `TrackingResult`, `DetectionResult`, OpenCV, YOLO, ByteTrack, Redis, Backend ou R2.
  - **`types.py`** — `AnalyzerName`/`AnalyzerVersion` (`NewType`).
  - **`exceptions.py`** — `AnalyzerError` → `AnalyzerInitializationError`/`AnalyzerExecutionError`.
  - **`results.py`** — `AnalyzerMetadata` (analyzer_name/analyzer_version/processing_time_ms), `AnalysisResult` (base: frame_index + metadata), `GoalkeeperPresenceResult(AnalysisResult)` (exists/visible/goalkeeper_count/track_id/age/current_position/current_bbox), `AnalysisStatistics` (analyzers_run/results_count). Tipos fortemente tipados, nunca listas de dicionários soltos.
  - **`goalkeeper_presence.py`** — `GoalkeeperPresenceAnalyzer(Analyzer)`: primeira implementação real.
  - **`context.py`** — `AnalyzerContext`: classe-base vazia, reservada para Analyzers futuros com estado.
  - **`registry.py`**/**`factory.py`** — `register_analyzer`/`get_analyzer_class`/`available_analyzers()`, `create_analyzer(nome, settings)`. Sétima família de Registry paralela.
  - **`processor.py`** — `AnalyzerProcessor(FrameProcessor)`: a ponte com a pipeline (registrada em `inference/processors/registry.py`, não vive lá).
- **`worker/inference/processors/base.py`** — `ProcessorContext` ganhou `analysis_results: list[AnalysisResult]` + `add_analysis_result()`.
- **`worker/inference/processors/registry.py`** — importa `AnalyzerProcessor` de `worker.analyzers.processor`, registrado por último (`color → resize → roi → statistics → yolo → tracking → scene_analysis → world_model → football_domain → analyzer`).
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"analysis_results"` (dict `analyzer_name → AnalysisResult.to_dict()`), `"analysis_statistics"`, `"analyzer_processing_time_ms"`.
- **`worker/config/settings.py`** — 1 campo novo: `analyzers: str` (default `""`, lista separada por vírgula) + propriedade `analyzer_names -> list[str]`.
- **`worker/domain/types.py`** — `TrackedFootballEntity` ganhou `bbox: Region` (achado necessário, ver abaixo).
- **`worker/domain/world_builder.py`** — `_build_entity()` populada com `bbox=Region(x=obj.bbox.x, y=obj.bbox.y, width=obj.bbox.width, height=obj.bbox.height)`.

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** (além da extensão aditiva `bbox` em `TrackedFootballEntity`, ver abaixo) — `WorldModel.update`, `SceneAnalyzer.analyze`, `Tracker.track`, `Detector.detect`, `InferenceEngine.process`, `FrameProcessor.process`, `FootballWorldBuilder.build` são idênticos aos de antes.

## Achado arquitetural necessário: `bbox` em `TrackedFootballEntity`

`GoalkeeperPresenceAnalyzer` precisa responder "qual o bounding box atual?", mas `FootballWorld`/suas entidades (W12) só carregavam `position` (o centro do objeto) — nenhuma caixa delimitadora. Mesma classe de achado do `SceneObjectSnapshot` (W11): uma extensão ADITIVA de um contrato de camada inferior, necessária para que a camada de cima (aqui, o Analyzer) responda à pergunta sem violar o Boundary Enforcement (`Analyzer` só conhece `FootballWorld`, nunca `ObjectState`).

Resolvido adicionando `bbox: Region` a `TrackedFootballEntity` (`worker/domain/types.py`), **reaproveitando `Region`** (já existente para `Field`/`Goal`, Seção 6.4) em vez de introduzir um tipo `BoundingBox` próprio do domínio — uma caixa delimitadora é estruturalmente idêntica a uma região. `FootballWorldBuilder._build_entity()` populada com `Region(x=obj.bbox.x, y=obj.bbox.y, width=obj.bbox.width, height=obj.bbox.height)` a partir do `ObjectState.bbox`, que já existia desde a W11. Todos os testes de domínio pré-existentes (W12) foram atualizados para incluir o novo campo obrigatório; validado que os 39 testes de `tests/domain/` continuam passando após a extensão, mais 1 teste novo confirmando o mapeamento `bbox`.

## Analyzer API

```python
class Analyzer(ABC):
    name: str
    version: str
    def __init__(self, settings: WorkerSettings) -> None: ...
    def analyze(self, football_world: FootballWorld) -> AnalysisResult: ...
    def reset(self) -> None: ...  # concreto, default no-op
```

`create_analyzer(nome, settings)` resolve um Analyzer específico a partir do seu nome, espelhando `create_world_model`. **Diferença central desta família:** em todas as anteriores (Detector/Tracker/SceneAnalyzer/WorldModel), só UMA implementação fica ativa por vez, resolvida por `WORKER_X=nome`. Aqui, `WORKER_ANALYZERS` é uma **lista** separada por vírgula — vários Analyzers coexistem simultaneamente, cada um respondendo uma pergunta independente sobre o MESMO `FootballWorld`, não são substitutos uns dos outros. Por isso um único campo de lista já basta como interruptor (vazio = desabilitado) — não há necessidade do par `WORKER_X`/`WORKER_X_ENABLED` usado pelas famílias anteriores.

## GoalkeeperPresenceAnalyzer

Responde, sem heurística/regra de futebol/avaliação/julgamento — totalmente determinístico:

| Pergunta | Campo | Fonte |
|---|---|---|
| Existe um goleiro? | `exists` | `len(football_world.goalkeepers) > 0` |
| Quantos goleiros existem? | `goalkeeper_count` | `len(football_world.goalkeepers)` |
| Qual TrackId representa o goleiro? | `track_id` | primeiro da lista (ver abaixo) |
| O goleiro está visível? | `visible` | `entity.active` |
| Há quantos frames ele existe? | `age` | `entity.age` |
| Qual a posição atual? | `current_position` | `entity.position` |
| Qual o bounding box atual? | `current_bbox` | `entity.bbox` (achado desta sprint) |

Quando `FootballWorld.goalkeepers` tem mais de um candidato (o Football Domain Model, W12, nunca desambigua "qual É o goleiro de verdade"), esta implementação escolhe deterministicamente o **primeiro** da lista — uma regra de ordem, não uma heurística comportamental. Sem goleiro algum, todos os campos opcionais são `None`/`False`/`0`.

## AnalyzerProcessor

```
frame → AnalyzerProcessor.process()
    → context.football_worlds vazio? → no-op
    → latest = context.football_worlds[-1]   [FootballWorld do MESMO frame]
    → para CADA Analyzer ativo: analyzer.analyze(latest) → AnalysisResult
    → context.add_analysis_result(result)  (uma vez por Analyzer)
    → devolve (frame, metadata, context) inalterados - so analisa, nunca detecta/rastreia/interpreta/transforma/decide
```

Registrado por último na pipeline (`color → resize → roi → statistics → yolo → tracking → scene_analysis → world_model → football_domain → analyzer`).

## Configuração

| Variável | Default | Efeito |
|---|---|---|
| `WORKER_ANALYZERS` | `""` (vazio) | Nomes dos Analyzers ativos, separados por vírgula (ex.: `goalkeeper_presence`). Vazio = `AnalyzerProcessor` desabilitado. Requer `WORKER_FOOTBALL_DOMAIN_ENABLED=true` (todo Analyzer consome `FootballWorld`). |

## Testes — 259/259 passando (233 sem dependência de Redis real, na baseline pré-W13, mais 26 novos; mais 31 de infraestrutura Redis, container descartável)

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `AnalyzerMetadata.to_dict()`; `AnalysisResult` base; `GoalkeeperPresenceResult.to_dict()` com/sem goleiro; `AnalysisStatistics.to_dict()` |
| Registry | `tests/analyzers/test_registry.py` | `GoalkeeperPresenceAnalyzer` registrado; registrar um novo o disponibiliza |
| Factory | `tests/analyzers/test_factory.py` | Nome desconhecido levanta exceção; falha de init é envolvida; resolve `goalkeeper_presence` |
| `GoalkeeperPresenceAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_presence.py` | Sem goleiro (todos campos `None`/`False`/`0`); com goleiro visível; goleiro presente mas não visível (`active=False`); múltiplos candidatos → primeiro escolhido deterministicamente; metadata correta |
| `AnalyzerProcessor` (real, sem mock) | `tests/analyzers/test_processor.py` | `is_enabled` reflete `analyzer_names`; no-op sem FootballWorld; analisa e registra no contexto; múltiplos Analyzers ativos cada um produz um resultado; `reset()` delega a cada Analyzer ativo |
| Domínio — extensão `bbox` | `tests/domain/entities/test_{goalkeeper,player,ball}.py`, `tests/domain/test_football_world.py`, `tests/domain/test_world_builder.py` | Todos atualizados para o novo campo obrigatório; novo teste confirma `bbox` mapeado corretamente de `ObjectState.bbox` |
| Registro/ordem | `tests/inference/processors/test_registry.py` | `analyzer` presente; ordem `[...,"football_domain","analyzer"]` |
| Configuração | `tests/test_settings.py` | `analyzers`/`analyzer_names` default vazio; parsing de múltiplos nomes separados por vírgula (com espaços/entradas vazias ignoradas) |
| Integração completa — Analyzer real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_analyzers_enabled_produces_a_coherent_goalkeeper_presence_result` | Mocka só o Detector (rótulo `"goalkeeper"`); Tracker/SceneAnalyzer/WorldModel/FootballDomain/Analyzer REAIS produzem um `GoalkeeperPresenceResult` coerente dentro de `analysis_results` |
| Reset entre Jobs (real, sem mock) | `test_basic_vision_engine.py::test_engine_resets_analyzer_state_between_jobs` | A mesma instância processa 2 vídeos; `age` reportado reinicia em 2, não continua 4 |
| Regressão | Todos os 233 testes anteriores (W1-W12, exceto os que exigem Redis real) | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `259 passed` (suíte completa exceto `tests/infrastructure/`, que depende de um container Redis descartável já encerrado após a validação manual anterior).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/analyzers/ tests/analyzers/` → nenhuma menção, nenhum `import` cruzado.
- `grep -rn "yolo\|YOLO\|ByteTrack\|ultralytics\|cv2\|redis\|Redis\|backend_client\|r2_client\|WorldState\|SceneAnalysisResult\|TrackingResult\|DetectionResult" worker/analyzers/*.py` → só menções em docstring explicando o que `Analyzer` NÃO conhece. Nenhum `import` real.
- Todos os `import`s reais de `worker/analyzers/*.py` conferidos manualmente: só stdlib (`time`/`dataclasses`/`typing`/`abc`) + `worker.config.settings` + `worker.core.exceptions` + `worker.domain.football_world`/`worker.domain.types`/`worker.domain.geometry.*` (o único ponto de entrada permitido) + `worker.inference.processors.base` (`FrameProcessor`/`ProcessorContext` — o contrato genérico do pipeline, não uma camada de IA concreta) + módulos internos de `worker.analyzers.*`. Nenhum `worker.inference.detectors`/`trackers`/`events`/`world`, `cv2`, `ultralytics`, `redis`, `worker.infrastructure.*`.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend via `docker compose up --build`), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores (`treinador-w7@example.com`, sessão `a19f2913-5aa2-4582-842e-47b9508d1b8e` — senha redefinida diretamente no banco via hash bcrypt real, já que a senha original não estava documentada). Gerei um vídeo real de 15 frames (640×480, 5fps) com um círculo vermelho se movendo continuamente (20px/frame), upload real via `httpx` multipart, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true`, `WORKER_FOOTBALL_DOMAIN_ENABLED=true`, `WORKER_ANALYZERS=goalkeeper_presence`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model', 'football_domain', 'analyzer']
analysis_statistics: {'analyzers_run': ['goalkeeper_presence'], 'results_count': 1}

goalkeeper_presence result:
  frame_index: 14
  exists: False
  visible: False
  goalkeeper_count: 0
  track_id: None
  age: None
  current_position: None
  current_bbox: None

football_world.balls: [{track_id=1, label=frisbee, age=15, speed=20.0, bbox={...}}]
football_world.goalkeepers: []
```

**Confirmado exatamente o que era esperado, honestamente:** o objeto real detectado pelo YOLO (um círculo vermelho) foi classificado como `"frisbee"` → `Ball`, não como pessoa/goleiro — mesma limitação já documentada desde a W12 (Risco 23): o modelo YOLO11n padrão nunca produz o rótulo `"goalkeeper"`. `GoalkeeperPresenceAnalyzer` respondeu corretamente `exists=False`/`goalkeeper_count=0` para essa cena real, confirmando que o Analyzer reflete fielmente `FootballWorld.goalkeepers`, sem inventar nada. O caminho "positivo" (`exists=True`, com um goleiro real presente) já está coberto por um teste de integração com Detector stub rotulado `"goalkeeper"` (`test_engine_with_analyzers_enabled_produces_a_coherent_goalkeeper_presence_result`), rodando a cadeia real de Tracker/SceneAnalyzer/WorldModel/FootballDomain/Analyzer — mesma disciplina de validação já aplicada na W12 (que também confirmou um "frisbee" real e deixou o caminho `goalkeeper` positivo para o nível de integração com stub). Lock liberado (`GET lock:video:...` vazio), fila sem pendências (`XPENDING`=0), status do Job `COMPLETED`. Stack derrubado ao final (`docker compose down`, volume preservado).

## Riscos (novos, registrados na Constituição — Seção 14)

24. **`GoalkeeperPresenceAnalyzer` escolhe o PRIMEIRO candidato de `FootballWorld.goalkeepers`** quando há mais de um — regra de ordem determinística, não heurística de identidade; sem continuidade de identidade entre frames nesta camada (isso pertence ao Tracker, W9).
25. **`WORKER_ANALYZERS` não valida nomes desconhecidos em tempo de configuração** — um nome inválido só falha em runtime, na primeira chamada a `create_analyzer` dentro de `AnalyzerProcessor.__init__`.

(Risco 23, já registrado na W12, ganhou uma consequência direta documentada nesta sprint: `GoalkeeperPresenceAnalyzer` herda a mesma limitação do modelo YOLO11n padrão, confirmada na validação manual acima.)

## Preparação para a W14

A W14 ainda não tem escopo definido (qual análise entra primeiro com julgamento/avaliação real — `GoalkeeperPositionAnalyzer`/`BallAnalyzer`/`ShotAnalyzer`/`SaveAnalyzer`/`DiveAnalyzer`/`GoalAnalyzer`). O que já está confirmado, pela sexta repetição consecutiva do padrão de encaixe (W8/W9/W10/W11/W12/W13): um novo Analyzer exige **apenas** escrever `XAnalyzer(Analyzer)`, registrá-lo em `analyzers/registry.py`, incluir seu nome em `WORKER_ANALYZERS` — nunca uma mudança em `AnalyzerProcessor`, `PipelineProcessor`, `BasicVisionEngine`, `Orchestrator`, `Detector`, `Tracker`, `SceneAnalyzer`, `WorldModel`, `FootballDomainProcessor` ou `video/`. A partir da W14, a lógica introduzida terá semântica de JULGAMENTO (uma defesa foi boa? um chute foi no gol?) em vez de apenas relatar fatos determinísticos — esta é a primeira sprint em que avaliação/heurística de negócio deixa de ser proibida. Os Analyzers devem continuar consumindo **exclusivamente** `FootballWorld`.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
