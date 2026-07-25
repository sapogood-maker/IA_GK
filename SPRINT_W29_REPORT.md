# Sprint W29 — Timeline Explorer (observabilidade da Perception Timeline)

## Objetivo

Antes de qualquer nova inteligência (W30+), construir uma ferramenta permanente para
observar a `PerceptionTimeline` (W28): navegar por frame/tempo/track_id/tipo de evento,
reconstruir a sequência cronológica, comparar a Timeline com
`detection_results`/`tracking_results`/`analysis_results`, explicar um frame em linguagem
legível e exportar estatísticas/resumo executivo. Substitui os scripts descartáveis
escritos ad-hoc para validar a W28 manualmente. Sem memória cognitiva, sem state machine,
sem Analyzer novo — puramente observabilidade.

## Arquivos criados

```
worker/explorers/
├── __init__.py
├── timeline_explorer.py   # TimelineExplorer - API de consulta
└── cli.py                  # python -m worker.explorers.cli

tests/explorers/
├── __init__.py
├── test_timeline_explorer.py
└── test_cli.py
```

Pacote próprio (`worker/explorers/`, não aninhado em `worker/timeline/`) por decisão
explícita: `TimelineExplorer` deve nascer preparado para um futuro `ArtifactExplorer`
irmão neste mesmo pacote. `__init__` guarda o artifact inteiro (não só `event_timeline`),
o que permite compor/estender sem recarregar nada.

## Nenhum arquivo existente alterado

Zero mudanças em `worker/timeline/`, `basic_vision_engine.py`, Processors, Analyzers,
Registry/Factory/Pipeline — ainda mais isolado que a W28.

## API implementada

- **Navegação**: `by_frame`, `by_time_range`, `by_track_id`, `by_event_type`,
  `chronological`, `reconstruct(up_to_frame=None)`.
- **Explicação**: `explain(frame_index)` — frases legíveis, cronológicas, formatando fatos
  já existentes (nenhuma inferência nova).
- **Comparação**: `compare_with_detections()` (ObjectDetected × contagem real de detecções
  por frame), `compare_with_tracking()` (contagem por tipo × `scene_statistics.events_by_type`,
  reusando o mapeamento `FROM_SCENE_EVENT_TYPE` já definido na W28), `compare_with_analysis()`
  (como `analysis_results` só guarda o último frame por Analyzer — limitação já documentada
  — a comparação verifica consistência estrutural: todo analyzer com `AnalyzerFinished` na
  Timeline, e as regras do `RuleEvaluated` mais recente, via `parent_event_id`, batendo com
  `rules_evaluated` do resultado final).
- **Relatórios**: `statistics()`, `summary()` (resumo executivo), `export_statistics(path)`.

## CLI

`python -m worker.explorers.cli ARTIFACT_PATH [--frame N | --time-range A B | --track-id N
| --event-type T | --chronological [--limit N] | --explain N | --compare-detections |
--compare-tracking | --compare-analysis | --stats [--export PATH] | --summary]`

## Testes

- 34 testes novos (`tests/explorers/`), 100% sintéticos (artifact construído à mão, sem
  vídeo/YOLO/Redis) — cobrem cada método de navegação, `explain`, os 3 comparadores em caso
  consistente **e** em caso de mismatch proposital (4 cenários de erro testados
  explicitamente), estatísticas, resumo, exportação e cada flag do CLI.
- Validação manual contra o `artifact.json` real da W28 (job `b07f0dc6`, 34.095 eventos):
  `--summary`, `--compare-detections`, `--compare-tracking` e `--compare-analysis` — todos
  retornaram `"consistent": true`, confirmando que a Timeline de produção é integralmente
  coerente com `detection_results`/`tracking_results`/`analysis_results`.
- Ajuste cosmético durante a validação manual: trocado "—" (em-dash) por "-" em `explain()`
  — o console do Windows não renderiza o caractere unicode corretamente.
- Suíte completa (`pytest tests/`) sem regressão nova (mesma verificação da W28).

## Próximos passos

W30 (Play Segmentation) e W32 (Temporal Memory API) podem usar `TimelineExplorer` como
ferramenta de validação manual desde já; nenhuma mudança nele deveria ser necessária para
isso.
