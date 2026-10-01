import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_http_client.dart';

const _configuredBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _driveUri(String path, {Map<String, String>? queryParameters}) {
  final base = _configuredBase.isNotEmpty
      ? Uri.parse('$_configuredBase/api/v1$path')
      : Uri.base.resolve('/api/v1$path');
  return queryParameters == null
      ? base
      : base.replace(queryParameters: queryParameters);
}

void _check(int statusCode, String body) {
  if (statusCode >= 200 && statusCode < 300) return;
  var message = body;
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];
      final error = decoded['error'];
      if (detail is String) {
        message = detail;
      } else if (error is Map<String, dynamic> && error['message'] is String) {
        message = error['message'] as String;
      }
    }
  } catch (_) {
    // Keep the raw body for transport errors that are not JSON.
  }
  throw Exception(message.isEmpty ? 'Drive request failed ($statusCode)' : message);
}

class PickerConfig {
  const PickerConfig({
    required this.clientId,
    required this.developerKey,
    required this.appId,
    required this.scope,
  });

  final String clientId;
  final String developerKey;
  final String appId;
  final String scope;

  factory PickerConfig.fromJson(Map<String, dynamic> json) => PickerConfig(
        clientId: json['client_id'] as String? ?? '',
        developerKey: json['developer_key'] as String? ?? '',
        appId: json['app_id'] as String? ?? '',
        scope: json['scope'] as String? ?? '',
      );
}

class DriveWorkspace {
  const DriveWorkspace({
    required this.id,
    required this.googleFolderId,
    required this.name,
    required this.webViewLink,
    required this.isEnabled,
    required this.isDefault,
  });

  final String id;
  final String googleFolderId;
  final String name;
  final String? webViewLink;
  final bool isEnabled;
  final bool isDefault;

  factory DriveWorkspace.fromJson(Map<String, dynamic> json) => DriveWorkspace(
        id: json['id'] as String,
        googleFolderId: json['google_folder_id'] as String,
        name: json['name'] as String? ?? 'Google Drive 工作區',
        webViewLink: json['web_view_link'] as String?,
        isEnabled: json['is_enabled'] as bool? ?? true,
        isDefault: json['is_default'] as bool? ?? false,
      );

  DriveWorkspace copyWith({
    String? name,
    bool? isEnabled,
    bool? isDefault,
  }) =>
      DriveWorkspace(
        id: id,
        googleFolderId: googleFolderId,
        name: name ?? this.name,
        webViewLink: webViewLink,
        isEnabled: isEnabled ?? this.isEnabled,
        isDefault: isDefault ?? this.isDefault,
      );
}

class DriveDocument {
  const DriveDocument({
    required this.id,
    required this.googleFileId,
    required this.name,
    required this.mimeType,
    required this.webViewLink,
    this.providerModifiedAt,
    this.lastMetadataRefreshAt,
    this.tags = const [],
  });

  final String id;
  final String googleFileId;
  final String name;
  final String mimeType;
  final String? webViewLink;
  final DateTime? providerModifiedAt;
  final DateTime? lastMetadataRefreshAt;
  final List<String> tags;

  factory DriveDocument.fromJson(Map<String, dynamic> json) => DriveDocument(
        id: json['id'] as String,
        googleFileId: json['google_file_id'] as String,
        name: json['name'] as String? ?? 'Google Drive 文件',
        mimeType: json['mime_type'] as String? ?? 'application/octet-stream',
        webViewLink: json['web_view_link'] as String?,
        providerModifiedAt: _date(json['provider_modified_at']),
        lastMetadataRefreshAt: _date(json['last_metadata_refresh_at']),
        tags: (json['tags'] as List?)?.whereType<String>().toList() ?? const [],
      );
}

class DriveAiSettings {
  const DriveAiSettings({
    this.autoTags = true,
    this.suggestRelatedNotes = true,
    this.allowContentAnalysis = false,
    this.maxRelatedNotes = 5,
  });

  final bool autoTags;
  final bool suggestRelatedNotes;
  final bool allowContentAnalysis;
  final int maxRelatedNotes;

  factory DriveAiSettings.fromJson(Map<String, dynamic> json) => DriveAiSettings(
        autoTags: json['auto_tags'] as bool? ?? true,
        suggestRelatedNotes: json['suggest_related_notes'] as bool? ?? true,
        allowContentAnalysis: json['allow_content_analysis'] as bool? ?? false,
        maxRelatedNotes: json['max_related_notes'] as int? ?? 5,
      );

