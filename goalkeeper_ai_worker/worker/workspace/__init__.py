"""Gerencia o diretorio de trabalho temporario de um Job (criacao/limpeza).

Distinto do diretorio de dados `goalkeeper_ai_worker/workspace/` (raiz do
projeto, nao versionado no git) - este modulo e o CODIGO que cria,
organiza e limpa subpastas dentro daquele diretorio, uma por Job em
andamento; o diretorio em si nao e o modulo.

Nao decide o que gravar ali - so oferece o espaco. Vazio ate a Sprint W3.
"""
