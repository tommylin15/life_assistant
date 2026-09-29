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
  final List<String> completedTaskIds = [];
  final List<String> deletedTaskIds = [];
  final List<Map<String, dynamic>> updatedTaskBodies = [];
  final List<Map<String, dynamic>> createdChecklistBodies = [];
  final List<Map<String, dynamic>> updatedChecklistBodies = [];
  final List<String> deletedChecklistIds = [];
  Map<String, dynamic>? createdBody;

  @override
  Future<Map<String, dynamic>> createChecklistItem(
    String taskId,
    Map<String, dynamic> body,
  ) async {
    createdChecklistBodies.add(Map<String, dynamic>.from(body));
    final item = <String, dynamic>{
      'id': 'c-new-${createdChecklistBodies.length}',
      'task_id': taskId,
      'is_done': false,
      ...body,
    };
    checklist.add(item);
    return item;
  }

  @override
  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body) async {
    createdBody = Map<String, dynamic>.from(body);
    final task = <String, dynamic>{
      'id': 'new-task',
      'status': 'pending',
      ...body,
    };
    tasks.add(task);
    return task;
  }

  @override
  Future<void> deleteChecklistItem(String taskId, String itemId) async {
    deletedChecklistIds.add(itemId);
    checklist.removeWhere((item) => item['id'] == itemId);
  }

  @override
  Future<void> deleteTask(String id) async {
    deletedTaskIds.add(id);
    tasks.removeWhere((task) => task['id'] == id);
  }

  @override
  Future<void> completeTask(String id) async {
    completedTaskIds.add(id);
    final task = tasks.firstWhere((item) => item['id'] == id);
    task['status'] = 'completed';
  }

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
  ) async {
    updatedChecklistBodies.add(Map<String, dynamic>.from(body));
    final item = checklist.firstWhere((entry) => entry['id'] == itemId);
    item.addAll(body);
    return item;
  }

  @override
  Future<Map<String, dynamic>> updateTask(
    String id,
    Map<String, dynamic> body,
  ) async {
    updatedTaskBodies.add(Map<String, dynamic>.from(body));
    final task = tasks.firstWhere((item) => item['id'] == id);
    task.addAll(body);
    return task;
  }
}

Map<String, dynamic> _task({
  required String id,
  required String title,
  String status = 'pending',
}) =>
    {
      'id': id,
      'title': title,
      'note': null,
      'status': status,
      'priority': 'normal',
      'due_at': null,
      'reminder_at': null,
      'project_id': null,
    };

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

Finder _checkboxWithSemanticLabel(String label) => find.byWidgetPredicate(
      (widget) => widget is Checkbox && widget.semanticLabel == label,
    );

Finder _textFieldWithLabel(String label) => find.byWidgetPredicate(
      (widget) =>
          widget is TextField && widget.decoration?.labelText == label,
    );

Finder _dropdownAt(int index) =>
    find.byType(DropdownButtonFormField<String>).at(index);

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
        _task(id: 't2', title: '已完成項目', status: 'completed'),
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
    await tester.enterText(_textFieldWithLabel('備註'), '彙整本週進度');

    await tester.tap(_dropdownAt(0));
    await tester.pumpAndSettle();
    await tester.tap(find.text('高').last);
    await tester.pumpAndSettle();

    await tester.tap(_dropdownAt(1));
    await tester.pumpAndSettle();
    await tester.tap(find.text('工作').last);
    await tester.pumpAndSettle();

    await tester.tap(find.text('到期時間：未設定'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('提醒時間：未設定'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('task-save-button')));
    await tester.pumpAndSettle();

    expect(api.createdBody?['title'], '整理週報');
    expect(api.createdBody?['note'], '彙整本週進度');
    expect(api.createdBody?['priority'], 'high');
    expect(api.createdBody?['project_id'], 'p1');
    expect(api.createdBody?['due_at'], isNotNull);
    expect(api.createdBody?['reminder_at'], isNotNull);
    expect(find.text('待辦已新增'), findsOneWidget);
  });

  testWidgets('opens checklist workspace from task actions', (tester) async {
    final api = _FakeTaskApi(
      tasks: [_task(id: 't1', title: '旅行準備')],
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

  testWidgets('creates toggles and deletes checklist items with confirmation',
      (tester) async {
    final api = _FakeTaskApi(tasks: [_task(id: 't1', title: '旅行準備')]);

    await _pumpTasksPage(tester, api);
    await tester.tap(find.byTooltip('待辦選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Checklist'));
    await tester.pumpAndSettle();

    await tester.enterText(
      _textFieldWithLabel('新增 Checklist 項目'),
      '帶護照',
    );
    await tester.tap(find.byTooltip('新增項目'));
    await tester.pumpAndSettle();

    expect(api.createdChecklistBodies.single['title'], '帶護照');
    expect(find.text('帶護照'), findsOneWidget);

    await tester.tap(find.byType(Checkbox).last);
    await tester.pumpAndSettle();
    expect(api.updatedChecklistBodies.single['is_done'], isTrue);
    expect(api.checklist.single['is_done'], isTrue);

    await tester.tap(find.byTooltip('刪除項目'));
    await tester.pumpAndSettle();
    expect(find.text('刪除 Checklist 項目？'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(api.deletedChecklistIds, ['c-new-1']);
    expect(api.checklist, isEmpty);
    expect(find.text('帶護照'), findsNothing);
  });

  testWidgets('completes restores and deletes a task with confirmation',
      (tester) async {
    final api = _FakeTaskApi(tasks: [_task(id: 't1', title: '完成驗收待辦')]);

    await _pumpTasksPage(tester, api);
    await tester.tap(_checkboxWithSemanticLabel('完成待辦'));
    await tester.pumpAndSettle();

    expect(api.completedTaskIds, ['t1']);
    expect(find.text('完成驗收待辦'), findsNothing);

    await tester.tap(find.text('已完成'));
    await tester.pumpAndSettle();
    expect(find.text('完成驗收待辦'), findsOneWidget);

    await tester.tap(_checkboxWithSemanticLabel('恢復待辦'));
    await tester.pumpAndSettle();
    expect(api.updatedTaskBodies.last['status'], 'pending');

    await tester.tap(find.widgetWithText(FilterChip, '進行中'));
    await tester.pumpAndSettle();
    expect(find.text('完成驗收待辦'), findsOneWidget);

    await tester.tap(find.byTooltip('待辦選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除'));
    await tester.pumpAndSettle();
    expect(find.text('刪除待辦？'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(api.deletedTaskIds, ['t1']);
    expect(api.tasks, isEmpty);
    expect(find.text('完成驗收待辦'), findsNothing);
    expect(find.text('待辦已刪除'), findsOneWidget);
  });
}
