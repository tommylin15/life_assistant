import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_http_client.dart';

const _configuredFreeEventsBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _freeEventsApiUri(String path) {
  if (_configuredFreeEventsBase.isNotEmpty) {
    return Uri.parse('$_configuredFreeEventsBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

abstract class FreeEventsApi {
  Future<List<Map<String, dynamic>>> listVerified({int limit = 20});
}

class HttpFreeEventsApi implements FreeEventsApi {
  final _client = createApiHttpClient();

  @override
  Future<List<Map<String, dynamic>>> listVerified({int limit = 20}) async {
    final uri = _freeEventsApiUri('/free-events').replace(
      queryParameters: {'limit': '$limit'},
    );
    final res = await _client.get(uri);
    if (res.statusCode >= 400) {
      throw Exception('API ${res.statusCode}: ${res.body}');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    if (body['policy'] != 'verified_public_catalog_only') {
      throw const FormatException('Unknown free-event verification policy');
    }
    return (body['items'] as List<dynamic>).cast<Map<String, dynamic>>();
  }
}

final freeEventsApiProvider = Provider<FreeEventsApi>((_) => HttpFreeEventsApi());
