# SPRINT_W17_REPORT.md — Goalkeeper AI Worker: Goalkeeper Ball Alignment Analyzer

> Escopo: construir o primeiro Analyzer RELACIONAL — `GoalkeeperBallAlignmentAnalyzer`, que mede a relação espacial entre goleiro, bola e gol, compondo os três Analyzers de geometria/posição já existentes (`GoalGeometryAnalyzer`, `GoalkeeperPositionAnalyzer`, `BallPositionAnalyzer`). Ainda **sem** avaliação de desempenho, julgamento de posicionamento, detecção de chutes ou conceito de "bem posicionado" — só mede. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W16_REPORT.md` antes de implementar.

- **`worker/analyzers/goalkeeper_ball_alignment.py`** (novo) — `GoalkeeperBallAlignmentAnalyzer(Analyzer)`: quinta implementação concreta da Analyzer API, e a primeira a compor **três** Analyzers ao mesmo tempo.
- **`worker/analyzers/results.py`** — `GoalkeeperBallAlignmentResult(AnalysisResult)` adicionado (16 campos, ver abaixo).
- **`worker/analyzers/registry.py`** — `register_analyzer("goalkeeper_ball_alignment", GoalkeeperBallAlignmentAnalyzer)` adicionado, sem nenhuma outra mudança.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goalkeeper_ball_alignment_result"` (alias de conveniência de `analysis_results["goalkeeper_ball_alignment"]`).

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, ou nos três Analyzers compostos (`GoalGeometryAnalyzer`/`GoalkeeperPositionAnalyzer`/`BallPositionAnalyzer`) — conforme exigido pela sprint.

## Composição com os três Analyzers

```python
class GoalkeeperBallAlignmentAnalyzer(Analyzer):
    def __init__(self, settings: WorkerSettings) -> None:
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
        self._goalkeeper_position_analyzer = GoalkeeperPositionAnalyzer(settings)
        self._ball_position_analyzer = BallPositionAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        goal_geometry = self._goal_geometry_analyzer.analyze(football_world)
        goalkeeper_result = self._goalkeeper_position_analyzer.analyze(football_world)
        ball_result = self._ball_position_analyzer.analyze(football_world)
        ...
```

Nenhum canal especial entre Analyzers foi criado; `ProcessorContext` não foi alterado. Validado que o Analyzer funciona corretamente mesmo quando `WORKER_ANALYZERS` contém **apenas** `"goalkeeper_ball_alignment"` (nenhum dos três Analyzers compostos precisa estar na lista).

**Princípio central: combinar apenas os resultados já produzidos.** `ball_to_goal_distance`/`ball_goal_angle` e `goalkeeper_to_goal_distance`/`goalkeeper_goal_angle` são ECOADOS diretamente de `BallPositionResult.distance_to_goal_center`/`.angle_to_goal` e `GoalkeeperPositionResult.distance_to_goal_center`/`.angle_to_goal` — nunca recalculados, o que evita qualquer divergência entre os Analyzers. O único cálculo genuinamente NOVO desta sprint é a relação goleiro↔bola (nenhum Analyzer anterior relaciona os dois diretamente) e o "alinhamento" geométrico.

## GoalkeeperBallAlignmentResult — geometria utilizada

