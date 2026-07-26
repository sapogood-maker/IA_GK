# Sprint W38 — Onde o núcleo cognitivo termina

## Objetivo

Analisar criticamente se a camada seguinte a Decision (W37) deveria ser uma `Execution`
real ou uma representação abstrata de intenção (`ExecutionIntent`) — e, mais a fundo, se
essa representação já não é o próprio `DecisionSet`. **Conclusão: nenhum pacote novo foi
criado.** `DecisionSet` (W37) passa a ser, formalmente, o último artefato produzido pelo
núcleo cognitivo.

## Processo: duas rodadas de análise crítica antes de qualquer decisão final

Como nas sprints W36/W37, o processo seguiu proposta → autocrítica → riscos →
alternativas → justificativa, com duas rodadas de revisão:

1. **Primeira rodada**: `Execution` real (chamar APIs, mover robôs, tocar hardware) foi
   analisada e **rejeitada categoricamente** — violaria os quatro pilares mantidos desde
   W28 (determinismo/sem efeito colateral, sem conhecimento de domínio, núcleo reutilizável,
   cada camada só lê a imediatamente abaixo). A hipótese do usuário — "o cérebro não deveria
   executar nada, só produzir uma representação abstrata da intenção" — foi confirmada como
   correta nesse ponto.
2. **Segunda rodada** (a pedido explícito do usuário, questionando a primeira versão desta
   proposta): comparação rigorosa entre adotar `DecisionSet` como contrato final do núcleo
   (Alternativa E) vs introduzir `ExecutionIntent` como camada intermediária nova
   (Alternativa B, desenhada por completo na primeira versão). **Resultado: `ExecutionIntent`,
   tal como desenhado, era um subconjunto estrito de `DecisionSet` — mesmos valores
   (`intent_type` = `plan_type`, `rationale` = `winning_criteria`, cópia literal), zero
   informação nova, zero abstração nova, custo real de complexidade (1 pacote, 3
   dataclasses, 1 builder, ~15 testes) sem benefício mensurável.** Pela mesma régua que já
   rejeitou `DecisionType`/`DecisionState`/prioridade fixa de `PlanType` na W37, a proposta
   foi revertida: nenhuma camada nova.

## Comparação decisiva (resumo)

| Critério | `DecisionSet` como final | `ExecutionIntent` intermediário |
|---|---|---|
| Informação nova | — | Nenhuma (cópia literal de 2 campos) |
| Redução de acoplamento real | Já suficiente (consumidor só lê os campos que quer) | Só reduziria acoplamento por engano evitado, não por construção |
| Complexidade adicional | Zero | 1 pacote + 3 dataclasses + 1 builder + ~15 testes |
| Impacto em Explainability futura | Tudo já disponível num só lugar | Precisaria "furar" a camada fina de qualquer forma |

## Único artefato desta sprint: nota de contrato em `worker/decision/`

Nenhum campo, tipo, assinatura ou comportamento mudou. Foi acrescentada uma nota de
documentação (docstring) a `decision_set.py`/`track_decision.py`/`entity_decision.py`
explicitando qual subconjunto de campos compõe o contrato estável para consumidores
externos (`track_id`/`entity`, `plan_type`, `winning_criteria`) e qual é registro interno
de auditoria do processo de decisão (`selected_plan_id`/`discarded_plan_ids` — útil para
uma futura Explainability Layer, não para acionar execução real). Suíte de testes de
`worker/decision/` (20 testes, W37) confirmada intacta após a mudança — puramente
documentação, sem impacto em comportamento.

## Riscos identificados

1. A separação "contrato estável vs auditoria interna" depende de disciplina/documentação,
   não de enforcement em código — se um adaptador real futuro se acoplar indevidamente a
   `selected_plan_id`/`discarded_plan_ids`, essa dor concreta seria a justificativa correta
   para então introduzir uma camada de tradução formal, não antes.
2. Nenhum mecanismo de versionamento de contrato existe para `DecisionSet` — uma mudança
   futura em sua forma poderia quebrar adaptadores externos sem aviso.
3. `PlanType`/nomes `track`/`entity` ainda carregam resquício do domínio de
   rastreamento/percepção — se o núcleo for aplicado a um domínio radicalmente diferente no
   futuro, pode exigir revisão de vocabulário em toda a pilha (não resolvido nem por
   `DecisionSet` nem por um `ExecutionIntent` hipotético).

## Compatibilidade

Nenhum arquivo de `worker/timeline/`, `worker/explorers/`, `worker/segments/`,
`worker/memory/`, `worker/perceptual_state/`, `worker/hypothesis/`, `worker/conviction/`,
`worker/planning/`, `worker/analyzers/`, `worker/domain/` foi alterado. Apenas 3 docstrings
em `worker/decision/` foram estendidas (nenhuma lógica).

## Impacto esperado no que vem depois

`DecisionSet` é o último artefato produzido pelo núcleo cognitivo. Um adaptador externo
futuro (fora de `worker/`, específico de cada aplicação — robótica, scouting, mercado
financeiro) consumiria `DecisionSet`, lendo só `track_id`/`entity`/`plan_type`/
`winning_criteria`, e traduziria isso para ações reais em seu próprio domínio — essa
tradução nunca é implementada dentro do núcleo cognitivo.

## Próximos passos

- Um adaptador de execução real para o domínio de scouting de goleiros — projeto separado,
  fora de `worker/`.
- Explainability Layer — consumiria `DecisionSet` diretamente (tem toda a informação:
  escolha final + critérios + descartados).
- Revisitar o vocabulário de `PlanType`/`track`/`entity` se um domínio radicalmente
  diferente precisar reutilizar o núcleo.
- Mecanismo de versionamento de contrato para `DecisionSet`, se/quando adaptadores externos
  reais existirem.
- Revisitar a decisão desta sprint (introduzir uma camada de tradução formal) se um caso
  concreto de acoplamento indevido aparecer na prática.
