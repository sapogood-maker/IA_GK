# SPRINT_W18_REPORT.md — Goalkeeper AI Worker: Ball Motion Analyzer

> Escopo: construir o primeiro Analyzer STATEFUL da Analyzer API — `BallMotionAnalyzer`, que mede o movimento OBSERVADO da bola entre frames consecutivos, compondo `BallPositionAnalyzer`. Ainda **sem** detecção de chute, previsão de trajetória futura ou avaliação de risco — apenas o que já aconteceu. **Regra vigente desde a W6 mantida: `AI_WORKER_CONSTITUTION.md` foi atualizada durante a própria implementação — nenhuma sprint de sincronização.**

## Arquitetura

Reli `AI_WORKER_CONSTITUTION.md`, `AI_WORKER_ARCHITECTURE.md`, os ADRs e `SPRINT_W17_REPORT.md` antes de implementar.

- **`worker/analyzers/ball_motion.py`** (novo) — `BallMotionAnalyzer(Analyzer)` + `BallMotionContext(AnalyzerContext)`: sexta implementação concreta, e a primeira genuinamente stateful.
- **`worker/analyzers/results.py`** — `BallMotionResult(AnalysisResult)` adicionado (13 campos, ver abaixo).
- **`worker/analyzers/registry.py`** — `register_analyzer("ball_motion", BallMotionAnalyzer)` adicionado, sem nenhuma outra mudança.
- **`worker/inference/basic_vision_engine.py`** — artefato ganha `"ball_motion_result"` (alias de conveniência de `analysis_results["ball_motion"]`).

**Nenhuma mudança** em `AnalyzerProcessor`, `PipelineProcessor`, `FootballDomainProcessor`, `WorldModel`, ou `BallPositionAnalyzer` — conforme exigido pela sprint. **Confirmação central desta sprint:** `AnalyzerProcessor.reset()` já existia desde a W13 e já delegava a `analyzer.reset()` de cada Analyzer ativo — mas até agora isso sempre foi um no-op herdado da classe base, já que nenhum Analyzer anterior tinha estado. A W18 é a primeira vez que esse `reset()` realmente limpa algo, e funcionou sem NENHUMA alteração na plumbing genérica.

## AnalyzerContext — primeiro uso real

`AnalyzerContext` foi criada na W13 como classe-base vazia, reservada para este momento. `BallMotionContext(AnalyzerContext)` (definida em `ball_motion.py`, não em `context.py` — mesmo padrão de `WorldModelContext`/`FootballDomainContext`, cada Context vive junto do seu Analyzer) adiciona:

```python
@dataclass
class BallMotionContext(AnalyzerContext):
    previous_position: Coordinate | None = None
    previous_velocity: Vector | None = None
    previous_track_id: EntityId | None = None
    frames_observed: int = 0

    def reset(self) -> None:
        self.previous_position = None
        self.previous_velocity = None
        self.previous_track_id = None
        self.frames_observed = 0
```

## Estado interno e continuidade

Cada chamada de `analyze()` compara o `Ball` atual (`football_world.balls[0]`, resolvido via `BallPositionAnalyzer` para a posição, mas lido diretamente para `confidence`/`track_id` — ver abaixo) com o estado guardado no `BallMotionContext`. A continuidade só é considerada válida quando **ambas** as condições são verdadeiras:

1. Existe uma `previous_position` guardada (não é a primeira observação).
2. O `track_id` atual é IGUAL ao `previous_track_id` guardado (é genuinamente a mesma bola rastreada, não uma identidade nova).

Quando a continuidade é válida, calcula-se: `displacement` (distância euclidiana), `velocity` (`Vector.between(previous, current)`), `speed` (magnitude de `velocity`), `direction_vector` (`velocity.normalized()`, magnitude 1 — distinto de `velocity`, que carrega a magnitude real), `direction_angle` (`velocity.angle_degrees()`), `acceleration` (`speed atual - speed anterior`, só se já havia uma `velocity` anterior também). **Nunca extrapola através de uma lacuna:** se a bola desaparece (`ball_detected=False`) OU o `track_id` muda, o `BallMotionContext` é limpo imediatamente e a próxima observação (mesmo que a bola reapareça no frame seguinte) é tratada como uma PRIMEIRA observação nova — `previous_position=None`, `displacement`/`velocity`/`acceleration`/`motion_detected`=`None`, `frames_observed` reinicia em 1.

