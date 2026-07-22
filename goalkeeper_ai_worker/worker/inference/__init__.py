"""Camada de inferencia do Worker - unico lugar onde codigo de visao
computacional pode existir (Sprint W4: so FakeInferenceEngine).

Pipeline, Orchestrator, Workspace e infrastructure/{redis,backend_client,
storage} nunca conhecem OpenCV/YOLO/PyTorch - so o contrato
`InferenceEngine.process(state)` (`base.py`). Trocar de motor e escrever
uma nova classe aqui, registra-la (`registry.py`) e apontar
WORKER_INFERENCE_ENGINE para o novo nome - nenhum outro modulo do Worker
precisa mudar.
"""
