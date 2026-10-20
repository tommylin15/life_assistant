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
  Map<String, dynamic>? fakeCandidate;
  List<Map<String, dynamic>>? fakeCandidates;
  Map<String, dynamic>? fakeDateHint;
  String fakeCommitStatus = 'CREATED';

  @override
  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    if (path == '/inbox/interpret') {
      interpreted++;
      return {
        'classification_source': 'rules',
        'saved': false,
        'date_hint': fakeDateHint,
        'candidates': fakeCandidates ?? [
          fakeCandidate ?? {
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
        'status': fakeCommitStatus == 'CREATED' ? 'COMPLETE' : 'PARTIAL',
        'results': [
          for (final entry in body['items'] as List)
            {
              'action_id': (entry as Map)['action_id'],
              'target': entry['target'], 'status': fakeCommitStatus,
              'entity_id': 'sample-id',
            }
        ],
      };
    }
    throw StateError('Unexpected path: $path');
  }
}

void main() {
  Future<void> mount(WidgetTester tester, _CaptureApi api,
      {double height = 1000}) async {
    tester.view.physicalSize = Size(850, height);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(ProviderScope(overrides: [
      platformApiProvider.overrideWithValue(api),
      effectiveFeaturesProvider.overrideWith((ref) async => {'life_inbox': true}),
    ], child: const MaterialApp(home: LifeCapturePage())));
    await tester.pumpAndSettle();
  }

  testWidgets('multiple suggestions preserve per-action dates and write only selected',
      (tester) async {
    final api = _CaptureApi()
      ..fakeDateHint = {
        'precision': 'day', 'date': '2026-10-22', 'year': 2026,
        'month': 10, 'day': 22, 'raw': '明天'
      }
      ..fakeCandidates = [
        {
          'proposal_id': 'p1', 'target': 'task',
          'fields': {'title': '明天提交報告'}, 'select_default': true,
          'date_hint': {
            'precision': 'day', 'date': '2026-10-22', 'year': 2026,
            'month': 10, 'day': 22, 'raw': '明天'
          }, 'evidence_spans': ['明天提交報告'], 'ambiguities': []
        },
        {
          'proposal_id': 'p2', 'target': 'task',
          'fields': {'title': '繳電費'}, 'select_default': true,
          'date_hint': null, 'evidence_spans': ['繳電費'], 'ambiguities': []
        }
      ];
    await mount(tester, api, height: 1900);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        '明天提交報告，記得繳電費');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('capture-candidate-0')), findsOneWidget);
    expect(find.byKey(const ValueKey('capture-candidate-1')), findsOneWidget);
    expect(find.textContaining('辨識建議（2 項'), findsOneWidget);
    await tester.ensureVisible(find.textContaining('確認新增所選 2 項'));
    await tester.tap(find.textContaining('確認新增所選 2 項'));
    await tester.pumpAndSettle();
    expect(api.committed, 1);
    final items = api.writes.single['items'] as List;
    expect(items, hasLength(2));
    expect((items[0]['fields'] as Map)['due_at'], '2026-10-22T23:59:00+08:00');
    expect((items[1]['fields'] as Map).containsKey('due_at'), false);
  });

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

  testWidgets('FAILED inbox write stays editable; UNKNOWN remains locked', (tester) async {
    for (final outcome in ['FAILED', 'UNKNOWN']) {
      final api = _CaptureApi()..fakeCommitStatus = outcome;
      await mount(tester, api);
      await tester.enterText(find.byKey(const ValueKey('capture-input')),
          '買牛奶的備忘');
      await tester.tap(find.text('智慧辨識'));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.textContaining('確認新增所選 1 項'));
      await tester.tap(find.textContaining('確認新增所選 1 項'));
      await tester.pumpAndSettle();
      expect(api.committed, 1);
      expect(find.textContaining(outcome), findsOneWidget);
      if (outcome == 'FAILED') {
        expect(find.textContaining('部分項目未建立'), findsOneWidget);
        expect(find.text('確認後才會新增'), findsOneWidget);
        api.fakeCommitStatus = 'CREATED';
        final checkbox = find.byType(CheckboxListTile).first;
        await tester.ensureVisible(checkbox);
        await tester.tap(checkbox);
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.textContaining('確認新增所選 1 項'));
        await tester.tap(find.textContaining('確認新增所選 1 項'));
        await tester.pumpAndSettle();
        expect(api.committed, 2);
      } else {
        expect(find.text('已處理，避免重複送出'), findsOneWidget);
        expect(find.textContaining('確認新增所選 0 項'), findsOneWidget);
      }
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
    }
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
  testWidgets('complete date fills task deadline without ISO typing', (tester) async {
    final api = _CaptureApi()
      ..fakeDateHint = {
        'precision': 'day', 'raw': '2026/11/05',
        'date': '2026-11-05', 'year': 2026, 'month': 11, 'day': 5,
      }
      ..fakeCandidate = {
        'proposal_id': 'p1', 'target': 'task',
        'fields': {'title': '寄回文件'},
        'select_default': true, 'ambiguities': [],
      };
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        '2026/11/05 寄回文件');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('capture-task-due-0')), findsOneWidget);
    expect(find.textContaining('2026-11-05 23:59'), findsOneWidget);
    expect(find.textContaining('ISO8601（'), findsNothing);
    await tester.ensureVisible(find.textContaining('確認新增所選 1 項'));
    await tester.tap(find.textContaining('確認新增所選 1 項'));
    await tester.pumpAndSettle();
    final row = (api.writes.single['items'] as List).single as Map;
    expect((row['fields'] as Map)['due_at'], '2026-11-05T23:59:00+08:00');
  });

  testWidgets('month and day only requires calendar picker and no guessed year',
      (tester) async {
    final api = _CaptureApi()
      ..fakeDateHint = {
        'precision': 'month_day', 'raw': '11月5日', 'month': 11, 'day': 5,
      }
      ..fakeCandidate = {
        'proposal_id': 'p1', 'target': 'task',
        'fields': {'title': '準備資料'},
        'select_default': false, 'ambiguities': ['日期不完整，請確認'],
      };
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        '11月5日準備資料');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.textContaining('缺少年份'), findsOneWidget);
    expect(find.textContaining('未設定（點選萬年曆）'), findsOneWidget);
    expect(api.committed, 0);
    await tester.ensureVisible(find.byKey(const ValueKey('capture-task-due-0')));
    await tester.tap(find.byKey(const ValueKey('capture-task-due-0')));
    await tester.pumpAndSettle();
    expect(find.byType(DatePickerDialog), findsOneWidget);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(api.committed, 0);
  });

  testWidgets('picker confirmation supplies missing year before creating task',
      (tester) async {
    final api = _CaptureApi()
      ..fakeDateHint = {
        'precision': 'month_day', 'raw': '11月5日', 'month': 11, 'day': 5,
      }
      ..fakeCandidate = {
        'proposal_id': 'p1', 'target': 'task',
        'fields': {'title': '交報告'},
        'select_default': false, 'ambiguities': ['缺少年份'],
      };
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        '11月5日交報告');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.textContaining('確認新增所選 0 項'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const ValueKey('capture-task-due-0')));
    await tester.tap(find.byKey(const ValueKey('capture-task-due-0')));
    await tester.pumpAndSettle();
    expect(find.byType(DatePickerDialog), findsOneWidget);
    await tester.tap(find.text('確認'));
    await tester.pumpAndSettle();
    expect(find.textContaining('確認新增所選 1 項'), findsOneWidget);
    await tester.ensureVisible(find.textContaining('確認新增所選 1 項'));
    await tester.tap(find.textContaining('確認新增所選 1 項'));
    await tester.pumpAndSettle();
    final fields = ((api.writes.single['items'] as List).single as Map)['fields'] as Map;
    expect(fields['due_at'], '${DateTime.now().year}-11-05T23:59:00+08:00');
  });

  testWidgets('calendar missing end stays disabled until picker supplies date',
      (tester) async {
    final api = _CaptureApi()
      ..fakeCandidate = {
        'proposal_id': 'p1', 'target': 'calendar',
        'fields': {'summary': '活動'},
        'select_default': true, 'ambiguities': ['請補齊行程開始與結束時間或全日日期'],
      };
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')), '活動安排');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.textContaining('確認新增所選 0 項'), findsOneWidget);
    expect(find.textContaining('請使用萬年曆補齊有效日期'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const ValueKey('capture-calendar-start-date-0')));
    await tester.tap(find.byKey(const ValueKey('capture-calendar-start-date-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('確認'));
    await tester.pumpAndSettle();
    expect(find.textContaining('確認新增所選 1 項'), findsOneWidget);
    await tester.ensureVisible(find.textContaining('確認新增所選 1 項'));
    await tester.tap(find.textContaining('確認新增所選 1 項'));
    await tester.pumpAndSettle();
    final fields = ((api.writes.single['items'] as List).single as Map)['fields'] as Map;
    expect(fields['end_date'],
        DateTime.parse(fields['start_date'] as String)
            .add(const Duration(days: 1)).toIso8601String().substring(0, 10));
  });

  testWidgets('complete calendar date auto-fills exclusive end but shows inclusive',
      (tester) async {
    final api = _CaptureApi()
      ..fakeDateHint = {
        'precision': 'day', 'raw': '2026年12月31日',
        'date': '2026-12-31', 'year': 2026, 'month': 12, 'day': 31,
      }
      ..fakeCandidate = {
        'proposal_id': 'p1', 'target': 'calendar',
        'fields': {'summary': '參加活動'},
        'select_default': true, 'ambiguities': [],
      };
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        '2026年12月31日參加活動');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('capture-calendar-start-date-0')),
        findsOneWidget);
    expect(find.byKey(const ValueKey('capture-calendar-end-date-0')),
        findsOneWidget);
    expect(find.textContaining('2026-12-31'), findsNWidgets(2));
    await tester.ensureVisible(find.textContaining('確認新增所選 1 項'));
    await tester.tap(find.textContaining('確認新增所選 1 項'));
    await tester.pumpAndSettle();
    final row = (api.writes.single['items'] as List).single as Map;
    final fields = row['fields'] as Map;
    expect(fields['start_date'], '2026-12-31');
    expect(fields['end_date'], '2027-01-01');
    expect(fields.containsKey('start'), false);
  });

  testWidgets('timed calendar uses date and time selection controls',
      (tester) async {
    final api = _CaptureApi()
      ..fakeCandidate = {
        'proposal_id': 'p1', 'target': 'calendar',
        'fields': {
          'summary': '開會',
          'start': '2026-10-21T10:00:00+08:00',
          'end': '2026-10-21T11:00:00+08:00',
        },
        'select_default': true, 'ambiguities': [],
      };
    await mount(tester, api);
    await tester.enterText(find.byKey(const ValueKey('capture-input')),
        '10月21日 10點開會');
    await tester.tap(find.text('智慧辨識'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('capture-calendar-start-time-0')),
        findsOneWidget);
    expect(find.byKey(const ValueKey('capture-calendar-end-time-0')),
        findsOneWidget);
    expect(find.byKey(const ValueKey('capture-calendar-start-date-0')),
        findsNothing);
  });

}
