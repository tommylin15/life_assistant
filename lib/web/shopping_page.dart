import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/design_system/app_components.dart';
import '../app/theme/app_tokens.dart';
import 'shopping_api.dart';
import 'visual_system.dart';

final _shoppingListsProvider = FutureProvider<List<_ShoppingListView>>((ref) async {
  final api = ref.read(shoppingApiProvider);
  return (await api.getShoppingLists()).map(_ShoppingListView.fromJson).toList();
});

class ShoppingPage extends ConsumerStatefulWidget {
  const ShoppingPage({super.key});

  @override
  ConsumerState<ShoppingPage> createState() => _ShoppingPageState();
}

class _ShoppingPageState extends ConsumerState<ShoppingPage> {
  final Set<String> _updatingItems = <String>{};
  final Set<String> _mutatingLists = <String>{};

  void _reload() => ref.invalidate(_shoppingListsProvider);

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(_shoppingListsProvider);
    final lists = value.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.pageActions;

    return Scaffold(
      body: value.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppStatePanel(
          title: '無法載入購物清單',
          message: '$error',
          icon: const Icon(Icons.cloud_off_outlined),
          action: FilledButton.icon(
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
            label: const Text('重試'),
          ),
        ),
        data: _content,
      ),
      floatingActionButton: !wide && lists != null
          ? FloatingActionButton(
              tooltip: '新增清單',
              onPressed: _createList,
              child: const Icon(Icons.add),
            )
          : null,
    );
  }

  Widget _content(List<_ShoppingListView> lists) {
    if (lists.isEmpty) {
      return Column(children: [
        const Padding(
          padding: EdgeInsets.all(16),
          child: LifeFeatureHeader(feature: LifeVisualFeature.shopping),
        ),
        Expanded(child: AppStatePanel(
        title: '還沒有購物清單',
        message: '建立清單、加入分類品項，採買時直接勾選完成。',
        icon: const Icon(Icons.shopping_cart_outlined),
        action: FilledButton.icon(
          onPressed: _createList,
          icon: const Icon(Icons.add),
          label: const Text('新增清單'),
        ),
      )),
      ]);
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(_shoppingListsProvider);
        await ref.read(_shoppingListsProvider.future);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          AppPageFrame(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                LifeFeatureHeader(
                  feature: LifeVisualFeature.shopping,
                  trailing: MediaQuery.sizeOf(context).width >= AppBreakpoints.pageActions
                    ? FilledButton.icon(
                        onPressed: _createList,
                        icon: const Icon(Icons.add),
                        label: const Text('新增清單')) : null,
                ),
                const SizedBox(height: AppSpacing.md),
                for (final list in lists) ...[
                  _ShoppingListCard(
                    list: list,
                    updatingItems: _updatingItems,
                    busy: _mutatingLists.contains(list.id),
                    onAddItem: () => _addItem(list),
                    onEditList: () => _editList(list),
                    onDeleteList: () => _deleteList(list),
                    onEditItem: (item) => _editItem(list, item),
                    onDeleteItem: (item) => _deleteItem(list, item),
                    onToggle: _toggleItem,
                  ),
                  const SizedBox(height: AppSpacing.md),
                ],
                const SizedBox(height: 72),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _createList() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const _ShoppingListDialog(),
    );
    if (result == null || !mounted) return;

    try {
      await ref.read(shoppingApiProvider).createShoppingList(result);
      _reload();
      if (mounted) _message('購物清單已新增');
    } catch (error) {
      if (mounted) _message('新增清單失敗：$error');
    }
  }

  Future<void> _addItem(_ShoppingListView list) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ShoppingItemDialog(listName: list.name),
    );
    if (result == null || !mounted) return;

    if (_mutatingLists.contains(list.id)) return;
    setState(() => _mutatingLists.add(list.id));
    try {
      final items = result['items'] as List<dynamic>;
      await ref.read(shoppingApiProvider).createShoppingItemsBatch(list.id, result);
      _reload();
      if (mounted) _message('已加入 ${items.length} 個品項至「${list.name}」');
    } catch (error) {
      if (mounted) _message('新增品項失敗：$error');
    } finally {
      if (mounted) setState(() => _mutatingLists.remove(list.id));
    }
  }

  Future<void> _editList(_ShoppingListView list) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ShoppingListDialog(list: list),
    );
    if (result == null || !mounted || _mutatingLists.contains(list.id)) return;
    setState(() => _mutatingLists.add(list.id));
    try {
      await ref.read(shoppingApiProvider).updateShoppingList(
        list.id, {'name': result['name']},
      );
      _reload();
      if (mounted) _message('清單已修改');
    } catch (error) {
      if (mounted) _message('修改清單失敗：$error');
    } finally {
      if (mounted) setState(() => _mutatingLists.remove(list.id));
    }
  }

  Future<bool> _confirmDelete(String title, String description) async {
    return await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text(title),
            content: Text(description),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const Text('確認刪除'),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _deleteList(_ShoppingListView list) async {
    final confirmed = await _confirmDelete(
      '刪除清單「${list.name}」？',
      '將同時刪除這份清單中的 ${list.items.length} 個品項，此操作無法復原。',
    );
    if (!confirmed || !mounted || _mutatingLists.contains(list.id)) return;
    setState(() => _mutatingLists.add(list.id));
    try {
      await ref.read(shoppingApiProvider).deleteShoppingList(list.id);
      _reload();
      if (mounted) _message('清單已刪除');
    } catch (error) {
      if (mounted) _message('刪除清單失敗：$error');
    } finally {
      if (mounted) setState(() => _mutatingLists.remove(list.id));
    }
  }

  Future<void> _editItem(_ShoppingListView list, _ShoppingItemView item) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ShoppingItemDialog(listName: list.name, item: item),
    );
    if (result == null || !mounted || _updatingItems.contains(item.id)) return;
    setState(() => _updatingItems.add(item.id));
    try {
      await ref.read(shoppingApiProvider).updateShoppingItem(item.id, result);
      _reload();
      if (mounted) _message('品項已修改');
    } catch (error) {
      if (mounted) _message('修改品項失敗：$error');
    } finally {
      if (mounted) setState(() => _updatingItems.remove(item.id));
    }
  }

  Future<void> _deleteItem(_ShoppingListView list, _ShoppingItemView item) async {
    final confirmed = await _confirmDelete(
      '刪除「${item.name}」？',
      '將從「${list.name}」移除此品項，此操作無法復原。',
    );
    if (!confirmed || !mounted || _updatingItems.contains(item.id)) return;
    setState(() => _updatingItems.add(item.id));
    try {
      await ref.read(shoppingApiProvider).deleteShoppingItem(item.id);
      _reload();
      if (mounted) _message('品項已刪除');
    } catch (error) {
      if (mounted) _message('刪除品項失敗：$error');
    } finally {
      if (mounted) setState(() => _updatingItems.remove(item.id));
    }
  }

  Future<void> _toggleItem(_ShoppingItemView item, bool value) async {
    if (_updatingItems.contains(item.id)) return;
    setState(() => _updatingItems.add(item.id));
    try {
      await ref
          .read(shoppingApiProvider)
          .updateShoppingItem(item.id, {'is_done': value});
      _reload();
      if (mounted) _message(value ? '已完成「${item.name}」' : '已恢復「${item.name}」');
    } catch (error) {
      if (mounted) _message('更新品項失敗：$error');
    } finally {
      if (mounted) setState(() => _updatingItems.remove(item.id));
    }
  }

  void _message(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}

