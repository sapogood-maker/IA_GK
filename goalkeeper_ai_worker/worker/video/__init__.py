"""Infraestrutura de leitura de vídeo (Sprint W5) — reutilizada por todo
motor de inferência futuro.

`VideoReader` é infraestrutura, nunca IA. OpenCV é usado exclusivamente
como biblioteca de leitura (`cv2.VideoCapture`) — nenhuma linha de
`cv2.dnn`, YOLO, modelo ou GPU vive aqui. `worker/inference/` conhece
apenas `FrameProvider`/`FrameIterator` — nunca abre um arquivo de vídeo
diretamente.
"""
