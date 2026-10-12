import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/personalize_page.dart';
import 'package:life_assistant/web/platform_api.dart';

class _FakePreferencesApi extends PlatformApi {
  Map<String, dynamic>? lastBody;
  @override
  Future<Map<String, dynamic>> put(String path, Map<String, dynamic> body) async {
    expect(path, '/me/ui-preferences');
    lastBody = Map<String, dynamic>.from(body);
    return {...body, 'revision': 1};
  }
}

void main() {
  testWidgets('home personalization includes opportunities and explore and saves their order',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = _FakePreferencesApi();
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      uiPreferencesProvider.overrideWith((ref) async => {
        'revision': 0, 'nav_mode': 'auto',
        'pinned': ['tasks', 'calendar', 'projects'],
        'more_order': ['notes', 'habits', 'shopping', 'drive'],
        'home_cards': ['tasks'],
      }),
      effectiveFeaturesProvider.overrideWith((ref) async =>
        {'opportunities': true, 'explore': true}),
    ], child: const MaterialApp(home: PersonalizePage())));
    await tester.pumpAndSettle();

    final opportunity = find.byKey(const ValueKey('home-card-opportunities'));
    final explore = find.byKey(const ValueKey('home-card-explore'));
    expect(opportunity, findsOneWidget);
    expect(explore, findsOneWidget);
    expect(tester.widget<CheckboxListTile>(opportunity).value, false);

    await tester.ensureVisible(opportunity);
    await tester.tap(opportunity);
    await tester.pumpAndSettle();
    await tester.ensureVisible(explore);
    await tester.tap(explore);
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(opportunity).value, true);
    expect(tester.widget<CheckboxListTile>(explore).value, true);

    final save = find.text('儲存偏好');
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();
    expect(api.lastBody?['home_cards'], ['tasks', 'opportunities', 'explore']);
  });
}
