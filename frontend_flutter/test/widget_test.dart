import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend_flutter/main.dart';
import 'package:frontend_flutter/providers/auth_provider.dart';
import 'package:frontend_flutter/providers/club_provider.dart';
import 'package:frontend_flutter/providers/dashboard_provider.dart';
import 'package:frontend_flutter/providers/goalkeeper_provider.dart';
import 'package:frontend_flutter/providers/training_session_provider.dart';
import 'package:frontend_flutter/providers/video_provider.dart';
import 'package:frontend_flutter/repositories/auth_repository.dart';
import 'package:frontend_flutter/repositories/club_repository.dart';
import 'package:frontend_flutter/repositories/dashboard_repository.dart';
import 'package:frontend_flutter/repositories/goalkeeper_repository.dart';
import 'package:frontend_flutter/repositories/training_session_repository.dart';
import 'package:frontend_flutter/repositories/video_repository.dart';
import 'package:frontend_flutter/services/api_client.dart';
import 'package:frontend_flutter/services/goalkeeper_service.dart';
import 'package:frontend_flutter/services/session_service.dart';

void main() {
  testWidgets('exibe login protegido em pt-BR', (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    final sessionService = SessionService(preferences);
    final apiClient = ApiClient(sessionService);
    final authRepository = AuthRepository(apiClient, sessionService);
    final authProvider = AuthProvider(authRepository, sessionService);
    await authProvider.initialize();

    await tester.pumpWidget(
      GkPerformanceApp(
        authProvider: authProvider,
        dashboardProvider: DashboardProvider(DashboardRepository(apiClient)),
        goalkeeperProvider: GoalkeeperProvider(
          GoalkeeperService(GoalkeeperRepository(apiClient)),
        ),
        clubProvider: ClubProvider(ClubRepository(apiClient)),
        trainingSessionProvider: TrainingSessionProvider(
          TrainingSessionRepository(apiClient),
        ),
        videoProvider: VideoProvider(VideoRepository(apiClient)),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Entrar'), findsWidgets);
    expect(find.text('E-mail'), findsOneWidget);
    expect(find.text('Senha'), findsOneWidget);
  });
}
