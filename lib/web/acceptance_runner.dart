enum AcceptanceStatus { pass, fail, notVerified }

class AcceptanceCheck {
  const AcceptanceCheck({
    required this.key,
    required this.label,
    required this.status,
    required this.detail,
  });

  final String key;
  final String label;
  final AcceptanceStatus status;
  final String detail;
}

class AcceptanceArtifacts {
  AcceptanceArtifacts({
    Set<String>? projectIds,
    Set<String>? taskIds,
    Set<String>? calendarEventIds,
  })  : projectIds = {...?projectIds},
        taskIds = {...?taskIds},
        calendarEventIds = {...?calendarEventIds};

  final Set<String> projectIds;
  final Set<String> taskIds;
  final Set<String> calendarEventIds;

  bool get isEmpty =>
      projectIds.isEmpty && taskIds.isEmpty && calendarEventIds.isEmpty;

  AcceptanceArtifacts copy() => AcceptanceArtifacts(
        projectIds: projectIds,
        taskIds: taskIds,
        calendarEventIds: calendarEventIds,
      );
}

class AcceptanceRunResult {
  const AcceptanceRunResult({
    required this.label,
    required this.checks,
    required this.remainingArtifacts,
  });

  final String label;
  final List<AcceptanceCheck> checks;
  final AcceptanceArtifacts remainingArtifacts;
}

