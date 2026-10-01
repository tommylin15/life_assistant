import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/app_shell.dart';

Widget _hostShell({
  required Size size,
  required String location,
  required ValueChanged<String> onNavigate,
}) {
  return MaterialApp(
    home: MediaQuery(
      data: MediaQueryData(size: size),
      child: AppShell(
        location: location,
        onNavigate: onNavigate,
        child: const Scaffold(body: Center(child: Text('content'))),
      ),
    ),
  );
}

void main() {
  testWidgets('uses bottom navigation on compact layouts', (tester) async {
    String? navigatedTo;

    await tester.pumpWidget(
      _hostShell(
        size: const Size(700, 900),
        location: '/tasks',
        onNavigate: (location) => navigatedTo = location,
      ),
    );

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);

    final navigationBar = tester.widget<NavigationBar>(
      find.byType(NavigationBar),
    );
    expect(navigationBar.selectedIndex, 1);

    await tester.tap(find.text('專案'));
    expect(navigatedTo, '/projects');
  });

  testWidgets('uses navigation rail on wide layouts', (tester) async {
    await tester.pumpWidget(
      _hostShell(
        size: const Size(1200, 900),
        location: '/projects/active',
        onNavigate: (_) {},
      ),
    );

    expect(find.byType(NavigationBar), findsNothing);
    expect(find.byType(NavigationRail), findsOneWidget);

    final navigationRail = tester.widget<NavigationRail>(
      find.byType(NavigationRail),
    );
    expect(navigationRail.selectedIndex, 3);
  });

  test('web app registers Drive routes and More entry', () {
    final source = File('lib/web/web_app.dart').readAsStringSync();
    expect(source, contains("path: '/more/drive'"));
    expect(source, contains("path: '/more/drive/settings'"));
    expect(source, contains("title: const Text('Google Drive')"));
  });
}