class _ShoppingListCard extends StatelessWidget {
  const _ShoppingListCard({
    required this.list,
    required this.updatingItems,
    required this.onAddItem,
    required this.onEditList,
    required this.onDeleteList,
    required this.onEditItem,
    required this.onDeleteItem,
    required this.onToggle,
    required this.busy,
  });

  final _ShoppingListView list;
  final Set<String> updatingItems;
  final bool busy;
  final VoidCallback onAddItem;
  final VoidCallback onEditList;
  final VoidCallback onDeleteList;
  final void Function(_ShoppingItemView item) onEditItem;
  final void Function(_ShoppingItemView item) onDeleteItem;
  final void Function(_ShoppingItemView item, bool value) onToggle;

  @override
  Widget build(BuildContext context) {
    final completed = list.items.where((item) => item.isDone).length;
    return AppSectionCard(
      title: list.name,
      subtitle: list.projectId == null ? '未連結專案' : '已連結專案',
      action: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            key: ValueKey('shopping-add-item-${list.id}'),
            tooltip: '新增品項：${list.name}',
            onPressed: busy ? null : onAddItem,
            icon: const Icon(Icons.add_shopping_cart_outlined),
          ),
          PopupMenuButton<String>(
            key: ValueKey('shopping-list-menu-${list.id}'),
            tooltip: '清單操作：${list.name}',
            enabled: !busy,
            onSelected: (action) {
              if (action == 'edit') {
                onEditList();
              } else if (action == 'delete') {
                onDeleteList();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'edit', child: Text('修改清單')),
              PopupMenuItem(value: 'delete', child: Text('刪除清單')),
            ],
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              AppStatusChip(
                icon: Icons.check_circle_outline,
                label: '完成 $completed / ${list.items.length}',
                tone: completed > 0 ? AppStatusTone.success : AppStatusTone.neutral,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          if (list.items.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Text('尚無品項，使用右上角按鈕加入第一個品項。'),
            )
          else
            for (final item in list.items)
              CheckboxListTile(
                key: ValueKey('shopping-toggle-${item.id}'),
                value: item.isDone,
                onChanged: busy || updatingItems.contains(item.id)
                    ? null
                    : (value) {
                        if (value != null) onToggle(item, value);
                      },
                controlAffinity: ListTileControlAffinity.leading,
                contentPadding: EdgeInsets.zero,
                title: Text(
                  item.name,
                  style: item.isDone
                      ? const TextStyle(decoration: TextDecoration.lineThrough)
                      : null,
                ),
                subtitle: item.category == null || item.category!.isEmpty
                    ? null
                    : Text('分類：${item.category}'),
                secondary: PopupMenuButton<String>(
                  key: ValueKey('shopping-item-menu-${item.id}'),
                  tooltip: '品項操作：${item.name}',
                  enabled: !busy && !updatingItems.contains(item.id),
                  onSelected: (action) {
                    if (action == 'edit') {
                      onEditItem(item);
                    } else if (action == 'delete') {
                      onDeleteItem(item);
                    }
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'edit', child: Text('修改品項')),
                    PopupMenuItem(value: 'delete', child: Text('刪除品項')),
                  ],
                ),
              ),
        ],
      ),
    );
  }
}

