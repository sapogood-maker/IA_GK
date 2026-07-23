# SPRINT_W25_REPORT.md — Goalkeeper AI Worker: Goalkeeper Performance Evaluation Analyzer

> Escopo: construir `GoalkeeperPerformanceEvaluationAnalyzer` — encerra a cadeia de AVALIAÇÃO do sistema. Responde APENAS "como foi o desempenho observado do goleiro nesta jogada?", cruzando exclusivamente Avaliação da Decisão (W23) + Resultado (W24) numa matriz determinística 3×3. Reutiliza obrigatoriamente a infraestrutura de Rule Evaluation da W23 — nenhum segundo mecanismo de regras. Ainda **sem** recomendação, **sem** coaching. **Constituição atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` e `SPRINT_W24_REPORT.md` antes de implementar. Cadeia completa desta arquitetura: **Observação (W13-W20) → Situação (W21) → Decisão (W22) → Avaliação da Decisão (W23) → Resultado (W24) → Avaliação de Desempenho (W25)**. Cada camada só combina a anterior, nunca a modifica ou reinterpreta.

- **`worker/analyzers/goalkeeper_performance_evaluation.py`** (novo) — `GoalkeeperPerformanceEvaluationAnalyzer(Analyzer)`: décima terceira implementação concreta, terceiro combinador puro sem `AnalyzerContext` próprio.
- **`worker/analyzers/types.py`** — `GoalkeeperPerformanceEvaluation(str, Enum)` adicionado (7 valores).
- **`worker/analyzers/results.py`** — `GoalkeeperPerformanceEvaluationResult(AnalysisResult)` adicionado.
- **`worker/analyzers/registry.py`** — `register_analyzer("goalkeeper_performance_evaluation", ...)`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goalkeeper_performance_evaluation_result"`.

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, `worker.analyzers.rules`, `worker/config/settings.py`, ou nos quatro Analyzers compostos. Nenhum campo numérico novo em `WorkerSettings` — a matriz é puramente categórica.

## GoalkeeperPerformanceEvaluationAnalyzer

Compõe QUATRO Analyzers — `PlaySituationAnalyzer`, `GoalkeeperDecisionAnalyzer`, `GoalkeeperDecisionEvaluationAnalyzer`, `PlayOutcomeAnalyzer` — mas usa apenas os DOIS últimos como fonte de conteúdo (`GoalkeeperDecisionEvaluationResult.evaluation` e `PlayOutcomeResult.outcome`), por instrução explícita da especificação. Os dois primeiros são instanciados e chamados só porque `GoalkeeperDecisionEvaluationAnalyzer`/`PlayOutcomeAnalyzer` já os compõem internamente — existem por completude e contribuem apenas como sinais adicionais de `confidence`, mesmo princípio já usado desde a W20 (`GoalGeometryAnalyzer` em `BallTrajectoryAnalyzer`).

`confidence` = `min()` das quatro confidências compostas (`play_situation`, `decision_result`, `decision_evaluation_result`, `outcome_result`), só quando todas estão disponíveis — nunca fabricado.

## Rule Evaluation reutilizada — mesma infraestrutura da W23

**Nenhum mecanismo novo foi criado.** `_PerformanceContext` (dataclass frozen com apenas `decision_evaluation`/`play_outcome`) é avaliado pelas mesmas `Rule`/`RuleOutcome`/`evaluate_rules` de `worker/analyzers/rules.py` (W23), sem nenhuma mudança no módulo genérico. 8 regras novas, específicas de desempenho:

| Regra | O que verifica |
|---|---|
| `actors_and_geometry_available` | decisão E resultado não são `INSUFFICIENT_INFORMATION` |
| `decisive_event_established` | decisão conhecida (não `UNKNOWN`) E resultado decisivo (não `UNKNOWN`/`LOST_TRACK`/`NO_SHOT_DETECTED`) |
| `decision_fully_compatible` | `decision_evaluation == COMPATIBLE` |
| `decision_partially_compatible` | `decision_evaluation == PARTIALLY_COMPATIBLE` |
| `decision_incompatible` | `decision_evaluation == INCOMPATIBLE` |
| `outcome_is_save` | `play_outcome == SAVE` |
| `outcome_is_neutral` | `play_outcome` em `{POST, BLOCKED, BALL_OUT, CROSSBAR}` |
| `outcome_is_goal` | `play_outcome == GOAL` |

As últimas 6 regras só se aplicam (retornam `None` senão) quando as duas primeiras passaram — mesma disciplina de precondição encadeada já usada na W23.

## A matriz determinística 3×3

| Decisão \ Resultado | `save` | `neutral` | `goal` |
|---|---|---|---|
| `compatible` | EXCELLENT | GOOD | ADEQUATE |
| `partial` | GOOD | ADEQUATE | POOR |
| `incompatible` | ADEQUATE | POOR | CRITICAL |

A diagonal principal (decisão compatível + defesa → EXCELLENT; decisão incompatível + gol → CRITICAL) reflete que o **processo** (a decisão foi correta?) pesa tanto quanto o **resultado observado** (sorte/desfecho) — nunca julga só pelo resultado isolado (um goleiro que erra a decisão mas é salvo pela sorte recebe ADEQUATE, não EXCELLENT) nem só pela decisão isolada (um goleiro correto que sofre gol recebe ADEQUATE, não CRITICAL).

`_classify()` primeiro checa os dois gates (`actors_and_geometry_available=False` → `INSUFFICIENT_INFORMATION`; `decisive_event_established=False` → `UNKNOWN`), depois localiza qual eixo de decisão e qual eixo de resultado foram satisfeitos e consulta a matriz — sempre rastreável até exatamente duas regras.

