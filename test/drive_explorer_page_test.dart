import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/drive_explorer_page.dart';
import 'package:life_assistant/web/platform_api.dart';

class _FakeDriveExplorerApi extends PlatformApi {
  final calls = <String>[];
  final writes = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> get(String path) async {
    calls.add(path);
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
  Future<Map<String, dynamic>> post(
      String path, Map<String, dynamic> body) async {
    writes.add({'path': path, ...body});
    return {'id': 'new-folder', 'name': body['name'], 'visibility': 'app_authorized_only'};
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
    expect(find.textContaining('已獲授權'), findsOneWidget);
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
}