class _ShoppingListDialog extends StatefulWidget {
  const _ShoppingListDialog({this.list});

  final _ShoppingListView? list;

  @override
  State<_ShoppingListDialog> createState() => _ShoppingListDialogState();
}

class _ShoppingListDialogState extends State<_ShoppingListDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();

  @override
  void initState() {
    super.initState();
    _name.text = widget.list?.name ?? '';
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(widget.list == null ? '新增購物清單' : '修改購物清單'),
        content: Form(
          key: _formKey,
          child: SizedBox(
            width: 480,
            child: TextFormField(
              key: const ValueKey('shopping-list-name-field'),
              controller: _name,
              autofocus: true,
              maxLength: 500,
              decoration: const InputDecoration(labelText: '清單名稱'),
              validator: (value) =>
                  (value ?? '').trim().isEmpty ? '請輸入清單名稱' : null,
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () {
              if (!(_formKey.currentState?.validate() ?? false)) return;
              Navigator.pop(context, {'name': _name.text.trim(), 'project_id': null});
            },
            child: const Text('儲存'),
          ),
        ],
      );
}

class _ShoppingItemDialog extends StatefulWidget {
  const _ShoppingItemDialog({required this.listName, this.item});

  final String listName;
  final _ShoppingItemView? item;

  @override
  State<_ShoppingItemDialog> createState() => _ShoppingItemDialogState();
}

