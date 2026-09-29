import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'task_api.dart';

final _taskWorkspaceProvider = FutureProvider<_TaskWorkspace>((ref) async {
  final api = ref.read(taskApiProvider);
  final results = await Future.wait([
    api.getTasks(),
    api.getProjects(),
  ]);
  return _TaskWorkspace(
    tasks: (results[0] as List<Map<String, dynamic>>)
        .map(_TaskView.fromJson)
        .toList(),
    projects: (results[1] as List<Map<String, dynamic>>)
        .map(_ProjectView.fromJson)
        .toList(),
  );
});

final _checklistProvider = FutureProvider.family<List<_ChecklistItem>, String>(
  (ref, taskId) async {
    final items = await ref.read(taskApiProvider).getChecklistItems(taskId);
    return items.map(_ChecklistItem.fromJson).toList();
  },
);

enum _TaskFilter { open, today, upcoming, completed, all }

class TasksPage extends ConsumerStatefulWidget {
  const TasksPage({super.key});

  @override
  ConsumerState<TasksPage> createState() => _TasksPageState();
}

class _TasksPageState extends ConsumerState<TasksPage> {
  _TaskFilter _filter = _TaskFilter.open;
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(_taskWorkspaceProvider);
    final workspaceData = workspace.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= 720;

    return Scaffold(
      appBar: AppBar(
        title: const Text('待辦'),
        actions: [
          if (wide)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: FilledButton.icon(
                onPressed: workspaceData == null
                    ? null
                    : () => _openEditor(workspaceData),
                icon: const Icon(Icons.add),
                label: const Text('新增待辦'),
              ),
            ),
        ],
      ),
      body: workspace.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _TaskErrorState(
          error: error,
          onRetry: () => ref.invalidate(_taskWorkspaceProvider),
        ),
        data: (data) => _buildContent(context, data),
      ),
      floatingActionButton: !wide && workspaceData != null
          ? FloatingActionButton(
              tooltip: '新增待辦',
              onPressed: () => _openEditor(workspaceData),
              child: const Icon(Icons.add),
            )
          : null,
    );
  }

  Widget _buildContent(BuildContext context, _TaskWorkspace workspace) {
    final filtered = _visibleTasks(workspace.tasks);
    final activeCount = workspace.tasks
        .where((task) => !task.isCompleted && !task.isCancelled)
        .length;
    final todayCount = workspace.tasks.where(_isDueTodayAndOpen).length;
    final overdueCount = workspace.tasks.where((task) => task.isOverdue).length;

    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1040),
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              sliver: SliverToBoxAdapter(
                child: _TaskOverview(
                  activeCount: activeCount,
                  todayCount: todayCount,
                  overdueCount: overdueCount,
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              sliver: SliverToBoxAdapter(
                child: TextField(
                  onChanged: (value) => setState(() => _query = value.trim()),
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search),
                    hintText: '搜尋待辦或備註',
                  ),
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
              sliver: SliverToBoxAdapter(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _filterChip(_TaskFilter.open, '進行中'),
                      _filterChip(_TaskFilter.today, '今天'),
                      _filterChip(_TaskFilter.upcoming, '之後'),
                      _filterChip(_TaskFilter.completed, '已完成'),
                      _filterChip(_TaskFilter.all, '全部'),
                    ],
                  ),
                ),
              ),
            ),
            if (filtered.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _TaskEmptyState(
                  hasAnyTasks: workspace.tasks.isNotEmpty,
                  onCreate: () => _openEditor(workspace),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                sliver: SliverList.builder(
                  itemCount: filtered.length,
                  itemBuilder: (context, index) {
                    final task = filtered[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _TaskCard(
                        task: task,
                        projectName: workspace.projectName(task.projectId),
                        onToggleCompleted: () => _toggleCompleted(task),
                        onEdit: () => _openEditor(workspace, task: task),
                        onChecklist: () => _openChecklist(task),
                        onDelete: () => _deleteTask(task),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _filterChip(_TaskFilter filter, String label) => Padding(
        padding: const EdgeInsets.only(right: 8),
        child: FilterChip(
          label: Text(label),
          selected: _filter == filter,
          onSelected: (_) => setState(() => _filter = filter),
        ),
      );

  List<_TaskView> _visibleTasks(List<_TaskView> tasks) {
    final query = _query.toLowerCase();
    final result = tasks.where((task) {
      if (query.isNotEmpty &&
          !task.title.toLowerCase().contains(query) &&
          !(task.note ?? '').toLowerCase().contains(query)) {
        return false;
      }
      switch (_filter) {
        case _TaskFilter.open:
          return !task.isCompleted && !task.isCancelled;
        case _TaskFilter.today:
          return _isDueTodayAndOpen(task);
        case _TaskFilter.upcoming:
          final due = task.dueAt?.toLocal();
          if (due == null || task.isCompleted || task.isCancelled) return false;
          return due.isAfter(_endOfToday());
        case _TaskFilter.completed:
          return task.isCompleted;
        case _TaskFilter.all:
          return true;
      }
    }).toList();

    result.sort((a, b) {
      if (a.isCompleted != b.isCompleted) return a.isCompleted ? 1 : -1;
      final aDue = a.dueAt?.toLocal();
      final bDue = b.dueAt?.toLocal();
      if (aDue != null && bDue != null) {
        final compare = aDue.compareTo(bDue);
        if (compare != 0) return compare;
      } else if (aDue != null) {
        return -1;
      } else if (bDue != null) {
        return 1;
      }
      return b.priorityRank.compareTo(a.priorityRank);
    });
    return result;
  }

  bool _isDueTodayAndOpen(_TaskView task) {
    if (task.isCompleted || task.isCancelled) return false;
    final due = task.dueAt?.toLocal();
    if (due == null) return false;
    final now = DateTime.now();
    return due.year == now.year && due.month == now.month && due.day == now.day;
  }

  DateTime _endOfToday() {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day, 23, 59, 59, 999);
  }

  Future<void> _toggleCompleted(_TaskView task) async {
    try {
      final api = ref.read(taskApiProvider);
      if (task.isCompleted) {
        await api.updateTask(task.id, {'status': 'pending'});
      } else {
        await api.completeTask(task.id);
      }
      ref.invalidate(_taskWorkspaceProvider);
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _openEditor(
    _TaskWorkspace workspace, {
    _TaskView? task,
  }) async {
    final result = await showDialog<_TaskEditorResult>(
      context: context,
      builder: (_) => _TaskEditorDialog(
        task: task,
        projects: workspace.projects,
      ),
    );
    if (result == null || !mounted) return;

    try {
      final api = ref.read(taskApiProvider);
      if (task == null) {
        await api.createTask(result.createBody);
      } else {
        await api.updateTask(task.id, result.updateBody);
      }
      ref.invalidate(_taskWorkspaceProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(task == null ? '待辦已新增' : '待辦已更新')),
        );
      }
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _openChecklist(_TaskView task) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => FractionallySizedBox(
        heightFactor: 0.86,
        child: _ChecklistSheet(task: task),
      ),
    );
  }

  Future<void> _deleteTask(_TaskView task) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('刪除待辦？'),
        content: Text('「${task.title}」及其 Checklist 將被刪除。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
              foregroundColor: Theme.of(context).colorScheme.onError,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('刪除'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    try {
      await ref.read(taskApiProvider).deleteTask(task.id);
      ref.invalidate(_taskWorkspaceProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('待辦已刪除')),
        );
      }
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('操作失敗：$error')),
    );
  }
}

class _TaskOverview extends StatelessWidget {
  const _TaskOverview({
    required this.activeCount,
    required this.todayCount,
    required this.overdueCount,
  });

  final int activeCount;
  final int todayCount;
  final int overdueCount;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 20,
          runSpacing: 12,
          children: [
            _OverviewMetric(label: '進行中', value: activeCount),
            _OverviewMetric(label: '今天', value: todayCount),
            _OverviewMetric(
              label: '逾期',
              value: overdueCount,
              emphasis: overdueCount > 0 ? theme.colorScheme.error : null,
            ),
          ],
        ),
      ),
    );
  }
}

