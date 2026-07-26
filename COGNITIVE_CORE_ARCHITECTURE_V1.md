# Cognitive Core Architecture — v1.0 (Architecture Freeze)

## 0. Status

**Architecture Freeze v1.0.** A partir da Sprint W41, o Cognitive Core — tudo entre
`worker/timeline/` e `worker/evaluation/` — está congelado. Novas funcionalidades
acontecem FORA do núcleo, em adaptadores externos que consomem `DecisionSet`/
`EvaluationSet`. Nenhuma camada listada aqui deve ser alterada sem uma exceção
explicitamente aprovada e documentada como desvio deliberado desta v1.0 (nunca uma
mudança silenciosa).

## 1. Pipeline definitivo

```
Timeline (W28)
  ↓
Explorer (W29)
  ↓
PlaySegment (W30)
  ↓
Enrichment (W31)
  ↓
TemporalMemory (W32)
  ↓
WorkingState (W33)
  ↓
Hypothesis (W34)
  ↓
Conviction (W35)
  ↓
Planning (W36)
  ↓
Decision (W37)
═══════════════════ Fim do Cognitive Core ═══════════════════
Evaluation (W39, observa o núcleo de fora - não participa da cognição)
  ↓
Adaptadores Externos (fora de worker/, não implementados aqui)
  ↓
Ambiente
```

`Evaluation` fica FORA da caixa do núcleo cognitivo propriamente dito (a linha em W37/W38
já fecha o "pensar") mas ainda DENTRO deste repositório/pacote `worker/`, numa posição
peculiar e deliberada: ela observa o resultado do núcleo (`DecisionSet`) sem nunca
alimentá-lo de volta — ver Seção 4, princípio 7.

## 2. Cada camada: responsabilidade e por que existe

| # | Camada | Entrada | Saída | Responsabilidade única |
|---|---|---|---|---|
| W28 | Timeline | eventos brutos do `ProcessorContext` | `PerceptionTimeline`/`Event` | Registrar fatos observados, cronologicamente, sem interpretar. |
| W29 | Explorer | `PerceptionTimeline` (via artifact) | consultas (`by_frame`, `by_track_id`, `chronological`, ...) | Consultar a Timeline sem duplicar seu armazenamento. |
| W30 | PlaySegment | Timeline explorada | `PlaySegment`s | Agrupar eventos em janelas temporais de "jogada" via `SegmentStrategy`. |
| W31 | Enrichment | eventos brutos | eventos DERIVADOS (`MotionTransition`, etc.) | Produzir fatos de mais alto nível a partir de padrões nos eventos brutos — nunca interpretação, só composição determinística. |
| W32 | TemporalMemory | eventos (brutos+derivados) | `TemporalMemory`/`TrackMemory`/`EntityMemory` | Resumir histórico por track/entidade (duração, contagem, sequência) — primeira camada de agregação/compressão. |
| W33 | WorkingState | `TemporalMemory` | `WorkingState`/`TrackState`/`EntityState` | Projetar o ESTADO ATUAL observável (nunca interpretar) — `MotionState`×`PresenceState` como eixos ortogonais. |
| W34 | Hypothesis | `WorkingState` | `HypothesisSet`/`TrackHypothesis`/`EntityHypothesis` | Primeira camada COGNITIVA — gerar possibilidades plausíveis, nunca fatos consumados; `support` nunca é confiança. |
| W35 | Conviction | `HypothesisSet` + `ConvictionSet` anterior | `ConvictionSet`/`TrackConviction`/`EntityConviction` | Primeira camada com MEMÓRIA — rastrear persistência de hipóteses ao longo do tempo (`ConvictionState`×`ConvictionLevel`). |
| W36 | Planning | `ConvictionSet` | `PlanningSet`/`TrackPlan`/`EntityPlan` | Reorganizar convicções em possibilidades de ação (`PlanType` genérico) — nunca escolhe, nunca prioriza. |
| W37 | Decision | `PlanningSet` | `DecisionSet`/`TrackDecision`/`EntityDecision` | Escolher UM plano por sujeito, com critérios 100% estruturais (nunca semânticos de domínio) — contrato terminal do núcleo (W38). |
| W39 | Evaluation | `DecisionSet` | `EvaluationSet`/`TrackEvaluation`/`EntityEvaluation` | Categorizar COMO cada decisão foi produzida (`ResolutionMethod`) — observa o processo, nunca o resultado no ambiente. |

