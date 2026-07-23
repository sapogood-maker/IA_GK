# SPRINT_W20_REPORT.md — Goalkeeper AI Worker: Ball Trajectory Analyzer

> Escopo: construir `BallTrajectoryAnalyzer`, que modela exclusivamente a trajetória OBSERVADA da bola ao longo de múltiplos frames, compondo `BallMotionAnalyzer`/`BallPositionAnalyzer`/`GoalGeometryAnalyzer`. Ainda **sem** detecção de gol, avaliação de defesa, julgamento de decisões do goleiro, ou qualquer previsão de posições futuras. Segundo Analyzer STATEFUL (depois de `BallMotionAnalyzer`, W18). **Constituição atualizada durante a própria implementação** — nenhuma sprint de sincronização.

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md` e `SPRINT_W19_REPORT.md` antes de implementar.

- **`worker/analyzers/ball_trajectory.py`** (novo) — `BallTrajectoryAnalyzer(Analyzer)` + `BallTrajectoryContext(AnalyzerContext)`: oitava implementação concreta, segundo Analyzer STATEFUL.
- **`worker/analyzers/results.py`** — `BallTrajectoryResult(AnalysisResult)` adicionado (12 campos, ver abaixo).
- **`worker/analyzers/registry.py`** — `register_analyzer("ball_trajectory", BallTrajectoryAnalyzer)` adicionado, sem nenhuma outra mudança.
- **`worker/config/settings.py`** — 1 campo novo: `trajectory_direction_change_threshold_degrees`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"ball_trajectory_result"` (alias de `analysis_results["ball_trajectory"]`).

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, ou nos três Analyzers compostos.

## BallTrajectoryAnalyzer

Composição idêntica em estrutura à do `ShotAnalyzer` (W19) — instancia os três Analyzers internamente e chama `.analyze(football_world)` como função pura em cada um:

```python
class BallTrajectoryAnalyzer(Analyzer):
    def __init__(self, settings: WorkerSettings) -> None:
        self._ball_motion_analyzer = BallMotionAnalyzer(settings)
        self._ball_position_analyzer = BallPositionAnalyzer(settings)
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
        self._direction_change_threshold_degrees = settings.trajectory_direction_change_threshold_degrees
        self._context = BallTrajectoryContext()
```

**Diferença deliberada em relação ao `ShotAnalyzer`:** `GoalGeometryAnalyzer` é composto, mas **nenhum campo de trajetória depende dele** — a trajetória é descrita inteiramente em relação a si mesma (sequência de posições, não posição relativa ao gol). Sua única contribuição é servir de terceiro sinal real para `confidence` (`min(ball_motion.confidence, ball_position.confidence, goal_geometry.confidence)`), mesma filosofia de "usar apenas sinais realmente disponíveis, nunca inventar probabilidades" já estabelecida. Isso foi documentado explicitamente no código, para que a composição não pareça um resíduo esquecido.

## AnalyzerContext — terceiro uso real

`BallTrajectoryContext` acumula `points: list[Coordinate]` — a sequência de posições da MESMA bola continuamente observada:

```python
@dataclass
class BallTrajectoryContext(AnalyzerContext):
    points: list[Coordinate] = field(default_factory=list)

    def reset(self) -> None:
        self.points = []
```

Continuidade decidida reaproveitando um sinal que `BallMotionAnalyzer` (W18) já calcula: `ball_motion.previous_position is None` indica que a bola atual é uma "primeira observação" (verdadeira primeira vez, OU reaparecimento após lacuna, OU `track_id` trocado) — em qualquer um desses três casos, `BallTrajectoryAnalyzer` reinicia `self._context.points = [current_position]` em vez de emendar com a trajetória anterior. Isso evita duplicar a lógica de comparação de `track_id` que `BallMotionAnalyzer` já implementa (princípio "combinar, nunca recalcular").

## Modelo de trajetória — critérios utilizados

A partir dos pontos acumulados, todos os cálculos derivam dos segmentos frame-a-frame (`Vector.between(points[i], points[i+1])`):

| Campo | Cálculo | Observação |
|---|---|---|
| `trajectory_length` | soma das magnitudes de cada segmento | comprimento do CAMINHO percorrido, distinto da distância em linha reta |
| `average_velocity` | média (dx, dy) de todos os segmentos | vetor médio — sempre calculado quando há ≥1 segmento, mesmo que nulo |
| `dominant_direction` | ângulo de `average_velocity` | `None` se o vetor médio for nulo (direção indefinida — nunca inventada) |
| `direction_consistency` | magnitude do vetor resultante médio dos segmentos NORMALIZADOS | estatística circular clássica ("mean resultant length"), sempre em [0, 1]: 1.0 = todos os segmentos apontam exatamente na mesma direção |
| `direction_changes` | contagem de pares de segmentos consecutivos com `angle_between() >= WORKER_TRAJECTORY_DIRECTION_CHANGE_THRESHOLD_DEGREES` | limiar configurável (default 30°) — evita contar ruído normal de detecção como mudança real |
| `linearity_score` | distância em linha reta (primeiro→último ponto) ÷ `trajectory_length` | sempre em [0, 1] pela desigualdade triangular; `None` quando `trajectory_length == 0` (divisão indefinida, nunca inventada) |

`linearity_score` e `direction_consistency` respondem só "o quanto o caminho se aproxima de uma reta" e "o quanto a direção se manteve estável" — **nenhum dos dois representa qualidade, perigo ou precisão**, conforme exigido pela sprint.

Nunca há previsão: todos os campos são funções puras dos pontos já observados até o frame atual; nenhum ponto futuro é extrapolado.

