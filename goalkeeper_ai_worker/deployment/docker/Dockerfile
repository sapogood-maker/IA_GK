# syntax=docker/dockerfile:1
#
# Goalkeeper AI Worker - imagem Docker (Deployment v1.0)
#
# Build context = raiz do repositorio do Worker (goalkeeper_ai_worker/),
# NAO este diretorio - o Dockerfile precisa copiar worker/, requirements.txt
# e pyproject.toml, que ficam acima de deployment/docker/. Ver
# docker-compose.yml (build.context: ../..) e DEPLOYMENT_V1_REPORT.md.
#
# Multi-stage:
#   1. builder - instala dependencias Python (incluindo torch/torchvision
#      CPU-ONLY do indice oficial do PyTorch, nunca o wheel CUDA padrao
#      do PyPI, dezenas de vezes maior e inutil sem runtime NVIDIA) num
#      virtualenv isolado.
#   2. runtime - so copia o virtualenv pronto + o codigo da aplicacao;
#      roda como usuario nao-root; nunca contem credenciais (toda
#      configuracao vem de variaveis de ambiente/.env, nunca desta imagem).
#
# CPU hoje, GPU amanha (mesma imagem, sem mudanca de codigo): o Worker em
# si nunca decide CPU/GPU - isso e responsabilidade de qual PyTorch esta
# instalado (Registry/factory de Detectors, Secao 6.1 da Constituicao, ja
# resolve YOLODetector sem saber se torch e CPU ou CUDA). Migrar para GPU
# em Ubuntu + NVIDIA Container Toolkit e documentado no
# DEPLOYMENT_V1_REPORT.md - troca so a base image e o pacote torch, nunca
# o codigo do Worker.

ARG PYTHON_VERSION=3.11-slim

# ---------------------------------------------------------------------
# Stage 1: builder
# ---------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder

WORKDIR /build

# Dependencias de sistema so para compilar wheels nativas (numpy/opencv) -
# nunca vao para a imagem final.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip

# torch/torchvision CPU-only, versoes identicas as ja validadas no
# ambiente de teste do projeto (ver DEPLOYMENT_V1_REPORT.md) - instaladas
# ANTES de requirements.txt para que a resolucao de dependencias do
# ultralytics (que exige torch>=1.8.0/torchvision>=0.9.0) encontre esta
# versao ja satisfeita e nunca puxe o wheel CUDA do PyPI.
RUN pip install --no-cache-dir \
        torch==2.13.0+cpu torchvision==0.28.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Achado desta sprint: `ultralytics` (8.4.104) declara `opencv-python`
# (variante COM GUI/X11) como dependencia obrigatoria propria, mesmo com
# `opencv-python-headless` ja satisfeito por requirements.txt - as duas
# distribuicoes instalam o MESMO pacote `cv2/`, entao a que for instalada
# por ultimo sobrescreve fisicamente os arquivos da outra (nao e um erro
# de resolucao do pip, e um conflito real e conhecido do ecossistema
# ultralytics/opencv). Sem este passo, `import cv2` falha na imagem final
# com `ImportError: libxcb.so.1` (dependencia X11 que a imagem
# deliberadamente nao instala, ver Constituicao/Secao 6.1 - W5 escolheu
# opencv-python-headless exatamente para NAO depender de X11/GUI).
# --force-reinstall --no-deps garante que os arquivos de opencv-python-headless
# fiquem por cima, deterministicamente, sem re-resolver nenhuma outra
# dependencia (numpy etc. ja satisfeitas acima).
RUN pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.10.0.84

# ---------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

LABEL org.opencontainers.image.title="goalkeeper-ai-worker" \
      org.opencontainers.image.description="Servico de visao computacional do Goalkeeper AI (independente do backend_fastapi)"

# Bibliotecas de sistema minimas exigidas em runtime por opencv-python-headless/
# torch - NENHUMA dependencia de GUI/X11 (a variante "headless" do OpenCV
# existe exatamente para isso).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Usuario nao-root dedicado - nenhum processo do Worker roda como root
# dentro do container.
RUN groupadd --gid 1000 worker \
    && useradd --uid 1000 --gid worker --create-home --shell /usr/sbin/nologin worker

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Nenhum arquivo de configuracao/segredo e copiado para a imagem - so
# codigo. .env/.env.* sao ignorados via .dockerignore; toda configuracao
# real chega via `env_file`/variaveis de ambiente do docker-compose em
# runtime (nunca embutida na imagem).
COPY worker/ ./worker/
COPY pyproject.toml ./

COPY deployment/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

# Diretorios montaveis como volume: logs (WORKER_LOG_DIR) e cache/modelos
# (WORKER_MODEL_PATH, pesos do YOLO baixados automaticamente pela
# Ultralytics no primeiro uso e reaproveitados nos proximos restarts via
# o volume). Criados e com dono correto ANTES de trocar para o usuario
# nao-root - senao o volume montaria com dono root e o processo nao-root
# nao conseguiria escrever.
RUN mkdir -p /app/logs /app/weights \
    && chown -R worker:worker /app

USER worker

VOLUME ["/app/logs", "/app/weights"]

# Health Check do Worker (worker/healthcheck.py) - verifica que as duas
# dependencias externas criticas (Redis, Worker API do backend) estao
# alcancaveis. start-period generoso porque o entrypoint ja aguarda o
# Redis antes de iniciar (wait_for_redis.py), mas o WorkerOrchestrator
# ainda carrega o motor de inferencia (e, se for a primeira execucao,
# baixa os pesos do YOLO no volume /app/weights) antes do primeiro ciclo
# do loop de consumo comecar.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -m worker.healthcheck || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "-m", "worker.main"]
