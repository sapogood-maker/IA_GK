"""API de Tracking — abstração `Tracker`, independente de qualquer
biblioteca/algoritmo concreto (Sprint W9).

`ByteTrackTracker` é apenas a primeira implementação. Trocar ByteTrack
por BoT-SORT/DeepSORT/StrongSORT/OC-SORT no futuro exige apenas escrever
uma nova classe que implemente `Tracker` e registrá-la — nenhuma mudança
em `TrackingProcessor`, `PipelineProcessor`, `BasicVisionEngine`,
`Detector` ou `YOLOProcessor`.

Tracking nunca conhece Detecção: `Tracker.track()` recebe apenas um
`DetectionResult` (o contrato de saída de QUALQUER Detector, não algo
específico do YOLO) e produz objetos persistentes entre frames."""
