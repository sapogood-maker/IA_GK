"""API de Detecção — abstração `Detector`, independente de qualquer
framework/modelo concreto (Sprint W8).

`YOLODetector` é apenas a primeira implementação. Trocar YOLO por
RT-DETR/GroundingDINO/OWLv2 no futuro exige apenas escrever uma nova
classe que implemente `Detector` e registrá-la — nenhuma mudança em
`YOLOProcessor`, `PipelineProcessor`, `BasicVisionEngine` ou no restante
do Worker."""