  DriveAiSettings copyWith({
    bool? autoTags,
    bool? suggestRelatedNotes,
    bool? allowContentAnalysis,
    int? maxRelatedNotes,
  }) =>
      DriveAiSettings(
        autoTags: autoTags ?? this.autoTags,
        suggestRelatedNotes: suggestRelatedNotes ?? this.suggestRelatedNotes,
        allowContentAnalysis: allowContentAnalysis ?? this.allowContentAnalysis,
        maxRelatedNotes: maxRelatedNotes ?? this.maxRelatedNotes,
      );
}

DateTime? _date(dynamic raw) {
  if (raw is! String || raw.isEmpty) return null;
  return DateTime.tryParse(raw);
}

abstract class DriveApi {
  Future<PickerConfig> getPickerConfig();
  Future<List<DriveWorkspace>> getWorkspaces();
  Future<DriveWorkspace> createWorkspace(String googleFolderId);
  Future<DriveWorkspace> updateWorkspace(String id, Map<String, dynamic> body);
  Future<void> deleteWorkspace(String id);
  Future<DriveAiSettings> getAiSettings();
  Future<DriveAiSettings> updateAiSettings(Map<String, dynamic> body);
  Future<List<DriveDocument>> getDocuments({String? q, String? workspaceId});
  Future<List<DriveDocument>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  });
  Future<DriveDocument> refreshDocument(String id);

  Future<List<Map<String, dynamic>>> getProjectDocuments({String? projectId}) =>
      throw UnimplementedError();

  Future<void> attachDocumentToProjects(
    String documentId,
    List<String> projectIds,
  ) =>
      throw UnimplementedError();

  Future<void> detachDocumentFromProject(
    String documentId,
    String projectId,
  ) =>
      throw UnimplementedError();

  Future<Map<String, dynamic>> importDocumentToNote(
    String documentId,
    Map<String, dynamic> body,
  ) =>
      throw UnimplementedError();

  Future<List<Map<String, dynamic>>> getDocumentNotes(String documentId) =>
      throw UnimplementedError();

  Future<void> linkDocumentToNote(String documentId, String noteId) =>
      throw UnimplementedError();

  Future<void> unlinkDocumentFromNote(String documentId, String noteId) =>
      throw UnimplementedError();

  Future<List<Map<String, dynamic>>> getNoteDocuments(String noteId) =>
      throw UnimplementedError();
}

class HttpDriveApi implements DriveApi {
  HttpDriveApi();

  final _client = createApiHttpClient();

