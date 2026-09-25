import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/browser_client.dart';

const _configuredBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _apiUri(String path) {
  if (_configuredBase.isNotEmpty) {
    return Uri.parse('$_configuredBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

class ApiClient {
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
      _apiUri('/tasks/$id'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<void> completeTask(String id) async {
    final res = await _client.post(_apiUri('/tasks/$id/complete'));
    _check(res.statusCode, res.body);
  }

  Future<void> deleteTask(String id) async {
    final res = await _client.delete(_apiUri('/tasks/$id'));
    if (res.statusCode != 204) _check(res.statusCode, res.body);
  }

  void _check(int statusCode, String body) {
    if (statusCode >= 400) {
      throw Exception('API $statusCode: $body');
    }
  }
}

final apiClientProvider = Provider((_) => ApiClient());
