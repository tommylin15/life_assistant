import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/web_app.dart';

GoRouter _router() => GoRouter(
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

Future<void> _pumpMore(WidgetTester tester, GoRouter router) async {
  await tester.pumpWidget(
    MaterialApp.router(
      theme: AppTheme.light,
      routerConfig: router,
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('More renders Google Drive intelligent organization entry', (
    tester,
  ) async {
    final router = _router();
    addTearDown(router.dispose);

    await _pumpMore(tester, router);

    expect(find.text('Google Drive'), findsOneWidget);
    expect(find.textContaining('智能整理'), findsOneWidget);
  });

  testWidgets('More navigates to Google Drive intelligent organization', (
    tester,
  ) async {
    final router = _router();
    addTearDown(router.dispose);

    await _pumpMore(tester, router);

    await tester.tap(find.text('Google Drive'));
    await tester.pumpAndSettle();

    expect(find.text('DRIVE_DESTINATION'), findsOneWidget);
  });
}
