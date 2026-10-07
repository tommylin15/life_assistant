import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_http_client.dart';

const _configuredHabitApiBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _habitApiUri(String path) {
  if (_configuredHabitApiBase.isNotEmpty) {
    return Uri.parse('$_configuredHabitApiBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

abstract class HabitApi {
  Future<List<Map<String, dynamic>>> getHabits();
  Future<Map<String, dynamic>> createHabit(Map<String, dynamic> body);
  Future<Map<String, dynamic>> updateHabit(
    String id,
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>> completeHabit(String id);
  Future<List<Map<String, dynamic>>> getHabitCompletions(String id);
}

class HttpHabitApi implements HabitApi {
  final _client = createApiHttpClient();

  void _check(int statusCode, String body) {
    if (statusCode >= 400) {
      throw Exception('API $statusCode: $body');
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getHabits() async {
    final res = await _client.get(_habitApiUri('/habits'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> createHabit(
    Map<String, dynamic> body,
  ) async {
    final res = await _client.post(
      _habitApiUri('/habits'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> updateHabit(
    String id,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.patch(
      _habitApiUri('/habits/$encoded'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> completeHabit(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.post(_habitApiUri('/habits/$encoded/complete'));
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<List<Map<String, dynamic>>> getHabitCompletions(String id) async {
    final encoded = Uri.encodeComponent(id);
    final res = await _client.get(
      _habitApiUri('/habits/$encoded/completions'),
    );
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }
}

final habitApiProvider = Provider<HabitApi>((_) => HttpHabitApi());
