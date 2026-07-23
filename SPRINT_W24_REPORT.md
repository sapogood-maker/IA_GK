# SPRINT_W24_REPORT.md — Goalkeeper AI Worker: Play Outcome Analyzer

> Escopo: construir `PlayOutcomeAnalyzer` — encerra a cadeia de observação do sistema. Responde APENAS "qual foi o resultado observado da jogada?", combinando cinco Analyzers já existentes. Ainda **sem** avaliar o goleiro, atribuir nota, ou julgar a qualidade da decisão. **Constituição atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` e `SPRINT_W23_REPORT.md` antes de implementar. Cadeia completa desta arquitetura: **Observação (W13-W20) → Situação (W21) → Decisão (W22) → Avaliação (W23) → Resultado (W24)**. Cada camada só combina a anterior, nunca a modifica ou reinterpreta.

- **`worker/analyzers/play_outcome.py`** (novo) — `PlayOutcomeAnalyzer(Analyzer)` + `PlayOutcomeContext(AnalyzerContext)`: décima segunda implementação concreta, quinto Analyzer STATEFUL.
- **`worker/analyzers/types.py`** — `PlayOutcome(str, Enum)` adicionado (10 valores).
- **`worker/analyzers/results.py`** — `PlayOutcomeResult(AnalysisResult)` adicionado.
- **`worker/config/settings.py`** — 2 campos novos: `outcome_post_proximity_px`, `outcome_save_proximity_px`.
- **`worker/analyzers/registry.py`** — `register_analyzer("play_outcome", ...)`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"play_outcome_result"`.

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, `worker.analyzers.rules`, ou nos cinco Analyzers compostos.

## PlayOutcomeAnalyzer

Compõe CINCO Analyzers — `PlaySituationAnalyzer`, `ShotAnalyzer`, `BallTrajectoryAnalyzer`, `GoalGeometryAnalyzer`, `GoalkeeperDecisionAnalyzer` — combinando apenas resultados já produzidos. Usa `Region.contains()`/`distance()` (utilitários geométricos puros, reutilizados desde a W12) para as checagens de containment/proximidade — nunca a LÓGICA de outro Analyzer. Lê `football_world.field.region` DIRETAMENTE (permitido — todo Analyzer conhece `FootballWorld`) para o critério `BALL_OUT`, sem precisar compor nenhum Analyzer adicional só para isso.

## Estado — quinto `AnalyzerContext`

```python
@dataclass
class PlayOutcomeContext(AnalyzerContext):
    was_tracking: bool = False
    last_known_ball_position: Coordinate | None = None
    last_known_goalkeeper_position: Coordinate | None = None
```

`last_known_ball_position`/`last_known_goalkeeper_position` sobrevivem a um frame em que a bola/o goleiro momentaneamente não é detectado — essencial para `LOST_TRACK` carregar alguma evidência posicional útil, em vez de ficar vazio exatamente no momento em que se torna interessante. `was_tracking` distingue "a bola estava sendo rastreada e sumiu" (`LOST_TRACK`) de "a bola nunca apareceu" (`INSUFFICIENT_INFORMATION`).

## Critérios utilizados — árvore de decisão priorizada

| Prioridade | `outcome` | Condição |
|---|---|---|
| 1 (mais alta) | `INSUFFICIENT_INFORMATION` | geometria do gol não disponível |
| 2 | `LOST_TRACK` | bola ausente agora, mas rastreada no frame anterior |
| 3 | `INSUFFICIENT_INFORMATION` | bola ausente e nunca foi rastreada |
| 4 | `UNKNOWN` | bola detectada, sem histórico suficiente (primeira observação) |
| 5 | `NO_SHOT_DETECTED` | nenhum chute detectado ainda |
| 6 (mais baixa) | `GOAL` > `POST` > `SAVE` > `BLOCKED` > `BALL_OUT` > `UNKNOWN` (fallback) | chute detectado — classificação geométrica nesta ordem |

**Critério geométrico (só quando `shot_detected=True`):**
- **GOAL**: última posição da bola dentro de alguma zona de `GoalGeometryResult.goal_regions` (grade 2×3, W14).
- **POST**: última posição da bola a `WORKER_OUTCOME_POST_PROXIMITY_PX` (default 15.0px) de `left_post`/`right_post`.
- **SAVE**: goleiro a `WORKER_OUTCOME_SAVE_PROXIMITY_PX` (default 30.0px) da última posição da bola.
- **BLOCKED**: trajetória registrou pelo menos uma mudança de direção (`BallTrajectoryResult.direction_changes >= 1`, W20) — sugere desvio.
- **BALL_OUT**: última posição da bola fora de `football_world.field.region`.
- **UNKNOWN** (fallback): nenhuma condição acima bateu — bola ainda "em voo".

## Explicabilidade — mais simples que a Rule Evaluation da W23

Por instrução explícita, `PlayOutcomeAnalyzer` **não reutiliza** `worker.analyzers.rules`. `supporting_evidence: list[str]` é construída incrementalmente conforme a árvore é percorrida (ex.: `"chute detectado"`, `"posicao da bola dentro da zona do gol 'top_right'"`) — suficiente para justificar `outcome` sem o aparato completo de `Rule`/`RuleOutcome`.

## Achado durante a implementação: `left_post`/`right_post` nunca foram genuinamente consumidos (Risco 39)

