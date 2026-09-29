import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/task_api.dart';
import 'package:life_assistant/web/tasks_page.dart';

class _FakeTaskApi implements TaskApi {
  _FakeTaskApi({
    List<Map<String, dynamic>>? tasks,
    List<Map<String, dynamic>>? projects,
    List<Map<String, dynamic>>? checklist,
  })  : tasks = tasks ?? [],
        projects = projects ?? [],
        checklist = checklist ?? [];

  final List<Map<String, dynamic>> tasks;
  final List<Map<String, dynamic>> projects;
  final List<Map<String, dynamic>> checklist;
  Map<String, dynamic>? createdBody;

  @override
  Future<Map<String, dynamic>> createChecklistItem(
    String taskId,
    Map<String, dynamic> body,
  ) async =>
      {'id': 'c-new', 'task_id': taskId, 'is_done': false, ...body};

  @override
  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body) async {
    createdBody = Map<String, dynamic>.from(body);
    return {'id': 'new-task', 'status': 'pending', ...body};
  }

  @override
  Future<void> deleteChecklistItem(String taskId, String itemId) async {}

  @override
  Future<void> deleteTask(String id) async {}

  @override
  Future<void> completeTask(String id) async {}

  @override
  Future<List<Map<String, dynamic>>> getChecklistItems(String taskId) async =>
      checklist;

  @override
  Future<List<Map<String, dynamic>>> getProjects() async => projects;

  @override
  Future<List<Map<String, dynamic>>> getTasks() async => tasks;

  @override
  Future<Map<String, dynamic>> updateChecklistItem(
    String taskId,
    String itemId,
    Map<String, dynamic> body,
  ) async =>
      {'id': itemId, 'task_id': taskId, ...body};

  @override
  Future<Map<String, dynamic>> updateTask(
    String id,
    Map<String, dynamic> body,
  ) async =>
      {'id': id, ...body};
}

Future<void> _pumpTasksPage(WidgetTester tester, _FakeTaskApi api) async {
  tester.view.physicalSize = const Size(1200, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [taskApiProvider.overrideWithValue(api)],
      child: MaterialApp(theme: AppTheme.light, home: const TasksPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders task metadata and filters completed tasks', (tester) async {
    final api = _FakeTaskApi(
      projects: [
        {'id': 'p1', 'name': '搬家'},
      ],
      tasks: [
        {
          'id': 't1',
          'title': '確認搬家公司',
          'note': '比較最後兩家報價',
          'status': 'in_progress',
          'priority': 'high',
          'due_at': '2099-01-02T08:30:00Z',
          'reminder_at': '2099-01-02T07:30:00Z',
          'project_id': 'p1',
        },
        {
          'id': 't2',
          'title': '已完成項目',
          'note': null,
          'status': 'completed',
          'priority': 'normal',
          'due_at': null,
          'reminder_at': null,
          'project_id': null,
        },
      ],
    );

    await _pumpTasksPage(tester, api);

    expect(find.text('確認搬家公司'), findsOneWidget);
    expect(find.text('比較最後兩家報價'), findsOneWidget);
    expect(find.text('高優先'), findsOneWidget);
    expect(find.text('搬家'), findsOneWidget);
    expect(find.text('已完成項目'), findsNothing);

    await tester.tap(find.text('全部'));
    await tester.pumpAndSettle();
    expect(find.text('已完成項目'), findsOneWidget);
  });

  testWidgets('creates a task through the full editor', (tester) async {
    final api = _FakeTaskApi(
      projects: [
        {'id': 'p1', 'name': '工作'},
      ],
    );

    await _pumpTasksPage(tester, api);
    await tester.tap(find.text('新增待辦').first);
    await tester.pumpAndSettle();

    expect(find.text('新增待辦'), findsWidgets);
    expect(find.text('備註'), findsOneWidget);
    expect(find.text('優先度'), findsOneWidget);
    expect(find.text('專案'), findsOneWidget);
    expect(find.textContaining('到期時間'), findsOneWidget);
    expect(find.textContaining('提醒時間'), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey('task-title-field')),
      '整理週報',
    );
    await tester.tap(find.byKey(const ValueKey('task-save-button')));
    await tester.pumpAndSettle();

    expect(api.createdBody?['title'], '整理週報');
    expect(api.createdBody?['priority'], 'normal');
    expect(find.text('待辦已新增'), findsOneWidget);
  });

  testWidgets('opens checklist workspace from task actions', (tester) async {
    final api = _FakeTaskApi(
      tasks: [
        {
          'id': 't1',
          'title': '旅行準備',
          'note': null,
          'status': 'pending',
          'priority': 'normal',
          'due_at': null,
          'reminder_at': null,
          'project_id': null,
        },
      ],
      checklist: [
        {'id': 'c1', 'task_id': 't1', 'title': '帶護照', 'is_done': false},
      ],
    );

    await _pumpTasksPage(tester, api);
    await tester.tap(find.byTooltip('待辦選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Checklist'));
    await tester.pumpAndSettle();

    expect(find.text('旅行準備'), findsWidgets);
    expect(find.text('帶護照'), findsOneWidget);
    expect(find.text('新增 Checklist 項目'), findsOneWidget);
  });
}
