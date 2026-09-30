import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/google_drive_picker.dart';
import 'package:life_assistant/web/project_api.dart';
import 'package:life_assistant/web/projects_page.dart';

class _FakeProjectApi implements ProjectApi {
  _FakeProjectApi({
    List<Map<String, dynamic>>? projects,
    List<Map<String, dynamic>>? tasks,
    this.deleteBlockedKind,
  })  : projects = projects ?? [],
        tasks = tasks ?? [];

  final List<Map<String, dynamic>> projects;
  final List<Map<String, dynamic>> tasks;
  ProjectLinkKind? deleteBlockedKind;
  Map<String, dynamic>? createdBody;
  final List<Map<String, dynamic>> updatedBodies = [];
  final List<String> deletedIds = [];

  @override
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body) async {
    createdBody = Map<String, dynamic>.from(body);
    final project = <String, dynamic>{
      'id': 'project-new',
      'created_at': '2026-09-29T10:00:00Z',
      'updated_at': '2026-09-29T10:00:00Z',
      ...body,
    };
    projects.add(project);
    return project;
  }

  @override
  Future<void> deleteProject(String id) async {
    final kind = deleteBlockedKind;
    if (kind != null) {
      throw ProjectDeleteBlockedException(kind);
    }
    deletedIds.add(id);
    projects.removeWhere((project) => project['id'] == id);
  }

  @override
  Future<List<Map<String, dynamic>>> getProjects() async => projects;

  @override
  Future<List<Map<String, dynamic>>> getTasks() async => tasks;

  @override
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  ) async {
    updatedBodies.add(Map<String, dynamic>.from(body));
    final project = projects.firstWhere((item) => item['id'] == id);
    project.addAll(body);
    project['updated_at'] = '2026-09-29T11:00:00Z';
    return project;
  }
}

class _FakeDriveApi implements DriveApi {
  _FakeDriveApi({List<Map<String, dynamic>>? projectDocuments})
      : projectDocuments = projectDocuments ?? [];

  final List<Map<String, dynamic>> projectDocuments;
  final List<(String, String)> detached = [];

  @override
  Future<List<Map<String, dynamic>>> getProjectDocuments({String? projectId}) async =>
      projectDocuments
          .where((item) => projectId == null || item['project_id'] == projectId)
          .toList();

  @override
  Future<void> attachDocumentToProjects(
    String documentId,
    List<String> projectIds,
  ) async {}

  @override
  Future<void> detachDocumentFromProject(String documentId, String projectId) async {
    detached.add((documentId, projectId));
    projectDocuments.removeWhere(
      (item) =>
          item['drive_document_id'] == documentId && item['project_id'] == projectId,
    );
  }

  @override
  Future<PickerConfig> getPickerConfig() => throw UnimplementedError();

  @override
  Future<List<DriveWorkspace>> getWorkspaces() async => const [];

  @override
  Future<DriveWorkspace> createWorkspace(String googleFolderId) =>
      throw UnimplementedError();

  @override
  Future<DriveWorkspace> updateWorkspace(
    String id,
    Map<String, dynamic> body,
  ) =>
      throw UnimplementedError();

  @override
  Future<void> deleteWorkspace(String id) => throw UnimplementedError();

  @override
  Future<DriveAiSettings> getAiSettings() async => const DriveAiSettings();

  @override
  Future<DriveAiSettings> updateAiSettings(Map<String, dynamic> body) =>
      throw UnimplementedError();

  @override
  Future<List<DriveDocument>> getDocuments({String? q, String? workspaceId}) async =>
      const [];

  @override
  Future<List<DriveDocument>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  }) =>
      throw UnimplementedError();

  @override
  Future<DriveDocument> refreshDocument(String id) => throw UnimplementedError();
}

class _FakePicker implements GoogleDrivePicker {
  final List<String> openedUrls = [];

  @override
  Future<List<String>> pickFiles({String? folderId, bool allowMultiple = true}) async =>
      const [];

  @override
  Future<String?> pickFolder() async => null;

  @override
  Future<void> openUrl(String url) async {
    openedUrls.add(url);
  }
}

Map<String, dynamic> _project({
  required String id,
  required String name,
  String? summary,
  String status = 'active',
}) =>
    {
      'id': id,
      'name': name,
      'summary': summary,
      'status': status,
      'created_at': '2026-09-28T08:00:00Z',
      'updated_at': '2026-09-29T08:00:00Z',
    };

Map<String, dynamic> _task({
  required String id,
  required String title,
  required String projectId,
  String status = 'pending',
}) =>
    {
      'id': id,
      'title': title,
      'status': status,
      'project_id': projectId,
      'due_at': null,
    };

Map<String, dynamic> _driveProjectDocument({
  required String projectId,
  required String documentId,
  required String name,
}) =>
    {
      'project_id': projectId,
      'drive_document_id': documentId,
      'google_file_id': 'google-$documentId',
      'name': name,
      'mime_type': 'application/vnd.google-apps.document',
      'web_view_link': 'https://docs.google.com/document/d/google-$documentId/edit',
      'provider_modified_at': '2026-09-30T08:00:00Z',
    };