Ao implementar o critério `POST`, descobri que `GoalGeometryResult.left_post`/`right_post` (W14) têm o MESMO `y` (`left_post = Coordinate(x=region.x, y=region.y)`, `right_post = Coordinate(x=region.x+region.width, y=region.y)`) — diferem só ao longo do eixo de PROFUNDIDADE (`region.width`), não ao longo do eixo LATERAL estabelecido pela W15 (`GoalkeeperPositionAnalyzer._covers_thirds`, que divide `region.height`). Nenhum Analyzer entre a W14 e a W23 consumiu esses campos genuinamente — a inconsistência estava dormente. Por instrução desta sprint ("nunca recalcular"), `PlayOutcomeAnalyzer` usa `left_post`/`right_post` exatamente como produzidos. **Consequência direta: `CROSSBAR` é deliberadamente nunca produzido** — o gol é modelado como um retângulo 2D (Risco 22), sem nenhuma dimensão vertical, e não há hoje uma fonte geométrica independente para distinguir "travessão" de "trave". `GoalGeometryAnalyzer` (W14) não foi alterado, conforme instrução explícita de não fazer mudanças estruturais. Documentado como **Risco 39**.

## Testes — 449/449 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `PlayOutcomeResult.to_dict()` com gol/sem bola |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | Analyzer registrado e resolvido corretamente |
| Configuração | `tests/test_settings.py` | os dois limiares configuráveis via env var |
| `PlayOutcomeAnalyzer` (real, sem mock) | `tests/analyzers/test_play_outcome.py` | Ausência de geometria do gol; ausência de bola (nunca apareceu); primeira observação (`UNKNOWN`); `NO_SHOT_DETECTED`; `LOST_TRACK` (com posição preservada); `GOAL`; `POST`; `SAVE`; `BLOCKED`; `BALL_OUT`; `UNKNOWN` (chute detectado, nenhuma condição geométrica atingida); composição interna sem depender do Registry; `reset()`; metadata. Todos os 9 cenários de outcome geométrico foram derivados computacionalmente (sequências de frames reais passadas pelos Analyzers reais) para garantir `shot_detected=True` exatamente no frame de destino, dada a sensibilidade angular de `ShotAnalyzer.towards_goal` perto do gol (Risco 34) |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_play_outcome_analyzer_produces_a_coherent_result` | Detector stub com goleiro parado + bola se movendo; `WORKER_ANALYZERS=play_outcome` sozinho; confirma tipos/coerência |
| Regressão | Todos os 435 testes anteriores (W1-W23) | Sem alteração de comportamento não intencional |

## Validação manual — stack real, DOIS Jobs consecutivos

Subi o stack real (Postgres + Redis + backend, volume persistido), reutilizei usuário/goleiro/sessão. Gerei UM vídeo real e fiz upload DUAS vezes (dois Jobs distintos). Rodei `python -m worker.main` UMA ÚNICA VEZ (mesmo processo), processando os dois Jobs sequencialmente, com os **doze** Analyzers ativos.

Resultado de AMBOS os Jobs (idêntico):

```
analysis_statistics: {'analyzers_run': [... 12 nomes], 'results_count': 12}

play_outcome_result:
  outcome: lost_track
  play_situation: no_ball_visible
  shot_detected: False
  ball_detected: False
  ball_visible: False
  goal_visible: True
  ball_last_position: {'x': 216.5, 'y': 240.0}
  goalkeeper_last_position: None
  supporting_evidence: ['bola estava sendo rastreada e desapareceu neste frame']
  confidence: None
```

**Achado interessante da validação real:** pela primeira vez desde a W12, o YOLO real DETECTOU a bola por parte do vídeo (o suficiente para estabelecer `trajectory_detected=True`) e depois a perdeu nos últimos frames — produzindo um `LOST_TRACK` genuíno com evidência posicional real (`ball_last_position` preservada), não apenas o resultado honesto-vazio usual. Ambos os Jobs, processados sequencialmente no MESMO processo do Worker mas com vídeos diferentes (uploads independentes), produziram resultados IDÊNTICOS e totalmente independentes — confirmando que `PlayOutcomeContext` (e a plumbing genérica de `reset()`) não vaza nenhum estado entre Jobs. Lock liberado, fila sem pendências, ambos os Jobs `COMPLETED`.

## Riscos (Constituição, Seção 14)

**Riscos 34/35/36/37/38 permanecem inalterados.**

39. **`GoalGeometryResult.left_post`/`right_post` não correspondem à real separação lateral dos postes** — descrito acima. `CROSSBAR` permanece deliberadamente nunca produzido.

## Preparação para a W25

A W25 (renomeada nesta revisão — antes seria "W24") é agora a primeira sprint a introduzir avaliação COMPLETA de desempenho, combinando `PlaySituationResult`/`GoalkeeperDecisionResult`/`GoalkeeperDecisionEvaluationResult`/`PlayOutcomeResult`. A W24 confirmou, pela décima segunda vez consecutiva, que um novo Analyzer se encaixa sem exigir nenhuma mudança estrutural — inclusive quando é STATEFUL, compõe cinco Analyzers (incluindo composição redundante de `PlaySituationAnalyzer`, já composto transitivamente por `GoalkeeperDecisionAnalyzer`) e lê `FootballWorld` diretamente para fatos simples. `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W25.
