# SPRINT_W22_REPORT.md — Goalkeeper AI Worker: Goalkeeper Decision Analyzer

> Escopo: construir `GoalkeeperDecisionAnalyzer` — o primeiro Analyzer ESPECÍFICO DO GOLEIRO. Identifica APENAS qual decisão o goleiro APARENTA estar executando, combinando cinco Analyzers já existentes. Ainda **sem** afirmar se a decisão foi correta, avaliar desempenho ou avaliar o resultado da jogada — é uma CLASSIFICAÇÃO de comportamento, não uma opinião. **Constituição atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` e `SPRINT_W21_REPORT.md` antes de implementar.

- **`worker/analyzers/goalkeeper_decision.py`** (novo) — `GoalkeeperDecisionAnalyzer(Analyzer)` + `GoalkeeperDecisionContext(AnalyzerContext)`: décima implementação concreta, primeiro Analyzer específico do goleiro, quarto Analyzer STATEFUL.
- **`worker/analyzers/types.py`** — `GoalkeeperDecision(str, Enum)` adicionado (10 valores).
- **`worker/analyzers/results.py`** — `GoalkeeperDecisionResult(AnalysisResult)` adicionado.
- **`worker/config/settings.py`** — 2 campos novos: `goalkeeper_shift_min_speed`, `goalkeeper_dive_min_speed`.
- **`worker/analyzers/registry.py`** — `register_analyzer("goalkeeper_decision", GoalkeeperDecisionAnalyzer)`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goalkeeper_decision_result"`.

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, ou nos cinco Analyzers compostos.

## GoalkeeperDecisionAnalyzer

Compõe CINCO Analyzers — `PlaySituationAnalyzer`, `GoalkeeperPositionAnalyzer`, `GoalkeeperBallAlignmentAnalyzer`, `BallTrajectoryAnalyzer`, `ShotAnalyzer`:

```python
def __init__(self, settings: WorkerSettings) -> None:
    self._play_situation_analyzer = PlaySituationAnalyzer(settings)
    self._goalkeeper_position_analyzer = GoalkeeperPositionAnalyzer(settings)
    self._goalkeeper_ball_alignment_analyzer = GoalkeeperBallAlignmentAnalyzer(settings)
    self._ball_trajectory_analyzer = BallTrajectoryAnalyzer(settings)
    self._shot_analyzer = ShotAnalyzer(settings)
    self._context = GoalkeeperDecisionContext()
```

`PlaySituationAnalyzer` já compõe outros quatro Analyzers (um deles, `ShotAnalyzer`, compõe mais três) — a cadeia de composição chega a seis camadas de profundidade (`GoalkeeperDecisionAnalyzer` → `PlaySituationAnalyzer` → `ShotAnalyzer` → `BallMotionAnalyzer` → `BallPositionAnalyzer` → `GoalGeometryAnalyzer`), confirmando que a profundidade de composição não introduz nenhuma complexidade estrutural — apenas mais chamadas `.analyze()` em cadeia, todas puras.

## A única informação genuinamente nova: movimento do goleiro

Nenhum dos cinco Analyzers compostos rastreia o movimento do PRÓPRIO goleiro entre frames — `GoalkeeperPositionAnalyzer` é uma fotografia geométrica por frame, sem histórico. Por isso `GoalkeeperDecisionAnalyzer` é STATEFUL (`GoalkeeperDecisionContext`, quarto `AnalyzerContext` real):

```python
@dataclass
class GoalkeeperDecisionContext(AnalyzerContext):
    previous_position: Coordinate | None = None
    previous_track_id: EntityId | None = None
    previous_depth_offset: float | None = None
    previous_decision: GoalkeeperDecision | None = None
```

Mesma disciplina de continuidade de `BallMotionAnalyzer` (W18): `track_id` lido diretamente de `football_world.goalkeepers[0]` (já que `GoalkeeperPositionResult` não o expõe), comparado entre frames; qualquer lacuna ou mudança de identidade reinicia a observação (`movement_speed=None` → `decision=UNKNOWN`), nunca extrapola.

## Estados implementados — `GoalkeeperDecision`

```python
class GoalkeeperDecision(str, Enum):
    UNKNOWN = "unknown"
    STAY_ON_LINE = "stay_on_line"
    STEP_FORWARD = "step_forward"
    STEP_BACK = "step_back"
    SHIFT_LEFT = "shift_left"
    SHIFT_RIGHT = "shift_right"
    PREPARE_DIVE = "prepare_dive"
    DIVE_LEFT = "dive_left"
    DIVE_RIGHT = "dive_right"
    RECOVER_POSITION = "recover_position"
```

## Critérios utilizados — árvore de decisão priorizada

| Prioridade | `decision` | Condição |
|---|---|---|
| 1 (mais alta) | `UNKNOWN` | sem goleiro, ou primeira observação/descontinuidade de `track_id` |
| 2 | `DIVE_LEFT`/`DIVE_RIGHT` | chute detectado + `movement_speed >= WORKER_GOALKEEPER_DIVE_MIN_SPEED` + eixo lateral dominante |
| 3 | `PREPARE_DIVE` | chute detectado, mas sem atingir o limiar de mergulho acima |
| 4 | `RECOVER_POSITION` | decisão anterior era de mergulho, chute já não é mais detectado, e ainda há movimento (`>= WORKER_GOALKEEPER_SHIFT_MIN_SPEED`) |
| 5 | `STAY_ON_LINE` | `movement_speed < WORKER_GOALKEEPER_SHIFT_MIN_SPEED` |
| 6 | `SHIFT_LEFT`/`SHIFT_RIGHT` | eixo lateral domina o deslocamento |
| 7 (mais baixa) | `STEP_FORWARD`/`STEP_BACK` | eixo de profundidade domina |

