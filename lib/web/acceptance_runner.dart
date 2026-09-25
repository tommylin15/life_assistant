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

class AcceptanceRunner {
  AcceptanceRunner(this.api);

  final AcceptanceApi api;

  Future<AcceptanceRunResult> runAll() async {
    final label =
        '[ACCEPTANCE TEST] ${DateTime.now().toUtc().toIso8601String()}';
    final checks = <AcceptanceCheck>[];
    final artifacts = AcceptanceArtifacts();
    final expectedActivity = <String, Set<String>>{};

    void add(
      String key,
      String displayLabel,
      AcceptanceStatus status,
      String detail,
    ) {
      checks.add(AcceptanceCheck(
        key: key,
        label: displayLabel,
        status: status,
        detail: detail,
      ));
    }

    void expectActivity(String actionType, String entityId) {
      expectedActivity.putIfAbsent(actionType, () => <String>{}).add(entityId);
    }

    Set<String> grantedServices = const {};
    try {
      final status = await api.getGoogleIntegrationStatus();
      grantedServices = ((status['granted_services'] as List?) ?? const [])
          .map((item) => item.toString())
          .toSet();
    } catch (_) {
      grantedServices = const {};
    }

    await _runProjectChecks(
      label: label,
      checks: checks,
      artifacts: artifacts,
      expectedActivity: expectedActivity,
      add: add,
      expectActivity: expectActivity,
    );

    await _runCalendarChecks(
      label: label,
      grantedServices: grantedServices,
      checks: checks,
      artifacts: artifacts,
      expectedActivity: expectedActivity,
      add: add,
      expectActivity: expectActivity,
    );

    await _runGmailChecks(
      label: label,
      grantedServices: grantedServices,
      checks: checks,
      artifacts: artifacts,
      expectedActivity: expectedActivity,
      add: add,
      expectActivity: expectActivity,
    );

    final cleanupErrors = await _cleanupArtifacts(artifacts);
    add(
      'cleanup',
      '測試資料清理',
      cleanupErrors.isEmpty ? AcceptanceStatus.pass : AcceptanceStatus.fail,
      cleanupErrors.isEmpty
          ? '所有已建立的 [ACCEPTANCE TEST] 測試資料都已清除。'
          : '仍有 ${artifacts.projectIds.length + artifacts.taskIds.length + artifacts.calendarEventIds.length} 筆測試資料未清除：${cleanupErrors.join('；')}',
    );

    try {
      final activity = await api.getActivity(limit: 100);
      final missing = <String>[];
      for (final entry in expectedActivity.entries) {
        for (final entityId in entry.value) {
          final found = activity.any(
            (item) =>
                item['action_type'] == entry.key &&
                item['entity_id'] == entityId &&
                item['status'] == 'succeeded',
          );
          if (!found) {
            missing.add('${entry.key}:$entityId');
          }
        }
      }
      add(
        'activity',
        'Activity Log',
        missing.isEmpty ? AcceptanceStatus.pass : AcceptanceStatus.fail,
        missing.isEmpty
            ? '本次重要操作均找到成功 execution evidence。'
            : '缺少 ${missing.length} 筆 execution evidence：${missing.join(', ')}',
      );
    } catch (error) {
      add(
        'activity',
        'Activity Log',
        AcceptanceStatus.fail,
        'Activity Log 讀取失敗：$error',
      );
    }

    return AcceptanceRunResult(
      label: label,
      checks: checks,
      remainingArtifacts: artifacts.copy(),
    );
  }

