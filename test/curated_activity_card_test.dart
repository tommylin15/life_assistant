import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/curated_activity_card.dart';
import 'package:life_assistant/web/platform_api.dart';

class _Api extends PlatformApi {
  final calls = <Map<String, dynamic>>[];
  bool saved = false;
  @override
  Future<Map<String, dynamic>> put(String path, Map<String, dynamic> body) async {
    calls.add({'path': path, ...body});
    saved = body['active'] == true;
    return {'active': saved};
  }
}

void main() {
  test('legacy identity cannot collide with a handoff parent key', () {
    expect(groupActivities([
      {'identity_key': 'same'},
      {'identity_key': 'other', 'handoff_event_key': 'same'},
    ]), hasLength(2));
  });
  test('one card groups a parent and distinct offers without losing links', () {
    final groups = groupActivities([
      {'identity_key': 'a', 'handoff_event_key': 'offer:a', 'parent_event_key': 'main:a', 'handoff_details': {'record_type': 'offer'}},
      {'identity_key': 'b', 'handoff_event_key': 'main:a', 'handoff_details': {'record_type': 'main'}},
      {'identity_key': 'c', 'handoff_event_key': 'offer:b', 'parent_event_key': 'main:a', 'handoff_details': {'record_type': 'offer'}},
    ]);
    expect(groups, hasLength(1));
    expect(groups.single, hasLength(3));
    expect(groups.single.first['identity_key'], 'b');
  });

  testWidgets('save and cancel only write when the user chooses', (tester) async {
    final api = _Api();
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      curatedActionsProvider.overrideWith((ref) async => {'items': [
        {'activity_id': 'one', 'kind': 'save', 'active': api.saved},
      ]}),
    ], child: MaterialApp(home: Scaffold(body: SingleChildScrollView(
      child: CuratedActivityCard(items: const [
        {'identity_key': 'one', 'title': '測試活動', 'importance': 5,
         'original_url': 'https://example.org/e'},
      ]),
    )))));
    await tester.pumpAndSettle();
    expect(api.calls, isEmpty);
    expect(find.textContaining('未知'), findsWidgets);
    final save = find.widgetWithText(FilterChip, '收藏');
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();
    expect(api.calls.single['active'], true);
    await tester.tap(save);
    await tester.pumpAndSettle();
    expect(api.calls, hasLength(2));
    expect(api.calls.last['active'], false);
  });
}
