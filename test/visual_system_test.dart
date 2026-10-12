import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:life_assistant/web/visual_system.dart';

void main() {
  test('five visual styles are distinct in both brightness modes', () {
    for (final brightness in Brightness.values) {
      final palettes = LifeVisualStyle.values
          .map((style) => LifeVisualTheme.build(style, brightness).colorScheme.primary)
          .toSet();
      expect(palettes.length, 5);
      for (final style in LifeVisualStyle.values) {
        final theme = LifeVisualTheme.build(style, brightness);
        expect(theme.brightness, brightness);
        expect(theme.cardTheme.color, isNotNull);
      }
    }
  });

  test('account appearance defaults and is independently editable', () {
    final first = LifeAppearanceController('first@example.com');
    final second = LifeAppearanceController('second@example.com');
    expect(first.state.style, LifeVisualStyle.warm);
    expect(first.state.mode, ThemeMode.system);
    first.setStyle(LifeVisualStyle.fresh);
    first.setMode(ThemeMode.dark);
    expect(first.state.style, LifeVisualStyle.fresh);
    expect(first.state.mode, ThemeMode.dark);
    expect(second.state.style, LifeVisualStyle.warm);
    first.dispose();
    second.dispose();
  });

  testWidgets('all feature identities share one compact header size', (tester) async {
    double? standardHeight;
    for (final feature in LifeVisualFeature.values) {
      tester.view.physicalSize = const Size(375, 812);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(ProviderScope(
        child: MaterialApp(
          theme: LifeVisualTheme.build(LifeVisualStyle.focus, Brightness.light),
          home: Scaffold(body: SingleChildScrollView(
            child: LifeFeatureHeader(feature: feature),
          )),
        ),
      ));
      expect(find.text(feature.title), findsOneWidget);
      expect(find.text(feature.description), findsOneWidget);
      expect(find.byIcon(feature.icon), findsOneWidget);
      final height = tester.getSize(find.byType(LifeFeatureHeader)).height;
      standardHeight ??= height;
      expect(height, standardHeight, reason: '${feature.name} differs from other feature headers');
      expect(height, lessThanOrEqualTo(80));
    }
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}
