# SPRINT_W21_REPORT.md — Goalkeeper AI Worker: Play Situation Analyzer

> Escopo: construir `PlaySituationAnalyzer` — o primeiro Analyzer COGNITIVO. Classifica o estado OBSERVADO da jogada atual, combinando exclusivamente resultados já produzidos por quatro Analyzers existentes (`ShotAnalyzer`/`BallTrajectoryAnalyzer`/`GoalkeeperBallAlignmentAnalyzer`/`GoalGeometryAnalyzer`). Ainda **sem** avaliar o goleiro, avaliar defesa, julgar decisões, ou emitir qualquer nota de qualidade — é uma CLASSIFICAÇÃO determinística, não uma opinião. **Constituição atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` e `SPRINT_W20_REPORT.md` antes de implementar.

- **`worker/analyzers/play_situation.py`** (novo) — `PlaySituationAnalyzer(Analyzer)`: nona implementação concreta, primeiro Analyzer COGNITIVO, **sem** `AnalyzerContext` próprio.
- **`worker/analyzers/types.py`** — `PlaySituation(str, Enum)` adicionado (8 valores).
- **`worker/analyzers/results.py`** — `PlaySituationResult(AnalysisResult)` adicionado.
- **`worker/analyzers/registry.py`** — `register_analyzer("play_situation", PlaySituationAnalyzer)`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"play_situation_result"`.

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, ou nos quatro Analyzers compostos. **Nenhum campo novo em `WorkerSettings`** — esta sprint não introduz nenhum limiar numérico, só uma árvore de decisão fixa sobre campos já computados.

## PlaySituationAnalyzer

```python
class PlaySituationAnalyzer(Analyzer):
    def __init__(self, settings: WorkerSettings) -> None:
        self._shot_analyzer = ShotAnalyzer(settings)
        self._ball_trajectory_analyzer = BallTrajectoryAnalyzer(settings)
        self._goalkeeper_ball_alignment_analyzer = GoalkeeperBallAlignmentAnalyzer(settings)
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
```

Compõe QUATRO Analyzers — dois deles (`ShotAnalyzer`, `BallTrajectoryAnalyzer`) já compõem TRÊS Analyzers cada por conta própria. Confirmado que isso não exige nenhum tratamento especial: são só mais chamadas `.analyze()` em cadeia, todas puras e sem efeito colateral.

**Sem estado próprio:** diferente de `ShotAnalyzer`/`BallTrajectoryAnalyzer` (W19/W20), `PlaySituationAnalyzer` não define um `AnalyzerContext` — é um combinador puro. O único estado envolvido pertence aos dois Analyzers compostos que já são stateful; `reset()` delega a todos os quatro por completude, mesmo padrão de `ShotAnalyzer.reset()`.

## Estados implementados — `PlaySituation`

```python
class PlaySituation(str, Enum):
    UNKNOWN = "unknown"
    NO_BALL_VISIBLE = "no_ball_visible"
    NO_GOALKEEPER_VISIBLE = "no_goalkeeper_visible"
    BALL_STATIONARY = "ball_stationary"
    BALL_MOVING = "ball_moving"
    SHOT_DETECTED = "shot_detected"
    SHOT_TOWARDS_GOAL = "shot_towards_goal"
    SHOT_AWAY_FROM_GOAL = "shot_away_from_goal"
```

`PlaySituationResult` tem dois campos deste tipo:

- **`situation`** — classificação PRIMÁRIA (sempre um valor, nunca `None`), por uma árvore de decisão determinística e PRIORIZADA:

| Prioridade | `situation` | Condição |
|---|---|---|
| 1 (mais alta) | `NO_BALL_VISIBLE` | `not ball_detected` |
| 2 | `NO_GOALKEEPER_VISIBLE` | `ball_detected and not goalkeeper_detected` |
| 3 | `SHOT_DETECTED` | `shot_detected is True` |
| 4 | `BALL_MOVING` | `motion_detected is True` |
| 5 | `BALL_STATIONARY` | `motion_detected is False` |
| 6 (mais baixa) | `UNKNOWN` | `motion_detected is None` (primeira observação) |

Ausência de bola tem prioridade sobre ausência de goleiro (sem bola, não há jogada para classificar); ausência de goleiro tem prioridade sobre chute detectado (a cena está incompleta sem o goleiro visível, mesmo que um chute genuíno esteja ocorrendo).

- **`sub_state`** — refinamento OPCIONAL e independente (`PlaySituation | None`) sobre a direção do movimento observado, populado sempre que `motion_detected is True` (mesmo quando `shot_detected` ainda é `False`):

```python
@staticmethod
def _classify_direction(motion_detected, towards_goal):
    if motion_detected is not True:
        return None
    if towards_goal is True:
        return PlaySituation.SHOT_TOWARDS_GOAL
    if towards_goal is False:
        return PlaySituation.SHOT_AWAY_FROM_GOAL
    return None
```

## Critérios utilizados — combinar, nunca recalcular

| Campo do resultado | Fonte |
|---|---|
| `ball_detected`/`goalkeeper_detected` | ecoados de `GoalkeeperBallAlignmentResult` |
| `shot_detected`/`motion_detected` (usado na árvore, não exposto) | ecoados de `ShotAnalysisResult` |
| `towards_goal` (usado no `sub_state`, não exposto) | ecoado de `ShotAnalysisResult` |
| `trajectory_detected` | ecoado de `BallTrajectoryResult` |
| `alignment_detected` | `alignment.alignment_offset is not None` (`GoalkeeperBallAlignmentResult`) |
| `confidence` | `min(shot.confidence, trajectory.confidence, alignment.confidence, goal_geometry.confidence)` quando os quatro estão disponíveis, `None` caso contrário |

