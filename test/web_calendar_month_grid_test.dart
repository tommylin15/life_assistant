import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/calendar_api.dart';
import 'package:life_assistant/web/calendar_page.dart';

class _FakeCalendar implements CalendarApi {
  _FakeCalendar(this.items);

  final List<Map<String, dynamic>> items;

  @override
  Future<Map<String, dynamic>> status() async =>
      {'connected': true, 'granted_services': ['calendar']};

  @override
  Future<List<Map<String, dynamic>>> events(DateTime from, DateTime until) async => items;

  @override
  Future<Map<String, dynamic>> create(Map<String, dynamic> body) async => body;

  @override
  Future<Map<String, dynamic>> update(String id, Map<String, dynamic> body) async => body;

  @override
  Future<void> deleteConfirmed(String id) async {}

  @override
  String authorizationUrl() => '/auth/google';
}

String _dateString(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

void main() {
  testWidgets('month grid selects a day and keeps the agenda compact until details',
      (tester) async {
    tester.view.physicalSize = const Size(1000, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final today = DateTime.now();
    final day = DateTime(today.year, today.month, today.day == 1 ? 2 : 1);
    final tomorrow = DateTime(day.year, day.month, day.day + 1);
    final api = _FakeCalendar([{
      'id': 'meeting-1',
      'summary': '會議：行程討論',
      'description': '僅詳情才能看到的完整內容',
      'location': '會議室',
      'start': {'date': _dateString(day)},
      'end': {'date': _dateString(tomorrow)},
    }]);
    await tester.pumpWidget(ProviderScope(
      overrides: [calendarApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: CalendarPage()),
    ));
    await tester.pumpAndSettle();

    expect(find.byType(GridView), findsOneWidget);
    expect(find.byIcon(Icons.groups_outlined), findsWidgets);
    expect(find.text('僅詳情才能看到的完整內容'), findsNothing);

    final key = ValueKey('calendar-day-${day.year}/${day.month}/${day.day}');
    await tester.ensureVisible(find.byKey(key));
    await tester.tap(find.byKey(key));
    await tester.pumpAndSettle();

    final agenda = find.byKey(const ValueKey('calendar-agenda-meeting-1'));
    expect(agenda, findsOneWidget);
    await tester.ensureVisible(agenda);
    await tester.tap(agenda);
    await tester.pumpAndSettle();
    expect(find.text('僅詳情才能看到的完整內容'), findsOneWidget);
    expect(find.text('編輯'), findsOneWidget);
    expect(find.text('刪除'), findsOneWidget);
  });
}
