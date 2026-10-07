import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/habit_api.dart';
import 'package:life_assistant/web/habits_page.dart';

class _FakeHabitApi implements HabitApi {
  _FakeHabitApi({
    List<Map<String, dynamic>>? habits,
    Map<String, List<Map<String, dynamic>>>? completions,
    this.loadError,
  })  : habits = habits ?? <Map<String, dynamic>>[],
        completions = completions ?? <String, List<Map<String, dynamic>>>{};

  final List<Map<String, dynamic>> habits;
  final Map<String, List<Map<String, dynamic>>> completions;
  final Object? loadError;
  Map<String, dynamic>? createdBody;
  final List<Map<String, dynamic>> updatedBodies = <Map<String, dynamic>>[];
  final List<String> completedIds = <String>[];
  int _nextId = 1;

  @override
  Future<List<Map<String, dynamic>>> getHabits() async {
    if (loadError != null) throw loadError!;
    return habits.map(Map<String, dynamic>.from).toList();
  }

  @override
  Future<Map<String, dynamic>> createHabit(Map<String, dynamic> body) async {
    createdBody = Map<String, dynamic>.from(body);
    final habit = <String, dynamic>{
      'id': 'habit-new-${_nextId++}',
      'is_active': true,
      'created_at': '2026-10-07T00:00:00Z',
      ...body,
    };
    habits.insert(0, habit);
    completions[habit['id'] as String] = <Map<String, dynamic>>[];
    return Map<String, dynamic>.from(habit);
  }

  @override
  Future<Map<String, dynamic>> updateHabit(
    String id,
    Map<String, dynamic> body,
  ) async {
    updatedBodies.add(Map<String, dynamic>.from(body));
    final habit = habits.firstWhere((item) => item['id'] == id);
    habit.addAll(body);
    return Map<String, dynamic>.from(habit);
  }

  @override
  Future<Map<String, dynamic>> completeHabit(String id) async {
    completedIds.add(id);
    final completion = <String, dynamic>{
      'id': 'completion-${completedIds.length}',
      'habit_id': id,
      'completed_at': '2026-10-07T01:30:00Z',
    };
    completions.putIfAbsent(id, () => <Map<String, dynamic>>[]).insert(
          0,
          completion,
        );
    return completion;
  }

  @override
  Future<List<Map<String, dynamic>>> getHabitCompletions(String id) async =>
      (completions[id] ?? const <Map<String, dynamic>>[])
          .map(Map<String, dynamic>.from)
          .toList();
}

Map<String, dynamic> _habit({
  required String id,
  required String title,
  String recurrence = 'FREQ=DAILY',
  String? reminder = '07:30',
}) =>
    <String, dynamic>{
      'id': id,
      'title': title,
      'recurrence_rule': recurrence,
      'reminder_time': reminder,
      'is_active': true,
      'created_at': '2026-10-06T00:00:00Z',
    };

Map<String, dynamic> _completion(String id, String habitId, String at) =>
    <String, dynamic>{
      'id': id,
      'habit_id': habitId,
      'completed_at': at,
    };

Future<void> _pumpHabitsPage(
  WidgetTester tester,
  HabitApi api, {
  Size size = const Size(1200, 900),
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [habitApiProvider.overrideWithValue(api)],
      child: MaterialApp(theme: AppTheme.light, home: const HabitsPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders recurrence reminder and append-only completion history', (
    tester,
  ) async {
    final api = _FakeHabitApi(
      habits: [_habit(id: 'h1', title: '晨間快走')],
      completions: {
        'h1': [
          _completion('c1', 'h1', '2026-10-07T00:15:00Z'),
          _completion('c0', 'h1', '2026-10-06T00:15:00Z'),
        ],
      },
    );

    await _pumpHabitsPage(tester, api);

    expect(find.text('晨間快走'), findsOneWidget);
    expect(find.text('每日'), findsOneWidget);
    expect(find.text('提醒 07:30'), findsOneWidget);
    expect(find.text('完成紀錄 2 筆'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('habit-history-h1')));
    await tester.pumpAndSettle();

    expect(find.text('晨間快走 · 完成紀錄'), findsOneWidget);
    expect(find.textContaining('2026/10/7'), findsOneWidget);
    expect(find.textContaining('2026/10/6'), findsOneWidget);
  });

  testWidgets('creates edits and records a completion through HabitApi', (
    tester,
  ) async {
    final api = _FakeHabitApi(
      habits: [_habit(id: 'h1', title: '晨間快走')],
    );
    await _pumpHabitsPage(tester, api);

    await tester.tap(find.text('新增習慣').first);
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('habit-title-field')),
      '晚間伸展',
    );
    await tester.enterText(
      find.byKey(const ValueKey('habit-reminder-field')),
      '21:30',
    );
    await tester.tap(find.byKey(const ValueKey('habit-save-button')));
    await tester.pumpAndSettle();

    expect(api.createdBody?['title'], '晚間伸展');
    expect(api.createdBody?['recurrence_rule'], 'FREQ=DAILY');
    expect(api.createdBody?['reminder_time'], '21:30');
    expect(find.text('習慣已新增'), findsOneWidget);
    expect(find.text('晚間伸展'), findsOneWidget);

    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('編輯習慣：晚間伸展'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('habit-title-field')),
      '睡前伸展',
    );
    await tester.enterText(
      find.byKey(const ValueKey('habit-reminder-field')),
      '22:00',
    );
    await tester.tap(find.byKey(const ValueKey('habit-save-button')));
    await tester.pumpAndSettle();

    expect(api.updatedBodies.last['title'], '睡前伸展');
    expect(api.updatedBodies.last['reminder_time'], '22:00');
    expect(find.text('睡前伸展'), findsOneWidget);

    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('habit-complete-habit-new-1')));
    await tester.pumpAndSettle();

    expect(api.completedIds, ['habit-new-1']);
    expect(find.text('完成紀錄 1 筆'), findsOneWidget);
    expect(find.textContaining('已記錄「睡前伸展」完成'), findsOneWidget);
  });

  testWidgets('validates reminder time and supports mobile empty state', (
    tester,
  ) async {
    final api = _FakeHabitApi();
    await _pumpHabitsPage(
      tester,
      api,
      size: const Size(390, 844),
    );

    expect(find.text('還沒有習慣'), findsOneWidget);
    expect(find.byTooltip('新增習慣'), findsOneWidget);

    await tester.tap(find.text('新增習慣'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('habit-title-field')),
      '喝水',
    );
    await tester.enterText(
      find.byKey(const ValueKey('habit-reminder-field')),
      '25:99',
    );
    await tester.tap(find.byKey(const ValueKey('habit-save-button')));
    await tester.pumpAndSettle();

    expect(find.text('請使用 HH:mm，例如 07:30'), findsOneWidget);
    expect(api.createdBody, isNull);
  });

  testWidgets('shows explicit load error and retry state', (tester) async {
    final api = _FakeHabitApi(loadError: StateError('backend unavailable'));
    await _pumpHabitsPage(tester, api);

    expect(find.text('無法載入習慣'), findsOneWidget);
    expect(find.textContaining('backend unavailable'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '重試'), findsOneWidget);
  });
}
