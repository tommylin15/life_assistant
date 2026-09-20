// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'shopping_dao.dart';

// ignore_for_file: type=lint
mixin _$ShoppingDaoMixin on DatabaseAccessor<AppDatabase> {
  $ShoppingListsTable get shoppingLists => attachedDatabase.shoppingLists;
  $ShoppingItemsTable get shoppingItems => attachedDatabase.shoppingItems;
  ShoppingDaoManager get managers => ShoppingDaoManager(this);
}

class ShoppingDaoManager {
  final _$ShoppingDaoMixin _db;
  ShoppingDaoManager(this._db);
  $$ShoppingListsTableTableManager get shoppingLists =>
      $$ShoppingListsTableTableManager(_db.attachedDatabase, _db.shoppingLists);
  $$ShoppingItemsTableTableManager get shoppingItems =>
      $$ShoppingItemsTableTableManager(_db.attachedDatabase, _db.shoppingItems);
}
