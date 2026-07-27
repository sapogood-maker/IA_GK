# Goalkeeper AI Worker

Serviço independente de visão computacional e raciocínio determinístico do Goalkeeper AI.
Processa vídeos de treino/jogo, percebe o que acontece em campo e produz decisões
estruturadas sobre o que fazer a seguir — sem nunca executar nada no mundo real.

No centro deste serviço vive um **Cognitive Core**: um pipeline de onze camadas,
inteiramente determinístico e agnóstico de domínio, que transforma eventos brutos de
percepção em decisões auditáveis. O scouting de goleiros é a primeira aplicação desse
núcleo, não o seu limite — a mesma arquitetura foi desenhada para ser reutilizável em
qualquer domínio que precise transformar observação em decisão de forma rastreável.

Este é um subprojeto do monorepo `IA_GK`, mas um sistema completamente separado do
backend em runtime, dependências, configuração e banco de dados — ver
`AI_WORKER_CONSTITUTION.md` (raiz do repositório), seção **Boundary Enforcement**.

---

## O que é

O Worker recebe um vídeo, executa detecção e rastreamento de objetos (jogador, goleiro,
bola), organiza o que foi observado em uma linha do tempo de fatos, e então raciocina
sobre esses fatos em etapas sucessivas — do estado atual observado até uma decisão final
sobre qual curso de ação faz sentido. Cada etapa desse raciocínio é uma transformação
pura e determinística: a mesma entrada sempre produz a mesma saída, sem exceção.

O Worker nunca executa a decisão que produz — ele para exatamente no momento em que
decide. O que acontece depois (mostrar ao treinador, acionar um sistema externo, etc.)
é responsabilidade de quem consome essa decisão, fora deste serviço.

## Objetivos

- Transformar vídeo bruto em fatos observáveis, de forma auditável e reproduzível.
- Raciocinar sobre esses fatos em camadas sucessivas, cada uma com uma única
  responsabilidade, sem misturar percepção, hipótese, crença e decisão.
- Produzir uma decisão estruturada — nunca uma ação real, nunca um veredito sobre o
  ambiente.
- Manter um núcleo de raciocínio genérico o bastante para ser reaproveitado por
  aplicações além do scouting de goleiros.

## Principais características

- **Cognitive Core genérico** — nenhuma camada do núcleo conhece futebol, goleiro,
  robótica ou qualquer outro domínio específico.
- **Independente de domínio** — o vocabulário interno (tipos de plano, critérios de
  decisão) é deliberadamente neutro; o goalkeeper scouting é só a primeira aplicação.
- **Determinístico** — toda camada é uma função pura: mesma entrada, mesma saída,
  sempre, sem relógio, estado global ou aleatoriedade.
- **Camadas imutáveis** — todo artefato produzido é um dado imutável (`frozen`), nunca
  um objeto que muda de estado por baixo dos panos.
- **`DecisionSet` como contrato terminal** — o núcleo para de "pensar" exatamente ao
  decidir; nenhuma camada cognitiva existe depois dela.
- **`Evaluation` como camada de observabilidade** — observa como cada decisão foi
  produzida, sem nunca influenciar a decisão em si.
- **Adaptadores externos** — qualquer execução real (mostrar, acionar, recomendar)
  vive fora do núcleo, em código que consome suas decisões.

## Arquitetura

```
Timeline → Explorer → PlaySegment → Enrichment → TemporalMemory → WorkingState
  → Hypothesis → Conviction → Planning → Decision
──────────────────────── fim do Cognitive Core ────────────────────────
  → Evaluation (observa o núcleo, não participa da cognição)
  → Adaptadores Externos → Ambiente
```

Este diagrama é só um resumo. A especificação completa — responsabilidade de cada
camada, o que foi deliberadamente rejeitado e por quê, princípios e invariantes — está em
[`COGNITIVE_CORE_ARCHITECTURE_V1.md`](../COGNITIVE_CORE_ARCHITECTURE_V1.md), na raiz do
monorepo.

## Estado do projeto

**Architecture Freeze v1.0.** O Cognitive Core (`worker/timeline/` até
`worker/evaluation/`) está congelado desde a Sprint W41 — é considerado estável e
completo para a v1.0. Novas funcionalidades acontecem **fora** do núcleo, em
adaptadores externos que consomem `DecisionSet`/`EvaluationSet`; nenhuma camada listada
acima deve ser alterada sem que isso seja tratado explicitamente como uma exceção
deliberada ao freeze, nunca como uma mudança incremental silenciosa.

