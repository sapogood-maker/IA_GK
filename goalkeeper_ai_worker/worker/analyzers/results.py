"""Tipos de resultado da Analyzer API - nunca listas de dicionários
soltos. `AnalysisResult` é a base comum de todo resultado de Analyzer;
cada Analyzer concreto declara sua PRÓPRIA subclasse (ex.:
`GoalkeeperPresenceResult`) - nenhuma união genérica, para que
analisadores futuros e consumidores do artefato saibam exatamente que
perguntas cada resultado responde."""
from __future__ import annotations

from dataclasses import dataclass

from worker.analyzers.types import (
    AnalyzerName,
    AnalyzerVersion,
    GoalkeeperCoaching,
    GoalkeeperDecision,
    GoalkeeperDecisionEvaluation,
    GoalkeeperPerformanceEvaluation,
    GoalZone,
    PlayOutcome,
    PlaySituation,
)
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import EntityId


@dataclass(frozen=True)
class AnalyzerMetadata:
    """Metadados de UMA execução de UM Analyzer - mesmo papel que
    `InferenceMetadata` (Seção 8) tem para o motor: identifica quem
    produziu o resultado e quanto tempo levou, sem carregar nenhum dado
    de análise em si."""

    analyzer_name: AnalyzerName
    analyzer_version: AnalyzerVersion
    processing_time_ms: float

    def to_dict(self) -> dict:
        return {
            "analyzer_name": self.analyzer_name,
            "analyzer_version": self.analyzer_version,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class AnalysisResult:
    """Base de todo resultado de Analyzer - `frame_index` (a que frame do
    FootballWorld este resultado se refere) + `metadata` (quem produziu).
    Subclasses adicionam os campos específicos da pergunta que respondem."""

    frame_index: int
    metadata: AnalyzerMetadata

    def to_dict(self) -> dict:
        return {"frame_index": self.frame_index, **self.metadata.to_dict()}


@dataclass
class GoalkeeperPresenceResult(AnalysisResult):
    """Resposta às perguntas factuais sobre a presença do goleiro -
    nenhuma avaliação de qualidade, nenhuma heurística. Quando existem
    vários candidatos rotulados `goalkeeper` no mesmo frame (o Football
    Domain Model, W12, nunca desambiguia isso), esta sprint escolhe
    deterministicamente o PRIMEIRO da lista `FootballWorld.goalkeepers`
    (ordem herdada de `WorldState.active_objects`) - não é uma heurística
    de qual É "o goleiro de verdade", é só a regra determinística mais
    simples possível para reportar UM track_id quando é pedido."""

    exists: bool
    visible: bool
    goalkeeper_count: int
    track_id: EntityId | None
    age: int | None
    current_position: Coordinate | None
    current_bbox: Region | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "exists": self.exists,
            "visible": self.visible,
            "goalkeeper_count": self.goalkeeper_count,
            "track_id": self.track_id,
            "age": self.age,
            "current_position": (
                {"x": self.current_position.x, "y": self.current_position.y}
                if self.current_position is not None
                else None
            ),
            "current_bbox": self.current_bbox.to_dict() if self.current_bbox is not None else None,
        })
        return payload


