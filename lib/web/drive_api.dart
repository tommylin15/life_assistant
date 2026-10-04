import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_http_client.dart';

const _configuredDriveApiBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _driveApiUri(String path) {
  if (_configuredDriveApiBase.isNotEmpty) {
    return Uri.parse('$_configuredDriveApiBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

abstract class DriveApi {
  Future<List<Map<String, dynamic>>> getDocuments();
  Future<Map<String, dynamic>> getEnrichmentSettings();
  Future<Map<String, dynamic>> updateEnrichmentSettings(
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>?> getEnrichment(String documentId);
  Future<Map<String, dynamic>> runEnrichment(
    String documentId, {
    bool force = false,
  });
  Future<Map<String, dynamic>> decideNoteSuggestion(
    String suggestionId,
    String decision,
  );
}

abstract class DrivePickerApi {
  Future<Map<String, dynamic>> getPickerConfig();
  Future<List<Map<String, dynamic>>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  });
}

abstract class DriveNoteApi {
  Future<Map<String, dynamic>> importDocumentToNote(
    String documentId,
    Map<String, dynamic> body,
  );
  Future<List<Map<String, dynamic>>> getDocumentNotes(String documentId);
  Future<List<Map<String, dynamic>>> getNoteDocuments(String noteId);
  Future<Map<String, dynamic>> linkDocumentNote(
    String documentId,
    String noteId,
  );
  Future<void> unlinkDocumentNote(String documentId, String noteId);
}

class HttpDriveApi implements DriveApi, DrivePickerApi, DriveNoteApi {
  final _client = createApiHttpClient();

  void _check(int statusCode, String body) {
    if (statusCode >= 400) {
      throw Exception('API $statusCode: $body');
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getDocuments() async {
    final res = await _client.get(_driveApiUri('/drive/documents'));
    _check(res.statusCode, res.body);
    final payload = jsonDecode(res.body) as Map<String, dynamic>;
    return (payload['documents'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> getPickerConfig() async {
    final res = await _client.get(_driveApiUri('/drive/picker-config'));
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<List<Map<String, dynamic>>> registerDocuments(
    List<String> googleFileIds, {
    String? workspaceId,
  }) async {
    final body = <String, dynamic>{'google_file_ids': googleFileIds};
    if (workspaceId != null && workspaceId.trim().isNotEmpty) {
      body['workspace_id'] = workspaceId.trim();
    }
    final res = await _client.post(
      _driveApiUri('/drive/documents/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    final payload = jsonDecode(res.body) as Map<String, dynamic>;
    return (payload['documents'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> importDocumentToNote(
    String documentId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(documentId);
    final res = await _client.post(
      _driveApiUri('/drive/documents/$encoded/note-import'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<List<Map<String, dynamic>>> getDocumentNotes(String documentId) async {
    final encoded = Uri.encodeComponent(documentId);
    final res = await _client.get(
      _driveApiUri('/drive/documents/$encoded/notes'),
    );
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<List<Map<String, dynamic>>> getNoteDocuments(String noteId) async {
    final encoded = Uri.encodeComponent(noteId);
    final res = await _client.get(
      _driveApiUri('/drive/notes/$encoded/documents'),
    );
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> linkDocumentNote(
    String documentId,
    String noteId,
  ) async {
    final document = Uri.encodeComponent(documentId);
    final note = Uri.encodeComponent(noteId);
    final res = await _client.post(
      _driveApiUri('/drive/documents/$document/notes/$note'),
      headers: {'Content-Type': 'application/json'},
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<void> unlinkDocumentNote(String documentId, String noteId) async {
    final document = Uri.encodeComponent(documentId);
    final note = Uri.encodeComponent(noteId);
    final res = await _client.delete(
      _driveApiUri('/drive/documents/$document/notes/$note'),
      headers: {
        'X-Life-Assistant-Confirmation':
            'explicit_user:drive.document.note.detach:$documentId:$noteId',
      },
    );
    if (res.statusCode != 204) {
      _check(res.statusCode, res.body);
    }
  }

  @override
  Future<Map<String, dynamic>> getEnrichmentSettings() async {
    final res = await _client.get(_driveApiUri('/drive/enrichment/settings'));
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> updateEnrichmentSettings(
    Map<String, dynamic> body,
  ) async {
    final res = await _client.put(
      _driveApiUri('/drive/enrichment/settings'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>?> getEnrichment(String documentId) async {
    final encoded = Uri.encodeComponent(documentId);
    final res = await _client.get(
      _driveApiUri('/drive/documents/$encoded/enrichment'),
    );
    _check(res.statusCode, res.body);
    final payload = jsonDecode(res.body);
    if (payload == null) return null;
    return payload as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> runEnrichment(
    String documentId, {
    bool force = false,
  }) async {
    final encoded = Uri.encodeComponent(documentId);
    final res = await _client.post(
      _driveApiUri('/drive/documents/$encoded/enrichment'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'force': force}),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> decideNoteSuggestion(
    String suggestionId,
    String decision,
  ) async {
    final encoded = Uri.encodeComponent(suggestionId);
    final res = await _client.post(
      _driveApiUri('/drive/note-suggestions/$encoded/decision'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'decision': decision}),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}

final _httpDriveApiProvider = Provider<HttpDriveApi>((_) => HttpDriveApi());

final driveApiProvider = Provider<DriveApi>(
  (ref) => ref.watch(_httpDriveApiProvider),
);

final drivePickerApiProvider = Provider<DrivePickerApi>(
  (ref) => ref.watch(_httpDriveApiProvider),
);

final driveNoteApiProvider = Provider<DriveNoteApi>(
  (ref) => ref.watch(_httpDriveApiProvider),
);
