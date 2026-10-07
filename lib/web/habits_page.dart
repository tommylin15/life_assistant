import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../app/design_system/app_components.dart';
import '../app/theme/app_tokens.dart';
import 'habit_api.dart';

final _habitsProvider = FutureProvider<_HabitWorkspace>((ref) async {
  final api = ref.read(habitApiProvider);
  final habits = (await api.getHabits()).map(_HabitView.fromJson).toList();
  final histories = <String, List<_HabitCompletionView>>{};

  await Future.wait([
    for (final habit in habits)
      api.getHabitCompletions(habit.id).then(
            (values) => histories[habit.id] =
                values.map(_HabitCompletionView.fromJson).toList(),
          ),
  ]);

  return _HabitWorkspace(habits: habits, histories: histories);
});

class HabitsPage extends ConsumerStatefulWidget {
  const HabitsPage({super.key});

  @override
  ConsumerState<HabitsPage> createState() => _HabitsPageState();
}

class _HabitsPageState extends ConsumerState<HabitsPage> {
  final Set<String> _completing = <String>{};

  void _reload() => ref.invalidate(_habitsProvider);

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(_habitsProvider);
    final workspace = value.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.pageActions;

    return Scaffold(
      appBar: AppBar(
        title: const Text('習慣'),
        actions: [
          if (wide)
            Padding(
              padding: const EdgeInsets.only(right: AppSpacing.lg),
              child: FilledButton.icon(
                onPressed: workspace == null ? null : () => _edit(),
                icon: const Icon(Icons.add),
                label: const Text('新增習慣'),
              ),
            ),
        ],
      ),
      body: value.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppStatePanel(
          title: '無法載入習慣',
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
      floatingActionButton: !wide && workspace != null
          ? FloatingActionButton(
              tooltip: '新增習慣',
              onPressed: _edit,
              child: const Icon(Icons.add),
            )
          : null,
    );
  }

  Widget _content(_HabitWorkspace workspace) {
    if (workspace.habits.isEmpty) {
      return AppStatePanel(
        title: '還沒有習慣',
        message: '建立週期與提醒，完成後留下紀錄。',
        icon: const Icon(Icons.repeat_rounded),
        action: FilledButton.icon(
          onPressed: _edit,
          icon: const Icon(Icons.add),
          label: const Text('新增習慣'),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(_habitsProvider);
        await ref.read(_habitsProvider.future);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          AppPageFrame(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  '維持中的習慣',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '記錄週期、提醒與每次完成時間。',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: AppSpacing.lg),
                for (final habit in workspace.habits) ...[
                  _HabitCard(
                    habit: habit,
                    completions: workspace.historyFor(habit.id),
                    completing: _completing.contains(habit.id),
                    onComplete: () => _complete(habit),
                    onEdit: () => _edit(habit: habit),
                    onHistory: () => _history(
                      habit,
                      workspace.historyFor(habit.id),
                    ),
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

  Future<void> _edit({_HabitView? habit}) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _HabitEditorDialog(habit: habit),
    );
    if (result == null || !mounted) return;

    try {
      final api = ref.read(habitApiProvider);
      if (habit == null) {
        await api.createHabit(result);
      } else {
        await api.updateHabit(habit.id, result);
      }
      _reload();
      if (!mounted) return;
      _message(habit == null ? '習慣已新增' : '習慣已更新');
    } catch (error) {
      if (mounted) _message('操作失敗：$error');
    }
  }

  Future<void> _complete(_HabitView habit) async {
    if (_completing.contains(habit.id)) return;
    setState(() => _completing.add(habit.id));
    try {
      await ref.read(habitApiProvider).completeHabit(habit.id);
      _reload();
      if (!mounted) return;
      _message('已記錄「${habit.title}」完成');
    } catch (error) {
      if (mounted) _message('記錄完成失敗：$error');
    } finally {
      if (mounted) {
        setState(() => _completing.remove(habit.id));
      }
    }
  }

  Future<void> _history(
    _HabitView habit,
    List<_HabitCompletionView> completions,
  ) =>
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text('${habit.title} · 完成紀錄'),
          content: SizedBox(
            width: 480,
            child: completions.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.xl),
                    child: Text('尚無完成紀錄'),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    itemCount: completions.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, index) {
                      final completedAt = completions[index].completedAt.toLocal();
                      return ListTile(
                        leading: const Icon(Icons.check_circle_outline),
                        title: Text(
                          DateFormat('yyyy/M/d HH:mm').format(completedAt),
                        ),
                      );
                    },
                  ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('關閉'),
            ),
          ],
        ),
      );

  void _message(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}

