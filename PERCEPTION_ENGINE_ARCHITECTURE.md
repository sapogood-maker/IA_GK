# Perception Engine — Auditoria Arquitetural e Roadmap

Documento de planejamento técnico. Nenhum código foi escrito. Base: leitura completa do
pipeline real (`goalkeeper_ai_worker/worker/`) e do `artifact.json` real produzido em
produção (ver auditoria da camada de IA, sessão anterior). Todo achado aqui é rastreável a
um arquivo/linha real do repositório — nada é especulação sobre o que "deveria existir".

---

## 1. Como deveria ser uma arquitetura profissional de percepção para goleiros

Empresas de Computer Vision aplicada a esporte (Second Spectrum, Stats Perform/Opta,
SkillCorner, Sportlogiq, Hawk-Eye) convergem para o mesmo desenho, independente do esporte:

```
Ingestão → Detecção → Tracking (+Re-ID) → Calibração (pixel→campo) →
Pose/Biomecânica → Timeline de Eventos → Entendimento Tático → Relatório
```

Cinco princípios que essa indústria trata como não-negociáveis, e que respondem
diretamente ao que falta hoje no Goalkeeper AI:

1. **Percepção é objetiva; julgamento é separado.** "A bola estava a 30cm da linha" é
   percepção. "O goleiro reagiu bem" é julgamento. O projeto já tem essa separação certa
   em espírito (Analyzers "de observação" vs. Analyzers "de avaliação" via Rule
   Evaluation) — é o instinto arquitetural mais valioso já presente e **não deve mudar**.
2. **Calibração pixel→campo é fundação, não opcional.** Sem homografia (transformar
   coordenadas de pixel em metros no campo real), nenhuma métrica física (km/h, metros
   percorridos) é válida — é sempre relativa ao zoom/ângulo daquela câmera específica.
   **Hoje isso não existe em nenhum lugar do código** (confirmado: todo cálculo de
   posição/velocidade nos Analyzers usa pixels/frame diretamente).
3. **Identidade persistente (tracking + Re-ID) sobrevive a oclusão.** ByteTrack sozinho
   perde a identidade de um objeto quando ele some de cena por alguns frames e reaparece;
   Re-ID (embedding de aparência) resolve isso. O `artifact.json` real mostra exatamente
   esse sintoma: 48 tracks iniciadas, 46 perdidas, ao longo de um único vídeo curto.
4. **A unidade de análise é o evento/jogada, nunca o frame isolado.** Nenhuma empresa séria
   de sports analytics decide "o que aconteceu" olhando um frame só — é sempre uma janela
   temporal. Esse é o ponto #1 a corrigir no projeto atual (seção 3).
5. **Confiança se propaga.** Uma detecção com 0.3 de confiança deveria produzir um evento
   de baixa confiança, não um `null` categórico ou um `true` categórico. Hoje a maioria dos
   Analyzers usa lógica binária (detectado/não-detectado) sem propagar a confiança da
   detecção original.

---

## 2. Componentes atuais — responsabilidades, o que está certo, o que não está

| Componente | Responsabilidade ideal | Está certo hoje | Está incorreto/faltando |
|---|---|---|---|
| **YOLO** (`inference/detectors/yolo_detector.py`) | Detectar as classes do domínio: bola, goleiro, jogador de linha, árbitro, trave | A abstração (`Detector` protocol + Registry/Factory, `inference/detectors/registry.py`) está certa — trocar o modelo não exige tocar em mais nada | O modelo concreto é `yolo11n.pt` **genérico, pré-treinado em COCO, nunca fine-tunado**. Confirmado: no vídeo real, classes detectadas incluíram `skateboard`, `tennis racket`, `frisbee` — ruído do COCO, não do domínio. Não existe classe "goleiro" nem "bola de futebol" nativa |
| **ByteTrack** (`inference/trackers/bytetrack_tracker.py`) | Manter identidade de cada objeto ao longo do clipe inteiro, inclusive sob oclusão | Escolha de algoritmo correta para o problema (multi-object tracking online); abstração (`Tracker` protocol) correta | Falta Re-ID (embedding de aparência) para recuperar identidade após oclusão longa; tracks operam só em pixels, sem noção de "isso é o MESMO goleiro que sumiu 2s atrás" além do que o ByteTrack puro oferece |
| **WorldModel** (`inference/world/world_model.py`) | Estado do mundo em coordenadas físicas do campo, com histórico completo | Camada genérica bem desenhada (não conhece regras de futebol, só objetos/trajetórias) — separação de responsabilidade correta | Falta calibração (tudo em pixels), e mantém só uma janela recente (`world_max_trajectory`/`world_history_size`), não o histórico do clipe inteiro |
| **15 Analyzers** (`worker/analyzers/`) | Responder perguntas específicas e compostas sobre a cena, com explicabilidade (Rule Evaluation) | **A parte mais bem desenhada do sistema hoje**: composição limpa (cada Analyzer combina os anteriores, nunca duplica lógica), Rule Evaluation explícita (`rules_evaluated`/`rules_passed`/`rules_failed`), Registry/Factory, testável isoladamente | Fundamentalmente comprometidos por operarem em **snapshot de um único frame**: `BasicVisionEngine.process()` (linha 284-286) faz `latest_results_by_analyzer[nome] = resultado` **dentro do loop de frames** — cada frame novo sobrescreve o anterior. Só o resultado do ÚLTIMO frame sobrevive no artifact. Isso não é um bug de implementação isolado: é a limitação arquitetural central de todo o projeto hoje |