## Explicabilidade — `summary` estruturado, não linguagem natural

Por instrução explícita ("Sem linguagem natural"), `summary` é uma string estruturada: `"performance=...; decision_evaluation=...; play_outcome=...; contributing_rules=..."` — nunca prosa. `rules_evaluated`/`rules_passed`/`rules_failed` completam a explicabilidade, mesmo padrão da W23.

## Sem `AnalyzerContext` próprio — terceiro combinador puro

`GoalkeeperPerformanceEvaluationAnalyzer` não introduz estado próprio — junta-se a `PlaySituationAnalyzer` (W21) e `GoalkeeperDecisionEvaluationAnalyzer` (W23) como combinador puro. `reset()` delega aos quatro Analyzers compostos (dois genuinamente stateful — `GoalkeeperDecisionAnalyzer`/`PlayOutcomeAnalyzer` — e dois por completude).

## Sem achado de contrato necessário

Diferente de W13/W19/W23/W24, nenhuma extensão de tipo de camada inferior foi necessária — `GoalkeeperDecisionEvaluation`/`PlayOutcome` (W23/W24) já continham tudo que a matriz precisava. **Nenhum Risco novo foi introduzido nesta sprint.**

## Testes — 465/465 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `GoalkeeperPerformanceEvaluationResult.to_dict()` (caso excellent, caso insufficient_information) |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | Analyzer registrado e resolvido corretamente |
| `GoalkeeperPerformanceEvaluationAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_performance_evaluation.py` (11 testes) | `INSUFFICIENT_INFORMATION` (nada visível); `UNKNOWN` (primeira observação); `EXCELLENT` (decisão compatível + `SAVE`, reaproveitando a sequência de frames real da W24); `ADEQUATE` (decisão compatível + `GOAL`, idem); explicações presentes para as 8 regras; composição interna dos quatro Analyzers sem depender do Registry; `reset()` limpa estado composto; metadata |
| Matriz exaustiva (agregação pura) | mesmo arquivo, `test_classify_matrix_covers_all_nine_combinations` | as 9 células da matriz via `RuleOutcome`s sintéticos diretos — mesmo padrão da W23 (`test_classify_incompatible...`) para cobrir combinações difíceis de alcançar via composição real completa; mais os dois gates (`INSUFFICIENT_INFORMATION`/`UNKNOWN`) isoladamente |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goalkeeper_performance_evaluation_analyzer_produces_a_coherent_result` | Detector stub com goleiro e bola se movendo; `WORKER_ANALYZERS=goalkeeper_performance_evaluation` sozinho; confirma tipos/coerência |
| Regressão | Todos os 454 testes anteriores (W1-W24) | Sem alteração de comportamento não intencional |

Nenhuma falha de teste ocorreu nesta sprint — as sequências de frames reais reutilizadas dos cenários SAVE/GOAL da W24 e a cobertura exaustiva da matriz via `_classify()` direto evitaram inteiramente a fragilidade geométrica que exigiu derivação computacional nas W23/W24 (Risco 34).

## Validação manual — stack real, cadeia completa até o R2

Subi o stack real (Postgres + Redis + backend, volume persistido), reutilizei usuário/goleiro/sessão. Gerei um vídeo real e fiz upload. Rodei `python -m worker.main` com os **treze** Analyzers ativos (`WORKER_ANALYZERS` completo).

```
analysis_statistics: {'analyzers_run': [... 13 nomes], 'results_count': 13}

goalkeeper_performance_evaluation_result:
  performance: insufficient_information
  decision_evaluation: insufficient_information
  play_outcome: lost_track
  rules_evaluated: [8 rule ids]
  rules_passed: []
  rules_failed: ['actors_and_geometry_available']
  summary: performance=insufficient_information; decision_evaluation=insufficient_information; play_outcome=lost_track; contributing_rules=none
  confidence: None

matches analysis_results['goalkeeper_performance_evaluation']: True
```

Mesmo comportamento real de detecção observado na validação da W24 (YOLO rastreando a bola por parte do vídeo e depois perdendo o rastreamento, produzindo `lost_track` genuíno) propagou corretamente por toda a cadeia — `play_outcome=lost_track` (não decisivo) fez `decisive_event_established` falhar antes mesmo de chegar lá, mas como `decision_evaluation` também ficou `insufficient_information` (ambos os lados insuficientes), o gate mais alto (`actors_and_geometry_available`) já classificou o resultado corretamente como `insufficient_information`, sem nunca avaliar o segundo gate. Artefato no R2 confirmado idêntico entre `goalkeeper_performance_evaluation_result` e `analysis_results['goalkeeper_performance_evaluation']`. Lock liberado (0 chaves), fila sem pendências, Job `COMPLETED`. Stack derrubado via `docker compose down` (volume preservado), `.env` do worker removido.

## Riscos (Constituição, Seção 14)

**Nenhum risco novo.** Riscos 34-39 permanecem inalterados e não se agravam — esta sprint não introduz nenhum cálculo geométrico novo, nenhuma extrapolação, nenhum novo campo sensível a calibração.

## Preparação para a W26

A W25 encerra a cadeia de AVALIAÇÃO (Situação → Decisão → Avaliação da Decisão → Resultado → Avaliação de Desempenho) e confirma, pela segunda vez, que `worker.analyzers.rules` é genuinamente reutilizável por um Analyzer completamente diferente sem nenhuma mudança no mecanismo. A W26 (ainda não especificada) poderá introduzir a primeira camada de recomendação/coaching — uma mudança de NATUREZA, não só mais uma camada de combinação: pela primeira vez o Worker produziria algo destinado à ação do goleiro, não apenas descrição/classificação/avaliação do que já aconteceu. `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W26.