@dataclass
class GoalGeometryResult(AnalysisResult):
    """Resposta às perguntas puramente geométricas sobre o gol - nenhuma
    avaliação de goleiro, defesa, chute, mergulho ou reação. Quando
    `FootballWorld.goals` tem mais de um candidato (o Football Domain
    Model, W12, sempre cria os dois gols do campo via
    `Goal.default_pair()`), esta sprint escolhe deterministicamente o
    PRIMEIRO da lista - mesma regra de ordem já usada por
    `GoalkeeperPresenceResult` (W13) para múltiplos candidatos, não uma
    heurística sobre qual gol é "o relevante".

    `confidence` aqui não é uma probabilidade de detecção (o domínio não
    carrega nenhum sinal desse tipo para `Goal` - é geometria placeholder,
    Seção 6.4/Risco 22) - é a validade ESTRUTURAL da região (retângulo com
    largura/altura positivas): `1.0` se bem formada, `0.0` se degenerada,
    `None` se não houver gol algum. Nunca um valor inventado."""

    goal_detected: bool
    goal_center: Coordinate | None
    goal_width: float | None
    goal_height: float | None
    left_post: Coordinate | None
    right_post: Coordinate | None
    goal_regions: dict[GoalZone, Region] | None
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "goal_detected": self.goal_detected,
            "goal_center": (
                {"x": self.goal_center.x, "y": self.goal_center.y}
                if self.goal_center is not None else None
            ),
            "goal_width": self.goal_width,
            "goal_height": self.goal_height,
            "left_post": (
                {"x": self.left_post.x, "y": self.left_post.y}
                if self.left_post is not None else None
            ),
            "right_post": (
                {"x": self.right_post.x, "y": self.right_post.y}
                if self.right_post is not None else None
            ),
            "goal_regions": (
                {zone.value: region.to_dict() for zone, region in self.goal_regions.items()}
                if self.goal_regions is not None else None
            ),
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperPositionResult(AnalysisResult):
    """Resposta às perguntas puramente geométricas sobre a relação entre
    goleiro e gol - nenhuma avaliação de qualidade, nenhum julgamento de
    "posição correta". Composição direta (não Registry/Processor) de
    `GoalkeeperPresenceAnalyzer`-like (leitura direta de
    `FootballWorld.goalkeepers[0]`) e `GoalGeometryAnalyzer` (Sprint W14,
    instanciado internamente e chamado como função pura).

    Quando falta goleiro OU gol, todo campo geométrico que dependeria dos
    dois é explicitamente `None` - nunca um valor inventado.

    `inside_goal_area`/`inside_penalty_area`: comparam a posição do
    goleiro contra retângulos derivados de PROPORÇÕES OFICIAIS de campo
    de futebol (área de meta ≈ 5.5m de profundidade / gol+11m de largura;
    área de pênalti ≈ 16.5m de profundidade / gol+33m de largura,
    convertidas em múltiplos de `goal_height`) - mesma disciplina de
    proporção fixa e documentada já usada por `Goal.default_pair()`
    (W12); não são medidas do vídeo real (mesma limitação de calibração
    do Risco 22/27).

    `covers_left_post`/`covers_center`/`covers_right_post`: dividem o
    vão do gol em 3 terços iguais ao longo do eixo y e verificam em qual
    terço a posição lateral do goleiro cai - **convenção determinística**
    de que y menor corresponde ao poste esquerdo (sem calibração de
    câmera/direção de jogo conhecida, Risco 22, esta correspondência é
    arbitrária mas fixa, nunca reavaliada por heurística)."""

    goalkeeper_detected: bool
    goal_detected: bool
    distance_to_goal_center: float | None
    lateral_offset: float | None
    depth_offset: float | None
    angle_to_goal: float | None
    inside_goal_area: bool | None
    inside_penalty_area: bool | None
    covers_left_post: bool | None
    covers_center: bool | None
    covers_right_post: bool | None
    goalkeeper_position: Coordinate | None
    goal_center: Coordinate | None
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "goalkeeper_detected": self.goalkeeper_detected,
            "goal_detected": self.goal_detected,
            "distance_to_goal_center": self.distance_to_goal_center,
            "lateral_offset": self.lateral_offset,
            "depth_offset": self.depth_offset,
            "angle_to_goal": self.angle_to_goal,
            "inside_goal_area": self.inside_goal_area,
            "inside_penalty_area": self.inside_penalty_area,
            "covers_left_post": self.covers_left_post,
            "covers_center": self.covers_center,
            "covers_right_post": self.covers_right_post,
            "goalkeeper_position": (
                {"x": self.goalkeeper_position.x, "y": self.goalkeeper_position.y}
                if self.goalkeeper_position is not None else None
            ),
            "goal_center": (
                {"x": self.goal_center.x, "y": self.goal_center.y}
                if self.goal_center is not None else None
            ),
            "confidence": self.confidence,
        })
        return payload