class _ShoppingItemDialogState extends State<_ShoppingItemDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _category = TextEditingController();

  bool get _editing => widget.item != null;

  @override
  void initState() {
    super.initState();
    _name.text = widget.item?.name ?? '';
    _category.text = widget.item?.category ?? '';
  }

  @override
  void dispose() {
    _name.dispose();
    _category.dispose();
    super.dispose();
  }

  List<String> _names() => _name.text
      .split(RegExp(r'\r?\n'))
      .map((name) => name.trim())
      .where((name) => name.isNotEmpty)
      .toList();

  String? _validateNames(String? value) {
    final names = _names();
    if (names.isEmpty) return '請輸入品項名稱';
    if (_editing && names.length != 1) return '一次只能修改一個品項';
    if (names.length > 50) return '一次最多新增 50 個品項';
    if (names.any((name) => name.length > 500)) return '每個品項名稱最多 500 字';
    return null;
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        scrollable: true,
        title: Text(_editing
            ? '修改品項 · ${widget.listName}'
            : '新增多個品項 · ${widget.listName}'),
        content: Form(
          key: _formKey,
          child: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  key: const ValueKey('shopping-item-name-field'),
                  controller: _name,
                  autofocus: true,
                  keyboardType: _editing ? TextInputType.text : TextInputType.multiline,
                  minLines: _editing ? 1 : 3,
                  maxLines: _editing ? 1 : 6,
                  maxLength: _editing ? 500 : 25050,
                  decoration: InputDecoration(
                    labelText: _editing ? '品項名稱' : '品項名稱（每行一項）',
                    helperText: _editing ? null : '可直接貼上多行清單，最多 50 項，儲存一次即可',
                    alignLabelWithHint: true,
                  ),
                  validator: _validateNames,
                ),
                const SizedBox(height: AppSpacing.md),
                TextFormField(
                  key: const ValueKey('shopping-item-category-field'),
                  controller: _category,
                  maxLength: 255,
                  decoration: InputDecoration(
                    labelText: '分類（選填）',
                    hintText: '例如 生鮮、日用品',
                    helperText: _editing ? null : '套用到本次所有品項',
                  ),
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () {
              if (!(_formKey.currentState?.validate() ?? false)) return;
              final category = _category.text.trim();
              final normalizedCategory = category.isEmpty ? null : category;
              if (_editing) {
                Navigator.pop(context, {
                  'name': _names().single,
                  'category': normalizedCategory,
                });
              } else {
                Navigator.pop(context, {
                  'items': _names().map((name) => {
                    'name': name,
                    'category': normalizedCategory,
                  }).toList(),
                });
              }
            },
            child: const Text('儲存'),
          ),
        ],
      );
}

class _ShoppingListView {
  const _ShoppingListView({
    required this.id,
    required this.name,
    required this.projectId,
    required this.items,
  });

  factory _ShoppingListView.fromJson(Map<String, dynamic> json) =>
      _ShoppingListView(
        id: json['id'] as String,
        name: json['name'] as String,
        projectId: json['project_id'] as String?,
        items: (json['items'] as List<dynamic>? ?? const [])
            .cast<Map<String, dynamic>>()
            .map(_ShoppingItemView.fromJson)
            .toList(),
      );

  final String id;
  final String name;
  final String? projectId;
  final List<_ShoppingItemView> items;
}

class _ShoppingItemView {
  const _ShoppingItemView({
    required this.id,
    required this.name,
    required this.category,
    required this.isDone,
  });

  factory _ShoppingItemView.fromJson(Map<String, dynamic> json) =>
      _ShoppingItemView(
        id: json['id'] as String,
        name: json['name'] as String,
        category: json['category'] as String?,
        isDone: json['is_done'] as bool,
      );

  final String id;
  final String name;
  final String? category;
  final bool isDone;
}
