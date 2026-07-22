"""Operações genéricas de pré-processamento de frame - reutilizáveis por
qualquer motor de inferência (não só `BasicVisionEngine`), preparadas para
a W7 reaproveitar sem duplicar lógica.

Puras: recebem um `Frame` e devolvem um novo `Frame` — nunca mutam o
original (`Frame`/`FrameMetadata` são `frozen=True`). Nenhuma lógica de
detecção/IA aqui — só normalização de imagem.
"""
from __future__ import annotations

import cv2

from worker.inference.types import RegionOfInterest
from worker.video.frame import Frame
from worker.video.metadata import FrameMetadata


def convert_bgr_to_rgb(frame: Frame) -> Frame:
    """Converte a imagem de BGR (formato nativo do OpenCV) para RGB."""
    rgb_image = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
    return Frame(image=rgb_image, metadata=frame.metadata)


def resize_frame(frame: Frame, target_width: int, target_height: int) -> Frame:
    """Redimensiona a imagem do frame para as dimensões alvo."""
    resized_image = cv2.resize(frame.image, (target_width, target_height))
    metadata = FrameMetadata(
        frame_index=frame.metadata.frame_index,
        timestamp_seconds=frame.metadata.timestamp_seconds,
        position_seconds=frame.metadata.position_seconds,
        fps=frame.metadata.fps,
        width=target_width,
        height=target_height,
        duration_seconds=frame.metadata.duration_seconds,
    )
    return Frame(image=resized_image, metadata=metadata)


def apply_roi(frame: Frame, roi: RegionOfInterest) -> Frame:
    """Recorta a imagem do frame para a região de interesse configurada."""
    cropped_image = frame.image[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
    metadata = FrameMetadata(
        frame_index=frame.metadata.frame_index,
        timestamp_seconds=frame.metadata.timestamp_seconds,
        position_seconds=frame.metadata.position_seconds,
        fps=frame.metadata.fps,
        width=roi.width,
        height=roi.height,
        duration_seconds=frame.metadata.duration_seconds,
    )
    return Frame(image=cropped_image, metadata=metadata)
