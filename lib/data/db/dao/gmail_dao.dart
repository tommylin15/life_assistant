import 'package:drift/drift.dart';

import '../app_database.dart';

part 'gmail_dao.g.dart';

@DriftAccessor(tables: [GmailRefs])
class GmailDao extends DatabaseAccessor<AppDatabase> with _$GmailDaoMixin {
  GmailDao(super.db);

  Stream<List<GmailRef>> watchAll() => (select(
    gmailRefs,
  )..orderBy([(t) => OrderingTerm.desc(t.receivedAt)])).watch();

  Future<void> upsert(GmailRefsCompanion entry) =>
      into(gmailRefs).insertOnConflictUpdate(entry);

  Future<void> deleteById(String id) =>
      (delete(gmailRefs)..where((t) => t.id.equals(id))).go();
}