@dataclass
class BallPositionResult(AnalysisResult):
    """Resposta às perguntas puramente geométricas sobre a relação entre
    bola e gol (Sprint W16) - nenhuma previsão de trajetória, nenhuma
    avaliação de risco, nenhum conceito de "bola perigosa". Composição
    direta (mesmo padrão da W15) de leitura direta de
    `FootballWorld.balls[0]` e `GoalGeometryAnalyzer` (instanciado
    internamente, chamado como função pura).

    `ball_region`: qual zona de `GoalGeometryResult.goal_regions` (a
    grade 2×3, W14) contém a posição atual da bola, se houver - `None`
    se a bola estiver fora de todas as zonas (o caso comum, já que a
    bola normalmente está longe da faixa fina do gol) ou se não houver
    zonas computadas (geometria degenerada). Mesma disciplina de
    `inside_goal_area`/`inside_penalty_area` de `GoalkeeperPositionResult`
    (W15): containment puramente geométrico, nunca previsão de para onde
    a bola vai."""

    ball_detected: bool
    goal_detected: bool
    ball_position: Coordinate | None
    ball_bbox: Region | None
    distance_to_goal_center: float | None
    lateral_offset: float | None
    depth_offset: float | None
    angle_to_goal: float | None
    inside_goal_area: bool | None
    inside_penalty_area: bool | None
    ball_region: GoalZone | None
    goal_center: Coordinate | None
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "ball_detected": self.ball_detected,
            "goal_detected": self.goal_detected,
            "ball_position": (
                {"x": self.ball_position.x, "y": self.ball_position.y}
                if self.ball_position is not None else None
            ),
            "ball_bbox": self.ball_bbox.to_dict() if self.ball_bbox is not None else None,
            "distance_to_goal_center": self.distance_to_goal_center,
            "lateral_offset": self.lateral_offset,
            "depth_offset": self.depth_offset,
            "angle_to_goal": self.angle_to_goal,
            "inside_goal_area": self.inside_goal_area,
            "inside_penalty_area": self.inside_penalty_area,
            "ball_region": self.ball_region.value if self.ball_region is not None else None,
            "goal_center": (
                {"x": self.goal_center.x, "y": self.goal_center.y}
                if self.goal_center is not None else None
            ),
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperBallAlignmentResult(AnalysisResult):
    """Resposta às perguntas puramente geométricas sobre a relação
    espacial entre goleiro, bola e gol (Sprint W17) - primeiro Analyzer
    RELACIONAL, combinando os resultados de três Analyzers já existentes
    (`GoalGeometryAnalyzer`/`GoalkeeperPositionAnalyzer`/
    `BallPositionAnalyzer`, cada um instanciado internamente). Nenhuma
    avaliação de desempenho, nenhum julgamento de posicionamento, nenhuma
    detecção de chute, nenhum conceito de "bem posicionado" - só mede.

    `ball_to_goal_distance`/`ball_goal_angle` e
    `goalkeeper_to_goal_distance`/`goalkeeper_goal_angle` são ECOADOS
    diretamente de `BallPositionResult.distance_to_goal_center`/
    `.angle_to_goal` e `GoalkeeperPositionResult.distance_to_goal_center`/
    `.angle_to_goal` - nunca recalculados, evitando divergência entre os
    Analyzers. `goalkeeper_to_ball_distance`/`goalkeeper_ball_angle` são
    o único cálculo genuinamente NOVO desta sprint (nenhum Analyzer
    anterior relaciona goleiro e bola diretamente).

    `alignment_line`: o vetor da bola até o centro do gol (a "linha de
    tiro" geométrica) - `Vector.between(ball_position, goal_center)`,
    reaproveitável tanto como ângulo (`.angle_degrees()`) quanto como
    componentes cartesianas (`.dx`/`.dy`) por analisadores futuros.

    `alignment_offset`/`is_between_ball_and_goal`: projeção geométrica do
    goleiro sobre a reta bola→gol (distância perpendicular e se a
    projeção cai dentro do segmento, não além de nenhuma das
    extremidades) - medição pura de alinhamento espacial, nunca uma
    afirmação de que o goleiro está "bem posicionado" (essa é uma decisão
    de julgamento, fora de escopo desta sprint)."""

    goalkeeper_detected: bool
    ball_detected: bool
    goal_detected: bool
    goalkeeper_position: Coordinate | None
    ball_position: Coordinate | None
    goal_center: Coordinate | None
    goalkeeper_to_ball_distance: float | None
    ball_to_goal_distance: float | None
    goalkeeper_to_goal_distance: float | None
    goalkeeper_ball_angle: float | None
    ball_goal_angle: float | None
    goalkeeper_goal_angle: float | None
    alignment_offset: float | None
    is_between_ball_and_goal: bool | None
    alignment_line: Vector | None
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "goalkeeper_detected": self.goalkeeper_detected,
            "ball_detected": self.ball_detected,
            "goal_detected": self.goal_detected,
            "goalkeeper_position": (
                {"x": self.goalkeeper_position.x, "y": self.goalkeeper_position.y}
                if self.goalkeeper_position is not None else None
            ),
            "ball_position": (
                {"x": self.ball_position.x, "y": self.ball_position.y}
                if self.ball_position is not None else None
            ),
            "goal_center": (
                {"x": self.goal_center.x, "y": self.goal_center.y}
                if self.goal_center is not None else None
            ),
            "goalkeeper_to_ball_distance": self.goalkeeper_to_ball_distance,
            "ball_to_goal_distance": self.ball_to_goal_distance,
            "goalkeeper_to_goal_distance": self.goalkeeper_to_goal_distance,
            "goalkeeper_ball_angle": self.goalkeeper_ball_angle,
            "ball_goal_angle": self.ball_goal_angle,
            "goalkeeper_goal_angle": self.goalkeeper_goal_angle,
            "alignment_offset": self.alignment_offset,
            "is_between_ball_and_goal": self.is_between_ball_and_goal,
            "alignment_line": (
                {"dx": self.alignment_line.dx, "dy": self.alignment_line.dy}
                if self.alignment_line is not None else None
            ),
            "confidence": self.confidence,
        })
        return payload


