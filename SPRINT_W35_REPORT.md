# Sprint W35 — Conviction Layer

## Objetivo

Primeira camada com memória própria: `update_convictions(previous_convictions,
current_hypotheses) -> ConvictionSet` compara `HypothesisSet`s sucessivos (W34) ao longo
do tempo e mantém, para cada hipótese que se repete, uma crença sobre sua persistência —
nasce, fortalece, persiste, enfraquece ou desaparece. Conviction nunca lê `Timeline`,
`Event`, `TemporalMemory` ou `WorkingState` — consome exclusivamente `HypothesisSet`. Sem
Decision, sem Planning, sem Coaching, sem Rule Engine, sem Evaluation, sem
Explainability, sem Prompt generation.

## Ajustes arquiteturais incorporados (aprovados antes da implementação)

1. **`hypothesis_id` consolida identificador e origem** — em vez de dois campos sempre
   idênticos, um único `hypothesis_id: str` serve como chave de identidade em
   `ConvictionSet` E como referência explícita à hipótese que originou a Conviction
   (nunca reconstruída).
2. **`missed_observations` (campo adicional, justificado por determinismo)** — sem ele,
   `update_convictions` não teria como distinguir a 1ª ausência (tolerada, `WEAKENED`) da
   2ª consecutiva (remoção) na chamada seguinte, já que toda a informação precisa estar
   dentro do `ConvictionSet` retornado.
3. **`lifetime_observations` (sugestão do usuário durante a revisão do plano)** —
   contagem cumulativa desde o `BORN` original, independente de `consecutive_observations`
   (que reinicia a cada `WEAKENED`). Não participa de `level_for()` nesta sprint, mas fica
   disponível como fato bruto para camadas futuras (Planning, Evaluation, Explainability)
   diferenciarem uma crença de longa data de uma recém-nascida.

## Arquivos criados (zero arquivos existentes alterados)

```
worker/conviction/
├── __init__.py
├── conviction_state.py       # ConvictionState (Enum): BORN, STRENGTHENED, PERSISTED, WEAKENED
├── conviction_level.py           # ConvictionLevel (Enum) + level_for() - unica fonte de verdade
├── track_conviction.py                # TrackConviction (dataclass, frozen)
├── entity_conviction.py                   # EntityConviction (dataclass, frozen)
├── conviction_set.py                          # ConvictionSet (dataclass, frozen) - raiz
└── builder.py                                     # update_convictions(previous, current)

tests/conviction/  (31 testes novos)
├── test_conviction_state.py, test_conviction_level.py
├── test_track_conviction.py, test_entity_conviction.py, test_conviction_set.py
└── test_builder.py
```

Nenhum arquivo de `worker/timeline/` (incl. `enrichment/`), `worker/explorers/`,
`worker/segments/`, `worker/memory/`, `worker/perceptual_state/`, `worker/hypothesis/`,
`worker/analyzers/`, `worker/domain/` foi alterado — `update_convictions` só LÊ
`HypothesisSet`.

## Modelo: dois eixos ortogonais

`ConvictionState` (o que aconteceu NESTE ciclo: `BORN`/`STRENGTHENED`/`PERSISTED`/
`WEAKENED` — "desaparecer" nunca é um valor armazenado, é representado por ausência do
`hypothesis_id` no `ConvictionSet` seguinte) × `ConvictionLevel` (força discreta:
`EMERGING`/`STABLE`/`STRONG`, nunca porcentagem/confiança/ML score). `level_for()` é a
única fonte de verdade que deriva o nível a partir de `consecutive_observations`
(limiares: `>=3` → `STABLE`, `>=6` → `STRONG`) — mesma estratégia de dois eixos pequenos
já usada em W33 (`MotionState`×`PresenceState`) e W34 (`HypothesisType`×escopo).

## Política de evolução

Cada `hypothesis_id` na união de `previous_convictions` e `current_hypotheses` é
processado independentemente: presente e novo → `BORN`; presente e já existia, nível sobe
→ `STRENGTHENED`; presente e nível permanece → `PERSISTED`; ausente pela 1ª vez → `WEAKENED`
(streak reinicia, `lifetime_observations` preservado); ausente pela 2ª vez consecutiva →
removida do `ConvictionSet`. Reaparecimento após `WEAKENED` é tratado como `PERSISTED` em
`EMERGING` (não `BORN` de novo, já que o objeto nunca desapareceu). Hipóteses conflitantes
(ex.: `MOVEMENT` e `VISIBILITY` do mesmo track) nunca se comparam — cada uma evolui em sua
própria Conviction, de forma totalmente independente.

