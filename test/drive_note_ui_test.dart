import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/browser_navigation.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/drive_page.dart';
import 'package:life_assistant/web/note_api.dart';
import 'package:life_assistant/web/notes_page.dart';

class _FakeDriveApi implements DriveApi {
  _FakeDriveApi(this.documents);

  final List<Map<String, dynamic>> documents;

  @override
  Future<Map<String, dynamic>> decideNoteSuggestion(
    String suggestionId,
    String decision,
  ) => throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getDocuments() async => documents;

  @override
  Future<Map<String, dynamic>?> getEnrichment(String documentId) async => null;

  @override
  Future<Map<String, dynamic>> getEnrichmentSettings() async => {
        'auto_tags_enabled': true,
        'note_suggestions_enabled': true,
        'allow_document_content': true,
        'max_related_note_suggestions': 5,
      };

  @override
  Future<Map<String, dynamic>> runEnrichment(
    String documentId, {
    bool force = false,
  }) => throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> updateEnrichmentSettings(
    Map<String, dynamic> body,
  ) => throw UnimplementedError();
}

class _FakeNoteApi implements NoteApi {
  _FakeNoteApi({required this.notes, required this.projects});

  final List<Map<String, dynamic>> notes;
  final List<Map<String, dynamic>> projects;

  @override
  Future<List<Map<String, dynamic>>> getNotes({String query = ''}) async => notes;

  @override
  Future<List<Map<String, dynamic>>> getProjects() async => projects;

  @override
  Future<Map<String, dynamic>> createNote(Map<String, dynamic> body) =>
      throw UnimplementedError();
  @override
  Future<void> deleteNote(String id) => throw UnimplementedError();
  @override
  Future<List<Map<String, dynamic>>> getNoteLinks(String id) async => const [];
  @override
  Future<List<String>> getNoteTags(String id) async => const [];
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
  ) => throw UnimplementedError();
}

class _FakeDriveNoteApi implements DriveNoteApi {
  final List<Map<String, dynamic>> imports = [];
  final List<Map<String, String>> links = [];
  final Map<String, List<Map<String, dynamic>>> documentNotes = {};
  final Map<String, List<Map<String, dynamic>>> noteDocuments = {};

  @override
  Future<Map<String, dynamic>> importDocumentToNote(
    String documentId,
    Map<String, dynamic> body,
  ) async {
    imports.add({'document_id': documentId, ...body});
    return {
      'id': 'imported-note-1',
      'title': body['title'] ?? 'Provider filename',
      'body': 'snapshot',
      'project_id': body['project_id'],
      'created_at': '2026-10-04T00:00:00Z',
      'updated_at': '2026-10-04T00:00:00Z',
    };
  }

  @override
  Future<List<Map<String, dynamic>>> getDocumentNotes(String documentId) async =>
      documentNotes[documentId] ?? const [];

  @override
  Future<List<Map<String, dynamic>>> getNoteDocuments(String noteId) async =>
      noteDocuments[noteId] ?? const [];

  @override
  Future<Map<String, dynamic>> linkDocumentNote(
    String documentId,
    String noteId,
  ) async {
    links.add({'document_id': documentId, 'note_id': noteId});
    return {
      'note': {'id': noteId, 'title': '既有筆記', 'body': ''},
      'relation_type': 'related',
      'link_source': 'manual',
    };
  }

  @override
  Future<void> unlinkDocumentNote(String documentId, String noteId) async {}
}

class _FakeBrowserNavigation implements BrowserNavigation {
  final List<String> opened = [];

  @override
  Future<void> openExternal(String url) async {
    opened.add(url);
  }
}

Map<String, dynamic> _document(String id, String name, String link) => {
      'id': id,
      'google_file_id': 'google-$id',
      'name': name,
      'mime_type': 'application/vnd.google-apps.document',
      'web_view_link': link,
      'modified_at': null,
      'created_at': '2026-10-04T00:00:00Z',
      'updated_at': '2026-10-04T00:00:00Z',
    };

Map<String, dynamic> _note(String id, String title) => {
      'id': id,
      'title': title,
      'body': 'body',
      'project_id': null,
      'created_at': '2026-10-04T00:00:00Z',
      'updated_at': '2026-10-04T00:00:00Z',
    };

void main() {
  testWidgets('Drive document can be converted to Note with title project and tags',
      (tester) async {
    final driveApi = _FakeDriveApi([
      _document('d1', 'Provider filename', 'https://drive.google.com/d1'),
    ]);
    final noteApi = _FakeNoteApi(
      notes: [_note('n1', '既有筆記')],
      projects: [
        {'id': 'p1', 'name': '旅行專案'},
      ],
    );
    final driveNoteApi = _FakeDriveNoteApi();

    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          driveApiProvider.overrideWithValue(driveApi),
          noteApiProvider.overrideWithValue(noteApi),
          driveNoteApiProvider.overrideWithValue(driveNoteApi),
        ],
        child: MaterialApp(theme: AppTheme.light, home: const DrivePage()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('drive-note-import-d1')), findsOneWidget);
    expect(find.byKey(const ValueKey('drive-note-link-d1')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('drive-note-import-d1')));
    await tester.pumpAndSettle();
    expect(find.text('轉成筆記'), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey('drive-note-title-field')),
      '旅行快照',
    );
    await tester.enterText(
      find.byKey(const ValueKey('drive-note-tags-field')),
      '旅行, 重要, 旅行',
    );
    await tester.tap(find.byKey(const ValueKey('drive-note-project-field')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('旅行專案').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('drive-note-import-save')));
    await tester.pumpAndSettle();

    expect(driveNoteApi.imports, [
      {
        'document_id': 'd1',
        'title': '旅行快照',
        'project_id': 'p1',
        'tags': ['旅行', '重要'],
      },
    ]);
    expect(find.textContaining('已轉成筆記'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('drive-note-link-d1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('drive-note-link-target')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('既有筆記').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('drive-note-link-save')));
    await tester.pumpAndSettle();

    expect(driveNoteApi.links, [
      {'document_id': 'd1', 'note_id': 'n1'},
    ]);
  });

  testWidgets('Notes distinguish source Drive and related Drive and open source',
      (tester) async {
    final noteApi = _FakeNoteApi(
      notes: [_note('n1', 'Drive 匯入筆記')],
      projects: const [],
    );
    final driveNoteApi = _FakeDriveNoteApi()
      ..noteDocuments['n1'] = [
        {
          'document': _document(
            'source',
            '原始文件',
            'https://drive.google.com/source',
          ),
          'relation_type': 'source_import',
          'link_source': 'import',
        },
        {
          'document': _document(
            'related',
            '參考文件',
            'https://drive.google.com/related',
          ),
          'relation_type': 'related',
          'link_source': 'manual',
        },
      ];
    final browser = _FakeBrowserNavigation();

    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          noteApiProvider.overrideWithValue(noteApi),
          driveNoteApiProvider.overrideWithValue(driveNoteApi),
          browserNavigationProvider.overrideWithValue(browser),
        ],
        child: MaterialApp(theme: AppTheme.light, home: const NotesPage()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('來源：Google Drive · 原始文件'), findsOneWidget);
    expect(find.textContaining('相關 Drive：參考文件'), findsOneWidget);
    expect(find.byTooltip('開啟原始文件'), findsOneWidget);

    await tester.tap(find.byTooltip('開啟原始文件'));
    await tester.pumpAndSettle();
    expect(browser.opened, ['https://drive.google.com/source']);
  });
}
