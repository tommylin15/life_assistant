import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/app_shell.dart';

Widget _hostShell({
  required Size size,
  required String location,
  required ValueChanged<String> onNavigate,
}) {
  return ProviderScope(child: MaterialApp(
    home: MediaQuery(
      data: MediaQueryData(size: size),
      child: AppShell(
        location: location,
        onNavigate: onNavigate,
        child: const Scaffold(body: Center(child: Text('content'))),
      ),
    ),
  ));
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

  testWidgets('keeps compact rail on medium desktop layouts', (tester) async {
    await tester.pumpWidget(
      _hostShell(
        size: const Size(900, 900),
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
    expect(navigationRail.extended, isFalse);
  });

  testWidgets('uses extended sidebar rail on roomy desktop layouts', (
    tester,
  ) async {
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
    expect(navigationRail.extended, isTrue);
  });
}
