"""Checkpoint efemero local do Job em andamento (AI_WORKER_CONSTITUTION.md,
Secao 3 e 5) - permite retomar da ultima etapa concluida apos um crash do
processo, em vez de recomecar do zero.

Nao e um banco de dados de producao - e um estado local, descartavel,
por Job. Vazio ate a Sprint W3.
"""
