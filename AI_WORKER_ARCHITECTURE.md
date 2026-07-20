# AI_WORKER_ARCHITECTURE.md — Arquitetura Oficial do AI Worker (Goalkeeper AI)

> Documento de arquitetura. Nenhum código foi escrito ou alterado para produzi-lo.
> Objetivo: definir a arquitetura do AI Worker pensando num horizonte de 2-3 anos (múltiplos workers, milhares de vídeos, vários clubes, vários modelos de IA), preservando as premissas definidas pelo usuário:
> - A IA **não** roda no servidor do SaaS — roda numa máquina separada (hoje: 1 máquina com AMD RX 7900 XTX; no futuro: várias máquinas).
> - O backend FastAPI continua responsável **apenas** por autenticação, gerenciamento, upload, Cloudflare R2, banco de dados e API.
> - O AI Worker é um serviço **totalmente independente**.

Onde esta proposta diverge do que já estava esboçado em `docs_ai_worker_spec.md`/`docs_architecture_overview.md` (documentos aspiracionais já existentes no repositório), isso é sinalizado explicitamente com **⚠️ Mudança proposta**.

---

## 1. Arquitetura geral do sistema

Componentes e como conversam entre si:

| Componente | Papel | Fala com |
|---|---|---|
| **Frontend (Flutter Web)** | UI para treinadores/clubes: cadastro, upload de vídeo, acompanhamento de status, relatórios | Backend (REST + JWT) |
| **Backend (FastAPI)** | Autenticação, regras de negócio, CRUD, geração de URLs assinadas do R2, única porta de entrada para o banco | Frontend, PostgreSQL, Cloudflare R2, Fila, Telegram |
| **PostgreSQL** | Fonte da verdade dos dados (usuários, clubes, goleiros, sessões, vídeos, jobs, eventos/resultados) | Somente o Backend |
| **Cloudflare R2** | Armazenamento de vídeos originais e artefatos gerados (thumbnails, clipes) | Backend (credenciais mestras) e AI Worker (apenas via URLs assinadas de curta duração) |
| **Fila de processamento** | Distribui jobs de vídeo entre os workers disponíveis, garantindo que cada vídeo seja processado por exatamente um worker por vez | Backend (publica) e AI Worker(s) (consomem) |
| **AI Worker(s)** | Serviço externo, independente, que consome jobs da fila, processa o vídeo e devolve resultados **somente via API do Backend** | Fila, Cloudflare R2 (via URL assinada), Backend (API REST) |
| **Dashboard** | Não é um componente separado — é a própria tela do Frontend (Painel/Vídeos/Análises), alimentada pelos dados que já passam pelo Backend | Backend |
| **Telegram** | Canal de notificação (ex.: "vídeo processado", "falha no processamento"), acionado pelo Backend quando o status de um job muda | Backend → API do Telegram |

Regra estrutural mais importante deste documento (detalhada na seção 12): **o AI Worker nunca acessa o PostgreSQL diretamente, e nunca guarda as credenciais mestras do R2**. Toda a comunicação do worker com o resto do sistema passa por (a) a fila, para receber trabalho, e (b) a API REST do backend, para tudo o mais. Isso é o que torna o worker verdadeiramente "totalmente independente" — ele pode rodar em qualquer máquina, de qualquer lugar, sem carregar nenhum segredo de acesso amplo ao sistema.

---

## 2. Fluxo completo de um vídeo (upload → relatório)