@dataclass
class BallMotionResult(AnalysisResult):
    """Resposta às perguntas sobre o movimento OBSERVADO da bola entre
    frames consecutivos (Sprint W18) - primeiro resultado de um Analyzer
    STATEFUL. Nenhuma previsão de trajetória futura, nenhuma detecção de
    chute, nenhuma avaliação de risco/perigo - apenas o que já aconteceu,
    comparando a posição atual com a posição anterior memorizada em
    `BallMotionContext`.

    `displacement`/`speed` são numericamente iguais (mesma convenção já
    estabelecida por `Motion` no World Model, Seção 6.1, W11: "velocidade"
    aqui é só o deslocamento por frame, já que nenhuma camada da Analyzer
    API recebe fps) - mantidos como campos distintos porque representam
    conceitos diferentes para quem consome o artefato (`speed` é a
    magnitude de `velocity`, `displacement` é a distância percorrida).
    `velocity` (vetor com magnitude = speed) é distinto de
    `direction_vector` (o MESMO vetor normalizado, magnitude 1) - dois
    formatos convenientes da mesma direção, sem redundância de
    informação nova.

    `motion_detected`/`acceleration`/`previous_position` são `None`
    sempre que não há uma posição anterior VÁLIDA para comparar - o que
    inclui tanto a primeira observação da bola quanto qualquer
    reaparecimento após a bola ter desaparecido (o `track_id` mudou ou
    a bola sumiu por 1+ frames): esta sprint NUNCA infere um
    deslocamento através de uma lacuna de frames onde a bola não foi
    vista, para não extrapolar."""

    ball_detected: bool
    current_position: Coordinate | None
    previous_position: Coordinate | None
    displacement: float | None
    velocity: Vector | None
    speed: float | None
    direction_vector: Vector | None
    direction_angle: float | None
    acceleration: float | None
    frames_observed: int
    motion_detected: bool | None
    stationary: bool | None
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "ball_detected": self.ball_detected,
            "current_position": (
                {"x": self.current_position.x, "y": self.current_position.y}
                if self.current_position is not None else None
            ),
            "previous_position": (
                {"x": self.previous_position.x, "y": self.previous_position.y}
                if self.previous_position is not None else None
            ),
            "displacement": self.displacement,
            "velocity": (
                {"dx": self.velocity.dx, "dy": self.velocity.dy}
                if self.velocity is not None else None
            ),
            "speed": self.speed,
            "direction_vector": (
                {"dx": self.direction_vector.dx, "dy": self.direction_vector.dy}
                if self.direction_vector is not None else None
            ),
            "direction_angle": self.direction_angle,
            "acceleration": self.acceleration,
            "frames_observed": self.frames_observed,
            "motion_detected": self.motion_detected,
            "stationary": self.stationary,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class ShotAnalysisResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W19): "houve um evento
    compatível com um chute?" - NUNCA detecta gol, NUNCA avalia defesa,
    NUNCA avalia qualidade. Primeiro Analyzer de EVENTOS: combina os
    resultados de `BallMotionAnalyzer`/`BallPositionAnalyzer`/
    `GoalGeometryAnalyzer` (todos ecoados, nunca recalculados) contra
    critérios determinísticos e parametrizáveis (`WORKER_SHOT_MIN_SPEED`/
    `WORKER_SHOT_MAX_ANGLE_DEVIATION_DEGREES`/
    `WORKER_SHOT_MIN_CONSECUTIVE_FRAMES`).

    `shot_detected` exige TRÊS condições simultâneas, mantidas por
    `WORKER_SHOT_MIN_CONSECUTIVE_FRAMES` frames CONSEGUIDOS: velocidade
    observada >= mínimo, direção consistente com "em direção ao gol"
    (`towards_goal`), e movimento contínuo (a mesma bola, sem lacuna -
    herdado de `BallMotionAnalyzer`). `shot_start_frame` é o frame_index
    em que essa sequência qualificante começou - não o frame em que
    `shot_detected` passou a `True` (que só acontece depois de already
    `WORKER_SHOT_MIN_CONSECUTIVE_FRAMES` terem se acumulado).

    `towards_goal` compara o ângulo entre a direção OBSERVADA do
    movimento (`direction_vector`, de `BallMotionAnalyzer`) e a direção
    da bola até o centro do gol (`Vector.between(position, goal_center)`)
    via `angle_between()` - geometria pura, nunca uma previsão de para
    onde a bola vai continuar."""

    ball_detected: bool
    motion_detected: bool | None
    shot_detected: bool
    shot_start_frame: int | None
    ball_speed: float | None
    direction_vector: Vector | None
    direction_angle: float | None
    towards_goal: bool | None
    distance_to_goal: float | None
    observation_count: int
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "ball_detected": self.ball_detected,
            "motion_detected": self.motion_detected,
            "shot_detected": self.shot_detected,
            "shot_start_frame": self.shot_start_frame,
            "ball_speed": self.ball_speed,
            "direction_vector": (
                {"dx": self.direction_vector.dx, "dy": self.direction_vector.dy}
                if self.direction_vector is not None else None
            ),
            "direction_angle": self.direction_angle,
            "towards_goal": self.towards_goal,
            "distance_to_goal": self.distance_to_goal,
            "observation_count": self.observation_count,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class BallTrajectoryResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W20): "como a bola se
    moveu, observada até agora?" - NUNCA detecta gol, NUNCA avalia
    defesa, NUNCA julga decisões do goleiro, NUNCA prevê posições
    futuras. Terceiro Analyzer STATEFUL (depois de `BallMotionAnalyzer`
    W18 e `ShotAnalyzer` W19): acumula, em `BallTrajectoryContext`, a
    sequência de posições da MESMA bola continuamente observada (mesma
    disciplina de continuidade de `BallMotionAnalyzer` - qualquer
    lacuna/mudança de `track_id` reinicia a trajetória do zero).

    `trajectory_length` é o comprimento acumulado do CAMINHO percorrido
    (soma das magnitudes de cada segmento frame-a-frame), distinto da
    distância em linha reta do primeiro ao último ponto. `linearity_score`
    é justamente a razão entre essas duas grandezas (distância em linha
    reta / comprimento do caminho, sempre em [0, 1] pela desigualdade
    triangular) - representa SÓ o quanto o caminho observado se aproxima
    de uma reta, nunca qualidade/perigo/precisão. `direction_consistency`
    é o comprimento do vetor resultante médio dos segmentos normalizados
    (estatística circular clássica, também em [0, 1]: 1.0 = todos os
    segmentos apontam exatamente na mesma direção). `average_velocity`
    (vetor) e `dominant_direction` (o mesmo vetor, como ângulo) são duas
    representações convenientes da mesma direção média - mesmo padrão já
    usado por `velocity`/`direction_angle` em `BallMotionResult` (W18).

    `confidence` combina os três sinais reais disponíveis - de
    `BallMotionAnalyzer`, `BallPositionAnalyzer` e `GoalGeometryAnalyzer`
    (via `min()`, nunca inventado) - embora nenhum campo de trajetória em
    si dependa de geometria do gol; `GoalGeometryAnalyzer` é composto
    apenas para fornecer esse terceiro sinal real de confiança."""

    ball_detected: bool
    trajectory_detected: bool
    trajectory_points: list[Coordinate] | None
    trajectory_length: float | None
    dominant_direction: float | None
    average_velocity: Vector | None
    direction_consistency: float | None
    direction_changes: int
    linearity_score: float | None
    frames_observed: int
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "ball_detected": self.ball_detected,
            "trajectory_detected": self.trajectory_detected,
            "trajectory_points": (
                [{"x": point.x, "y": point.y} for point in self.trajectory_points]
                if self.trajectory_points is not None else None
            ),
            "trajectory_length": self.trajectory_length,
            "dominant_direction": self.dominant_direction,
            "average_velocity": (
                {"dx": self.average_velocity.dx, "dy": self.average_velocity.dy}
                if self.average_velocity is not None else None
            ),
            "direction_consistency": self.direction_consistency,
            "direction_changes": self.direction_changes,
            "linearity_score": self.linearity_score,
            "frames_observed": self.frames_observed,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class PlaySituationResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W21): "qual é a situação
    atual da jogada?" - primeiro Analyzer COGNITIVO: classifica o estado
    OBSERVADO, nunca avalia o goleiro, nunca avalia defesa, nunca julga
    decisões, nunca emite nota de qualidade. Combina EXCLUSIVAMENTE
    resultados já produzidos por `ShotAnalyzer`/`BallTrajectoryAnalyzer`/
    `GoalkeeperBallAlignmentAnalyzer`/`GoalGeometryAnalyzer` - nenhuma
    geometria/cinemática é recalculada.

    `situation` é a classificação PRIMÁRIA, por uma árvore de decisão
    determinística e priorizada (ver `PlaySituationAnalyzer._classify`):
    ausência de bola > ausência de goleiro > chute detectado > bola em
    movimento > bola parada > desconhecido (histórico insuficiente).
    `sub_state` é um refinamento OPCIONAL e independente sobre a direção
    do movimento observado (`towards_goal`, de `ShotAnalyzer`) - populado
    sempre que há uma direção observável comparável contra o gol, mesmo
    quando `shot_detected` ainda é `False` (ex.: movimento real mas
    abaixo do limiar de velocidade/frames consecutivos de um chute)."""

    situation: PlaySituation
    sub_state: PlaySituation | None
    ball_detected: bool
    goalkeeper_detected: bool
    shot_detected: bool
    trajectory_detected: bool
    alignment_detected: bool
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "situation": self.situation,
            "sub_state": self.sub_state,
            "ball_detected": self.ball_detected,
            "goalkeeper_detected": self.goalkeeper_detected,
            "shot_detected": self.shot_detected,
            "trajectory_detected": self.trajectory_detected,
            "alignment_detected": self.alignment_detected,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperDecisionResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W22): "qual decisão o
    goleiro aparenta estar executando?" - primeiro Analyzer específico do
    goleiro. NUNCA avalia se a decisão foi correta, NUNCA dá nota, NUNCA
    julga desempenho - apenas identifica o comportamento observado.
    Combina resultados já produzidos por `PlaySituationAnalyzer`/
    `GoalkeeperPositionAnalyzer`/`GoalkeeperBallAlignmentAnalyzer`/
    `BallTrajectoryAnalyzer`/`ShotAnalyzer` - nenhuma geometria/cinemática
    já calculada é recalculada.

    `movement_direction`/`movement_speed` são a única informação
    GENUINAMENTE NOVA desta sprint (nenhum Analyzer composto rastreia o
    movimento do PRÓPRIO goleiro entre frames) - calculados comparando a
    posição atual do goleiro (`GoalkeeperPositionResult.goalkeeper_position`)
    com a posição memorizada do frame anterior, mesma disciplina de
    continuidade de `BallMotionAnalyzer` (W18): qualquer lacuna ou
    mudança de `track_id` reinicia a observação, nunca extrapola.

    `decision` é sempre um valor (nunca `None`) - `UNKNOWN` quando não há
    goleiro/histórico suficiente para classificar. `play_situation` ecoa
    `PlaySituationResult.situation` (W21) - o contexto da jogada em que a
    decisão foi tomada."""

    decision: GoalkeeperDecision
    play_situation: PlaySituation
    ball_detected: bool
    goalkeeper_detected: bool
    goalkeeper_position: Coordinate | None
    movement_direction: Vector | None
    movement_speed: float | None
    ball_direction: float | None
    alignment: bool | None
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "decision": self.decision,
            "play_situation": self.play_situation,
            "ball_detected": self.ball_detected,
            "goalkeeper_detected": self.goalkeeper_detected,
            "goalkeeper_position": (
                {"x": self.goalkeeper_position.x, "y": self.goalkeeper_position.y}
                if self.goalkeeper_position is not None else None
            ),
            "movement_direction": (
                {"dx": self.movement_direction.dx, "dy": self.movement_direction.dy}
                if self.movement_direction is not None else None
            ),
            "movement_speed": self.movement_speed,
            "ball_direction": self.ball_direction,
            "alignment": self.alignment,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperDecisionEvaluationResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W23): "a decisão tomada
    pelo goleiro foi compatível com a situação observada?" - primeiro
    Analyzer de AVALIAÇÃO. NUNCA avalia o resultado da jogada (não
    determina se houve defesa/gol), NUNCA julga desempenho - só verifica
    CONSISTÊNCIA lógica entre `PlaySituation` (W21) e `GoalkeeperDecision`
    (W22), via um mecanismo explícito e auditável de Rule Evaluation
    (`worker.analyzers.rules`).

    `evaluation` é o veredito agregado (sempre um valor, nunca `None`).
    `rules_evaluated`/`rules_passed`/`rules_failed`/`explanations` tornam
    esse veredito EXPLICÁVEL - nunca um estado isolado sem justificativa:
    `rules_evaluated` lista TODOS os `Rule.id` avaliados (mesmo os que
    resultaram `None`/não aplicável); `rules_passed`/`rules_failed`
    listam só os `id`s cujo resultado foi `True`/`False`;
    `explanations` traz uma frase legível por regra, na mesma ordem."""

    evaluation: GoalkeeperDecisionEvaluation
    play_situation: PlaySituation
    goalkeeper_decision: GoalkeeperDecision
    rules_evaluated: list[str]
    rules_passed: list[str]
    rules_failed: list[str]
    explanations: list[str]
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "evaluation": self.evaluation,
            "play_situation": self.play_situation,
            "goalkeeper_decision": self.goalkeeper_decision,
            "rules_evaluated": list(self.rules_evaluated),
            "rules_passed": list(self.rules_passed),
            "rules_failed": list(self.rules_failed),
            "explanations": list(self.explanations),
            "confidence": self.confidence,
        })
        return payload


@dataclass
class PlayOutcomeResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W24): "qual foi o
    resultado OBSERVADO da jogada?" - encerra a cadeia Observação
    (W13-W20) → Situação (W21) → Decisão (W22) → Avaliação (W23) →
    Resultado (W24). NUNCA avalia o goleiro, NUNCA atribui nota, NUNCA
    julga a qualidade da decisão - apenas identifica o resultado
    observável, combinando exclusivamente resultados já produzidos por
    `PlaySituationAnalyzer`/`ShotAnalyzer`/`BallTrajectoryAnalyzer`/
    `GoalGeometryAnalyzer`/`GoalkeeperDecisionAnalyzer`.

    `ball_last_position`/`goalkeeper_last_position` sobrevivem a um
    frame em que a bola/o goleiro momentaneamente não é detectado
    (memorizados em `PlayOutcomeContext`) - essencial para `LOST_TRACK`
    carregar alguma evidência posicional útil, em vez de ficar vazio no
    exato momento em que se torna interessante.

    `supporting_evidence` traz explicações SIMPLES (não o mecanismo
    completo de Rule Evaluation da W23, por instrução explícita desta
    sprint) - uma lista de frases legíveis descrevendo os fatos que
    levaram à classificação de `outcome`."""

    outcome: PlayOutcome
    play_situation: PlaySituation
    shot_detected: bool
    ball_detected: bool
    goalkeeper_detected: bool
    ball_visible: bool
    goal_visible: bool
    ball_last_position: Coordinate | None
    goalkeeper_last_position: Coordinate | None
    supporting_evidence: list[str]
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "outcome": self.outcome,
            "play_situation": self.play_situation,
            "shot_detected": self.shot_detected,
            "ball_detected": self.ball_detected,
            "goalkeeper_detected": self.goalkeeper_detected,
            "ball_visible": self.ball_visible,
            "goal_visible": self.goal_visible,
            "ball_last_position": (
                {"x": self.ball_last_position.x, "y": self.ball_last_position.y}
                if self.ball_last_position is not None else None
            ),
            "goalkeeper_last_position": (
                {"x": self.goalkeeper_last_position.x, "y": self.goalkeeper_last_position.y}
                if self.goalkeeper_last_position is not None else None
            ),
            "supporting_evidence": list(self.supporting_evidence),
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperPerformanceEvaluationResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W25): "como foi o
    desempenho OBSERVADO do goleiro nesta jogada?" - encerra a cadeia
    Situação (W21) → Decisão (W22) → Avaliação da Decisão (W23) →
    Resultado (W24) → Avaliação de Desempenho (W25). NUNCA gera
    recomendação, NUNCA faz coaching - combina EXCLUSIVAMENTE
    `GoalkeeperDecisionEvaluationResult.evaluation` (W23) e
    `PlayOutcomeResult.outcome` (W24), via o MESMO mecanismo de Rule
    Evaluation da W23 (`worker.analyzers.rules`) - nenhum mecanismo de
    regras novo, nenhuma geometria/cinemática recalculada.

    `summary` é uma string ESTRUTURADA (não linguagem natural, por
    instrução explícita desta sprint) - concatena `performance`/
    `decision_evaluation`/`play_outcome`/as regras que contribuíram,
    suficiente para auditoria sem gerar prosa."""

    performance: GoalkeeperPerformanceEvaluation
    decision_evaluation: GoalkeeperDecisionEvaluation
    play_outcome: PlayOutcome
    rules_evaluated: list[str]
    rules_passed: list[str]
    rules_failed: list[str]
    summary: str
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "performance": self.performance,
            "decision_evaluation": self.decision_evaluation,
            "play_outcome": self.play_outcome,
            "rules_evaluated": list(self.rules_evaluated),
            "rules_passed": list(self.rules_passed),
            "rules_failed": list(self.rules_failed),
            "summary": self.summary,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperCoachingResult(AnalysisResult):
    """Resposta à única pergunta desta sprint (W26): "qual orientação
    técnica pode ser extraída desta jogada?" - primeiro Analyzer de
    COACHING, encerra a transição de AVALIAÇÃO (W21-W25, descreve/
    classifica/avalia o que já aconteceu) para ORIENTAÇÃO (o que fazer
    diferente da próxima vez). NUNCA gera linguagem natural, NUNCA
    produz relatório final - apenas uma classificação fortemente tipada
    (`GoalkeeperCoaching`), via o MESMO mecanismo de Rule Evaluation da
    W23 (`worker.analyzers.rules`) - nenhum mecanismo de regras novo.

    `decision_evaluation` é incluído (além dos campos sugeridos pela
    especificação) para auditabilidade - as regras de coaching desta
    sprint leem diretamente `GoalkeeperDecisionEvaluationResult.rules_failed`
    (W23) para identificar qual desvio específico motivou a orientação
    (ex.: "shot_prompts_active_response" violada -> `MOVE_EARLIER`) -
    documentar também de qual avaliação de compatibilidade a orientação
    partiu completa a cadeia de auditoria.

    `summary` é uma string ESTRUTURADA (não linguagem natural, mesmo
    princípio da W25) - concatena `coaching`/`performance`/`decision`/
    `outcome`/as regras que contribuíram."""

    coaching: GoalkeeperCoaching
    performance: GoalkeeperPerformanceEvaluation
    decision_evaluation: GoalkeeperDecisionEvaluation
    decision: GoalkeeperDecision
    outcome: PlayOutcome
    rules_evaluated: list[str]
    rules_passed: list[str]
    rules_failed: list[str]
    summary: str
    confidence: float | None

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "coaching": self.coaching,
            "performance": self.performance,
            "decision_evaluation": self.decision_evaluation,
            "decision": self.decision,
            "outcome": self.outcome,
            "rules_evaluated": list(self.rules_evaluated),
            "rules_passed": list(self.rules_passed),
            "rules_failed": list(self.rules_failed),
            "summary": self.summary,
            "confidence": self.confidence,
        })
        return payload


@dataclass
class GoalkeeperAnalysisReport(AnalysisResult):
    """Resposta à única pergunta desta sprint (W27): "qual é a análise
    COMPLETA e consolidada desta jogada?" - encerra oficialmente o MVP
    arquitetural do Worker. NÃO produz nenhuma conclusão nova, NÃO
    recalcula nada, NÃO executa nenhuma regra nova - apenas AGREGA os
    seis resultados já produzidos por `PlaySituationAnalyzer` (W21),
    `GoalkeeperDecisionAnalyzer` (W22), `GoalkeeperDecisionEvaluationAnalyzer`
    (W23), `PlayOutcomeAnalyzer` (W24), `GoalkeeperPerformanceEvaluationAnalyzer`
    (W25) e `GoalkeeperCoachingAnalyzer` (W26) - cada um deles já
    encerra, por si só, toda a cadeia de camadas anteriores.

    Passa a ser o **CONTRATO OFICIAL de saída do Worker** - consumidores
    externos (o Backend FastAPI) devem depender deste objeto, não de
    `analysis_results` individuais no artefato bruto.

    Os seis campos tipados abaixo preservam INTEGRALMENTE cada
    sub-resultado (nunca removem `rules_evaluated`/`rules_passed`/
    `rules_failed`/`explanations`/`summary`/`supporting_evidence` -
    `to_dict()` delega a cada um deles, não reconstrói nenhum campo).
    `artifacts` é um espelho de conveniência dos mesmos seis
    sub-resultados, agora indexados por nome de Analyzer (mesma
    convenção de `analysis_results` desde a W13) - útil para um
    consumidor genérico que itere por nome em vez de conhecer os seis
    nomes de campo de antemão. `confidence_summary` CONSOLIDA (nunca
    recalcula) as seis `confidence`s já produzidas, mais `overall` (o
    `min()` das seis, só quando todas disponíveis - mesmo princípio de
    "nunca fabricar" já usado em todo Analyzer composto desde a W17).
    `analysis_version` é a versão do ESQUEMA deste relatório consolidado
    (distinta de `worker_version`, a versão do software - mesmo
    princípio de `WORKER_PROTOCOL_VERSION` vs. `worker.__version__`,
    Sprint W2). `generated_at` é um timestamp real (ISO 8601, UTC) de
    quando o relatório foi montado - o único campo desta sprint que não
    é determinístico frame-a-frame, mas reflete um fato real (agora),
    não uma inferência fabricada."""

    play_situation: PlaySituationResult
    goalkeeper_decision: GoalkeeperDecisionResult
    decision_evaluation: GoalkeeperDecisionEvaluationResult
    play_outcome: PlayOutcomeResult
    performance_evaluation: GoalkeeperPerformanceEvaluationResult
    coaching: GoalkeeperCoachingResult
    confidence_summary: dict
    artifacts: dict
    analysis_version: str
    worker_version: str
    generated_at: str

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload.update({
            "play_situation": self.play_situation.to_dict(),
            "goalkeeper_decision": self.goalkeeper_decision.to_dict(),
            "decision_evaluation": self.decision_evaluation.to_dict(),
            "play_outcome": self.play_outcome.to_dict(),
            "performance_evaluation": self.performance_evaluation.to_dict(),
            "coaching": self.coaching.to_dict(),
            "confidence_summary": self.confidence_summary,
            "artifacts": self.artifacts,
            "analysis_version": self.analysis_version,
            "worker_version": self.worker_version,
            "generated_at": self.generated_at,
        })
        return payload


@dataclass
class AnalysisStatistics:
    """Resumo do estado ATUAL da Analyzer API - reflete o último frame
    processado, mesmo espírito de `WorldStatistics`/`SceneStatistics`
    (não é cumulativo ao longo do vídeo, é uma fotografia)."""

    analyzers_run: list[str]
    results_count: int

    def to_dict(self) -> dict:
        return {"analyzers_run": self.analyzers_run, "results_count": self.results_count}
