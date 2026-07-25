# Sprint W36 — Planning Layer

## Objetivo

Reclassificação determinística de `ConvictionSet` (W35) num conjunto de PLANOS POSSÍVEIS —
`build_plans(conviction_set) -> PlanningSet` responde "dadas essas crenças, quais cursos
de ação passam a existir?", sempre em linguagem de possibilidade ("um plano de X passa a
ser possível para..."), nunca de escolha/execução/recomendação. Sem Decision, sem Rule
Engine, sem Explainability, sem Evaluation, sem Coaching, sem Prompt Generation.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **`PlanType` genérico, não específico de domínio** — a taxonomia inicial
   (`APPROACH`/`INTERCEPT`) soava a táticas de futebol/goleiro. Renomeada para vocabulário
   neutro de rastreamento/percepção — `ENGAGE`/`PURSUE`/`REACQUIRE`/`DISENGAGE` — mantendo
   Planning no mesmo nível de abstração das camadas anteriores.
2. **O mapeamento 1:1 `HypothesisType`→`PlanType` é uma escolha desta sprint, não um
   contrato permanente** — registrado explicitamente para que uma sprint futura possa
   decidir que um mesmo `hypothesis_type` origina múltiplos `PlanType`s, mudando apenas
   `worker/planning/builder.py`, sem tocar `worker/hypothesis/` ou `worker/conviction/`.
3. **Strings replicadas de `HypothesisType`/limiar de `ConvictionLevel.STABLE` tratadas
   como dívida arquitetural conhecida** — não apenas um risco mitigado por teste, mas uma
   solução provisória assumida, a ser revisitada se surgir um mecanismo melhor de
   compartilhar contratos entre camadas sem aumentar acoplamento.

## Arquivos criados (zero arquivos existentes alterados)

```
worker/planning/
├── __init__.py
├── plan_type.py        # PlanType (Enum): ENGAGE, PURSUE, REACQUIRE, DISENGAGE
├── plan_state.py           # PlanState (Enum): EMERGED, ONGOING, INVALIDATED
├── track_plan.py                # TrackPlan (dataclass, frozen)
├── entity_plan.py                   # EntityPlan (dataclass, frozen)
├── planning_set.py                      # PlanningSet (dataclass, frozen) - raiz
└── builder.py                               # build_plans(conviction_set) -> PlanningSet

tests/planning/  (29 testes novos)
├── test_plan_type.py, test_plan_state.py
├── test_track_plan.py, test_entity_plan.py, test_planning_set.py
└── test_builder.py  (inclui 2 testes de regressão comparando as strings/limiar
                        replicados contra os valores reais de worker.hypothesis/worker.conviction)
```

Nenhum arquivo de `worker/timeline/` (incl. `enrichment/`), `worker/explorers/`,
`worker/segments/`, `worker/memory/`, `worker/perceptual_state/`, `worker/hypothesis/`,
`worker/conviction/`, `worker/analyzers/`, `worker/domain/` foi alterado — `build_plans`
só LÊ `ConvictionSet`, sem importar `worker.hypothesis` em nenhum código de produção.

## Planning é sem memória própria

`build_plans` recebe UM ÚNICO argumento (`ConvictionSet`) e deriva o `state` de cada plano
(`EMERGED`/`ONGOING`/`INVALIDATED`) inteiramente do snapshot atual — usando
`conviction.state`, `conviction.level` e `conviction.consecutive_observations`/
`lifetime_observations`, todos já computados pela Conviction Layer (que TEM memória).
Nenhum `PlanningSet` anterior é lido ou necessário.

## Taxonomia

| `PlanType` | Habilitado por | Objetivo |
|---|---|---|
| `ENGAGE` | conviction `stationary` ≥ `STABLE` | "Um plano de engajamento passa a ser possível..." |
| `PURSUE` | conviction `movement` ≥ `STABLE` | "Um plano de perseguição passa a ser possível..." |
| `REACQUIRE` | conviction `recovery` ≥ `STABLE` | "Um plano de reaquisição de identidade passa a ser possível..." |
| `DISENGAGE` | conviction `visibility` ≥ `STABLE` (track e entity) | "Um plano de desengajamento passa a ser possível..." |

