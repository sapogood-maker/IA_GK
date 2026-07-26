"""Testes de worker.evaluation.evaluation_set.EvaluationSet."""
from __future__ import annotations

import dataclasses

import pytest

from worker.evaluation.evaluation_set import EvaluationSet
from worker.evaluation.resolution_method import ResolutionMethod
from worker.evaluation.track_evaluation import TrackEvaluation


def _track_evaluation(track_id: int) -> TrackEvaluation:
    return TrackEvaluation(track_id=track_id, resolution_method=ResolutionMethod.SINGLE_CANDIDATE)


def test_is_frozen_immutable():
    evaluation_set = EvaluationSet()
    with pytest.raises(dataclasses.FrozenInstanceError):
        evaluation_set.observed_at_frame = 99  # type: ignore[misc]


def test_defaults_produce_empty_set_not_errors():
    payload = EvaluationSet().to_dict()
    assert payload["track_evaluations"] == {}
    assert payload["entity_evaluations"] == {}


def test_to_dict_sorts_track_evaluations_by_track_id():
    evaluation_set = EvaluationSet(track_evaluations={3: _track_evaluation(3), 1: _track_evaluation(1)})
    assert list(evaluation_set.to_dict()["track_evaluations"].keys()) == [1, 3]