## Testes

31 testes novos: enums e `level_for()` nos limiares exatos; imutabilidade e serialização
de `TrackConviction`/`EntityConviction`/`ConvictionSet` (incluindo **teste que prova a
ausência de qualquer campo Decision/Action/Recommendation/Coaching/confidence**);
`update_convictions` cobrindo nascimento, fortalecimento (cruzando `STABLE` e `STRONG`),
persistência, enfraquecimento, remoção após 2 ausências, reaparecimento pós-`WEAKENED`,
nascimento genuíno após remoção completa, determinismo, identidade estável (mesma hipótese
sempre atualiza a mesma Conviction), conflitos não resolvidos, e serialização com múltiplas
convicções.

## Validação contra o artifact real (job `b07f0dc6`, mesmo `HypothesisSet` da W34)

Simulei 6 ciclos encadeados de `update_convictions` sobre o mesmo `HypothesisSet` de 76
hipóteses de track + 6 de entidade (W34) — já que esta sprint não dispõe de múltiplos
`HypothesisSet`s cronológicos reais para "replay" (limitação documentada no plano, Seção
12).

| Métrica | Valor |
|---|---|
| `track_convictions` após 6 ciclos | **76** (todas em `STRONG`, `state=strengthened`) |
| `entity_convictions` após 6 ciclos | **6** (todas em `STRONG`) |
| Determinismo (2 sequências idênticas de 6 ciclos) | **Confirmado** |
| Tamanho serializado — `WorkingState` | 23.468 bytes |
| Tamanho serializado — `ConvictionSet` (após 6 ciclos) | 29.980 bytes |

`stationary:track:1` e `recovery:track:1` (o mesmo "person" analisado desde W28): ambas
com `consecutive_observations=6`, `lifetime_observations=6`, `level=STRONG`,
`state=STRENGTHENED` após o 6º ciclo. Ao remover as hipóteses do track 1 por um ciclo:
`stationary:track:1` passou para `WEAKENED` (`consecutive_observations=0`,
`missed_observations=1`, `lifetime_observations` preservado em `6`); numa 2ª ausência
consecutiva, desapareceu do `ConvictionSet`.

**Nota honesta**: como os 6 ciclos reutilizaram o MESMO `HypothesisSet` (mesmo
`observed_at_timestamp`), `persistence_duration_seconds` permaneceu em `0.0` durante o
teste — isso é uma limitação da validação (ausência de múltiplos frames reais em
sequência), não um bug: em produção, cada ciclo traria um `observed_at_timestamp`
diferente, e `persistence_duration_seconds` cresceria normalmente. Assim como em W34,
`ConvictionSet` é maior que `WorkingState` (expansão esperada, não regressão — múltiplas
convicções independentes por track).

## Compatibilidade

Zero mudança em qualquer arquivo pré-existente. Suíte completa: **786 passed** (755 da
baseline W34 + 31 novos), mesmos 26 failed / 16 errors pré-existentes em
`tests/infrastructure/` (exigem Redis/backend reais) — sem regressão.

## Impacto esperado na futura Planning Layer

Uma futura Planning Layer consumirá `ConvictionSet` (nunca `HypothesisSet`/`WorkingState`
diretamente) e acrescentará decisões/ações condicionadas ao NÍVEL de crença (ex.: uma
Conviction `STRONG` de `STATIONARY` pode justificar uma ação futura), resolução de
conflitos entre convicções concorrentes do mesmo sujeito (Conviction nunca faz isso), e
qualquer noção de objetivo/plano/recomendação. O que continua exclusivo da Conviction
Layer: o mecanismo de persistência em si (nascer/fortalecer/persistir/enfraquecer/
desaparecer), a taxonomia discreta de níveis, e a rastreabilidade `hypothesis_id` até a
hipótese de origem. Planning nunca recalcula convicções a partir de `HypothesisSet`
diretamente.

## Próximos passos

- Revisar a política de reset total de `consecutive_observations` numa única ausência
  contra dado real de produção (múltiplos `HypothesisSet`s cronológicos verdadeiros), se
  se mostrar contraproducente.
- Planning Layer (consome `ConvictionSet`).
- Decision Engine, Coaching, Rule Engine, Explainability, Evaluation (mais distantes,
  consumiriam Planning, não Conviction diretamente).
- Orquestração de quando/com que frequência invocar `update_convictions` ao longo de um
  vídeo (fora do escopo arquitetural desta camada).
