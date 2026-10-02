import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/drive_api.dart';
import 'package:life_assistant/web/drive_settings_page.dart';

class _FakeDriveApi implements DriveApi {
  _FakeDriveApi(this.settings, {this.failSave = false});

  Map<String, dynamic> settings;
  final bool failSave;
  Map<String, dynamic>? lastUpdate;

  @override
  Future<Map<String, dynamic>> getEnrichmentSettings() async => settings;

  @override
  Future<Map<String, dynamic>> updateEnrichmentSettings(
    Map<String, dynamic> body,
  ) async {
    lastUpdate = Map<String, dynamic>.from(body);
    if (failSave) throw Exception('save failed');
    settings = {...settings, ...body};
    return settings;
  }

  @override
  Future<Map<String, dynamic>> decideNoteSuggestion(
    String suggestionId,
    String decision,
  ) =>
      throw UnimplementedError();
  @override
  Future<List<Map<String, dynamic>>> getDocuments() => throw UnimplementedError();
  @override
  Future<Map<String, dynamic>?> getEnrichment(String documentId) =>
      throw UnimplementedError();
  @override
  Future<Map<String, dynamic>> runEnrichment(
    String documentId, {
    bool force = false,
  }) =>
      throw UnimplementedError();
}

Future<void> _pumpSettings(WidgetTester tester, _FakeDriveApi api) async {
  tester.view.physicalSize = const Size(900, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [driveApiProvider.overrideWithValue(api)],
      child: MaterialApp(
        theme: AppTheme.light,
        home: const DriveSettingsPage(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Map<String, dynamic> _settings() => {
      'auto_tags_enabled': true,
      'note_suggestions_enabled': true,
      'allow_document_content': false,
      'max_related_note_suggestions': 5,
    };

void main() {
  testWidgets('renders explicit consent and persists all provider-neutral settings', (
    tester,
  ) async {
    final api = _FakeDriveApi(_settings());
    await _pumpSettings(tester, api);

    expect(find.widgetWithText(AppBar, '智能整理設定'), findsOneWidget);
    expect(find.text('自動套用建議標籤'), findsOneWidget);
    expect(find.text('建議相關筆記'), findsOneWidget);
    expect(find.text('允許將文件內容送交 AI 分析'), findsOneWidget);
    expect(find.textContaining('文件內容可能會送交目前設定的 AI 分析服務'), findsOneWidget);

    final consent = tester.widget<SwitchListTile>(
      find.widgetWithText(SwitchListTile, '允許將文件內容送交 AI 分析'),
    );
    expect(consent.value, isFalse);

    await tester.tap(
      find.widgetWithText(SwitchListTile, '允許將文件內容送交 AI 分析'),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('max-related-note-suggestions')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('8').last);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('save-drive-ai-settings')));
    await tester.pumpAndSettle();

    expect(api.lastUpdate, {
      'auto_tags_enabled': true,
      'note_suggestions_enabled': true,
      'allow_document_content': true,
      'max_related_note_suggestions': 8,
    });
    expect(find.text('設定已儲存'), findsOneWidget);
  });

  testWidgets('save failure stays visible and never claims success', (tester) async {
    final api = _FakeDriveApi(_settings(), failSave: true);
    await _pumpSettings(tester, api);

    await tester.tap(find.byKey(const ValueKey('save-drive-ai-settings')));
    await tester.pumpAndSettle();

    expect(find.textContaining('設定儲存失敗'), findsOneWidget);
    expect(find.text('設定已儲存'), findsNothing);
  });
}
