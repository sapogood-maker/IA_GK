# Sprint W37 — Decision Layer

## Objetivo

Reclassificação determinística de `PlanningSet` (W36) que escolhe, para cada sujeito
(track ou entidade) com pelo menos um plano ainda válido, qual único plano deveria ser
executado — `decide(planning_set) -> DecisionSet` responde apenas "qual plano deve ser
executado?", nunca cria planos/hipóteses/convicções novas, nunca executa, nunca avalia,
nunca gera texto em linguagem natural.

## Processo: análise crítica antes da implementação

A pedido explícito do usuário, esta sprint seguiu um processo formal antes de qualquer
código: (1) proposta arquitetural, (2) autocrítica da própria proposta, (3) identificação
de problemas futuros, (4) alternativas consideradas, (5) justificativa da escolha final —
documentado por completo no plano aprovado, com duas rodadas de revisão antes da
implementação começar.

## Achado inicial e ajustes aprovados

Antes de propor qualquer coisa, o código real de `worker/planning/` foi verificado —
`TrackPlan`/`EntityPlan` (W36) não têm campo de "prioridade" nem de "confiança"/nível
numérico, ao contrário do que uma primeira leitura do pedido sugeria. A proposta original
cogitava três caminhos para resolver isso; após duas rodadas de revisão, os seguintes
ajustes foram aprovados e são a espinha dorsal desta sprint:

1. **Zero mudança em `worker/planning/`** — nenhum campo (`origin_conviction_level`,
   `priority`, `confidence` ou equivalente) foi adicionado a W36 "para facilitar" Decision.
   W36 permanece exatamente como foi aprovada e commitada.
2. **Nenhuma prioridade fixa por `PlanType`** — Decision não incorpora conhecimento
   semântico de domínio (ex.: `REACQUIRE > ENGAGE > PURSUE > DISENGAGE` foi
   explicitamente rejeitado). Qualquer desempate usa só critérios estruturais e
   determinísticos, preservando o núcleo cognitivo como reutilizável para qualquer domínio
   futuro (princípio reafirmado desde W28) — scouting de goleiros é só a primeira
   aplicação, não o modelo do núcleo.
3. **Sem `DecisionState`, sem reaproveitar `PlanState`** — Decisão e Plano são conceitos
   distintos. `PlanState` é lido só como filtro de candidatura (um plano `INVALIDATED`
   nunca compete), nunca copiado para `TrackDecision`/`EntityDecision`. Avaliado se
   Decision precisa de um estado próprio: concluído que não — `winning_criteria` já
   representa, de forma estruturada, o resultado do processo de escolha.

## Arquivos criados (zero arquivos existentes alterados, incluindo `worker/planning/`)

```
worker/decision/
├── __init__.py
├── track_decision.py      # TrackDecision (dataclass, frozen)
├── entity_decision.py          # EntityDecision (dataclass, frozen)
├── decision_set.py                  # DecisionSet (dataclass, frozen) - raiz
└── builder.py                            # decide(planning_set) -> DecisionSet

tests/decision/  (20 testes novos)
├── test_track_decision.py, test_entity_decision.py, test_decision_set.py
└── test_builder.py
```

Nenhum arquivo de `worker/timeline/` (incl. `enrichment/`), `worker/explorers/`,
`worker/segments/`, `worker/memory/`, `worker/perceptual_state/`, `worker/hypothesis/`,
`worker/conviction/`, **`worker/planning/`**, `worker/analyzers/`, `worker/domain/` foi
alterado — `decide` só LÊ `PlanningSet`.

## Critérios de desempate — inteiramente estruturais

Para cada sujeito com 1+ plano: (1) filtrar candidatos com `state != INVALIDATED`; (2) se
sobrar 1, vencedor automático (`"only_candidate"`); (3) se sobrar 2+, comparar por maior
`len(satisfied_preconditions)` (`"more_satisfied_preconditions"`), depois por ordem
lexicográfica de `plan_id` (`"deterministic_tiebreak_by_plan_id"`) — nenhum critério
interpreta o significado de `ENGAGE`/`PURSUE`/`REACQUIRE`/`DISENGAGE`. Sem `DecisionType`
novo (`plan_type` do vencedor é copiado só como fato informativo, nunca usado para
priorizar).

