import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/note_api.dart';
import 'package:life_assistant/web/notes_page.dart';

class _FakeNoteApi implements NoteApi {
  final deleted = <String>[];

  @override
  Future<List<Map<String, dynamic>>> getNotes({String query = ''}) async => [
        {
          'id': 'n1',
          'title': '巢狀導航刪除驗收',
          'body': 'body',
          'project_id': null,
          'updated_at': '2026-10-02T00:00:00Z',
        },
      ];

  @override
  Future<List<Map<String, dynamic>>> getProjects() async => [];

  @override
  Future<void> deleteNote(String id) async {
    deleted.add(id);
  }

  @override
  Future<Map<String, dynamic>> createNote(Map<String, dynamic> body) =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> updateNote(
    String id,
    Map<String, dynamic> body,
  ) =>
      throw UnimplementedError();

  @override
  Future<List<String>> getNoteTags(String id) async => [];

  @override
  Future<List<String>> replaceNoteTags(String id, List<String> tags) async => tags;

  @override
  Future<List<Map<String, dynamic>>> getNoteLinks(String id) async => [];

  @override
  Future<void> linkNote(String id, String targetId) async {}

  @override
  Future<void> unlinkNote(String id, String targetId) async {}
}

void main() {
  testWidgets('delete confirmation closes root dialog from nested navigator',
      (tester) async {
    final api = _FakeNoteApi();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [noteApiProvider.overrideWithValue(api)],
        child: MaterialApp(
          home: Navigator(
            onGenerateRoute: (_) => MaterialPageRoute<void>(
              builder: (_) => const NotesPage(),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('巢狀導航刪除驗收'), findsOneWidget);
    await tester.tap(find.byTooltip('筆記選項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除'));
    await tester.pumpAndSettle();

    expect(find.text('刪除筆記？'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '刪除'));
    await tester.pumpAndSettle();

    expect(api.deleted, ['n1']);
    expect(find.text('刪除筆記？'), findsNothing);
  });
}
