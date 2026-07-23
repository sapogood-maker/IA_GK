"""Tipos básicos próprios da Analyzer API - mesma pequena duplicação já
praticada entre `inference/detectors`/`trackers`/`events`/`world` (cada
família define seus próprios `NewType`s, em vez de importar de outra
camada - reforça que `analyzers/` não depende de nenhuma delas)."""
from __future__ import annotations

from enum import Enum
from typing import NewType

AnalyzerName = NewType("AnalyzerName", str)
AnalyzerVersion = NewType("AnalyzerVersion", str)


class GoalZone(str, Enum):
    """Zona de cobertura do gol - subdivisão puramente geométrica da
    região do gol numa grade 2x3 (2 linhas: topo/base; 3 colunas:
    esquerda/centro/direita). Convenção comum de análise de goleiro
    (canto superior esquerdo, canto inferior direito, etc.) - mas esta
    sprint apenas nomeia e calcula as zonas, nenhuma avaliação de qual
    zona é "melhor" ou "pior" para um goleiro cobrir."""

    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class PlaySituation(str, Enum):
    """Classificação do estado OBSERVADO da jogada atual (Sprint W21) -
    puramente descritiva, nunca uma avaliação de qualidade/mérito/
    decisão. Cada valor é produzido por uma regra determinística sobre
    campos já computados por outros Analyzers (ver `PlaySituationAnalyzer`)
    - nenhuma IA, nenhum modelo treinado.

    `BALL_INSIDE_GOAL_AREA`/`BALL_INSIDE_PENALTY_AREA` (mencionados como
    exemplos na especificação da sprint) foram DELIBERADAMENTE deixados
    de fora desta enumeração - exigiriam compor `BallPositionAnalyzer`
    diretamente (que já calcula `inside_goal_area`/`inside_penalty_area`),
    fora da lista explícita de Analyzers a reutilizar nesta sprint
    (`ShotAnalyzer`/`BallTrajectoryAnalyzer`/
    `GoalkeeperBallAlignmentAnalyzer`/`GoalGeometryAnalyzer`); adicioná-los
    exigiria recalcular essa informação ou estourar a composição
    combinada - ambos violam a regra desta sprint. Documentado
    honestamente (ver Constituição, achado da W21)."""

    UNKNOWN = "unknown"
    NO_BALL_VISIBLE = "no_ball_visible"
    NO_GOALKEEPER_VISIBLE = "no_goalkeeper_visible"
    BALL_STATIONARY = "ball_stationary"
    BALL_MOVING = "ball_moving"
    SHOT_DETECTED = "shot_detected"
    SHOT_TOWARDS_GOAL = "shot_towards_goal"
    SHOT_AWAY_FROM_GOAL = "shot_away_from_goal"


class GoalkeeperDecision(str, Enum):
    """Classificação da decisão OBSERVADA que o goleiro aparenta estar
    executando (Sprint W22) - primeiro Analyzer específico do goleiro.
    NUNCA avalia se a decisão foi correta, nunca dá nota, nunca julga
    desempenho - apenas identifica o comportamento observado (o quanto o
    goleiro se moveu, em qual direção, e em que contexto de jogada) via
    regras 100% determinísticas sobre campos já computados por outros
    Analyzers (ver `GoalkeeperDecisionAnalyzer`) - nenhuma IA, nenhum
    modelo treinado, nenhuma estimativa de pose/postura (o Worker não tem
    keypoints do goleiro - `PREPARE_DIVE` é um proxy determinístico
    baseado em velocidade observada, não em postura corporal real;
    documentado honestamente como limitação, não uma detecção genuína de
    "posição de preparação")."""

    UNKNOWN = "unknown"
    STAY_ON_LINE = "stay_on_line"
    STEP_FORWARD = "step_forward"
    STEP_BACK = "step_back"
    SHIFT_LEFT = "shift_left"
    SHIFT_RIGHT = "shift_right"
    PREPARE_DIVE = "prepare_dive"
    DIVE_LEFT = "dive_left"
    DIVE_RIGHT = "dive_right"
    RECOVER_POSITION = "recover_position"


class GoalkeeperDecisionEvaluation(str, Enum):
    """Veredito de COMPATIBILIDADE entre a decisão observada do goleiro
    (`GoalkeeperDecision`, W22) e a situação de jogada observada
    (`PlaySituation`, W21) - Sprint W23, primeiro Analyzer de AVALIAÇÃO.
    NUNCA avalia o resultado da jogada (não determina se houve defesa ou
    gol) - responde apenas "a decisão foi compatível com a situação?",
    via um mecanismo explícito de Rule Evaluation (`worker.analyzers.rules`),
    100% determinístico, documentado e auditável - nenhuma IA, nenhum
    modelo treinado, nenhuma regra opaca.

    `UNKNOWN` (atores visíveis, mas decisão ainda não estabelecida -
    primeira observação/descontinuidade do goleiro, W22) é distinto de
    `INSUFFICIENT_INFORMATION` (bola e/ou goleiro nem sequer visíveis) -
    duas causas diferentes de "não dá para avaliar ainda"."""

    UNKNOWN = "unknown"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    COMPATIBLE = "compatible"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    INCOMPATIBLE = "incompatible"


