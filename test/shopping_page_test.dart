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
}

Future<void> _pump(
  WidgetTester tester,
  _FakeShoppingApi api,
) async {
  await tester.pumpWidget(
    ProviderScope(
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

    expect(find.text('採買中的清單'), findsOneWidget);
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

  testWidgets('shows empty and error states', (tester) async {
    await _pump(tester, _FakeShoppingApi(lists: []));
    expect(find.text('還沒有購物清單'), findsOneWidget);

    await _pump(tester, _FakeShoppingApi(error: Exception('offline')));
    expect(find.text('無法載入購物清單'), findsOneWidget);
    expect(find.text('重試'), findsOneWidget);
  });
}