1. O treinador seleciona Clube → Goleiro → Sessão de treino → arquivo de vídeo, na tela "Vídeos" do Frontend (já implementado).
2. O Frontend envia o arquivo para o Backend (`upload` multipart).
3. O Backend valida o arquivo (extensão, tamanho), envia o vídeo para o Cloudflare R2, cria o registro do vídeo (status: enviado/"no R2") e cria um **job de processamento** com status inicial de pendente.
4. O Backend publica uma mensagem na **fila**, referenciando esse job (contendo o suficiente para o worker saber qual vídeo processar: identificador do job, do vídeo, e da sessão/goleiro/clube associados).
5. Um **AI Worker** disponível — entre 1 e N, dependendo de quantos estiverem online — consome essa mensagem da fila. A fila garante que **somente um** worker recebe aquela mensagem por vez.
6. O worker pede ao Backend uma **URL assinada de leitura** para aquele vídeo específico no R2, e atualiza o status do job para "baixando".
7. O worker baixa o vídeo diretamente do R2 usando essa URL (não passa pelo Backend para isso, evitando sobrecarregá-lo).
8. O worker atualiza o status do job para "processando" e executa o pipeline interno (detalhado na seção 9): pré-processamento, detecção, rastreamento, extração de métricas, classificação de eventos.
9. O worker atualiza o status para "gerando relatório" e monta os artefatos (thumbnails, recortes de clipe, JSON estruturado de eventos).
10. O worker pede ao Backend uma **URL assinada de escrita** para subir esses artefatos ao R2 (num prefixo próprio daquele job).
11. O worker envia o resultado estruturado (eventos detectados, metadados, referências aos artefatos) para o Backend via API.
12. O Backend persiste os eventos/relatório no PostgreSQL e marca o job como concluído (ou como falho, com a mensagem de erro, se algo deu errado em qualquer etapa).
13. O Backend atualiza o Frontend (mecanismo detalhado na seção 13) e, opcionalmente, dispara uma notificação no Telegram.
14. O treinador acessa a tela de Análises/Relatórios, revisa os eventos detectados e pode confirmá-los/corrigi-los (fluxo de validação humana, já previsto na documentação original do produto, mesmo que ainda não implementado).

---

## 3. Como o AI Worker deve funcionar

- **Quando inicia:** é um processo de longa duração (roda continuamente na máquina dedicada), iniciado junto com o serviço/sistema daquela máquina. Ao subir, conecta-se à fila e faz um "anúncio" de que está disponível (relevante para o monitoramento, seção 14).
- **Como recebe trabalho:** consumindo mensagens da fila — não fica perguntando ativamente ao backend "tem vídeo novo?" (isso seria *polling*, descartado na seção 4). A fila empurra o trabalho para o primeiro worker livre.
- **Como sabe que existe vídeo novo:** o Backend publica a mensagem na fila no exato momento em que o upload é concluído — o worker só precisa estar conectado, a fila cuida da entrega.
- **Como baixa o vídeo:** solicita uma URL assinada de leitura ao Backend e baixa diretamente do R2 (seção 11).
- **Como processa:** pipeline interno de várias etapas (seção 9), reportando progresso incremental ao Backend a cada etapa concluída, não só no início/fim.
- **Como devolve o resultado:** via chamadas REST ao Backend (mesma API que o Frontend usa, com uma identidade própria de worker — seção 6), nunca escrevendo diretamente no banco.

---

## 4. Fila de processamento — comparação e recomendação

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **Polling** (worker pergunta ao backend de tempos em tempos) | Trivial de implementar, já existe suporte parcial na API atual | Atraso proporcional ao intervalo de consulta; gera carga constante no backend/banco mesmo sem trabalho; **não garante exclusividade** (dois workers podem pegar o mesmo job sem um mecanismo extra de "trava") |
| **Redis** (Streams com *consumer groups*) | Leve, simples de operar, baixa latência; Streams com consumer group já entregam exclusividade de mensagem, confirmação (ACK) e reentrega automática em caso de falha do worker; roda facilmente em qualquer provedor, inclusive Coolify | Recursos de roteamento mais limitados que um broker de mensageria "de verdade"; menos ferramental de administração pronta que o RabbitMQ |
| **RabbitMQ** | Broker de mensageria maduro: fila de mortos (DLQ), prioridade, retry nativo, roteamento flexível, interface de administração pronta | Mais um serviço a operar (processo Erlang, mais memória), curva de aprendizado maior; para o volume deste projeto, boa parte dos recursos avançados não seria usada |
| **Kafka** | Pensado para volumes altíssimos (milhões de eventos/segundo) e retenção/replay de longo prazo | Complexidade operacional desproporcional ao caso de uso ("milhares" de vídeos, não milhões de eventos); exige mais infraestrutura de suporte; não agrega benefício real neste cenário |
| **Outras** (AWS SQS, NATS) | SQS é gerenciado (zero operação); NATS é leve e simples | SQS amarraria o projeto à AWS, quando o armazenamento já é Cloudflare R2 (evitar mais um provedor); NATS tem ecossistema/comunidade menor para este caso de uso |

### Recomendação: **Redis (Streams com consumer group)**

