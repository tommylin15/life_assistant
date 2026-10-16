import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/life_capture_page.dart';
import 'package:life_assistant/web/platform_api.dart';

class _CaptureApi extends PlatformApi {
  int interpreted = 0;
  int articlesFetched = 0;
  int committed = 0;
  final writes = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    if (path == '/inbox/interpret') {
      interpreted++;
      return {
        'classification_source': 'rules',
        'saved': false,
        'candidates': [
          {
            'proposal_id': 'p1', 'target': 'note',
            'fields': {'body': body['text'], 'title': ''},
            'select_default': true, 'ambiguities': [],
          }
        ],
      };
    }
    if (path == '/inbox/article-preview') {
      articlesFetched++;
      return {
        'status': 'ok', 'saved': false,
        'source_url': body['url'], 'source_title': '文章示意',
        'key_points': ['重點一', '重點二'], 'uncertainties': ['資訊待確認'],
      };
    }
    if (path == '/inbox/commit') {
      committed++;
      writes.add(body);
      return {
        'status': 'COMPLETE',
        'results': [
          for (final entry in body['items'] as List)
            {
              'action_id': (entry as Map)['action_id'],
              'target': entry['target'], 'status': 'CREATED',
              'entity_id': 'sample-id',
            }
        ],
      };
    }
    throw StateError('Unexpected path: $path');
  }
}

void main() {
  Future<void> mount(WidgetTester tester, _CaptureApi api) async {
    tester.view.physicalSize = const Size(850, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      effectiveFeaturesProvider.overrideWith((ref) async => {'life_inbox': true}),
    ], child: const MaterialApp(home: LifeCapturePage())));
    await tester.pumpAndSettle();
  }

  testWidgets('classification and saving are two separate explicit actions', (tester) async {
    final api = _CaptureApi();
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        'https://example.com/article');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(api.interpreted, 1);
    expect(api.committed, 0);
    expect(api.articlesFetched, 0);
    expect(find.textContaining('確認後才會新增'), findsOneWidget);
    await tester.ensureVisible(find.textContaining('確認新增所選'));
    await tester.tap(find.textContaining('確認新增所選'));
    await tester.pumpAndSettle();
    expect(api.committed, 1);
    expect(api.writes.single['items'], hasLength(1));
    expect(find.textContaining('CREATED'), findsOneWidget);
    expect(find.textContaining('確認新增所選 0 項'), findsOneWidget);
  });

  testWidgets('web fetch is opt-in and does not save a note automatically', (tester) async {
    final api = _CaptureApi();
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        'https://example.com/article');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(api.articlesFetched, 0);
    await tester.ensureVisible(find.textContaining('擷取這個公開網址'));
    await tester.tap(find.textContaining('擷取這個公開網址'));
    await tester.pumpAndSettle();
    expect(api.articlesFetched, 1);
    expect(api.committed, 0);
  });
}
