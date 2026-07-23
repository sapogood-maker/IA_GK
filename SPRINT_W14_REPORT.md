# SPRINT_W14_REPORT.md — Goalkeeper AI Worker: Goal Geometry Analyzer

> Escopo: construir o primeiro Analyzer puramente geométrico — `GoalGeometryAnalyzer`, que modela a geometria do gol (centro, postes, dimensões, regiões/zonas de cobertura) a partir de `FootballWorld`. Ainda **sem** avaliação de goleiro, defesa, chute, mergulho, reação ou qualquer heurística de futebol. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W13_REPORT.md` antes de implementar.

- **`worker/analyzers/goal_geometry.py`** (novo) — `GoalGeometryAnalyzer(Analyzer)`: segunda implementação concreta da Analyzer API (W13), puramente geométrica.
- **`worker/analyzers/results.py`** — `GoalGeometryResult(AnalysisResult)` adicionado (goal_detected/goal_center/goal_width/goal_height/left_post/right_post/goal_regions/confidence).
- **`worker/analyzers/types.py`** — `GoalZone` (`Enum` de string: `TOP_LEFT`/`TOP_CENTER`/`TOP_RIGHT`/`BOTTOM_LEFT`/`BOTTOM_CENTER`/`BOTTOM_RIGHT`) adicionado, mesmo padrão de `Direction` (`worker/domain/geometry/direction.py`).
- **`worker/analyzers/registry.py`** — `register_analyzer("goal_geometry", GoalGeometryAnalyzer)` adicionado, sem nenhuma outra mudança.
- **`worker/analyzers/processor.py`** — docstring expandida documentando o padrão de composição entre Analyzers (ver abaixo); **zero mudança funcional**.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"goal_geometry_result"` (alias de conveniência de `analysis_results["goal_geometry"]`).

**Nenhuma classe existente foi renomeada. Nenhum contrato público foi alterado** — `Analyzer.analyze(football_world) -> AnalysisResult` é idêntico ao de antes; `AnalyzerProcessor`, `registry.py`/`factory.py` da Analyzer API não precisaram de nenhuma mudança estrutural além da nova linha de registro.

## GoalGeometryResult

| Campo | Fonte | Observação |
|---|---|---|
| `goal_detected` | `len(football_world.goals) > 0` | `False` se nenhum gol no `FootballWorld` |
| `goal_center` | `region.center` | `None` se sem gol |
| `goal_width`/`goal_height` | `region.width`/`.height` | `None` se sem gol |
| `left_post`/`right_post` | cantos superiores esquerdo/direito da região | o "travessão" fica implícito (`left_post.y == right_post.y`) — nenhum campo redundante |
| `goal_regions` | grade 2×3 (`GoalZone`) | `None` se sem gol OU se a região for degenerada (largura/altura ≤ 0) |
| `confidence` | validade ESTRUTURAL do retângulo | `1.0` bem formado, `0.0` degenerado, `None` sem gol algum — **nunca** uma probabilidade de detecção inventada |

## GoalGeometryAnalyzer

```python
class GoalGeometryAnalyzer(Analyzer):
    name = "goal_geometry"
    version = "1.0.0"
    def analyze(self, football_world: FootballWorld) -> AnalysisResult: ...
```

Lê `football_world.goals`. Quando há mais de um candidato (o Football Domain Model, W12, sempre cria os dois gols do campo via `Goal.default_pair()`), escolhe deterministicamente o **primeiro** da lista — mesma regra de ordem já usada por `GoalkeeperPresenceAnalyzer` (W13) para múltiplos candidatos, não uma heurística sobre qual gol é "o relevante" (isso dependeria de saber de que lado o goleiro está — fora de escopo, puramente geométrico).

