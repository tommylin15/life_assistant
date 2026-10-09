import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/calendar_api.dart';
import 'package:life_assistant/web/calendar_page.dart';

class _FakeCalendarApi implements CalendarApi {
  _FakeCalendarApi({this.connected = true, this.failure = false}) {
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, 10, 9);
    final end = start.add(const Duration(hours: 1));
    eventsData.add({
      'id': 'event-1',
      'summary': '會議',
      'description': '每週討論',
      'location': '線上',
      'start': {'dateTime': start.toUtc().toIso8601String()},
      'end': {'dateTime': end.toUtc().toIso8601String()},
    });
    eventsData.add({
      'id': 'all-day-1',
      'summary': '全天休假',
      'start': {'date': DateTime(today.year, today.month, 5)
          .toIso8601String().substring(0, 10)},
      'end': {'date': DateTime(today.year, today.month, 6)
          .toIso8601String().substring(0, 10)},
    });
  }

  final bool connected;
  final bool failure;
  final List<Map<String, dynamic>> eventsData = [];
  final List<Map<String, dynamic>> created = [];
  final List<Map<String, dynamic>> updated = [];
  final List<String> deleted = [];

  @override
  String authorizationUrl() => '/api/v1/integrations/google/authorize?services=calendar';

  @override
  Future<Map<String, dynamic>> status() async => {
    'connected': connected,
    'granted_services': connected ? ['calendar'] : <String>[],
  };

  @override
  Future<List<Map<String, dynamic>>> events(DateTime from, DateTime until) async {
    if (failure) throw Exception('Google unavailable');
    return eventsData;
  }

  @override
  Future<Map<String, dynamic>> create(Map<String, dynamic> body) async {
    created.add(Map.of(body));
    final event = {
      'id': 'new-1',
      'summary': body['summary'],
      'start': body['start_date'] != null
          ? {'date': body['start_date']}
          : {'dateTime': body['start']},
      'end': body['end_date'] != null
          ? {'date': body['end_date']}
          : {'dateTime': body['end']},
    };
    eventsData.add(event);
    return event;
  }

  @override
  Future<Map<String, dynamic>> update(
    String id, Map<String, dynamic> body,
  ) async {
    updated.add({'id': id, ...body});
    final event = eventsData.firstWhere((value) => value['id'] == id);
    event['summary'] = body['summary'];
    event['start'] = body['start_date'] != null
        ? {'date': body['start_date']}
        : {'dateTime': body['start']};
    event['end'] = body['end_date'] != null
        ? {'date': body['end_date']}
        : {'dateTime': body['end']};
    return event;
  }

  @override
  Future<void> deleteConfirmed(String id) async {
    deleted.add(id);
    eventsData.removeWhere((item) => item['id'] == id);
  }
}

