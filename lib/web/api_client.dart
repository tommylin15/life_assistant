import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/browser_client.dart';

import 'acceptance_runner.dart';

const _configuredBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _apiUri(String path) {
  if (_configuredBase.isNotEmpty) {
    return Uri.parse('$_configuredBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

class ApiClient implements AcceptanceApi {
  final BrowserClient _client = BrowserClient()..withCredentials = true;

  Future<List<Map<String, dynamic>>> getTasks() async {
    final res = await _client.get(_apiUri('/tasks'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast();
  }

  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body) async {
    final res = await _client.post(
      _apiUri('/tasks'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateTask(
    String id,
    Map<String, dynamic> body,
  ) async {
    final res = await _client.patch(
      _apiUri('/tasks/${Uri.encodeComponent(id)}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<void> completeTask(String id) async {
    final res = await _client.post(
      _apiUri('/tasks/${Uri.encodeComponent(id)}/complete'),
    );
    _check(res.statusCode, res.body);
  }

  @override
  Future<void> deleteTask(String id) async {
    final res = await _client.delete(
      _apiUri('/tasks/${Uri.encodeComponent(id)}'),
    );
    if (res.statusCode != 204) _check(res.statusCode, res.body);
  }

  Future<List<Map<String, dynamic>>> getProjects() async {
    final res = await _client.get(_apiUri('/projects'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast();
  }

  @override
  Future<Map<String, dynamic>> createProject(Map<String, dynamic> body) async {
    final res = await _client.post(
      _apiUri('/projects'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> getProject(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.get(_apiUri('/projects/$encoded'));
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> updateProject(
    String id,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.patch(
      _apiUri('/projects/$encoded'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<void> deleteProject(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.delete(_apiUri('/projects/$encoded'));
    if (res.statusCode != 204) _check(res.statusCode, res.body);
  }

  @override
  Future<Map<String, dynamic>> getGoogleIntegrationStatus() async {
    final res = await _client.get(_apiUri('/integrations/google/status'));
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getGoogleCapabilities() async {
    final res = await _client.get(_apiUri('/integrations/google/capabilities'));
    _check(res.statusCode, res.body);
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    return (body['capabilities'] as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> getGmailMetadata({int limit = 1}) async {
    final uri = _apiUri('/integrations/google/gmail/messages').replace(
      queryParameters: {'limit': '$limit'},
    );
    final res = await _client.get(uri);
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> gmailMessageToTask(
    String messageId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(messageId);
    final res = await _client.post(
      _apiUri('/integrations/google/gmail/messages/$encoded/task'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> gmailMessageToProject(
    String messageId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(messageId);
    final res = await _client.post(
      _apiUri('/integrations/google/gmail/messages/$encoded/project'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> gmailMessageToCalendar(
    String messageId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(messageId);
    final res = await _client.post(
      _apiUri('/integrations/google/gmail/messages/$encoded/calendar'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getCalendarEvents({
    required DateTime timeMin,
    required DateTime timeMax,
    int limit = 1,
  }) async {
    final uri = _apiUri('/integrations/google/calendar/events').replace(
      queryParameters: {
        'time_min': timeMin.toUtc().toIso8601String(),
        'time_max': timeMax.toUtc().toIso8601String(),
        'limit': '$limit',
      },
    );
    final res = await _client.get(uri);
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> createCalendarEvent(
    Map<String, dynamic> body,
  ) async {
    final res = await _client.post(
      _apiUri('/integrations/google/calendar/events'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> updateCalendarEvent(
    String eventId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(eventId);
    final res = await _client.patch(
      _apiUri('/integrations/google/calendar/events/$encoded'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<void> deleteCalendarEvent(String eventId) async {
    final encoded = Uri.encodeComponent(eventId);
    final res = await _client.delete(
      _apiUri('/integrations/google/calendar/events/$encoded'),
    );
    if (res.statusCode != 204) _check(res.statusCode, res.body);
  }

  @override
  Future<List<Map<String, dynamic>>> getActivity({int limit = 100}) async {
    final uri = _apiUri('/activity').replace(
      queryParameters: {'limit': '$limit'},
    );
    final res = await _client.get(uri);
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> ensureDriveBridge() async {
    final res = await _client.post(_apiUri('/integrations/google/drive/bridge'));
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  String googleAuthorizationUrl(String services) => _apiUri(
        '/integrations/google/authorize',
      ).replace(queryParameters: {'services': services}).toString();

  void _check(int statusCode, String body) {
    if (statusCode >= 400) {
      throw Exception('API $statusCode: $body');
    }
  }
}

final apiClientProvider = Provider((_) => ApiClient());
