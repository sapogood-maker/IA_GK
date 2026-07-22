"""Testes de worker.inference.frame_ops - operações puras de pré-processamento."""
from __future__ import annotations

import numpy as np

from worker.inference.frame_ops import apply_roi, convert_bgr_to_rgb, resize_frame
from worker.inference.types import RegionOfInterest
from worker.video.frame import Frame
from worker.video.metadata import FrameMetadata


def _make_frame(width: int = 64, height: int = 48) -> Frame:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :, 0] = 255  # canal B = 255 (azul puro em BGR)
    metadata = FrameMetadata(
        frame_index=0,
        timestamp_seconds=0.0,
        position_seconds=0.0,
        fps=10.0,
        width=width,
        height=height,
        duration_seconds=1.0,
    )
    return Frame(image=image, metadata=metadata)


def test_convert_bgr_to_rgb_swaps_channels() -> None:
    frame = _make_frame()

    result = convert_bgr_to_rgb(frame)

    assert result.image[0, 0, 0] == 0
    assert result.image[0, 0, 2] == 255
    assert result.metadata == frame.metadata


def test_resize_frame_changes_dimensions_and_metadata() -> None:
    frame = _make_frame(width=64, height=48)

    result = resize_frame(frame, target_width=32, target_height=24)

    assert result.image.shape[1] == 32
    assert result.image.shape[0] == 24
    assert result.metadata.width == 32
    assert result.metadata.height == 24
    assert result.metadata.frame_index == frame.metadata.frame_index


def test_apply_roi_crops_the_image_and_updates_metadata() -> None:
    frame = _make_frame(width=64, height=48)
    roi = RegionOfInterest(x=10, y=5, width=20, height=15)

    result = apply_roi(frame, roi)

    assert result.image.shape == (15, 20, 3)
    assert result.metadata.width == 20
    assert result.metadata.height == 15


def test_frame_ops_never_mutate_the_original_frame() -> None:
    frame = _make_frame()
    original_image_copy = frame.image.copy()

    convert_bgr_to_rgb(frame)
    resize_frame(frame, 10, 10)
    apply_roi(frame, RegionOfInterest(x=0, y=0, width=5, height=5))

    assert np.array_equal(frame.image, original_image_copy)
