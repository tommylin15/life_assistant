/// 依序執行 schema migration。
/// 每次新增 schema 版本時，在此加入對應的 case。
Future<void> runMigrations(
  int from,
  int to,
  Future<void> Function(int version) migrate,
) async {
  for (var version = from + 1; version <= to; version++) {
    await migrate(version);
  }
}
