import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:life_assistant/web/more_page.dart';

void main() {
  testWidgets('More exposes Habits and navigates to the product route', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/more',
      routes: [
        GoRoute(path: '/more', builder: (_, __) => const MorePage()),
        GoRoute(
          path: '/more/habits',
          builder: (_, __) => const Scaffold(body: Text('Habits route reached')),
        ),
      ],
    );

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();

    expect(find.text('習慣'), findsOneWidget);
    expect(find.text('週期、提醒與完成紀錄'), findsOneWidget);

    await tester.tap(find.text('習慣'));
    await tester.pumpAndSettle();

    expect(find.text('Habits route reached'), findsOneWidget);
  });
}
