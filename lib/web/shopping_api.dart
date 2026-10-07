import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_http_client.dart';

const _configuredShoppingApiBase =
    String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _shoppingApiUri(String path) {
  if (_configuredShoppingApiBase.isNotEmpty) {
    return Uri.parse('$_configuredShoppingApiBase$path');
  }
  return Uri.base.resolve('/api/v1$path');
}

abstract class ShoppingApi {
  Future<List<Map<String, dynamic>>> getShoppingLists();
  Future<Map<String, dynamic>> createShoppingList(Map<String, dynamic> body);
  Future<Map<String, dynamic>> createShoppingItem(
    String listId,
    Map<String, dynamic> body,
  );
  Future<Map<String, dynamic>> updateShoppingItem(
    String itemId,
    Map<String, dynamic> body,
  );
}

class HttpShoppingApi implements ShoppingApi {
  final _client = createApiHttpClient();

  void _check(int statusCode, String body) {
    if (statusCode >= 400) {
      throw Exception('API $statusCode: $body');
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getShoppingLists() async {
    final res = await _client.get(_shoppingApiUri('/shopping-lists'));
    _check(res.statusCode, res.body);
    return (jsonDecode(res.body) as List).cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> createShoppingList(
    Map<String, dynamic> body,
  ) async {
    final res = await _client.post(
      _shoppingApiUri('/shopping-lists'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> createShoppingItem(
    String listId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(listId);
    final res = await _client.post(
      _shoppingApiUri('/shopping-lists/$encoded/items'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>> updateShoppingItem(
    String itemId,
    Map<String, dynamic> body,
  ) async {
    final encoded = Uri.encodeComponent(itemId);
    final res = await _client.patch(
      _shoppingApiUri('/shopping-items/$encoded'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(res.statusCode, res.body);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}

final shoppingApiProvider = Provider<ShoppingApi>((_) => HttpShoppingApi());