class _OverviewMetric extends StatelessWidget {
  const _OverviewMetric({
    required this.label,
    required this.value,
    this.emphasis,
  });

  final String label;
  final int value;
  final Color? emphasis;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 110,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$value',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: emphasis,
                  ),
            ),
            const SizedBox(height: 2),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
}

class _TaskCard extends StatelessWidget {
  const _TaskCard({
    required this.task,
    required this.projectName,
    required this.onToggleCompleted,
    required this.onEdit,
    required this.onChecklist,
    required this.onDelete,
  });

  final _TaskView task;
  final String? projectName;
  final VoidCallback onToggleCompleted;
  final VoidCallback onEdit;
  final VoidCallback onChecklist;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = task.isCompleted || task.isCancelled;
    final due = task.dueAt?.toLocal();
    final reminder = task.reminderAt?.toLocal();

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onEdit,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 10, 8, 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Checkbox(
                value: task.isCompleted,
                onChanged: (_) => onToggleCompleted(),
                semanticLabel: task.isCompleted ? '恢復待辦' : '完成待辦',
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 4, bottom: 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        task.title,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          decoration:
                              task.isCompleted ? TextDecoration.lineThrough : null,
                          color: muted
                              ? theme.colorScheme.onSurface.withValues(alpha: 0.58)
                              : null,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if ((task.note ?? '').trim().isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          task.note!.trim(),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          _MetaChip(
                            icon: Icons.circle_outlined,
                            label: task.statusLabel,
                          ),
                          _MetaChip(
                            icon: Icons.flag_outlined,
                            label: task.priorityLabel,
                          ),
                          if (due != null)
                            _MetaChip(
                              icon: task.isOverdue
                                  ? Icons.warning_amber_rounded
                                  : Icons.schedule,
                              label: task.isOverdue
                                  ? '逾期 ${DateFormat('M/d HH:mm').format(due)}'
                                  : DateFormat('M/d HH:mm').format(due),
                              error: task.isOverdue,
                            ),
                          if (reminder != null)
                            _MetaChip(
                              icon: Icons.notifications_none,
                              label: DateFormat('M/d HH:mm').format(reminder),
                            ),
                          if (projectName != null)
                            _MetaChip(
                              icon: Icons.folder_outlined,
                              label: projectName!,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              PopupMenuButton<String>(
                tooltip: '待辦選項',
                onSelected: (value) {
                  switch (value) {
                    case 'checklist':
                      onChecklist();
                      break;
                    case 'edit':
                      onEdit();
                      break;
                    case 'delete':
                      onDelete();
                      break;
                  }
                },
                itemBuilder: (_) => const [
                  PopupMenuItem(value: 'checklist', child: Text('Checklist')),
                  PopupMenuItem(value: 'edit', child: Text('編輯')),
                  PopupMenuItem(value: 'delete', child: Text('刪除')),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.icon,
    required this.label,
    this.error = false,
  });

  final IconData icon;
  final String label;
  final bool error;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final foreground = error ? theme.colorScheme.error : null;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: error
            ? theme.colorScheme.error.withValues(alpha: 0.10)
            : theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: error
              ? theme.colorScheme.error.withValues(alpha: 0.35)
              : theme.dividerColor,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: foreground),
          const SizedBox(width: 4),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(color: foreground),
          ),
        ],
      ),
    );
  }
}