Divide a região do gol numa grade 2×3 (2 linhas: topo/base; 3 colunas: esquerda/centro/direita) — só aritmética (`region.width / 3`, `region.height / 2`), nenhuma interpretação de qual zona é "melhor" ou "pior" para o goleiro cobrir. Sem gol algum, todo campo geométrico retorna explicitamente `None` — "desconhecido", nunca um valor inventado.

## Padrão de composição entre Analyzers (achado desta sprint)

A meta da sprint pedia que, ao final, fosse possível implementar `GoalkeeperPositionAnalyzer` consumindo `FootballWorld` **+** `GoalGeometryResult`, sem alterar nenhum outro módulo. Como o contrato `Analyzer.analyze(football_world)` aceita só um argumento, a solução não exigiu estender o contrato nem o `AnalyzerProcessor`/`ProcessorContext`: um Analyzer futuro que precise do resultado de outro simplesmente **instancia o Analyzer consumido internamente** (`self._geometry_analyzer = GoalGeometryAnalyzer(settings)`) e chama `.analyze(football_world)` como uma função pura reutilizável — válido porque `GoalGeometryAnalyzer` é determinístico e sem estado. Documentado em `processor.py` e na Constituição (Seção 6.5/16) como o padrão oficial de composição para W15+.

## Testes — 271/271 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `GoalGeometryResult.to_dict()` com/sem gol, `goal_regions` serializado por chave de `GoalZone` |
| Registry | `tests/analyzers/test_registry.py` | `GoalGeometryAnalyzer` registrado sob `"goal_geometry"` |
| Factory | `tests/analyzers/test_factory.py` | `create_analyzer("goal_geometry", ...)` resolve corretamente |
| `GoalGeometryAnalyzer` (real, sem mock) | `tests/analyzers/test_goal_geometry.py` | Sem gol (tudo `None`); gol bem formado produz geometria completa; grade 2×3 cobre exatamente a região do gol (6 zonas, sem sobreposição/gap); região degenerada (largura=0) → `confidence=0.0`, `goal_regions=None`; múltiplos gols → primeiro escolhido deterministicamente; metadata correta |
| Integração com `AnalyzerProcessor` (real, sem mock) | `tests/analyzers/test_processor.py::test_goalkeeper_presence_and_goal_geometry_run_together` | Dois Analyzers reais (W13+W14) rodando simultaneamente sobre o mesmo `FootballWorld`, cada um produzindo seu próprio `AnalysisResult` |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_goal_geometry_analyzer_produces_a_coherent_result` | Detector sem detecções (Field/Goal são construídos pelo `FootballWorldBuilder` independente de qualquer detecção); artefato contém `"goal_geometry_result"` coerente, idêntico a `analysis_results["goal_geometry"]` |
| Regressão | Todos os 259 testes anteriores (W1-W13) | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `271 passed` (suíte completa exceto `tests/infrastructure/`, que depende de um container Redis descartável já encerrado após a validação manual).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/analyzers/goal_geometry.py tests/analyzers/test_goal_geometry.py` → nenhuma menção.
- `grep -n "YOLO\|ByteTrack\|Tracker\|WorldState\|Detector\|cv2\|redis" worker/analyzers/goal_geometry.py` → nenhuma menção real, nenhum `import`.
- Todos os `import`s reais de `worker/analyzers/goal_geometry.py`: `time` (stdlib) + `worker.analyzers.base`/`results`/`types` + `worker.config.settings` + `worker.domain.football_world`/`worker.domain.geometry.coordinate`/`worker.domain.geometry.region` (o único ponto de entrada permitido). Nenhum `worker.inference.detectors`/`trackers`/`events`/`world`.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores. Gerei um vídeo real de 10 frames (640×480, 5fps) com um círculo vermelho se movendo, upload real via `httpx`, publicação real no Redis.