Justificativa: este é um projeto mantido por uma equipe pequena, hospedado via Coolify, com uma expectativa de escala de "milhares de vídeos" e até "20 workers" em alguns anos — não milhões de eventos por segundo. Redis Streams já entrega exatamente as garantias que importam aqui (um job vai para um único worker por vez; se o worker cair no meio do processamento, a mensagem volta para a fila depois de um tempo, sem duplicar trabalho em condições normais) com uma fração da complexidade operacional do RabbitMQ ou do Kafka. RabbitMQ é uma alternativa perfeitamente válida caso, no futuro, surjam necessidades de roteamento mais sofisticadas (múltiplas filas por prioridade/tipo de tarefa, retry com backoff configurável por fila, etc.) — a migração de Redis Streams para RabbitMQ é viável mais adiante sem redesenhar o resto da arquitetura, porque o contrato entre backend/worker é sempre "publicar/consumir uma mensagem de job", independente do broker por trás.

---

## 5. Comunicação — comparação e recomendação

Aqui é importante separar duas necessidades diferentes de comunicação:

**(a) Backend → Worker (entrega de trabalho):** já resolvido pela fila (seção 4). Não é REST, gRPC nem WebSocket — é mensageria.

**(b) Worker → Backend (reportar progresso e resultados) e Backend → Frontend (mostrar progresso):**

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **REST (HTTP/JSON)** | Já é o padrão usado entre Frontend e Backend; simples, legível, fácil de depurar; o worker vira "só mais um cliente" da mesma API | Não é o mecanismo ideal para *push* em tempo real do backend para o frontend (mas o worker→backend é sempre um cliente chamando, então isso não é problema nessa direção) |
| **gRPC** | Mais eficiente em volume altíssimo de chamadas, contratos fortemente tipados | Exige geração de código a partir de esquemas (protobuf), menos acessível/depurável, complexidade desnecessária para a frequência de chamadas deste caso (atualização de progresso de job, não uma chamada de altíssima frequência) |
| **WebSocket** | Bidirecional, tempo real | Overhead de gerenciar conexões persistentes (reconexão, múltiplas abas do navegador, etc.) — desproporcional a uma necessidade que é, na prática, unidirecional (servidor avisando o cliente) |
| **Mensageria** (usar a mesma fila também para status) | Reaproveita a infraestrutura já existente | Obrigaria o Backend a também ser um consumidor de fila só para atualizar status — mais complexidade na API sem necessidade, já que o Backend já é (e deve continuar sendo) uma API REST comum |

### Recomendação: **REST** para Worker → Backend (mesmo estilo já usado pelo Frontend), e **Server-Sent Events (SSE)** para Backend → Frontend quando o polling atual não for mais suficiente (detalhado na seção 13). gRPC e WebSocket ficam descartados para este caso de uso — não resolvem nada que REST/SSE já não resolvam aqui, e adicionam complexidade operacional que não se paga na escala prevista.

---

## 6. Autenticação do Worker — comparação e recomendação

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **JWT** (reaproveitar o login de usuário comum) | Reaproveita 100% do mecanismo já existente, zero código novo de autenticação | Mistura o conceito de "usuário humano" com "identidade de máquina"; access tokens expiram em minutos, exigindo lógica de refresh constante no worker; não dá para restringir facilmente "isso só pode chamar endpoints de job" |
| **API Key** | Simples, de longa duração, fácil de revogar por worker/máquina individualmente; não depende de fluxo de login; fácil de auditar qual worker fez o quê | Precisa de um mecanismo próprio de emissão/rotação no backend (pouco código, mas é novo) |
| **Service Account** (conceito de autorização, não de transporte) | Formaliza que o worker é uma identidade de máquina com permissões restritas (só endpoints de job, nunca CRUD de clubes/usuários) | Não é uma alternativa a JWT/API Key — é uma camada de **autorização** que deve ser combinada com uma delas |
| **mTLS** | Nível mais alto de segurança (certificado por máquina, autenticação na camada de transporte) | Overhead operacional real: emissão, rotação e revogação de certificados por máquina, desproporcional ao tamanho da equipe/operação atual |