abstract class AcceptanceApi {
  Future<Map<String, dynamic>> getGoogleIntegrationStatus();

  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body);
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>> getProject(String id);
  Future<void> deleteProject(String id);

  Future<Map<String, dynamic>> createCalendarEvent(Map<String, dynamic> body);
  Future<Map<String, dynamic>> updateCalendarEvent(
    String eventId,
    Map<String, dynamic> body,
  );
  Future<void> deleteCalendarEvent(String eventId);

  Future<Map<String, dynamic>> getGmailMetadata({int limit = 1});
  Future<Map<String, dynamic>> gmailMessageToTask(
    String messageId,
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>> gmailMessageToProject(
    String messageId,
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>> gmailMessageToCalendar(
    String messageId,
    Map<String, dynamic> body,
  );

  Future<void> deleteTask(String id);
  Future<List<Map<String, dynamic>>> getActivity({int limit = 100});
}

typedef _ExpectedActivity = ({String actionType, String entityId});

class AcceptanceRunner {
  AcceptanceRunner(this.api);

  final AcceptanceApi api;

  Future<AcceptanceRunResult> runAll() async {
    final label =
        '[ACCEPTANCE TEST] ${DateTime.now().toUtc().toIso8601String()}';
    final checks = <AcceptanceCheck>[];
    final artifacts = AcceptanceArtifacts();
    final expectedActivity = <_ExpectedActivity>{};

    var grantedServices = <String>{};
    try {
      final status = await api.getGoogleIntegrationStatus();
      grantedServices = ((status['granted_services'] as List?) ?? const [])
          .map((item) => item.toString())
          .toSet();
    } catch (_) {
      grantedServices = <String>{};
    }

    await _runProject(label, checks, artifacts, expectedActivity);
    await _runCalendar(
      label,
      grantedServices,
      checks,
      artifacts,
      expectedActivity,
    );
    await _runGmail(
      label,
      grantedServices,
      checks,
      artifacts,
      expectedActivity,
    );

    final cleanupErrors = await _cleanup(artifacts);
    _add(
      checks,
      key: 'cleanup',
      label: '測試資料清理',
      status: cleanupErrors.isEmpty
          ? AcceptanceStatus.pass
          : AcceptanceStatus.fail,
      detail: cleanupErrors.isEmpty
          ? '所有已建立的 [ACCEPTANCE TEST] 測試資料都已清除。'
          : '仍有 ${_artifactCount(artifacts)} 筆測試資料未清除：${cleanupErrors.join('；')}',
    );

    await _verifyActivity(checks, expectedActivity);

    return AcceptanceRunResult(
      label: label,
      checks: checks,
      remainingArtifacts: artifacts.copy(),
    );
  }

  Future<void> _runProject(
    String label,
    List<AcceptanceCheck> checks,
    AcceptanceArtifacts artifacts,
    Set<_ExpectedActivity> expectedActivity,
  ) async {
    String? projectId;
    final updatedName = '$label Project Updated';

    try {
      final created = await api.createProject({
        'name': '$label Project',
        'summary': '$label automatic project acceptance',
        'status': 'active',
      });
      projectId = _extractId(created);
      if (projectId == null) {
        throw StateError('Project create response missing id');
      }
      artifacts.projectIds.add(projectId);
      expectedActivity.add((actionType: 'project.create', entityId: projectId));
      _add(
        checks,
        key: 'project.create',
        label: 'Project 建立',
        status: AcceptanceStatus.pass,
        detail: '已建立 $projectId',
      );
    } catch (error) {
      _add(
        checks,
        key: 'project.create',
        label: 'Project 建立',
        status: AcceptanceStatus.fail,
        detail: '建立失敗：$error',
      );
      _notVerified(checks, 'project.update', 'Project 修改', '前置 Project 建立未成功。');
      _notVerified(checks, 'project.reread', 'Project 讀回', '前置 Project 建立未成功。');
      _notVerified(checks, 'project.delete', 'Project 刪除', '前置 Project 建立未成功。');
      return;
    }

    try {
      final updated = await api.updateProject(projectId, {'name': updatedName});
      if (updated['name'] != updatedName) {
        throw StateError('Project update response did not contain updated name');
      }
      expectedActivity.add((actionType: 'project.update', entityId: projectId));
      _add(
        checks,
        key: 'project.update',
        label: 'Project 修改',
        status: AcceptanceStatus.pass,
        detail: '修改回應符合預期。',
      );
    } catch (error) {
      _add(
        checks,
        key: 'project.update',
        label: 'Project 修改',
        status: AcceptanceStatus.fail,
        detail: '修改失敗：$error',
      );
    }

    try {
      final reread = await api.getProject(projectId);
      if (reread['name'] != updatedName) {
        throw StateError('Project reread data mismatch');
      }
      _add(
        checks,
        key: 'project.reread',
        label: 'Project 讀回',
        status: AcceptanceStatus.pass,
        detail: '重新讀取後資料與修改結果一致。',
      );
    } catch (error) {
      _add(
        checks,
        key: 'project.reread',
        label: 'Project 讀回',
        status: AcceptanceStatus.fail,
        detail: '讀回驗證失敗：$error',
      );
    }

    try {
      await api.deleteProject(projectId);
      artifacts.projectIds.remove(projectId);
      expectedActivity.add((actionType: 'project.delete', entityId: projectId));
      _add(
        checks,
        key: 'project.delete',
        label: 'Project 刪除',
        status: AcceptanceStatus.pass,
        detail: '測試 Project 已刪除。',
      );
    } catch (error) {
      _add(
        checks,
        key: 'project.delete',
        label: 'Project 刪除',
        status: AcceptanceStatus.fail,
        detail: '刪除失敗；將由 cleanup 再嘗試：$error',
      );
    }
  }

  Future<void> _runCalendar(
    String label,
    Set<String> grantedServices,
    List<AcceptanceCheck> checks,
    AcceptanceArtifacts artifacts,
    Set<_ExpectedActivity> expectedActivity,
  ) async {
    if (!grantedServices.contains('calendar')) {
      _notVerified(checks, 'calendar.create', 'Calendar 建立', 'Calendar 尚未授權。');
      _notVerified(checks, 'calendar.update', 'Calendar 修改', 'Calendar 尚未授權。');
      _notVerified(checks, 'calendar.delete', 'Calendar 刪除', 'Calendar 尚未授權。');
      return;
    }

    final start = DateTime.now().toUtc().add(const Duration(days: 1));
    final end = start.add(const Duration(minutes: 30));
    final updatedSummary = '$label Calendar Updated';
    String? eventId;

    try {
      final created = await api.createCalendarEvent({
        'summary': '$label Calendar',
        'start': start.toIso8601String(),
        'end': end.toIso8601String(),
        'description': '$label automatic calendar acceptance',
      });
      eventId = _extractId(created, nestedKey: 'event');
      if (eventId == null) {
        throw StateError('Calendar create response missing id');
      }
      artifacts.calendarEventIds.add(eventId);
      expectedActivity.add((actionType: 'calendar.create', entityId: eventId));
      _add(
        checks,
        key: 'calendar.create',
        label: 'Calendar 建立',
        status: AcceptanceStatus.pass,
        detail: '已建立 $eventId',
      );
    } catch (error) {
      _add(
        checks,
        key: 'calendar.create',
        label: 'Calendar 建立',
        status: AcceptanceStatus.fail,
        detail: '建立失敗：$error',
      );
      _notVerified(checks, 'calendar.update', 'Calendar 修改', '前置 Calendar 建立未成功。');
      _notVerified(checks, 'calendar.delete', 'Calendar 刪除', '前置 Calendar 建立未成功。');
      return;
    }

    try {
      final updated = await api.updateCalendarEvent(
        eventId,
        {'summary': updatedSummary},
      );
      if (updated['summary'] != updatedSummary) {
        throw StateError('Calendar update response mismatch');
      }
      expectedActivity.add((actionType: 'calendar.update', entityId: eventId));
      _add(
        checks,
        key: 'calendar.update',
        label: 'Calendar 修改',
        status: AcceptanceStatus.pass,
        detail: '修改回應符合預期。',
      );
    } catch (error) {
      _add(
        checks,
        key: 'calendar.update',
        label: 'Calendar 修改',
        status: AcceptanceStatus.fail,
        detail: '修改失敗：$error',
      );
    }

    try {
      await api.deleteCalendarEvent(eventId);
      artifacts.calendarEventIds.remove(eventId);
      expectedActivity.add((actionType: 'calendar.delete', entityId: eventId));
      _add(
        checks,
        key: 'calendar.delete',
        label: 'Calendar 刪除',
        status: AcceptanceStatus.pass,
        detail: '測試 Calendar event 已刪除。',
      );
    } catch (error) {
      _add(
        checks,
        key: 'calendar.delete',
        label: 'Calendar 刪除',
        status: AcceptanceStatus.fail,
        detail: '刪除失敗；將由 cleanup 再嘗試：$error',
      );
    }
  }

  Future<void> _runGmail(
    String label,
    Set<String> grantedServices,
    List<AcceptanceCheck> checks,
    AcceptanceArtifacts artifacts,
    Set<_ExpectedActivity> expectedActivity,
  ) async {
    if (!grantedServices.contains('gmail')) {
      _gmailNotVerified(checks, 'Gmail 尚未授權，未執行真實帳號測試。');
      return;
    }

    String? messageId;
    try {
      final response = await api.getGmailMetadata(limit: 1);
      final messages = (response['messages'] as List?) ?? const [];
      if (messages.isEmpty) {
        _gmailNotVerified(
          checks,
          '最近沒有可供驗收的 Gmail 郵件，因此未建立衍生資料。',
        );
        return;
      }
      final first = messages.first;
      if (first is! Map) {
        throw StateError('Unexpected Gmail metadata response');
      }
      messageId = first['id']?.toString();
      if (messageId == null || messageId.isEmpty) {
        throw StateError('Gmail message missing id');
      }
      _add(
        checks,
        key: 'gmail.read',
        label: 'Gmail 讀取',
        status: AcceptanceStatus.pass,
        detail: '已取得一封 Gmail metadata。',
      );
    } catch (error) {
      _add(
        checks,
        key: 'gmail.read',
        label: 'Gmail 讀取',
        status: AcceptanceStatus.fail,
        detail: 'Gmail metadata 讀取失敗：$error',
      );
      _notVerified(checks, 'gmail.to_task', 'Gmail → Task', '前置 Gmail 讀取未成功。');
      _notVerified(checks, 'gmail.to_project', 'Gmail → Project', '前置 Gmail 讀取未成功。');
      _notVerified(checks, 'gmail.to_calendar', 'Gmail → Calendar', '前置 Gmail 讀取未成功。');
      return;
    }

    try {
      final result = await api.gmailMessageToTask(messageId, {
        'title': '$label Gmail Task',
        'note': '$label automatic Gmail to Task acceptance',
      });
      final taskId = _extractId(result, nestedKey: 'task');
      if (taskId == null) {
        throw StateError('Gmail to Task response missing id');
      }
      artifacts.taskIds.add(taskId);
      expectedActivity.add((actionType: 'gmail.to_task', entityId: taskId));
      _add(
        checks,
        key: 'gmail.to_task',
        label: 'Gmail → Task',
        status: AcceptanceStatus.pass,
        detail: '已建立測試 Task $taskId',
      );
    } catch (error) {
      _add(
        checks,
        key: 'gmail.to_task',
        label: 'Gmail → Task',
        status: AcceptanceStatus.fail,
        detail: '轉換失敗：$error',
      );
    }

    try {
      final result = await api.gmailMessageToProject(messageId, {
        'name': '$label Gmail Project',
        'summary': '$label automatic Gmail to Project acceptance',
        'status': 'active',
      });
      final projectId = _extractId(result, nestedKey: 'project');
      if (projectId == null) {
        throw StateError('Gmail to Project response missing id');
      }
      artifacts.projectIds.add(projectId);
      expectedActivity.add((actionType: 'gmail.to_project', entityId: projectId));
      _add(
        checks,
        key: 'gmail.to_project',
        label: 'Gmail → Project',
        status: AcceptanceStatus.pass,
        detail: '已建立測試 Project $projectId',
      );
    } catch (error) {
      _add(
        checks,
        key: 'gmail.to_project',
        label: 'Gmail → Project',
        status: AcceptanceStatus.fail,
        detail: '轉換失敗：$error',
      );
    }

    if (!grantedServices.contains('calendar')) {
      _notVerified(
        checks,
        'gmail.to_calendar',
        'Gmail → Calendar',
        'Calendar 尚未授權，無法驗證 Gmail → Calendar。',
      );
      return;
    }

    final start = DateTime.now().toUtc().add(const Duration(days: 2));
    final end = start.add(const Duration(minutes: 30));
    try {
      final result = await api.gmailMessageToCalendar(messageId, {
        'summary': '$label Gmail Calendar',
        'description': '$label automatic Gmail to Calendar acceptance',
        'start': start.toIso8601String(),
        'end': end.toIso8601String(),
      });
      final eventId = _extractId(result, nestedKey: 'event');
      if (eventId == null) {
        throw StateError('Gmail to Calendar response missing id');
      }
      artifacts.calendarEventIds.add(eventId);
      expectedActivity.add((actionType: 'gmail.to_calendar', entityId: eventId));
      _add(
        checks,
        key: 'gmail.to_calendar',
        label: 'Gmail → Calendar',
        status: AcceptanceStatus.pass,
        detail: '已建立測試 Calendar event $eventId',
      );
    } catch (error) {
      _add(
        checks,
        key: 'gmail.to_calendar',
        label: 'Gmail → Calendar',
        status: AcceptanceStatus.fail,
        detail: '轉換失敗：$error',
      );
    }
  }

  Future<List<String>> _cleanup(AcceptanceArtifacts artifacts) async {
    final errors = <String>[];

    for (final id in artifacts.taskIds.toList()) {
      try {
        await api.deleteTask(id);
        artifacts.taskIds.remove(id);
      } catch (error) {
        errors.add('Task $id: $error');
      }
    }
    for (final id in artifacts.projectIds.toList()) {
      try {
        await api.deleteProject(id);
        artifacts.projectIds.remove(id);
      } catch (error) {
        errors.add('Project $id: $error');
      }
    }
    for (final id in artifacts.calendarEventIds.toList()) {
      try {
        await api.deleteCalendarEvent(id);
        artifacts.calendarEventIds.remove(id);
      } catch (error) {
        errors.add('Calendar $id: $error');
      }
    }

    return errors;
  }

  Future<void> _verifyActivity(
    List<AcceptanceCheck> checks,
    Set<_ExpectedActivity> expectedActivity,
  ) async {
    try {
      final activity = await api.getActivity(limit: 100);
      final missing = <String>[];
      for (final expected in expectedActivity) {
        final found = activity.any(
          (item) =>
              item['action_type'] == expected.actionType &&
              item['entity_id'] == expected.entityId &&
              item['status'] == 'success',
        );
        if (!found) {
          missing.add('${expected.actionType}:${expected.entityId}');
        }
      }
      _add(
        checks,
        key: 'activity',
        label: 'Activity Log',
        status: missing.isEmpty ? AcceptanceStatus.pass : AcceptanceStatus.fail,
        detail: missing.isEmpty
            ? '本次重要操作均找到成功 execution evidence。'
            : '缺少 ${missing.length} 筆 execution evidence：${missing.join(', ')}',
      );
    } catch (error) {
      _add(
        checks,
        key: 'activity',
        label: 'Activity Log',
        status: AcceptanceStatus.fail,
        detail: 'Activity Log 讀取失敗：$error',
      );
    }
  }

  void _gmailNotVerified(List<AcceptanceCheck> checks, String detail) {
    _notVerified(checks, 'gmail.read', 'Gmail 讀取', detail);
    _notVerified(checks, 'gmail.to_task', 'Gmail → Task', detail);
    _notVerified(checks, 'gmail.to_project', 'Gmail → Project', detail);
    _notVerified(checks, 'gmail.to_calendar', 'Gmail → Calendar', detail);
  }

  void _notVerified(
    List<AcceptanceCheck> checks,
    String key,
    String label,
    String detail,
  ) {
    _add(
      checks,
      key: key,
      label: label,
      status: AcceptanceStatus.notVerified,
      detail: detail,
    );
  }

  void _add(
    List<AcceptanceCheck> checks, {
    required String key,
    required String label,
    required AcceptanceStatus status,
    required String detail,
  }) {
    checks.add(AcceptanceCheck(
      key: key,
      label: label,
      status: status,
      detail: detail,
    ));
  }

  int _artifactCount(AcceptanceArtifacts artifacts) =>
      artifacts.projectIds.length +
      artifacts.taskIds.length +
      artifacts.calendarEventIds.length;

  String? _extractId(Map<String, dynamic> response, {String? nestedKey}) {
    final root = response['id'];
    if (root != null && root.toString().isNotEmpty) {
      return root.toString();
    }
    if (nestedKey != null) {
      final nested = response[nestedKey];
      if (nested is Map) {
        final value = nested['id'];
        if (value != null && value.toString().isNotEmpty) {
          return value.toString();
        }
      }
    }
    return null;
  }
}
