import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

const _base = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000/api/v1');

class ApiClient {
  final _client = http.Client();

  Future<List<Map<String, dynamic>>> getTasks() async {
    final res = await _client.get(Uri.parse('$_base/tasks'));
    _check(res);
    return (jsonDecode(res.body) as List).cast();
  }

  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body) async {
    final res = await _client.post(
      Uri.parse('$_base/tasks'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateTask(String id, Map<String, dynamic> body) async {
    final res = await _client.patch(
      Uri.parse('$_base/tasks/$id'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<void> completeTask(String id) async {
    final res = await _client.post(Uri.parse('$_base/tasks/$id/complete'));
    _check(res);
  }

  Future<void> deleteTask(String id) async {
    final res = await _client.delete(Uri.parse('$_base/tasks/$id'));
    if (res.statusCode != 204) _check(res);
  }

  void _check(http.Response res) {
    if (res.statusCode >= 400) throw Exception('API ${res.statusCode}: ${res.body}');
  }
}

final apiClientProvider = Provider((_) => ApiClient());