### Recomendação: **API Key** (um segredo de longa duração por worker/máquina, enviado num header próprio) **combinada com um perfil de "Service Account"** no backend — ou seja, essa identidade de worker só tem permissão para chamar os endpoints relacionados a jobs (buscar detalhes, pedir URL assinada, reportar progresso/resultado), nunca os de gestão de clubes, goleiros ou usuários. Isso já estava esboçado (com HMAC adicional sobre o payload) no `docs_ai_worker_spec.md` original — confirmo essa direção como correta e a mantenho como recomendação oficial. mTLS fica como um endurecimento futuro, se o parque de máquinas crescer para fora de uma rede confiável.

---

## 7. Escalabilidade (1 → 5 → 20 workers)

- **Quem controla a distribuição:** a própria fila (Redis Streams com consumer group). Não é necessário construir um "orquestrador" próprio — isso é exatamente o papel nativo de um consumer group.
- **Quem distribui o trabalho:** o broker da fila entrega cada mensagem a exatamente um consumidor conectado no grupo, automaticamente, sem lógica central adicional no backend.
- **Como evitar dois workers pegarem o mesmo vídeo:** é uma propriedade nativa do modelo de consumer group — uma mensagem só é entregue a um consumidor por vez; se esse consumidor não confirmar o processamento (por falha, crash ou timeout), a mensagem é reentregue a outro consumidor depois de um intervalo configurável. Isso evita tanto a duplicação simultânea quanto a perda de jobs por falha de um worker específico.
- **Escala horizontal:** adicionar um worker novo é simplesmente subir mais um processo apontando para a mesma fila e para a mesma API do backend — nenhuma mudança de código central é necessária para isso. Esse é o principal argumento para adotar, desde já (mesmo com um único worker hoje), um modelo de fila com semântica de consumer group, em vez de crescer organicamente a partir de *polling* e ter que reescrever essa parte depois.
- **Diferenciação por capacidade de hardware:** se, no futuro, existirem máquinas com GPUs diferentes (ex.: uma RX 7900 XTX e depois uma máquina mais modesta, ou até um fallback em CPU), a fila pode ser dividida por "perfil"/prioridade (ex.: uma fila para jobs que exigem GPU potente, outra para processamento mais leve), permitindo que cada worker só consuma da fila compatível com sua capacidade — sem precisar de lógica de negócio no backend para isso.
- **Múltiplos clubes:** o volume de vídeos de vários clubes compartilha o mesmo pool de workers — não há necessidade de isolar processamento por cliente/tenant (isso seria desperdício de capacidade). O isolamento que importa é o de **dados** (cada job carrega a referência de clube/goleiro/sessão, e o backend continua sendo o único responsável por aplicar as regras de acesso a esses dados).

---

## 8. Estrutura do projeto — mesmo repositório ou repositório separado?

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **Mesmo repositório** (monorepo) | Mais fácil manter o contrato de API sincronizado entre backend e worker (uma mudança que afeta os dois pode ir num só PR); um clone só; todo o histórico de decisão (este documento incluído) já vive num lugar só | O worker tem uma stack de dependências totalmente diferente (visão computacional, modelos, possivelmente CUDA/ROCm) — misturar isso com as dependências leves do backend infla o repositório e complica a configuração de ambiente; ciclos de release diferentes (o worker pode evoluir num ritmo bem diferente do backend) ficam artificialmente acoplados |
| **Repositório separado** | Isola completamente o ciclo de vida, dependências e deploy do worker; reforça, também no nível organizacional, a premissa de que o worker é "totalmente independente"; mais fácil de restringir acesso no futuro (se alguém só mexer em IA, não precisa nem ver o código do backend/frontend) | Contratos de API que mudam nos dois lados precisam ser coordenados entre dois PRs/repositórios; configuração inicial duplicada (lint, README, etc.) |

### Recomendação: **repositório separado** (ex.: `goalkeeper-ai-worker`), na mesma organização/conta Git do projeto atual.

**⚠️ Mudança proposta em relação ao que já está documentado:** `docs_folder_structure.md` sugere manter `ai_worker/` como uma pasta dentro do mesmo monorepo (com uma nota reconhecendo que "manter como repositório separado também é uma opção válida"). Given que você definiu explicitamente que a IA "será um serviço totalmente independente" e rodará numa máquina completamente separada, recomendo formalizar isso também como repositório separado — evita a tentação natural de "já que está tudo no mesmo lugar, deixa eu só importar direto" (seja um módulo Python, seja acesso a arquivo/banco), e mantém a pasta `ai_worker/` do repositório atual livre para virar, no máximo, um `README.md` curto apontando para o novo repositório.

