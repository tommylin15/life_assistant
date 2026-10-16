import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/api_client.dart';
import 'package:life_assistant/web/platform_api.dart';
import 'package:life_assistant/web/session_identity.dart';
import 'package:life_assistant/web/today_page.dart';

class _FakeHomeApi extends ApiClient {
  int projectReads = 0;
  List<Map<String, dynamic>> tasksData = [];

  @override
  Future<List<Map<String, dynamic>>> getTasks() async => tasksData;

  @override
  Future<List<Map<String, dynamic>>> getProjects() async {
    projectReads++;
    throw StateError('API 403: legacy projects are not tenant scoped');
  }

  @override
  Future<Map<String, dynamic>> getCalendarEvents({
    required DateTime timeMin,
    required DateTime timeMax,
    int limit = 1,
  }) async => {'events': []};
}

Future<void> _mountHome(WidgetTester tester, _FakeHomeApi api,
    {required bool projectsAvailable, List<String>? homeCards}) async {
  tester.view.physicalSize = const Size(1200, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(ProviderScope(overrides: [
    sessionIdentityProvider.overrideWithValue('staging-test-user'),
    apiClientProvider.overrideWithValue(api),
    uiPreferencesProvider.overrideWith((ref) async => {
      'revision': 0,
      'home_cards': homeCards ?? ['tasks', 'calendar', 'projects'],
    }),
    effectiveFeaturesProvider.overrideWith((ref) async => {
      'today': true,
      'tasks': true,
      'calendar': true,
      'projects': projectsAvailable,
    }),
  ], child: const MaterialApp(home: TodayPage())));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('staging tester sees home without contacting unsafe legacy projects',
      (tester) async {
    final api = _FakeHomeApi();
    await _mountHome(tester, api, projectsAvailable: false);
    expect(find.text('待辦事項'), findsOneWidget);
    expect(find.text('首頁資料暫時無法讀取，點此重試'), findsNothing);
    expect(api.projectReads, 0);
  });

  testWidgets('home preserves tasks when optional projects API fails',
      (tester) async {
    final api = _FakeHomeApi();
    await _mountHome(tester, api, projectsAvailable: true);
    expect(find.text('待辦事項'), findsOneWidget);
    expect(find.text('專案資料目前無法取得'), findsOneWidget);
    expect(api.projectReads, greaterThanOrEqualTo(1));
  });
  testWidgets('home merges overdue alert and tasks without duplicate card',
      (tester) async {
    final now = DateTime.now();
    final api = _FakeHomeApi()..tasksData = [
      {'title': '逾期帳單', 'status': 'pending',
        'due_at': DateTime(now.year, now.month, now.day - 1, 12).toIso8601String()},
      {'title': '今天會議', 'status': 'pending',
        'due_at': DateTime(now.year, now.month, now.day, 13).toIso8601String()},
      {'title': '下週計畫', 'status': 'pending',
        'due_at': DateTime(now.year, now.month, now.day + 7).toIso8601String()},
      {'title': '未排日期', 'status': 'pending', 'due_at': null},
      {'title': '已完成事項', 'status': 'completed',
        'due_at': DateTime(now.year, now.month, now.day - 1).toIso8601String()},
    ];
    await _mountHome(tester, api, projectsAvailable: false,
        homeCards: ['attention', 'tasks']);
    expect(find.text('待辦事項'), findsOneWidget);
    expect(find.text('需要關注'), findsNothing);
    expect(find.textContaining('逾期 1'), findsOneWidget);
    expect(find.textContaining('今日到期 1'), findsOneWidget);
    expect(find.textContaining('待完成 4'), findsOneWidget);
    expect(find.textContaining('逾期帳單 · 今天會議'), findsOneWidget);
    expect(find.textContaining('已完成事項'), findsNothing);
  });

  testWidgets('legacy attention-only setting becomes a single tasks card',
      (tester) async {
    final api = _FakeHomeApi();
    await _mountHome(tester, api, projectsAvailable: false,
        homeCards: ['attention']);
    expect(find.text('待辦事項'), findsOneWidget);
    expect(find.text('需要關注'), findsNothing);
    expect(find.textContaining('待完成 0'), findsOneWidget);
    expect(find.textContaining('目前沒有待完成事項'), findsOneWidget);
  });

}