**Conclusão da seção 2**: a arquitetura de camadas (Detector → Tracker → SceneAnalyzer →
WorldModel → FootballDomain → Analyzer, tudo via Registry/Factory + Processor pipeline)
está certa e deve ser preservada integralmente. O que falta não é "trocar componentes" — é
**adicionar uma camada temporal que hoje não existe**, e trocar dados de entrada (modelo
genérico → domínio) sem tocar nas interfaces.

---

## 3. Arquitetura temporal — de snapshot para sequência de eventos

### O problema exato, com evidência
`BasicVisionEngine.process()` roda os 15 Analyzers a cada um dos 569 frames, mas só guarda
o resultado do frame 568 (o último) no artifact final. Se o goleiro fez uma defesa no frame
300, e nos frames 560-569 a cena está vazia (bola/goleiro fora de quadro), o relatório final
diz `"insufficient_information"` — a defesa "aconteceu" mas nunca aparece em lugar nenhum.
Isso foi comprovado no vídeo real de produção.

### Event Timeline
Um log **append-only**, ordenado por frame/timestamp, de objetos `Event` tipados
(`event_type`, `frame_index`, `timestamp_seconds`, `track_ids` envolvidos, `confidence`,
`payload`). Em vez de um Analyzer devolver "o estado atual", ele **emite eventos quando
detecta uma transição relevante** (`ShotDetected@frame312`, `GoalkeeperDived@frame315`,
`SaveMade@frame320`). Nada é sobrescrito; tudo se acumula. Isso substitui diretamente o
`latest_results_by_analyzer` de hoje — mesma responsabilidade dos Analyzers, saída
diferente (eventos, não snapshot).

### Temporal Memory
Uma interface compartilhada que qualquer Analyzer pode consultar: "o que aconteceu nos
últimos N segundos" ou "desde que a jogada começou", não só "agora". Hoje isso já existe de
forma ad-hoc e isolada em alguns Analyzers stateful (`BallMotionAnalyzer`,
`BallTrajectoryAnalyzer` mantêm histórico próprio internamente) — a proposta é **generalizar
esse padrão** numa API única, em vez de cada Analyzer reimplementar sua própria memória.

### Track History
Hoje o `WorldModel` mantém só uma janela recente por objeto (`world_max_trajectory=30`
pontos). Track History é a trajetória **completa do clipe inteiro** por `track_id` —
necessária para métricas biomecânicas reais (distância total percorrida, tempo de reação
medido desde o primeiro movimento detectado).

### State Transitions
Hoje `goalkeeper_decision_result.decision` é uma classificação **independente por frame**
(pode ser `"unknown"` num frame e `"DIVE_LEFT"` no seguinte sem nenhuma transição
validada entre os dois). A proposta é uma máquina de estados explícita por entidade (seção
7), onde toda mudança de estado passa por uma transição com guarda (ex.: só se pode ir de
`READY` para `DIVING` se houve um `ShotDetected` antes) — usando o mesmo mecanismo de Rule
Evaluation que já existe (W23), só que decidindo transições em vez de vereditos isolados.

### Scene Understanding
A unidade de análise deixa de ser o frame e passa a ser a **Jogada** (`Play`): um segmento
temporal delimitado por `PlayStarted`/`PlayEnded`, contendo toda a Event Timeline daquele
intervalo. Os Analyzers cognitivos (situação, decisão, avaliação, resultado, coaching)
passam a raciocinar sobre **a Jogada inteira**, não sobre "o frame atual" — resolvendo
diretamente o problema descrito no início desta seção.

---

## 4. Arquitetura em camadas

Refinando a proposta do usuário com base no que já existe e no que a seção 3 exige:

