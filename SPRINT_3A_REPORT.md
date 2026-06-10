# Sprint 3A - Integração Flutter Web + FastAPI

## Arquivos criados

- `frontend_flutter/lib/core/api_config.dart`
- `frontend_flutter/lib/models/auth_tokens.dart`
- `frontend_flutter/lib/models/auth_user.dart`
- `frontend_flutter/lib/models/dashboard_data.dart`
- `frontend_flutter/lib/providers/auth_provider.dart`
- `frontend_flutter/lib/providers/dashboard_provider.dart`
- `frontend_flutter/lib/repositories/auth_repository.dart`
- `frontend_flutter/lib/repositories/dashboard_repository.dart`
- `frontend_flutter/lib/services/api_client.dart`
- `frontend_flutter/lib/services/session_service.dart`

## Arquivos alterados

- `frontend_flutter/lib/main.dart`
- `frontend_flutter/pubspec.yaml`
- `frontend_flutter/pubspec.lock`
- `frontend_flutter/test/widget_test.dart`
- `frontend_flutter/macos/Flutter/GeneratedPluginRegistrant.swift`
- `frontend_flutter/linux/flutter/generated_plugin_registrant.cc`
- `frontend_flutter/linux/flutter/generated_plugin_registrant.h`
- `frontend_flutter/linux/flutter/generated_plugins.cmake`
- `frontend_flutter/windows/flutter/generated_plugin_registrant.cc`
- `frontend_flutter/windows/flutter/generated_plugin_registrant.h`
- `frontend_flutter/windows/flutter/generated_plugins.cmake`

## Endpoints integrados

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/videos`
- `GET /api/v1/processing-jobs`
- `GET /api/v1/clubs`
- `GET /api/v1/training-sessions`

## Fluxo de autenticação implementado

- Configuração centralizada em `ApiConfig.baseUrl`.
- Login real via JWT com `dio`.
- Persistência de `access_token` e `refresh_token` com `shared_preferences`.
- Interceptor HTTP adicionando `Authorization: Bearer <token>`.
- Renovação automática ao receber `401`, usando `/api/v1/auth/refresh`.
- Recuperação de usuário autenticado via `/api/v1/auth/me`.
- Logout limpando tokens locais e redirecionando para `/login`.
- Rotas protegidas com `go_router`: usuários anônimos vão para `/login`, usuários autenticados abrem `/painel`.
- Tela de login em PT-BR com e-mail, senha, botão Entrar e mensagens amigáveis.

## Dashboard

- Cards executivos usam dados reais quando endpoints retornam listas.
- Fila de análises usa `processing-jobs`.
- Sessões recentes usam `training-sessions`.
- Status lateral da IA usa jobs em processamento.
- Blocos sem endpoint suficiente exibem `Sem dados disponíveis`.

## Pendências para Sprint 3B

- Corrigir no backend `GET /api/v1/auth/me` para ler `Authorization` via header FastAPI (`Header`) em vez de query parameter.
- Criar endpoint de dashboard agregado para evitar múltiplas chamadas e padronizar métricas.
- Criar endpoint global ou agregado para goleiros ativos.
- Criar endpoint de métricas técnicas para preencher `Mapa de desempenho`.
- Definir status canônicos de `processing-jobs` (`DONE`, `PROCESSING`, etc.) e alinhar UI/backend.
- Conectar ações de criação/upload a formulários reais.
- Ampliar testes de integração com backend ou contratos HTTP.

## Verificação

- `dart format lib test`
- `flutter analyze`
- `flutter test`
