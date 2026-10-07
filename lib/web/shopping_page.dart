import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/design_system/app_components.dart';
import '../app/theme/app_tokens.dart';
import 'shopping_api.dart';

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

  void _reload() => ref.invalidate(_shoppingListsProvider);

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(_shoppingListsProvider);
    final lists = value.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.pageActions;

    return Scaffold(
      appBar: AppBar(
        title: const Text('購物清單'),
        actions: [
          if (wide)
            Padding(
              padding: const EdgeInsets.only(right: AppSpacing.lg),
              child: FilledButton.icon(
                onPressed: lists == null ? null : _createList,
                icon: const Icon(Icons.add),
                label: const Text('新增清單'),
              ),
            ),
        ],
      ),
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
      return AppStatePanel(
        title: '還沒有購物清單',
        message: '建立清單、加入分類品項，採買時直接勾選完成。',
        icon: const Icon(Icons.shopping_cart_outlined),
        action: FilledButton.icon(
          onPressed: _createList,
          icon: const Icon(Icons.add),
          label: const Text('新增清單'),
        ),
      );
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
                Text(
                  '採買中的清單',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '依清單與分類整理品項，完成後勾選即可保留狀態。',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: AppSpacing.lg),
                for (final list in lists) ...[
                  _ShoppingListCard(
                    list: list,
                    updatingItems: _updatingItems,
                    onAddItem: () => _addItem(list),
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

    try {
      await ref.read(shoppingApiProvider).createShoppingItem(list.id, result);
      _reload();
      if (mounted) _message('品項已加入「${list.name}」');
    } catch (error) {
      if (mounted) _message('新增品項失敗：$error');
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
    required this.onToggle,
  });

  final _ShoppingListView list;
  final Set<String> updatingItems;
  final VoidCallback onAddItem;
  final void Function(_ShoppingItemView item, bool value) onToggle;

  @override
  Widget build(BuildContext context) {
    final completed = list.items.where((item) => item.isDone).length;
    return AppSectionCard(
      title: list.name,
      subtitle: list.projectId == null ? '未連結專案' : '已連結專案',
      action: IconButton(
        key: ValueKey('shopping-add-item-${list.id}'),
        tooltip: '新增品項：${list.name}',
        onPressed: onAddItem,
        icon: const Icon(Icons.add_shopping_cart_outlined),
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
                onChanged: updatingItems.contains(item.id)
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
              ),
        ],
      ),
    );
  }
}

class _ShoppingListDialog extends StatefulWidget {
  const _ShoppingListDialog();

  @override
  State<_ShoppingListDialog> createState() => _ShoppingListDialogState();
}

class _ShoppingListDialogState extends State<_ShoppingListDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('新增購物清單'),
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
  const _ShoppingItemDialog({required this.listName});

  final String listName;

  @override
  State<_ShoppingItemDialog> createState() => _ShoppingItemDialogState();
}

class _ShoppingItemDialogState extends State<_ShoppingItemDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _category = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    _category.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text('新增品項 · ${widget.listName}'),
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
                  maxLength: 500,
                  decoration: const InputDecoration(labelText: '品項名稱'),
                  validator: (value) =>
                      (value ?? '').trim().isEmpty ? '請輸入品項名稱' : null,
                ),
                const SizedBox(height: AppSpacing.md),
                TextFormField(
                  key: const ValueKey('shopping-item-category-field'),
                  controller: _category,
                  maxLength: 255,
                  decoration: const InputDecoration(
                    labelText: '分類（選填）',
                    hintText: '例如 生鮮、日用品',
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
              Navigator.pop(context, {
                'name': _name.text.trim(),
                'category': category.isEmpty ? null : category,
              });
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
