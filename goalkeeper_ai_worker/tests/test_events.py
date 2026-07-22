"""Testes de worker.events.events - por enquanto so confirmam que emit() loga
sem levantar excecao e que os dataclasses carregam os campos esperados."""
from __future__ import annotations

import logging

import pytest

from worker.events.events import JobCompleted, JobFailed, JobStarted, emit


def test_emit_logs_the_event_name_and_fields(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        emit(JobStarted(job_id="job-1", video_id="video-1"))

    assert "JobStarted" in caplog.text
    assert "job-1" in caplog.text
    assert "video-1" in caplog.text


def test_job_completed_event_fields() -> None:
    event = JobCompleted(job_id="job-1", video_id="video-1")
    assert event.job_id == "job-1"
    assert event.video_id == "video-1"


def test_job_failed_event_carries_error_message() -> None:
    event = JobFailed(job_id="job-1", video_id="video-1", error="algo deu errado")
    assert event.error == "algo deu errado"
