# Sprint W34 — Hypothesis Layer

## Objetivo

Primeira camada cognitiva: reclassifica `WorkingState` (W33) num conjunto de
**possibilidades**, nunca de conclusões. `HypothesisSet` responde "dado esse estado,
quais hipóteses fazem sentido?" — sempre em linguagem de possibilidade ("aparenta",
"pode haver", "sugere"), nunca de fato consumado ou julgamento. Sem Conviction, sem
Decision, sem Planning, sem Rule Engine, sem Coaching, sem Avaliação, sem
Explicabilidade final.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **`producers/`, não `rules/`** — o pacote foi deliberadamente nomeado para não sugerir
   um motor genérico de regras interpretadas/configuráveis. Cada arquivo é um produtor
   determinístico de UM tipo de hipótese: código Python fixo, não dado interpretado em
   tempo de execução.
2. **`origin` é um identificador estável do conceito, não o nome de uma função** — valores
   como `"stationary"`, `"recovery"`, `"visibility_track"`, `"visibility_entity"`, nunca
   `"produce_stationary_hypothesis"`. Reduz acoplamento entre o dado produzido e o detalhe
   de implementação que o gerou.

## Arquivos criados (zero arquivos existentes alterados)

```
worker/hypothesis/
├── __init__.py
├── hypothesis_type.py         # HypothesisType (Enum) - taxonomia fechada, 4 valores
├── evidence.py                    # Evidence (dataclass, frozen)
├── track_hypothesis.py                # TrackHypothesis (dataclass, frozen)
├── entity_hypothesis.py                   # EntityHypothesis (dataclass, frozen)
├── hypothesis_set.py                          # HypothesisSet (dataclass, frozen) - raiz
├── producers/
│   ├── __init__.py
│   ├── stationary.py                                # produce_stationary_hypothesis()
│   ├── movement.py                                      # produce_movement_hypothesis()
│   ├── recovery.py                                          # produce_recovery_hypothesis()
│   └── visibility.py                                            # produce_track_visibility_hypothesis() +
│                                                                     produce_entity_visibility_hypothesis()
└── builder.py                                                       # build_hypotheses(working_state)

tests/hypothesis/  (45 testes novos)
├── test_hypothesis_type.py, test_evidence.py
├── test_track_hypothesis.py, test_entity_hypothesis.py, test_hypothesis_set.py
├── producers/
│   ├── test_stationary.py, test_movement.py
│   ├── test_recovery.py, test_visibility.py
└── test_builder.py
```

Nenhum arquivo de `worker/timeline/` (incl. `enrichment/`), `worker/explorers/`,
`worker/segments/`, `worker/memory/`, `worker/perceptual_state/`, `worker/analyzers/`,
`worker/domain/` foi alterado — `build_hypotheses` só LÊ `WorkingState`.

## Taxonomia: `HypothesisType` (4 valores)

| Tipo | Nível | Campo(s) de `WorkingState` que sustentam |
|---|---|---|
| `STATIONARY` | track | `motion_state == STOPPED` |
| `MOVEMENT` | track | `motion_state == MOVING` |
| `RECOVERY` | track | `recovery_count >= 1` |
| `VISIBILITY` | track e entity | track: `presence_state == ENDED`; entity: `active_track_ids` vazio + `ended_track_ids` não-vazio |

`TrajectoryHypothesis` (sugerida no pedido original) foi deliberadamente descartada:
`WorkingState`/`TrackState` não carregam posição, bounding box ou vetor de direção —
posição só existe no `Event` bruto (W28), fora do alcance permitido (Hypothesis só lê
`WorkingState`). Documentado como item de roadmap, exigiria estender `TrackMemory` (W32).

`motion_state == UNKNOWN` não gera nem `STATIONARY` nem `MOVEMENT` — ausência de sinal é
representada pela ausência de hipótese. `STATIONARY`/`MOVEMENT` são mutuamente exclusivas
por construção; `RECOVERY`/`VISIBILITY` coexistem livremente com qualquer uma das outras.

## Modelo de dados

`TrackHypothesis`/`EntityHypothesis` são `dataclass` irmãos (não uma hierarquia por
herança) — mesmo padrão de `TrackState`/`EntityState` (W33). Campos: `hypothesis_id`
(determinístico, ex. `"stationary:track:1"`), `hypothesis_type`, `track_id`/`entity`,
`description` (sempre linguagem de possibilidade), `evidence` (fatos literais de
`WorkingState`, nunca de `Timeline`/`Event`), `matching_conditions` (nomes das condições
que bateram), `support` (contagem inteira — **nunca `confidence`**), `origin`.