**Por que ler `Ball.confidence`/`.track_id` diretamente em vez de só via `BallPositionResult`:** `BallPositionResult` não expõe `track_id`, e seu `confidence` é `min(ball.confidence, goal_geometry.confidence)` — um valor combinado que faz sentido para uma medição de posição relativa ao gol, mas que seria enganoso para uma medição de MOVIMENTO da bola, que não depende do gol de forma alguma. `BallMotionAnalyzer` usa `Ball.confidence` puro, o sinal real e relevante disponível.

**Achado deliberadamente REJEITADO:** o World Model (`inference/world/motion.py`, W11) já calcula exatamente esta mesma cinemática (`compute_motion()`/`Motion`) para objetos genéricos. Reaproveitá-lo pareceria natural, mas `worker.inference.world` está fora da lista de módulos permitidos para `worker/analyzers/` (Boundary Enforcement, Seção 6.5) — importar de lá seria uma violação de camada. A pequena duplicação de matemática (distância/vetor/normalização, todos reconstruídos a partir de `worker.domain.geometry`) foi aceita, seguindo a mesma disciplina já praticada entre `detectors`/`trackers`/`events`/`world` (cada família mantém seus próprios tipos/funções pequenas, em vez de importar de uma camada vizinha).

## BallMotionResult — campos

| Campo | Significado |
|---|---|
| `ball_detected` | há uma bola neste frame? |
| `current_position`/`previous_position` | posição atual e a posição usada como base de comparação (`None` se não há continuidade válida) |
| `displacement` | distância percorrida desde a posição anterior |
| `velocity` | vetor (dx, dy) do deslocamento — magnitude = `speed` |
| `speed` | magnitude de `velocity` (numericamente igual a `displacement` — mesma convenção de `Motion` no World Model, W11: "por frame", já que nenhuma camada da Analyzer API recebe fps) |
| `direction_vector` | `velocity` normalizado (magnitude 1) — só a direção |
| `direction_angle` | ângulo de `velocity` em graus |
| `acceleration` | variação de `speed` desde a chamada anterior (`None` se ainda não há uma velocidade anterior) |
| `frames_observed` | tamanho da sequência CONTÍNUA de observações (reinicia após uma lacuna) |
| `motion_detected`/`stationary` | `displacement > 0` / `displacement == 0` (comparação exata, nenhum limiar arbitrário inventado) |
| `confidence` | `Ball.confidence` real |

## Testes — 331/331 passando

| Categoria | Onde | O que valida |
|---|---|---|
| Resultados | `tests/analyzers/test_results.py` | `BallMotionResult.to_dict()` com/sem movimento |
| Registry/Factory | `tests/analyzers/test_registry.py`/`test_factory.py` | `BallMotionAnalyzer` registrado e resolvido corretamente |
| `BallMotionAnalyzer` (real, sem mock) | `tests/analyzers/test_ball_motion.py` | Sem bola; primeira observação (tudo `None` exceto posição/frames_observed=1); segunda observação (displacement/velocity/speed/direction corretos, acceleration ainda `None`); terceira observação (acceleration calculada); bola estacionária (`stationary=True`); bola desaparece (reseta continuidade); bola reaparece após desaparecer (tratada como primeira observação nova); `track_id` muda sem a bola sumir (também tratada como nova); `reset()` explícito limpa tudo; composição interna com `BallPositionAnalyzer` funciona sem depender do Registry; metadata correta |
| Integração completa — motor real (real, sem mock) | `test_basic_vision_engine.py::test_engine_with_ball_motion_analyzer_produces_a_coherent_result` | Detector stub move a bola 5px/frame (mesmo track_id); `WORKER_ANALYZERS=ball_motion` sozinho; `frames_observed=5`, `displacement`/`speed=5.0`, `motion_detected=True`; `acceleration` não-`None` e pequena (ByteTrack aplica suavização de Kalman, então não é exatamente `0.0` mesmo com passo fixo) |
| Reset entre Jobs (real, sem mock) | `test_basic_vision_engine.py::test_engine_resets_ball_motion_state_between_jobs` | A mesma instância processa 2 vídeos; `frames_observed` reinicia em 3 no segundo vídeo, não continua 6 |
| Regressão | Todos os 314 testes anteriores (W1-W17) | Sem alteração de comportamento não intencional |

Confirmado via `pytest` nesta revisão: `331 passed` (suíte completa exceto `tests/infrastructure/`, dependente de um container Redis descartável já encerrado após a validação manual).

## Boundary Enforcement