Future<void> _pumpProjectsPage(
  WidgetTester tester,
  _FakeProjectApi api, {
  _FakeDriveApi? driveApi,
  _FakePicker? picker,
}) async {
  tester.view.physicalSize = const Size(1200, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        projectApiProvider.overrideWithValue(api),
        driveApiProvider.overrideWithValue(driveApi ?? _FakeDriveApi()),
        if (picker != null) googleDrivePickerProvider.overrideWithValue(picker),
      ],
      child: MaterialApp(theme: AppTheme.light, home: const ProjectsPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders project summary, linked tasks, search and status filters',
      (tester) async {
    final api = _FakeProjectApi(
      projects: [
        _project(
          id: 'p1',
          name: '日本旅行',
          summary: '規劃秋季家庭旅行',
        ),
        _project(id: 'p2', name: '舊專案', status: 'archived'),
      ],
      tasks: [
        _task(id: 't1', title: '確認機票', projectId: 'p1'),
        _task(
          id: 't2',
          title: '已完成住宿',
          projectId: 'p1',
          status: 'completed',
        ),
      ],
    );

    await _pumpProjectsPage(tester, api);

    expect(find.text('日本旅行'), findsOneWidget);
    expect(find.text('規劃秋季家庭旅行'), findsOneWidget);
    expect(find.text('確認機票'), findsOneWidget);
    expect(find.text('未完成待辦 1'), findsOneWidget);
    expect(find.text('舊專案'), findsNothing);

    await tester.enterText(
      find.widgetWithText(TextField, '搜尋專案、摘要或待辦'),
      '機票',
    );
    await tester.pumpAndSettle();
    expect(find.text('日本旅行'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilterChip, '已封存'));
    await tester.pumpAndSettle();
    expect(find.text('舊專案'), findsNothing);

    await tester.enterText(
      find.widgetWithText(TextField, '搜尋專案、摘要或待辦'),
      '',
    );
    await tester.pumpAndSettle();
    expect(find.text('舊專案'), findsOneWidget);
  });

  testWidgets('renders related Drive documents and supports open and detach',
      (tester) async {
    final driveApi = _FakeDriveApi(
      projectDocuments: [
        _driveProjectDocument(
          projectId: 'p1',
          documentId: 'd1',
          name: '年度預算',
        ),
      ],
    );
    final picker = _FakePicker();
    await _pumpProjectsPage(
      tester,
      _FakeProjectApi(projects: [_project(id: 'p1', name: '家庭財務')]),
      driveApi: driveApi,
      picker: picker,
    );

    expect(find.text('關聯文件'), findsOneWidget);
    expect(find.text('年度預算'), findsOneWidget);
    expect(find.text('在 Drive 開啟'), findsOneWidget);
    expect(find.text('相關筆記'), findsOneWidget);
    expect(find.text('解除關聯'), findsOneWidget);

    await tester.tap(find.text('在 Drive 開啟'));
    await tester.pump();
    expect(
      picker.openedUrls,
      ['https://docs.google.com/document/d/google-d1/edit'],
    );

    await tester.tap(find.text('解除關聯'));
    await tester.pumpAndSettle();
    expect(driveApi.detached, [('d1', 'p1')]);
  });

  testWidgets('creates and edits a project without inventing status enums',
      (tester) async {
    final api = _FakeProjectApi();
    await _pumpProjectsPage(tester, api);

    await tester.tap(find.text('新增專案').first);
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('project-name-field')),
      '搬家計畫',
    );
    await tester.enterText(
      find.byKey(const ValueKey('project-summary-field')),
      '整理搬家前後事項',
    );
    await tester.enterText(
      find.byKey(const ValueKey('project-status-field')),
      'paused',
    );
    await tester.tap(find.byKey(const ValueKey('project-save-button')));
    await tester.pumpAndSettle();

    expect(api.createdBody?['name'], '搬家計畫');
    expect(api.createdBody?['summary'], '整理搬家前後事項');
    expect(api.createdBody?['status'], 'paused');
    expect(find.text('專案已新增'), findsOneWidget);

    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilterChip, '暫停'));
    await tester.pumpAndSettle();
    expect(find.text('搬家計畫'), findsOneWidget);

    await tester.tap(find.byTooltip('專案選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('編輯'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('project-name-field')),
      '搬家計畫 2',
    );
    await tester.tap(find.byKey(const ValueKey('project-save-button')));
    await tester.pumpAndSettle();

    expect(api.updatedBodies.last['name'], '搬家計畫 2');
    expect(find.text('專案已更新'), findsOneWidget);
    expect(find.text('搬家計畫 2'), findsOneWidget);
  });

  testWidgets('shows delete guard reason for linked entities', (tester) async {
    final api = _FakeProjectApi(
      projects: [_project(id: 'p1', name: '受保護專案')],
      deleteBlockedKind: ProjectLinkKind.tasks,
    );
    await _pumpProjectsPage(tester, api);

    await tester.tap(find.byTooltip('專案選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除'));
    await tester.pumpAndSettle();
    expect(find.text('刪除專案？'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(api.deletedIds, isEmpty);
    expect(find.textContaining('仍有關聯待辦'), findsOneWidget);
    expect(find.text('受保護專案'), findsOneWidget);
  });

  testWidgets('surfaces Drive document delete guard', (tester) async {
    final api = _FakeProjectApi(
      projects: [_project(id: 'p1', name: 'Drive 受保護專案')],
      deleteBlockedKind: ProjectLinkKind.driveDocuments,
    );
    await _pumpProjectsPage(tester, api);

    await tester.tap(find.byTooltip('專案選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(find.textContaining('關聯 Drive 文件'), findsOneWidget);
    expect(find.text('Drive 受保護專案'), findsOneWidget);
  });

  testWidgets('deletes an unlinked project after explicit confirmation',
      (tester) async {
    final api = _FakeProjectApi(
      projects: [_project(id: 'p1', name: '可刪除專案')],
    );
    await _pumpProjectsPage(tester, api);

    await tester.tap(find.byTooltip('專案選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(api.deletedIds, ['p1']);
    expect(find.text('專案已刪除'), findsOneWidget);
    expect(find.text('可刪除專案'), findsNothing);
  });
}