Um track pode gerar 0 a N hipóteses simultâneas (não 1:1 como `WorkingState.track_states`)
— por isso `HypothesisSet.track_hypotheses`/`entity_hypotheses` são tuplas.

## Testes

45 testes novos: taxonomia fechada e ausência de `"trajectory"`; imutabilidade e
serialização de `Evidence`/`TrackHypothesis`/`EntityHypothesis`/`HypothesisSet` (incluindo
**teste que prova a ausência de qualquer campo `confidence`** e que `origin` nunca contém
sufixo de função); cada produtor testado isoladamente (disparo/não-disparo, limiares
exatos, `UNKNOWN` não gera nem `STATIONARY` nem `MOVEMENT`, `STATIONARY`/`MOVEMENT`
mutuamente exclusivas, `RECOVERY` coexiste com `STATIONARY`); `build_hypotheses` com
`WorkingState` vazio, um track com 3 hipóteses simultâneas, ordenação determinística por
`track_id`/`entity`, determinismo (2 chamadas, mesma saída).

## Validação contra o artifact real (job `b07f0dc6`, mesmo `WorkingState` da W33)

Mesmos 48 `TrackState`/8 `EntityState` já validados em W33.

| Métrica | Valor |
|---|---|
| `track_hypotheses` produzidas | **76** |
| `entity_hypotheses` produzidas | **6** |
| Distribuição por tipo (track) | `{stationary: 8, recovery: 27, visibility: 39, movement: 2}` |
| Distribuição por tipo (entity) | `{visibility: 6}` |
| Tracks com 2+ hipóteses simultâneas | **28 de 48** |
| Tamanho serializado — `WorkingState` | 23.468 bytes |
| Tamanho serializado — `HypothesisSet` | 33.222 bytes |
| Determinismo (2 chamadas idênticas) | **Confirmado** |

`track_id=1` (o mesmo "person" analisado desde W28): `STATIONARY` (`support=2`:
`motion_state_is_stopped` + `duration_is_known`, sem `duration_at_least_one_second` pois a
duração medida é 0,033s) e `RECOVERY` (`support=2`: `recovery_count_at_least_one` +
`recovery_count_at_least_two`, pois `recovery_count=2`) — nenhuma `VISIBILITY` (track
presente no último frame da janela).

**Nota honesta**: diferente de W29-W33 (cada camada sempre menor que a anterior,
compressão progressiva), `HypothesisSet` (33.222 bytes) é **maior** que `WorkingState`
(23.468 bytes) — esperado e correto: esta camada enumera possibilidades, não resume fatos;
um único track pode gerar várias hipóteses simultâneas (28 dos 48 tracks geraram 2+), então
expansão aqui é o comportamento certo, não uma regressão de eficiência.

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente. Suíte completa: **755 passed** (710 da
baseline W33 + 45 novos), mesmos 26 failed / 16 errors pré-existentes em
`tests/infrastructure/` (exigem Redis/backend reais) — sem regressão.

## Impacto esperado na futura Conviction Layer

Uma futura Conviction Layer consumirá `HypothesisSet` (nunca pulará direto para
`WorkingState`) e acrescentará o que a Hypothesis Layer deliberadamente não tem:
persistência temporal (comparar `HypothesisSet`s de múltiplos frames/observações ao longo
do tempo), confiança real e comparável entre tipos (a métrica que W34 evita — `support` só
é comparável DENTRO do mesmo tipo de hipótese), e resolução de coexistência quando várias
hipóteses convivem no mesmo track (Conviction decide como ponderá-las; Hypothesis só lista
todas sem hierarquia). O que continua exclusivo da Hypothesis Layer: a enumeração do que é
logicamente possível dado o estado atual, e a rastreabilidade literal
`evidence`/`matching_conditions` até campos de `WorkingState`.

## Próximos passos

- `TrajectoryHypothesis` — exigiria estender `TrackMemory`/`TrackState` com
  posição/direção, precisaria de aprovação explícita para reabrir `worker/memory/` e
  `worker/perceptual_state/`.
- Hipóteses agregadas de entidade além de `VISIBILITY` (usando
  `EntityState.motion_state_counts`) — descartado nesta sprint por beirar "estado
  dominante" (interpretação agregada).
- Conviction Layer (consome `HypothesisSet`).
- Decision Engine, Planning, Coaching, Rule Engine, Explainability (mais distantes,
  consumiriam Conviction, não Hypothesis diretamente).
