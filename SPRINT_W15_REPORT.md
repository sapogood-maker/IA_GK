# SPRINT_W15_REPORT.md — Goalkeeper AI Worker: Goalkeeper Position Analyzer

> Escopo: construir o primeiro Analyzer que mede a relação geométrica entre goleiro e gol — `GoalkeeperPositionAnalyzer`, o primeiro a COMPOR outro Analyzer (`GoalGeometryAnalyzer`, W14) internamente. Ainda **sem** avaliação de qualidade, sem julgamento de posicionamento correto — só mede. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W14_REPORT.md` antes de implementar.

- **`worker/analyzers/goalkeeper_position.py`** (novo) — `GoalkeeperPositionAnalyzer(Analyzer)`: terceira implementação concreta da Analyzer API, e a primeira a compor outro Analyzer.
- **`worker/analyzers/results.py`** — `GoalkeeperPositionResult(AnalysisResult)` adicionado (14 campos, ver abaixo).
- **`worker/analyzers/registry.py`** — `register_analyzer("goalkeeper_position", GoalkeeperPositionAnalyzer)` adicionado, sem nenhuma outra mudança.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goalkeeper_position_result"` (alias de conveniência de `analysis_results["goalkeeper_position"]`).

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, `GoalGeometryAnalyzer`, `Detector`, `Tracker`, `SceneAnalyzer` ou qualquer outro módulo além dos listados acima — conforme exigido pela sprint.

## Composição com GoalGeometryAnalyzer

Seguindo o padrão oficial definido na W14 (Seção 6.5/16 da Constituição):

```python
class GoalkeeperPositionAnalyzer(Analyzer):
    def __init__(self, settings: WorkerSettings) -> None:
        self._geometry_analyzer = GoalGeometryAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        goal_geometry = self._geometry_analyzer.analyze(football_world)
        ...
```

Nenhum canal especial entre Analyzers foi criado; `ProcessorContext` não foi alterado. Validado que `GoalkeeperPositionAnalyzer` funciona corretamente mesmo quando `WORKER_ANALYZERS` contém **apenas** `"goalkeeper_position"` (sem `"goal_geometry"` na lista) — a composição é inteiramente interna e independente da configuração/Registry.

## GoalkeeperPositionResult — geometria utilizada

| Campo | Cálculo | Fonte |
|---|---|---|
| `goalkeeper_detected`/`goal_detected` | presença em `FootballWorld.goalkeepers`/`GoalGeometryResult.goal_detected` | — |
| `distance_to_goal_center` | `domain.geometry.coordinate.distance(goalkeeper.position, goal_center)` | distância euclidiana |
| `lateral_offset` | `goalkeeper.position.y - goal_center.y` | deslocamento ao longo do vão do gol |
| `depth_offset` | `goalkeeper.position.x - goal_center.x` | deslocamento em profundidade (para dentro do campo) |
| `angle_to_goal` | `Vector.between(goalkeeper.position, goal_center).angle_degrees()` | ângulo puro, 0–360° |
| `inside_goal_area`/`inside_penalty_area` | `Region.contains(goalkeeper.position)` contra retângulos derivados de **proporções oficiais fixas de campo** (5.5m/16.5m, convertidas em múltiplos de `goal_height`) | mesma disciplina de proporção fixa e documentada de `Goal.default_pair()` (W12) — nunca medidas do vídeo real |
| `covers_left_post`/`covers_center`/`covers_right_post` | o vão do gol dividido em 3 terços iguais (eixo y); qual terço contém `goalkeeper.position.y` | **convenção determinística e arbitrária**: y menor = poste esquerdo (sem calibração de câmera/direção conhecida) |
| `goalkeeper_position`/`goal_center` | ecoam `goalkeeper.position`/`goal_geometry.goal_center` | conveniência |
| `confidence` | `min(goalkeeper.confidence, goal_geometry.confidence)` | combinação determinística de dois sinais reais — nunca um valor inventado |

Falta goleiro OU gol: todo campo que dependeria dos dois é explicitamente `None` — nunca um valor inventado. `goalkeeper_position`/`goal_center` são preenchidos quando o lado correspondente está disponível, mesmo que o outro não esteja.

**Nenhuma avaliação, nenhum julgamento:** os booleanos `inside_goal_area`/`covers_left_post`/etc. são medições geométricas de containment/alinhamento, nunca uma afirmação de que a posição é "boa" ou "ruim".

