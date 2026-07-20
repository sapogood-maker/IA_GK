# SPRINT_REPORT.md — Sprint 2 (Goleiros funcional + Clubes mínimo)

> Referência: `PROJECT_ANALYSIS.md`, roadmap Sprint 2, escopo reduzido combinado com o usuário (só Goleiros + leitura mínima de Clubes, em vez das 9 telas originais).
> Motivação direta: usuário reportou, após logar, não conseguir cadastrar goleiros ("tem o campo para adicionar novo goleiro porém sem conseguir fazer nada").

## Objetivo

Tornar a tela "Goleiros" funcional de ponta a ponta: listar goleiros reais vindos da API e permitir cadastrar um novo goleiro de verdade pela UI, com um clube real selecionado. A tela de Clubes em si permanece com dados fictícios (fora do escopo combinado) — apenas a leitura de clubes por trás (para alimentar o formulário) é real.

## Problema identificado antes de implementar

Além da tela ser 100% estática, encontrei **dois bugs que impediriam o cadastro de funcionar mesmo ligando o botão**:
1. Backend: `GET /api/v1/goalkeepers` sem `club_id` retornava `[]` fixo (achado 7.9 do `PROJECT_ANALYSIS.md`) — não dava para listar os goleiros existentes.
2. Frontend: o model `Goalkeeper` (Dart) não tinha campo `club_id`, mas o backend exige `club_id` para criar um goleiro — o app nunca conseguiria montar um payload de criação válido.

Ambos foram corrigidos como parte desta sprint, por serem bloqueadores diretos do objetivo.

## Arquivos modificados/criados

| Arquivo | Alteração |
|---|---|
| `backend_fastapi/app/repositories/repositories.py` | Adicionado `GoalkeeperRepository.get_all()` |
| `backend_fastapi/app/api/v1/goalkeepers.py` | `list_goalkeepers` sem `club_id` agora chama `get_all()` em vez de retornar `[]` |
| `frontend_flutter/lib/models/goalkeeper.dart` | Adicionado campo `clubId` (obrigatório), lido/escrito como `club_id` no JSON |
| `frontend_flutter/lib/models/club.dart` **(novo)** | Model `Club` (id, name, city) |
| `frontend_flutter/lib/repositories/club_repository.dart` **(novo)** | `getClubs()` — `GET /api/v1/clubs` |
| `frontend_flutter/lib/repositories/goalkeeper_repository.dart` | Adicionado `getAllGoalkeepers()` — `GET /api/v1/goalkeepers` sem filtro |
| `frontend_flutter/lib/services/goalkeeper_service.dart` | Adicionado `getAllGoalkeepers()` (repassa ao repository) |
| `frontend_flutter/lib/providers/club_provider.dart` **(novo)** | Estado reativo de clubes (`clubs`, `isLoading`, `errorMessage`, `load()`) |
| `frontend_flutter/lib/providers/goalkeeper_provider.dart` | Ganhou estado real (`goalkeepers`, `isLoading`, `errorMessage`, `loadAll()`); `createGoalkeeper` agora retorna `bool` e recarrega a lista após sucesso; removidos os `print()`/`rethrow` que geravam warnings de lint (pendência 4 da Sprint 0); métodos `getGoalkeepersByClubId`/`getGoalkeeperById` mantidos como estavam |
| `frontend_flutter/lib/main.dart` | Registra `GoalkeeperProvider` e `ClubProvider` no `MultiProvider`; `GkPerformanceApp` ganha os dois novos parâmetros obrigatórios; `_CabecalhoSecao` ganha callback opcional `onAcao` (as outras 8 telas continuam com botão sem ação, comportamento inalterado); `GoleirosScreen` reescrita como `StatefulWidget` que carrega goleiros e clubes reais e abre um diálogo de cadastro (`_DialogNovoGoleiro`) com validação, estado de carregamento e tratamento de erro |
| `frontend_flutter/test/widget_test.dart` | Atualizado para passar os dois novos providers obrigatórios ao `GkPerformanceApp` |

