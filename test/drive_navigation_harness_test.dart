import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/web_app.dart';

void main() {
  testWidgets('baseline plain MaterialApp pumps', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const Scaffold(body: Text('BASELINE')),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('BASELINE'), findsOneWidget);
  });

  testWidgets('MorePage pumps in plain MaterialApp', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const MorePage(),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('Google Drive'), findsOneWidget);
  });

  testWidgets('baseline local GoRouter pumps', (tester) async {
    final router = GoRouter(
      initialLocation: '/baseline',
      routes: [
        GoRoute(
          path: '/baseline',
          builder: (_, __) => const Scaffold(body: Text('ROUTER_BASELINE')),
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
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('ROUTER_BASELINE'), findsOneWidget);
  });

  testWidgets('MorePage pumps once with local GoRouter', (tester) async {
    final router = GoRouter(
      initialLocation: '/more',
      routes: [
        GoRoute(path: '/more', builder: (_, __) => const MorePage()),
        GoRoute(
          path: '/more/drive',
          builder: (_, __) => const Scaffold(body: Text('DRIVE_DESTINATION')),
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
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('Google Drive'), findsOneWidget);
  });
}
