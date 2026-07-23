# SPRINT_W16_REPORT.md — Goalkeeper AI Worker: Ball Position Analyzer

> Escopo: construir o segundo Analyzer que compõe `GoalGeometryAnalyzer` — `BallPositionAnalyzer`, que mede a relação geométrica entre a bola e o gol. Ainda **sem** análise de chute, sem previsão de trajetória, sem avaliação de decisões do goleiro, sem conceito de "bola perigosa" — só mede. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W15_REPORT.md` antes de implementar.

- **`worker/analyzers/ball_position.py`** (novo) — `BallPositionAnalyzer(Analyzer)`: quarta implementação concreta da Analyzer API, e o segundo Analyzer a compor outro (mesmo padrão exato da W15, agora aplicado a `football_world.balls[0]`).
- **`worker/analyzers/field_areas.py`** (novo) — `estimate_goal_and_penalty_areas(goal_region, field_region) -> tuple[Region, Region]`: **extraído de `goalkeeper_position.py`** (refatoração comportamento-preservando — testes da W15 continuam passando sem alteração) para ser reutilizado por `ball_position.py`, evitando duplicar a mesma derivação de proporções oficiais de campo em dois arquivos.
- **`worker/analyzers/goalkeeper_position.py`** — refatorado para importar `estimate_goal_and_penalty_areas` de `field_areas.py` em vez de manter sua própria cópia privada (`_estimate_areas`), removida sem alteração de comportamento.
- **`worker/analyzers/results.py`** — `BallPositionResult(AnalysisResult)` adicionado (13 campos, ver abaixo).
- **`worker/analyzers/registry.py`** — `register_analyzer("ball_position", BallPositionAnalyzer)` adicionado, sem nenhuma outra mudança.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"ball_position_result"` (alias de conveniência de `analysis_results["ball_position"]`).

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, `GoalGeometryAnalyzer`, `Detector`, `Tracker`, `SceneAnalyzer` ou qualquer outro módulo além dos listados acima — conforme exigido pela sprint.

## Composição com GoalGeometryAnalyzer

Seguindo exatamente o padrão introduzido na W15:

```python
class BallPositionAnalyzer(Analyzer):
    def __init__(self, settings: WorkerSettings) -> None:
        self._geometry_analyzer = GoalGeometryAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        goal_geometry = self._geometry_analyzer.analyze(football_world)
        ...
```

Nenhum canal especial entre Analyzers foi criado; `ProcessorContext` não foi alterado. Validado que `BallPositionAnalyzer` funciona corretamente mesmo quando `WORKER_ANALYZERS` contém **apenas** `"ball_position"` (sem `"goal_geometry"` na lista).

## BallPositionResult — geometria utilizada

| Campo | Cálculo | Fonte |
|---|---|---|
| `ball_detected`/`goal_detected` | presença em `FootballWorld.balls`/`GoalGeometryResult.goal_detected` | — |
| `ball_position`/`ball_bbox` | ecoam `Ball.position`/`Ball.bbox` | conveniência |
| `distance_to_goal_center` | `domain.geometry.coordinate.distance(ball.position, goal_center)` | distância euclidiana |
| `lateral_offset`/`depth_offset` | `ball.position.y/x - goal_center.y/x` | mesmo desenho da W15 |
| `angle_to_goal` | `Vector.between(ball.position, goal_center).angle_degrees()` | ângulo puro, 0–360° |
| `inside_goal_area`/`inside_penalty_area` | `Region.contains(ball.position)` contra retângulos de `estimate_goal_and_penalty_areas()` (`field_areas.py`) | mesma disciplina de proporção fixa de `GoalkeeperPositionAnalyzer` (W15) |
| `ball_region` | qual zona de `GoalGeometryResult.goal_regions` (grade 2×3, W14) contém `ball.position`, se houver | **conceito novo desta sprint** — containment puramente geométrico contra a faixa fina do próprio gol, `None` no caso comum (bola longe da linha do gol) |
| `goal_center` | eco de `goal_geometry.goal_center` | conveniência |
| `confidence` | `min(ball.confidence, goal_geometry.confidence)` | mesma filosofia da W15 — combinação determinística de dois sinais reais, nunca inventado |

Falta bola OU gol: todo campo dependente de ambos é explicitamente `None`. `ball_position`/`ball_bbox`/`goal_center` são preenchidos quando o lado correspondente está disponível.

**Nenhuma previsão, nenhuma avaliação:** `ball_region`/`inside_goal_area`/etc. são medições geométricas de containment no instante atual, nunca uma previsão de trajetória ou uma afirmação de risco/perigo.

