import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import 'api_client.dart';
import 'auth_state.dart';

final _tasksProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  return ref.read(apiClientProvider).getTasks();
});

class TasksPage extends ConsumerWidget {
  const TasksPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasks = ref.watch(_tasksProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('待辦'),
        actions: [
          IconButton(
            tooltip: 'Google 整合',
            icon: const Icon(Icons.hub_outlined),
            onPressed: () => context.go('/integrations'),
          ),
          IconButton(
            tooltip: '登出',
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              ref.invalidate(_tasksProvider);
            },
          ),
        ],
      ),
      body: tasks.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('載入失敗：$e')),
        data: (items) => items.isEmpty
            ? const Center(child: Text('還沒有待辦'))
            : ListView.builder(
                itemCount: items.length,
                itemBuilder: (_, i) => _TaskTile(
                  items[i],
                  onChanged: () => ref.invalidate(_tasksProvider),
                ),
              ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showTaskDialog(context, ref),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _showTaskDialog(BuildContext context, WidgetRef ref) async {
    final title = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('新增待辦'),
        content: TextField(
          controller: title,
          autofocus: true,
          decoration: const InputDecoration(labelText: '標題'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('儲存'),
          ),
        ],
      ),
    );
    if (ok == true && title.text.trim().isNotEmpty) {
      await ref
          .read(apiClientProvider)
          .createTask({'title': title.text.trim()});
      ref.invalidate(_tasksProvider);
    }
  }
}

class _TaskTile extends ConsumerWidget {
  const _TaskTile(this.task, {required this.onChanged});
  final Map<String, dynamic> task;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final done = task['status'] == 'completed';
    final dueAt = task['due_at'] != null
        ? DateTime.tryParse(task['due_at'] as String)
        : null;
    return ListTile(
      leading: Checkbox(
        value: done,
        onChanged: (_) async {
          if (!done) {
            await ref
                .read(apiClientProvider)
                .completeTask(task['id'] as String);
          }
          onChanged();
        },
      ),
      title: Text(
        task['title'] as String,
        style: done
            ? const TextStyle(decoration: TextDecoration.lineThrough)
            : null,
      ),
      subtitle:
          dueAt != null ? Text(DateFormat('M/d HH:mm').format(dueAt)) : null,
      trailing: IconButton(
        icon: const Icon(Icons.delete_outline),
        onPressed: () async {
          await ref.read(apiClientProvider).deleteTask(task['id'] as String);
          onChanged();
        },
      ),
    );
  }
}
