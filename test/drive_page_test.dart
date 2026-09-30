import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/drive_page.dart';
import 'package:life_assistant/web/google_drive_picker.dart';
import 'package:life_assistant/web/project_api.dart';

class _FakeDriveApi implements DriveApi {
  _FakeDriveApi({List<DriveDocument>? documents, List<DriveWorkspace>? workspaces})
      : documents = documents ?? [],
        workspaces = workspaces ?? [];

  final List<DriveDocument> documents;
  final List<DriveWorkspace> workspaces;
  List<String>? registeredIds;
  String? registeredWorkspaceId;
  String? lastQuery;
  String? lastWorkspaceFilter;
  String? attachedDocumentId;
  List<String>? attachedProjectIds;

  @override
  Future<PickerConfig> getPickerConfig() async => const PickerConfig(
        clientId: 'client',
        developerKey: 'key',
        appId: 'app',
        scope: 'https://www.googleapis.com/auth/drive.file',
      );

  @override
  Future<List<DriveWorkspace>> getWorkspaces() async => workspaces;

  @override
  Future<DriveWorkspace> createWorkspace(String googleFolderId) {
    throw UnimplementedError();
  }

  @override
  Future<DriveWorkspace> updateWorkspace(
    String id,
    Map<String, dynamic> body,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<void> deleteWorkspace(String id) {
    throw UnimplementedError();
  }

  @override
  Future<DriveAiSettings> getAiSettings() async => const DriveAiSettings();

  @override
  Future<DriveAiSettings> updateAiSettings(Map<String, dynamic> body) {
    throw UnimplementedError();
  }

  @override
  Future<List<DriveDocument>> getDocuments({String? q, String? workspaceId}) async {
    lastQuery = q;
    lastWorkspaceFilter = workspaceId;
    final query = (q ?? '').trim().toLowerCase();
    return documents
        .where((document) =>
            query.isEmpty || document.name.toLowerCase().contains(query))
        .toList();
  }

  @override
  Future<List<DriveDocument>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  }) async {
    registeredIds = List.of(googleFileIds);
    registeredWorkspaceId = workspaceId;
    return documents;
  }

  @override
  Future<DriveDocument> refreshDocument(String id) {
    throw UnimplementedError();
  }

  @override
  Future<List<Map<String, dynamic>>> getProjectDocuments({String? projectId}) async =>
      const [];

  @override
  Future<void> attachDocumentToProjects(
    String documentId,
    List<String> projectIds,
  ) async {
    attachedDocumentId = documentId;
    attachedProjectIds = List.of(projectIds);
  }

  @override
  Future<void> detachDocumentFromProject(
    String documentId,
    String projectId,
  ) async {}
}

class _FakeProjectApi implements ProjectApi {
  _FakeProjectApi({List<Map<String, dynamic>>? projects})
      : projects = projects ?? [];

  final List<Map<String, dynamic>> projects;

  @override
  Future<List<Map<String, dynamic>>> getProjects() async => projects;

  @override
  Future<List<Map<String, dynamic>>> getTasks() async => const [];

  @override
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body) {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<void> deleteProject(String id) {
    throw UnimplementedError();
  }
}

class _FakePicker implements GoogleDrivePicker {
  _FakePicker({this.fileIds = const []});

  final List<String> fileIds;
  String? passedFolderId;
  bool? passedAllowMultiple;
  final List<String> openedUrls = [];

  @override
  Future<List<String>> pickFiles({String? folderId, bool allowMultiple = true}) async {
    passedFolderId = folderId;
    passedAllowMultiple = allowMultiple;
    return fileIds;
  }

  @override
  Future<String?> pickFolder() async => null;

  @override
  Future<void> openUrl(String url) async {
    openedUrls.add(url);
  }
}

DriveDocument _document(String id, String name) => DriveDocument(
      id: id,
      googleFileId: 'g-$id',
      name: name,
      mimeType: 'application/vnd.google-apps.document',
      webViewLink: 'https://docs.google.com/document/d/g-$id/edit',
      providerModifiedAt: DateTime.utc(2026, 9, 30, 10),
    );

DriveWorkspace _workspace() => const DriveWorkspace(
      id: 'w1',
      googleFolderId: 'folder-1',
      name: '工作文件',
      webViewLink: 'https://drive.google.com/drive/folders/folder-1',
      isEnabled: true,
      isDefault: true,
    );

