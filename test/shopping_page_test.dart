import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/shopping_api.dart';
import 'package:life_assistant/web/shopping_page.dart';

class _FakeShoppingApi implements ShoppingApi {
  _FakeShoppingApi({
    List<Map<String, dynamic>>? lists,
    this.error,
  }) : lists = lists ??
            [
              {
                'id': 'list-1',
                'name': '生活用品',
                'project_id': null,
                'created_at': '2026-10-07T00:00:00Z',
                'items': <Map<String, dynamic>>[
                  {
                    'id': 'item-1',
                    'list_id': 'list-1',
                    'name': '牛奶',
                    'category': '生鮮',
                    'is_done': false,
                    'sort_order': 0,
                  },
                ],
              },
            ];

  final List<Map<String, dynamic>> lists;
  final Object? error;
  final List<Map<String, dynamic>> createdLists = [];
  final List<Map<String, dynamic>> createdItems = [];
  final List<Map<String, dynamic>> updates = [];
  final List<Map<String, dynamic>> listUpdates = [];
  final List<String> deletedLists = [];
  final List<String> deletedItems = [];
  var nextList = 2;
  var nextItem = 2;

  @override
  Future<List<Map<String, dynamic>>> getShoppingLists() async {
    if (error != null) throw error!;
    return lists;
  }

  @override
  Future<Map<String, dynamic>> createShoppingList(
    Map<String, dynamic> body,
  ) async {
    createdLists.add(Map.of(body));
    final list = <String, dynamic>{
      'id': 'list-${nextList++}',
      'name': body['name'],
      'project_id': body['project_id'],
      'created_at': '2026-10-07T01:00:00Z',
      'items': <Map<String, dynamic>>[],
    };
    lists.insert(0, list);
    return list;
  }

  @override
  Future<Map<String, dynamic>> updateShoppingList(
    String listId, Map<String, dynamic> body,
  ) async {
    listUpdates.add({'id': listId, ...body});
    final list = lists.firstWhere((entry) => entry['id'] == listId);
    list.addAll(body);
    return list;
  }

  @override
  Future<void> deleteShoppingList(String listId) async {
    deletedLists.add(listId);
    lists.removeWhere((entry) => entry['id'] == listId);
  }

  @override
  Future<Map<String, dynamic>> createShoppingItem(
    String listId,
    Map<String, dynamic> body,
  ) async {
    createdItems.add({'list_id': listId, ...body});
    final item = <String, dynamic>{
      'id': 'item-${nextItem++}',
      'list_id': listId,
      'name': body['name'],
      'category': body['category'],
      'is_done': false,
      'sort_order': 0,
    };
    final list = lists.firstWhere((entry) => entry['id'] == listId);
    (list['items'] as List<Map<String, dynamic>>).add(item);
    return item;
  }

  @override
  Future<List<Map<String, dynamic>>> createShoppingItemsBatch(
    String listId, Map<String, dynamic> body,
  ) async {
    final created = <Map<String, dynamic>>[];
    for (final entry in (body['items'] as List<dynamic>)) {
      created.add(await createShoppingItem(listId, entry as Map<String, dynamic>));
    }
    return created;
  }

  @override
  Future<Map<String, dynamic>> updateShoppingItem(
    String itemId,
    Map<String, dynamic> body,
  ) async {
    updates.add({'item_id': itemId, ...body});
    for (final list in lists) {
      for (final item in (list['items'] as List<Map<String, dynamic>>)) {
        if (item['id'] == itemId) {
          item.addAll(body);
          return item;
        }
      }
    }
    throw StateError('item not found');
  }

  @override
  Future<void> deleteShoppingItem(String itemId) async {
    deletedItems.add(itemId);
    for (final list in lists) {
      (list['items'] as List<Map<String, dynamic>>)
          .removeWhere((item) => item['id'] == itemId);
    }
  }
}

