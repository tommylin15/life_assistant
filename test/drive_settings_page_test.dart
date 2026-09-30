import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/drive_settings_page.dart';
import 'package:life_assistant/web/google_drive_picker.dart';

class _FakeDriveApi implements DriveApi {
  _FakeDriveApi({List<DriveWorkspace>? workspaces})
      : workspaces = workspaces ?? [],
        settings = const DriveAiSettings();

  final List<DriveWorkspace> workspaces;
  DriveAiSettings settings;
  String? createdFolderId;
  final List<Map<String, dynamic>> workspaceUpdates = [];
  final List<String> deletedWorkspaceIds = [];
  final List<Map<String, dynamic>> aiUpdates = [];

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
  Future<DriveWorkspace> createWorkspace(String googleFolderId) async {
    createdFolderId = googleFolderId;
    final workspace = DriveWorkspace(
      id: 'new-workspace',
      googleFolderId: googleFolderId,
      name: '新增工作區',
      webViewLink: null,
      isEnabled: true,
      isDefault: false,
    );
    workspaces.add(workspace);
    return workspace;
  }

  @override
  Future<DriveWorkspace> updateWorkspace(
    String id,
    Map<String, dynamic> body,
  ) async {
    workspaceUpdates.add({'id': id, ...body});
    final index = workspaces.indexWhere((workspace) => workspace.id == id);
    final old = workspaces[index];
    final updated = old.copyWith(
      name: body['name'] as String?,
      isEnabled: body['is_enabled'] as bool?,
      isDefault: body['is_default'] as bool?,
    );
    if (body['is_default'] == true) {
      for (var i = 0; i < workspaces.length; i++) {
        workspaces[i] = workspaces[i].copyWith(isDefault: false);
      }
    }
    workspaces[index] = updated;
    return updated;
  }

  @override
  Future<void> deleteWorkspace(String id) async {
    deletedWorkspaceIds.add(id);
    workspaces.removeWhere((workspace) => workspace.id == id);
  }

  @override
  Future<DriveAiSettings> getAiSettings() async => settings;

  @override
  Future<DriveAiSettings> updateAiSettings(Map<String, dynamic> body) async {
    aiUpdates.add(Map<String, dynamic>.from(body));
    settings = settings.copyWith(
      autoTags: body['auto_tags'] as bool?,
      suggestRelatedNotes: body['suggest_related_notes'] as bool?,
      allowContentAnalysis: body['allow_content_analysis'] as bool?,
      maxRelatedNotes: body['max_related_notes'] as int?,
    );
    return settings;
  }

  @override
  Future<List<DriveDocument>> getDocuments({String? q, String? workspaceId}) async => [];

  @override
  Future<List<DriveDocument>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  }) async => [];

  @override
  Future<DriveDocument> refreshDocument(String id) => throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getProjectDocuments({String? projectId}) async =>
      const [];

  @override
  Future<void> attachDocumentToProjects(
    String documentId,
    List<String> projectIds,
  ) async {}

  @override
  Future<void> detachDocumentFromProject(
    String documentId,
    String projectId,
  ) async {}
}

class _FakePicker implements GoogleDrivePicker {
  _FakePicker(this.folderId);
  final String? folderId;

  @override
  Future<List<String>> pickFiles({String? folderId, bool allowMultiple = true}) async => [];

  @override
  Future<String?> pickFolder() async => folderId;

  @override
  Future<void> openUrl(String url) async {}
}

DriveWorkspace _workspace(
  String id,
  String name, {
  bool enabled = true,
  bool isDefault = false,
}) =>
    DriveWorkspace(
      id: id,
      googleFolderId: 'folder-$id',
      name: name,
      webViewLink: null,
      isEnabled: enabled,
      isDefault: isDefault,
    );

Future<void> _pump(
  WidgetTester tester,
  _FakeDriveApi api,
  _FakePicker picker,
) async {
  tester.view.physicalSize = const Size(900, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        driveApiProvider.overrideWithValue(api),
        googleDrivePickerProvider.overrideWithValue(picker),
      ],
      child: MaterialApp(
        theme: AppTheme.light,
        home: const DriveSettingsPage(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('manages multiple workspaces and explains non-recursive access',
      (tester) async {
    final api = _FakeDriveApi(
      workspaces: [
        _workspace('w1', '工作文件', isDefault: true),
        _workspace('w2', '投資研究'),
      ],
    );
    await _pump(tester, api, _FakePicker('folder-new'));

    expect(find.text('工作文件'), findsOneWidget);
    expect(find.text('投資研究'), findsOneWidget);
    expect(find.textContaining('不會自動取得資料夾內所有檔案'), findsOneWidget);

    await tester.tap(find.text('新增工作區'));
    await tester.pumpAndSettle();
    expect(api.createdFolderId, 'folder-new');

    await tester.tap(find.byKey(const ValueKey('drive-workspace-default-w2')));
    await tester.pumpAndSettle();
    expect(
      api.workspaceUpdates.any(
        (item) => item['id'] == 'w2' && item['is_default'] == true,
      ),
      isTrue,
    );

    await tester.tap(find.byKey(const ValueKey('drive-workspace-enabled-w1')));
    await tester.pumpAndSettle();
    expect(
      api.workspaceUpdates.any(
        (item) => item['id'] == 'w1' && item['is_enabled'] == false,
      ),
      isTrue,
    );
  });

  testWidgets('renders persisted intelligent-organization defaults and toggles',
      (tester) async {
    final api = _FakeDriveApi();
    await _pump(tester, api, _FakePicker(null));

    final autoTags = tester.widget<SwitchListTile>(
      find.widgetWithText(SwitchListTile, '自動智能 Tag'),
    );
    final suggest = tester.widget<SwitchListTile>(
      find.widgetWithText(SwitchListTile, '建議相關 Notes'),
    );
    final allow = tester.widget<SwitchListTile>(
      find.widgetWithText(SwitchListTile, '允許將文件內容送交 AI 分析'),
    );
    expect(autoTags.value, isTrue);
    expect(suggest.value, isTrue);
    expect(allow.value, isFalse);
    expect(find.textContaining('最多 5 筆'), findsOneWidget);

    await tester.tap(find.text('允許將文件內容送交 AI 分析'));
    await tester.pumpAndSettle();
    expect(api.aiUpdates.last['allow_content_analysis'], true);
  });
}
