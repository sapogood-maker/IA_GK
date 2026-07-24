"""Configuracao centralizada do Worker.

Nenhum valor sensivel e hardcoded: tudo e lido do arquivo .env (ou do
ambiente do processo). Nao compartilha nenhum campo, arquivo ou schema
com a configuracao do backend (Boundary Enforcement - ver
AI_WORKER_CONSTITUTION.md).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from worker.core.exceptions import ConfigurationError


class WorkerSettings(BaseSettings):
    """Configuracao de runtime de uma instancia do Worker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WORKER_",
        extra="ignore",
        # `model_path` (Sprint W8) colide com o namespace protegido "model_"
        # do proprio pydantic (usado por model_config/model_fields/etc.) -
        # falso positivo, nao ha conflito real de atributo.
        protected_namespaces=(),
    )

    env: str = Field(
        default="development",
        description="Ambiente de execucao (development|production).",
    )
    instance_id: str = Field(
        description="Identificador unico desta instancia de Worker (Worker Instance).",
    )
    log_level: str = Field(
        default="INFO",
        description="Nivel de log (DEBUG|INFO|WARNING|ERROR).",
    )
    log_dir: str = Field(
        default="",
        description="Deployment v1.0 (Docker): diretorio para logs em "
        "arquivo (rotacionado), montavel como volume (`/app/logs`). "
        "Vazio (padrao) = so stdout/stderr, mesmo comportamento de "
        "antes desta sprint - nenhum teste existente foi afetado.",
    )

    # --- Redis (fila de processamento - Sprint W2) ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL do Redis - deve ser o mesmo Redis usado pelo backend.",
    )
    consumer_group: str = Field(
        default="goalkeeper_ai_worker",
        description="Nome do consumer group do stream `processing_jobs`. "
        "Fixo por convencao entre instancias - todas devem usar o mesmo "
        "grupo para balancear carga corretamente.",
    )
    startup_wait_timeout_seconds: float = Field(
        default=60.0,
        description="Deployment v1.0 (Docker): tempo maximo, em segundos, "
        "que `worker.wait_for_redis` aguarda o Redis ficar alcancavel antes "
        "de desistir (usado pelo entrypoint.sh do container, nunca em "
        "runtime pelo Orchestrator - reconexao apos o startup e "
        "responsabilidade do connection pool do redis.asyncio + do "
        "restart:unless-stopped do Docker).",
    )

    # --- Worker API do backend (Sprint W2) ---
    backend_api_url: str = Field(
        description="URL base da Worker API do backend (ex.: http://localhost:8001).",
    )
    api_key: str = Field(
        description="Segredo enviado no header X-Worker-Api-Key. Mesmo VALOR "
        "configurado como WORKER_API_KEY no backend - cada lado mantem seu "
        "proprio arquivo de configuracao (Boundary Enforcement).",
    )

    # --- Lock distribuido por video (Sprint W2, ADR-001/003) ---
    lock_ttl_seconds: int = Field(
        default=300,
        description="TTL do lock distribuido por video, em segundos.",
    )

    # --- Identificacao de protocolo (Sprint W2) ---
    protocol_version: str = Field(
        default="1.0",
        description="Versao do contrato REST falado com o backend (enviada "
        "no header X-Worker-Version). Distinta de worker.__version__, que e "
        "a versao do software do Worker.",
    )

    # --- Motor de inferencia ativo (Sprint W4/W6) ---
    inference_engine: str = Field(
        default="basic_vision",
        description="Nome do motor de inferencia ativo, resolvido pelo "
        "Registry (worker.inference.registry). 'basic_vision' e o motor "
        "padrao desde a W6; 'fake' continua registrado, usado nos testes. "
        "Futuramente 'yolo'/'multimodel' sem alterar o Pipeline.",
    )

    # --- Pre-processamento de frame do BasicVisionEngine (Sprint W6) ---
    frame_skip: int = Field(
        default=0,
        description="Quantos frames pular entre cada frame processado "
        "(0 = processa todos os frames).",
    )
    enable_resize: bool = Field(
        default=False,
        description="Se True, redimensiona cada frame para target_width/target_height.",
    )
    target_width: int = Field(
        default=0,
        description="Largura alvo do resize, em pixels. So usado se enable_resize=True.",
    )
    target_height: int = Field(
        default=0,
        description="Altura alvo do resize, em pixels. So usado se enable_resize=True.",
    )
    enable_roi: bool = Field(
        default=False,
        description="Se True, recorta cada frame para a Region of Interest "
        "definida por roi_x/roi_y/roi_width/roi_height.",
    )
    roi_x: int = Field(default=0, description="Coordenada X (canto superior esquerdo) da ROI.")
    roi_y: int = Field(default=0, description="Coordenada Y (canto superior esquerdo) da ROI.")
    roi_width: int = Field(default=0, description="Largura da ROI, em pixels.")
    roi_height: int = Field(default=0, description="Altura da ROI, em pixels.")

    # --- Habilitacao de Processors da pipeline interna (Sprint W7) ---
    # enable_resize/enable_roi (acima) ja controlam ResizeProcessor/ROIProcessor;
    # estes dois cobrem os dois Processors que nao tinham flag propria ate a W7.
    enable_color_processor: bool = Field(
        default=True,
        description="Se True, o ColorProcessor (conversao BGR->RGB) entra na pipeline.",
    )
    enable_statistics_processor: bool = Field(
        default=True,
        description="Se True, o StatisticsProcessor (so mede, nao transforma) entra na pipeline.",
    )

    # --- API de Deteccao (Sprint W8) ---
    detector: str = Field(
        default="",
        description="Nome do Detector ativo, resolvido por worker.inference."
        "detectors.factory.create_detector. Vazio (padrao) = YOLOProcessor "
        "desabilitado, sem tentar carregar nenhum modelo. 'yolo' e o unico "
        "Detector registrado hoje; futuramente 'rtdetr'/'groundingdino'/"
        "'owlv2' sem alterar YOLOProcessor, PipelineProcessor ou o motor.",
    )
    model_path: str = Field(
        default="weights/yolo11n.pt",
        description="Caminho (ou nome, para auto-download da Ultralytics) "
        "dos pesos do modelo usado pelo Detector ativo. O padrao aponta "
        "para weights/ (nao versionado no git - ver .gitignore).",
    )
    confidence_threshold: float = Field(
        default=0.25,
        description="Confianca minima para uma deteccao ser mantida.",
    )
    iou_threshold: float = Field(
        default=0.45,
        description="Limiar de IoU usado no NMS (Non-Maximum Suppression) do Detector.",
    )

    # --- API de Tracking (Sprint W9) ---
    tracker: str = Field(
        default="",
        description="Nome do Tracker ativo, resolvido por worker.inference."
        "trackers.factory.create_tracker. Vazio (padrao) = TrackingProcessor "
        "desabilitado. 'bytetrack' e o unico Tracker registrado hoje; "
        "futuramente 'botsort'/'deepsort'/'strongsort'/'ocsort' sem alterar "
        "TrackingProcessor, PipelineProcessor ou o motor.",
    )
    tracking_enabled: bool = Field(
        default=False,
        description="Liga/desliga o TrackingProcessor. Precisa estar True E "
        "'tracker' precisa apontar para um Tracker registrado para o "
        "tracking realmente rodar - dois interruptores independentes, "
        "de proposito (permite configurar o Tracker sem ainda habilita-lo).",
    )
    track_min_confidence: float = Field(
        default=0.25,
        description="Confianca minima para iniciar uma nova trilha - "
        "mapeada para os limiares internos do Tracker ativo.",
    )
    track_max_age: int = Field(
        default=30,
        description="Quantos frames uma trilha perdida pode ficar sem "
        "deteccao correspondente antes de ser removida.",
    )
    track_min_hits: int = Field(
        default=1,
        description="Quantas deteccoes consecutivas uma trilha precisa "
        "acumular antes de aparecer no artefato (1 = nenhuma supressao).",
    )

    # --- API de Eventos de Cena (Sprint W10) ---
    scene_analyzer: str = Field(
        default="",
        description="Nome do SceneAnalyzer ativo, resolvido por worker.inference."
        "events.factory.create_analyzer. Vazio (padrao) = SceneAnalysisProcessor "
        "desabilitado. 'basic' e o unico SceneAnalyzer registrado hoje; "
        "futuras analises especificas (GoalkeeperAnalyzer, BallAnalyzer, "
        "DiveAnalyzer, SaveAnalyzer, GoalAnalyzer) consomem SceneEvents, "
        "sem alterar SceneAnalysisProcessor, PipelineProcessor ou o motor.",
    )
    scene_analysis_enabled: bool = Field(
        default=False,
        description="Liga/desliga o SceneAnalysisProcessor. Precisa estar "
        "True E 'scene_analyzer' precisa apontar para um SceneAnalyzer "
        "registrado - dois interruptores independentes, mesmo padrao de "
        "tracking_enabled/tracker (Sprint W9).",
    )
    scene_motion_threshold_px: float = Field(
        default=5.0,
        description="Deslocamento minimo (em pixels) do centro da caixa "
        "delimitadora entre frames para considerar uma trilha em movimento "
        "(abaixo disso, e considerada parada).",
    )
    scene_occlusion_iou_threshold: float = Field(
        default=0.3,
        description="Limiar de IoU entre duas trilhas no MESMO frame para "
        "considerar que ha oclusao entre elas.",
    )

    # --- World Model (Sprint W11) ---
    world_model: str = Field(
        default="",
        description="Nome do WorldModel ativo, resolvido por worker.inference."
        "world.factory.create_world_model. Vazio (padrao) = WorldModelProcessor "
        "desabilitado. 'basic' e o unico WorldModel registrado hoje - a ultima "
        "camada generica da arquitetura; futuros analisadores especificos de "
        "futebol (W12+) consomem WorldState, sem conhecer Detector/Tracker/"
        "SceneAnalyzer diretamente.",
    )
    world_model_enabled: bool = Field(
        default=False,
        description="Liga/desliga o WorldModelProcessor. Precisa estar True E "
        "'world_model' precisa apontar para um WorldModel registrado - dois "
        "interruptores independentes, mesmo padrao de tracking_enabled/tracker "
        "(Sprint W9) e scene_analysis_enabled/scene_analyzer (Sprint W10).",
    )
    world_history_size: int = Field(
        default=30,
        description="Quantos SceneEvents recentes o WorldModel mantem em "
        "memoria (WorldState.recent_events) - nunca cresce alem disso.",
    )
    world_max_trajectory: int = Field(
        default=30,
        description="Quantos pontos recentes de posicao cada ObjectState.trajectory "
        "mantem - nunca cresce alem disso.",
    )
    world_max_objects: int = Field(
        default=200,
        description="Quantos objetos (ativos + perdidos) o WorldModel mantem "
        "em memoria no maximo - ao exceder, remove os objetos perdidos mais "
        "antigos primeiro (nunca remove um objeto ativo). <=0 desativa o limite.",
    )

    # --- Football Domain Model (Sprint W12) ---
    football_domain_enabled: bool = Field(
        default=False,
        description="Liga/desliga o FootballDomainProcessor. Diferente de "
        "Detector/Tracker/SceneAnalyzer/WorldModel, nao ha um segundo "
        "interruptor de 'qual implementacao' - FootballWorldBuilder e a "
        "unica implementacao do dominio, nao uma familia de Plugin "
        "substituivel (sem Registry/factory nesta camada, de proposito).",
    )

    # --- Analyzer API (Sprint W13) ---
    analyzers: str = Field(
        default="",
        description="Nomes dos Analyzers ativos, separados por virgula "
        "(ex.: 'goalkeeper_presence'), resolvidos por worker.analyzers."
        "factory.create_analyzer. Vazio (padrao) = AnalyzerProcessor "
        "desabilitado. Diferente de Detector/Tracker/SceneAnalyzer/"
        "WorldModel (uma unica implementacao ativa por vez), varios "
        "Analyzers podem rodar simultaneamente - cada um responde uma "
        "pergunta independente sobre o mesmo FootballWorld; por isso um "
        "unico campo de lista basta como interruptor (vazio = "
        "desabilitado), sem precisar de um segundo '_enabled' separado.",
    )

    @property
    def analyzer_names(self) -> list[str]:
        """`analyzers` (string bruta) recortada em nomes individuais,
        ignorando espacos e entradas vazias - usado por AnalyzerProcessor
        para resolver, via factory, cada Analyzer ativo."""
        return [name.strip() for name in self.analyzers.split(",") if name.strip()]

    # --- Shot Analyzer (Sprint W19) ---
    shot_min_speed: float = Field(
        default=20.0,
        description="Velocidade minima observada (pixels/frame - ver "
        "Motion.speed, Secao 6.1) para considerar o movimento da bola "
        "compativel com um chute. Placeholder nao calibrado a nenhum "
        "video real (mesma limitacao de escala do Risco 20/22/27) - "
        "ajustar por deployment conforme resolucao/distancia de camera.",
    )
    shot_max_angle_deviation_degrees: float = Field(
        default=25.0,
        description="Desvio angular maximo (graus) entre a direcao "
        "observada do movimento da bola e a direcao da bola ate o centro "
        "do gol, para considerar o movimento 'em direcao ao gol'.",
    )
    shot_min_consecutive_frames: int = Field(
        default=2,
        description="Quantos frames CONSECUTIVOS o movimento precisa "
        "satisfazer velocidade minima + direcao consistente antes de "
        "shot_detected se tornar True - exige 'movimento continuo', nao "
        "um pico isolado de velocidade num unico frame.",
    )

    # --- Ball Trajectory Analyzer (Sprint W20) ---
    trajectory_direction_change_threshold_degrees: float = Field(
        default=30.0,
        description="Desvio angular minimo (graus) entre dois segmentos "
        "consecutivos da trajetoria observada da bola para contar como "
        "uma 'mudanca de direcao' (direction_changes) - abaixo disso, e "
        "considerado ruido normal de deteccao, nao uma mudanca real.",
    )

    # --- Goalkeeper Decision Analyzer (Sprint W22) ---
    goalkeeper_shift_min_speed: float = Field(
        default=3.0,
        description="Velocidade minima observada do PROPRIO goleiro "
        "(pixels/frame) para considerar que ele se moveu de proposito "
        "(reposicionamento) - abaixo disso, e tratado como ruido normal "
        "de deteccao/tracking e classificado como STAY_ON_LINE.",
    )
    goalkeeper_dive_min_speed: float = Field(
        default=15.0,
        description="Velocidade minima observada do goleiro (pixels/frame) "
        "para que um movimento lateral durante um chute detectado conte "
        "como um mergulho (DIVE_LEFT/DIVE_RIGHT) em vez de apenas "
        "'preparando' (PREPARE_DIVE) - placeholder nao calibrado a nenhum "
        "video real, mesma limitacao de escala do Risco 20/22/27/34.",
    )

    # --- Goalkeeper Decision Evaluation Analyzer (Sprint W23) ---
    goalkeeper_evaluation_min_lateral_signal: float = Field(
        default=2.0,
        description="Magnitude minima (pixels/frame) da componente lateral "
        "de movimento (goleiro OU bola) para considerar a direcao um sinal "
        "claro o suficiente para a regra 'dive_direction_matches_ball_"
        "direction' - abaixo disso, a regra e marcada como NAO APLICAVEL "
        "(nunca forca um veredito sobre ruido de deteccao/tracking).",
    )

    # --- Play Outcome Analyzer (Sprint W24) ---
    outcome_post_proximity_px: float = Field(
        default=15.0,
        description="Distancia maxima (pixels) entre a ultima posicao "
        "conhecida da bola e um poste (GoalGeometryResult.left_post/"
        "right_post) para classificar o resultado como POST - placeholder "
        "nao calibrado a nenhum video real, mesma limitacao de escala do "
        "Risco 20/22/27/34.",
    )
    outcome_save_proximity_px: float = Field(
        default=30.0,
        description="Distancia maxima (pixels) entre a ultima posicao "
        "conhecida da bola e a ultima posicao conhecida do goleiro, apos "
        "um chute detectado, para classificar o resultado como SAVE - "
        "mesma limitacao de escala do Risco 20/22/27/34.",
    )


@lru_cache
def get_settings() -> WorkerSettings:
    """Carrega (e armazena em cache) a configuracao do Worker a partir do .env."""
    try:
        return WorkerSettings()
    except Exception as exc:
        raise ConfigurationError(f"Configuracao invalida ou incompleta: {exc}") from exc