## Decisões arquiteturais

- **`GoalkeeperProvider` foi ampliado, não recriado.** Era código morto (nunca registrado, com `print()` de erro) — os 3 métodos originais (`createGoalkeeper`, `getGoalkeepersByClubId`, `getGoalkeeperById`) tiveram assinatura preservada onde fazia sentido; só `createGoalkeeper` mudou de `Future<void>` para `Future<bool>`, porque a UI precisa saber se deu certo para fechar o diálogo ou mostrar erro — mudança necessária, não gratuita, já que o método nunca tinha sido usado por ninguém antes.
- **`_CabecalhoSecao` ganhou um parâmetro opcional (`onAcao`), não foi duplicado.** As 8 telas estáticas restantes (Clubes, Vídeos, Análises, Sessões, Relatórios, Telegram, Usuários, Configurações) continuam chamando `_TelaSecao` exatamente como antes, sem passar `onAcao` — o botão delas continua sem ação, comportamento 100% preservado.
- **Não criei fluxo de criação de Clube nem toquei na tela "Clubes"** — só a leitura (`ClubRepository.getClubs()`) foi implementada, estritamente para alimentar o dropdown do formulário de goleiro, conforme escopo combinado.
- **Campo `notes` do model `Goalkeeper` não ganhou input no formulário** — o backend (model/schema/migration) não tem coluna `notes` na tabela `goalkeepers`; adicionar isso exigiria uma migration Alembic nova, fora do escopo desta sprint. Registrado como pendência.
- **A tela "Goleiros" perdeu os cards de métricas fictícias** ("Goleiros ativos: 36", "GK Score médio: 82,4" etc.) que existiam no mockup — como não há dado real equivalente ainda (GK Score, alertas técnicos não existem no backend), optei por não substituir por números fictícios novos; a tela agora mostra só a lista real de goleiros. Fica como pendência futura calcular métricas reais quando fizer sentido.

## Testes/verificações executados

| Verificação | Resultado |
|---|---|
| `flutter analyze` | **0 erros, 0 avisos** (corrigi 2 avisos de `unnecessary_cast` que apareceram no meu próprio código antes do ajuste final) |
| `flutter test` | **1/1 passou** |
| `flutter build web --release` | **Build concluído com sucesso** |
| `python -m py_compile` em todo `backend_fastapi/app/` | **Sem erros de sintaxe** |
| Execução real do backend (subir servidor e testar `POST /api/v1/goalkeepers` de ponta a ponta) | **Não executado** — mesma limitação de ambiente já registrada na Sprint 1 (Python 3.14 local vs. dependências do projeto pinadas para 3.11; `pydantic-core` não compila aqui). Recomendo validar via `docker compose up` |

## Pendências

1. **Validar em runtime real** (via Docker) o fluxo completo: login → abrir "Goleiros" → "Novo Goleiro" → selecionar clube → salvar → ver o goleiro na lista.
2. Se ainda não existir nenhum clube cadastrado no banco, o formulário vai mostrar o aviso "Cadastre um clube antes de adicionar um goleiro" — hoje só é possível criar um clube via API diretamente (`POST /api/v1/clubs`), já que a tela de Clubes continua estática. Isso deve ser resolvido quando a tela de Clubes for conectada de verdade (próxima sprint candidata).
3. Campo `notes` do goleiro sem suporte no backend (sem coluna/migration) — não exposto no formulário.
4. Sem métricas reais na tela de Goleiros (métricas fictícias removidas, nada substituiu ainda).

## Próximos passos sugeridos

Testar manualmente o fluxo (crie ao menos um clube via `POST /api/v1/clubs` para conseguir testar o cadastro de goleiro pela UI). Depois, sugiro como próxima sprint conectar a tela de **Clubes** (listar + criar clube de verdade), o que também resolve a pendência 2 acima.

Aguardando sua aprovação para a próxima sprint.