Cada camada só lê a que está imediatamente abaixo dela nesta tabela — nunca pula camadas,
nunca lê duas abaixo (ex.: Decision nunca lê `ConvictionSet` diretamente).

## 3. O que NÃO existe — e por quê (consolidado de W33-W40)

| Rejeitado | Sprint | Por que |
|---|---|---|
| `Execution` real dentro do núcleo | W38 | Executar = efeito colateral + conhecimento de domínio + acoplamento a ambiente — viola os 3 pilares do núcleo (determinismo, domain-agnosticismo, reutilização). |
| `ExecutionIntent` (camada intermediária entre Decision e ambiente) | W38 | Subconjunto estrito de `DecisionSet` — zero informação nova, zero redução de acoplamento real (um consumidor já lê só os campos que quer). |
| `Explainability` (camada entre Decision/Evaluation e o exterior) | W40 | Toda pergunta que ela responderia já aponta para um campo tipado existente em `DecisionSet`/`EvaluationSet` — juntar os dois por chave é trivial e sempre seguro (join total garantido por construção). |
| `DecisionType`/`DecisionState` | W37 | `PlanType`/`PlanState` já bastam, reaproveitados só como fato (nunca para priorizar) — enums paralelos idênticos seriam redundantes. |
| Prioridade fixa de `PlanType` (ex. `REACQUIRE > ENGAGE > PURSUE > DISENGAGE`) | W37 | Incorporaria conhecimento semântico de domínio dentro de Decision — preservar o núcleo reutilizável para qualquer aplicação futura exige critérios de desempate 100% estruturais. |
| `EvaluationState`/`EvaluationType` separados | W39 | `ResolutionMethod` sozinho já cobre toda a variação real; um segundo enum seria uma codificação mais pobre da mesma informação. |
| `candidate_count`(int) + booleanos redundantes em Evaluation | W39 | Colapsam todos na mesma informação categórica que `ResolutionMethod` já representa. |
| Registry/Factory em qualquer camada | W32-W40 | Nenhuma camada tem, hoje, implementações alternativas reais — introduzir o padrão sem uma segunda implementação concreta seria abstração sem justificativa. |
| Confiança/probabilidade/ML score em qualquer camada | W34, W35 | `support` (Hypothesis) é uma contagem estrutural; `ConvictionLevel` é um nível discreto de persistência — nenhum dos dois é, nem pretende ser, uma medida estatística de acerto. |
| Rule Engine explícito ou implícito | W31, W35, W36, W37 | Cada camada é código fixo (funções puras específicas), nunca um interpretador de regras como dado — distinção mantida mesmo ao nomear pacotes (`producers/`, não `rules/`, W36). |

## 4. Princípios fundamentais (formalizados)

1. **Responsabilidade única por camada** — cada camada responde exatamente UMA pergunta
   (Seção 2, coluna 4). Nenhuma camada tenta fazer o trabalho da próxima nem da anterior.
2. **Cada camada produz conhecimento GENUINAMENTE novo** — critério de existência de
   qualquer camada. Testado explicitamente e negativamente em W38/W40 (`ExecutionIntent`,
   `Explainability` reprovados nesse teste) e positivamente em cada camada que existe
   (Seção 2).
3. **Nenhuma camada duplica outra** — dado que já existe em forma tipada num artefato não
   é copiado para outro; quem precisar, cruza pela chave (`track_id`/`entity`).
