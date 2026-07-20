# SPRINT_REPORT.md — Sprint Clubes (Conectar tela de Clubes à API)

> Referência: pendência registrada no `SPRINT_REPORT.md` da Sprint 2 ("hoje só é possível criar um clube via API diretamente, já que a tela de Clubes continua estática").

## Objetivo

Tornar a tela "Clubes" funcional: listar clubes reais da API e permitir cadastrar um novo clube pela UI, no mesmo padrão já estabelecido para Goleiros na sprint anterior. Isso também resolve a pendência de UX da sprint passada — agora dá para criar um clube e, na sequência, cadastrar um goleiro vinculado a ele sem sair do app.

## Arquivos modificados

| Arquivo | Alteração |
|---|---|
| `frontend_flutter/lib/models/club.dart` | Adicionado `toJson()` (faltava; necessário para enviar o cadastro) |
| `frontend_flutter/lib/repositories/club_repository.dart` | Adicionado `createClub(Club)` — `POST /api/v1/clubs` |
| `frontend_flutter/lib/providers/club_provider.dart` | Adicionado `createClub(Club)`, retornando `bool` e recarregando a lista após sucesso (mesmo padrão do `GoalkeeperProvider.createGoalkeeper`) |
| `frontend_flutter/lib/main.dart` | `ClubesScreen` deixou de ser `StatelessWidget` estático e virou `StatefulWidget` que carrega clubes reais no `initState` e abre um diálogo de cadastro funcional (`_DialogNovoClube` + `_LinhaClube`) |

Nenhum arquivo do backend foi alterado — `GET`/`POST /api/v1/clubs` já funcionavam corretamente (diferente do caso de Goleiros na sprint anterior, aqui não havia bug de listagem).

## Decisões arquiteturais

- **Mesmo padrão da Sprint 2 (Goleiros), reaproveitado por consistência:** `_CabecalhoSecao` com `onAcao`, diálogo com `Form`/`GlobalKey<FormState>`, `Provider` expondo `list`/`isLoading`/`errorMessage` e um método `create*` que retorna `bool` e recarrega a lista. Isso mantém as duas telas com a mesma "forma", facilitando manutenção futura.
- **Cards de métricas fictícias removidos** ("Clubes ativos: 12", "Goleiros vinculados: 36" etc.), pelo mesmo motivo da sprint anterior — não há dado real equivalente ainda para "vídeos no mês" por clube. A tela mostra a lista real.
- **`Club.toJson()` não inclui `id`** (diferente de `Goalkeeper.toJson()`, que inclui um `id` vazio por herança do código pré-existente) — o schema `ClubCreate` do backend só aceita `name`/`city`, então optei por não replicar essa pequena inconsistência em código novo.

## Testes/verificações executados

| Verificação | Resultado |
|---|---|
| `flutter analyze` | **0 erros, 0 avisos** |
| `flutter test` | **1/1 passou** |
| `flutter build web --release` | **Build concluído com sucesso** |
| Backend (`py_compile`) | Não aplicável — nenhum arquivo Python foi alterado nesta sprint |
| Execução real (Docker) do fluxo completo (criar clube → ver na lista → usar no cadastro de goleiro) | **Não executado** — mesma limitação de ambiente já registrada nas sprints anteriores (Python 3.14 local vs. dependências pinadas para 3.11) |

## Pendências

1. Validar em runtime real (via Docker) o fluxo: "Clubes" → "Novo Clube" → salvar → ver na lista → ir em "Goleiros" → "Novo Goleiro" → selecionar o clube recém-criado.
2. Editar/excluir clube ainda não implementado (só criar e listar) — não fazia parte do pedido desta sprint.
3. Seguem valendo as pendências já registradas nas sprints anteriores (autorização granular por papel, rotação de refresh token, telas de Vídeos/Sessões/Análises/Relatórios/Telegram/Usuários/Configurações ainda estáticas).

## Próximos passos sugeridos

Testar manualmente o fluxo completo Clube → Goleiro pela UI. Como próxima sprint, sugiro **Vídeos** (upload real pela UI usando `POST /api/v1/videos/upload`, que já existe e funciona no backend) ou **Sessões de Treino**, dependendo do que for mais útil para você validar agora.

Aguardando sua aprovação para a próxima sprint.