  Future<void> _runProjectChecks({
    required String label,
    required List<AcceptanceCheck> checks,
    required AcceptanceArtifacts artifacts,
    required Map<String, Set<String>> expectedActivity,
    required void Function(
      String key,
      String displayLabel,
      AcceptanceStatus status,
      String detail,
    ) add,
    required void Function(String actionType, String entityId) expectActivity,
  }) async {
    String? projectId;
    final updatedName = '$label Project Updated';

    try {
      final project = await api.createProject({
        'name': '$label Project',
        'summary': '$label automatic project acceptance',
        'status': 'active',
      });
      projectId = _extractId(project);
      if (projectId == null) {
        throw StateError('Project create response missing id');
      }
      artifacts.projectIds.add(projectId);
      expectActivity('project.create', projectId);
      add(
        'project.create',
        'Project 建立',
        AcceptanceStatus.pass,
        '已建立 $projectId',
      );
    } catch (error) {
      add(
        'project.create',
        'Project 建立',
        AcceptanceStatus.fail,
        '建立失敗：$error',
      );
      for (final item in const [
        ('project.update', 'Project 修改'),
        ('project.reread', 'Project 讀回'),
        ('project.delete', 'Project 刪除'),
      ]) {
        add(
          item.$1,
          item.$2,
          AcceptanceStatus.notVerified,
          '前置 Project 建立未成功。',
        );
      }
      return;
    }

    try {
      final updated = await api.updateProject(projectId, {'name': updatedName});
      final matches = updated['name'] == updatedName;
      if (!matches) {
        throw StateError('Project update response did not contain updated name');
      }
      expectActivity('project.update', projectId);
      add(
        'project.update',
        'Project 修改',
        AcceptanceStatus.pass,
        '修改回應符合預期。',
      );
    } catch (error) {
      add(
        'project.update',
        'Project 修改',
        AcceptanceStatus.fail,
        '修改失敗：$error',
      );
    }

    try {
      final reread = await api.getProject(projectId);
      if (reread['name'] != updatedName) {
        throw StateError('Project reread data mismatch');
      }
      add(
        'project.reread',
        'Project 讀回',
        AcceptanceStatus.pass,
        '重新讀取後資料與修改結果一致。',
      );
    } catch (error) {
      add(
        'project.reread',
        'Project 讀回',
        AcceptanceStatus.fail,
        '讀回驗證失敗：$error',
      );
    }

    try {
      await api.deleteProject(projectId);
      artifacts.projectIds.remove(projectId);
      expectActivity('project.delete', projectId);
      add(
        'project.delete',
        'Project 刪除',
        AcceptanceStatus.pass,
        '測試 Project 已刪除。',
      );
    } catch (error) {
      add(
        'project.delete',
        'Project 刪除',
        AcceptanceStatus.fail,
        '刪除失敗；將由 cleanup 再嘗試：$error',
      );
    }
  }

  Future<void> _runCalendarChecks({
    required String label,
    required Set<String> grantedServices,
    required List<AcceptanceCheck> checks,
    required AcceptanceArtifacts artifacts,
    required Map<String, Set<String>> expectedActivity,
    required void Function(
      String key,
      String displayLabel,
      AcceptanceStatus status,
      String detail,
    ) add,
    required void Function(String actionType, String entityId) expectActivity,
  }) async {
    if (!grantedServices.contains('calendar')) {
      for (final item in const [
        ('calendar.create', 'Calendar 建立'),
        ('calendar.update', 'Calendar 修改'),
        ('calendar.delete', 'Calendar 刪除'),
      ]) {
        add(
          item.$1,
          item.$2,
          AcceptanceStatus.notVerified,
          'Calendar 尚未授權，未執行真實帳號測試。',
        );
      }
      return;
    }

    final start = DateTime.now().toUtc().add(const Duration(days: 1));
    final end = start.add(const Duration(minutes: 30));
    final updatedSummary = '$label Calendar Updated';
    String? eventId;

    try {
      final event = await api.createCalendarEvent({
        'summary': '$label Calendar',
        'start': start.toIso8601String(),
        'end': end.toIso8601String(),
        'description': '$label automatic calendar acceptance',
      });
      eventId = _extractId(event, nestedKey: 'event');
      if (eventId == null) {
        throw StateError('Calendar create response missing id');
      }
      artifacts.calendarEventIds.add(eventId);
      expectActivity('calendar.create', eventId);
      add(
        'calendar.create',
        'Calendar 建立',
        AcceptanceStatus.pass,
        '已建立 $eventId',
      );
    } catch (error) {
      add(
        'calendar.create',
        'Calendar 建立',
        AcceptanceStatus.fail,
        '建立失敗：$error',
      );
      add(
        'calendar.update',
        'Calendar 修改',
        AcceptanceStatus.notVerified,
        '前置 Calendar 建立未成功。',
      );
      add(
        'calendar.delete',
        'Calendar 刪除',
        AcceptanceStatus.notVerified,
        '前置 Calendar 建立未成功。',
      );
      return;
    }

    try {
      final updated = await api.updateCalendarEvent(eventId, {
        'summary': updatedSummary,
      });
      if (updated['summary'] != updatedSummary) {
        throw StateError('Calendar update response mismatch');
      }
      expectActivity('calendar.update', eventId);
      add(
        'calendar.update',
        'Calendar 修改',
        AcceptanceStatus.pass,
        '修改回應符合預期。',
      );
    } catch (error) {
      add(
        'calendar.update',
        'Calendar 修改',
        AcceptanceStatus.fail,
        '修改失敗：$error',
      );
    }

    try {
      await api.deleteCalendarEvent(eventId);
      artifacts.calendarEventIds.remove(eventId);
      expectActivity('calendar.delete', eventId);
      add(
        'calendar.delete',
        'Calendar 刪除',
        AcceptanceStatus.pass,
        '測試 Calendar event 已刪除。',
      );
    } catch (error) {
      add(
        'calendar.delete',
        'Calendar 刪除',
        AcceptanceStatus.fail,
        '刪除失敗；將由 cleanup 再嘗試：$error',
      );
    }
  }

