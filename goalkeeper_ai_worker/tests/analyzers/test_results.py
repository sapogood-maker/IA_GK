"""Testes de worker.analyzers.results - tipos fortemente tipados de
resultado de Analyzer."""
from __future__ import annotations

from worker.analyzers.results import (
    AnalysisResult,
    AnalysisStatistics,
    AnalyzerMetadata,
    BallMotionResult,
    BallPositionResult,
    BallTrajectoryResult,
    GoalGeometryResult,
    GoalkeeperAnalysisReport,
    GoalkeeperBallAlignmentResult,
    GoalkeeperCoachingResult,
    GoalkeeperDecisionEvaluationResult,
    GoalkeeperDecisionResult,
    GoalkeeperPerformanceEvaluationResult,
    GoalkeeperPositionResult,
    GoalkeeperPresenceResult,
    PlayOutcomeResult,
    PlaySituationResult,
    ShotAnalysisResult,
)
from worker.domain.geometry.vector import Vector
from worker.analyzers.types import (
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


def _metadata() -> AnalyzerMetadata:
    return AnalyzerMetadata(analyzer_name="goalkeeper_presence", analyzer_version="1.0.0", processing_time_ms=0.5)


def test_analyzer_metadata_to_dict() -> None:
    payload = _metadata().to_dict()
    assert payload == {
        "analyzer_name": "goalkeeper_presence",
        "analyzer_version": "1.0.0",
        "processing_time_ms": 0.5,
    }


def test_analysis_result_base_to_dict() -> None:
    result = AnalysisResult(frame_index=4, metadata=_metadata())
    payload = result.to_dict()
    assert payload["frame_index"] == 4
    assert payload["analyzer_name"] == "goalkeeper_presence"


def test_goalkeeper_presence_result_to_dict_with_goalkeeper() -> None:
    result = GoalkeeperPresenceResult(
        frame_index=2, metadata=_metadata(),
        exists=True, visible=True, goalkeeper_count=1, track_id=9, age=12,
        current_position=Coordinate(x=1, y=2), current_bbox=Region(x=0, y=0, width=10, height=20),
    )

    payload = result.to_dict()

    assert payload["exists"] is True
    assert payload["visible"] is True
    assert payload["goalkeeper_count"] == 1
    assert payload["track_id"] == 9
    assert payload["age"] == 12
    assert payload["current_position"] == {"x": 1, "y": 2}
    assert payload["current_bbox"] == {"x": 0, "y": 0, "width": 10, "height": 20}
    assert payload["analyzer_name"] == "goalkeeper_presence"  # metadata embutida


def test_goalkeeper_presence_result_to_dict_without_goalkeeper() -> None:
    result = GoalkeeperPresenceResult(
        frame_index=0, metadata=_metadata(),
        exists=False, visible=False, goalkeeper_count=0, track_id=None, age=None,
        current_position=None, current_bbox=None,
    )

    payload = result.to_dict()

    assert payload["current_position"] is None
    assert payload["current_bbox"] is None
    assert payload["track_id"] is None


def test_goalkeeper_position_result_to_dict_with_both_detected() -> None:
    result = GoalkeeperPositionResult(
        frame_index=1, metadata=_metadata(),
        goalkeeper_detected=True, goal_detected=True,
        distance_to_goal_center=40.0, lateral_offset=0.0, depth_offset=40.0, angle_to_goal=180.0,
        inside_goal_area=True, inside_penalty_area=True,
        covers_left_post=False, covers_center=True, covers_right_post=False,
        goalkeeper_position=Coordinate(x=50, y=250), goal_center=Coordinate(x=10, y=250),
        confidence=0.9,
    )

    payload = result.to_dict()

    assert payload["goalkeeper_detected"] is True
    assert payload["goal_detected"] is True
    assert payload["distance_to_goal_center"] == 40.0
    assert payload["angle_to_goal"] == 180.0
    assert payload["inside_goal_area"] is True
    assert payload["covers_center"] is True
    assert payload["goalkeeper_position"] == {"x": 50, "y": 250}
    assert payload["goal_center"] == {"x": 10, "y": 250}
    assert payload["confidence"] == 0.9


def test_goalkeeper_position_result_to_dict_without_either() -> None:
    result = GoalkeeperPositionResult(
        frame_index=0, metadata=_metadata(),
        goalkeeper_detected=False, goal_detected=False,
        distance_to_goal_center=None, lateral_offset=None, depth_offset=None, angle_to_goal=None,
        inside_goal_area=None, inside_penalty_area=None,
        covers_left_post=None, covers_center=None, covers_right_post=None,
        goalkeeper_position=None, goal_center=None, confidence=None,
    )

    payload = result.to_dict()

    assert payload["goalkeeper_position"] is None
    assert payload["goal_center"] is None
    assert payload["distance_to_goal_center"] is None
    assert payload["confidence"] is None


def test_ball_position_result_to_dict_with_both_detected() -> None:
    from worker.analyzers.types import GoalZone

    result = BallPositionResult(
        frame_index=2, metadata=_metadata(),
        ball_detected=True, goal_detected=True,
        ball_position=Coordinate(x=50, y=250), ball_bbox=Region(x=45, y=245, width=10, height=10),
        distance_to_goal_center=40.0, lateral_offset=0.0, depth_offset=40.0, angle_to_goal=0.0,
        inside_goal_area=True, inside_penalty_area=True,
        ball_region=GoalZone.TOP_LEFT, goal_center=Coordinate(x=10, y=250), confidence=0.7,
    )

    payload = result.to_dict()

    assert payload["ball_detected"] is True
    assert payload["goal_detected"] is True
    assert payload["ball_position"] == {"x": 50, "y": 250}
    assert payload["ball_bbox"] == {"x": 45, "y": 245, "width": 10, "height": 10}
    assert payload["distance_to_goal_center"] == 40.0
    assert payload["inside_goal_area"] is True
    assert payload["ball_region"] == "top_left"
    assert payload["goal_center"] == {"x": 10, "y": 250}
    assert payload["confidence"] == 0.7


def test_ball_position_result_to_dict_without_either() -> None:
    result = BallPositionResult(
        frame_index=0, metadata=_metadata(),
        ball_detected=False, goal_detected=False,
        ball_position=None, ball_bbox=None,
        distance_to_goal_center=None, lateral_offset=None, depth_offset=None, angle_to_goal=None,
        inside_goal_area=None, inside_penalty_area=None,
        ball_region=None, goal_center=None, confidence=None,
    )

    payload = result.to_dict()

    assert payload["ball_position"] is None
    assert payload["ball_bbox"] is None
    assert payload["ball_region"] is None
    assert payload["confidence"] is None


def test_goalkeeper_ball_alignment_result_to_dict_with_all_detected() -> None:
    result = GoalkeeperBallAlignmentResult(
        frame_index=9, metadata=_metadata(),
        goalkeeper_detected=True, ball_detected=True, goal_detected=True,
        goalkeeper_position=Coordinate(x=50, y=250), ball_position=Coordinate(x=200, y=250),
        goal_center=Coordinate(x=10, y=250),
        goalkeeper_to_ball_distance=150.0, ball_to_goal_distance=190.0, goalkeeper_to_goal_distance=40.0,
        goalkeeper_ball_angle=0.0, ball_goal_angle=180.0, goalkeeper_goal_angle=180.0,
        alignment_offset=0.0, is_between_ball_and_goal=True,
        alignment_line=Vector(dx=-190.0, dy=0.0), confidence=0.3,
    )

    payload = result.to_dict()

    assert payload["goalkeeper_detected"] is True
    assert payload["ball_detected"] is True
    assert payload["goal_detected"] is True
    assert payload["goalkeeper_position"] == {"x": 50, "y": 250}
    assert payload["ball_position"] == {"x": 200, "y": 250}
    assert payload["goal_center"] == {"x": 10, "y": 250}
    assert payload["goalkeeper_to_ball_distance"] == 150.0
    assert payload["ball_to_goal_distance"] == 190.0
    assert payload["goalkeeper_to_goal_distance"] == 40.0
    assert payload["alignment_offset"] == 0.0
    assert payload["is_between_ball_and_goal"] is True
    assert payload["alignment_line"] == {"dx": -190.0, "dy": 0.0}
    assert payload["confidence"] == 0.3


def test_goalkeeper_ball_alignment_result_to_dict_with_none_detected() -> None:
    result = GoalkeeperBallAlignmentResult(
        frame_index=0, metadata=_metadata(),
        goalkeeper_detected=False, ball_detected=False, goal_detected=False,
        goalkeeper_position=None, ball_position=None, goal_center=None,
        goalkeeper_to_ball_distance=None, ball_to_goal_distance=None, goalkeeper_to_goal_distance=None,
        goalkeeper_ball_angle=None, ball_goal_angle=None, goalkeeper_goal_angle=None,
        alignment_offset=None, is_between_ball_and_goal=None,
        alignment_line=None, confidence=None,
    )

    payload = result.to_dict()

    assert payload["goalkeeper_position"] is None
    assert payload["alignment_line"] is None
    assert payload["is_between_ball_and_goal"] is None
    assert payload["confidence"] is None


def test_ball_motion_result_to_dict_with_motion() -> None:
    result = BallMotionResult(
        frame_index=2, metadata=_metadata(),
        ball_detected=True, current_position=Coordinate(x=20, y=10), previous_position=Coordinate(x=10, y=10),
        displacement=10.0, velocity=Vector(dx=10.0, dy=0.0), speed=10.0,
        direction_vector=Vector(dx=1.0, dy=0.0), direction_angle=0.0, acceleration=5.0,
        frames_observed=3, motion_detected=True, stationary=False, confidence=0.7,
    )

    payload = result.to_dict()

    assert payload["ball_detected"] is True
    assert payload["current_position"] == {"x": 20, "y": 10}
    assert payload["previous_position"] == {"x": 10, "y": 10}
    assert payload["displacement"] == 10.0
    assert payload["velocity"] == {"dx": 10.0, "dy": 0.0}
    assert payload["speed"] == 10.0
    assert payload["direction_vector"] == {"dx": 1.0, "dy": 0.0}
    assert payload["direction_angle"] == 0.0
    assert payload["acceleration"] == 5.0
    assert payload["frames_observed"] == 3
    assert payload["motion_detected"] is True
    assert payload["stationary"] is False
    assert payload["confidence"] == 0.7


def test_ball_motion_result_to_dict_without_ball() -> None:
    result = BallMotionResult(
        frame_index=0, metadata=_metadata(),
        ball_detected=False, current_position=None, previous_position=None,
        displacement=None, velocity=None, speed=None,
        direction_vector=None, direction_angle=None, acceleration=None,
        frames_observed=0, motion_detected=None, stationary=None, confidence=None,
    )

    payload = result.to_dict()

    assert payload["current_position"] is None
    assert payload["velocity"] is None
    assert payload["direction_vector"] is None
    assert payload["frames_observed"] == 0
    assert payload["confidence"] is None


def test_shot_analysis_result_to_dict_with_shot_detected() -> None:
    result = ShotAnalysisResult(
        frame_index=2, metadata=_metadata(),
        ball_detected=True, motion_detected=True, shot_detected=True, shot_start_frame=1,
        ball_speed=25.0, direction_vector=Vector(dx=-1.0, dy=0.0), direction_angle=180.0,
        towards_goal=True, distance_to_goal=240.0, observation_count=3, confidence=0.8,
    )

    payload = result.to_dict()

    assert payload["ball_detected"] is True
    assert payload["shot_detected"] is True
    assert payload["shot_start_frame"] == 1
    assert payload["ball_speed"] == 25.0
    assert payload["direction_vector"] == {"dx": -1.0, "dy": 0.0}
    assert payload["towards_goal"] is True
    assert payload["distance_to_goal"] == 240.0
    assert payload["observation_count"] == 3
    assert payload["confidence"] == 0.8


def test_shot_analysis_result_to_dict_without_ball() -> None:
    result = ShotAnalysisResult(
        frame_index=0, metadata=_metadata(),
        ball_detected=False, motion_detected=None, shot_detected=False, shot_start_frame=None,
        ball_speed=None, direction_vector=None, direction_angle=None,
        towards_goal=None, distance_to_goal=None, observation_count=0, confidence=None,
    )

    payload = result.to_dict()

    assert payload["shot_detected"] is False
    assert payload["direction_vector"] is None
    assert payload["confidence"] is None


def test_ball_trajectory_result_to_dict_with_trajectory() -> None:
    result = BallTrajectoryResult(
        frame_index=2, metadata=_metadata(),
        ball_detected=True, trajectory_detected=True,
        trajectory_points=[Coordinate(x=300, y=250), Coordinate(x=275, y=250), Coordinate(x=250, y=250)],
        trajectory_length=50.0, dominant_direction=180.0,
        average_velocity=Vector(dx=-25.0, dy=0.0), direction_consistency=1.0,
        direction_changes=0, linearity_score=1.0, frames_observed=3, confidence=0.8,
    )

    payload = result.to_dict()

    assert payload["ball_detected"] is True
    assert payload["trajectory_detected"] is True
    assert payload["trajectory_points"] == [
        {"x": 300, "y": 250}, {"x": 275, "y": 250}, {"x": 250, "y": 250},
    ]
    assert payload["trajectory_length"] == 50.0
    assert payload["dominant_direction"] == 180.0
    assert payload["average_velocity"] == {"dx": -25.0, "dy": 0.0}
    assert payload["direction_consistency"] == 1.0
    assert payload["direction_changes"] == 0
    assert payload["linearity_score"] == 1.0
    assert payload["frames_observed"] == 3
    assert payload["confidence"] == 0.8


def test_ball_trajectory_result_to_dict_without_ball() -> None:
    result = BallTrajectoryResult(
        frame_index=0, metadata=_metadata(),
        ball_detected=False, trajectory_detected=False, trajectory_points=None,
        trajectory_length=None, dominant_direction=None, average_velocity=None,
        direction_consistency=None, direction_changes=0, linearity_score=None,
        frames_observed=0, confidence=None,
    )

    payload = result.to_dict()

    assert payload["trajectory_detected"] is False
    assert payload["trajectory_points"] is None
    assert payload["average_velocity"] is None
    assert payload["confidence"] is None


def test_play_situation_result_to_dict_with_shot_detected() -> None:
    result = PlaySituationResult(
        frame_index=2, metadata=_metadata(),
        situation=PlaySituation.SHOT_DETECTED, sub_state=PlaySituation.SHOT_TOWARDS_GOAL,
        ball_detected=True, goalkeeper_detected=True, shot_detected=True,
        trajectory_detected=True, alignment_detected=True, confidence=0.8,
    )

    payload = result.to_dict()

    assert payload["situation"] == "shot_detected"
    assert payload["sub_state"] == "shot_towards_goal"
    assert payload["ball_detected"] is True
    assert payload["goalkeeper_detected"] is True
    assert payload["shot_detected"] is True
    assert payload["trajectory_detected"] is True
    assert payload["alignment_detected"] is True
    assert payload["confidence"] == 0.8


def test_play_situation_result_to_dict_without_ball() -> None:
    result = PlaySituationResult(
        frame_index=0, metadata=_metadata(),
        situation=PlaySituation.NO_BALL_VISIBLE, sub_state=None,
        ball_detected=False, goalkeeper_detected=False, shot_detected=False,
        trajectory_detected=False, alignment_detected=False, confidence=None,
    )

    payload = result.to_dict()

    assert payload["situation"] == "no_ball_visible"
    assert payload["sub_state"] is None
    assert payload["confidence"] is None


def test_goalkeeper_decision_result_to_dict_with_dive() -> None:
    result = GoalkeeperDecisionResult(
        frame_index=2, metadata=_metadata(),
        decision=GoalkeeperDecision.DIVE_RIGHT, play_situation=PlaySituation.SHOT_DETECTED,
        ball_detected=True, goalkeeper_detected=True,
        goalkeeper_position=Coordinate(x=50, y=280), movement_direction=Vector(dx=0.0, dy=30.0),
        movement_speed=30.0, ball_direction=180.0, alignment=True, confidence=0.7,
    )

    payload = result.to_dict()

    assert payload["decision"] == "dive_right"
    assert payload["play_situation"] == "shot_detected"
    assert payload["goalkeeper_position"] == {"x": 50, "y": 280}
    assert payload["movement_direction"] == {"dx": 0.0, "dy": 30.0}
    assert payload["movement_speed"] == 30.0
    assert payload["ball_direction"] == 180.0
    assert payload["alignment"] is True
    assert payload["confidence"] == 0.7


def test_goalkeeper_decision_result_to_dict_without_goalkeeper() -> None:
    result = GoalkeeperDecisionResult(
        frame_index=0, metadata=_metadata(),
        decision=GoalkeeperDecision.UNKNOWN, play_situation=PlaySituation.NO_GOALKEEPER_VISIBLE,
        ball_detected=True, goalkeeper_detected=False,
        goalkeeper_position=None, movement_direction=None, movement_speed=None,
        ball_direction=None, alignment=None, confidence=None,
    )

    payload = result.to_dict()

    assert payload["decision"] == "unknown"
    assert payload["goalkeeper_position"] is None
    assert payload["movement_direction"] is None
    assert payload["confidence"] is None


def test_goalkeeper_decision_evaluation_result_to_dict_compatible() -> None:
    result = GoalkeeperDecisionEvaluationResult(
        frame_index=2, metadata=_metadata(),
        evaluation=GoalkeeperDecisionEvaluation.COMPATIBLE,
        play_situation=PlaySituation.SHOT_DETECTED, goalkeeper_decision=GoalkeeperDecision.DIVE_RIGHT,
        rules_evaluated=["actors_visible", "decision_established", "shot_prompts_active_response"],
        rules_passed=["actors_visible", "decision_established", "shot_prompts_active_response"],
        rules_failed=[], explanations=["[actors_visible] ... -> satisfeita"], confidence=0.7,
    )

    payload = result.to_dict()

    assert payload["evaluation"] == "compatible"
    assert payload["play_situation"] == "shot_detected"
    assert payload["goalkeeper_decision"] == "dive_right"
    assert payload["rules_evaluated"] == ["actors_visible", "decision_established", "shot_prompts_active_response"]
    assert payload["rules_passed"] == ["actors_visible", "decision_established", "shot_prompts_active_response"]
    assert payload["rules_failed"] == []
    assert payload["explanations"] == ["[actors_visible] ... -> satisfeita"]
    assert payload["confidence"] == 0.7


def test_goalkeeper_decision_evaluation_result_to_dict_insufficient_information() -> None:
    result = GoalkeeperDecisionEvaluationResult(
        frame_index=0, metadata=_metadata(),
        evaluation=GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION,
        play_situation=PlaySituation.NO_BALL_VISIBLE, goalkeeper_decision=GoalkeeperDecision.UNKNOWN,
        rules_evaluated=["actors_visible"], rules_passed=[], rules_failed=["actors_visible"],
        explanations=["[actors_visible] ... -> violada"], confidence=None,
    )

    payload = result.to_dict()

    assert payload["evaluation"] == "insufficient_information"
    assert payload["rules_failed"] == ["actors_visible"]
    assert payload["confidence"] is None


def test_play_outcome_result_to_dict_with_goal() -> None:
    result = PlayOutcomeResult(
        frame_index=2, metadata=_metadata(),
        outcome=PlayOutcome.GOAL, play_situation=PlaySituation.SHOT_DETECTED, shot_detected=True,
        ball_detected=True, goalkeeper_detected=True, ball_visible=True, goal_visible=True,
        ball_last_position=Coordinate(x=10, y=250), goalkeeper_last_position=Coordinate(x=50, y=250),
        supporting_evidence=["chute detectado", "posicao da bola dentro da zona do gol"], confidence=0.7,
    )

    payload = result.to_dict()

    assert payload["outcome"] == "goal"
    assert payload["play_situation"] == "shot_detected"
    assert payload["shot_detected"] is True
    assert payload["ball_last_position"] == {"x": 10, "y": 250}
    assert payload["goalkeeper_last_position"] == {"x": 50, "y": 250}
    assert payload["supporting_evidence"] == ["chute detectado", "posicao da bola dentro da zona do gol"]
    assert payload["confidence"] == 0.7


def test_play_outcome_result_to_dict_without_ball() -> None:
    result = PlayOutcomeResult(
        frame_index=0, metadata=_metadata(),
        outcome=PlayOutcome.INSUFFICIENT_INFORMATION, play_situation=PlaySituation.NO_BALL_VISIBLE,
        shot_detected=False, ball_detected=False, goalkeeper_detected=False, ball_visible=False,
        goal_visible=True, ball_last_position=None, goalkeeper_last_position=None,
        supporting_evidence=["bola nao detectada"], confidence=None,
    )

    payload = result.to_dict()

    assert payload["outcome"] == "insufficient_information"
    assert payload["ball_last_position"] is None
    assert payload["confidence"] is None


def test_goalkeeper_performance_evaluation_result_to_dict_excellent() -> None:
    result = GoalkeeperPerformanceEvaluationResult(
        frame_index=2, metadata=_metadata(),
        performance=GoalkeeperPerformanceEvaluation.EXCELLENT,
        decision_evaluation=GoalkeeperDecisionEvaluation.COMPATIBLE, play_outcome=PlayOutcome.SAVE,
        rules_evaluated=["actors_and_geometry_available", "decisive_event_established"],
        rules_passed=["actors_and_geometry_available", "decisive_event_established"],
        rules_failed=[], summary="performance=excellent; decision_evaluation=compatible; play_outcome=save",
        confidence=0.7,
    )

    payload = result.to_dict()

    assert payload["performance"] == "excellent"
    assert payload["decision_evaluation"] == "compatible"
    assert payload["play_outcome"] == "save"
    assert payload["summary"] == "performance=excellent; decision_evaluation=compatible; play_outcome=save"
    assert payload["confidence"] == 0.7


def test_goalkeeper_performance_evaluation_result_to_dict_insufficient_information() -> None:
    result = GoalkeeperPerformanceEvaluationResult(
        frame_index=0, metadata=_metadata(),
        performance=GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION,
        decision_evaluation=GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION,
        play_outcome=PlayOutcome.INSUFFICIENT_INFORMATION,
        rules_evaluated=["actors_and_geometry_available"], rules_passed=[],
        rules_failed=["actors_and_geometry_available"], summary="performance=insufficient_information; ...",
        confidence=None,
    )

    payload = result.to_dict()

    assert payload["performance"] == "insufficient_information"
    assert payload["rules_failed"] == ["actors_and_geometry_available"]
    assert payload["confidence"] is None


def test_goalkeeper_coaching_result_to_dict_attack_ball() -> None:
    result = GoalkeeperCoachingResult(
        frame_index=2, metadata=_metadata(),
        coaching=GoalkeeperCoaching.ATTACK_BALL,
        performance=GoalkeeperPerformanceEvaluation.CRITICAL,
        decision_evaluation=GoalkeeperDecisionEvaluation.INCOMPATIBLE,
        decision=GoalkeeperDecision.STAY_ON_LINE, outcome=PlayOutcome.GOAL,
        rules_evaluated=["evaluation_available", "decisive_performance_established"],
        rules_passed=["evaluation_available", "decisive_performance_established"],
        rules_failed=[], summary="coaching=attack_ball; performance=critical; decision=stay_on_line; outcome=goal",
        confidence=0.6,
    )

    payload = result.to_dict()

    assert payload["coaching"] == "attack_ball"
    assert payload["performance"] == "critical"
    assert payload["decision"] == "stay_on_line"
    assert payload["outcome"] == "goal"
    assert payload["summary"] == "coaching=attack_ball; performance=critical; decision=stay_on_line; outcome=goal"
    assert payload["confidence"] == 0.6


def test_goalkeeper_coaching_result_to_dict_insufficient_information() -> None:
    result = GoalkeeperCoachingResult(
        frame_index=0, metadata=_metadata(),
        coaching=GoalkeeperCoaching.INSUFFICIENT_INFORMATION,
        performance=GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION,
        decision_evaluation=GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION,
        decision=GoalkeeperDecision.UNKNOWN, outcome=PlayOutcome.INSUFFICIENT_INFORMATION,
        rules_evaluated=["evaluation_available"], rules_passed=[],
        rules_failed=["evaluation_available"], summary="coaching=insufficient_information; ...",
        confidence=None,
    )

    payload = result.to_dict()

    assert payload["coaching"] == "insufficient_information"
    assert payload["rules_failed"] == ["evaluation_available"]
    assert payload["confidence"] is None


def _play_situation_result() -> PlaySituationResult:
    return PlaySituationResult(
        frame_index=0, metadata=_metadata(),
        situation=PlaySituation.SHOT_DETECTED, sub_state=PlaySituation.SHOT_TOWARDS_GOAL,
        ball_detected=True, goalkeeper_detected=True, shot_detected=True,
        trajectory_detected=True, alignment_detected=True, confidence=0.9,
    )


def _goalkeeper_decision_result() -> GoalkeeperDecisionResult:
    return GoalkeeperDecisionResult(
        frame_index=0, metadata=_metadata(),
        decision=GoalkeeperDecision.DIVE_LEFT, play_situation=PlaySituation.SHOT_DETECTED,
        ball_detected=True, goalkeeper_detected=True, goalkeeper_position=None,
        movement_direction=None, movement_speed=20.0, ball_direction=None, alignment=True,
        confidence=0.85,
    )


def _goalkeeper_decision_evaluation_result() -> GoalkeeperDecisionEvaluationResult:
    return GoalkeeperDecisionEvaluationResult(
        frame_index=0, metadata=_metadata(),
        evaluation=GoalkeeperDecisionEvaluation.COMPATIBLE, play_situation=PlaySituation.SHOT_DETECTED,
        goalkeeper_decision=GoalkeeperDecision.DIVE_LEFT,
        rules_evaluated=["actors_visible"], rules_passed=["actors_visible"], rules_failed=[],
        explanations=["[actors_visible] ... -> satisfeita"], confidence=0.8,
    )


def _play_outcome_result() -> PlayOutcomeResult:
    return PlayOutcomeResult(
        frame_index=0, metadata=_metadata(),
        outcome=PlayOutcome.SAVE, play_situation=PlaySituation.SHOT_DETECTED,
        shot_detected=True, ball_detected=True, goalkeeper_detected=True,
        ball_visible=True, goal_visible=True, ball_last_position=None, goalkeeper_last_position=None,
        supporting_evidence=["chute detectado"], confidence=0.75,
    )


def _goalkeeper_performance_evaluation_result() -> GoalkeeperPerformanceEvaluationResult:
    return GoalkeeperPerformanceEvaluationResult(
        frame_index=0, metadata=_metadata(),
        performance=GoalkeeperPerformanceEvaluation.EXCELLENT,
        decision_evaluation=GoalkeeperDecisionEvaluation.COMPATIBLE, play_outcome=PlayOutcome.SAVE,
        rules_evaluated=["actors_and_geometry_available"], rules_passed=["actors_and_geometry_available"],
        rules_failed=[], summary="performance=excellent; ...", confidence=0.7,
    )


def _goalkeeper_coaching_result() -> GoalkeeperCoachingResult:
    return GoalkeeperCoachingResult(
        frame_index=0, metadata=_metadata(),
        coaching=GoalkeeperCoaching.NO_FEEDBACK,
        performance=GoalkeeperPerformanceEvaluation.EXCELLENT,
        decision_evaluation=GoalkeeperDecisionEvaluation.COMPATIBLE,
        decision=GoalkeeperDecision.DIVE_LEFT, outcome=PlayOutcome.SAVE,
        rules_evaluated=["evaluation_available"], rules_passed=["evaluation_available"],
        rules_failed=[], summary="coaching=no_feedback; ...", confidence=0.65,
    )


def test_goalkeeper_analysis_report_to_dict_preserves_every_sub_result() -> None:
    play_situation = _play_situation_result()
    goalkeeper_decision = _goalkeeper_decision_result()
    decision_evaluation = _goalkeeper_decision_evaluation_result()
    play_outcome = _play_outcome_result()
    performance_evaluation = _goalkeeper_performance_evaluation_result()
    coaching = _goalkeeper_coaching_result()

    report = GoalkeeperAnalysisReport(
        frame_index=0, metadata=_metadata(),
        play_situation=play_situation, goalkeeper_decision=goalkeeper_decision,
        decision_evaluation=decision_evaluation, play_outcome=play_outcome,
        performance_evaluation=performance_evaluation, coaching=coaching,
        confidence_summary={"play_situation": 0.9, "overall": 0.65},
        artifacts={"play_situation": play_situation.to_dict()},
        analysis_version="1.0.0", worker_version="0.1.0", generated_at="2026-07-23T00:00:00+00:00",
    )

    payload = report.to_dict()

    assert payload["play_situation"] == play_situation.to_dict()
    assert payload["goalkeeper_decision"] == goalkeeper_decision.to_dict()
    assert payload["decision_evaluation"] == decision_evaluation.to_dict()
    assert payload["play_outcome"] == play_outcome.to_dict()
    assert payload["performance_evaluation"] == performance_evaluation.to_dict()
    assert payload["coaching"] == coaching.to_dict()
    # Explainability integralmente preservada - nada foi removido/reconstruido
    assert payload["decision_evaluation"]["rules_evaluated"] == ["actors_visible"]
    assert payload["decision_evaluation"]["explanations"] == ["[actors_visible] ... -> satisfeita"]
    assert payload["performance_evaluation"]["summary"] == "performance=excellent; ..."
    assert payload["coaching"]["summary"] == "coaching=no_feedback; ..."
    assert payload["analysis_version"] == "1.0.0"
    assert payload["worker_version"] == "0.1.0"
    assert payload["generated_at"] == "2026-07-23T00:00:00+00:00"


def test_analysis_statistics_to_dict() -> None:
    stats = AnalysisStatistics(analyzers_run=["goalkeeper_presence"], results_count=1)
    assert stats.to_dict() == {"analyzers_run": ["goalkeeper_presence"], "results_count": 1}


def test_goal_geometry_result_to_dict_with_goal() -> None:
    result = GoalGeometryResult(
        frame_index=3, metadata=_metadata(),
        goal_detected=True, goal_center=Coordinate(x=50, y=20),
        goal_width=100.0, goal_height=40.0,
        left_post=Coordinate(x=0, y=0), right_post=Coordinate(x=100, y=0),
        goal_regions={GoalZone.TOP_LEFT: Region(x=0, y=0, width=33.3, height=20)},
        confidence=1.0,
    )

    payload = result.to_dict()

    assert payload["goal_detected"] is True
    assert payload["goal_center"] == {"x": 50, "y": 20}
    assert payload["goal_width"] == 100.0
    assert payload["goal_height"] == 40.0
    assert payload["left_post"] == {"x": 0, "y": 0}
    assert payload["right_post"] == {"x": 100, "y": 0}
    assert payload["goal_regions"]["top_left"] == {"x": 0, "y": 0, "width": 33.3, "height": 20}
    assert payload["confidence"] == 1.0


def test_goal_geometry_result_to_dict_without_goal() -> None:
    result = GoalGeometryResult(
        frame_index=0, metadata=_metadata(),
        goal_detected=False, goal_center=None, goal_width=None, goal_height=None,
        left_post=None, right_post=None, goal_regions=None, confidence=None,
    )

    payload = result.to_dict()

    assert payload["goal_detected"] is False
    assert payload["goal_center"] is None
    assert payload["goal_regions"] is None
    assert payload["confidence"] is None
