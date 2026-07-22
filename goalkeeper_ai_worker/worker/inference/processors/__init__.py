"""Processors de frame — cada transformação/medição isolada em uma classe
própria, nunca concentrada num único método (Sprint W7).

Nenhum Processor conhece outro Processor. `PipelineProcessor` (`pipeline.py`)
executa a sequência de Processors habilitados; `registry.py` decide quais
existem e podem ser habilitados via configuração, sem alterar código.
"""
