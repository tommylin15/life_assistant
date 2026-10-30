import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/curated_events_page.dart';
import 'package:life_assistant/web/platform_api.dart';
import 'package:life_assistant/web/session_identity.dart';

class _FakeApi extends PlatformApi {
  final reads = <String>[];

  @override
  Future<Map<String, dynamic>> get(String path) async {
    reads.add(path);
    if (path == '/ui/features') {
      return {
        'features': [
          {'key': 'explore', 'available': true},
          {'key': 'opportunities', 'available': true},
        ],
      };
    }
    if (path == '/free-events/curated/filters') {
      return {'cities': <String>[], 'categories': <String>[]};
    }
    if (path.startsWith('/free-events/curated?')) {
      return {'items': <Map<String, dynamic>>[], 'has_more': false};
    }
    throw StateError('Unexpected API request: $path');
  }
}

void main() {
  testWidgets('discovery shortcuts lead with latest_3d and keep three filters in More',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final api = _FakeApi();
    await tester.pumpWidget(ProviderScope(
      overrides: [
        platformApiProvider.overrideWithValue(api),
        sessionIdentityProvider.overrideWithValue('filters@tests.local'),
      ],
      child: const MaterialApp(home: CuratedEventsPage()),
    ));
    await tester.pumpAndSettle();

    expect(find.text('最近三日收錄'), findsOneWidget);
    expect(find.text('正在進行'), findsOneWidget);
    expect(tester.getTopLeft(find.text('最近三日收錄')).dx,
        lessThan(tester.getTopLeft(find.text('正在進行')).dx));
    expect(find.text('本週末'), findsOneWidget);
    expect(find.text('7 天內開始'), findsNothing);
    expect(find.text('30 天內開始'), findsNothing);
    expect(find.text('免費活動'), findsNothing);

    final more = find.byKey(const ValueKey('activity-more-quick-filters'));
    expect(more, findsOneWidget);
    await tester.tap(more);
    await tester.pumpAndSettle();
    expect(find.text('7 天內開始'), findsOneWidget);
    expect(find.text('30 天內開始'), findsOneWidget);
    expect(find.text('免費活動'), findsOneWidget);

    await tester.tap(find.text('7 天內開始'));
    await tester.pumpAndSettle();
    expect(find.text('更多：7 天內開始'), findsOneWidget);
    expect(api.reads
        .where((path) => path.startsWith('/free-events/curated?'))
        .any((path) =>
            Uri.parse(path).queryParameters['quick'] == 'next_7'), isTrue);

    // Selecting the same More item again clears the quick filter.
    await tester.tap(more);
    await tester.pumpAndSettle();
    await tester.tap(find.text('7 天內開始'));
    await tester.pumpAndSettle();
    expect(find.text('更多'), findsOneWidget);
    expect(api.reads
        .where((path) => path.startsWith('/free-events/curated?'))
        .any((path) =>
            !Uri.parse(path).queryParameters.containsKey('quick')), isTrue);
  });
}