  @override
  Future<PickerConfig> getPickerConfig() async {
    final response = await _client.get(_driveUri('/drive/picker-config'));
    _check(response.statusCode, response.body);
    return PickerConfig.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  @override
  Future<List<DriveWorkspace>> getWorkspaces() async {
    final response = await _client.get(_driveUri('/drive/workspaces'));
    _check(response.statusCode, response.body);
    return (jsonDecode(response.body) as List)
        .cast<Map<String, dynamic>>()
        .map(DriveWorkspace.fromJson)
        .toList();
  }

  @override
  Future<DriveWorkspace> createWorkspace(String googleFolderId) async {
    final response = await _client.post(
      _driveUri('/drive/workspaces'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'google_folder_id': googleFolderId}),
    );
    _check(response.statusCode, response.body);
    return DriveWorkspace.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  @override
  Future<DriveWorkspace> updateWorkspace(
    String id,
    Map<String, dynamic> body,
  ) async {
    final response = await _client.patch(
      _driveUri('/drive/workspaces/${Uri.encodeComponent(id)}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(response.statusCode, response.body);
    return DriveWorkspace.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  @override
  Future<void> deleteWorkspace(String id) async {
    final response = await _client.delete(
      _driveUri('/drive/workspaces/${Uri.encodeComponent(id)}'),
    );
    if (response.statusCode != 204) _check(response.statusCode, response.body);
  }

  @override
  Future<DriveAiSettings> getAiSettings() async {
    final response = await _client.get(_driveUri('/drive/ai-settings'));
    _check(response.statusCode, response.body);
    return DriveAiSettings.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  @override
  Future<DriveAiSettings> updateAiSettings(Map<String, dynamic> body) async {
    final response = await _client.put(
      _driveUri('/drive/ai-settings'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(response.statusCode, response.body);
    return DriveAiSettings.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  @override
  Future<List<DriveDocument>> getDocuments({
    String? q,
    String? workspaceId,
  }) async {
    final params = <String, String>{};
    if (q != null && q.trim().isNotEmpty) params['q'] = q.trim();
    if (workspaceId != null && workspaceId.isNotEmpty) {
      params['workspace_id'] = workspaceId;
    }
    final response = await _client.get(
      _driveUri('/drive/documents', queryParameters: params.isEmpty ? null : params),
    );
    _check(response.statusCode, response.body);
    return (jsonDecode(response.body) as List)
        .cast<Map<String, dynamic>>()
        .map(DriveDocument.fromJson)
        .toList();
  }

  @override
  Future<List<DriveDocument>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  }) async {
    final body = <String, dynamic>{'google_file_ids': googleFileIds};
    if (workspaceId != null) body['workspace_id'] = workspaceId;
    final response = await _client.post(
      _driveUri('/drive/documents/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(response.statusCode, response.body);
    return (jsonDecode(response.body) as List)
        .cast<Map<String, dynamic>>()
        .map(DriveDocument.fromJson)
        .toList();
  }

  @override
  Future<DriveDocument> refreshDocument(String id) async {
    final response = await _client.post(
      _driveUri('/drive/documents/${Uri.encodeComponent(id)}/refresh'),
    );
    _check(response.statusCode, response.body);
    return DriveDocument.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  @override
  Future<List<Map<String, dynamic>>> getProjectDocuments({String? projectId}) async {
    final params = <String, String>{};
    if (projectId != null && projectId.isNotEmpty) params['project_id'] = projectId;
    final response = await _client.get(
      _driveUri(
        '/drive/project-documents',
        queryParameters: params.isEmpty ? null : params,
      ),
    );
    _check(response.statusCode, response.body);
    return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<void> attachDocumentToProjects(
    String documentId,
    List<String> projectIds,
  ) async {
    final response = await _client.post(
      _driveUri('/drive/documents/${Uri.encodeComponent(documentId)}/projects'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'project_ids': projectIds}),
    );
    _check(response.statusCode, response.body);
  }

  @override
  Future<void> detachDocumentFromProject(
    String documentId,
    String projectId,
  ) async {
    final response = await _client.delete(
      _driveUri(
        '/drive/documents/${Uri.encodeComponent(documentId)}/projects/${Uri.encodeComponent(projectId)}',
      ),
    );
    if (response.statusCode != 204) _check(response.statusCode, response.body);
  }

  @override
  Future<Map<String, dynamic>> importDocumentToNote(
    String documentId,
    Map<String, dynamic> body,
  ) async {
    final response = await _client.post(
      _driveUri('/drive/documents/${Uri.encodeComponent(documentId)}/note-import'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(response.statusCode, response.body);
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  @override
  Future<List<Map<String, dynamic>>> getDocumentNotes(String documentId) async {
    final response = await _client.get(
      _driveUri('/drive/documents/${Uri.encodeComponent(documentId)}/notes'),
    );
    _check(response.statusCode, response.body);
    return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<void> linkDocumentToNote(String documentId, String noteId) async {
    final response = await _client.post(
      _driveUri(
        '/drive/documents/${Uri.encodeComponent(documentId)}/notes/${Uri.encodeComponent(noteId)}',
      ),
    );
    _check(response.statusCode, response.body);
  }

  @override
  Future<void> unlinkDocumentFromNote(String documentId, String noteId) async {
    final response = await _client.delete(
      _driveUri(
        '/drive/documents/${Uri.encodeComponent(documentId)}/notes/${Uri.encodeComponent(noteId)}',
      ),
    );
    if (response.statusCode != 204) _check(response.statusCode, response.body);
  }

  @override
  Future<List<Map<String, dynamic>>> getNoteDocuments(String noteId) async {
    final response = await _client.get(
      _driveUri('/drive/notes/${Uri.encodeComponent(noteId)}/documents'),
    );
    _check(response.statusCode, response.body);
    return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
  }
}

final driveApiProvider = Provider<DriveApi>((ref) => HttpDriveApi());
