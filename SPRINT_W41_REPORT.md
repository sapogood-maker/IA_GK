# Sprint W41 — Architecture Freeze v1.0

## Objetivo

Última sprint da arquitetura do núcleo cognitivo: consolidar todas as decisões tomadas
entre W28 e W40 num único documento definitivo, `COGNITIVE_CORE_ARCHITECTURE_V1.md`, e
declarar o núcleo (`worker/timeline/` até `worker/evaluation/`) formalmente CONGELADO.
Nenhum código, nenhum teste, nenhuma nova camada/dataclass/pacote — apenas consolidação.

## Conteúdo do documento

`COGNITIVE_CORE_ARCHITECTURE_V1.md` (raiz do repositório) contém:

1. Pipeline definitivo (Timeline → ... → Decision, com Evaluation observando de fora).
2. Tabela de cada camada (W28-W39): entrada, saída, responsabilidade única.
3. Tabela consolidada do que NÃO existe e por quê (`Execution`, `ExecutionIntent`,
   `Explainability`, `DecisionType`/`DecisionState`, prioridade fixa de `PlanType`,
   Registry/Factory, confiança/ML score, Rule Engine).
4. 9 princípios fundamentais formalizados (responsabilidade única, conhecimento novo,
   sem duplicação, leitura só da camada imediatamente inferior, núcleo nunca conhece
   ambiente, execução nunca modifica cognição, Evaluation observa mas não participa da
   cognição, determinismo total, vocabulário sempre genérico).
5. Lista definitiva de invariantes arquiteturais.
6. Resposta explícita às seis perguntas obrigatórias desta sprint (por que Decision é o
   contrato terminal; por que Execution não pertence ao núcleo; por que ExecutionIntent
   foi rejeitado; por que Evaluation existe; por que Explainability não existe; quais
   princípios impediram essas decisões).
7. Roadmap de como adicionar funcionalidade sem modificar o núcleo, com exemplos
   concretos de adaptadores externos (goalkeeper scouting, trading, robótica,
   diagnóstico, sistemas especialistas) — todos reutilizando exatamente o mesmo núcleo.
8. Autocrítica honesta: 8 limitações que permanecem deliberadamente não resolvidas (sem
   dado espacial, `PresenceState` pobre, limiares arbitrários, acoplamento textual
   W37→W39, mapeamento 1:1 `HypothesisType`→`PlanType` como simplificação não permanente,
   sem arbitração cross-subject, validação de Conviction sem múltiplos `HypothesisSet`s
   cronológicos reais, `EvaluationSet` cego a sujeitos sem decisão); o que ficou fora por
   decisão (texto em linguagem natural, aprendizado automático, persistência,
   versionamento de contrato); o que justificaria uma v2.0.
9. Declaração formal de congelamento das 11 camadas que compõem o núcleo v1.0.

## Compatibilidade

Nenhum arquivo de código ou teste foi alterado. Apenas dois arquivos de documentação
foram criados: `COGNITIVE_CORE_ARCHITECTURE_V1.md` e este relatório.

## Próximos passos

Toda funcionalidade futura relacionada ao núcleo deve viver em adaptadores externos, fora
de `worker/`, consumindo `DecisionSet`/`EvaluationSet`. Qualquer alteração dentro das
camadas congeladas exige ser tratada como uma exceção explícita a este freeze, nunca uma
mudança incremental silenciosa.
