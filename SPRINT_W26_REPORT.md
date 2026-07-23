# SPRINT_W26_REPORT.md — Goalkeeper AI Worker: Goalkeeper Coaching Analyzer

> Escopo: construir `GoalkeeperCoachingAnalyzer` — primeiro Analyzer de COACHING. Responde APENAS "qual orientação técnica pode ser extraída desta jogada?", interpretando `GoalkeeperPerformanceEvaluation` (W25) + `GoalkeeperDecisionEvaluationResult.rules_failed` (W23) + `GoalkeeperDecision` (W22) + `PlayOutcome` (W24) via a MESMA infraestrutura de Rule Evaluation da W23/W25. Ainda **sem** linguagem natural, **sem** relatório final. **Constituição atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` e `SPRINT_W25_REPORT.md` antes de implementar. Cadeia completa desta arquitetura: **Observação (W13-W20) → Situação (W21) → Decisão (W22) → Avaliação da Decisão (W23) → Resultado (W24) → Avaliação de Desempenho (W25) → Coaching (W26)**. Cada camada só combina a anterior, nunca a modifica ou reinterpreta.

- **`worker/analyzers/goalkeeper_coaching.py`** (novo) — `GoalkeeperCoachingAnalyzer(Analyzer)`: décima quarta implementação concreta, quarto combinador puro sem `AnalyzerContext` próprio.
- **`worker/analyzers/types.py`** — `GoalkeeperCoaching(str, Enum)` adicionado (10 valores).
- **`worker/analyzers/results.py`** — `GoalkeeperCoachingResult(AnalysisResult)` adicionado.
- **`worker/analyzers/registry.py`** — `register_analyzer("goalkeeper_coaching", ...)`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goalkeeper_coaching_result"`.

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, `worker.analyzers.rules`, `worker/config/settings.py`, ou nos quatro Analyzers compostos. Nenhum campo numérico novo em `WorkerSettings`.

## GoalkeeperCoachingAnalyzer

Compõe QUATRO Analyzers — `GoalkeeperPerformanceEvaluationAnalyzer`, `GoalkeeperDecisionEvaluationAnalyzer`, `PlayOutcomeAnalyzer`, `GoalkeeperDecisionAnalyzer` — e, diferente da W25 (onde dois dos quatro compostos só contribuíam para `confidence`), **todos os quatro contribuem com conteúdo real**: `performance` (do primeiro), `decision_evaluation.rules_passed`/`rules_failed` (do segundo, para identificar desvios específicos), `outcome` (do terceiro) e `decision` (do quarto, o comportamento bruto observado do goleiro).

`confidence` = `min()` das quatro confidências compostas, só quando todas disponíveis.

## Rule Evaluation reutilizada — segunda vez consecutiva

**Nenhum mecanismo novo foi criado.** `_CoachingContext` (dataclass frozen com `performance`/`decision_evaluation`/`decision`/`outcome`/`decision_evaluation_rules_passed`/`decision_evaluation_rules_failed`) é avaliado pelas mesmas `Rule`/`RuleOutcome`/`evaluate_rules` (W23), sem nenhuma mudança no módulo genérico. 8 regras novas, específicas de coaching:

| Regra | O que verifica |
|---|---|
| `evaluation_available` | espelha o 1º gate da W25: `performance != INSUFFICIENT_INFORMATION` |
| `decisive_performance_established` | espelha o 2º gate da W25: `performance != UNKNOWN` |
| `performance_was_reinforcement` | `performance` em `{EXCELLENT, GOOD}` |
| `conceded_goal_without_active_response` | `outcome == GOAL` e `decision` não é uma reação ativa |
| `committed_without_shot` | `no_dive_without_shot` (W23) está em `rules_failed` — mergulho sem chute |
| `reacted_passively_to_shot` | `shot_prompts_active_response` (W23) está em `rules_failed` — chute sem reação ativa |
| `dived_wrong_direction` | `dive_direction_matches_ball_direction` (W23) está em `rules_failed` — mergulho no lado errado |
| `recovery_was_insufficient` | `decision == RECOVER_POSITION` e desempenho ainda não foi de reforço |