---

## 9. Pipeline interno do Worker (sem código, apenas etapas)

1. **Download**: recebe o job da fila, solicita e usa a URL assinada de leitura, baixa o vídeo para um armazenamento temporário local.
2. **Validação/Pré-processamento**: confirma integridade do arquivo, extrai metadados (duração, resolução, fps, orientação), normaliza o que for necessário (ex.: correção de rotação, reamostragem de fps para um padrão de processamento).
3. **Detecção**: localiza o goleiro (e, se aplicável, a bola e outros jogadores de contexto) nos frames analisados.
4. **Tracking (rastreamento)**: mantém a identidade do goleiro ao longo do tempo, associando detecções entre frames e lidando com oclusões curtas.
5. **Extração de métricas**: calcula posição, deslocamento, velocidade, ângulos e outras métricas a partir das trajetórias rastreadas.
6. **Classificação de eventos**: identifica janelas de tempo que correspondem a eventos técnicos relevantes (defesas, saídas, reposições, quedas, etc.), a partir das métricas extraídas.
7. **Geração de artefatos**: recorta thumbnails e pequenos clipes correspondentes a cada evento detectado, e opcionalmente um mapa de calor de posicionamento.
8. **Montagem do resultado estruturado**: organiza tudo isso num formato estruturado (lista de eventos com tipo, instante, confiança, e referências aos artefatos gerados).
9. **Upload dos artefatos**: envia os artefatos gerados para o R2, usando a URL assinada de escrita.
10. **Envio do resultado ao Backend**: reporta o resultado estruturado final via API, encerrando o job como concluído (ou como falho, com uma mensagem de erro clara, se qualquer etapa anterior não puder ser concluída).

Cada etapa deve reportar progresso incremental ao Backend (não só 0% no início e 100% no fim) — isso alimenta diretamente o mecanismo de status detalhado da seção 13.

---

## 10. Modelos de IA — como trocar sem afetar o resto do sistema

Princípio central: cada estágio do pipeline (detecção, tracking, classificação de eventos) deve ser tratado como um **componente plugável**, com uma entrada e uma saída padronizadas — independente de qual algoritmo/modelo está por trás. Por exemplo: um "detector" sempre recebe um frame e devolve uma lista de objetos localizados com classe e confiança, não importa se por trás disso está um modelo ou outro; um "classificador de eventos" sempre recebe uma janela de métricas e devolve um tipo de evento com confiança, não importa qual técnica foi usada para chegar nesse resultado.

Práticas que sustentam isso, ao longo do tempo:

- **Modelos como artefato externo, não como parte do código**: os arquivos de modelo (pesos treinados) não devem viver dentro do repositório de código — ficam num local próprio de armazenamento (poderia inclusive ser um prefixo dedicado no próprio Cloudflare R2), carregados em tempo de execução conforme configuração.
- **Escolha de modelo via configuração, não via redeploy de código**: qual modelo usar em cada estágio deve ser algo definido em configuração (ex.: qual arquivo/versão de modelo carregar), não uma decisão fixa embutida no pipeline. Trocar de modelo deve significar trocar uma configuração, não reescrever o orquestrador do pipeline.
- **Rastreabilidade de versão**: cada resultado gerado deve registrar qual versão de modelo foi usada para produzi-lo — importante para comparar desempenho entre versões de modelo ao longo do tempo, e para investigar regressões.
- **Convivência de múltiplos modelos**: a arquitetura deve permitir que jobs diferentes usem modelos diferentes (por exemplo, um modelo em teste rodando só para uma parte dos vídeos, antes de virar o padrão para todos) — isso é possível se a escolha do modelo for um parâmetro por job/execução, e não uma constante fixa do worker.

Essa separação evita que a equipe de ML precise reescrever o "orquestrador" do pipeline toda vez que quiser evoluir um modelo — só o componente plugável correspondente muda.

---

## 11. Cloudflare R2 — acesso seguro do Worker

