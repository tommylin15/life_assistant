import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'api_http_client.dart';

const _configuredAuthBase =
    String.fromEnvironment('AUTH_BASE_URL', defaultValue: '');

Uri _authUri(String path) {
  if (_configuredAuthBase.isNotEmpty) {
    return Uri.parse('$_configuredAuthBase$path');
  }
  return Uri.base.resolve(path);
}

class AuthNotifier extends Notifier<AsyncValue<Map<String, String>?>> {
  // Browser uses credentialed BrowserClient; Flutter VM tests use http.Client.
  final http.Client _client = createApiHttpClient();

  @override
  AsyncValue<Map<String, String>?> build() {
    _init();
    return const AsyncValue.loading();
  }

  Future<void> _init() async {
    try {
      final response = await _client.get(_authUri('/auth/me'));
      if (response.statusCode == 401 || response.statusCode == 403) {
        state = const AsyncValue.data(null);
        return;
      }
      if (response.statusCode >= 400) {
        throw Exception('Auth ${response.statusCode}: ${response.body}');
      }

      final body = jsonDecode(response.body) as Map<String, dynamic>;
      state = AsyncValue.data({
        'email': body['email']?.toString() ?? '',
        'name': body['name']?.toString() ?? '',
      });
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    await _init();
  }

  Future<void> logout() async {
    // Keep the authenticated state if the server fails to clear its cookie.
    final response = await _client.post(_authUri('/auth/logout'));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw StateError('Logout failed (' + response.statusCode.toString() + ')');
    }
    state = const AsyncValue.data(null);
  }
}

final authProvider =
    NotifierProvider<AuthNotifier, AsyncValue<Map<String, String>?>>(
  AuthNotifier.new,
);