**Achado técnico corrigido durante a implementação:** `GoalkeeperDecisionEvaluationResult.rules_evaluated` sempre lista os 6 ids das regras da W23, independentemente de aplicabilidade (`evaluate_rules()` produz um `RuleOutcome` por `Rule` mesmo quando `passed is None`). A primeira versão das regras de coaching checava `"x" in rules_evaluated` para decidir aplicabilidade — sempre verdadeiro, portanto errado. Corrigido para checar `"x" in rules_passed or "x" in rules_failed` (união de resultados com `passed is not None`), que é a definição correta de "regra aplicável".

## A agregação num veredito único

Dois gates (espelhando a W25) + um caso de REFORÇO + cinco regras específicas em ordem de PRIORIDADE fixa + fallback residual:

| Prioridade | `GoalkeeperCoaching` | Condição |
|---|---|---|
| 1 (mais alta) | `INSUFFICIENT_INFORMATION` | `evaluation_available` falhou |
| 2 | `UNKNOWN` | `decisive_performance_established` falhou |
| 3 | `NO_FEEDBACK` / `KEEP_POSITION` | `performance_was_reinforcement` — `NO_FEEDBACK` se `EXCELLENT`, `KEEP_POSITION` se `GOOD` |
| 4 | `ATTACK_BALL` | gol sofrido sem reação ativa |
| 5 | `MOVE_LATER` | mergulho sem chute detectado |
| 6 | `MOVE_EARLIER` | chute sem reação ativa |
| 7 | `STAY_PATIENT` | mergulho na direção errada |
| 8 | `RECOVER_FASTER` | reposicionamento insuficiente |
| 9 (mais baixa, fallback) | `IMPROVE_POSITIONING` | nenhuma regra específica satisfeita |

Quando mais de uma regra específica é satisfeita simultaneamente (ex.: reação passiva a um chute que termina em gol), a mais severa/concreta prevalece por desempate documentado, não por ambiguidade.

## Explicabilidade — `summary` estruturado, não linguagem natural

Mesmo princípio da W25: `summary` é `"coaching=...; performance=...; decision=...; outcome=...; contributing_rules=..."` — nunca prosa, mesmo numa sprint de COACHING. `rules_evaluated`/`rules_passed`/`rules_failed` completam a explicabilidade.

## Achado estrutural (não um bug): `ATTACK_BALL` é inalcançável via composição real completa

`conceded_goal_without_active_response` (a regra por trás de `ATTACK_BALL`) exige `outcome == GOAL` e `decision` fora de `{PREPARE_DIVE, DIVE_LEFT, DIVE_RIGHT}`. Mas `PlayOutcome.GOAL` (W24) só é produzido quando `shot_detected=True` no mesmo frame, e `GoalkeeperDecisionAnalyzer` (W22) **sempre** classifica uma reação ativa quando `shot_detected=True`, por construção da sua própria árvore de decisão. Logo `decision` nunca fica fora do conjunto de reações ativas no mesmo frame em que `outcome == GOAL` — a regra é estruturalmente garantida a nunca disparar via composição real, mesmo padrão do Risco 38 (W23). Testado diretamente na agregação pura (`test_classify_attack_ball_when_goal_conceded_without_active_response`); documentado honestamente no código e na Constituição, não escondido. **Nenhum Risco numerado novo foi necessário** — não é uma limitação de dado real, é uma consequência lógica do design já existente.