Regra central: **o worker nunca tem as credenciais mestras do R2** (as mesmas `R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY` que hoje só existem no backend). Todo acesso do worker ao R2 acontece através de **URLs assinadas (presigned URLs)** de curta duração, geradas sob demanda pelo backend — que já tem, hoje, a capacidade de gerar esse tipo de URL.

- **Leitura**: ao pegar um job, o worker pede ao backend uma URL assinada de leitura para aquele vídeo específico. O backend gera essa URL (validade curta, ex.: da ordem de uma hora) e a devolve. O worker baixa diretamente do R2 usando essa URL — nunca vê a credencial mestra.
- **Escrita (artefatos)**: mesmo princípio — o worker pede uma URL assinada de escrita, restrita ao prefixo de artefatos daquele job específico, sobe os arquivos, e avisa o backend que terminou.
- **Escopo mínimo**: cada URL assinada deve valer apenas para o objeto/prefixo daquele job específico, nunca uma credencial de acesso amplo ao bucket inteiro, e deve expirar rapidamente.
- **Por que isso importa especialmente aqui**: a máquina de IA está, por definição do próprio projeto, **fora** do ambiente controlado do SaaS — é fisicamente uma máquina separada, potencialmente numa rede diferente. Ela é, portanto, o elo mais exposto do sistema. Se essa máquina for comprometida, o pior cenário possível deve ser o vazamento de uma URL de curta duração para um objeto específico — nunca a credencial mestra de todo o bucket.

---

## 12. Banco de dados — o Worker acessa direto ou só via API?

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **Acesso direto ao PostgreSQL** | Elimina uma chamada HTTP a mais; potencialmente mais rápido | Exigiria expor a porta do banco para uma máquina fora do ambiente controlado; se essa máquina for comprometida, o acesso não fica restrito a jobs de vídeo — fica aberto a **todos** os dados do sistema; acopla o worker ao schema exato do banco (uma migration no backend pode quebrar o worker silenciosamente); múltiplos workers escrevendo direto no banco, sem passar pelas validações/regras de negócio do backend, é risco real de inconsistência de dados |
| **Somente via API** | Mantém uma única porta de entrada controlada, já autenticada e (no futuro) auditada; o schema do banco pode evoluir livremente sem quebrar o worker, desde que o contrato da API se mantenha estável; reforça exatamente a premissa definida por você — o worker "totalmente independente", o backend responsável pelo banco | Uma chamada HTTP a mais por atualização — overhead desprezível diante do tempo que o próprio processamento de vídeo já consome |

### Recomendação: **somente via API**, sem exceção, em nenhuma fase. Esta é, na minha avaliação, **a decisão mais importante de todo este documento** — é o que de fato torna o worker desacoplado, e não apenas "rodando numa máquina diferente, mas ainda enxergando o mesmo banco por dentro".

---

## 13. Atualização de progresso — como o Frontend fica sabendo

Estados a comunicar: pendente → baixando → processando → gerando relatório → concluído / falhou.

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **Polling do Frontend** (como já funciona hoje) | Já implementado, simples, funciona em qualquer rede/navegador | Atraso proporcional ao intervalo de consulta; tráfego desnecessário quando nada mudou |
| **WebSocket** | Bidirecional, atualização quase instantânea | A necessidade aqui é unidirecional (servidor avisa o cliente) — WebSocket resolve mais do que o problema pede, com mais complexidade de conexão (reconexão, múltiplas abas) |
| **Server-Sent Events (SSE)** | Unidirecional (exatamente o que este caso precisa), atualização quase instantânea, roda sobre HTTP comum — bem mais simples de operar que WebSocket | Não serve para comunicação bidirecional (mas isso não é uma necessidade real aqui) |

### Recomendação: **manter o polling atual para o momento presente** (já funciona, baixo esforço, volume ainda pequeno) e **evoluir para SSE** quando o volume de vídeos/usuários simultâneos justificar a atualização em tempo real. Não recomendo WebSocket — entregaria o mesmo resultado prático que SSE, com mais complexidade operacional para gerenciar.

---

## 14. Monitoramento

O que monitorar: workers online, GPU (utilização, temperatura, VRAM), tamanho/tempo de espera da fila, tempo médio de processamento, taxa de falhas.

Abordagem (arquitetura, não implementação):