  Future<void> _runGmailChecks({
    required String label,
    required Set<String> grantedServices,
    required List<AcceptanceCheck> checks,
    required AcceptanceArtifacts artifacts,
    required Map<String, Set<String>> expectedActivity,
    required void Function(
      String key,
      String displayLabel,
      AcceptanceStatus status,
      String detail,
    ) add,
    required void Function(String actionType, String entityId) expectActivity,
  }) async {
    if (!grantedServices.contains('gmail')) {
      _addGmailNotVerified(add, 'Gmail 尚未授權，未執行真實帳號測試。');
      return;
    }

    String? messageId;
    try {
      final response = await api.getGmailMetadata(limit: 1);
      final messages = (response['messages'] as List?) ?? const [];
      if (messages.isEmpty) {
        _addGmailNotVerified(
          add,
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
      add(
        'gmail.read',
        'Gmail 讀取',
        AcceptanceStatus.pass,
        '已取得一封 Gmail metadata。',
      );
    } catch (error) {
      add(
        'gmail.read',
        'Gmail 讀取',
        AcceptanceStatus.fail,
        'Gmail metadata 讀取失敗：$error',
      );
      for (final item in const [
        ('gmail.to_task', 'Gmail → Task'),
        ('gmail.to_project', 'Gmail → Project'),
        ('gmail.to_calendar', 'Gmail → Calendar'),
      ]) {
        add(
          item.$1,
          item.$2,
          AcceptanceStatus.notVerified,
          '前置 Gmail 讀取未成功。',
        );
      }
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
      expectActivity('gmail.to_task', taskId);
      add(
        'gmail.to_task',
        'Gmail → Task',
        AcceptanceStatus.pass,
        '已建立測試 Task $taskId',
      );
    } catch (error) {
      add(
        'gmail.to_task',
        'Gmail → Task',
        AcceptanceStatus.fail,
        '轉換失敗：$error',
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
      expectActivity('gmail.to_project', projectId);
      add(
        'gmail.to_project',
        'Gmail → Project',
        AcceptanceStatus.pass,
        '已建立測試 Project $projectId',
      );
    } catch (error) {
      add(
        'gmail.to_project',
        'Gmail → Project',
        AcceptanceStatus.fail,
        '轉換失敗：$error',
      );
    }

    if (!grantedServices.contains('calendar')) {
      add(
        'gmail.to_calendar',
        'Gmail → Calendar',
        AcceptanceStatus.notVerified,
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
      expectActivity('gmail.to_calendar', eventId);
      add(
        'gmail.to_calendar',
        'Gmail → Calendar',
        AcceptanceStatus.pass,
        '已建立測試 Calendar event $eventId',
      );
    } catch (error) {
      add(
        'gmail.to_calendar',
        'Gmail → Calendar',
        AcceptanceStatus.fail,
        '轉換失敗：$error',
      );
    }
  }

  void _addGmailNotVerified(
    void Function(
      String key,
      String displayLabel,
      AcceptanceStatus status,
      String detail,
    ) add,
    String detail,
  ) {
    for (final item in const [
      ('gmail.read', 'Gmail 讀取'),
      ('gmail.to_task', 'Gmail → Task'),
      ('gmail.to_project', 'Gmail → Project'),
      ('gmail.to_calendar', 'Gmail → Calendar'),
    ]) {
      add(item.$1, item.$2, AcceptanceStatus.notVerified, detail);
    }
  }

  Future<List<String>> _cleanupArtifacts(AcceptanceArtifacts artifacts) async {
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
