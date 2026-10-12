import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/auth_state.dart';
import 'package:life_assistant/web/personalize_page.dart';
import 'package:life_assistant/web/platform_api.dart';

class _TestAuth extends AuthNotifier {
  @override
  AsyncValue<Map<String, String>?> build() => const AsyncValue.data({
    'email': 'user@example.test', 'name': 'Test user',
  });
}

void main() {
  testWidgets('account switch remains accessible when preferences fail', (tester) async {
    await tester.pumpWidget(ProviderScope(overrides: [
      authProvider.overrideWith(_TestAuth.new),
      uiPreferencesProvider.overrideWith((ref) async =>
          throw StateError('Preferences unavailable')),
      effectiveFeaturesProvider.overrideWith((ref) async => {}),
    ], child: const MaterialApp(home: PersonalizePage())));
    await tester.pumpAndSettle();
    expect(find.text('無法取得介面偏好'), findsOneWidget);
    expect(find.byKey(const ValueKey('personalize-logout')), findsOneWidget);
    expect(find.text('user@example.test'), findsOneWidget);
    expect(find.text('登出／切換帳號'), findsOneWidget);
  });
}
