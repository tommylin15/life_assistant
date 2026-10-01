import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

abstract class ProjectApi {
  Future<List<Map<String, dynamic>>> getProjects();
  Future<List<Map<String, dynamic>>> getTasks();
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body);
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  );
  Future<void> deleteProject(String id);
}

enum ProjectLinkKind { tasks, notes, shoppingLists, driveDocuments }

class ProjectDeleteBlockedException implements Exception {
  const ProjectDeleteBlockedException(this.kind);

  final ProjectLinkKind kind;

  String get userMessage {
    switch (kind) {
      case ProjectLinkKind.tasks:
        return '這個專案仍有關聯待辦，請先移除待辦的專案關聯後再刪除。';
      case ProjectLinkKind.notes:
        return '這個專案仍有關聯筆記，請先移除筆記的專案關聯後再刪除。';
      case ProjectLinkKind.shoppingLists:
        return '這個專案仍有關聯購物清單，請先移除購物清單的專案關聯後再刪除。';
      case ProjectLinkKind.driveDocuments:
        return '這個專案仍有關聯 Drive 文件，請先解除 Drive 文件的專案關聯後再刪除。';
    }
  }

  @override
  String toString() => userMessage;
}

class ApiClientProjectApi implements ProjectApi {
  ApiClientProjectApi(this._client);

  final ApiClient _client;

  @override
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body) =>
      _client.createProject(body);

  @override
  Future<void> deleteProject(String id) async {
    try {
      await _client.deleteProject(id);
    } catch (error) {
      final message = error.toString();
      if (message.contains('Project has linked tasks')) {
        throw const ProjectDeleteBlockedException(ProjectLinkKind.tasks);
      }
      if (message.contains('Project has linked notes')) {
        throw const ProjectDeleteBlockedException(ProjectLinkKind.notes);
      }
      if (message.contains('Project has linked shopping lists')) {
        throw const ProjectDeleteBlockedException(ProjectLinkKind.shoppingLists);
      }
      if (message.contains('Project has linked Drive documents')) {
        throw const ProjectDeleteBlockedException(ProjectLinkKind.driveDocuments);
      }
      rethrow;
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getProjects() => _client.getProjects();

  @override
  Future<List<Map<String, dynamic>>> getTasks() => _client.getTasks();

  @override
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  ) =>
      _client.updateProject(id, body);
}

final projectApiProvider = Provider<ProjectApi>(
  (ref) => ApiClientProjectApi(ref.read(apiClientProvider)),
);