## Testes

20 testes novos: imutabilidade e serialização de `TrackDecision`/`EntityDecision`/
`DecisionSet` (incluindo teste de ausência de campos Execution/Command e de qualquer
`state`/`plan_state` copiado do plano); `decide()` cobrindo decisão trivial, ausência de
decisão sem candidato válido, desempate por precondições estruturais, desempate
determinístico final por `plan_id`, exclusão de planos `INVALIDATED` mesmo quando
estruturalmente "melhores", independência entre sujeitos, determinismo, serialização.

## Validação contra o `PlanningSet` real (job `b07f0dc6`, W36)

Sobre os 76 `track_plans`/6 `entity_plans` já validados em W36.

| Métrica | Valor |
|---|---|
| `track_decisions` produzidas | **47** |
| `entity_decisions` produzidas | **6** |
| Distribuição de `winning_criteria` (track) | `deterministic_tiebreak_by_plan_id: 28`, `only_candidate: 19` |
| Determinismo (2 chamadas idênticas) | **Confirmado** |
| Tamanho serializado — `PlanningSet` | 26.287 bytes |
| Tamanho serializado — `DecisionSet` | 9.774 bytes |

`track_id=1` tinha `engage:track:1` e `reacquire:track:1` coexistindo (ambos `ONGOING`,
ambos com 1 precondição satisfeita — empate total nos critérios estruturais) → decisão:
**`engage:track:1`** vence por `"deterministic_tiebreak_by_plan_id"` (`"engage"` <
`"reacquire"` lexicograficamente) — exatamente o comportamento previsto no documento
aprovado antes da implementação.

**Nota honesta**: nenhuma das 47 decisões foi resolvida por `"more_satisfied_preconditions"`
— `build_plans` (W36) sempre produz exatamente 1 precondição por plano hoje, então esse
critério nunca desempata nada no dado real. Isso é uma consequência direta e aceita dos
ajustes aprovados (sem nível de convicção, sem prioridade de tipo disponíveis) — a maioria
dos empates reais (28 de 47) cai no desempate alfabético final, que não carrega nenhum
significado além de garantir determinismo. Documentado como o comportamento real esperado,
não escondido (ver riscos, abaixo).

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente, **incluindo `worker/planning/`**. Suíte
completa: **835 passed** (815 da baseline W36 + 20 novos), mesmos 26 failed / 16 errors
pré-existentes em `tests/infrastructure/` — sem regressão.

## Impacto esperado nas futuras camadas (Execution/Evaluation/Explainability)

Uma futura Execution Layer consumirá `DecisionSet` (nunca `PlanningSet`/`ConvictionSet`
diretamente) e acrescentará a execução de fato do `selected_plan_id`, efeitos colaterais
reais, e possivelmente feedback de resultado. Uma futura Explainability Layer poderia
traduzir `winning_criteria`/`discarded_plan_ids` (já estruturados aqui) em texto em
linguagem natural — Decision nunca faz isso sozinha. O que continua exclusivo da Decision
Layer: o mecanismo de escolha em si e a rastreabilidade estruturada
`selected_plan_id`/`discarded_plan_ids` até os planos originais.

## Próximos passos

- Reavaliar se `ConvictionLevel` deveria, algum dia, ficar acessível a Decision (exigiria
  reabrir W36 — decisão explícita futura, não presumida aqui).
- Cross-subject Decision (uma única decisão global no vídeo inteiro), se algum dia
  necessário — sprint própria, escopo maior e mais presunçoso do que o atual.
- Execution Layer (consome `DecisionSet`).
- Explainability, Evaluation, Coaching, Rule Engine (mais distantes).
