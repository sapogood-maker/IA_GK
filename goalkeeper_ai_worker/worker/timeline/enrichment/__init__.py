"""Perception Enrichment (Sprint W31) - subpacote de worker/timeline/.

Deriva NOVOS Events (mesma classe `worker.timeline.event.Event`, sem
alteracoes de schema) a partir de relacoes temporais entre eventos ja
existentes na Perception Timeline (W28) - transicoes de estado, padroes
de frequencia, correlacoes dentro do mesmo frame. Nunca decide, nunca
julga - continua sendo fato de percepcao, nao cognicao.

Vive DENTRO de worker/timeline/ (nao como pacote irmao) de proposito: e
uma extensao natural do que a Timeline representa, nao um dominio a
parte. Nenhum arquivo ja existente em worker/timeline/ (event.py,
event_types.py, timeline.py, builder.py) e alterado - so esta pasta e
nova. Consome (nunca modifica) worker.explorers.timeline_explorer.
TimelineExplorer e worker.segments.play_segment.PlaySegment como dados
de entrada.

Ver PERCEPTION_ENGINE_ARCHITECTURE.md e o documento arquitetural da
Sprint W31 para o raciocinio completo por tras de cada decisao aqui.
"""
