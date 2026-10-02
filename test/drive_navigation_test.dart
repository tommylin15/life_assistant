import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/web_app.dart';

void main() {
  testWidgets('More exposes Google Drive intelligent organization entry', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/more',
      routes: [
        GoRoute(path: '/more', builder: (_, __) => const MorePage()),
        GoRoute(
          path: '/more/drive',
          builder: (_, __) => const Scaffold(
            body: Center(child: Text('DRIVE_DESTINATION')),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      MaterialApp.router(
        theme: AppTheme.light,
        routerConfig: router,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Google Drive'), findsOneWidget);
    expect(find.textContaining('智能整理'), findsOneWidget);

    await tester.tap(find.text('Google Drive'));
    await tester.pumpAndSettle();

    expect(find.text('DRIVE_DESTINATION'), findsOneWidget);
  });
}
