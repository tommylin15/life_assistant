import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_theme.dart';
import 'package:life_assistant/web/shopping_api.dart';
import 'package:life_assistant/web/shopping_page.dart';

class _FakeShoppingApi implements ShoppingApi {
  final lists = <Map<String, dynamic>>[
    {'id': 'list1', 'name': '出門採買', 'project_id': null,
     'items': <Map<String, dynamic>>[
       {'id': 'i1', 'name': '牛奶', 'category': null, 'is_done': false},
     ]}
  ];
  int batchCalls = 0;
  int listDeleteCalls = 0;
  int itemDeleteCalls = 0;

  @override
  Future<List<Map<String, dynamic>>> getShoppingLists() async => lists
      .map((list) => <String, dynamic>{...list,
        'items': List<Map<String, dynamic>>.from(list['items'] as List)})
      .toList();

  @override
  Future<Map<String, dynamic>> createShoppingList(Map<String, dynamic> body) async {
    final item = {'id': 'l2', 'name': body['name'], 'project_id': null,
                  'items': <Map<String, dynamic>>[]};
    lists.add(item);
    return item;
  }

  @override
  Future<Map<String, dynamic>> updateShoppingList(String id, Map<String, dynamic> body) async {
    final list = lists.firstWhere((l) => l['id'] == id);
    list.addAll(body);
    return list;
  }

  @override
  Future<void> deleteShoppingList(String id) async {
    listDeleteCalls++;
    lists.removeWhere((l) => l['id'] == id);
  }

  @override
  Future<Map<String, dynamic>> createShoppingItem(String listId, Map<String, dynamic> body) async {
    final result = await createShoppingItemsBatch(listId, {'items': [body]});
    return result.single;
  }

  @override
  Future<List<Map<String, dynamic>>> createShoppingItemsBatch(
      String listId, Map<String, dynamic> body) async {
    batchCalls++;
    final list = lists.firstWhere((l) => l['id'] == listId);
    final items = list['items'] as List<Map<String, dynamic>>;
    final created = (body['items'] as List).map((raw) =>
      <String, dynamic>{'id': 'new${items.length + 1}',
        'is_done': false, ...Map<String, dynamic>.from(raw as Map)}).toList();
    items.addAll(created);
    return created;
  }

  @override
  Future<Map<String, dynamic>> updateShoppingItem(String id, Map<String, dynamic> body) async {
    final item = (lists.single['items'] as List<Map<String, dynamic>>)
        .firstWhere((v) => v['id'] == id);
    item.addAll(body);
    return item;
  }

  @override
  Future<void> deleteShoppingItem(String id) async {
    itemDeleteCalls++;
    for (final list in lists) {
      (list['items'] as List<Map<String, dynamic>>)
          .removeWhere((i) => i['id'] == id);
    }
  }
}

void main() {
  Future<void> launch(WidgetTester tester, _FakeShoppingApi api) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(ProviderScope(
      overrides: [shoppingApiProvider.overrideWithValue(api)],
      child: MaterialApp(theme: AppTheme.light, home: const ShoppingPage())));
    await tester.pumpAndSettle();
  }

  testWidgets('batch add, item removal and list rename survive reload', (tester) async {
    final api = _FakeShoppingApi();
    await launch(tester, api);
    expect(find.text('牛奶'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('shopping-add-item-list1')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('shopping-item-name-field')),
        '雞蛋\n蘋果');
    await tester.tap(find.widgetWithText(FilledButton, '儲存'));
    await tester.pumpAndSettle();
    expect(api.batchCalls, 1);
    expect(find.text('雞蛋'), findsOneWidget);
    expect(find.text('蘋果'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('shopping-item-menu-i1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除品項'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '確認刪除'));
    await tester.pumpAndSettle();
    expect(api.itemDeleteCalls, 1);
    expect(find.text('牛奶'), findsNothing);
    expect(find.text('蘋果'), findsOneWidget);
    expect(api.listDeleteCalls, 0);

    await tester.tap(find.byKey(const ValueKey('shopping-list-menu-list1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('修改清單'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('shopping-list-name-field')),
        '週末採買');
    await tester.tap(find.widgetWithText(FilledButton, '儲存'));
    await tester.pumpAndSettle();
    expect(find.text('週末採買'), findsOneWidget);
    expect(find.text('雞蛋'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('cancel deletion preserves list, confirmed deletion removes only that list',
      (tester) async {
    final api = _FakeShoppingApi();
    await launch(tester, api);
    await tester.tap(find.byKey(const ValueKey('shopping-list-menu-list1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除清單'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(api.listDeleteCalls, 0);
    expect(find.text('出門採買'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('shopping-list-menu-list1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('刪除清單'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '確認刪除'));
    await tester.pumpAndSettle();
    expect(api.listDeleteCalls, 1);
    expect(find.text('出門採買'), findsNothing);
    expect(find.text('還沒有購物清單'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
