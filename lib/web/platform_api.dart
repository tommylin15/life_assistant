import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_http_client.dart';

const _base = String.fromEnvironment('API_BASE_URL', defaultValue: '');

Uri _uri(String path) =>
    _base.isNotEmpty ? Uri.parse('$_base$path') : Uri.base.resolve('/api/v1$path');

class PlatformApi {
  final _client = createApiHttpClient();

  Future<Map<String, dynamic>> get(String path) async {
    final response = await _client.get(_uri(path));
    if (response.statusCode >= 400) throw StateError('API ${response.statusCode}');
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> put(String path, Map<String, dynamic> body) async {
    final response = await _client.put(
      _uri(path),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    if (response.statusCode >= 400) throw StateError('API ${response.statusCode}');
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}

final platformApiProvider = Provider<PlatformApi>((_) => PlatformApi());
final effectiveFeaturesProvider = FutureProvider<Map<String, bool>>((ref) async {
  final json = await ref.read(platformApiProvider).get('/ui/features');
  return {for (final feature in (json['features'] as List))
    feature['key'] as String: feature['available'] as bool};
});

final uiPreferencesProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(platformApiProvider).get('/me/ui-preferences');
});

class FeatureAccess extends ConsumerWidget {
  const FeatureAccess({super.key, required this.feature, required this.child});
  final String feature;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final features = ref.watch(effectiveFeaturesProvider);
    return features.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(child: Text('無法確認功能權限，請稍後重試')),
      data: (flags) => flags[feature] == true
          ? child
          : const Center(child: Text('此功能目前未開放')),
    );
  }
}

final ownerAuthorizedProvider = FutureProvider<bool>((ref) async {
  try { await ref.read(platformApiProvider).get('/admin/feature-rollouts'); return true; }
  catch (_) { return false; }
});

class AdminAccess extends ConsumerWidget {
  const AdminAccess({super.key, required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
    ref.watch(ownerAuthorizedProvider).when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(child: Text('無法驗證管理員權限')),
      data: (allowed) => allowed ? child
          : const Center(child: Text('僅管理員可使用此功能')),
    );
}
