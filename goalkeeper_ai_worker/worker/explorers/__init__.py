"""Explorers (Sprint W29) - ferramentas de observabilidade sobre artifacts
ja gerados pelo Worker. Puramente leitura/relatorio - nenhuma classe aqui
decide nada nem altera o artifact original.

`TimelineExplorer` e o primeiro - opera sobre o artifact.json inteiro
(nao so `event_timeline`) de proposito: um futuro `ArtifactExplorer`
(irmao neste mesmo pacote) pode compor/reutilizar a mesma representacao
sem recarregar nada. Ver PERCEPTION_ENGINE_ARCHITECTURE.md.
"""