class _TaskEditorDialog extends StatefulWidget {
  const _TaskEditorDialog({required this.task, required this.projects});

  final _TaskView? task;
  final List<_ProjectView> projects;

  @override
  State<_TaskEditorDialog> createState() => _TaskEditorDialogState();
}

class _TaskEditorDialogState extends State<_TaskEditorDialog> {
  late final TextEditingController _title;
  late final TextEditingController _note;
  late String _priority;
  late String _status;
  late String _projectId;
  DateTime? _dueAt;
  DateTime? _reminderAt;

  @override
  void initState() {
    super.initState();
    final task = widget.task;
    _title = TextEditingController(text: task?.title ?? '');
    _note = TextEditingController(text: task?.note ?? '');
    _priority = task?.priority ?? 'normal';
    _status = task?.status ?? 'pending';
    _projectId = task?.projectId ?? '';
    _dueAt = task?.dueAt?.toLocal();
    _reminderAt = task?.reminderAt?.toLocal();
  }

  @override
  void dispose() {
    _title.dispose();
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.task != null;
    return AlertDialog(
      title: Text(editing ? '編輯待辦' : '新增待辦'),
      content: SizedBox(
        width: 560,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                key: const ValueKey('task-title-field'),
                controller: _title,
                autofocus: true,
                decoration: const InputDecoration(labelText: '標題 *'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _note,
                minLines: 2,
                maxLines: 5,
                decoration: const InputDecoration(labelText: '備註'),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _priority,
                      decoration: const InputDecoration(labelText: '優先度'),
                      items: const [
                        DropdownMenuItem(value: 'low', child: Text('低')),
                        DropdownMenuItem(value: 'normal', child: Text('一般')),
                        DropdownMenuItem(value: 'high', child: Text('高')),
                      ],
                      onChanged: (value) {
                        if (value != null) setState(() => _priority = value);
                      },
                    ),
                  ),
                  if (editing) ...[
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: _status,
                        decoration: const InputDecoration(labelText: '狀態'),
                        items: const [
                          DropdownMenuItem(value: 'pending', child: Text('待處理')),
                          DropdownMenuItem(
                            value: 'in_progress',
                            child: Text('進行中'),
                          ),
                          DropdownMenuItem(value: 'waiting', child: Text('等待中')),
                          DropdownMenuItem(
                            value: 'scheduled',
                            child: Text('已排程'),
                          ),
                          DropdownMenuItem(value: 'completed', child: Text('已完成')),
                          DropdownMenuItem(value: 'cancelled', child: Text('已取消')),
                        ],
                        onChanged: (value) {
                          if (value != null) setState(() => _status = value);
                        },
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _projectId,
                decoration: const InputDecoration(labelText: '專案'),
                items: [
                  const DropdownMenuItem<String>(
                    value: '',
                    child: Text('無專案'),
                  ),
                  for (final project in widget.projects)
                    DropdownMenuItem<String>(
                      value: project.id,
                      child: Text(project.name),
                    ),
                ],
                onChanged: (value) {
                  if (value != null) setState(() => _projectId = value);
                },
              ),
              const SizedBox(height: 12),
              _DateTimeField(
                label: '到期時間',
                value: _dueAt,
                onPick: () => _pickDateTime(_dueAt, (value) => _dueAt = value),
                onClear: _dueAt == null ? null : () => setState(() => _dueAt = null),
              ),
              const SizedBox(height: 8),
              _DateTimeField(
                label: '提醒時間',
                value: _reminderAt,
                onPick: () => _pickDateTime(
                  _reminderAt,
                  (value) => _reminderAt = value,
                ),
                onClear: _reminderAt == null
                    ? null
                    : () => setState(() => _reminderAt = null),
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
          key: const ValueKey('task-save-button'),
          onPressed: _save,
          child: const Text('儲存'),
        ),
      ],
    );
  }

  Future<void> _pickDateTime(
    DateTime? current,
    ValueChanged<DateTime> setValue,
  ) async {
    final now = DateTime.now();
    final initial = current ?? now;
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 10),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (time == null || !mounted) return;
    setState(() {
      setValue(DateTime(date.year, date.month, date.day, time.hour, time.minute));
    });
  }

  void _save() {
    final title = _title.text.trim();
    if (title.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('請輸入待辦標題')),
      );
      return;
    }
    Navigator.pop(
      context,
      _TaskEditorResult(
        title: title,
        note: _note.text.trim().isEmpty ? null : _note.text.trim(),
        priority: _priority,
        status: _status,
        projectId: _projectId.isEmpty ? null : _projectId,
        dueAt: _dueAt,
        reminderAt: _reminderAt,
      ),
    );
  }
}

