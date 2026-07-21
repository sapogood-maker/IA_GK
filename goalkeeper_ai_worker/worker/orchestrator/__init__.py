"""Executa o Pipeline: decide a transicao entre Stages e aplica a politica
de timeout/retry/cancelamento (AI_WORKER_CONSTITUTION.md, Secao 1 e 5).

Nao conhece R2 nem qual Plugin esta ativo - so orquestra a sequencia
declarada em `worker.pipeline`. Vazio ate a Sprint W3.
"""
