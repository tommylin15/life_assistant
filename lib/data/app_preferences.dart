import 'dart:convert';

import 'db/app_database.dart';

class AppPreferences {
  const AppPreferences(this.db);
  final AppDatabase db;
  Future<bool> getBool(String key, {bool fallback = false}) async {
    final value = await db.preferencesDao.get(key);
    return value == null ? fallback : jsonDecode(value) == true;
  }

  Future<void> setBool(String key, bool value) =>
      db.preferencesDao.set(key, jsonEncode(value));
  Future<List<String>> getList(String key, List<String> fallback) async {
    final value = await db.preferencesDao.get(key);
    if (value == null) return fallback;
    return (jsonDecode(value) as List).cast<String>();
  }

  Future<String?> getString(String key) async {
    final value = await db.preferencesDao.get(key);
    return value == null ? null : jsonDecode(value) as String?;
  }

  Future<void> setString(String key, String value) =>
      db.preferencesDao.set(key, jsonEncode(value));
  Future<void> setList(String key, List<String> value) =>
      db.preferencesDao.set(key, jsonEncode(value));
}