Map<String, dynamic> _project(String id, String name) => {
      'id': id,
      'name': name,
      'summary': null,
      'status': 'active',
      'created_at': '2026-09-30T08:00:00Z',
      'updated_at': '2026-09-30T08:00:00Z',
    };

Future<void> _pump(
  WidgetTester tester,
  DriveApi api,
  GoogleDrivePicker picker, {
  ProjectApi? projectApi,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        driveApiProvider.overrideWithValue(api),
        googleDrivePickerProvider.overrideWithValue(picker),
        if (projectApi != null) projectApiProvider.overrideWithValue(projectApi),
      ],
      child: MaterialApp(theme: AppTheme.light, home: const DrivePage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('lists registered files and only later Note import stays disabled',
      (tester) async {
    final api = _FakeDriveApi(
      documents: [_document('d1', '年度預算'), _document('d2', '會議紀錄')],
      workspaces: [_workspace()],
    );
    final picker = _FakePicker();
    await _pump(
      tester,
      api,
      picker,
      projectApi: _FakeProjectApi(projects: [_project('p1', '家庭財務')]),
    );

    expect(find.text('年度預算'), findsOneWidget);
    expect(find.text('會議紀錄'), findsOneWidget);
    expect(find.text('開啟'), findsWidgets);
    expect(find.text('加入專案'), findsWidgets);
    expect(find.text('轉入 Notes'), findsWidgets);

    final addProject = tester.widget<TextButton>(
      find.widgetWithText(TextButton, '加入專案').first,
    );
    final importNote = tester.widget<TextButton>(
      find.widgetWithText(TextButton, '轉入 Notes').first,
    );
    expect(addProject.onPressed, isNotNull);
    expect(importNote.onPressed, isNull);
  });

  testWidgets('add to project dialog supports multiple project selection',
      (tester) async {
    final api = _FakeDriveApi(documents: [_document('d1', '年度預算')]);
    await _pump(
      tester,
      api,
      _FakePicker(),
      projectApi: _FakeProjectApi(
        projects: [_project('p1', '家庭財務'), _project('p2', '裝修')],
      ),
    );

    await tester.tap(find.widgetWithText(TextButton, '加入專案'));
    await tester.pumpAndSettle();

    expect(find.text('加入專案'), findsWidgets);
    expect(find.text('家庭財務'), findsOneWidget);
    expect(find.text('裝修'), findsOneWidget);
    expect(find.byType(Checkbox), findsNWidgets(2));

    await tester.tap(find.text('家庭財務'));
    await tester.tap(find.text('裝修'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '加入'));
    await tester.pumpAndSettle();

    expect(api.attachedDocumentId, 'd1');
    expect(api.attachedProjectIds, ['p1', 'p2']);
  });

  testWidgets('adds picker-selected files into active workspace and opens source',
      (tester) async {
    final api = _FakeDriveApi(
      documents: [_document('d1', '年度預算')],
      workspaces: [_workspace()],
    );
    final picker = _FakePicker(fileIds: const ['google-1', 'google-2']);
    await _pump(tester, api, picker);

    await tester.tap(find.text('新增 Drive 文件'));
    await tester.pumpAndSettle();

    expect(picker.passedFolderId, 'folder-1');
    expect(api.registeredIds, ['google-1', 'google-2']);
    expect(api.registeredWorkspaceId, 'w1');

    await tester.tap(find.widgetWithText(TextButton, '開啟').first);
    await tester.pump();
    expect(
      picker.openedUrls,
      ['https://docs.google.com/document/d/g-d1/edit'],
    );
  });

  testWidgets('search is limited to registered metadata and empty state explains scope',
      (tester) async {
    final api = _FakeDriveApi(
      documents: [_document('d1', '年度預算'), _document('d2', '會議紀錄')],
    );
    await _pump(tester, api, _FakePicker());

    await tester.enterText(find.byKey(const ValueKey('drive-search-field')), '預算');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();
    expect(api.lastQuery, '預算');
    expect(find.text('年度預算'), findsOneWidget);
    expect(find.text('會議紀錄'), findsNothing);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();

    final emptyApi = _FakeDriveApi();
    await _pump(tester, emptyApi, _FakePicker());
    expect(find.textContaining('只會顯示你透過 Google Picker'), findsOneWidget);
  });
}
