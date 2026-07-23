# SPRINT_W23_REPORT.md — Goalkeeper AI Worker: Goalkeeper Decision Evaluation Analyzer

> Escopo: construir `GoalkeeperDecisionEvaluationAnalyzer` — o primeiro Analyzer de AVALIAÇÃO. Responde APENAS "a decisão observada do goleiro (W22) foi compatível com a situação observada (W21)?", via um mecanismo explícito e auditável de Rule Evaluation. Ainda **sem** avaliar o resultado da jogada, sem afirmar se houve defesa ou gol. **Constituição atualizada durante a própria implementação.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md` e `SPRINT_W22_REPORT.md` antes de implementar. Separação rigorosa de camadas: **Observação → Situação → Decisão → Avaliação** — esta sprint nunca modifica ou reinterpreta os resultados anteriores, só os combina.

- **`worker/analyzers/rules.py`** (novo, módulo genérico) — mecanismo de **Rule Evaluation**: `Rule[T]`, `RuleOutcome`, `evaluate_rules()`. Não pertence a nenhum Analyzer específico — reutilizável por qualquer Analyzer de avaliação futuro.
- **`worker/analyzers/goalkeeper_decision_evaluation.py`** (novo) — `GoalkeeperDecisionEvaluationAnalyzer(Analyzer)`: décima primeira implementação concreta, primeiro Analyzer de avaliação, sem `AnalyzerContext` próprio.
- **`worker/analyzers/types.py`** — `GoalkeeperDecisionEvaluation(str, Enum)` adicionado (5 valores).
- **`worker/analyzers/results.py`** — `GoalkeeperDecisionEvaluationResult(AnalysisResult)` adicionado.
- **`worker/config/settings.py`** — 1 campo novo: `goalkeeper_evaluation_min_lateral_signal`.
- **`worker/analyzers/registry.py`** — `register_analyzer("goalkeeper_decision_evaluation", ...)`.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goalkeeper_decision_evaluation_result"`.

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, ou nos seis Analyzers compostos.

## Rule Evaluation — mecanismo genérico

```python
@dataclass(frozen=True)
class Rule(Generic[T]):
    id: str
    description: str
    condition: Callable[[T], bool | None]

@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    description: str
    passed: bool | None    # True=satisfeita, False=violada, None=nao aplicavel
    explanation: str

def evaluate_rules(rules: list[Rule[T]], context: T) -> list[RuleOutcome]: ...
```

`condition` é sempre uma função pura, sem efeito colateral. `evaluate_rules()` nunca descarta, reordena ou resume uma regra silenciosamente — cada `Rule` produz exatamente um `RuleOutcome`, sempre com uma `explanation` textual pronta (`f"[{rule.id}] {rule.description} -> {verdict}"`).

## Explainability

Esta sprint inaugura a camada de Explainability: nenhuma conclusão é um estado isolado. `GoalkeeperDecisionEvaluationResult` expõe:

- `rules_evaluated` — todos os `id`s avaliados, mesmo os não aplicáveis
- `rules_passed`/`rules_failed` — só os `id`s com resultado `True`/`False`
- `explanations` — uma frase legível por regra, na mesma ordem

## As 6 regras

| `Rule.id` | Aplicável quando | Verifica |
|---|---|---|
| `actors_visible` | sempre | bola e goleiro visíveis |
| `decision_established` | atores visíveis | `GoalkeeperDecision != UNKNOWN` (histórico suficiente, W22) |
| `shot_prompts_active_response` | `situation == SHOT_DETECTED` | decisão é uma reação ativa (`PREPARE_DIVE`/`DIVE_LEFT`/`DIVE_RIGHT`) |
| `no_dive_without_shot` | decisão é um mergulho | `situation == SHOT_DETECTED` |
| `recover_follows_shot_ending` | decisão é `RECOVER_POSITION` | `situation != SHOT_DETECTED` |
| `dive_direction_matches_ball_direction` | decisão é um mergulho e sinais laterais fortes o bastante (`WORKER_GOALKEEPER_EVALUATION_MIN_LATERAL_SIGNAL`) | lado do mergulho coincide com o lado da direção lateral observada da bola |

## Agregação — `_classify`

| Prioridade | `evaluation` | Condição |
|---|---|---|
| 1 (mais alta) | `INSUFFICIENT_INFORMATION` | `actors_visible` falhou |
| 2 | `UNKNOWN` | `decision_established` falhou (atores visíveis, decisão ainda não estabelecida) |
| 3 | `COMPATIBLE` | nenhuma regra de conteúdo aplicável, ou todas satisfeitas |
| 4 | `INCOMPATIBLE` | todas as regras de conteúdo aplicáveis violadas |
| 5 (mais baixa) | `PARTIALLY_COMPATIBLE` | mistura de satisfeitas/violadas |

## Achado durante a implementação (corrigido antes da validação manual)

