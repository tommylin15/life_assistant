import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_http_client.dart';

const _configuredNoteApiBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _noteApiUri(String path) {
  if (_configuredNoteApiBase.isNotEmpty) {
    return Uri.parse('$_configuredNoteApiBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

abstract class NoteApi {
  Future<List<Map<String, dynamic>>> getNotes({String query = ''});
  Future<List<Map<String, dynamic>>> getProjects();
  Future<Map<String, dynamic>> createNote(Map<String, dynamic> body);
  Future<Map<String, dynamic>> updateNote(
    String id,
    Map<String, dynamic> body,
  );
  Future<void> deleteNote(String id);
  Future<List<String>> getNoteTags(String id);
  Future<List<String>> replaceNoteTags(String id, List<String> tags);
  Future<List<Map<String, dynamic>>> getNoteLinks(String id);
  Future<void> linkNote(String id, String targetId);
  Future<void> unlinkNote(String id, String targetId);

  Future<List<Map<String, dynamic>>> getNoteDriveDocuments(String id) =>
      throw UnimplementedError();
}

class HttpNoteApi implements NoteApi {
  final _client = createApiHttpClient();

  void _check(int statusCode, String body) {
    if (statusCode >= 400) {
      throw Exception('API $statusCode: $body');
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getNotes({String query = ''}) async {
    var uri = _noteApiUri('/notes');
    final normalized = query.trim();
    if (normalized.isNotEmpty) {
      uri = uri.replace(queryParameters: {'q': normalized});
    }
    final res = await _client.get(uri);
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<List<Map<String, dynamic>>> getProjects() async {
    final res = await _client.get(_noteApiUri('/projects'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> createNote(Map<String, dynamic> body) async {
    final res = await _client.post(
      _noteApiUri('/notes'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> updateNote(
    String id,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.patch(
      _noteApiUri('/notes/$encoded'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<void> deleteNote(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.delete(
      _noteApiUri('/notes/$encoded'),
      headers: {
        'X-Life-Assistant-Confirmation': 'explicit_user:note.delete:$id',
      },
    );
    if (res.statusCode != 204) {
      _check(res.statusCode, res.body);
    }
  }

  @override
  Future<List<String>> getNoteTags(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.get(_noteApiUri('/notes/$encoded/tags'));
    _check(res.statusCode, res.body);
    final payload = jsonDecode(res.body) as Map<String, dynamic>;
    return (payload['tags'] as List? ?? const []).cast<String>();
  }

  @override
  Future<List<String>> replaceNoteTags(String id, List<String> tags) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.put(
      _noteApiUri('/notes/$encoded/tags'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'tags': tags}),
    );
    _check(res.statusCode, res.body);
    final payload = jsonDecode(res.body) as Map<String, dynamic>;
    return (payload['tags'] as List? ?? const []).cast<String>();
  }

  @override
  Future<List<Map<String, dynamic>>> getNoteLinks(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.get(_noteApiUri('/notes/$encoded/links'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<void> linkNote(String id, String targetId) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.post(
      _noteApiUri('/notes/$encoded/links'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'target_note_id': targetId}),
    );
    if (res.statusCode != 204) {
      _check(res.statusCode, res.body);
    }
  }

  @override
  Future<void> unlinkNote(String id, String targetId) async {
    final encoded = Uri.encodeComponent(id);
    final target = Uri.encodeComponent(targetId);
    final res = await _client.delete(
      _noteApiUri('/notes/$encoded/links/$target'),
    );
    if (res.statusCode != 204) {
      _check(res.statusCode, res.body);
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getNoteDriveDocuments(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.get(_noteApiUri('/drive/notes/$encoded/documents'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }
}

final noteApiProvider = Provider<NoteApi>((_) => HttpNoteApi());
