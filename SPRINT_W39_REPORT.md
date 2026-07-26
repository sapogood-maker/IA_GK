# Sprint W39 — Evaluation Layer

## Objetivo

Reclassificação determinística de `DecisionSet` (W37/W38) que expõe, de forma tipada,
fatos ESTRUTURAIS sobre COMO cada decisão foi produzida — `evaluate(decision_set) ->
EvaluationSet` responde "havia conflito? foi resolvida por um critério real ou só por
desempate alfabético?", nunca "a decisão foi correta no mundo real". Sem conhecimento de
domínio, sem feedback do ambiente, sem sensores/banco/API/hardware.

## Processo: duas rodadas de refinamento crítico

**Primeira análise**: todas as sete perguntas estruturais do pedido resultaram derivadas
diretamente de `winning_criteria`/`discarded_plan_ids` (já existentes em `TrackDecision`/
`EntityDecision`, W37) — sem precisar de nenhum dado novo. Duas delas ("a decisão foi
consistente?", "foi determinística?") revelaram-se propriedades ESTÁTICAS de `decide()`
como função pura e total — sempre verdadeiras para qualquer `DecisionSet` que o pipeline
produza, não fatos que variam por instância; documentadas como invariantes do código, não
como campos. Uma ("havia evidências suficientes?") revelou-se só parcialmente
respondível: `DecisionSet` não preserva nenhum traço de sujeitos que nunca tiveram decisão
(todos os planos invalidados vs. nenhum plano — a mesma ausência) — limitação honesta,
registrada, não contornável sem violar "consumir exclusivamente `DecisionSet`".

**Segunda rodada** (a pedido do usuário, questionando a primeira versão desta proposta):
duas simplificações adicionais, aplicando o mesmo rigor que reverteu `ExecutionIntent` na
W38:
1. **`winning_criteria` removido de `TrackEvaluation`/`EntityEvaluation`** — copiá-lo
   repetiria o erro corrigido na W38 (duplicar um campo já acessível em `DecisionSet`,
   que continua disponível ao lado de `EvaluationSet`).
2. **`candidate_count` (int) + `resolved_by_deterministic_tiebreak` (bool) substituídos
   por um único enum fechado, `ResolutionMethod`** (`SINGLE_CANDIDATE`/
   `STRUCTURAL_CRITERION`/`DETERMINISTIC_TIEBREAK`) — a magnitude absoluta de candidatos
   não acrescenta significado estrutural além de qual mecanismo decidiu o vencedor. Nome
   evita deliberadamente a palavra "rule" (Rule Engine excluído do núcleo desde W31/W36).

## Arquivos criados (zero arquivos existentes alterados, incluindo `worker/decision/`)

```
worker/evaluation/
├── __init__.py
├── resolution_method.py      # ResolutionMethod (Enum): SINGLE_CANDIDATE, STRUCTURAL_CRITERION, DETERMINISTIC_TIEBREAK
├── track_evaluation.py           # TrackEvaluation (dataclass, frozen)
├── entity_evaluation.py              # EntityEvaluation (dataclass, frozen)
├── evaluation_set.py                     # EvaluationSet (dataclass, frozen) - raiz
└── builder.py                                # evaluate(decision_set) -> EvaluationSet

tests/evaluation/  (21 testes novos)
├── test_resolution_method.py
├── test_track_evaluation.py, test_entity_evaluation.py, test_evaluation_set.py
└── test_builder.py  (inclui 2 testes de regressão que rodam decide() real, W37)
```

## Modelo final — só o fato que realmente varia por decisão

```python
@dataclass(frozen=True)
class TrackEvaluation:
    track_id: int
    resolution_method: ResolutionMethod
```

Mapeamento a partir de `winning_criteria`: se `"deterministic_tiebreak_by_plan_id"`
estiver presente (isolado ou combinado com `"more_satisfied_preconditions"`) →
`DETERMINISTIC_TIEBREAK` (o desempate alfabético é sempre o fator decisivo final, mesmo
que uma filtragem estrutural tenha ocorrido antes); senão, se
`"more_satisfied_preconditions"` presente → `STRUCTURAL_CRITERION`; senão →
`SINGLE_CANDIDATE`. As strings são REPLICADAS de `worker/decision/builder.py` (nem sequer
são constantes nomeadas lá hoje, só literais soltos) — protegidas por testes de
regressão que rodam o `decide()` real.

## Testes

21 testes novos: taxonomia fechada de `ResolutionMethod` (ausência de valores de
julgamento e da palavra "rule"); imutabilidade e serialização de
`TrackEvaluation`/`EntityEvaluation`/`EvaluationSet` (incluindo ausência de qualquer campo
de resultado/ambiente/execução e ausência de `winning_criteria`/`selected_plan_id`/
`discarded_plan_ids` copiados); `evaluate()` cobrindo os 3 valores do enum a partir de
`winning_criteria` sintético, o caso combinado (`STRUCTURAL_CRITERION` +
`DETERMINISTIC_TIEBREAK` juntos → classifica como `DETERMINISTIC_TIEBREAK`), entidades,
determinismo, serialização; e **2 testes de regressão que rodam o `decide()` real** (W37)
sobre um `PlanningSet` sintético desenhado para empatar totalmente, provando que as
strings replicadas em `worker/evaluation/builder.py` ainda batem com o comportamento
real de `worker/decision/builder.py`, sem importar nada de lá.

## Validação contra o `DecisionSet` real (job `b07f0dc6`, W37)

Sobre as 47 `TrackDecision`/6 `EntityDecision` já validadas em W37.

| Métrica | Valor |
|---|---|
| `track_evaluations` produzidas | **47** (`deterministic_tiebreak: 28`, `single_candidate: 19`, `structural_criterion: 0`) |
| `entity_evaluations` produzidas | **6** (todas `single_candidate`) |
| Determinismo (2 chamadas idênticas) | **Confirmado** |
| Tamanho serializado — `DecisionSet` | 9.774 bytes |
| Tamanho serializado — `EvaluationSet` | 3.865 bytes |

`track_id=1` (empate entre `engage:track:1` e `reacquire:track:1`) → `resolution_method
= DETERMINISTIC_TIEBREAK`. `structural_criterion` nunca ocorre no dado real — consistente
com o próprio achado honesto do relatório da W37 ("`more_satisfied_preconditions` nunca
desempata nada hoje, já que `build_plans` sempre produz exatamente 1 precondição por
plano").

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente, **incluindo `worker/decision/`**. Suíte
completa: **856 passed** (835 da baseline W37/W38 + 21 novos), mesmos 26 failed / 16
errors pré-existentes em `tests/infrastructure/` — sem regressão.

## Riscos identificados

1. Acoplamento textual a duas strings não nomeadas em `worker/decision/builder.py` — mais
   frágil que réplicas anteriores (W32/W36), que ao menos citavam uma constante existente.
   Mitigado pelos testes de regressão que rodam `decide()` de verdade.
2. Evaluation nunca avalia sujeitos que nunca tiveram decisão (limitação honesta, Seção 1
   do documento arquitetural) — não contornável sem violar "consumir exclusivamente
   `DecisionSet`".
3. "Consistência"/"determinismo" ficam só como nota de documentação (docstring do pacote),
   nunca como campo — decisão consciente, não descuido.

## Impacto esperado no que vem depois

`EvaluationSet` não é consumido por nenhuma camada cognitiva futura — é, junto com
`DecisionSet`, um artefato final do núcleo, disponível para observabilidade/auditoria
externa (ex.: um painel monitorando "quantas decisões recentes precisaram de fallback"),
sem nunca saber o que aconteceu no ambiente.

## Próximos passos

- Se `worker/decision/builder.py` expuser as strings de `winning_criteria` como
  constantes nomeadas exportáveis, revisitar a réplica desta sprint.
- Avaliar, com caso de uso concreto, se vale a pena uma camada que também leia
  `PlanningSet` para cobrir sujeitos sem decisão — não antecipado aqui.
- Um painel externo de observabilidade do núcleo, consumindo `DecisionSet` +
  `EvaluationSet` — fora de `worker/`, não implementado aqui.