## Composição e `confidence`

Mesmo princípio "combinar, nunca recalcular" das W17-W19: `trajectory_length`/`average_velocity`/etc. são calculados só a partir da sequência de posições já obtida via `ball_motion.current_position` (nenhuma redetecção). `confidence = min(ball_motion.confidence, ball_position.confidence, goal_geometry.confidence)` quando os três estão disponíveis, `None` caso contrário — mesma filosofia de nunca inventar uma probabilidade.

## Testes — 365/365 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `BallTrajectoryResult.to_dict()` com/sem trajetória |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `BallTrajectoryAnalyzer` registrado e resolvido corretamente |
| Configuração | `tests/test_settings.py` | limiar de mudança de direção configurável via env var |
| `BallTrajectoryAnalyzer` (real, sem mock) | `tests/analyzers/test_ball_trajectory.py` | Sem bola; primeira observação (ainda não é trajetória); trajetória reta (linearidade/consistência = 1.0, zero mudanças de direção); trajetória com mudança de 90° (linearidade/consistência entre 0 e 1, uma mudança contada); desvio pequeno não conta como mudança (ruído); bola parada (comprimento zero, direção/linearidade `None`, nunca inventadas); desaparecimento da bola descarta a trajetória acumulada; reaparecimento inicia uma trajetória nova; mudança de `track_id` também inicia uma trajetória nova; composição interna sem depender do Registry; `reset()` limpa a sequência acumulada e delega aos três Analyzers compostos; metadata correta |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_ball_trajectory_analyzer_produces_a_coherent_result` | Detector stub move a bola 5px/frame em linha reta; `WORKER_ANALYZERS=ball_trajectory` sozinho; confirma trajetória de 5 pontos coerente (comprimento > 0, linearidade/consistência/confiança presentes) |
| Regressão | Todos os 353 testes anteriores (W1-W19) | Sem alteração de comportamento não intencional |

Confirmado via `pytest`: `365 passed`.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores. Gerei um vídeo real (640×480, 5fps, 10 frames) com um círculo se movendo em linha reta, upload real via `httpx`.

Rodei `python -m worker.main` com os **oito** Analyzers ativos (`goalkeeper_presence,goal_geometry,goalkeeper_position,ball_position,goalkeeper_ball_alignment,ball_motion,shot,ball_trajectory`). Log real confirmou o ciclo completo (`JobStarted → download → VideoDownloaded → upload → UploadFinished → JobCompleted`).

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
analysis_statistics: {'analyzers_run': [... 8 nomes incluindo 'ball_trajectory'], 'results_count': 8}

ball_trajectory_result:
  ball_detected: False
  trajectory_detected: False
  trajectory_points: None
  (todos os campos geométricos: None)
  direction_changes: 0
  frames_observed: 0
  confidence: None

matches analysis_results['ball_trajectory']: True
```

**Confirmado o comportamento honesto esperado:** o YOLO real não detectou bola neste vídeo sintético (mesma variabilidade já observada desde a W12) — todos os oito Analyzers rodaram corretamente juntos na mesma execução da pipeline, e `ball_trajectory_result` refletiu fielmente a ausência de bola.

**Validação de `reset()` entre Jobs:** fiz upload de um SEGUNDO vídeo real e reexecutei `python -m worker.main` no MESMO processo do Worker (a mesma instância viva de `BallTrajectoryAnalyzer`, reaproveitada entre Jobs sequenciais — Seção 6.1, "Estado entre Jobs"). O segundo Job completou de ponta a ponta sem erro, confirmando que `self._pipeline.reset()` (chamado no início de cada `process()`) delega corretamente até `BallTrajectoryContext.reset()` sem exceções, mesmo com o novo Analyzer stateful na composição. O caminho positivo exato (uma trajetória genuinamente acumulada sendo descartada por `reset()`) já está coberto, com precisão total, por `test_reset_clears_the_accumulated_trajectory` (coordenadas controladas) — a mesma limitação estrutural de detecção real (Risco 23) que afeta toda sprint desde a W12 impede observar isso via YOLO real neste vídeo sintético.

Lock liberado, fila sem pendências (`XPENDING=0`), ambos os Jobs `COMPLETED`. Stack derrubado ao final (volume preservado); `.env` do Worker removido após a validação (continha o segredo de desenvolvimento).

## Riscos (Constituição, Seção 14)

**Risco 34 (W19) não corrigido, por instrução explícita** — confirmado que não se agrava: nenhum cálculo de `BallTrajectoryAnalyzer` referencia `goal_center`/geometria do gol.

35. **`BallTrajectoryContext.points` cresce sem limite** — diferente de `Trajectory`/`History` do World Model (W11, com teto via `WORKER_WORLD_MAX_TRAJECTORY`), a lista de posições acumuladas não tem limite: para uma bola continuamente rastreada por um vídeo longo, `trajectory_points` cresce proporcionalmente à duração da observação, inflando o artefato JSON. Aceito nesta sprint (nenhum limite foi pedido); uma sprint futura pode introduzir `WORKER_TRAJECTORY_MAX_POINTS` se isso se tornar um problema real.

## Preparação para a W21

A W21 (renomeada nesta revisão — antes seria "W20") continua sendo a primeira sprint a introduzir avaliação de QUALIDADE. A W20 confirmou, pela oitava vez consecutiva, que um novo Analyzer se encaixa sem exigir nenhuma mudança estrutural — inclusive quando compõe um Analyzer sem usar nenhum de seus campos diretamente (só para `confidence`). `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W21.
