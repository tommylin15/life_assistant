import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';

void main() {
  testWidgets('plain MaterialApp baseline without web_app import', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const Scaffold(body: Text('BASELINE_OK')),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('BASELINE_OK'), findsOneWidget);
  });
}