| Campo | Cálculo | Depende de |
|---|---|---|
| `goalkeeper_detected`/`ball_detected`/`goal_detected` | ecoados dos três sub-resultados | — |
| `goalkeeper_position`/`ball_position`/`goal_center` | ecoados | — |
| `goalkeeper_to_ball_distance` | `distance(goalkeeper_position, ball_position)` — **novo** | goleiro + bola (não precisa do gol) |
| `goalkeeper_ball_angle` | `Vector.between(goalkeeper_position, ball_position).angle_degrees()` — **novo** | goleiro + bola |
| `ball_to_goal_distance` | ecoado de `BallPositionResult.distance_to_goal_center` | bola + gol (não precisa do goleiro) |
| `goalkeeper_to_goal_distance` | ecoado de `GoalkeeperPositionResult.distance_to_goal_center` | goleiro + gol (não precisa da bola) |
| `ball_goal_angle`/`goalkeeper_goal_angle` | ecoados | idem |
| `alignment_line` | `Vector.between(ball_position, goal_center)` — o vetor bola→gol, a "linha de tiro" | bola + gol |
| `alignment_offset`/`is_between_ball_and_goal` | projeção geométrica do goleiro sobre a reta bola→gol: distância perpendicular + `0 <= t <= 1` | goleiro + bola + gol (os três) |
| `confidence` | `min(goalkeeper_result.confidence, ball_result.confidence)` | transitivamente incorpora `goal_geometry.confidence`, já que ambos os sub-resultados o incluem em seu próprio `min()` |

Cada campo relacional só exige os DOIS lados de que genuinamente precisa — ex.: `goalkeeper_to_ball_distance` é calculado mesmo sem gol detectado; `ball_to_goal_distance` mesmo sem goleiro detectado. Só `alignment_offset`/`is_between_ball_and_goal` exigem os três presentes.

**Projeção geométrica (a única matemática nova, além de distância/ângulo já conhecidos):**

```python
def _project_onto_line(point, line_start, line_end):
    dx, dy = line_end.x - line_start.x, line_end.y - line_start.y
    length_squared = dx*dx + dy*dy
    t = ((point.x - line_start.x)*dx + (point.y - line_start.y)*dy) / length_squared
    projection = Coordinate(x=line_start.x + t*dx, y=line_start.y + t*dy)
    return distance(point, projection), (0.0 <= t <= 1.0)
```

`t` é o parâmetro de projeção ao longo do segmento bola→gol (0 na bola, 1 no gol); `alignment_offset` é a distância perpendicular do goleiro a essa reta; `is_between_ball_and_goal` reflete se a projeção cai dentro do segmento (não além de nenhuma extremidade) — puramente geométrico, nunca uma afirmação de que o goleiro está "no caminho certo".

## Testes — 314/314 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `GoalkeeperBallAlignmentResult.to_dict()` com/sem tudo detectado, incluindo serialização de `alignment_line` (Vector → {dx,dy}) |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `GoalkeeperBallAlignmentAnalyzer` registrado e resolvido corretamente |
| `GoalkeeperBallAlignmentAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_ball_alignment.py` | Nada detectado; só gol (goalkeeper_to_ball/alignment tudo None); só bola+goal (ball_to_goal calculado, sem depender do goleiro); só goleiro+bola sem gol (goalkeeper_to_ball calculado, sem depender do gol); geometria completa com goleiro perfeitamente alinhado (offset=0.0, is_between=True, valores calculados à mão conferidos); goleiro fora da reta (offset=50.0); goleiro além do gol (is_between=False); `confidence=min(...)`; composição interna com os três Analyzers funciona sem depender do Registry; metadata correta |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goalkeeper_ball_alignment_analyzer_produces_a_coherent_result` | Detector stub emite DUAS detecções por frame (goalkeeper + sports ball); `WORKER_ANALYZERS=goalkeeper_ball_alignment` (SEM os três Analyzers compostos) — prova que a composição TRIPLA funciona na pipeline real; artefato contém `"goalkeeper_ball_alignment_result"` coerente, idêntico a `analysis_results["goalkeeper_ball_alignment"]` |
| Regressão | Todos os 299 testes anteriores (W1-W16) | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `314 passed` (suíte completa exceto `tests/infrastructure/`, dependente de um container Redis descartável já encerrado após a validação manual).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/analyzers/goalkeeper_ball_alignment.py tests/analyzers/test_goalkeeper_ball_alignment.py` → nenhuma menção.
- `grep -n "YOLO\|ByteTrack\|Tracker\|WorldState\|Detector\|cv2\|redis\|SceneAnalyzer" worker/analyzers/goalkeeper_ball_alignment.py` → nenhuma menção real, nenhum `import`.
- Todos os `import`s reais: `time` (stdlib) + `worker.analyzers.ball_position`/`base`/`goal_geometry`/`goalkeeper_position`/`results`/`types` + `worker.config.settings` + `worker.domain.football_world`/`worker.domain.geometry.coordinate`/`worker.domain.geometry.vector`. Os imports de `worker.analyzers.{ball_position,goal_geometry,goalkeeper_position}` são composição DENTRO da própria família de Analyzers, não uma dependência de camada inferior.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores. Gerei um vídeo real de 10 frames (640×480, 5fps) com um círculo vermelho se movendo, upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true`, `WORKER_FOOTBALL_DOMAIN_ENABLED=true`, `WORKER_ANALYZERS=goalkeeper_presence,goal_geometry,goalkeeper_position,ball_position,goalkeeper_ball_alignment`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model', 'football_domain', 'analyzer']
analysis_statistics: {'analyzers_run': ['ball_position', 'goal_geometry', 'goalkeeper_ball_alignment', 'goalkeeper_position', 'goalkeeper_presence'], 'results_count': 5}

goalkeeper_ball_alignment_result:
  goalkeeper_detected: False
  ball_detected: False
  goal_detected: True
  goalkeeper_position: None
  ball_position: None
  ...(todos os campos geometricos: None)
  goal_center: {'x': 0.01, 'y': 0.5}
  confidence: None

matches analysis_results['goalkeeper_ball_alignment']: True
football_world.balls: []
football_world.goalkeepers: []
```

