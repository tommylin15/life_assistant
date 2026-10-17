import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/drive_explorer_page.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/google_drive_picker.dart';
import 'package:life_assistant/web/platform_api.dart';

class _FakeDriveExplorerApi extends PlatformApi {
  final calls = <String>[];
  final writes = <Map<String, dynamic>>[];
  final textSaves = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> get(String path) async {
    calls.add(path);
    if (path.endsWith('/text-preview')) {
      return {
        'id': 'file-one', 'name': 'Planning.txt',
        'text': 'Original note', 'version': '12',
        'content_sha256': '4b8cf23995d2c9ee4a1f548aadb2a1f1d75adc5f0a3f3ebc42c676a1d68a721e',
        'mime_type': 'text/plain', 'can_edit': true,
      };
    }
    final query = Uri.parse(path).queryParameters;
    if (query['folder_id'] == 'folder-a') {
      return {
        'visibility': 'app_authorized_only',
        'files': [
          {'id': 'child-one', 'name': 'inside.md', 'is_folder': false,
           'mime_type': 'text/markdown', 'can_edit': true,
           'web_view_link': 'https://drive.google.com/file/d/child-one/view'},
        ],
        'next_page_token': null,
      };
    }
    return {
      'visibility': 'app_authorized_only',
      'files': [
        {'id': 'folder-a', 'name': 'Folder A', 'is_folder': true,
         'mime_type': 'application/vnd.google-apps.folder', 'can_edit': true},
        {'id': 'file-one', 'name': 'Planning.txt', 'is_folder': false,
         'mime_type': 'text/plain', 'can_edit': true},
      ],
      'next_page_token': null,
    };
  }

  @override
  Future<Map<String, dynamic>> put(
      String path, Map<String, dynamic> body) async {
    textSaves.add({'path': path, ...body});
    return {'verified': true, 'unchanged': false, 'version': '13'};
  }

  @override
  Future<Map<String, dynamic>> post(
      String path, Map<String, dynamic> body) async {
    writes.add({'path': path, ...body});
    return {'id': 'new-folder', 'name': body['name'], 'visibility': 'app_authorized_only'};
  }
}

class _FakePickerDriveApi implements DrivePickerApi {
  List<String> registered = [];
  @override
  Future<Map<String, dynamic>> getPickerConfig() async => {
    'client_id': 'fake-client', 'developer_key': 'fake-key',
    'app_id': 'fake-app', 'scope': driveFileScope,
  };
  @override
  Future<List<Map<String, dynamic>>> registerDocuments(
      List<String> googleFileIds, {String? workspaceId}) async {
    registered = googleFileIds;
    return [
      for (final id in googleFileIds)
        {'id': 'doc-' + id, 'google_file_id': id},
    ];
  }
}

class _FakeGooglePicker implements GoogleDrivePicker {
  final List<bool> folderChoices = [];
  @override
  Future<List<String>> pick(PickerConfig config, {
    required bool folders, bool multiSelect = true,
  }) async {
    folderChoices.add(folders);
    return [folders ? 'folder-selected' : 'file-selected'];
  }
}

void main() {
  testWidgets('Drive explorer shows app-grant scope and folder navigation',
      (tester) async {
    final api = _FakeDriveExplorerApi();
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: DriveExplorerPage()),
    ));
    await tester.pumpAndSettle();
    expect(find.textContaining('逐檔授權'), findsOneWidget);
    expect(find.text('Folder A'), findsOneWidget);
    await tester.tap(find.text('Folder A'));
    await tester.pumpAndSettle();
    expect(find.text('inside.md'), findsOneWidget);
    expect(api.calls.last, contains('folder_id=folder-a'));
  });

  testWidgets('new folder operation inherits current Drive folder',
      (tester) async {
    final api = _FakeDriveExplorerApi();
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: DriveExplorerPage()),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Folder A'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('drive-explorer-new-folder')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'New Folder');
    await tester.tap(find.text('建立'));
    await tester.pumpAndSettle();
    expect(api.writes, hasLength(1));
    expect(api.writes.first['path'], '/drive/manager/folders');
    expect(api.writes.first['name'], 'New Folder');
    expect(api.writes.first['parent_id'], 'folder-a');
  });
  testWidgets('Drive small text can be edited and saved through owner-bound API',
      (tester) async {
    final api = _FakeDriveExplorerApi();
    tester.view.physicalSize = const Size(1000, 1500);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(ProviderScope(
      overrides: [
        platformApiProvider.overrideWithValue(api),
        drivePickerApiProvider.overrideWithValue(_FakePickerDriveApi()),
      ],
      child: const MaterialApp(home: DriveExplorerPage()),
    ));
    await tester.pumpAndSettle();
    final item = find.byKey(const ValueKey('drive-file-file-one'));
    expect(item, findsOneWidget);
    await tester.tap(find.descendant(
        of: item, matching: find.byType(PopupMenuButton<String>)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('在 Life 內編輯文字'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('drive-explorer-text-editor')), findsOneWidget);
    await tester.enterText(
        find.byKey(const ValueKey('drive-explorer-text-editor')), 'Edited note');
    await tester.tap(find.byKey(const ValueKey('drive-explorer-text-save')));
    await tester.pumpAndSettle();
    expect(api.textSaves, hasLength(1));
    expect(api.textSaves.first['path'],
        '/drive/manager/documents/doc-file-one/text');
    expect(api.textSaves.first['text'], 'Edited note');
    expect(api.textSaves.first['expected_version'], '12');
    expect(api.textSaves.first['expected_sha256'], isNotEmpty);
  });

  testWidgets('Drive file manager grants additional files through Google Picker',
      (tester) async {
    final api = _FakeDriveExplorerApi();
    final pickerApi = _FakePickerDriveApi();
    final picker = _FakeGooglePicker();
    await tester.pumpWidget(ProviderScope(
      overrides: [
        platformApiProvider.overrideWithValue(api),
        drivePickerApiProvider.overrideWithValue(pickerApi),
        googleDrivePickerProvider.overrideWithValue(picker),
      ],
      child: const MaterialApp(home: DriveExplorerPage()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Google Drive 檔案總管'), findsOneWidget);
    expect(find.text('選取更多檔案'), findsOneWidget);
    expect(find.text('在 Google Drive 查看全部檔案'), findsOneWidget);
    expect(find.text('Drive 智能整理'), findsNothing);
    await tester.tap(find.byKey(
        const ValueKey('drive-explorer-select-files')));
    await tester.pumpAndSettle();
    expect(picker.folderChoices, [false]);
    expect(pickerApi.registered, ['file-selected']);

    await tester.tap(find.byKey(
        const ValueKey('drive-explorer-select-folder')));
    await tester.pumpAndSettle();
    expect(picker.folderChoices, [false, true]);
    expect(pickerApi.registered, ['folder-selected']);
  });

}
