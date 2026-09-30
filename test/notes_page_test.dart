import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/note_api.dart';
import 'package:life_assistant/web/notes_page.dart';

class _FakeNoteApi implements NoteApi {
  _FakeNoteApi({
    List<Map<String, dynamic>>? notes,
    List<Map<String, dynamic>>? projects,
    this.failTagReplace = false,
  })  : notes = notes ?? [],
        projects = projects ?? [];

  final List<Map<String, dynamic>> notes;
  final List<Map<String, dynamic>> projects;
  final bool failTagReplace;
  final Map<String, List<String>> tags = {};
  final Map<String, List<String>> links = {};
  final List<String> deletedIds = [];
  final List<String> searchQueries = [];
  int _nextId = 1;

  @override
  Future<Map<String, dynamic>> createNote(Map<String, dynamic> body) async {
    final note = <String, dynamic>{
      'id': 'note-new-${_nextId++}',
      'created_at': '2026-09-30T01:00:00Z',
      'updated_at': '2026-09-30T01:00:00Z',
      ...body,
    };
    notes.insert(0, note);
    return note;
  }

  @override
  Future<void> deleteNote(String id) async {
    deletedIds.add(id);
    notes.removeWhere((note) => note['id'] == id);
    tags.remove(id);
    links.remove(id);
    for (final values in links.values) {
      values.remove(id);
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getNoteLinks(String id) async {
    final ids = links[id] ?? const [];
    return notes.where((note) => ids.contains(note['id'])).toList();
  }

  @override
  Future<List<Map<String, dynamic>>> getNotes({String query = ''}) async {
    searchQueries.add(query);
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) return List<Map<String, dynamic>>.from(notes);
    return notes.where((note) {
      final title = (note['title'] ?? '').toString().toLowerCase();
      final body = (note['body'] ?? '').toString().toLowerCase();
      return title.contains(normalized) || body.contains(normalized);
    }).toList();
  }

  @override
  Future<List<String>> getNoteTags(String id) async =>
      List<String>.from(tags[id] ?? const []);

  @override
  Future<List<Map<String, dynamic>>> getProjects() async => projects;

  @override
  Future<void> linkNote(String id, String targetId) async {
    links.putIfAbsent(id, () => []).add(targetId);
    links.putIfAbsent(targetId, () => []).add(id);
  }

  @override
  Future<List<String>> replaceNoteTags(String id, List<String> values) async {
    if (failTagReplace) throw Exception('tag write failed');
    tags[id] = List<String>.from(values);
    return tags[id]!;
  }

  @override
  Future<void> unlinkNote(String id, String targetId) async {
    links[id]?.remove(targetId);
    links[targetId]?.remove(id);
  }

  @override
  Future<Map<String, dynamic>> updateNote(
    String id,
    Map<String, dynamic> body,
  ) async {
    final note = notes.firstWhere((item) => item['id'] == id);
    note.addAll(body);
    note['updated_at'] = '2026-09-30T02:00:00Z';
    return note;
  }
}

Map<String, dynamic> _note({
  required String id,
  required String title,
  required String body,
  String? projectId,
}) =>
    {
      'id': id,
      'title': title,
      'body': body,
      'project_id': projectId,
      'created_at': '2026-09-29T01:00:00Z',
      'updated_at': '2026-09-30T01:00:00Z',
    };

Future<void> _pumpNotesPage(
  WidgetTester tester,
  _FakeNoteApi api, {
  Size size = const Size(1200, 900),
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [noteApiProvider.overrideWithValue(api)],
      child: MaterialApp(theme: AppTheme.light, home: const NotesPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders notes and sends search query through NoteApi', (tester) async {
    final api = _FakeNoteApi(
      notes: [
        _note(id: 'n1', title: '日本旅行', body: '機票與住宿'),
        _note(id: 'n2', title: '工作紀錄', body: 'release checklist'),
      ],
    );
    await _pumpNotesPage(tester, api);

    expect(find.text('日本旅行'), findsOneWidget);
    expect(find.text('工作紀錄'), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey('notes-search-field')),
      '住宿',
    );
    await tester.tap(find.byKey(const ValueKey('notes-search-button')));
    await tester.pumpAndSettle();

    expect(api.searchQueries.last, '住宿');
    expect(find.text('日本旅行'), findsOneWidget);
    expect(find.text('工作紀錄'), findsNothing);
    expect(find.textContaining('1 筆'), findsOneWidget);
  });

  testWidgets('creates markdown note and normalizes tags', (tester) async {
    final api = _FakeNoteApi(
      projects: [
        {'id': 'p1', 'name': '旅行'},
      ],
    );
    await _pumpNotesPage(tester, api);

    await tester.tap(find.text('新增筆記').first);
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('note-title-field')),
      '行程筆記',
    );
    await tester.enterText(
      find.byKey(const ValueKey('note-body-field')),
      '# 東京\n**住宿** 已確認',
    );
    await tester.enterText(
      find.byKey(const ValueKey('note-tags-field')),
      '旅行, 重要, 旅行',
    );

    await tester.tap(find.text('預覽'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('note-markdown-preview')), findsOneWidget);
    expect(find.text('東京'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('note-save-button')));
    await tester.pumpAndSettle();

    final created = api.notes.single;
    expect(created['title'], '行程筆記');
    expect(created['body'], '# 東京\n**住宿** 已確認');
    expect(api.tags[created['id']], ['旅行', '重要']);
    expect(find.text('筆記已新增'), findsOneWidget);
    expect(find.text('行程筆記'), findsOneWidget);
  });

  testWidgets('surfaces partial success when note saves but tags fail', (tester) async {
    final api = _FakeNoteApi(failTagReplace: true);
    await _pumpNotesPage(tester, api);

    await tester.tap(find.text('新增筆記').first);
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('note-title-field')),
      '部分成功筆記',
    );
    await tester.enterText(
      find.byKey(const ValueKey('note-body-field')),
      'body',
    );
    await tester.enterText(
      find.byKey(const ValueKey('note-tags-field')),
      '重要',
    );
    await tester.tap(find.byKey(const ValueKey('note-save-button')));
    await tester.pumpAndSettle();

    expect(api.notes.single['title'], '部分成功筆記');
    expect(find.textContaining('筆記已儲存，但標籤更新失敗'), findsOneWidget);
  });

  testWidgets('edits links and deletes note after confirmation', (tester) async {
    final api = _FakeNoteApi(
      notes: [
        _note(id: 'n1', title: '主筆記', body: 'body'),
        _note(id: 'n2', title: '被連結筆記', body: 'target'),
      ],
    );
    await _pumpNotesPage(tester, api);

    await tester.tap(find.byTooltip('筆記選項').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('雙向連結'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('note-link-target-field')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('被連結筆記').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('note-link-add-button')));
    await tester.pumpAndSettle();
    expect(api.links['n1'], contains('n2'));
    expect(find.text('被連結筆記'), findsWidgets);

    await tester.tap(find.text('關閉'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('筆記選項').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除'));
    await tester.pumpAndSettle();
    expect(find.text('刪除筆記？'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(api.deletedIds, ['n1']);
    expect(find.text('筆記已刪除'), findsOneWidget);
    expect(find.text('主筆記'), findsNothing);
  });
}