**Confirmado exatamente o comportamento honesto esperado:** o YOLO real, neste vídeo, não detectou nenhum goleiro nem bola — `goalkeeper_detected=False`, `ball_detected=False`, `goal_detected=True`, e TODO campo geométrico dependente explicitamente `None`. Os cinco Analyzers rodaram corretamente juntos na mesma execução da pipeline. `goalkeeper_ball_alignment_result` bate exatamente com `analysis_results["goalkeeper_ball_alignment"]`. O caminho "positivo" (goleiro + bola + gol, geometria/alinhamento completos) já está coberto pelo teste de integração com Detector stub emitindo duas detecções (goleiro + bola) e pelos testes unitários com valores calculados à mão. Lock liberado, fila sem pendências (`XPENDING`=0), Job `COMPLETED`. Stack derrubado ao final (volume preservado).

## Riscos (novo, registrado na Constituição — Seção 14)

32. **`GoalkeeperBallAlignmentAnalyzer` executa `GoalGeometryAnalyzer.analyze()` efetivamente TRÊS vezes por frame** (uma direta, uma dentro de cada um dos dois sub-Analyzers compostos) — seguro (função pura, sem estado), mas gasta CPU redundante; cresceria combinatoriamente se um Analyzer futuro compor `GoalkeeperBallAlignmentAnalyzer`. Aceito por simplicidade nesta sprint.

## Preparação para a W18

A W18 ainda não tem escopo definido (qual análise entra primeiro com julgamento/avaliação real). O que já está confirmado, pela décima repetição consecutiva do padrão de encaixe (W8 a W17): um novo Analyzer exige **apenas** escrever `XAnalyzer(Analyzer)`, registrá-lo, incluir seu nome em `WORKER_ANALYZERS` — nunca uma mudança em `AnalyzerProcessor`/pipeline/famílias de Plugin existentes. A W17 confirmou pela primeira vez que o padrão de composição escala para MÚLTIPLOS Analyzers simultâneos dentro de um só, e estabeleceu o princípio de "combinar resultados já calculados em vez de recalcular" para Analyzers que compõem outros. A partir da W18, a lógica introduzida terá semântica de JULGAMENTO em vez de apenas medir/relatar fatos — esta é a primeira sprint em que avaliação/heurística de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
