import 'package:drift/drift.dart';

import '../app_database.dart';

part 'items_dao.g.dart';

@DriftAccessor(tables: [Items, ChecklistItems])
class ItemsDao extends DatabaseAccessor<AppDatabase> with _$ItemsDaoMixin {
  ItemsDao(super.db);

  Stream<List<Item>> watchActive() =>
      (select(items)
            ..where((t) => t.deletedAt.isNull())
            ..orderBy([(t) => OrderingTerm.desc(t.createdAt)]))
          .watch();

  Future<List<Item>> getByProject(String projectId) => (select(
    items,
  )..where((t) => t.projectId.equals(projectId) & t.deletedAt.isNull())).get();

  Future<Item?> getById(String id) =>
      (select(items)..where((t) => t.id.equals(id))).getSingleOrNull();

  Future<void> upsert(ItemsCompanion entry) =>
      into(items).insertOnConflictUpdate(entry);

  Future<void> softDelete(String id) =>
      (update(items)..where((t) => t.id.equals(id))).write(
        ItemsCompanion(deletedAt: Value(DateTime.now())),
      );

  // Checklist
  Stream<List<ChecklistItem>> watchChecklist(String itemId) =>
      (select(checklistItems)
            ..where((t) => t.itemId.equals(itemId))
            ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
          .watch();

  Future<void> upsertChecklist(ChecklistItemsCompanion entry) =>
      into(checklistItems).insertOnConflictUpdate(entry);

  Future<void> deleteChecklist(String id) =>
      (delete(checklistItems)..where((t) => t.id.equals(id))).go();
}