Future<void> _pump(
  WidgetTester tester,
  _FakeShoppingApi api,
) async {
  await tester.pumpWidget(
    ProviderScope(
      key: UniqueKey(),
      overrides: [shoppingApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: ShoppingPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders shopping lists, category and progress', (tester) async {
    final api = _FakeShoppingApi();
    await _pump(tester, api);

    expect(find.text('購物清單'), findsOneWidget);
    expect(find.text('生活用品'), findsOneWidget);
    expect(find.text('完成 0 / 1'), findsOneWidget);
    expect(find.text('牛奶'), findsOneWidget);
    expect(find.text('分類：生鮮'), findsOneWidget);
  });

  testWidgets('creates a shopping list', (tester) async {
    final api = _FakeShoppingApi();
    await _pump(tester, api);

    await tester.tap(find.text('新增清單'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('shopping-list-name-field')),
      '旅行採買',
    );
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();

    expect(api.createdLists.single['name'], '旅行採買');
    expect(find.text('旅行採買'), findsOneWidget);
    expect(find.text('購物清單已新增'), findsOneWidget);
  });

  testWidgets('adds and toggles a shopping item', (tester) async {
    final api = _FakeShoppingApi();
    await _pump(tester, api);

    await tester.tap(find.byKey(const ValueKey('shopping-add-item-list-1')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('shopping-item-name-field')),
      '洗衣精',
    );
    await tester.enterText(
      find.byKey(const ValueKey('shopping-item-category-field')),
      '日用品',
    );
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();

    expect(api.createdItems.single['name'], '洗衣精');
    expect(api.createdItems.single['category'], '日用品');
    expect(find.text('洗衣精'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('shopping-toggle-item-2')));
    await tester.pumpAndSettle();

    expect(api.updates.single['item_id'], 'item-2');
    expect(api.updates.single['is_done'], isTrue);
    expect(find.text('完成 1 / 2'), findsOneWidget);
  });

  testWidgets('adds multiple items in one save', (tester) async {
    final api = _FakeShoppingApi();
    await _pump(tester, api);

    await tester.tap(find.byKey(const ValueKey('shopping-add-item-list-1')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('shopping-item-name-field')),
      '蘋果\n牛奶\n麵包',
    );
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();

    expect(api.createdItems.map((entry) => entry['name']),
        ['蘋果', '牛奶', '麵包']);
    expect(find.text('蘋果'), findsOneWidget);
    expect(find.text('麵包'), findsOneWidget);
    expect(find.text('完成 0 / 4'), findsOneWidget);
  });

  testWidgets('edits and deletes an item without deleting the list', (tester) async {
    final api = _FakeShoppingApi();
    await _pump(tester, api);

    await tester.tap(find.byKey(const ValueKey('shopping-item-menu-item-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('修改品項'));
    await tester.pumpAndSettle();
    expect(find.text('修改品項 · 生活用品'), findsOneWidget);
    await tester.enterText(find.byKey(const ValueKey('shopping-item-name-field')), '低脂牛奶');
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();
    expect(api.updates.last['name'], '低脂牛奶');
    expect(find.text('低脂牛奶'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('shopping-item-menu-item-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除品項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(api.deletedItems, isEmpty);

    await tester.tap(find.byKey(const ValueKey('shopping-item-menu-item-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除品項'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('確認刪除'));
    await tester.pumpAndSettle();
    expect(api.deletedItems, ['item-1']);
    expect(find.text('生活用品'), findsOneWidget);
    expect(find.text('低脂牛奶'), findsNothing);
  });

  testWidgets('edits list name and confirms cascade delete', (tester) async {
    final api = _FakeShoppingApi();
    await _pump(tester, api);

    await tester.tap(find.byKey(const ValueKey('shopping-list-menu-list-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('修改清單'));
    await tester.pumpAndSettle();
    expect(find.text('修改購物清單'), findsOneWidget);
    await tester.enterText(
      find.byKey(const ValueKey('shopping-list-name-field')), '出遊清單',
    );
    await tester.tap(find.text('儲存'));
    await tester.pumpAndSettle();
    expect(api.listUpdates.single['name'], '出遊清單');

    await tester.tap(find.byKey(const ValueKey('shopping-list-menu-list-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除清單'));
    await tester.pumpAndSettle();
    expect(find.textContaining('將同時刪除這份清單中的 1 個品項'), findsOneWidget);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(api.deletedLists, isEmpty);

    await tester.tap(find.byKey(const ValueKey('shopping-list-menu-list-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除清單'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('確認刪除'));
    await tester.pumpAndSettle();
    expect(api.deletedLists, ['list-1']);
    expect(find.text('還沒有購物清單'), findsOneWidget);
  });

  testWidgets('shows empty and error states', (tester) async {
    await _pump(tester, _FakeShoppingApi(lists: []));
    expect(find.text('還沒有購物清單'), findsOneWidget);

    await _pump(tester, _FakeShoppingApi(error: Exception('offline')));
    expect(find.text('無法載入購物清單'), findsOneWidget);
    expect(find.text('重試'), findsOneWidget);
  });
}