## Testes

29 testes novos: taxonomia fechada (ausência de `"approach"`/`"intercept"`/`"trajectory"`
como valores); `PlanState` sem `"abandoned"` armazenado; imutabilidade e serialização de
`TrackPlan`/`EntityPlan`/`PlanningSet` (incluindo teste de ausência de campos
Decision/Command/Recommendation/Action/Execution); `build_plans` cobrindo criação (conviction
cruza `STABLE`), não-criação (conviction ainda `EMERGING`), coexistência (`MOVEMENT`+
`VISIBILITY` do mesmo track), continuidade (`STABLE`→`STRONG` mantém `ONGOING`),
invalidação (após `WEAKENED` tendo alcançado `lifetime_observations>=3`), remoção/abandono
(conviction removida → plano ausente), determinismo, identificadores estáveis,
serialização; e 2 testes de regressão comparando as strings/limiar replicados contra os
valores reais de `HypothesisType`/`level_for`.

## Validação contra o `ConvictionSet` real (job `b07f0dc6`, após os 6 ciclos da W35)

Mesmas 76 convicções de track (todas em `STRONG`) + 6 de entidade já validadas em W35.

| Métrica | Valor |
|---|---|
| `track_plans` produzidos | **76** (`pursue: 2, reacquire: 27, engage: 8, disengage: 39`) |
| `entity_plans` produzidos | **6** (todos `disengage`) |
| `state` de todos os planos | **`ongoing`** (cruzaram `STABLE` no ciclo 3, antes do snapshot final) |
| Determinismo (2 chamadas idênticas) | **Confirmado** |
| Tamanho serializado — `ConvictionSet` | 29.980 bytes |
| Tamanho serializado — `PlanningSet` | 26.287 bytes |

`track_id=1` produz `engage:track:1` (origem: `stationary:track:1`) e
`reacquire:track:1` (origem: `recovery:track:1`) simultaneamente — a mesma coexistência já
esperada desde a Conviction Layer.

**Nota honesta**: ao contrário de W34/W35 (onde a camada seguinte era maior que a
anterior), `PlanningSet` (26.287 bytes) ficou MENOR que `ConvictionSet` (29.980 bytes)
desta vez — não por filtrar convicções (as 76 convicções produziram 76 planos, 1:1, sem
nenhuma descartada, já que todas estavam em `STRONG`, bem acima do gate de `STABLE`), mas
porque `TrackPlan` tem menos campos que `TrackConviction` (sem timestamps/frame/duração).

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente. Suíte completa: **815 passed** (786 da
baseline W35 + 29 novos), mesmos 26 failed / 16 errors pré-existentes em
`tests/infrastructure/` (exigem Redis/backend reais) — sem regressão.

## Impacto esperado na futura Decision Layer

Uma futura Decision Layer consumirá `PlanningSet` (nunca `ConvictionSet`/`HypothesisSet`/
`WorkingState` diretamente) e acrescentará ESCOLHA entre planos coexistentes (ex.:
`engage:track:1` e um eventual `disengage:track:1` concorrentes), priorização definitiva,
geração de comandos/execução, explicação da escolha, avaliação de resultado. O que
continua exclusivo da Planning Layer: a enumeração do que é logicamente possível dado o
conjunto de crenças atuais, a taxonomia fechada de tipos de plano, e a rastreabilidade
`origin_conviction_id` até a Conviction de origem. Decision nunca recalcula planos a
partir de `ConvictionSet` diretamente.

## Próximos passos

- Revisitar a heurística de `INVALIDATED` (baseada em `lifetime_observations`) se
  `worker/conviction/` for reaberto para preservar o nível pré-enfraquecimento com mais
  precisão.
- Novos `PlanType`s se W34 ganhar novos `HypothesisType`s no futuro.
- Decision Layer (consome `PlanningSet`).
- Rule Engine, Explainability, Evaluation, Coaching, Prompt Generation (mais distantes,
  consumiriam Decision, não Planning diretamente).