class _DateTimeField extends StatelessWidget {
  const _DateTimeField({
    required this.label,
    required this.value,
    required this.onPick,
    required this.onClear,
  });

  final String label;
  final DateTime? value;
  final VoidCallback onPick;
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: onPick,
              icon: const Icon(Icons.event_outlined),
              label: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  value == null
                      ? '$label：未設定'
                      : '$label：${DateFormat('yyyy/M/d HH:mm').format(value!)}',
                ),
              ),
            ),
          ),
          if (onClear != null)
            IconButton(
              tooltip: '清除$label',
              onPressed: onClear,
              icon: const Icon(Icons.close),
            ),
        ],
      );
}

class _ChecklistSheet extends ConsumerStatefulWidget {
  const _ChecklistSheet({required this.task});

  final _TaskView task;

  @override
  ConsumerState<_ChecklistSheet> createState() => _ChecklistSheetState();
}

class _ChecklistSheetState extends ConsumerState<_ChecklistSheet> {
  final _newItem = TextEditingController();

  @override
  void dispose() {
    _newItem.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final checklist = ref.watch(_checklistProvider(widget.task.id));
    return Scaffold(
      appBar: AppBar(title: Text(widget.task.title)),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _newItem,
                    decoration: const InputDecoration(
                      labelText: '新增 Checklist 項目',
                    ),
                    onSubmitted: (_) => _addItem(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  tooltip: '新增項目',
                  onPressed: _addItem,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
          ),
          Expanded(
            child: checklist.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => _TaskErrorState(
                error: error,
                onRetry: () => ref.invalidate(_checklistProvider(widget.task.id)),
              ),
              data: (items) => items.isEmpty
                  ? const Center(child: Text('還沒有 Checklist 項目'))
                  : ListView.separated(
                      padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
                      itemCount: items.length,
                      separatorBuilder: (_, __) => const Divider(),
                      itemBuilder: (_, index) {
                        final item = items[index];
                        return ListTile(
                          leading: Checkbox(
                            value: item.isDone,
                            onChanged: (value) => _setDone(item, value ?? false),
                          ),
                          title: Text(
                            item.title,
                            style: item.isDone
                                ? const TextStyle(
                                    decoration: TextDecoration.lineThrough,
                                  )
                                : null,
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                tooltip: '編輯項目',
                                onPressed: () => _editItem(item),
                                icon: const Icon(Icons.edit_outlined),
                              ),
                              IconButton(
                                tooltip: '刪除項目',
                                onPressed: () => _deleteItem(item),
                                icon: const Icon(Icons.delete_outline),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _addItem() async {
    final title = _newItem.text.trim();
    if (title.isEmpty) return;
    try {
      await ref.read(taskApiProvider).createChecklistItem(
        widget.task.id,
        {'title': title},
      );
      _newItem.clear();
      ref.invalidate(_checklistProvider(widget.task.id));
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _setDone(_ChecklistItem item, bool isDone) async {
    try {
      await ref.read(taskApiProvider).updateChecklistItem(
        widget.task.id,
        item.id,
        {'is_done': isDone},
      );
      ref.invalidate(_checklistProvider(widget.task.id));
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _editItem(_ChecklistItem item) async {
    final controller = TextEditingController(text: item.title);
    final title = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('編輯 Checklist'),
        content: TextField(controller: controller, autofocus: true),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('儲存'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (title == null || title.isEmpty || !mounted) return;
    try {
      await ref.read(taskApiProvider).updateChecklistItem(
        widget.task.id,
        item.id,
        {'title': title},
      );
      ref.invalidate(_checklistProvider(widget.task.id));
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _deleteItem(_ChecklistItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('刪除 Checklist 項目？'),
        content: Text('「${item.title}」將被刪除。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
              foregroundColor: Theme.of(context).colorScheme.onError,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('刪除'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await ref
          .read(taskApiProvider)
          .deleteChecklistItem(widget.task.id, item.id);
      ref.invalidate(_checklistProvider(widget.task.id));
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('操作失敗：$error')),
    );
  }
}

class _TaskErrorState extends StatelessWidget {
  const _TaskErrorState({required this.error, required this.onRetry});

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined, size: 44),
              const SizedBox(height: 12),
              const Text('待辦載入失敗'),
              const SizedBox(height: 4),
              Text(
                '$error',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('重試'),
              ),
            ],
          ),
        ),
      );
}

class _TaskEmptyState extends StatelessWidget {
  const _TaskEmptyState({required this.hasAnyTasks, required this.onCreate});

  final bool hasAnyTasks;
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.task_alt, size: 48),
              const SizedBox(height: 12),
              Text(
                hasAnyTasks ? '這個篩選條件沒有待辦' : '還沒有待辦',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                hasAnyTasks ? '切換篩選條件，或新增一個待辦。' : '先建立第一個待辦。',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: onCreate,
                icon: const Icon(Icons.add),
                label: const Text('新增待辦'),
              ),
            ],
          ),
        ),
      );
}

class _TaskWorkspace {
  const _TaskWorkspace({required this.tasks, required this.projects});

  final List<_TaskView> tasks;
  final List<_ProjectView> projects;

  String? projectName(String? id) {
    if (id == null) return null;
    for (final project in projects) {
      if (project.id == id) return project.name;
    }
    return null;
  }
}

class _TaskView {
  const _TaskView({
    required this.id,
    required this.title,
    required this.note,
    required this.status,
    required this.priority,
    required this.dueAt,
    required this.reminderAt,
    required this.projectId,
  });

  factory _TaskView.fromJson(Map<String, dynamic> json) => _TaskView(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        note: json['note']?.toString(),
        status: json['status']?.toString() ?? 'pending',
        priority: json['priority']?.toString() ?? 'normal',
        dueAt: DateTime.tryParse(json['due_at']?.toString() ?? ''),
        reminderAt: DateTime.tryParse(json['reminder_at']?.toString() ?? ''),
        projectId: json['project_id']?.toString(),
      );

  final String id;
  final String title;
  final String? note;
  final String status;
  final String priority;
  final DateTime? dueAt;
  final DateTime? reminderAt;
  final String? projectId;

  bool get isCompleted => status == 'completed';
  bool get isCancelled => status == 'cancelled';
  bool get isOverdue =>
      dueAt != null && !isCompleted && !isCancelled && dueAt!.isBefore(DateTime.now());

  int get priorityRank => switch (priority) {
        'high' => 3,
        'normal' => 2,
        'low' => 1,
        _ => 0,
      };

  String get priorityLabel => switch (priority) {
        'high' => '高優先',
        'low' => '低優先',
        _ => '一般',
      };

  String get statusLabel => switch (status) {
        'in_progress' => '進行中',
        'waiting' => '等待中',
        'scheduled' => '已排程',
        'completed' => '已完成',
        'cancelled' => '已取消',
        _ => '待處理',
      };
}

class _ProjectView {
  const _ProjectView({required this.id, required this.name});

  factory _ProjectView.fromJson(Map<String, dynamic> json) => _ProjectView(
        id: json['id']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
      );

  final String id;
  final String name;
}

class _ChecklistItem {
  const _ChecklistItem({
    required this.id,
    required this.title,
    required this.isDone,
  });

  factory _ChecklistItem.fromJson(Map<String, dynamic> json) => _ChecklistItem(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        isDone: json['is_done'] == true,
      );

  final String id;
  final String title;
  final bool isDone;
}

class _TaskEditorResult {
  const _TaskEditorResult({
    required this.title,
    required this.note,
    required this.priority,
    required this.status,
    required this.projectId,
    required this.dueAt,
    required this.reminderAt,
  });

  final String title;
  final String? note;
  final String priority;
  final String status;
  final String? projectId;
  final DateTime? dueAt;
  final DateTime? reminderAt;

  Map<String, dynamic> get createBody => {
        'title': title,
        'note': note,
        'priority': priority,
        'due_at': dueAt?.toUtc().toIso8601String(),
        'reminder_at': reminderAt?.toUtc().toIso8601String(),
        'project_id': projectId,
      };

  Map<String, dynamic> get updateBody => {
        ...createBody,
        'status': status,
      };
}