## Estrutura do repositório

```
worker/
├── timeline/ … evaluation/   # Cognitive Core (11 pacotes, congelado - ver Arquitetura acima)
├── analyzers/, domain/           # análise específica de futebol/goleiro - produz os eventos que alimentam o Timeline
├── inference/                       # engine de visão computacional (detecção, tracking, mundo)
├── explorers/, segments/                # consulta e segmentação da Timeline (já fazem parte do núcleo)
├── infrastructure/, pipeline/,              # infraestrutura de execução do Job: Redis, backend,
│   orchestrator/, core/, config/                R2, ciclo de vida do processo
└── main.py                                          # ponto de entrada do processo

tests/       # espelha worker/ - um pacote de teste por camada
```

## Como executar

Requer Python 3.10+. Ambiente virtual e dependências são inteiramente próprios deste
subprojeto — nunca reutilizar o venv/`requirements.txt` do backend.

```
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e ajuste os valores antes de executar.

```
python -m worker.main
```

O processo inicializa configuração, logging e as dependências externas (Redis, Worker
API), e delega a execução ao `WorkerOrchestrator`, que consome jobs da fila e processa
cada vídeo através do pipeline completo — da inferência até a decisão.

## Testes

```
pytest
```

O projeto tem quase 900 testes automatizados, organizados em um pacote por camada
(incluindo um pacote de teste dedicado para cada uma das camadas do Cognitive Core).
Parte da suíte — os testes de infraestrutura que dependem de Redis/backend reais em
execução — só passa com esses serviços disponíveis localmente; o restante roda de forma
isolada, sem nenhuma dependência externa.

## Documentação

- [`COGNITIVE_CORE_ARCHITECTURE_V1.md`](../COGNITIVE_CORE_ARCHITECTURE_V1.md) — fonte
  oficial da arquitetura do núcleo cognitivo: pipeline definitivo, o que existe e por
  quê, o que foi rejeitado e por quê, princípios e invariantes.
- `SPRINT_W28_REPORT.md` a `SPRINT_W41_REPORT.md` (raiz do monorepo) — histórico
  sprint-a-sprint da construção do núcleo, com as decisões e validações de cada etapa.
- `AI_WORKER_ARCHITECTURE.md`, `AI_WORKER_CONSTITUTION.md`, `DOMAIN_ARCHITECTURE.md`
  (raiz do monorepo) — fronteiras deste Worker dentro do monorepo `IA_GK` (isolamento do
  backend, regras de contrato, domínio de negócio).
- `PERCEPTION_ENGINE_ARCHITECTURE.md` (raiz do monorepo) — documento de planejamento
  histórico que originou o esforço de construção do núcleo.

## Roadmap

O Cognitive Core está congelado — o roadmap daqui em diante é sobre o que se constrói
**ao redor** dele, nunca dentro dele. Qualquer aplicação nova é um adaptador externo que
consome `DecisionSet`/`EvaluationSet` e traduz o vocabulário genérico do núcleo (tipos de
plano, critérios de decisão) para ações concretas do seu próprio domínio:

- Scouting de goleiros (aplicação atual).
- Trading.
- Robótica.
- Diagnóstico (médico ou industrial).

Nenhum desses adaptadores existe neste repositório ainda — o ponto é que o núcleo já foi
desenhado para suportá-los sem precisar mudar.

## Princípios

- Cada camada tem responsabilidade única e só lê a camada imediatamente anterior.
- Cada camada só existe se produz conhecimento genuinamente novo — nunca duplica outra.
- O núcleo nunca conhece o ambiente: sem rede, banco, hardware ou sensores em nenhuma
  camada cognitiva.
- Execução nunca modifica cognição — não há caminho de volta do ambiente para o núcleo.
- Determinismo sempre: mesma entrada, mesma saída, sem estado oculto.

Lista completa e justificativa de cada princípio em
[`COGNITIVE_CORE_ARCHITECTURE_V1.md`](../COGNITIVE_CORE_ARCHITECTURE_V1.md).

## Licença

Ainda não definida.
