"""Evaluation Layer (Sprint W39).

Reclassificação determinística de `DecisionSet` (W37/W38) que expõe,
de forma tipada, fatos ESTRUTURAIS sobre COMO cada decisão foi
produzida - nunca sobre se ela "deu certo" no ambiente. Evaluation
nunca sabe se um robô chegou ao destino, se o goleiro defendeu a bola,
ou se uma operação financeira deu lucro - essas informações pertencem
ao ambiente, nunca ao núcleo cognitivo.

Consome EXCLUSIVAMENTE `DecisionSet` - nenhum código aqui importa
`worker.planning`, `worker.conviction`, `worker.hypothesis`,
`worker.perceptual_state` ou camadas inferiores. Nunca modifica
`DecisionSet`.

Nota sobre duas perguntas do pedido original que NUNCA viram campo:
"a decisão foi consistente?" e "a decisão foi determinística?" são
propriedades ESTÁTICAS de `decide()` (W37) como função pura e total -
sempre verdadeiras para qualquer `DecisionSet` que este pipeline
produza, nunca um fato que varia por instância. Por isso não existem
como campos em `TrackEvaluation`/`EntityEvaluation` - são garantias do
próprio código, documentadas aqui, não dado a ser avaliado."""
