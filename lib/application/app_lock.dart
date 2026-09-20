import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

class AppLockService {
  AppLockService({FlutterSecureStorage? storage, LocalAuthentication? auth})
    : _storage = storage ?? const FlutterSecureStorage(),
      _auth = auth ?? LocalAuthentication();

  static const _pinKey = 'app_lock_pin_v1';
  final FlutterSecureStorage _storage;
  final LocalAuthentication _auth;

  Future<bool> get hasPin async => await _storage.read(key: _pinKey) != null;

  Future<void> setPin(String pin) async {
    if (!RegExp(r'^\d{4,8}$').hasMatch(pin))
      throw const FormatException('PIN 必須為 4–8 位數字');
    final salt = List<int>.generate(16, (_) => Random.secure().nextInt(256));
    final hash = sha256.convert([...salt, ...utf8.encode(pin)]).toString();
    await _storage.write(key: _pinKey, value: '${base64Encode(salt)}:$hash');
  }

  Future<bool> verifyPin(String pin) async {
    final stored = await _storage.read(key: _pinKey);
    if (stored == null) return false;
    final parts = stored.split(':');
    if (parts.length != 2) return false;
    return sha256.convert([
          ...base64Decode(parts[0]),
          ...utf8.encode(pin),
        ]).toString() ==
        parts[1];
  }

  Future<bool> authenticateBiometric() async {
    if (!await _auth.isDeviceSupported()) return false;
    return _auth.authenticate(
      localizedReason: '解鎖生活助理',
      biometricOnly: true,
      persistAcrossBackgrounding: true,
    );
  }

  Future<void> disable() => _storage.delete(key: _pinKey);
}
