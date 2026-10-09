import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/free_events_api.dart';
import 'package:life_assistant/web/free_events_page.dart';
import 'package:life_assistant/web/browser_navigation.dart';

class _FakeFreeEventsApi implements FreeEventsApi {
  _FakeFreeEventsApi({this.items = const [], this.error});
  final List<Map<String, dynamic>> items;
  final Object? error;
  int calls = 0;

  @override
  Future<List<Map<String, dynamic>>> listVerified({int limit = 20}) async {
    calls += 1;
    if (error != null) throw error!;
    return items;
  }
}

class _FakeNavigation implements BrowserNavigation {
  final List<String> opened = [];
  @override
  Future<void> openExternal(String url) async => opened.add(url);
}

Map<String, dynamic> _item({bool windowConfirmedOpen = false}) => {
  'event_id': 'event-1',
  'session_id': 'session-1',
  'opportunity_id': 'ticket-1',
  'title': '市立藝文活動',
  'summary': '詳細內容以官方活動與報名頁為準。',
  'city': '台北',
  'venue': '文化中心',
  'starts_at': '2026-10-24T09:00:00+08:00',
  'starts_on': null,
  'fee_kind': 'conditional_free',
  'eligibility_note': '須符合居民資格',
  'window_confirmed_open': windowConfirmedOpen,
  'registration_opens_at': null,
  'official_url': 'https://organizer.example.tw/event',
  'registration_url': 'https://organizer.example.tw/register',
};

Future<void> _pump(
  WidgetTester tester, _FakeFreeEventsApi api, _FakeNavigation navigator,
  {Size size = const Size(1200, 900)}
) async {
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: [
        freeEventsApiProvider.overrideWithValue(api),
        browserNavigationProvider.overrideWithValue(navigator),
      ],
      child: MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: const FreeEventsPage(),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders verified-only card with unknown registration start', (tester) async {
    final api = _FakeFreeEventsApi(items: [_item()]);
    final navigator = _FakeNavigation();
    await _pump(tester, api, navigator);
    expect(find.text('台灣免費活動'), findsOneWidget);
    expect(find.text('市立藝文活動'), findsOneWidget);
    expect(find.text('有條件免費（請看資格）'), findsOneWidget);
    expect(find.text('報名開始時間未確認'), findsOneWidget);
    expect(find.text('免費資格：須符合居民資格'), findsOneWidget);
    expect(find.text('前往原站不代表已報名；請自行確認是否額滿與費用。'), findsOneWidget);
    expect(api.calls, 1);
    expect(navigator.opened, isEmpty);
  });

  testWidgets('the two outbound links are opt-in and separate', (tester) async {
    final api = _FakeFreeEventsApi(items: [_item()]);
    final navigator = _FakeNavigation();
    await _pump(tester, api, navigator);
    await tester.tap(find.byKey(const ValueKey('free-event-source-ticket-1')));
    await tester.pump();
    expect(navigator.opened, ['https://organizer.example.tw/event']);
    await tester.ensureVisible(find.byKey(const ValueKey('free-event-register-ticket-1')));
    await tester.tap(find.byKey(const ValueKey('free-event-register-ticket-1')));
    await tester.pump();
    expect(navigator.opened, [
      'https://organizer.example.tw/event',
      'https://organizer.example.tw/register',
    ]);
  });

  testWidgets('no activity and provider failure are not fake recommendations', (tester) async {
    await _pump(tester, _FakeFreeEventsApi(), _FakeNavigation(),
      size: const Size(390, 844));
    expect(find.text('目前沒有已核實的免費活動'), findsOneWidget);
    expect(find.text('未核實候選不會顯示。', findRichText: true), findsNothing);

    await _pump(tester, _FakeFreeEventsApi(error: Exception('offline')),
        _FakeNavigation(), size: const Size(390, 844));
    expect(find.text('無法載入活動'), findsOneWidget);
    expect(find.text('重試'), findsOneWidget);
  });

  testWidgets('confirmed date alone is never described as seat availability', (tester) async {
    await _pump(tester,
        _FakeFreeEventsApi(items: [_item(windowConfirmedOpen: true)]),
        _FakeNavigation());
    expect(find.text('已核實報名時段 · 原站仍需確認名額'), findsOneWidget);
    expect(find.text('已報名'), findsNothing);
  });
}