## Testes — 299/299 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `BallPositionResult.to_dict()` com/sem ambos detectados, incluindo serialização de `ball_region` (enum → string) |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `BallPositionAnalyzer` registrado e resolvido corretamente |
| `BallPositionAnalyzer` (real, sem mock) | `tests/analyzers/test_ball_position.py` | Sem bola e sem gol; gol sem bola; bola sem gol; geometria completa com bola em frente ao gol (distância/offset/áreas corretos, valores calculados à mão conferidos); `ball_region` corretamente identificado quando a bola sobrepõe a faixa fina do gol (`GoalZone.TOP_LEFT`); bola longe do gol → fora de ambas as áreas e sem zona; `confidence = min(...)`; composição interna funciona sem depender do Registry; metadata correta |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_ball_position_analyzer_produces_a_coherent_result` | `WORKER_ANALYZERS=ball_position` (SEM `goal_geometry`) — prova que a composição funciona na pipeline real mesmo sem o outro Analyzer ativo; artefato contém `"ball_position_result"` coerente, idêntico a `analysis_results["ball_position"]` |
| Regressão | Todos os 285 testes anteriores (W1-W15), incluindo os de `GoalkeeperPositionAnalyzer` após a refatoração de `field_areas.py` | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `299 passed` (suíte completa exceto `tests/infrastructure/`, dependente de um container Redis descartável já encerrado após a validação manual).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/analyzers/ball_position.py worker/analyzers/field_areas.py tests/analyzers/test_ball_position.py` → nenhuma menção.
- `grep -n "YOLO\|ByteTrack\|Tracker\|WorldState\|Detector\|cv2\|redis\|SceneAnalyzer" worker/analyzers/ball_position.py` → nenhuma menção real, nenhum `import`.
- Todos os `import`s reais: `time` (stdlib) + `worker.analyzers.base`/`field_areas`/`goal_geometry`/`results`/`types` + `worker.config.settings` + `worker.domain.football_world`/`worker.domain.geometry.coordinate`/`worker.domain.geometry.region`/`worker.domain.geometry.vector`. Os imports de `worker.analyzers.goal_geometry`/`worker.analyzers.field_areas` são composição DENTRO da própria família de Analyzers, não uma dependência de camada inferior.

## Validação manual — stack real

Docker Desktop precisou ser reiniciado (não estava rodando no início da sessão). Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores. Gerei um vídeo real de 10 frames (640×480, 5fps) com um círculo vermelho se movendo, upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true`, `WORKER_FOOTBALL_DOMAIN_ENABLED=true`, `WORKER_ANALYZERS=goalkeeper_presence,goal_geometry,goalkeeper_position,ball_position`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model', 'football_domain', 'analyzer']
analysis_statistics: {'analyzers_run': ['ball_position', 'goal_geometry', 'goalkeeper_position', 'goalkeeper_presence'], 'results_count': 4}

ball_position_result:
  ball_detected: False
  goal_detected: True
  ball_position: None
  ball_bbox: None
  distance_to_goal_center: None
  ...(todos os campos geometricos: None)
  goal_center: {'x': 0.01, 'y': 0.5}
  confidence: None

matches analysis_results['ball_position']: True
football_world.balls: []
```

**Confirmado exatamente o comportamento honesto esperado:** o YOLO real, neste vídeo, não detectou nenhum objeto rotulado bola (mesma variabilidade já observada na validação manual da W15) — `ball_detected=False`, `goal_detected=True`, e TODO campo geométrico dependente explicitamente `None`, nunca um valor inventado. `ball_position_result` bate exatamente com `analysis_results["ball_position"]`. O caminho "positivo" (bola + gol detectados, geometria completa, incluindo `ball_region`) já está coberto pelo teste de integração com Detector stub rotulado "sports ball" (`test_engine_with_ball_position_analyzer_produces_a_coherent_result`), que roda a cadeia real de Tracker/SceneAnalyzer/WorldModel/FootballDomain/Analyzer com `WORKER_ANALYZERS=ball_position` sozinho. Lock liberado, fila sem pendências (`XPENDING`=0), Job `COMPLETED`. Stack derrubado ao final (volume preservado).

## Riscos (novos, registrados na Constituição — Seção 14)

30. **`BallPositionAnalyzer` herda a mesma limitação dos Riscos 26/28 sem resolvê-la** — lê sempre `football_world.goals[0]` (o gol esquerdo por construção), não uma lógica de "para qual gol a bola se dirige".
31. **`BallPositionResult.ball_region` quase sempre será `None` na prática** — a grade 2×3 do gol (W14) subdivide a faixa fina do próprio gol, não a área de meta/pênalti (muito mais larga); a bola precisaria estar literalmente sobre a linha do gol para que `ball_region` seja diferente de `None`.

## Preparação para a W17

A W17 ainda não tem escopo definido (qual análise entra primeiro com julgamento/avaliação real). O que já está confirmado, pela nona repetição consecutiva do padrão de encaixe (W8 a W16): um novo Analyzer exige **apenas** escrever `XAnalyzer(Analyzer)`, registrá-lo, incluir seu nome em `WORKER_ANALYZERS` — nunca uma mudança em `AnalyzerProcessor`/pipeline/famílias de Plugin existentes. A W16 confirmou pela SEGUNDA vez em produção o padrão de composição entre Analyzers, e introduziu o padrão adicional de extrair lógica geométrica compartilhada para um módulo utilitário (`field_areas.py`) em vez de duplicá-la entre Analyzers. A partir da W17, a lógica introduzida terá semântica de JULGAMENTO em vez de apenas medir/relatar fatos — esta é a primeira sprint em que avaliação/heurística de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
