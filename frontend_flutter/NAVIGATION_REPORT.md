# Relatório de Navegação

## Rotas criadas

- `/painel` -> Painel
- `/clubes` -> Clubes
- `/goleiros` -> Goleiros
- `/videos` -> Vídeos
- `/analises` -> Análises
- `/sessoes-de-treino` -> Sessões de Treino
- `/relatorios` -> Relatórios
- `/telegram` -> Telegram
- `/usuarios` -> Usuários
- `/configuracoes` -> Configurações

## Telas criadas

- `PainelScreen`
- `ClubesScreen`
- `GoleirosScreen`
- `VideosScreen`
- `AnalisesScreen`
- `SessoesTreinoScreen`
- `RelatoriosScreen`
- `TelegramScreen`
- `UsuariosScreen`
- `ConfiguracoesScreen`

## Arquivos criados

- `frontend_flutter/NAVIGATION_REPORT.md`

## Arquivos modificados

- `frontend_flutter/lib/main.dart`
- `frontend_flutter/pubspec.yaml`
- `frontend_flutter/pubspec.lock`
- `frontend_flutter/test/widget_test.dart`
- `frontend_flutter/web/index.html`
- `frontend_flutter/web/manifest.json`
- `frontend_flutter/README.md`

## Resumo técnico

- `MaterialApp` foi substituído por `MaterialApp.router`.
- `GoRouter` foi configurado com `ShellRoute` para manter o layout principal.
- O menu lateral agora navega usando `context.go(...)`.
- O item ativo do menu é calculado pela rota atual.
- A barra lateral permanece fixa no desktop.
- Em telas menores, o menu é aberto por `Drawer`.
- Todos os textos visíveis adicionados permanecem em português do Brasil.
