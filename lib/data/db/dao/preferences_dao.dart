import 'package:drift/drift.dart';

import '../app_database.dart';

part 'preferences_dao.g.dart';

@DriftAccessor(tables: [Preferences, BridgeState])
class PreferencesDao extends DatabaseAccessor<AppDatabase>
    with _$PreferencesDaoMixin {
  PreferencesDao(super.db);

  Future<String?> get(String key) async {
    final row = await (select(
      preferences,
    )..where((t) => t.key.equals(key))).getSingleOrNull();
    return row?.valueJson;
  }

  Future<void> set(String key, String valueJson) => into(preferences)
      .insertOnConflictUpdate(
        PreferencesCompanion(key: Value(key), valueJson: Value(valueJson)),
      );

  Future<String?> getBridgeState(String key) async {
    final row = await (select(
      bridgeState,
    )..where((t) => t.key.equals(key))).getSingleOrNull();
    return row?.valueJson;
  }

  Future<void> setBridgeState(String key, String valueJson) => into(bridgeState)
      .insertOnConflictUpdate(
        BridgeStateCompanion(key: Value(key), valueJson: Value(valueJson)),
      );
}