4. **Cada camada lê só a imediatamente inferior** — nunca pula camadas, nunca acessa duas
   ou mais camadas abaixo diretamente. Garantido em código (imports) e em documento desde
   W28.
5. **O núcleo nunca conhece o ambiente** — nenhuma camada, do `Timeline` ao `Evaluation`,
   acessa rede, banco, hardware, sensores ou APIs externas. Tudo opera sobre estruturas em
   memória.
6. **Execução nunca modifica cognição** — não existe caminho de volta do ambiente para
   dentro do núcleo (nenhuma camada recebe "feedback de execução" como entrada).
7. **Evaluation observa, mas não participa da cognição** — `EvaluationSet` nunca é lido
   por nenhuma camada do núcleo (Hypothesis/Conviction/Planning/Decision nunca dependem
   dela); ela só olha o resultado já produzido, de fora.
8. **Determinismo total, sempre** — mesma entrada, mesma saída, sempre, em toda camada,
   sem relógio de parede, sem estado global, sem cache obrigatório, sem números
   aleatórios.
9. **Vocabulário sempre genérico, nunca de domínio** — nenhuma camada do núcleo conhece
   futebol, goleiro, robótica ou finanças (revisado explicitamente em W36/W37 para
   remover vocabulário de domínio que havia se infiltrado).

## 5. Invariantes arquiteturais (lista definitiva)

- `Decision` (`DecisionSet`) encerra o núcleo cognitivo — nenhuma camada cognitiva existe
  depois dela (W38).
- `Evaluation` nunca influencia `Decision` — a leitura é estritamente unidirecional
  (`Decision` → `Evaluation`, nunca o contrário).
- Nenhuma camada futura pode acessar `Timeline`/`Event` diretamente se existir uma camada
  intermediária mais próxima que já exponha o dado necessário.
- Nenhuma camada pode produzir conhecimento (campo, fato, categoria) que já existe, de
  forma tipada, em outra camada — deve reaproveitar (import do tipo) ou, se o
  acoplamento direto for indesejável, replicar literalmente com teste de regressão
  (nunca copiar como novo campo "para conveniência").
- Nenhuma camada futura pode ser criada sem uma responsabilidade genuinamente nova,
  testável pelo mesmo critério aplicado em W38/W40 (informação nova, redução de
  acoplamento real, ou responsabilidade distinta — pelo menos uma das três).
- Toda camada é implementada como `dataclass(frozen=True)` + função pura de construção —
  nunca uma classe com métodos que mutam estado.
- Toda ordenação de dict/set em serialização (`to_dict()`) é explícita (`sorted()`) —
  nunca depende da ordem interna de iteração do Python.
- Toda camada tem, no máximo, dois "sujeitos" de agregação: por track (`int`) e por
  entidade (`str`) — nunca um terceiro eixo de agregação introduzido ad hoc.
- Nenhuma camada usa Registry/Factory sem uma segunda implementação real concorrente.
- Campos de julgamento/qualidade/confiança (`confidence`, `quality`, `correct`, `good`)
  nunca existem em nenhuma camada do núcleo.

## 6. As seis perguntas obrigatórias desta sprint

**1. Por que `Decision` é o contrato terminal do núcleo?** Porque é o ponto exato em que
o "pensar" termina e o "agir" começaria — qualquer coisa além de escolher um plano
(executar, avaliar resultado) exigiria conhecimento de ambiente, que o núcleo nunca tem
(W38, Seção 1).

**2. Por que `Execution` não pertence ao núcleo?** Porque executar é, por definição,
efeito colateral + conhecimento de domínio + acoplamento externo — as três coisas que o
núcleo foi construído para nunca ter, sprint após sprint, desde W28 (W38, Seção 1).

