import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/app_shell.dart';

Widget hostShell({required Size size, required ValueChanged<String> onNavigate}) =>
    ProviderScope(child: MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(size: size),
        child: AppShell(
          location: '/tasks', onNavigate: onNavigate,
          child: const Scaffold(body: Center(child: Text('content'))),
        ),
      ),
    ));

void main() {
  testWidgets('phone keeps four shortcuts and uses grouped drawer without More or Home',
      (tester) async {
    String? path;
    await tester.pumpWidget(hostShell(
        size: const Size(375, 800), onNavigate: (value) => path = value));
    final bar = tester.widget<NavigationBar>(find.byType(NavigationBar));
    expect(bar.destinations.length, 4);
    expect((bar.destinations.first as NavigationDestination).label, '首頁');
    expect(find.byType(NavigationRail), findsNothing);
    final scaffold = tester.widget<Scaffold>(
      find.descendant(of: find.byType(AppShell), matching: find.byType(Scaffold)).first);

    expect(scaffold.drawer, isNotNull);
    await tester.tap(find.byIcon(Icons.menu).first);
    await tester.pumpAndSettle();
    expect(find.text('日常生活'), findsWidgets);
    expect(find.text('知識與計畫'), findsWidgets);
    expect(find.text('活動與機會'), findsWidgets);
    expect(find.text('個人化'), findsWidgets);
    expect(find.text('更多'), findsNothing);
    await tester.tap(find.text('個人化'));
    expect(path, '/more/personalize');
  });

  testWidgets('desktop uses one grouped collapsible sidebar with bottom four shortcuts',
      (tester) async {
    String? path;
    await tester.pumpWidget(hostShell(
        size: const Size(1200, 900), onNavigate: (value) => path = value));
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
    expect(find.text('日常生活'), findsOneWidget);
    expect(find.text('活動與機會'), findsOneWidget);
    expect(find.text('Google 整合'), findsNothing);
    expect(find.text('更多'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('nav-group-daily')));
    await tester.pump();
    expect(find.byKey(const ValueKey('nav-item-tasks')), findsNothing);
    await tester.tap(find.byKey(const ValueKey('nav-group-daily')));
    await tester.pump();
    expect(find.byKey(const ValueKey('nav-item-tasks')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('nav-item-shopping')));
    expect(path, '/more/shopping');
    await tester.tap(find.byTooltip('收合左側選單'));
    await tester.pump();
    expect(find.byTooltip('展開左側選單'), findsOneWidget);
  });
}
