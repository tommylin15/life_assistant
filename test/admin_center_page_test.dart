import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/admin_center_page.dart';
import 'package:life_assistant/web/platform_api.dart';

class _Api extends PlatformApi {
  String status = 'beta';
  String audience = 'owner';
  int revision = 0;
  final writes = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> get(String path) async {
    if (path != '/admin/feature-rollouts') throw StateError('Not needed for this test');
    return {'features': [{'key': 'opportunities', 'title': '限時機會',
      'status': status, 'audience': audience, 'revision': revision}]};
  }

  @override
  Future<Map<String, dynamic>> put(String path, Map<String, dynamic> body) async {
    expect(path, '/admin/feature-rollouts');
    expect(body['expected_revision'], revision);
    writes.add(body);
    status = body['status'] as String;
    audience = body['audience'] as String;
    revision++;
    return {'revision': revision};
  }
}

void main() {
  testWidgets('admin can open a beta activity to all and restore owner access', (tester) async {
    final api = _Api();
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
    ], child: const MaterialApp(home: AdminCenterPage())));
    await tester.pumpAndSettle();
    expect(api.writes, isEmpty);
    for (final choice in ['開放給所有使用者', '開放給管理員', '測試（管理員）']) {
      await tester.tap(find.byTooltip('調整開放狀態'));
      await tester.pumpAndSettle();
      await tester.tap(find.text(choice));
      await tester.pumpAndSettle();
    }
    expect(api.writes.map((b) => [b['status'], b['audience']]).toList(),
      [['enabled', 'all'], ['enabled', 'owner'], ['beta', 'owner']]);
    expect(find.text('目前：beta / owner'), findsOneWidget);
  });
}