- **Métricas dos workers**: cada worker expõe/emite métricas periodicamente para um sistema central de coleta. **Prometheus** é o padrão de mercado para isso — pode ser configurado no modo *pull* (Prometheus busca as métricas de um endpoint do worker) ou *push* via um componente intermediário (mais adequado aqui, já que os workers estão fisicamente fora da rede do servidor principal e podem não estar sempre "alcançáveis" a partir do backend).
- **Métricas de GPU**: coletadas pelas próprias ferramentas do fabricante (para AMD, o equivalente ao `rocm-smi`) e expostas junto das demais métricas do worker — temperatura, uso de VRAM, utilização de processamento.
- **Métricas da fila**: o próprio broker (Redis) já expõe nativamente tamanho de fila, consumidores conectados e mensagens pendentes — reaproveitar isso em vez de reconstruir manualmente.
- **Visualização**: **Grafana** consumindo o Prometheus, dando um painel único com workers online, GPU, fila, tempo médio de processamento e falhas — sem precisar construir telas de monitoramento dentro do próprio Flutter.
- **Alertas**: Grafana/Alertmanager para avisar quando um worker cair, a fila crescer além do esperado, ou a taxa de falha subir — podendo, inclusive, notificar via **Telegram** (canal que já está nos planos do produto).
- **"Heartbeat" de worker vivo**: cada worker deve informar periodicamente ao sistema (mesmo antes de uma stack completa de Prometheus/Grafana existir) que está ativo — permite mostrar "workers online" de forma simples desde o início, sem depender de toda a stack de observabilidade estar pronta.

---

## 15. Roadmap de implementação (visão geral, sem detalhar tarefas técnicas)

| Sprint | Objetivo |
|---|---|
| **A — Fundação de mensageria** | Subir o broker (Redis Streams), Backend passa a publicar uma mensagem na fila no momento do upload — ainda sem nenhum worker consumindo |
| **B — Identidade e endpoints do Worker** | Criar a identidade de "worker" (API Key + escopo restrito) no Backend; endpoints dedicados para buscar detalhes do job, solicitar URLs assinadas de leitura/escrita, e reportar progresso/resultado |
| **C — Worker esqueleto** | Repositório novo, worker mínimo: consome da fila, baixa o vídeo, extrai só metadados básicos, marca o job como concluído — sem nenhuma IA ainda. Objetivo: provar toda a esteira ponta a ponta |
| **D — Primeira detecção real** | Integrar um detector genérico pré-treinado (pessoa/bola), gerar um resultado simples por frame amostrado — ainda sem classificar eventos |
| **E — Tracking e eventos** | Adicionar rastreamento entre frames e uma primeira versão (mesmo que simples) de classificação de eventos técnicos |
| **F — Artefatos e relatório** | Geração de thumbnails/clipes, upload ao R2, montagem do relatório estruturado, conectar à tela de Análises/Relatórios do Frontend |
| **G — Observabilidade** | Prometheus + Grafana, métricas de GPU, heartbeat de workers, alertas via Telegram |
| **H — Escala horizontal** | Validar múltiplos workers simultâneos, filas por perfil de hardware, testes de carga |
| **I — Modelo especializado em goleiro** | Com o pipeline todo validado, iniciar a construção de um dataset rotulado próprio e um modelo especializado — hoje ainda não existe nenhuma base de dados para isso (`datasets/` está vazio) |

---

## Resumo das decisões recomendadas

| Decisão | Recomendação |
|---|---|
| Fila de processamento | Redis (Streams + consumer group) |
| Comunicação Worker ↔ Backend | REST (mesmo padrão já usado pelo Frontend) |
| Comunicação Backend → Frontend (progresso) | Polling hoje, evoluir para SSE quando necessário |
| Autenticação do Worker | API Key + escopo de "service account" restrito a endpoints de job |
| Acesso ao banco de dados | Somente via API — nunca acesso direto ao PostgreSQL |
| Acesso ao Cloudflare R2 | Somente via URLs assinadas de curta duração, geradas pelo Backend sob demanda |
| Estrutura de repositório | Repositório separado (`goalkeeper-ai-worker`) |
| Monitoramento | Prometheus + Grafana, com heartbeat simples de workers desde o início |

---

*Documento de arquitetura. Nenhum arquivo de código, Dockerfile ou configuração foi criado ou alterado. Aguardando sua aprovação (ou ajustes) antes de qualquer implementação.*