A regra `dive_direction_matches_ball_direction` inicialmente lia `shot.direction_vector.dy` diretamente como se fosse o deslocamento lateral cru da bola — mas `ShotAnalysisResult.direction_vector` é ecoado de `BallMotionResult.direction_vector`, que é `velocity.normalized()` (W18), sempre magnitude 1. Um teste falhou revelando isso ANTES da validação manual (`assert "dive_direction_matches_ball_direction" in result.rules_passed` falhava porque o componente normalizado ficava abaixo do limiar de sinal). Corrigido reconstruindo a componente lateral crua: `direction_vector.dy * ball_speed` (ambos já ecoados por `ShotAnalyzer`, nenhuma geometria recalculada, só uma recombinação de dois campos já produzidos).

## Achado arquitetural: a maioria das regras é auditoria garantida por construção

`shot_prompts_active_response`, `no_dive_without_shot` e `recover_follows_shot_ending` não podem falhar sozinhas com os dados hoje disponíveis, porque `GoalkeeperDecisionAnalyzer` (W22) já só produz mergulhos quando `shot_detected=True` e só produz `RECOVER_POSITION` quando `shot_detected=False`. Elas são auditorias de consistência cruzada (úteis para capturar uma futura regressão em qualquer um dos dois lados), não checagens independentes hoje. Consequência: `INCOMPATIBLE` puro não é alcançável via composição real com o conjunto de regras atual — um mergulho com direção incompatível produz `PARTIALLY_COMPATIBLE` (as três regras garantidas concordam, a única independente diverge). A lógica de agregação foi testada diretamente (com um `RuleOutcome` sintético) para confirmar que o caminho `INCOMPATIBLE` está correto quando alcançado. Documentado honestamente como **Risco 38**.

## Testes — 429/429 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Rule Evaluation (genérico) | `tests/analyzers/test_rules.py` | `evaluate_rules()` produz um outcome por regra na ordem certa; explicação reflete o veredito; `condition` recebe o contexto; `to_dict()`; lista vazia |
| Resultados | `tests/analyzers/test_results.py` | `GoalkeeperDecisionEvaluationResult.to_dict()` compatível/insuficiente |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | Analyzer registrado e resolvido corretamente |
| Configuração | `tests/test_settings.py` | limiar de sinal lateral configurável via env var |
| `GoalkeeperDecisionEvaluationAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_decision_evaluation.py` | Ausência de bola/goleiro → `INSUFFICIENT_INFORMATION`; primeira observação → `UNKNOWN`; nenhuma regra de conteúdo aplicável → `COMPATIBLE`; mergulho com direção compatível → `COMPATIBLE`; mergulho com direção incompatível → `PARTIALLY_COMPATIBLE`; sinal lateral fraco → regra marcada não aplicável; explicabilidade (todas as 6 regras sempre reportadas); agregação `INCOMPATIBLE` testada diretamente (cenário sintético, documentado como não alcançável via composição real hoje); composição interna sem depender do Registry; `reset()`; metadata |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goalkeeper_decision_evaluation_analyzer_produces_a_coherent_result` | Detector stub com goleiro + bola móveis; `WORKER_ANALYZERS=goalkeeper_decision_evaluation` sozinho; confirma tipos/coerência, 6 regras sempre presentes |
| Regressão | Todos os 406 testes anteriores (W1-W22) | Sem alteração de comportamento não intencional |

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend, volume persistido), reutilizei usuário/goleiro/sessão. Gerei vídeo real, upload real via `httpx`. Rodei `python -m worker.main` com os **onze** Analyzers ativos. Log real confirmou o ciclo completo.

Artefato real (via `boto3`):

```
analysis_statistics: {'analyzers_run': [... 11 nomes], 'results_count': 11}

goalkeeper_decision_evaluation_result:
  evaluation: insufficient_information
  play_situation: no_ball_visible
  goalkeeper_decision: unknown
  rules_evaluated: ['actors_visible', 'decision_established', 'shot_prompts_active_response',
                    'no_dive_without_shot', 'recover_follows_shot_ending', 'dive_direction_matches_ball_direction']
  rules_passed: []
  rules_failed: ['actors_visible']
  explanations: [... 6 frases explicativas, uma por regra ...]
  confidence: None

matches analysis_results['goalkeeper_decision_evaluation']: True
```

**Confirmado o comportamento honesto e EXPLICÁVEL esperado:** YOLO real não detectou bola/goleiro (mesma variabilidade desde a W12); todas as 11 Analyzers rodaram juntos; o veredito `INSUFFICIENT_INFORMATION` veio acompanhado das 6 explicações completas, provando que a camada de Explainability funciona mesmo no caso honestamente vazio. Lock liberado, fila sem pendências, Job `COMPLETED`.

## Riscos (Constituição, Seção 14)

**Riscos 34/35/36/37 permanecem inalterados.**

38. **A maioria das regras de conteúdo são auditorias garantidas por construção** — descrito acima.

## Preparação para a W24

A W24 (renomeada nesta revisão — antes seria "W23") continua sendo a primeira sprint a introduzir avaliação de QUALIDADE DO RESULTADO da jogada (defesa/gol). A W23 confirmou, pela décima primeira vez consecutiva, que um novo Analyzer se encaixa sem exigir nenhuma mudança estrutural — e entregou um mecanismo genérico de Rule Evaluation (`worker.analyzers.rules`) pronto para ser reutilizado, não reinventado, por qualquer Analyzer de avaliação futuro. `AI_WORKER_CONSTITUTION.md`, Seção 16, já está atualizada com a preparação formal para a W24.
