import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kAccessToken = 'access_token';
const _kUserEmail = 'user_email';
const _kUserName = 'user_name';

class AuthNotifier extends Notifier<AsyncValue<Map<String, String>?>> {
  final _storage = const FlutterSecureStorage();

  @override
  AsyncValue<Map<String, String>?> build() {
    _init();
    return const AsyncValue.loading();
  }

  Future<void> _init() async {
    final token = await _storage.read(key: _kAccessToken);
    if (token == null) {
      state = const AsyncValue.data(null);
      return;
    }
    final email = await _storage.read(key: _kUserEmail) ?? '';
    final name = await _storage.read(key: _kUserName) ?? '';
    state = AsyncValue.data({'token': token, 'email': email, 'name': name});
  }

  Future<void> saveSession({
    required String token,
    required String email,
    required String name,
  }) async {
    await _storage.write(key: _kAccessToken, value: token);
    await _storage.write(key: _kUserEmail, value: email);
    await _storage.write(key: _kUserName, value: name);
    state = AsyncValue.data({'token': token, 'email': email, 'name': name});
  }

  Future<void> logout() async {
    await _storage.deleteAll();
    state = const AsyncValue.data(null);
  }
}

final authProvider = NotifierProvider<AuthNotifier, AsyncValue<Map<String, String>?>>(
  AuthNotifier.new,
);