Future<void> _pump(WidgetTester tester, _FakeCalendarApi api) async {
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: [calendarApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: CalendarPage()),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _pumpNested(WidgetTester tester, _FakeCalendarApi api) async {
  // MaterialApp owns the root navigator and the page lives inside another
  // Navigator, matching Flutter Web shells that nest navigation scopes.
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: [calendarApiProvider.overrideWithValue(api)],
      child: MaterialApp(
        home: Navigator(
          onGenerateRoute: (_) => MaterialPageRoute<void>(
            builder: (_) => const CalendarPage(),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('delete dialog returns result through root navigator even inside nested shell', (tester) async {
    final api = _FakeCalendarApi();
    await _pumpNested(tester, api);
    final delete = find.byKey(const ValueKey('calendar-delete-event-1'));
    await tester.ensureVisible(delete);
    await tester.tap(delete);
    await tester.pumpAndSettle();
    expect(find.text('確認刪除行程'), findsOneWidget);

    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(api.deleted, isEmpty);
    expect(find.text('確認刪除行程'), findsNothing);
    expect(find.text('會議'), findsOneWidget);

    final deleteAgain = find.byKey(const ValueKey('calendar-delete-event-1'));
    await tester.ensureVisible(deleteAgain);
    await tester.tap(deleteAgain);
    await tester.pumpAndSettle();
    await tester.tap(find.text('確認刪除'));
    await tester.pumpAndSettle();
    expect(api.deleted, ['event-1']);
    expect(find.text('確認刪除行程'), findsNothing);
    expect(find.text('會議'), findsNothing);
  });

  testWidgets('month view displays timed and all-day Google events', (tester) async {
    await _pump(tester, _FakeCalendarApi());
    expect(find.text('我的 Google 行程'), findsOneWidget);
    expect(find.text('會議'), findsOneWidget);
    expect(find.text('全天休假'), findsOneWidget);
    expect(find.text('地點：線上'), findsOneWidget);
    expect(find.text('共 2 筆'), findsOneWidget);
  });

  testWidgets('calendar create sends timezone-aware timestamps', (tester) async {
    final api = _FakeCalendarApi();
    await _pump(tester, api);

    await tester.tap(find.text('新增行程'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('calendar-title-field')), '醫院回診');
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();

    expect(api.created.single['summary'], '醫院回診');
    expect(DateTime.parse(api.created.single['start'] as String).isUtc, true);
    expect(find.text('醫院回診'), findsOneWidget);
  });

  testWidgets('calendar edit updates the selected Google event', (tester) async {
    final api = _FakeCalendarApi();
    await _pump(tester, api);

    final edit = find.byKey(const ValueKey('calendar-edit-event-1'));
    await tester.ensureVisible(edit);
    await tester.pumpAndSettle();
    await tester.tap(edit);
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const ValueKey('calendar-title-field')), '工作會議');
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();
    expect(api.updated.single['id'], 'event-1');
    expect(api.updated.single['summary'], '工作會議');
    expect(DateTime.parse(api.updated.single['start'] as String).isUtc, true);
    // A renamed event must also expose the updated accessible action label.
    expect(find.byTooltip('刪除行程：工作會議'), findsOneWidget);
    expect(find.byTooltip('刪除行程：會議'), findsNothing);
  });

  testWidgets('delete requires explicit confirmation', (tester) async {
    final api = _FakeCalendarApi();
    await _pump(tester, api);

    final button = find.byKey(const ValueKey('calendar-delete-event-1'));
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pumpAndSettle();
    expect(find.text('確認刪除行程'), findsOneWidget);
    expect(api.deleted, isEmpty);

    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(api.deleted, isEmpty);

    await tester.tap(button);
    await tester.pumpAndSettle();
    await tester.tap(find.text('確認刪除'));
    await tester.pumpAndSettle();
    expect(api.deleted, ['event-1']);
    expect(find.text('會議'), findsNothing);
  });

  testWidgets('all-day edit keeps date fields and exclusive end', (tester) async {
    final api = _FakeCalendarApi();
    await _pump(tester, api);
    final edit = find.byKey(const ValueKey('calendar-edit-all-day-1'));
    await tester.ensureVisible(edit);
    await tester.tap(edit);
    await tester.pumpAndSettle();

    expect(find.byType(SwitchListTile), findsOneWidget);
    expect(tester.widget<SwitchListTile>(find.byType(SwitchListTile)).value, true);
    await tester.enterText(find.byKey(const ValueKey('calendar-title-field')), '新假期');
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();

    final today = DateTime.now();
    final start = DateTime(today.year, today.month, 5).toIso8601String().substring(0, 10);
    final exclusive = DateTime(today.year, today.month, 6).toIso8601String().substring(0, 10);
    expect(api.updated.single['start_date'], start);
    expect(api.updated.single['end_date'], exclusive);
    expect(api.updated.single.containsKey('start'), false);
    expect(find.text('新假期'), findsOneWidget);
  });

  testWidgets('all-day create sends civil dates, not UTC timestamps', (tester) async {
    final api = _FakeCalendarApi();
    await _pump(tester, api);
    await tester.tap(find.text('新增行程'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('calendar-title-field')), '全天研討');
    await tester.tap(find.byType(SwitchListTile));
    await tester.pumpAndSettle();
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();

    expect(api.created.single['start_date'], isNotNull);
    expect(api.created.single['end_date'], isNotNull);
    expect(api.created.single.containsKey('start'), false);
    expect(find.text('全天研討'), findsOneWidget);
  });

  testWidgets('shows connect, empty, and error states', (tester) async {
    await _pump(tester, _FakeCalendarApi(connected: false));
    expect(find.text('尚未連結 Google Calendar'), findsOneWidget);

    final empty = _FakeCalendarApi()..eventsData.clear();
    await _pump(tester, empty);
    expect(find.text('本月還沒有行程'), findsOneWidget);

    await _pump(tester, _FakeCalendarApi(failure: true));
    expect(find.text('無法載入日曆'), findsOneWidget);
    expect(find.text('重試'), findsOneWidget);
  });
}
