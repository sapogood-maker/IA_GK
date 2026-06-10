import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';

import 'package:frontend_flutter/main.dart';

void main() {
  testWidgets('exibe painel comercial de goleiros em pt-BR', (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const GkPerformanceApp());

    expect(find.text('Painel'), findsWidgets);
    expect(find.text('Vídeos Enviados'), findsOneWidget);
    expect(find.text('Análises Concluídas'), findsOneWidget);
    expect(find.text('GK Score Médio'), findsOneWidget);
    expect(find.text('Goleiros Ativos'), findsOneWidget);
    expect(find.text('Sessões de Treino'), findsOneWidget);
    expect(find.text('Enviar Vídeo'), findsWidgets);

    await tester.tap(find.text('Clubes'));
    await tester.pumpAndSettle();

    expect(find.text('Novo Clube'), findsOneWidget);
    expect(find.text('Clubes ativos'), findsOneWidget);

    await tester.tap(find.text('Configurações'));
    await tester.pumpAndSettle();

    expect(find.text('Salvar'), findsOneWidget);
    expect(find.text('Critérios do GK Score'), findsOneWidget);
  });
}