- `grep -rn "backend_fastapi\|frontend_flutter" worker/analyzers/ball_motion.py tests/analyzers/test_ball_motion.py` → nenhuma menção.
- `grep -n "YOLO\|ByteTrack\|Tracker\|WorldState\|Detector\|cv2\|redis\|SceneAnalyzer\|inference.world" worker/analyzers/ball_motion.py` → nenhuma menção real, nenhum `import` — **confirmado explicitamente que `worker.inference.world.motion`/`Motion` NÃO foi importado**, apesar de já existir uma implementação equivalente lá (ver "Achado deliberadamente rejeitado" acima).
- Todos os `import`s reais: `time`/`dataclasses` (stdlib) + `worker.analyzers.base`/`ball_position`/`context`/`results`/`types` + `worker.config.settings` + `worker.domain.football_world`/`worker.domain.geometry.coordinate`/`worker.domain.geometry.vector`/`worker.domain.types`.

## Validação manual — stack real

Subi o stack real (Postgres + Redis + backend), reutilizei o usuário/goleiro/sessão de treino de sprints anteriores. Gerei um vídeo real de 10 frames (640×480, 5fps) com um círculo vermelho se movendo, upload real via `httpx`, publicação real no Redis — **desta vez enviei DOIS vídeos (Jobs A e B)**, especificamente para validar `reset()` entre Jobs reais.

Rodei `python -m worker.main` uma única vez com `WORKER_ANALYZERS` incluindo `ball_motion` (entre outros); o mesmo processo consumiu AMBAS as mensagens da fila sequencialmente, reaproveitando a mesma instância de `BasicVisionEngine`/`AnalyzerProcessor`/`BallMotionAnalyzer` para os dois Jobs — exatamente o cenário que `reset()` precisa cobrir.

Busquei os dois artefatos de volta **diretamente do R2 real** (via `boto3`):

```
=== JOB A ===
ball_motion_result: ball_detected=False, frames_observed=0, (todos os campos geometricos None)

=== JOB B ===
ball_motion_result: ball_detected=False, frames_observed=0, (todos os campos geometricos None)
```

**Resultado honesto:** o YOLO real não detectou nenhum objeto rotulado bola em nenhum dos dois vídeos (mesma variabilidade já observada nas validações manuais das W15-W17) — ambos os Jobs produziram `ball_detected=False`/`frames_observed=0` de forma idêntica, confirmando que NENHUM estado vazou de A para B (não havia estado não-trivial para vazar neste caso específico, mas a ausência de qualquer contaminação entre os dois Jobs, rodando na mesma instância do processo, é a confirmação relevante aqui). **A prova definitiva de que `reset()` limpa estado NÃO-trivial** (posição/velocidade/frames_observed acumulados de verdade) está na suíte automatizada (`test_engine_resets_ball_motion_state_between_jobs`, com Detector stub controlado, confirmando `frames_observed` reiniciando de 3 para 3 em vez de continuar para 6). Lock liberado em ambos os Jobs, fila sem pendências (`XPENDING`=0), ambos `COMPLETED`. Stack derrubado ao final (volume preservado).

## Riscos (novo, registrado na Constituição — Seção 14)

33. **`BallMotionAnalyzer` decide continuidade comparando `track_id` entre frames, mas `BallPositionAnalyzer`/`FootballWorldBuilder` sempre escolhem `balls[0]` (mesma limitação dos Riscos 26/28/30)** — se o ByteTrack perder e recuperar o mesmo objeto físico com um NOVO `track_id` (reidentificação, comportamento real e possível de qualquer Tracker), `BallMotionAnalyzer` tratará isso corretamente-dado-o-sinal-disponível como "não é a mesma bola" e reiniciará a contagem, mesmo que fisicamente seja a mesma bola. Resolver isso exigiria mudanças na camada de Tracking, fora do escopo de `analyzers/`.

## Preparação para a W19

A W19 ainda não tem escopo definido (qual análise entra primeiro com julgamento/avaliação real). O que já está confirmado, pela décima primeira repetição consecutiva do padrão de encaixe (W8 a W18): um novo Analyzer exige **apenas** escrever `XAnalyzer(Analyzer)`, registrá-lo, incluir seu nome em `WORKER_ANALYZERS` — nunca uma mudança em `AnalyzerProcessor`/pipeline/famílias de Plugin existentes. A W18 confirmou que Analyzers stateful se encaixam na arquitetura sem NENHUMA mudança estrutural — a plumbing de `reset()` já estava correta desde a W13. A partir da W19, a lógica introduzida terá semântica de JULGAMENTO em vez de apenas medir/relatar fatos — esta é a primeira sprint em que avaliação/heurística de negócio deixa de ser proibida.

`AI_WORKER_CONSTITUTION.md`, Seção 16, registra isso formalmente — já atualizada nesta sprint, não ficando pendente para depois.
