import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

abstract class TaskApi {
  Future<List<Map<String, dynamic>>> getTasks();
  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body);
  Future<Map<String, dynamic>> updateTask(String id, Map<String, dynamic> body);
  Future<void> completeTask(String id);
  Future<void> deleteTask(String id);
  Future<List<Map<String, dynamic>>> getChecklistItems(String taskId);
  Future<Map<String, dynamic>> createChecklistItem(
    String taskId,
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>> updateChecklistItem(
    String taskId,
    String itemId,
    Map<String, dynamic> body,
  );
  Future<void> deleteChecklistItem(String taskId, String itemId);
  Future<List<Map<String, dynamic>>> getProjects();
}

class ApiClientTaskApi implements TaskApi {
  ApiClientTaskApi(this._client);

  final ApiClient _client;

  @override
  Future<Map<String, dynamic>> createChecklistItem(
    String taskId,
    Map<String, dynamic> body,
  ) =>
      _client.createChecklistItem(taskId, body);

  @override
  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body) =>
      _client.createTask(body);

  @override
  Future<void> deleteChecklistItem(String taskId, String itemId) =>
      _client.deleteChecklistItem(taskId, itemId);

  @override
  Future<void> deleteTask(String id) => _client.deleteTask(id);

  @override
  Future<void> completeTask(String id) => _client.completeTask(id);

  @override
  Future<List<Map<String, dynamic>>> getChecklistItems(String taskId) =>
      _client.getChecklistItems(taskId);

  @override
  Future<List<Map<String, dynamic>>> getProjects() => _client.getProjects();

  @override
  Future<List<Map<String, dynamic>>> getTasks() => _client.getTasks();

  @override
  Future<Map<String, dynamic>> updateChecklistItem(
    String taskId,
    String itemId,
    Map<String, dynamic> body,
  ) =>
      _client.updateChecklistItem(taskId, itemId, body);

  @override
  Future<Map<String, dynamic>> updateTask(
    String id,
    Map<String, dynamic> body,
  ) =>
      _client.updateTask(id, body);
}

final taskApiProvider = Provider<TaskApi>(
  (ref) => ApiClientTaskApi(ref.read(apiClientProvider)),
);
