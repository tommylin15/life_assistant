import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/visual_system.dart';

void main() {
  testWidgets('all six functional headers render at phone and desktop widths in five styles',
      (tester) async {
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.view.devicePixelRatio = 1.0;

    for (final width in [320.0, 375.0, 768.0, 1440.0]) {
      tester.view.physicalSize = Size(width, 900);
      for (final style in LifeVisualStyle.values) {
        for (final feature in LifeVisualFeature.values) {
          await tester.pumpWidget(ProviderScope(
            key: UniqueKey(),
            overrides: [
              lifeAppearanceProvider.overrideWith(
                (ref) => LifeAppearanceController(null)..setStyle(style),
              ),
            ],
            child: MaterialApp(
              theme: LifeVisualTheme.build(style, Brightness.light),
              home: Scaffold(
                body: SingleChildScrollView(
                  child: Padding(
                    padding: const EdgeInsets.all(8),
                    child: LifeFeatureHeader(feature: feature),
                  ),
                ),
              ),
            ),
          ));
          expect(tester.takeException(), isNull,
              reason: '${style.name} / ${feature.name} / width $width');
          expect(find.text(feature.title), findsOneWidget);
          expect(find.byIcon(feature.icon), findsOneWidget);
          final header = tester.getRect(find.byType(LifeFeatureHeader));
          expect(header.width, lessThanOrEqualTo(width));
          expect(header.left, greaterThanOrEqualTo(0));
          expect(header.right, lessThanOrEqualTo(width));
        }
      }
    }
  });
}
