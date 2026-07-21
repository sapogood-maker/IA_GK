"""Contratos publicos do Backend, do ponto de vista do Worker.

Este pacote representa exclusivamente o formato dos dados trocados nos
tres canais permitidos pelo Boundary Enforcement (REST API e Redis - R2 e
tratado via URL assinada, sem payload proprio). Nenhum tipo aqui importa
`app/schemas/schemas.py` do backend: cada estrutura e definida de forma
independente, mesmo que duplique campos - e exatamente o que o Boundary
Enforcement exige para "Compartilhamento de Schemas".
"""