class PlayOutcome(str, Enum):
    """Classificação do resultado OBSERVADO da jogada (Sprint W24) -
    encerra a cadeia Observação → Situação → Decisão → Avaliação →
    Resultado. NUNCA avalia o goleiro, NUNCA atribui nota, NUNCA julga a
    qualidade da decisão - responde só "qual foi o resultado observado?"
    via regras 100% determinísticas sobre campos já computados por
    outros Analyzers (ver `PlayOutcomeAnalyzer`) - nenhuma IA, nenhum
    modelo treinado.

    `CROSSBAR` está listado (fortemente tipado, conforme especificação
    da sprint) mas é DELIBERADAMENTE nunca produzido pela implementação
    atual - este Worker modela o gol como um retângulo 2D (Seção 6.4,
    Risco 22), sem nenhuma dimensão vertical/altura real; além disso,
    `GoalGeometryResult.left_post`/`right_post` (W14) têm o MESMO `y`
    (ambos em `region.y`), então não correspondem à real separação
    lateral dos postes estabelecida pela W15
    (`GoalkeeperPositionAnalyzer._covers_thirds`, que divide `region.height`
    para lateralidade) - não há hoje informação geométrica independente
    para distinguir "bateu na trave" de "bateu no travessão". Documentado
    honestamente (ver Constituição, achado da W24, Risco 39)."""

    UNKNOWN = "unknown"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    SAVE = "save"
    GOAL = "goal"
    BALL_OUT = "ball_out"
    BLOCKED = "blocked"
    POST = "post"
    CROSSBAR = "crossbar"
    LOST_TRACK = "lost_track"
    NO_SHOT_DETECTED = "no_shot_detected"


class GoalkeeperPerformanceEvaluation(str, Enum):
    """Avaliação FINAL do desempenho observado do goleiro nesta jogada
    (Sprint W25) - encerra a cadeia Situação (W21) → Decisão (W22) →
    Avaliação da Decisão (W23) → Resultado (W24) → Avaliação de
    Desempenho (W25). NUNCA gera recomendação, NUNCA faz coaching, NUNCA
    sugere melhoria - é a classificação FINAL da jogada, via um
    mecanismo explícito e auditável de Rule Evaluation (a MESMA
    infraestrutura da W23, `worker.analyzers.rules` - nenhum mecanismo
    de regras novo foi criado).

    Deriva EXCLUSIVAMENTE de `GoalkeeperDecisionEvaluation` (W23 - a
    decisão foi compatível com a situação?) cruzado com `PlayOutcome`
    (W24 - qual foi o resultado observado?), numa matriz 3x3
    determinística e documentada (ver `GoalkeeperPerformanceEvaluationAnalyzer`)
    - nunca uma reinterpretação de `PlaySituation`/`GoalkeeperDecision`
    diretamente."""

    UNKNOWN = "unknown"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"
    CRITICAL = "critical"


class GoalkeeperCoaching(str, Enum):
    """Orientação técnica extraída desta jogada (Sprint W26) - primeiro
    Analyzer de COACHING, encerrando a transição de AVALIAÇÃO (W21-W25:
    descreve/classifica/avalia o que já aconteceu) para ORIENTAÇÃO (o que
    fazer diferente da próxima vez). NUNCA gera linguagem natural, NUNCA
    produz relatório final, NUNCA sugere um plano de treino - responde
    apenas "qual orientação técnica esta jogada sugere?", via um
    mecanismo explícito e auditável de Rule Evaluation (a MESMA
    infraestrutura da W23/W25, `worker.analyzers.rules` - nenhum
    mecanismo de regras novo foi criado).

    Deriva EXCLUSIVAMENTE de `GoalkeeperPerformanceEvaluation` (W25),
    `GoalkeeperDecisionEvaluation`/`rules_failed` (W23, para identificar
    QUAL desvio específico motivou a orientação), `GoalkeeperDecision`
    (W22, o comportamento observado) e `PlayOutcome` (W24) - nunca uma
    reinterpretação de `PlaySituation` diretamente, nunca uma nova
    geometria/cinemática.

    `UNKNOWN`/`INSUFFICIENT_INFORMATION` espelham os mesmos dois gates de
    `GoalkeeperPerformanceEvaluation` (W25) - se a avaliação de
    desempenho não pôde ser estabelecida, nenhuma orientação técnica pode
    ser extraída dela. `NO_FEEDBACK` (desempenho `EXCELLENT`) e
    `KEEP_POSITION` (desempenho `GOOD`) são orientações de REFORÇO -
    "continue fazendo o que já está fazendo", não uma correção.
    `IMPROVE_POSITIONING` é a orientação residual/genérica (desempenho
    `ADEQUATE`/`POOR`/`CRITICAL` sem nenhum desvio específico e
    auditável identificado pelas regras). `MOVE_EARLIER`/`MOVE_LATER`/
    `ATTACK_BALL`/`STAY_PATIENT`/`RECOVER_FASTER` são orientações
    ESPECÍFICAS, cada uma rastreável até exatamente uma regra desta
    sprint (ver `GoalkeeperCoachingAnalyzer`)."""

    UNKNOWN = "unknown"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    NO_FEEDBACK = "no_feedback"
    KEEP_POSITION = "keep_position"
    IMPROVE_POSITIONING = "improve_positioning"
    MOVE_EARLIER = "move_earlier"
    MOVE_LATER = "move_later"
    ATTACK_BALL = "attack_ball"
    STAY_PATIENT = "stay_patient"
    RECOVER_FASTER = "recover_faster"
