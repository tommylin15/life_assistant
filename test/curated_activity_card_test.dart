import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/curated_activity_card.dart';
import 'package:life_assistant/web/platform_api.dart';
import 'package:life_assistant/web/session_identity.dart';

class _Api extends PlatformApi {
  final calls = <Map<String, dynamic>>[];
  final reads = <String>[];
  bool saved = false;

  @override
  Future<Map<String, dynamic>> get(String path) async {
    reads.add(path);
    return {'items': const []};
  }

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
      {'identity_key': 'a', 'handoff_event_key': 'offer:a',
       'parent_event_key': 'main:a', 'handoff_details': {'record_type': 'offer'}},
      {'identity_key': 'b', 'handoff_event_key': 'main:a',
       'handoff_details': {'record_type': 'main'}},
      {'identity_key': 'c', 'handoff_event_key': 'offer:b',
       'parent_event_key': 'main:a', 'handoff_details': {'record_type': 'offer'}},
    ]);
    expect(groups, hasLength(1));
    expect(groups.single, hasLength(3));
    expect(groups.single.first['identity_key'], 'b');
  });

  testWidgets('saved expired activity remains labeled, not silently disguised', (tester) async {
    final api = _Api();
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      sessionIdentityProvider.overrideWithValue('sample@tests.local'),
    ], child: MaterialApp(home: Scaffold(body: SingleChildScrollView(
      child: CuratedActivityCard(entry: 'opportunities', items: const [
        {'identity_key': 'historic', 'title': '過往優惠', 'importance': 5,
         'ends_on': '2001-01-01', 'registration_status': 'closed',
         'saved': true, 'handoff_details': {},
         'original_url': 'https://example.org/historic'},
      ]),
    )))));
    await tester.pumpAndSettle();
    expect(find.text('已結束／截止'), findsOneWidget);
    expect(find.textContaining('★'), findsNothing);
    expect(find.byTooltip('取消收藏'), findsOneWidget);
  });

  testWidgets('two cards on the same page share one action read', (tester) async {
    final api = _Api();
    final first = List.filled(64, 'a').join();
    final second = List.filled(64, 'b').join();
    final sharedIds = '${first},${second}';
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      sessionIdentityProvider.overrideWithValue('batch@tests.local'),
    ], child: MaterialApp(home: Scaffold(body: SingleChildScrollView(child: Column(children: [
      CuratedActivityCard(
        actionIds: sharedIds,
        items: [{'identity_key': first, 'title': '親子活動',
          'handoff_details': const {}, 'original_url': 'https://example.org/a'}]),
      CuratedActivityCard(
        actionIds: sharedIds,
        items: [{'identity_key': second, 'title': '城市漫遊',
          'handoff_details': const {}, 'original_url': 'https://example.org/b'}]),
    ]))))));
    await tester.pumpAndSettle();
    expect(api.reads.where((path) => path.contains('/actions?activity_ids=')).length, 1);
    await tester.tap(find.byTooltip('收藏').first);
    await tester.pumpAndSettle();
    // Both cards see the same refreshed state through a single provider call.
    expect(api.reads.where((path) => path.contains('/actions?activity_ids=')).length, 2);
  });

  testWidgets('V3 card hides stars and toggles main bookmark explicitly', (tester) async {
    final api = _Api();
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      sessionIdentityProvider.overrideWithValue('sample@tests.local'),
    ], child: MaterialApp(home: Scaffold(body: SingleChildScrollView(
      child: CuratedActivityCard(items: const [
        {'identity_key': 'one', 'title': '測試活動', 'importance': 5,
         'category': '親子活動', 'handoff_details': {'organizer': '文學館',
           'record_type': 'main',
           'opportunity_type': '報名', 'district': '中西區'},
         'original_url': 'https://example.org/e'},
      ]),
    )))));
    await tester.pumpAndSettle();
    expect(api.calls, isEmpty);
    expect(find.text('測試活動'), findsWidgets);
    expect(find.textContaining('★'), findsNothing);
    await tester.tap(find.byTooltip('收藏'));
    await tester.pumpAndSettle();
    expect(api.calls.single['active'], true);
    expect(api.calls.single['path'].toString(), contains('/one/actions/save'));
    await tester.tap(find.byTooltip('取消收藏'));
    await tester.pumpAndSettle();
    expect(api.calls, hasLength(2));
    expect(api.calls.last['active'], false);
  });
}