## Testes — 489/489 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `GoalkeeperCoachingResult.to_dict()` (caso `attack_ball`, caso `insufficient_information`) |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | Analyzer registrado e resolvido corretamente |
| `GoalkeeperCoachingAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_coaching.py` | `INSUFFICIENT_INFORMATION` (nada visível); `UNKNOWN` (primeira observação); `NO_FEEDBACK` (performance `EXCELLENT`, reaproveitando a sequência SAVE da W25); `IMPROVE_POSITIONING` (performance `ADEQUATE`, decisão já ativa, reaproveitando a sequência GOAL da W25); explicações presentes para as 8 regras; composição interna dos quatro Analyzers sem depender do Registry; `reset()` limpa estado composto; metadata |
| Agregação pura (`_classify`) | mesmo arquivo | as 10 orientações cobertas via `RuleOutcome`s sintéticos diretos (mesmo padrão da W23/W25) — incluindo `ATTACK_BALL` (estruturalmente inalcançável por composição real) e o desempate de prioridade quando duas regras específicas disparam ao mesmo tempo |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goalkeeper_coaching_analyzer_produces_a_coherent_result` | Detector stub com goleiro parado + bola se movendo; `WORKER_ANALYZERS=goalkeeper_coaching` sozinho; confirma tipos/coerência |
| Regressão | Todos os 478 testes anteriores (W1-W25) | Sem alteração de comportamento não intencional |

## Validação manual — stack real, cadeia completa até o R2

Subi o stack real (Postgres + Redis + backend, volume persistido), reutilizei usuário/goleiro/sessão (`treinador-w7@example.com`). Gerei um vídeo real e fiz upload. Rodei `python -m worker.main` com os **catorze** Analyzers ativos (`WORKER_ANALYZERS` completo).

```
analysis_statistics: {'analyzers_run': [... 14 nomes], 'results_count': 14}

goalkeeper_coaching_result:
  coaching: insufficient_information
  performance: insufficient_information
  decision_evaluation: insufficient_information
  decision: unknown
  outcome: lost_track
  rules_evaluated: [8 rule ids]
  rules_passed: []
  rules_failed: ['evaluation_available']
  summary: coaching=insufficient_information; performance=insufficient_information; decision=unknown; outcome=lost_track; contributing_rules=none
  confidence: None

matches analysis_results['goalkeeper_coaching']: True
```

Mesmo comportamento real de detecção observado nas validações da W24/W25 (YOLO rastreando a bola por parte do vídeo e depois perdendo o rastreamento, produzindo `lost_track` genuíno) propagou corretamente por toda a cadeia de 14 Analyzers. Artefato no R2 confirmado idêntico entre `goalkeeper_coaching_result` e `analysis_results['goalkeeper_coaching']`. Job `COMPLETED`, lock liberado (0 chaves), fila sem pendências. Stack derrubado via `docker compose down` (volume preservado), `.env` do worker removido.

## Riscos (Constituição, Seção 14)

**Nenhum risco novo.** Riscos 34-39 permanecem inalterados e não se agravam — esta sprint não introduz nenhum cálculo geométrico novo. O achado estrutural sobre `ATTACK_BALL` (acima) foi documentado no código e na Constituição, mas não recebeu numeração de Risco — não é uma limitação/calibração pendente, é uma consequência lógica garantida do design já existente (mesma categoria do Risco 38).

## Preparação para a W27

A W26 encerra a cadeia de COACHING (uma única camada: Situação→Decisão→Avaliação da Decisão→Resultado→Avaliação de Desempenho→Coaching) e confirma, pela segunda vez, que `worker.analyzers.rules` é reutilizável por Analyzers inteiramente diferentes — incluindo, pela primeira vez, um Analyzer que lê a Explainability (`rules_passed`/`rules_failed`) de outro Analyzer composto como parte da própria entrada, não só o veredito agregado. A W27 (ainda não especificada) poderá introduzir o primeiro relatório final/saída em linguagem natural — uma mudança de NATUREZA (texto legível por humanos, não só enums/strings estruturadas), diferente de todas as sprints anteriores. `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W27.