```
L1  Raw Video           — worker/video/reader.py (existe, OpenCV)
L2  Frame               — worker/video/iterator.py + color_processor (existe)
L3  Calibration         — NOVO. Homografia pixel→campo. Hoje inexistente.
L4  Detections          — YOLODetector (existe; modelo precisa ser trocado, não a interface)
L5  Tracking + Re-ID    — ByteTrack (existe); Re-ID é NOVO
L6  World State         — WorldModel (existe; precisa consumir L3 p/ unidades físicas)
L7  Football Domain     — FootballWorld (existe; goals hoje são geometria assumida, não
                          detectada — ver seção 2/relatório anterior)
L8  Event Timeline      — NOVO. Substitui o overwrite por acumulação (seção 3)
L9  Play Segmentation   — NOVO. Agrupa a Timeline em unidades de Jogada
L10 Goalkeeper          — Analyzers de decisão/avaliação (existem), reescritos para
    Understanding         consumir L9 em vez de snapshot de frame único
L11 Performance &       — performance_evaluation/coaching Analyzers (existem), mesma
    Coaching               correção de L10 aplicada
L12 Coaching Report     — goalkeeper_analysis_report (existe), evolui para agregar
                          múltiplas Jogadas de uma sessão, não só uma
```

L1, L2, L4, L5, L6, L7, L10, L11, L12 já têm implementação real hoje — a evolução é
**consumir a camada nova (L8/L9) sem quebrar o que já existe**, não reescrever do zero.
L3 e L8/L9 são as únicas camadas genuinamente novas.

---

## 5. Entidades do domínio

**Atores**: `Goalkeeper`, `Player` (linha), `Referee`, `Team`.

**Objetos físicos**: `Ball`, `Goal`, `Pitch`/`Field`, `GoalZone` (já existe).

**Estruturas de rastreio**: `Track`, `Trajectory`, `TrackHistory` (novo).

**Ações/técnicas do goleiro**: `Save`, `Dive`, `Jump`, `FootContact`, `HandContact`,
`Punch`, `Catch`, `Deflection`, `Clearance`, `Rebound`, `Recovery`.

**Ações de jogo (bola)**: `Shot`, `Pass`, `Cross`, `Touch`, `BallOut`, `Turnover`.

**Estruturais/situacionais**: `Play` (novo, unidade central da seção 3), `Attack`,
`Defense`, `Transition`, `Possession`, `Pressure`.

**Situações de bola parada** (contexto que muda a interpretação do goleiro): `CornerKick`,
`FreeKick`, `Penalty`, `ThrowIn`.

**Métricas/saída**: `Metric` (já existe no schema Postgres), `Event` (novo),
`GoalkeeperDecision` (já existe como enum), `Report` (já existe no schema Postgres, vazio).

---

## 6. Eventos

**Detecção/tracking (infraestrutura, já parcialmente existe em `scene_events`)**:
`BallDetected`, `BallLost`, `GoalkeeperDetected`, `GoalkeeperLost`, `PlayerDetected`,
`TrackStarted`, `TrackRecovered` (já existem hoje, nível de cena genérica).

**Bola**: `ShotStarted`, `BallReleased`, `BallTouched`, `BallCaught`, `BallPunched`,
`BallDeflected`, `BallOut`, `BallCrossedLine`, `ReboundOccurred`.

**Goleiro**: `GoalkeeperMoved`, `GoalkeeperPositioned`, `GoalkeeperJumped`,
`GoalkeeperDived`, `GoalkeeperRecovered`, `GoalkeeperCommitted`, `SaveMade`.

**Resultado**: `GoalScored`, `ShotBlocked`, `ShotMissed`, `ShotOnTarget`, `ShotOffTarget`.

**Jogada/tático**: `PlayStarted`, `PlayEnded`, `PossessionChanged`, `PressureApplied`,
`TransitionDetected`, `CrossDetected`, `PassDetected`.

Todo evento carrega: tipo, frame/timestamp, `track_ids` envolvidos, confiança, e um payload
específico do tipo — nunca reaproveita o formato ad-hoc de `scene_events` de hoje (que é
genérico demais para carregar semântica de futebol).

---

## 7. Máquina de estados

Duas máquinas **ortogonais** que interagem (o estado da Jogada restringe quais transições
do Goleiro são válidas — mesmo papel que a Rule Evaluation da W23 já cumpre hoje, ex.:
"`shot_prompts_active_response`"):

**Estado da Jogada (Play)**:
```
WAITING → BALL_IN_PLAY → SHOT_IN_PROGRESS → PLAY_FINISHED → WAITING
                ↓
            BALL_OUT → WAITING
```

**Estado do Goleiro**, guardas entre parênteses (condição/evento que habilita a
transição):
```
OBSERVING ──(GoalkeeperPositioned)──▶ READY
READY ──(ShotStarted)──▶ PREPARE_DIVE
PREPARE_DIVE ──(GoalkeeperJumped | GoalkeeperDived)──▶ DIVING
DIVING ──(SaveMade | GoalScored | BallOut)──▶ RECOVERING
RECOVERING ──(GoalkeeperRecovered)──▶ OBSERVING
READY ──(PlayEnded, sem chute)──▶ OBSERVING
```
Cada transição é uma regra explícita e testável isoladamente (mesmo padrão de
`goalkeeper_decision_evaluation.py`, reaproveitado — não reinventado).