**Eixos:** `movement_direction.dy` é o eixo LATERAL (mesma convenção de `lateral_offset`/`covers_left_post` — y menor = esquerda); `movement_direction.dx` é o eixo de PROFUNDIDADE. `STEP_FORWARD`/`STEP_BACK` usa a variação da MAGNITUDE de `depth_offset` (não o sinal cru de `dx`), tornando a regra agnóstica a qual dos dois gols (`Goal.default_pair()`, W12) o goleiro está defendendo.

**Desempate documentado:** quando `abs(lateral) == abs(depth)`, a regra favorece a classificação lateral (`SHIFT_*`) — determinístico, não uma ambiguidade real, coberto por teste dedicado.

**Limitação honesta:** `PREPARE_DIVE` é um proxy determinístico baseado em VELOCIDADE observada, não uma detecção real de postura/pose (este Worker não tem estimativa de keypoints do goleiro). Um goleiro genuinamente estático por indecisão seria classificado da mesma forma. Documentado como **Risco 37** na Constituição.

## Campos do resultado — combinar, nunca recalcular

| Campo | Fonte |
|---|---|
| `play_situation`, `ball_detected`, `goalkeeper_detected` | ecoados de `PlaySituationResult` |
| `ball_direction` | ecoado de `ShotAnalysisResult.direction_angle` |
| `alignment` | ecoado de `GoalkeeperBallAlignmentResult.is_between_ball_and_goal` |
| `goalkeeper_position` | ecoado de `GoalkeeperPositionResult.goalkeeper_position` |
| `movement_direction`, `movement_speed` | calculados internamente (única informação nova) |
| `confidence` | `min(goalkeeper_position.confidence, alignment.confidence, trajectory.confidence, shot.confidence)` quando os quatro estão disponíveis, `None` caso contrário |

## Testes — 406/406 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `GoalkeeperDecisionResult.to_dict()` com/sem goleiro |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `GoalkeeperDecisionAnalyzer` registrado e resolvido corretamente |
| Configuração | `tests/test_settings.py` | os dois limiares configuráveis via env var |
| `GoalkeeperDecisionAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_decision.py` | Ausência de goleiro; ausência de bola (ainda classifica comportamento do goleiro); ausência de ambos (prioridade correta); primeira observação; `STAY_ON_LINE`; `STEP_FORWARD`/`STEP_BACK`; `SHIFT_LEFT`/`SHIFT_RIGHT`; **cenário ambíguo de empate** lateral/profundidade (desempate documentado); `PREPARE_DIVE`; `DIVE_LEFT`/`DIVE_RIGHT`; `RECOVER_POSITION` após quebra do streak de chute; composição interna sem depender do Registry; `reset()` limpa o estado; metadata correta |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goalkeeper_decision_analyzer_produces_a_coherent_result` | Detector stub emite goleiro se movendo lateralmente + bola se movendo; `WORKER_ANALYZERS=goalkeeper_decision` sozinho; confirma tipos/coerência do resultado |
| Regressão | Todos os 388 testes anteriores (W1-W21) | Sem alteração de comportamento não intencional |

Confirmado via `pytest`: `406 passed` (todos os 17 testes novos passaram já na primeira execução).

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend, volume persistido de sprints anteriores), reutilizei usuário/goleiro/sessão de treino. Gerei um vídeo real (640×480, 5fps, 10 frames), upload real via `httpx`.

Rodei `python -m worker.main` com os **dez** Analyzers ativos. Log real confirmou o ciclo completo (`JobStarted → download → VideoDownloaded → upload → UploadFinished → JobCompleted`).

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
analysis_statistics: {'analyzers_run': [... 10 nomes incluindo 'goalkeeper_decision'], 'results_count': 10}

goalkeeper_decision_result:
  decision: unknown
  play_situation: no_ball_visible
  ball_detected: False
  goalkeeper_detected: False
  goalkeeper_position: None
  movement_direction: None
  movement_speed: None
  ball_direction: None
  alignment: None
  confidence: None

matches analysis_results['goalkeeper_decision']: True
```

**Confirmado o comportamento honesto esperado:** o YOLO real não detectou bola nem goleiro neste vídeo sintético (mesma variabilidade desde a W12) — todos os dez Analyzers rodaram corretamente juntos, e `goalkeeper_decision_result` refletiu fielmente `decision=UNKNOWN`/`play_situation=NO_BALL_VISIBLE`. Lock liberado, fila sem pendências, Job `COMPLETED`. Stack derrubado ao final; `.env` do Worker removido após a validação.

## Riscos (Constituição, Seção 14)

**Riscos 34/35/36 (W19/W20/W21) permanecem inalterados.**

37. **`PREPARE_DIVE` é um proxy determinístico baseado em velocidade, não uma detecção real de postura corporal** — descrito acima. Documentado honestamente; corrigir exigiria uma sprint de estimativa de pose, fora do escopo atual.

## Preparação para a W23

A W23 (renomeada nesta revisão — antes seria "W22") continua sendo a primeira sprint a introduzir avaliação de QUALIDADE. A W22 confirmou, pela décima vez consecutiva, que um novo Analyzer se encaixa sem exigir nenhuma mudança estrutural — inclusive quando compõe CINCO Analyzers com até seis camadas de profundidade de composição, E mantém seu próprio estado. `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W23, incluindo a limitação de pose (Risco 37) que qualquer novo Analyzer precisa considerar se depender de postura do goleiro.
