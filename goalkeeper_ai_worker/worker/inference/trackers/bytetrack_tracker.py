"""ByteTrackTracker: primeira implementação real de `Tracker`, usando o
algoritmo ByteTrack (via a implementação já vendorizada pela Ultralytics -
`ultralytics.trackers.byte_tracker.BYTETracker`).

Todo código específico de ByteTrack (o adaptador que traduz nosso
`DetectionResult` para o formato que `BYTETracker.update()` espera, e a
tradução de volta para `TrackingResult`) fica exclusivamente aqui -
nenhuma outra parte do Worker sabe que ByteTrack existe."""
from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
from ultralytics.trackers.byte_tracker import BYTETracker

from worker.config.settings import WorkerSettings
from worker.inference.detectors.types import DetectionResult
from worker.inference.trackers.base import Tracker
from worker.inference.trackers.exceptions import TrackerExecutionError
from worker.inference.trackers.types import (
    BoundingBox,
    ClassLabel,
    Confidence,
    TrackedObject,
    TrackId,
    TrackingResult,
    TrackingStatistics,
    TrackState,
)


class _DetectionsAdapter:
    """Objeto "results-like" mínimo exigido por `BYTETracker.update()` -
    expõe `xywh`/`conf`/`cls` e suporta indexação booleana, sem depender
    de nenhum tipo do pacote `ultralytics.engine.results`."""

    def __init__(self, xywh: np.ndarray, conf: np.ndarray, cls: np.ndarray) -> None:
        self.xywh = xywh
        self.conf = conf
        self.cls = cls

    def __len__(self) -> int:
        return len(self.conf)

    def __getitem__(self, mask: np.ndarray) -> "_DetectionsAdapter":
        return _DetectionsAdapter(self.xywh[mask], self.conf[mask], self.cls[mask])


def _to_results_like(detections: DetectionResult) -> _DetectionsAdapter:
    count = len(detections.detections)
    xywh = np.zeros((count, 4), dtype=np.float32)
    conf = np.zeros(count, dtype=np.float32)
    cls = np.zeros(count, dtype=np.float32)
    for i, detection in enumerate(detections.detections):
        bbox = detection.bbox
        xywh[i] = (bbox.x + bbox.width / 2, bbox.y + bbox.height / 2, bbox.width, bbox.height)
        conf[i] = detection.confidence
    return _DetectionsAdapter(xywh, conf, cls)


class ByteTrackTracker(Tracker):
    """Tracker de objetos baseado no algoritmo ByteTrack."""

    name = "bytetrack"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        args = SimpleNamespace(
            track_high_thresh=settings.track_min_confidence,
            track_low_thresh=0.1,
            new_track_thresh=settings.track_min_confidence,
            track_buffer=settings.track_max_age,
            match_thresh=0.8,
            fuse_score=True,
        )
        self._tracker = BYTETracker(args)
        self._min_hits = settings.track_min_hits
        self._hit_counts: dict[int, int] = {}

    def track(self, detections: DetectionResult) -> TrackingResult:
        start = time.monotonic()
        try:
            results_like = _to_results_like(detections)
            raw = self._tracker.update(results_like)
        except Exception as exc:
            raise TrackerExecutionError(f"Falha na atualizacao do ByteTrack: {exc}") from exc
        duration_ms = (time.monotonic() - start) * 1000

        tracked_objects: list[TrackedObject] = []
        for row in raw:
            x1, y1, x2, y2, track_id, score, _cls, idx = row[:8]
            track_id_int = int(track_id)
            self._hit_counts[track_id_int] = self._hit_counts.get(track_id_int, 0) + 1
            age = self._hit_counts[track_id_int]
            if age < self._min_hits:
                continue

            label = detections.detections[int(idx)].label if detections.detections else ClassLabel("")
            tracked_objects.append(
                TrackedObject(
                    track_id=TrackId(track_id_int),
                    label=ClassLabel(label),
                    confidence=Confidence(float(score)),
                    bbox=BoundingBox(
                        x=int(x1), y=int(y1), width=int(x2 - x1), height=int(y2 - y1)
                    ),
                    age=age,
                    state=TrackState.NEW if age == 1 else TrackState.TRACKED,
                    frame_index=0,
                )
            )

        statistics = TrackingStatistics(
            total_tracks=len(self._hit_counts),
            active_tracks=len(raw),
            lost_tracks=len(self._tracker.lost_stracks),
            removed_tracks=len(self._tracker.removed_stracks),
        )
        return TrackingResult(
            tracked_objects=tracked_objects,
            tracker_name=self.name,
            tracker_version=self.version,
            duration_ms=duration_ms,
            statistics=statistics,
        )

    def reset(self) -> None:
        self._tracker.reset()
        self._hit_counts.clear()
