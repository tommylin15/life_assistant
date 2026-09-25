import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/acceptance_center_page.dart';
import 'package:life_assistant/web/acceptance_runner.dart';

class _CleanupApi implements AcceptanceApi {
  final List<String> deletedProjects = [];
  final List<String> deletedTasks = [];
  final List<String> deletedCalendarEvents = [];

  @override
  Future<void> deleteProject(String id) async => deletedProjects.add(id);

  @override
  Future<void> deleteTask(String id) async => deletedTasks.add(id);

  @override
  Future<void> deleteCalendarEvent(String eventId) async =>
      deletedCalendarEvents.add(eventId);

  @override
  Future<Map<String, dynamic>> getGoogleIntegrationStatus() async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> getProject(String id) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> createCalendarEvent(
    Map<String, dynamic> body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> updateCalendarEvent(
    String eventId,
    Map<String, dynamic> body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> getGmailMetadata({int limit = 1}) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> gmailMessageToTask(
    String messageId,
    Map<String, dynamic> body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> gmailMessageToProject(
    String messageId,
    Map<String, dynamic> body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> gmailMessageToCalendar(
    String messageId,
    Map<String, dynamic> body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getActivity({int limit = 100}) async =>
      throw UnimplementedError();
}

void main() {
  test('retry cleanup clears only the recorded acceptance artifacts', () async {
    final api = _CleanupApi();
    final remaining = await AcceptanceRunner(api).retryCleanup(
      AcceptanceArtifacts(
        projectIds: {'project-left'},
        taskIds: {'task-left'},
        calendarEventIds: {'calendar-left'},
      ),
    );

    expect(remaining.isEmpty, isTrue);
    expect(api.deletedProjects, ['project-left']);
    expect(api.deletedTasks, ['task-left']);
    expect(api.deletedCalendarEvents, ['calendar-left']);
  });

  testWidgets('acceptance center confirms, runs, and shows all status types',
      (tester) async {
    var runCalls = 0;
    var cleanupCalls = 0;
    final result = AcceptanceRunResult(
      label: '[ACCEPTANCE TEST] test-run',
      checks: const [
        AcceptanceCheck(
          key: 'pass',
          label: '通過項目',
          status: AcceptanceStatus.pass,
          detail: 'pass detail',
        ),
        AcceptanceCheck(
          key: 'fail',
          label: '失敗項目',
          status: AcceptanceStatus.fail,
          detail: 'fail detail',
        ),
        AcceptanceCheck(
          key: 'not-verified',
          label: '未驗證項目',
          status: AcceptanceStatus.notVerified,
          detail: 'not verified detail',
        ),
      ],
      remainingArtifacts: AcceptanceArtifacts(projectIds: {'left-project'}),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: AcceptanceCenterPage(
          runAcceptance: () async {
            runCalls += 1;
            return result;
          },
          retryCleanup: (artifacts) async {
            cleanupCalls += 1;
            return AcceptanceArtifacts();
          },
        ),
      ),
    );

    expect(find.text('驗收中心'), findsOneWidget);
    expect(find.text('執行完整驗收'), findsOneWidget);

    await tester.tap(find.text('執行完整驗收'));
    await tester.pump();
    expect(runCalls, 0);
    expect(find.text('確認執行驗收？'), findsOneWidget);

    await tester.tap(find.text('確認執行'));
    await tester.pumpAndSettle();
    expect(runCalls, 1);
    expect(find.text('PASS'), findsOneWidget);
    expect(find.text('FAIL'), findsOneWidget);
    expect(find.text('NOT VERIFIED'), findsOneWidget);
    expect(find.text('重試清理'), findsOneWidget);

    await tester.tap(find.text('重試清理'));
    await tester.pumpAndSettle();
    expect(cleanupCalls, 1);
    expect(find.text('重試清理'), findsNothing);
  });
}
