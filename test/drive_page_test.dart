import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/drive_page.dart';
import 'package:life_assistant/web/note_api.dart';

class _FakeDriveApi implements DriveApi {
  _FakeDriveApi({
    required this.documents,
    required this.settings,
    Map<String, Map<String, dynamic>?>? enrichments,
    Set<String>? enrichmentErrors,
  })  : enrichments = enrichments ?? {},
        enrichmentErrors = enrichmentErrors ?? {};

  final List<Map<String, dynamic>> documents;
  Map<String, dynamic> settings;
  final Map<String, Map<String, dynamic>?> enrichments;
  final Set<String> enrichmentErrors;
  final List<Map<String, String>> decisions = [];
  final List<Map<String, dynamic>> runRequests = [];

  @override
  Future<Map<String, dynamic>> decideNoteSuggestion(
    String suggestionId,
    String decision,
  ) async {
    decisions.add({'suggestion_id': suggestionId, 'decision': decision});
    for (final run in enrichments.values.whereType<Map<String, dynamic>>()) {
      final suggestions = (run['note_suggestions'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      for (final suggestion in suggestions) {
        if (suggestion['id'] == suggestionId) {
          suggestion['decision'] = decision;
          return suggestion;
        }
      }
    }
    throw StateError('suggestion not found');
  }

  @override
  Future<List<Map<String, dynamic>>> getDocuments() async => documents;

  @override
  Future<Map<String, dynamic>?> getEnrichment(String documentId) async {
    if (enrichmentErrors.contains(documentId)) {
      throw Exception('enrichment unavailable');
    }
    return enrichments[documentId];
  }

  @override
  Future<Map<String, dynamic>> getEnrichmentSettings() async => settings;

  @override
  Future<Map<String, dynamic>> runEnrichment(
    String documentId, {
    bool force = false,
  }) async {
    runRequests.add({'document_id': documentId, 'force': force});
    return enrichments[documentId] ??
        {
          'id': 'run-$documentId',
          'drive_document_id': documentId,
          'status': 'skipped',
          'suggested_tags': <String>[],
          'note_suggestions': <Map<String, dynamic>>[],
          'cache_hit': false,
        };
  }

  @override
  Future<Map<String, dynamic>> updateEnrichmentSettings(
    Map<String, dynamic> body,
  ) async {
    settings = {...settings, ...body};
    return settings;
  }
}

class _FakeNoteApi implements NoteApi {
  _FakeNoteApi(this.notes);

  final List<Map<String, dynamic>> notes;

  @override
  Future<List<Map<String, dynamic>>> getNotes({String query = ''}) async => notes;

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

Map<String, dynamic> _document(String id, String name) => {
      'id': id,
      'google_file_id': 'google-$id',
      'name': name,
      'mime_type': 'application/vnd.google-apps.document',
      'web_view_link': 'https://drive.google.com/$id',
      'modified_at': null,
      'created_at': '2026-10-02T00:00:00Z',
      'updated_at': '2026-10-02T00:00:00Z',
    };

Map<String, dynamic> _run(
  String documentId,
  String status, {
  List<String> tags = const [],
  List<Map<String, dynamic>> suggestions = const [],
  bool cacheHit = false,
}) =>
    {
      'id': 'run-$documentId',
      'drive_document_id': documentId,
      'content_fingerprint': 'fp-$documentId',
      'provider': 'openai-should-not-render',
      'model': 'vendor-model-should-not-render',
      'status': status,
      'suggested_tags': tags,
      'note_suggestions': suggestions,
      'error_code': status == 'partial' ? 'note_stage_failed' : null,
      'cache_hit': cacheHit,
      'created_at': '2026-10-02T00:00:00Z',
    };

Future<void> _pumpDrivePage(
  WidgetTester tester,
  _FakeDriveApi driveApi,
  _FakeNoteApi noteApi,
) async {
  tester.view.physicalSize = const Size(1200, 1600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        driveApiProvider.overrideWithValue(driveApi),
        noteApiProvider.overrideWithValue(noteApi),
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
  testWidgets(
    'reviews enrichment without exposing provider identity or hiding core documents',
    (tester) async {
      final driveApi = _FakeDriveApi(
        documents: [
          _document('d1', '旅行規劃'),
          _document('d2', 'AI 暫時失敗仍可見'),
          _document('d3', '尚未分析文件'),
          _document('d4', '分析失敗文件'),
          _document('d5', '略過分析文件'),
        ],
        settings: {
          'auto_tags_enabled': true,
          'note_suggestions_enabled': true,
          'allow_document_content': false,
          'max_related_note_suggestions': 5,
        },
        enrichments: {
          'd1': _run(
            'd1',
            'partial',
            tags: ['旅行', '行程'],
            cacheHit: true,
            suggestions: [
              {
                'id': 's1',
                'note_id': 'n1',
                'confidence': 0.91,
                'reason': '內容與秋季旅行筆記高度相關',
                'decision': 'pending',
                'decided_at': null,
                'created_at': '2026-10-02T00:00:00Z',
              },
            ],
          ),
          'd3': null,
          'd4': _run('d4', 'failed'),
          'd5': _run('d5', 'skipped'),
        },
        enrichmentErrors: {'d2'},
      );
      final noteApi = _FakeNoteApi([
        {'id': 'n1', 'title': '秋季旅行筆記'},
      ]);

      await _pumpDrivePage(tester, driveApi, noteApi);

      expect(find.text('Google Drive 智能整理'), findsOneWidget);
      expect(find.textContaining('目前未允許將文件內容送交 AI 分析'), findsOneWidget);
      expect(find.text('旅行規劃'), findsOneWidget);
      expect(find.text('AI 暫時失敗仍可見'), findsOneWidget);
      expect(find.text('部分完成'), findsOneWidget);
      expect(find.text('尚未分析'), findsOneWidget);
      expect(find.text('分析失敗'), findsOneWidget);
      expect(find.text('已略過'), findsOneWidget);
      expect(find.text('旅行'), findsOneWidget);
      expect(find.text('行程'), findsOneWidget);
      expect(find.text('秋季旅行筆記'), findsOneWidget);
      expect(find.text('使用快取'), findsOneWidget);
      expect(find.textContaining('智能整理狀態暫時無法取得'), findsOneWidget);
      expect(find.text('openai-should-not-render'), findsNothing);
      expect(find.text('vendor-model-should-not-render'), findsNothing);

      await tester.tap(find.byKey(const ValueKey('accept-s1')));
      await tester.pumpAndSettle();
      expect(
        driveApi.decisions,
        [
          {'suggestion_id': 's1', 'decision': 'accepted'},
        ],
      );
      expect(find.text('已接受'), findsOneWidget);

      await tester.tap(find.byKey(const ValueKey('reanalyze-d1')));
      await tester.pumpAndSettle();
      expect(
        driveApi.runRequests,
        [
          {'document_id': 'd1', 'force': true},
        ],
      );
    },
  );

  testWidgets('reject keeps the suggestion authoritative and visible', (tester) async {
    final driveApi = _FakeDriveApi(
      documents: [_document('d1', '工作文件')],
      settings: {
        'auto_tags_enabled': true,
        'note_suggestions_enabled': true,
        'allow_document_content': true,
        'max_related_note_suggestions': 5,
      },
      enrichments: {
        'd1': _run(
          'd1',
          'succeeded',
          suggestions: [
            {
              'id': 's2',
              'note_id': 'n2',
              'confidence': 0.7,
              'reason': '候選關係',
              'decision': 'pending',
              'decided_at': null,
              'created_at': '2026-10-02T00:00:00Z',
            },
          ],
        ),
      },
    );

    await _pumpDrivePage(tester, driveApi, _FakeNoteApi(const []));

    expect(find.textContaining('n2'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('reject-s2')));
    await tester.pumpAndSettle();

    expect(driveApi.decisions.single['decision'], 'rejected');
    expect(find.text('已拒絕'), findsOneWidget);
  });
}
