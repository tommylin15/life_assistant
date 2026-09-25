import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/acceptance_runner.dart';

class _FakeAcceptanceApi implements AcceptanceApi {
  _FakeAcceptanceApi({this.gmailMessages = const [
    {'id': 'gmail-1', 'subject': 'Acceptance source'}
  ]});

  final List<Map<String, dynamic>> gmailMessages;
  final List<String> deletedProjectIds = [];
  final List<String> deletedTaskIds = [];
  final List<String> deletedCalendarIds = [];
  final List<Map<String, dynamic>> _activity = [];

  Map<String, dynamic>? _project;
  var _projectCounter = 0;
  var _calendarCounter = 0;
  var _taskCounter = 0;

  void _log(String actionType, String entityId) {
    _activity.insert(0, {
      'action_type': actionType,
      'entity_id': entityId,
      'status': 'success',
      'result': 'ok',
    });
  }

  @override
  Future<Map<String, dynamic>> getGoogleIntegrationStatus() async => {
        'connected': true,
        'granted_services': ['gmail', 'calendar'],
      };

  @override
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body) async {
    final id = 'project-${++_projectCounter}';
    _project = {'id': id, ...body};
    _log('project.create', id);
    return Map<String, dynamic>.from(_project!);
  }

  @override
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  ) async {
    _project = {'id': id, ...?_project, ...body};
    _log('project.update', id);
    return Map<String, dynamic>.from(_project!);
  }

  @override
  Future<Map<String, dynamic>> getProject(String id) async =>
      Map<String, dynamic>.from(_project!);

  @override
  Future<void> deleteProject(String id) async {
    deletedProjectIds.add(id);
    _log('project.delete', id);
  }

  @override
  Future<Map<String, dynamic>> createCalendarEvent(
    Map<String, dynamic> body,
  ) async {
    final id = 'calendar-${++_calendarCounter}';
    _log('calendar.create', id);
    return {'id': id, ...body};
  }

  @override
  Future<Map<String, dynamic>> updateCalendarEvent(
    String eventId,
    Map<String, dynamic> body,
  ) async {
    _log('calendar.update', eventId);
    return {'id': eventId, ...body};
  }

  @override
  Future<void> deleteCalendarEvent(String eventId) async {
    deletedCalendarIds.add(eventId);
    _log('calendar.delete', eventId);
  }

  @override
  Future<Map<String, dynamic>> getGmailMetadata({int limit = 1}) async => {
        'messages': gmailMessages.take(limit).toList(),
        'returned': gmailMessages.take(limit).length,
      };

  @override
  Future<Map<String, dynamic>> gmailMessageToTask(
    String messageId,
    Map<String, dynamic> body,
  ) async {
    final id = 'task-${++_taskCounter}';
    _log('gmail.to_task', id);
    return {
      'task': {'id': id, ...body}
    };
  }

  @override
  Future<Map<String, dynamic>> gmailMessageToProject(
    String messageId,
    Map<String, dynamic> body,
  ) async {
    final id = 'project-${++_projectCounter}';
    _log('gmail.to_project', id);
    return {
      'project': {'id': id, ...body}
    };
  }

  @override
  Future<Map<String, dynamic>> gmailMessageToCalendar(
    String messageId,
    Map<String, dynamic> body,
  ) async {
    final id = 'calendar-${++_calendarCounter}';
    _log('gmail.to_calendar', id);
    return {'id': id, ...body};
  }

  @override
  Future<void> deleteTask(String id) async {
    deletedTaskIds.add(id);
  }

  @override
  Future<List<Map<String, dynamic>>> getActivity({int limit = 100}) async =>
      _activity.take(limit).toList();
}

AcceptanceCheck _check(AcceptanceRunResult result, String key) =>
    result.checks.singleWhere((item) => item.key == key);

void main() {
  test('complete acceptance run passes and cleans created test data', () async {
    final api = _FakeAcceptanceApi();
    final result = await AcceptanceRunner(api).runAll();

    expect(result.label, startsWith('[ACCEPTANCE TEST]'));
    for (final key in [
      'project.create',
      'project.update',
      'project.reread',
      'project.delete',
      'calendar.create',
      'calendar.update',
      'calendar.delete',
      'gmail.read',
      'gmail.to_task',
      'gmail.to_project',
      'gmail.to_calendar',
      'activity',
      'cleanup',
    ]) {
      expect(_check(result, key).status, AcceptanceStatus.pass, reason: key);
    }

    expect(api.deletedTaskIds, contains('task-1'));
    expect(api.deletedProjectIds, containsAll(['project-1', 'project-2']));
    expect(api.deletedCalendarIds, containsAll(['calendar-1', 'calendar-2']));
    expect(result.remainingArtifacts.isEmpty, isTrue);
  });

  test('empty Gmail inbox is NOT VERIFIED instead of FAIL', () async {
    final api = _FakeAcceptanceApi(gmailMessages: const []);
    final result = await AcceptanceRunner(api).runAll();

    for (final key in [
      'gmail.read',
      'gmail.to_task',
      'gmail.to_project',
      'gmail.to_calendar',
    ]) {
      expect(
        _check(result, key).status,
        AcceptanceStatus.notVerified,
        reason: key,
      );
    }
    expect(_check(result, 'cleanup').status, AcceptanceStatus.pass);
  });
}