---

## 8. Métricas

| Métrica | Depende de |
|---|---|
| Tempo de reação | `ShotStarted` → primeiro `GoalkeeperMoved` (Event Timeline) |
| Velocidade lateral | Track History + Calibração (L3) |
| Velocidade do mergulho | Track History no intervalo `PREPARE_DIVE`→`DIVING` |
| Distância percorrida (por jogada/sessão) | Track History completa + Calibração |
| Posicionamento (desvio do ângulo ideal) | `goalkeeper_position_result` + `goal_geometry` real (não placeholder) |
| Cobertura do gol | `GoalZone` (já existe) + posição real do goleiro |
| Tempo até recuperação | `DIVING`→`RECOVERING` (máquina de estados, seção 7) |
| Número de defesas | Contagem de `SaveMade` na Event Timeline |
| Eficiência (% de reações corretas) | `goalkeeper_decision_evaluation` agregado por sessão, não por frame |
| Precisão de posicionamento | Desvio médio ao longo de todas as Jogadas de uma sessão |

Todas dependem diretamente das seções 3/4/5 — nenhuma é calculável de forma confiável no
modelo atual de snapshot único.

---

## 9. Worker como motor cognitivo

Três camadas de raciocínio, formalizando o que já existe parcialmente hoje:

1. **Percepção** ("o que existe neste frame?") — L4-L7 de hoje, inalteradas.
2. **Consciência situacional** ("o que está acontecendo na jogada?") — Event Timeline +
   Play Segmentation (L8-L9, novas) agregando percepção ao longo do tempo.
3. **Julgamento** ("qual decisão o goleiro tomou, e foi a certa?") — os Analyzers
   cognitivos de hoje (`goalkeeper_decision`, `..._evaluation`, `play_outcome`,
   `performance_evaluation`, `coaching`), **realimentados pela camada 2 em vez do frame
   único** — a mudança de fonte de dados, não de lógica de julgamento (a Rule Evaluation
   já é sofisticada o suficiente; só precisa de melhor matéria-prima).

---

## 10. Roadmap — Sprints incrementais (W28+)

Cada sprint: aditiva, testes verdes, zero breaking change nos campos do artifact já
existentes (novos campos são adicionados ao lado dos antigos, nunca substituem até uma
sprint explícita de migração).

| Sprint | Entrega | Por quê nessa ordem |
|---|---|---|
| **W28** | `Event` + `EventTimeline` (estruturas de dados só, sem mudar Analyzers ainda) | Fundação sem risco — não toca em nada existente |
| **W29** | Track History completo (todo o clipe, não só janela recente) | Pré-requisito de métricas de distância/velocidade |
| **W30** | Play Segmentation (`PlayStarted`/`PlayEnded`) | Define a unidade de análise antes de mudar quem a consome |
| **W31** | Goalkeeper State Machine (seção 7), rodando em paralelo ao `decision` atual | Testável isoladamente antes de virar a fonte oficial |
| **W32** | Temporal Memory API (generaliza o padrão stateful já usado por Ball Motion/Trajectory) | Interface única para os Analyzers consumirem histórico |
| **W33** | Rewire dos Analyzers cognitivos para consumir Timeline/Play (campos novos ao lado dos antigos) | Sprint mais sensível — por isso vem depois de tudo validado isoladamente |
| **W34** | Calibração (homografia pixel→campo) | Independente das anteriores, pode paralelizar |
| **W35** | Métricas em unidades físicas reais (usa W29+W34) | |
| **W36** | Re-ID (persistência de identidade sob oclusão) | Melhora ByteTrack sem trocar sua interface |
| **W37** | Fine-tuning do Detector para classes do domínio (bola, goleiro, trave) — troca só o peso do modelo, não a interface `Detector` | Maior ganho de qualidade de detecção, isolado das mudanças estruturais |
| **W38** | Novas entidades/eventos (Pass, Cross, Rebound, Possession, Pressure, Transition) | Depende da Timeline (W28) já estar madura |
| **W39** | Metrics Engine (agrega todas as métricas da seção 8 num relatório único) | |
| **W40** | Coaching Report v2 — agregação multi-jogada/multi-sessão | Fecha o ciclo: de detector de objetos a treinador virtual |

Cada sprint segue o mesmo processo já usado nas Sprints W13-W27 (Analyzer novo + testes +
validação manual + relatório `SPRINT_W{N}_REPORT.md`) — nenhum processo novo precisa ser
inventado, só continuado.
