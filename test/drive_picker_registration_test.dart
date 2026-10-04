import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/drive_page.dart';
import 'package:life_assistant/web/google_drive_picker.dart';
import 'package:life_assistant/web/note_api.dart';

class _FakeDriveApi implements DriveApi {
  final List<Map<String, dynamic>> documents = [];
  final List<List<String>> registrations = [];

  @override
  Future<List<Map<String, dynamic>>> getDocuments() async => documents;

  @override
  Future<Map<String, dynamic>> getPickerConfig() async => {
        'client_id': 'web-client.apps.googleusercontent.com',
        'developer_key': 'restricted-browser-key',
        'app_id': '123456789',
        'scope': 'https://www.googleapis.com/auth/drive.file',
      };

  @override
  Future<List<Map<String, dynamic>>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  }) async {
    registrations.add(List<String>.from(googleFileIds));
    documents.add({
      'id': 'document-1',
      'google_file_id': googleFileIds.single,
      'name': 'Picker selected document',
      'mime_type': 'application/vnd.google-apps.document',
      'web_view_link': 'https://drive.google.com/document-1',
      'modified_at': null,
      'created_at': '2026-10-04T00:00:00Z',
      'updated_at': '2026-10-04T00:00:00Z',
    });
    return documents;
  }

  @override
  Future<Map<String, dynamic>> getEnrichmentSettings() async => {
        'auto_tags_enabled': true,
        'note_suggestions_enabled': true,
        'allow_document_content': false,
        'max_related_note_suggestions': 5,
      };

  @override
  Future<Map<String, dynamic>?> getEnrichment(String documentId) async => null;

  @override
  Future<Map<String, dynamic>> updateEnrichmentSettings(
    Map<String, dynamic> body,
  ) =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> runEnrichment(
    String documentId, {
    bool force = false,
  }) =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> decideNoteSuggestion(
    String suggestionId,
    String decision,
  ) =>
      throw UnimplementedError();
}

class _FakePicker implements GoogleDrivePicker {
  _FakePicker(this.result);

  final List<String> result;
  PickerConfig? lastConfig;
  bool? lastFolders;
  bool? lastMultiSelect;

  @override
  Future<List<String>> pick(
    PickerConfig config, {
    required bool folders,
    bool multiSelect = true,
  }) async {
    lastConfig = config;
    lastFolders = folders;
    lastMultiSelect = multiSelect;
    return result;
  }
}

class _FakeNoteApi implements NoteApi {
  @override
  Future<List<Map<String, dynamic>>> getNotes({String query = ''}) async => const [];

  @override
  Future<Map<String, dynamic>> createNote(Map<String, dynamic> body) =>
      throw UnimplementedError();
  @override
  Future<void> deleteNote(String id) => throw UnimplementedError();
  @override
  Future<List<Map<String, dynamic>>> getNoteLinks(String id) =>
      throw UnimplementedError();
  @override
  Future<List<String>> getNoteTags(String id) => throw UnimplementedError();
  @override
  Future<List<Map<String, dynamic>>> getProjects() => throw UnimplementedError();
  @override
  Future<void> linkNote(String id, String targetId) => throw UnimplementedError();
  @override
  Future<List<String>> replaceNoteTags(String id, List<String> tags) =>
      throw UnimplementedError();
  @override
  Future<void> unlinkNote(String id, String targetId) => throw UnimplementedError();
  @override
  Future<Map<String, dynamic>> updateNote(
    String id,
    Map<String, dynamic> body,
  ) =>
      throw UnimplementedError();
}

Future<void> _pump(
  WidgetTester tester,
  _FakeDriveApi api,
  _FakePicker picker,
) async {
  tester.view.physicalSize = const Size(1000, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        driveApiProvider.overrideWithValue(api),
        googleDrivePickerProvider.overrideWithValue(picker),
        noteApiProvider.overrideWithValue(_FakeNoteApi()),
      ],
      child: MaterialApp(
        theme: AppTheme.light,
        home: const DrivePage(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('registers only explicitly selected Picker files and reloads documents',
      (tester) async {
    final api = _FakeDriveApi();
    final picker = _FakePicker(['google-file-1']);
    await _pump(tester, api, picker);

    await tester.tap(find.byKey(const ValueKey('add-drive-files')));
    await tester.pumpAndSettle();

    expect(api.registrations, [
      ['google-file-1'],
    ]);
    expect(picker.lastFolders, isFalse);
    expect(picker.lastMultiSelect, isTrue);
    expect(
      picker.lastConfig?.scope,
      'https://www.googleapis.com/auth/drive.file',
    );
    expect(find.text('Picker selected document'), findsOneWidget);
  });

  testWidgets('Picker cancellation performs no registration mutation', (tester) async {
    final api = _FakeDriveApi();
    final picker = _FakePicker(const []);
    await _pump(tester, api, picker);

    await tester.tap(find.byKey(const ValueKey('add-drive-files')));
    await tester.pumpAndSettle();

    expect(api.registrations, isEmpty);
  });
}