**Achado durante a implementação:** `ShotAnalyzer.towards_goal` (W19) pode ser `True` para uma bola PARADA — quando `direction_vector` é o vetor nulo, `angle_between()` devolve 0° por convenção matemática para vetores degenerados (comportamento correto da função, mas enganoso se interpretado como "movimento real em direção ao gol"). Sem o guard `motion_detected is True` em `_classify_direction`, `sub_state=SHOT_TOWARDS_GOAL` apareceria junto de `situation=BALL_STATIONARY`. Corrigido com o guard explícito acima; documentado como **Risco 36** na Constituição — qualquer consumidor futuro de `towards_goal` precisa do mesmo cuidado.

**Deliberadamente NÃO implementados nesta sprint:** `BALL_INSIDE_GOAL_AREA`/`BALL_INSIDE_PENALTY_AREA` (mencionados como exemplos na especificação da sprint) exigiriam compor `BallPositionAnalyzer` diretamente (que já calcula `inside_goal_area`/`inside_penalty_area`) — fora da lista explícita de quatro Analyzers a reutilizar nesta sprint (`ShotAnalyzer`/`BallTrajectoryAnalyzer`/`GoalkeeperBallAlignmentAnalyzer`/`GoalGeometryAnalyzer`). Adicioná-los exigiria ou recalcular essa informação ou estourar a composição combinada — ambos violam a regra "reutilizar apenas resultados já produzidos, nunca recalcular" desta sprint. Documentado honestamente no docstring de `PlaySituation`.

## Testes — 383/383 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `PlaySituationResult.to_dict()` com/sem chute detectado |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `PlaySituationAnalyzer` registrado e resolvido corretamente |
| `PlaySituationAnalyzer` (real, sem mock) | `tests/analyzers/test_play_situation.py` | Sem bola; sem goleiro; ausência de bola tem prioridade sobre ausência de goleiro; primeira observação é `UNKNOWN`; bola parada (`sub_state=None`, nunca inventa direção); bola em movimento abaixo do limiar de chute com `sub_state=SHOT_TOWARDS_GOAL`; bola se afastando do gol com `sub_state=SHOT_AWAY_FROM_GOAL`; chute detectado com `sub_state=SHOT_TOWARDS_GOAL`; **transições** entre estados ao longo de uma sequência real de frames (`UNKNOWN → BALL_MOVING → SHOT_DETECTED`); bola desaparecendo no meio da sequência; composição interna sem depender do Registry; `reset()` limpa o estado dos Analyzers compostos; metadata correta |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_play_situation_analyzer_produces_a_coherent_result` | Detector stub emite goleiro parado + bola se movendo 5px/frame; `WORKER_ANALYZERS=play_situation` sozinho; confirma tipos/coerência do resultado |
| Regressão | Todos os 365 testes anteriores (W1-W20) | Sem alteração de comportamento não intencional |

Confirmado via `pytest`: `383 passed`.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores (volume Docker persistido entre sessões). Gerei um vídeo real (640×480, 5fps, 10 frames) com um círculo se movendo, upload real via `httpx`.

Rodei `python -m worker.main` com os **nove** Analyzers ativos (`goalkeeper_presence,goal_geometry,goalkeeper_position,ball_position,goalkeeper_ball_alignment,ball_motion,shot,ball_trajectory,play_situation`). Log real confirmou o ciclo completo (`JobStarted → download → VideoDownloaded → upload → UploadFinished → JobCompleted`).

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
analysis_statistics: {'analyzers_run': [... 9 nomes incluindo 'play_situation'], 'results_count': 9}

play_situation_result:
  situation: no_ball_visible
  sub_state: None
  ball_detected: False
  goalkeeper_detected: False
  shot_detected: False
  trajectory_detected: False
  alignment_detected: False
  confidence: None

matches analysis_results['play_situation']: True
```

**Confirmado o comportamento honesto esperado:** o YOLO real não detectou bola nem goleiro neste vídeo sintético (mesma variabilidade já observada desde a W12) — todos os nove Analyzers rodaram corretamente juntos na mesma execução da pipeline, e `play_situation_result` refletiu fielmente a ausência de ambos os atores via `NO_BALL_VISIBLE` (prioridade correta sobre `NO_GOALKEEPER_VISIBLE`, já que os dois estavam ausentes). Lock liberado, fila sem pendências (`XPENDING=0`), Job `COMPLETED`. Stack derrubado ao final (volume preservado); `.env` do Worker removido após a validação.

## Riscos (Constituição, Seção 14)

**Riscos 34/35 (W19/W20) permanecem inalterados** — `PlaySituationAnalyzer` só ecoa `towards_goal`/`trajectory_length` já calculados, nunca recalcula geometria nem introduz novo descompasso de escala.

36. **`ShotAnalyzer.towards_goal` pode ser `True` para uma bola parada** — descrito acima ("Achado durante a implementação"). Não é um bug de `ShotAnalyzer` (o campo é calculado corretamente segundo sua própria definição via `angle_between()`), mas uma armadilha para qualquer consumidor que não verifique `motion_detected` primeiro. `PlaySituationAnalyzer` já aplica o guard correto; documentado para que Analyzers futuros que consumam `towards_goal` diretamente façam o mesmo.

## Preparação para a W22

A W22 (renomeada nesta revisão — antes seria "W21") continua sendo a primeira sprint a introduzir avaliação de QUALIDADE. A W21 confirmou, pela nona vez consecutiva, que um novo Analyzer se encaixa sem exigir nenhuma mudança estrutural — inclusive quando compõe QUATRO Analyzers (dois deles já compostos) sem manter nenhum estado próprio. `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W22, incluindo o guard de `towards_goal` (Risco 36) que qualquer novo Analyzer precisará replicar se consumir esse campo diretamente.
