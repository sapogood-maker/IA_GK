"""normalize_entity_label: funcao pura que resolve a inconsistencia de
rotulo entre familias de evento da Timeline (Sprint W31, achado do
documento arquitetural, Secao 3).

`ObjectDetected`/`BallDetected`/`PersonDetected` (worker/timeline/builder.py)
ja usam rotulo NORMALIZADO (`"ball"`, `"person"`). `TrackStarted`/
`TrackUpdated`/etc. (eventos de cena) usam o rotulo BRUTO do YOLO
(`scene_event.label`, ex. `"sports ball"`) - sem essa normalizacao, um
Enricher nao consegue reconhecer "isto e a bola" nas duas familias com
uma simples comparacao de string. Nao mexe em `worker/timeline/` - so
resolve a inconsistencia do lado de quem consome.
"""
from __future__ import annotations

_LABEL_ALIASES: dict[str, str] = {
    "sports ball": "ball",
}


def normalize_entity_label(label: str | None) -> str | None:
    """Rotulo desconhecido passa adiante sem erro (nunca falha por um
    rotulo novo que o Detector venha a emitir no futuro - ex. quando o
    Detector for fine-tunado, W37, e passar a emitir `"goalkeeper"`
    diretamente, que ja e sua propria forma normalizada)."""
    if label is None:
        return None
    return _LABEL_ALIASES.get(label, label)