**3. Por que `ExecutionIntent` foi rejeitado?** Porque, desenhado com o rigor devido, ele
seria um subconjunto estrito de `DecisionSet` — mesmos valores copiados, zero informação
nova, zero redução de acoplamento real (um consumidor que só quer 2 campos já pode ler só
esses 2 campos de `DecisionSet`) (W38, Seção 2).

**4. Por que `Evaluation` existe?** Porque, ao contrário de `ExecutionIntent`, ela
CALCULA algo que não existia como fato tipado em lugar nenhum —
`ResolutionMethod` categoriza uma string opaca (`winning_criteria`) que exigiria parsing
manual de qualquer consumidor. Passa no teste que `ExecutionIntent` reprovou (W39, Seção
5, Alternativa F).

**5. Por que `Explainability` NÃO existe como camada?** Porque, ao contrário de
`Evaluation`, todas as perguntas que ela deveria responder já apontam para campos
tipados, prontos, existentes em `DecisionSet`+`EvaluationSet` — não sobra nenhum parsing
ou cálculo a fazer; juntar os dois por chave é uma operação trivial e sempre seguro
(join total garantido por construção), não uma responsabilidade nova (W40, Seção 3).

**6. Quais princípios impediram essas decisões?** Os princípios 2 ("cada camada produz
conhecimento genuinamente novo") e 5 ("o núcleo nunca conhece o ambiente") da Seção 4,
aplicados consistentemente: qualquer proposta de camada nova passou pelo teste "isso é
FATO NOVO ou CÓPIA?" antes de virar código — `Evaluation` passou, `ExecutionIntent` e
`Explainability` não.

## 7. Roadmap: como adicionar funcionalidade SEM modificar o núcleo

Toda funcionalidade nova — de qualquer domínio — deve ser um ADAPTADOR EXTERNO, vivendo
fora de `worker/`, que:
1. Consome `DecisionSet` (e, opcionalmente, `EvaluationSet`) como única entrada.
2. Nunca importa camadas internas do núcleo além dessas duas (nunca `WorkingState`,
   `HypothesisSet`, etc. diretamente).
3. Traduz `plan_type`/`winning_criteria`/`resolution_method` (vocabulário genérico) para
   ações concretas do SEU domínio — essa tradução nunca volta a viver dentro de `worker/`.

Exemplos concretos (todos reutilizando exatamente o mesmo núcleo, sem alterar nenhuma
camada):

| Domínio | Adaptador (fora do núcleo) traduziria... |
|---|---|
| Goalkeeper scouting (aplicação atual) | `ENGAGE`/`PURSUE`/`REACQUIRE`/`DISENGAGE` → sugestões táticas para o painel do treinador. |
| Trading | Os mesmos 4 `PlanType`s → ordens de compra/venda/manutenção/saída de posição, com `resolution_method` informando o operador sobre o grau de certeza estrutural da escolha. |
| Robótica | `ENGAGE`/`PURSUE` → comandos de aproximação/perseguição de um atuador físico; `DISENGAGE` → parada seguindo protocolo do robô. |
| Diagnóstico (médico/industrial) | `RECOVERY`/`REACQUIRE` → reconfirmar uma leitura de sensor antes de agir; `winning_criteria` alimentando um log de auditoria clínico/industrial. |
| Sistemas especialistas genéricos | `DecisionSet`+`EvaluationSet` → entrada para uma camada de regras de negócio especializada, fora do núcleo, sem nunca precisar entender Hypothesis/Conviction/Planning internamente. |

Nenhum desses adaptadores é implementado aqui — o ponto desta seção é mostrar que o
NÚCLEO JÁ é suficientemente genérico para todos eles, sem mudar uma linha.

## 8. Autocrítica honesta do núcleo v1.0

**Limitações que permanecem, deliberadamente não resolvidas:**

1. **Sem dado espacial/trajetória** — `TrackMemory`/`WorkingState` nunca carregam
   posição/direção (achado de W34) — qualquer `TrajectoryHypothesis` ou plano baseado em
   rota permanece impossível sem estender `worker/memory/`, fora do escopo de qualquer
   sprint até agora.
2. **`PresenceState` é um modelo de presença deliberadamente pobre** (só
   `PRESENT`/`ENDED`, W33) — não reconstrói períodos intermediários de perda/recuperação,
   só a foto final da janela observada.
3. **Limiares numéricos arbitrários em várias camadas** (`_STABLE_THRESHOLD=3`,
   `_STRONG_THRESHOLD=6`, `_MAX_CONSECUTIVE_MISSES=1`, W35; `_MIN_STABLE_DURATION_SECONDS`,
   W34) — escolhas de projeto, nunca derivadas de dado real de produção em escala.
4. **Acoplamento textual entre W37→W39** (strings de `winning_criteria` replicadas sem
   constante nomeada de origem) — a réplica mais frágil já introduzida no núcleo,
   protegida só por teste de regressão, não por import.
5. **O mapeamento 1:1 `HypothesisType`→`PlanType` é uma simplificação, não uma lei
   permanente** (W36, explicitamente registrado) — um mesmo tipo de hipótese só habilita
   um tipo de plano hoje.
6. **Nenhuma resolução de conflito ENTRE sujeitos diferentes existe** — Decision (e toda
   camada acima) opera estritamente por sujeito (track/entidade); nunca existiu, em
   nenhuma sprint, uma arbitração cross-subject.
7. **Validação de Conviction/Planning contra dado real usou o MESMO `HypothesisSet`
   repetido em ciclo, não múltiplos `HypothesisSet`s cronológicos genuínos** (W35) —
   `persistence_duration_seconds` nunca foi exercitada com progressão real de tempo em
   produção.
8. **`EvaluationSet` não vê sujeitos que nunca tiveram decisão** (W39) — não distingue
   "evidência insuficiente" de "nada a avaliar".

**O que deliberadamente ficou fora (por decisão, não por limitação técnica):**

- Qualquer geração de texto em linguagem natural (Explainability, W40, risco 1).
- Qualquer forma de aprendizado/ajuste automático de limiares.
- Qualquer persistência em banco/arquivo dos artefatos intermediários (tudo vive em
  memória, por chamada).
- Qualquer mecanismo de versionamento de contrato para `DecisionSet`/`EvaluationSet`
  (W38/W39, risco registrado, não implementado).

**O que justificaria uma v2.0 do núcleo** (não implementado aqui, só registrado):

- Extensão de `TrackMemory`/`WorkingState` com dado espacial real, habilitando
  `TrajectoryHypothesis`/`PlanType`s de rota.
- Um mecanismo real de versionamento de contrato para `DecisionSet`/`EvaluationSet`, se
  adaptadores externos reais passarem a depender dele em produção.
- Revisitar `PresenceState` com um sinal de presença mais rico, se `TrackMemory` for
  estendida.
- Uma camada de arbitração cross-subject, se um caso de uso concreto exigir "só uma ação
  por vez no total".
- Geração de texto em linguagem natural, como sprint genuinamente nova e distinta (nunca
  uma revisão de W40).

## 9. Declaração de congelamento

A partir de W41: `worker/timeline/`, `worker/explorers/`, `worker/segments/`,
`worker/timeline/enrichment/`, `worker/memory/`, `worker/perceptual_state/`,
`worker/hypothesis/`, `worker/conviction/`, `worker/planning/`, `worker/decision/`,
`worker/evaluation/` compõem o Cognitive Core v1.0, CONGELADO. Qualquer alteração futura
nessas camadas exige ser tratada explicitamente como uma exceção a este freeze — nunca uma
mudança incremental silenciosa — e justificada com o mesmo rigor usado em toda decisão
deste documento (Seção 4, princípio 2: informação genuinamente nova, ou não se justifica).
