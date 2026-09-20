import 'package:drift/drift.dart';

import '../app_database.dart';

part 'shopping_dao.g.dart';

@DriftAccessor(tables: [ShoppingLists, ShoppingItems])
class ShoppingDao extends DatabaseAccessor<AppDatabase>
    with _$ShoppingDaoMixin {
  ShoppingDao(super.db);

  Stream<List<ShoppingList>> watchLists() => (select(
    shoppingLists,
  )..orderBy([(t) => OrderingTerm.desc(t.createdAt)])).watch();

  Stream<List<ShoppingItem>> watchItems(String listId) =>
      (select(shoppingItems)
            ..where((t) => t.listId.equals(listId))
            ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
          .watch();

  Future<void> upsertList(ShoppingListsCompanion entry) =>
      into(shoppingLists).insertOnConflictUpdate(entry);

  Future<void> upsertItem(ShoppingItemsCompanion entry) =>
      into(shoppingItems).insertOnConflictUpdate(entry);

  Future<void> deleteItem(String id) =>
      (delete(shoppingItems)..where((t) => t.id.equals(id))).go();
}