## Testes — 285/285 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `GoalkeeperPositionResult.to_dict()` com/sem ambos detectados |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `GoalkeeperPositionAnalyzer` registrado e resolvido corretamente |
| `GoalkeeperPositionAnalyzer` (real, sem mock) | `tests/analyzers/test_goalkeeper_position.py` | Sem goleiro e sem gol (tudo `None`); gol sem goleiro; goleiro sem gol; geometria completa com goleiro centrado (distância/offset/ângulo/áreas/terços corretos, valores calculados à mão conferidos); goleiro longe do gol → fora de ambas as áreas; goleiro nos extremos → `covers_left_post`/`covers_right_post` corretos; `confidence = min(...)`; composição interna funciona sem depender do Registry (`analyzer._geometry_analyzer` é uma instância real de `GoalGeometryAnalyzer`); metadata correta |
| Integração com `AnalyzerProcessor` (real, sem mock) | `test_goalkeeper_position.py` (via `FootballWorld` sintético) | — |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goalkeeper_position_analyzer_produces_a_coherent_result` | `WORKER_ANALYZERS=goalkeeper_position` (SEM `goal_geometry`) — prova que a composição funciona na pipeline real mesmo sem o outro Analyzer ativo; artefato contém `"goalkeeper_position_result"` coerente, idêntico a `analysis_results["goalkeeper_position"]` |
| Regressão | Todos os 271 testes anteriores (W1-W14) | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `285 passed` (suíte completa exceto `tests/infrastructure/`, dependente de um container Redis descartável já encerrado após a validação manual).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/analyzers/goalkeeper_position.py tests/analyzers/test_goalkeeper_position.py` → nenhuma menção.
- `grep -n "YOLO\|ByteTrack\|Tracker\|WorldState\|Detector\|cv2\|redis\|SceneAnalyzer" worker/analyzers/goalkeeper_position.py` → nenhuma menção real, nenhum `import`.
- Todos os `import`s reais: `time` (stdlib) + `worker.analyzers.base`/`goal_geometry`/`results`/`types` + `worker.config.settings` + `worker.domain.football_world`/`worker.domain.geometry.coordinate`/`worker.domain.geometry.region`/`worker.domain.geometry.vector`. O `import` de `worker.analyzers.goal_geometry` é composição DENTRO da própria família de Analyzers, não uma dependência de camada inferior.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores. Gerei um vídeo real de 10 frames (640×480, 5fps) com um círculo vermelho se movendo, upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true`, `WORKER_FOOTBALL_DOMAIN_ENABLED=true`, `WORKER_ANALYZERS=goalkeeper_presence,goal_geometry,goalkeeper_position`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model', 'football_domain', 'analyzer']
analysis_statistics: {'analyzers_run': ['goal_geometry', 'goalkeeper_position', 'goalkeeper_presence'], 'results_count': 3}

goalkeeper_position_result:
  goalkeeper_detected: False
  goal_detected: True
  distance_to_goal_center: None
  lateral_offset: None
  ...(todos os campos geometricos: None)
  goal_center: {'x': 0.01, 'y': 0.5}
  confidence: None

matches analysis_results['goalkeeper_position']: True
```

**Confirmado exatamente o comportamento honesto esperado:** o YOLO real, neste vídeo, não detectou nenhum objeto rotulado "goalkeeper" (mesma limitação já documentada desde a W12, Risco 23) — `goalkeeper_detected=False`, `goal_detected=True` (Field/Goal sempre construídos pelo `FootballWorldBuilder`), e TODO campo geométrico que dependeria de ambos explicitamente `None`, nunca um valor inventado. `goalkeeper_position_result` bate exatamente com `analysis_results["goalkeeper_position"]`. O caminho "positivo" (goleiro + gol detectados, geometria completa) já está coberto pelo teste de integração com Detector stub rotulado "goalkeeper" (`test_engine_with_goalkeeper_position_analyzer_produces_a_coherent_result`), que roda a cadeia real de Tracker/SceneAnalyzer/WorldModel/FootballDomain/Analyzer com `WORKER_ANALYZERS=goalkeeper_position` sozinho — confirmando a composição interna também dentro da pipeline real. Lock liberado, fila sem pendências (`XPENDING`=0), Job `COMPLETED`. Stack derrubado ao final (volume preservado).

## Riscos (novos, registrados na Constituição — Seção 14)

28. **`GoalkeeperPositionAnalyzer` herda a limitação do Risco 26 sem resolvê-la** — lê sempre `football_world.goals[0]` (o gol esquerdo por construção), não uma lógica de "qual gol o goleiro defende". Um goleiro real no gol direito teria todas as medidas calculadas contra o gol errado.
29. **Proporções de área de meta/pênalti (5.5m/16.5m) e a correspondência "y menor = poste esquerdo" são convenções fixas, não medidas do vídeo real** — geometricamente corretas EM RELAÇÃO à geometria placeholder atual, mas não correspondem necessariamente à realidade física até que exista calibração de câmera.

## Preparação para a W16

A W16 ainda não tem escopo definido (qual análise entra primeiro com julgamento/avaliação real). O que já está confirmado, pela oitava repetição consecutiva do padrão de encaixe (W8 a W15): um novo Analyzer exige **apenas** escrever `XAnalyzer(Analyzer)`, registrá-lo, incluir seu nome em `WORKER_ANALYZERS` — nunca uma mudança em `AnalyzerProcessor`/pipeline/famílias de Plugin existentes. A W15 confirmou EM PRODUÇÃO (não só em teoria) o padrão de composição entre Analyzers definido na W14. A partir da W16, a lógica introduzida terá semântica de JULGAMENTO em vez de apenas medir/relatar fatos — esta é a primeira sprint em que avaliação/heurística de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