Rodei `python -m worker.main` com `WORKER_DETECTOR=yolo`, `WORKER_TRACKER=bytetrack`+`WORKER_TRACKING_ENABLED=true`, `WORKER_SCENE_ANALYZER=basic`+`WORKER_SCENE_ANALYSIS_ENABLED=true`, `WORKER_WORLD_MODEL=basic`+`WORKER_WORLD_MODEL_ENABLED=true`, `WORKER_FOOTBALL_DOMAIN_ENABLED=true`, `WORKER_ANALYZERS=goalkeeper_presence,goal_geometry`. Log real confirmou o ciclo completo: `JobStarted → GET job → download-url → GET R2 (download real) → VideoDownloaded → artifacts/upload-url → PUT R2 (upload real) → UploadFinished → PUT status → JobCompleted`.

Busquei o artefato de volta **diretamente do R2 real** (via `boto3`):

```
processor_order: ['color', 'statistics', 'yolo', 'tracking', 'scene_analysis', 'world_model', 'football_domain', 'analyzer']
analysis_statistics: {'analyzers_run': ['goal_geometry', 'goalkeeper_presence'], 'results_count': 2}

goal_geometry_result:
  goal_detected: True
  goal_center: {'x': 0.01, 'y': 0.5}
  goal_width: 0.02
  goal_height: 0.3
  left_post: {'x': 0.0, 'y': 0.35}
  right_post: {'x': 0.02, 'y': 0.35}
  goal_regions: {top_left, top_center, top_right, bottom_left, bottom_center, bottom_right} (6 zonas, grade 2x3 completa)
  confidence: 1.0

matches analysis_results['goal_geometry']: True
```

**Confirmado exatamente o que a sprint pediu — um `GoalGeometryResult` coerente:** o gol (placeholder, construído pelo `FootballWorldBuilder` independente de qualquer detecção real) foi corretamente geometrizado — `goal_center`/`goal_width`/`goal_height`/`left_post`/`right_post` consistentes com a região do gol esquerdo (`Goal.default_pair()`), as 6 zonas da grade 2×3 cobrindo exatamente a região sem sobreposição, `confidence=1.0` (retângulo bem formado). `goal_geometry_result` no artefato bate exatamente com `analysis_results["goal_geometry"]`. Lock liberado, fila sem pendências (`XPENDING`=0), Job `COMPLETED`. Stack derrubado ao final (volume preservado).

## Riscos (novos, registrados na Constituição — Seção 14)

26. **`GoalGeometryAnalyzer` escolhe o PRIMEIRO gol de `FootballWorld.goals`** quando há mais de um — como `Goal.default_pair()` sempre cria exatamente 2 gols, o "primeiro" é sempre o gol esquerdo por construção, não por identificação de relevância. Um `GoalkeeperPositionAnalyzer` futuro precisará de lógica própria de seleção se precisar saber qual gol o goleiro defende.
27. **`GoalGeometryAnalyzer.confidence` reflete só validade estrutural, não precisão real** — `Goal`/`Field` seguem sendo geometria placeholder não calibrada (Risco 22); `confidence=1.0` hoje significa "retângulo bem formado", nunca "posição real do gol no vídeo".

## Preparação para a W15

A W15 ainda não tem escopo definido (qual análise entra primeiro com julgamento/avaliação real). O que já está confirmado, pela sétima repetição consecutiva do padrão de encaixe (W8/W9/W10/W11/W12/W13/W14): um novo Analyzer exige **apenas** escrever `XAnalyzer(Analyzer)`, registrá-lo, incluir seu nome em `WORKER_ANALYZERS` — nunca uma mudança em `AnalyzerProcessor`/pipeline/famílias de Plugin existentes. A W14 confirmou adicionalmente, pela primeira vez: (a) dois Analyzers reais rodando simultaneamente sem qualquer mudança estrutural, e (b) um padrão de composição entre Analyzers (instanciação interna + chamada direta a `.analyze()`) para quando um Analyzer precisar do resultado de outro. A partir da W15, a lógica introduzida terá semântica de JULGAMENTO em vez de apenas relatar fatos/geometria — esta é a primeira sprint em que avaliação/heurística de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