class _HabitCard extends StatelessWidget {
  const _HabitCard({
    required this.habit,
    required this.completions,
    required this.completing,
    required this.onComplete,
    required this.onEdit,
    required this.onHistory,
  });

  final _HabitView habit;
  final List<_HabitCompletionView> completions;
  final bool completing;
  final VoidCallback onComplete;
  final VoidCallback onEdit;
  final VoidCallback onHistory;

  @override
  Widget build(BuildContext context) {
    final latest = completions.isEmpty
        ? null
        : completions.first.completedAt.toLocal();

    return AppSectionCard(
      title: habit.title,
      subtitle: _recurrenceLabel(habit.recurrenceRule),
      action: IconButton(
        tooltip: '編輯習慣：${habit.title}',
        onPressed: onEdit,
        icon: const Icon(Icons.edit_outlined),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              if (habit.reminderTime case final reminder?)
                AppStatusChip(
                  icon: Icons.notifications_none,
                  label: '提醒 $reminder',
                  tone: AppStatusTone.info,
                ),
              AppStatusChip(
                icon: Icons.history,
                label: '完成紀錄 ${completions.length} 筆',
                tone: completions.isEmpty
                    ? AppStatusTone.neutral
                    : AppStatusTone.success,
              ),
              if (latest != null)
                AppStatusChip(
                  icon: Icons.check_circle_outline,
                  label: '最近 ${DateFormat('M/d HH:mm').format(latest)}',
                  tone: AppStatusTone.success,
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              Semantics(
                button: true,
                label: '記錄完成：${habit.title}',
                child: FilledButton.icon(
                  key: ValueKey('habit-complete-${habit.id}'),
                  onPressed: completing ? null : onComplete,
                  icon: completing
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.check),
                  label: Text(completing ? '記錄中' : '記錄完成'),
                ),
              ),
              OutlinedButton.icon(
                key: ValueKey('habit-history-${habit.id}'),
                onPressed: onHistory,
                icon: const Icon(Icons.history),
                label: const Text('完成紀錄'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HabitEditorDialog extends StatefulWidget {
  const _HabitEditorDialog({required this.habit});

  final _HabitView? habit;

  @override
  State<_HabitEditorDialog> createState() => _HabitEditorDialogState();
}

class _HabitEditorDialogState extends State<_HabitEditorDialog> {
  static const _daily = 'FREQ=DAILY';
  static const _weekdays = 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR';
  static const _weekly = 'FREQ=WEEKLY';
  static const _custom = '__custom__';

  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _reminder;
  late final TextEditingController _customRule;
  late String _recurrenceChoice;

  @override
  void initState() {
    super.initState();
    final habit = widget.habit;
    final rule = habit?.recurrenceRule ?? _daily;
    _title = TextEditingController(text: habit?.title ?? '');
    _reminder = TextEditingController(text: habit?.reminderTime ?? '');
    _recurrenceChoice = {_daily, _weekdays, _weekly}.contains(rule)
        ? rule
        : _custom;
    _customRule = TextEditingController(
      text: _recurrenceChoice == _custom ? rule : '',
    );
  }

  @override
  void dispose() {
    _title.dispose();
    _reminder.dispose();
    _customRule.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.habit != null;
    return AlertDialog(
      title: Text(editing ? '編輯習慣' : '新增習慣'),
      content: SizedBox(
        width: 520,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  key: const ValueKey('habit-title-field'),
                  controller: _title,
                  autofocus: true,
                  maxLength: 500,
                  decoration: const InputDecoration(labelText: '名稱'),
                  validator: (value) =>
                      (value ?? '').trim().isEmpty ? '請輸入習慣名稱' : null,
                ),
                const SizedBox(height: AppSpacing.md),
                DropdownButtonFormField<String>(
                  key: const ValueKey('habit-recurrence-field'),
                  initialValue: _recurrenceChoice,
                  decoration: const InputDecoration(labelText: '週期'),
                  items: const [
                    DropdownMenuItem(value: _daily, child: Text('每日')),
                    DropdownMenuItem(value: _weekdays, child: Text('平日')),
                    DropdownMenuItem(value: _weekly, child: Text('每週')),
                    DropdownMenuItem(value: _custom, child: Text('自訂規則')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() => _recurrenceChoice = value);
                    }
                  },
                ),
                if (_recurrenceChoice == _custom) ...[
                  const SizedBox(height: AppSpacing.md),
                  TextFormField(
                    key: const ValueKey('habit-custom-rule-field'),
                    controller: _customRule,
                    decoration: const InputDecoration(
                      labelText: '自訂週期規則',
                      helperText: '例如 FREQ=WEEKLY;BYDAY=MO,WE,FR',
                    ),
                    validator: (value) {
                      if (_recurrenceChoice != _custom) return null;
                      return (value ?? '').trim().isEmpty ? '請輸入週期規則' : null;
                    },
                  ),
                ],
                const SizedBox(height: AppSpacing.md),
                TextFormField(
                  key: const ValueKey('habit-reminder-field'),
                  controller: _reminder,
                  keyboardType: TextInputType.datetime,
                  decoration: const InputDecoration(
                    labelText: '提醒時間（選填）',
                    hintText: 'HH:mm',
                    helperText: '使用 24 小時制，例如 07:30。',
                  ),
                  validator: (value) {
                    final normalized = (value ?? '').trim();
                    if (normalized.isEmpty) return null;
                    final valid = RegExp(
                      r'^(?:[01]\d|2[0-3]):[0-5]\d$',
                    ).hasMatch(normalized);
                    return valid ? null : '請使用 HH:mm，例如 07:30';
                  },
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消'),
        ),
        FilledButton(
          key: const ValueKey('habit-save-button'),
          onPressed: _submit,
          child: const Text('儲存'),
        ),
      ],
    );
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final reminder = _reminder.text.trim();
    final recurrence = _recurrenceChoice == _custom
        ? _customRule.text.trim()
        : _recurrenceChoice;
    Navigator.pop(context, <String, dynamic>{
      'title': _title.text.trim(),
      'recurrence_rule': recurrence,
      'reminder_time': reminder.isEmpty ? null : reminder,
    });
  }
}

class _HabitWorkspace {
  const _HabitWorkspace({required this.habits, required this.histories});

  final List<_HabitView> habits;
  final Map<String, List<_HabitCompletionView>> histories;

  List<_HabitCompletionView> historyFor(String habitId) =>
      histories[habitId] ?? const [];
}

class _HabitView {
  const _HabitView({
    required this.id,
    required this.title,
    required this.recurrenceRule,
    required this.reminderTime,
  });

  factory _HabitView.fromJson(Map<String, dynamic> json) => _HabitView(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        recurrenceRule: json['recurrence_rule']?.toString() ?? '',
        reminderTime: json['reminder_time']?.toString(),
      );

  final String id;
  final String title;
  final String recurrenceRule;
  final String? reminderTime;
}

class _HabitCompletionView {
  const _HabitCompletionView({required this.completedAt});

  factory _HabitCompletionView.fromJson(Map<String, dynamic> json) =>
      _HabitCompletionView(
        completedAt: DateTime.parse(json['completed_at'].toString()),
      );

  final DateTime completedAt;
}

String _recurrenceLabel(String rule) {
  switch (rule) {
    case 'FREQ=DAILY':
    case 'daily':
      return '每日';
    case 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR':
    case 'weekdays':
      return '平日';
    case 'FREQ=WEEKLY':
    case 'weekly':
      return '每週';
    default:
      return rule;
  }
}
