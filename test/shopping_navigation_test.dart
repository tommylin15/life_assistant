import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:life_assistant/web/more_page.dart';

void main() {
  testWidgets('More exposes Shopping and navigates to the product route', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/more',
      routes: [
        GoRoute(path: '/more', builder: (_, __) => const MorePage()),
        GoRoute(
          path: '/more/shopping',
          builder: (_, __) =>
              const Scaffold(body: Text('Shopping route reached')),
        ),
      ],
    );

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();

    expect(find.text('購物清單'), findsOneWidget);
    expect(find.text('清單、分類與採買完成狀態'), findsOneWidget);

    await tester.tap(find.text('購物清單'));
    await tester.pumpAndSettle();

    expect(find.text('Shopping route reached'), findsOneWidget);
  });
}
