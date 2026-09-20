import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../domain/models.dart';
import 'providers.dart';
import 'feature_pages.dart';
import 'theme/app_theme.dart';

final _router = GoRouter(
  routes: [GoRoute(path: '/', builder: (_, __) => const HomeShell())],
);

class LifeAssistantApp extends ConsumerStatefulWidget {
  const LifeAssistantApp({super.key});
  @override
  ConsumerState<LifeAssistantApp> createState() => _LifeAssistantAppState();
}

class _LifeAssistantAppState extends ConsumerState<LifeAssistantApp> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      final saved = await ref.read(appPreferencesProvider).getString('theme');
      final choice = AppThemeChoice.values
          .where((e) => e.name == saved)
          .firstOrNull;
      if (choice != null) ref.read(themeModeProvider.notifier).state = choice;
    });
  }

  @override
  Widget build(BuildContext context) => MaterialApp.router(
    title: '生活助理',
    debugShowCheckedModeBanner: false,
    theme: ref.watch(themeModeProvider) == AppThemeChoice.clean
        ? AppTheme.clean
        : AppTheme.light,
    darkTheme: AppTheme.dark,
    themeMode: switch (ref.watch(themeModeProvider)) {
      AppThemeChoice.dark => ThemeMode.dark,
      AppThemeChoice.system => ThemeMode.system,
      _ => ThemeMode.light,
    },
    routerConfig: _router,
    builder: (context, child) => LockGate(
      child: OnboardingGate(child: child ?? const SizedBox.shrink()),
    ),
  );
}

class OnboardingGate extends ConsumerStatefulWidget {
  const OnboardingGate({super.key, required this.child});
  final Widget child;
  @override
  ConsumerState<OnboardingGate> createState() => _OnboardingState();
}

class _OnboardingState extends ConsumerState<OnboardingGate> {
  bool? done;
  int page = 0;
  static const pages = [
    ('你的資料留在本機', 'SQLite 是主要資料來源，沒有網路仍可管理生活事項。', Icons.phone_android),
    (
      '按需連接 Google',
      'Calendar、Gmail、Drive 只在使用功能時要求最小權限。',
      Icons.cloud_outlined,
    ),
    (
      'ChatGPT 只提出建議',
      'Bridge 的 proposed actions 一律先預覽，由你確認後才執行。',
      Icons.verified_user_outlined,
    ),
  ];
  @override
  void initState() {
    super.initState();
    ref.read(appPreferencesProvider).getBool('onboarding_done').then((v) {
      if (mounted) setState(() => done = v);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (done == null) return const Center(child: CircularProgressIndicator());
    if (done!) return widget.child;
    final item = pages[page];
    return Material(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            children: [
              const Spacer(),
              Icon(item.$3, size: 72),
              const SizedBox(height: 24),
              Text(
                item.$1,
                style: Theme.of(context).textTheme.headlineMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(item.$2, textAlign: TextAlign.center),
              const Spacer(),
              FilledButton(
                onPressed: () async {
                  if (page < pages.length - 1) {
                    setState(() => page++);
                  } else {
                    await ref
                        .read(appPreferencesProvider)
                        .setBool('onboarding_done', true);
                    setState(() => done = true);
                  }
                },
                child: Text(page < pages.length - 1 ? '下一步' : '開始使用'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LockGate extends ConsumerStatefulWidget {
  const LockGate({super.key, required this.child});
  final Widget child;
  @override
  ConsumerState<LockGate> createState() => _LockGateState();
}

class _LockGateState extends ConsumerState<LockGate>
    with WidgetsBindingObserver {
  bool ready = false, unlocked = false;
  final pin = TextEditingController();
  String? error;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _check();
  }

  Future<void> _check() async {
    final lock = ref.read(appLockProvider);
    final enabled = await lock.hasPin;
    if (!enabled) {
      unlocked = true;
    } else {
      unlocked = await lock.authenticateBiometric();
    }
    if (mounted) setState(() => ready = true);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && mounted)
      setState(() => unlocked = false);
    if (state == AppLifecycleState.resumed) _check();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    pin.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!ready)
      return const ColoredBox(
        color: Colors.white,
        child: Center(child: CircularProgressIndicator()),
      );
    if (unlocked) return widget.child;
    return Material(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 320),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.lock_outline, size: 48),
                const SizedBox(height: 16),
                TextField(
                  controller: pin,
                  obscureText: true,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: 'PIN',
                    errorText: error,
                  ),
                  onSubmitted: (_) => _unlock(),
                ),
                const SizedBox(height: 12),
                FilledButton(onPressed: _unlock, child: const Text('解鎖')),
                TextButton(onPressed: _check, child: const Text('使用生物辨識')),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _unlock() async {
    final ok = await ref.read(appLockProvider).verifyPin(pin.text);
    if (mounted)
      setState(() {
        unlocked = ok;
        error = ok ? null : 'PIN 錯誤';
      });
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;
  static const pages = [
    DashboardPage(),
    TasksPage(),
    CalendarPage(),
    ProjectsPage(),
    MorePage(),
  ];
  static const titles = ['今天', '待辦', '日曆', '專案', '更多'];
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(titles[index])),
    body: IndexedStack(index: index, children: pages),
    bottomNavigationBar: NavigationBar(
      selectedIndex: index,
      onDestinationSelected: (value) => setState(() => index = value),
      destinations: const [
        NavigationDestination(icon: Icon(Icons.home_outlined), label: '首頁'),
        NavigationDestination(
          icon: Icon(Icons.check_circle_outline),
          label: '待辦',
        ),
        NavigationDestination(
          icon: Icon(Icons.calendar_month_outlined),
          label: '日曆',
        ),
        NavigationDestination(icon: Icon(Icons.folder_outlined), label: '專案'),
        NavigationDestination(icon: Icon(Icons.more_horiz), label: '更多'),
      ],
    ),
  );
}

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => ref
      .watch(tasksProvider)
      .when(
        loading: () => const Busy(),
        error: (e, _) => Message('待辦讀取失敗，本機資料仍安全。\n$e'),
        data: (tasks) {
          final sections =
              ref.watch(dashboardSectionsProvider).value ??
              defaultDashboardSections;
          final actions =
              ref.watch(quickActionsProvider).value ?? defaultQuickActions;
          final today = DateUtils.dateOnly(DateTime.now());
          final open =
              tasks
                  .where(
                    (e) =>
                        e.status != ItemStatus.completed &&
                        e.status != ItemStatus.cancelled,
                  )
                  .toList()
                ..sort((a, b) => _score(a, today).compareTo(_score(b, today)));
          final due = open
              .where((e) => DateUtils.isSameDay(e.dueAt, today))
              .length;
          final overdue = open
              .where((e) => e.dueAt?.isBefore(today) ?? false)
              .length;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                DateFormat('M 月 d 日 EEEE', 'zh_TW').format(today),
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    '今天有 ${open.length} 件待處理，$due 件今天到期${overdue > 0 ? '，$overdue 件已逾期' : ''}。',
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (actions.contains('task'))
                    ActionChip(
                      avatar: const Icon(Icons.add_task),
                      label: const Text('待辦'),
                      onPressed: () => editTask(context, ref),
                    ),
                  if (actions.contains('event'))
                    ActionChip(
                      avatar: const Icon(Icons.event),
                      label: const Text('行程'),
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) =>
                              const Scaffold(body: CalendarIntegrationPage()),
                        ),
                      ),
                    ),
                  if (actions.contains('shopping'))
                    ActionChip(
                      avatar: const Icon(Icons.shopping_basket_outlined),
                      label: const Text('採買'),
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const Scaffold(body: ShoppingPage()),
                        ),
                      ),
                    ),
                  if (actions.contains('voice'))
                    ActionChip(
                      avatar: const Icon(Icons.mic),
                      label: const Text('語音'),
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const Scaffold(
                            body: SafeArea(child: QuickCapturePage()),
                          ),
                        ),
                      ),
                    ),
                  if (actions.contains('note'))
                    ActionChip(
                      avatar: const Icon(Icons.note_add_outlined),
                      label: const Text('筆記'),
                      onPressed: () => editNote(context, ref),
                    ),
                  if (actions.contains('project'))
                    ActionChip(
                      avatar: const Icon(Icons.create_new_folder_outlined),
                      label: const Text('專案'),
                      onPressed: () async {
                        final name = await prompt(context, '新增專案', '專案名稱');
                        if (name != null)
                          await ref
                              .read(lifeRepositoryProvider)
                              .saveProject(name: name);
                      },
                    ),
                ],
              ),
              const SizedBox(height: 16),
              if (sections.contains('tasks')) ...[
                Text('優先事項', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                if (open.isEmpty)
                  const Message('今天目前沒有待處理事項')
                else
                  ...open.take(5).map((e) => TaskTile(e)),
              ],
              if (sections.contains('waiting')) ...[
                const SizedBox(height: 12),
                Text('等待中', style: Theme.of(context).textTheme.headlineSmall),
                ...open
                    .where((e) => e.status == ItemStatus.waiting)
                    .take(3)
                    .map(TaskTile.new),
              ],
              if (sections.contains('calendar')) ...[
                const SizedBox(height: 12),
                Text('今日行程', style: Theme.of(context).textTheme.headlineSmall),
                StreamBuilder<List<CalendarSlot>>(
                  stream: ref
                      .read(googleIntegrationProvider)
                      .watchCalendar(today, today.add(const Duration(days: 1))),
                  builder: (_, snap) => Column(
                    children: (snap.data ?? [])
                        .map(
                          (e) => ListTile(
                            leading: const Icon(Icons.event),
                            title: Text(e.title),
                            subtitle: Text(
                              DateFormat('HH:mm').format(e.startsAt),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
              ],
              if (sections.contains('reminders')) ...[
                const SizedBox(height: 12),
                Text('提醒', style: Theme.of(context).textTheme.headlineSmall),
                ...open
                    .where((e) => e.reminderAt != null)
                    .take(3)
                    .map(
                      (e) => ListTile(
                        leading: const Icon(Icons.notifications_outlined),
                        title: Text(e.title),
                        subtitle: Text(
                          DateFormat('M/d HH:mm').format(e.reminderAt!),
                        ),
                      ),
                    ),
              ],
              if (sections.contains('shopping')) ...[
                const SizedBox(height: 12),
                Text('採買', style: Theme.of(context).textTheme.headlineSmall),
                ...(ref.watch(shoppingProvider).value ??
                        const <LifeShoppingList>[])
                    .expand((e) => e.items.where((i) => !i.isDone))
                    .take(3)
                    .map(
                      (e) => ListTile(
                        leading: const Icon(Icons.shopping_basket_outlined),
                        title: Text(e.name),
                        subtitle: e.category == null ? null : Text(e.category!),
                      ),
                    ),
              ],
              if (sections.contains('habits')) ...[
                const SizedBox(height: 12),
                Text('習慣', style: Theme.of(context).textTheme.headlineSmall),
                ...(ref.watch(habitsProvider).value ?? const <LifeHabit>[])
                    .take(3)
                    .map(
                      (e) => ListTile(
                        leading: const Icon(Icons.repeat),
                        title: Text(e.title),
                        trailing: IconButton(
                          icon: const Icon(Icons.check),
                          onPressed: () => ref
                              .read(lifeRepositoryProvider)
                              .completeHabit(e.id),
                        ),
                      ),
                    ),
              ],
              if (sections.contains('projects')) ...[
                const SizedBox(height: 12),
                Text('近期專案', style: Theme.of(context).textTheme.headlineSmall),
                ...(ref.watch(projectsProvider).value ?? const <LifeProject>[])
                    .take(3)
                    .map(
                      (e) => ListTile(
                        leading: const Icon(Icons.folder_outlined),
                        title: Text(e.name),
                        subtitle: Text(e.summary ?? ''),
                      ),
                    ),
              ],
            ],
          );
        },
      );
  int _score(TaskItem item, DateTime today) =>
      (item.dueAt?.isBefore(today) ?? false)
      ? 0
      : DateUtils.isSameDay(item.dueAt, today)
      ? 1
      : item.priority == ItemPriority.high
      ? 2
      : 3;
}

class TasksPage extends ConsumerWidget {
  const TasksPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => _withAdd(
    context,
    ref
        .watch(tasksProvider)
        .when(
          loading: () => const Busy(),
          error: (e, _) => Message('$e'),
          data: (items) => items.isEmpty
              ? const Message('還沒有待辦，先記下一件事吧')
              : ListView(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 88),
                  children: items.map(TaskTile.new).toList(),
                ),
        ),
    () => editTask(context, ref),
  );
}

class TaskTile extends ConsumerWidget {
  const TaskTile(this.task, {super.key});
  final TaskItem task;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Card(
    margin: const EdgeInsets.only(bottom: 8),
    child: ListTile(
      leading: Checkbox(
        value: task.status == ItemStatus.completed,
        onChanged: (v) => ref
            .read(lifeRepositoryProvider)
            .setTaskStatus(
              task.id,
              v == true ? ItemStatus.completed : ItemStatus.pending,
            ),
      ),
      title: Text(
        task.title,
        style: task.status == ItemStatus.completed
            ? const TextStyle(decoration: TextDecoration.lineThrough)
            : null,
      ),
      subtitle: Text(
        [
          if (task.dueAt != null) DateFormat('M/d HH:mm').format(task.dueAt!),
          if (task.priority != ItemPriority.normal) task.priority.name,
        ].join(' · '),
      ),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => TaskDetailPage(task: task)),
      ),
      trailing: IconButton(
        icon: const Icon(Icons.edit_outlined),
        onPressed: () => editTask(context, ref, task),
      ),
    ),
  );
}

class TaskDetailPage extends ConsumerWidget {
  const TaskDetailPage({super.key, required this.task});
  final TaskItem task;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    appBar: AppBar(
      title: Text(task.title),
      actions: [
        IconButton(
          icon: const Icon(Icons.delete_outline),
          onPressed: () async {
            await ref.read(lifeRepositoryProvider).deleteTask(task.id);
            if (context.mounted) Navigator.pop(context);
          },
        ),
      ],
    ),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (task.note?.isNotEmpty == true) Text(task.note!),
        if (task.dueAt != null)
          ListTile(
            leading: const Icon(Icons.event),
            title: Text(DateFormat('yyyy/M/d HH:mm').format(task.dueAt!)),
          ),
        Text('Checklist', style: Theme.of(context).textTheme.headlineSmall),
        ref
            .watch(checklistProvider(task.id))
            .when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text('$e'),
              data: (items) => Column(
                children: [
                  ...items.map(
                    (e) => CheckboxListTile(
                      value: e.isDone,
                      title: Text(e.title),
                      onChanged: (v) => ref
                          .read(lifeRepositoryProvider)
                          .toggleChecklist(e.id, v == true),
                    ),
                  ),
                  ListTile(
                    leading: const Icon(Icons.add),
                    title: const Text('新增 Checklist'),
                    onTap: () async {
                      final value = await prompt(context, '新增 Checklist', '內容');
                      if (value != null)
                        await ref
                            .read(lifeRepositoryProvider)
                            .addChecklist(task.id, value);
                    },
                  ),
                ],
              ),
            ),
        const SizedBox(height: 12),
        Text('標籤', style: Theme.of(context).textTheme.headlineSmall),
        ref
            .watch(taskTagsProvider(task.id))
            .when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text('$e'),
              data: (tags) => Wrap(
                spacing: 8,
                children: tags
                    .map(
                      (e) => FilterChip(
                        label: Text(e.name),
                        selected: e.selected,
                        onSelected: (v) => ref
                            .read(lifeRepositoryProvider)
                            .toggleTag('task', task.id, e.id, v),
                      ),
                    )
                    .toList(),
              ),
            ),
        const SizedBox(height: 12),
        Text('附件', style: Theme.of(context).textTheme.headlineSmall),
        ref
            .watch(taskAttachmentsProvider(task.id))
            .when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text('$e'),
              data: (files) => Column(
                children: [
                  ...files.map(
                    (e) => ListTile(
                      leading: const Icon(Icons.attach_file),
                      title: Text(e.displayName),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete_outline),
                        onPressed: () async {
                          await ref
                              .read(attachmentServiceProvider)
                              .delete(e.localPath);
                          await ref
                              .read(lifeRepositoryProvider)
                              .removeAttachment(e.id);
                        },
                      ),
                    ),
                  ),
                  ListTile(
                    leading: const Icon(Icons.add),
                    title: const Text('加入檔案'),
                    onTap: () async {
                      final file = await ref
                          .read(attachmentServiceProvider)
                          .pickFile();
                      if (file != null)
                        await ref
                            .read(lifeRepositoryProvider)
                            .addAttachment(
                              'task',
                              task.id,
                              file.path.replaceAll('\\', '/').split('/').last,
                              file.path,
                            );
                    },
                  ),
                ],
              ),
            ),
      ],
    ),
  );
}

Future<void> editTask(
  BuildContext context,
  WidgetRef ref, [
  TaskItem? task,
]) async {
  final title = TextEditingController(text: task?.title);
  final note = TextEditingController(text: task?.note);
  ItemPriority priority = task?.priority ?? ItemPriority.normal;
  DateTime? due = task?.dueAt;
  DateTime? reminder = task?.reminderAt;
  String? projectId = task?.projectId;
  final projects = ref.read(projectsProvider).value ?? const <LifeProject>[];
  final save = await showDialog<bool>(
    context: context,
    builder: (_) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: Text(task == null ? '新增待辦' : '編輯待辦'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: title,
                autofocus: true,
                decoration: const InputDecoration(labelText: '標題'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: note,
                maxLines: 3,
                decoration: const InputDecoration(labelText: '備註'),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField(
                initialValue: priority,
                decoration: const InputDecoration(labelText: '優先度'),
                items: ItemPriority.values
                    .map((e) => DropdownMenuItem(value: e, child: Text(e.name)))
                    .toList(),
                onChanged: (v) => setState(() => priority = v!),
              ),
              if (projects.isNotEmpty)
                DropdownButtonFormField<String?>(
                  initialValue: projectId,
                  decoration: const InputDecoration(labelText: '所屬專案'),
                  items: [
                    const DropdownMenuItem<String?>(
                      value: null,
                      child: Text('無'),
                    ),
                    ...projects.map(
                      (e) => DropdownMenuItem<String?>(
                        value: e.id,
                        child: Text(e.name),
                      ),
                    ),
                  ],
                  onChanged: (v) => setState(() => projectId = v),
                ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(
                  due == null ? '設定到期日' : DateFormat('yyyy/M/d').format(due!),
                ),
                trailing: const Icon(Icons.event),
                onTap: () async {
                  final value = await showDatePicker(
                    context: context,
                    firstDate: DateTime(2020),
                    lastDate: DateTime(2100),
                    initialDate: due ?? DateTime.now(),
                  );
                  if (value != null)
                    setState(
                      () => due = DateTime(
                        value.year,
                        value.month,
                        value.day,
                        18,
                      ),
                    );
                },
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(
                  reminder == null
                      ? '設定提醒'
                      : DateFormat('yyyy/M/d HH:mm').format(reminder!),
                ),
                trailing: const Icon(Icons.notifications_outlined),
                onTap: () async {
                  final value = await showDatePicker(
                    context: context,
                    firstDate: DateTime.now(),
                    lastDate: DateTime(2100),
                    initialDate: reminder ?? due ?? DateTime.now(),
                  );
                  if (value != null)
                    setState(
                      () => reminder = DateTime(
                        value.year,
                        value.month,
                        value.day,
                        9,
                      ),
                    );
                },
              ),
            ],
          ),
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
    ),
  );
  if (save == true && title.text.trim().isNotEmpty) {
    final id = await ref
        .read(lifeRepositoryProvider)
        .saveTask(
          id: task?.id,
          title: title.text,
          note: note.text,
          priority: priority,
          dueAt: due,
          reminderAt: reminder,
          projectId: projectId,
        );
    if (reminder != null) {
      final notifications = ref.read(notificationProvider);
      await notifications.initialize();
      await notifications.schedule(
        id: id.hashCode & 0x7fffffff,
        title: title.text.trim(),
        body: note.text.trim().isEmpty ? '待辦提醒' : note.text.trim(),
        at: reminder!,
      );
    }
  }
}

class ProjectsPage extends ConsumerWidget {
  const ProjectsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => _withAdd(
    context,
    ref
        .watch(projectsProvider)
        .when(
          loading: () => const Busy(),
          error: (e, _) => Message('$e'),
          data: (items) => items.isEmpty
              ? const Message('這個專案區還是空的')
              : ListView(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 88),
                  children: items
                      .map(
                        (e) => Card(
                          child: ListTile(
                            title: Text(e.name),
                            subtitle: Text(e.summary ?? '尚無摘要'),
                            onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => ProjectDetailPage(project: e),
                              ),
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
        ),
    () async {
      final name = await prompt(context, '新增專案', '專案名稱');
      if (name != null)
        await ref.read(lifeRepositoryProvider).saveProject(name: name);
    },
  );
}

class ProjectDetailPage extends ConsumerWidget {
  const ProjectDetailPage({super.key, required this.project});
  final LifeProject project;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasks =
            ref
                .watch(tasksProvider)
                .value
                ?.where((e) => e.projectId == project.id)
                .toList() ??
            [],
        notes =
            ref
                .watch(notesProvider)
                .value
                ?.where((e) => e.projectId == project.id)
                .toList() ??
            [],
        activity =
            ref
                .watch(activityProvider)
                .value
                ?.where(
                  (e) =>
                      e.entityId == project.id ||
                      tasks.any((t) => t.id == e.entityId) ||
                      notes.any((n) => n.id == e.entityId),
                )
                .toList() ??
            [];
    final now = DateTime.now();
    return Scaffold(
      appBar: AppBar(
        title: Text(project.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text('刪除專案？'),
                  content: const Text('此操作需要確認；已連結的待辦與筆記不會自動刪除。'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('取消'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('刪除'),
                    ),
                  ],
                ),
              );
              if (ok == true) {
                await ref
                    .read(lifeRepositoryProvider)
                    .deleteProject(project.id);
                if (context.mounted) Navigator.pop(context);
              }
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(project.summary ?? '尚無摘要'),
          const SizedBox(height: 16),
          Text('待辦', style: Theme.of(context).textTheme.headlineSmall),
          if (tasks.isEmpty)
            const ListTile(title: Text('這個專案還沒有待辦'))
          else
            ...tasks.map(TaskTile.new),
          Text('行程', style: Theme.of(context).textTheme.headlineSmall),
          StreamBuilder<List<CalendarSlot>>(
            stream: ref
                .read(googleIntegrationProvider)
                .watchCalendar(
                  now.subtract(const Duration(days: 365)),
                  now.add(const Duration(days: 365)),
                ),
            builder: (_, snap) {
              final all = snap.data ?? [],
                  linked = all.where((e) => e.projectId == project.id).toList();
              return Column(
                children: [
                  ...linked.map(
                    (e) => ListTile(
                      leading: const Icon(Icons.event),
                      title: Text(e.title),
                      subtitle: Text(
                        DateFormat('yyyy/M/d HH:mm').format(e.startsAt),
                      ),
                    ),
                  ),
                  ListTile(
                    leading: const Icon(Icons.add),
                    title: const Text('掛入既有行程'),
                    onTap: () async {
                      final event = await showDialog<CalendarSlot>(
                        context: context,
                        builder: (_) => SimpleDialog(
                          title: const Text('選擇行程'),
                          children: all
                              .map(
                                (e) => SimpleDialogOption(
                                  onPressed: () => Navigator.pop(context, e),
                                  child: Text(e.title),
                                ),
                              )
                              .toList(),
                        ),
                      );
                      if (event != null)
                        await ref
                            .read(googleIntegrationProvider)
                            .linkEventToProject(event.id, project.id);
                    },
                  ),
                ],
              );
            },
          ),
          Text('筆記', style: Theme.of(context).textTheme.headlineSmall),
          ...notes.map(
            (e) => ListTile(
              title: Text(e.title.isEmpty ? '未命名筆記' : e.title),
              onTap: () => editNote(context, ref, e),
            ),
          ),
          Text('相關 Gmail', style: Theme.of(context).textTheme.headlineSmall),
          StreamBuilder<List<GmailSummary>>(
            stream: ref.read(googleIntegrationProvider).watchGmail(),
            builder: (_, snap) => Column(
              children: (snap.data ?? [])
                  .where((e) => e.linkedEntityId == project.id)
                  .map(
                    (e) => ListTile(
                      leading: const Icon(Icons.mail_outline),
                      title: Text(e.subject),
                      subtitle: Text(e.sender),
                    ),
                  )
                  .toList(),
            ),
          ),
          Text('附件', style: Theme.of(context).textTheme.headlineSmall),
          StreamBuilder<List<LifeAttachment>>(
            stream: ref
                .read(lifeRepositoryProvider)
                .watchAttachments('project', project.id),
            builder: (_, snap) => Column(
              children: [
                ...(snap.data ?? []).map(
                  (e) => ListTile(
                    leading: const Icon(Icons.attach_file),
                    title: Text(e.displayName),
                  ),
                ),
                ListTile(
                  leading: const Icon(Icons.add),
                  title: const Text('加入附件'),
                  onTap: () async {
                    final file = await ref
                        .read(attachmentServiceProvider)
                        .pickFile();
                    if (file != null)
                      await ref
                          .read(lifeRepositoryProvider)
                          .addAttachment(
                            'project',
                            project.id,
                            file.path.replaceAll('\\', '/').split('/').last,
                            file.path,
                          );
                  },
                ),
              ],
            ),
          ),
          Text('最近活動', style: Theme.of(context).textTheme.headlineSmall),
          ...activity
              .take(10)
              .map(
                (e) => ListTile(
                  leading: const Icon(Icons.history),
                  title: Text(e.summary),
                  subtitle: Text(DateFormat('M/d HH:mm').format(e.createdAt)),
                ),
              ),
        ],
      ),
    );
  }
}

class CalendarPage extends StatelessWidget {
  const CalendarPage({super.key});
  @override
  Widget build(BuildContext context) => const CalendarIntegrationPage();
}

class MorePage extends StatelessWidget {
  const MorePage({super.key});
  @override
  Widget build(BuildContext context) => ListView(
    children: [
      _link(context, Icons.search, '搜尋', const SearchPage()),
      _link(
        context,
        Icons.fact_check_outlined,
        '每日回顧',
        const DailyReviewPage(),
      ),
      _link(context, Icons.timeline_outlined, '長期視圖', const LongTermPage()),
      _link(context, Icons.bolt, '快速輸入 / 語音', const QuickCapturePage()),
      _link(context, Icons.mail_outline, 'Gmail', const GmailPage()),
      _link(context, Icons.note_outlined, '筆記 / Markdown', const NotesPage()),
      _link(context, Icons.repeat, '習慣', const HabitsPage()),
      _link(
        context,
        Icons.shopping_basket_outlined,
        '採買',
        const ShoppingPage(),
      ),
      _link(context, Icons.history, 'Activity Log', const ActivityPage()),
      _link(
        context,
        Icons.dashboard_customize_outlined,
        '範本',
        const TemplatesPage(),
      ),
      _link(context, Icons.label_outline, '標籤', const TagManagerPage()),
      _link(context, Icons.attach_file, '附件 / 掃描', const AttachmentPage()),
      _link(context, Icons.settings_outlined, '設定', const SettingsPage()),
    ],
  );
  Widget _link(
    BuildContext context,
    IconData icon,
    String title,
    Widget page,
  ) => ListTile(
    leading: Icon(icon),
    title: Text(title),
    trailing: const Icon(Icons.chevron_right),
    onTap: () => Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(title)),
          body: page,
        ),
      ),
    ),
  );
}

class NotesPage extends ConsumerWidget {
  const NotesPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => _withAdd(
    context,
    ref
        .watch(notesProvider)
        .when(
          loading: () => const Busy(),
          error: (e, _) => Message('$e'),
          data: (items) => items.isEmpty
              ? const Message('尚未建立任何筆記')
              : ListView(
                  children: items
                      .map(
                        (e) => ListTile(
                          title: Text(e.title.isEmpty ? '未命名筆記' : e.title),
                          subtitle: Text(
                            e.body,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          onTap: () => editNote(context, ref, e),
                        ),
                      )
                      .toList(),
                ),
        ),
    () => editNote(context, ref),
  );
}

Future<void> editNote(
  BuildContext context,
  WidgetRef ref, [
  LifeNote? note,
]) async {
  await Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => NoteEditorPage(note: note)),
  );
}

class NoteEditorPage extends ConsumerStatefulWidget {
  const NoteEditorPage({super.key, this.note});
  final LifeNote? note;
  @override
  ConsumerState<NoteEditorPage> createState() => _NoteEditorState();
}

class _NoteEditorState extends ConsumerState<NoteEditorPage> {
  late final title = TextEditingController(text: widget.note?.title),
      body = TextEditingController(text: widget.note?.body);
  Timer? timer;
  bool preview = false;
  late String? noteId = widget.note?.id, projectId = widget.note?.projectId;
  @override
  void initState() {
    super.initState();
    title.addListener(queueSave);
    body.addListener(queueSave);
  }

  void queueSave() {
    timer?.cancel();
    timer = Timer(const Duration(milliseconds: 600), save);
    setState(() {});
  }

  Future<void> save() async {
    noteId = await ref
        .read(lifeRepositoryProvider)
        .saveNote(
          id: noteId,
          title: title.text,
          body: body.text,
          projectId: projectId,
        );
    if (mounted) setState(() {});
  }

  void insert(String before, [String after = '']) {
    final selection = body.selection,
        start = selection.start < 0 ? body.text.length : selection.start,
        end = selection.end < 0 ? start : selection.end;
    final selected = body.text.substring(start, end);
    body.value = TextEditingValue(
      text: body.text.replaceRange(start, end, '$before$selected$after'),
      selection: TextSelection.collapsed(
        offset: start + before.length + selected.length,
      ),
    );
  }

  Future<void> linkNote() async {
    await save();
    final candidates = (ref.read(notesProvider).value ?? [])
        .where((e) => e.id != noteId)
        .toList();
    if (!mounted || candidates.isEmpty) return;
    final target = await showDialog<LifeNote>(
      context: context,
      builder: (_) => SimpleDialog(
        title: const Text('連結相關筆記'),
        children: candidates
            .map(
              (e) => SimpleDialogOption(
                onPressed: () => Navigator.pop(context, e),
                child: Text(e.title.isEmpty ? '未命名筆記' : e.title),
              ),
            )
            .toList(),
      ),
    );
    if (target != null)
      await ref.read(lifeRepositoryProvider).linkNotes(noteId!, target.id);
  }

  @override
  void dispose() {
    timer?.cancel();
    save();
    title.dispose();
    body.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final projects = ref.watch(projectsProvider).value ?? const <LifeProject>[];
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: title,
          decoration: const InputDecoration(
            hintText: '筆記標題',
            border: InputBorder.none,
          ),
        ),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'task')
                await ref
                    .read(lifeRepositoryProvider)
                    .saveTask(
                      title: title.text.isEmpty ? '處理筆記' : title.text,
                      note: body.text,
                      projectId: projectId,
                    );
              if (value == 'calendar') {
                final start = DateTime.now().add(const Duration(days: 1));
                await ref
                    .read(googleIntegrationProvider)
                    .createEvent(
                      title.text.isEmpty ? '筆記事項' : title.text,
                      start,
                      start.add(const Duration(hours: 1)),
                    );
              }
              if (value == 'link') await linkNote();
              if (value == 'delete' && noteId != null) {
                await ref.read(lifeRepositoryProvider).deleteNote(noteId!);
                if (mounted) Navigator.pop(context);
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'task', child: Text('轉成待辦')),
              PopupMenuItem(value: 'calendar', child: Text('轉成行程')),
              PopupMenuItem(value: 'link', child: Text('連結相關筆記')),
              PopupMenuItem(value: 'delete', child: Text('刪除筆記')),
            ],
          ),
          IconButton(
            icon: Icon(preview ? Icons.edit : Icons.visibility),
            onPressed: () => setState(() => preview = !preview),
          ),
          IconButton(icon: const Icon(Icons.save), onPressed: save),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18),
            child: DropdownButtonFormField<String?>(
              initialValue: projectId,
              decoration: const InputDecoration(labelText: '所屬專案'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('無')),
                ...projects.map(
                  (e) => DropdownMenuItem<String?>(
                    value: e.id,
                    child: Text(e.name),
                  ),
                ),
              ],
              onChanged: (v) {
                projectId = v;
                queueSave();
              },
            ),
          ),
          Expanded(
            child: preview
                ? Markdown(
                    data: body.text,
                    padding: const EdgeInsets.all(20),
                    selectable: true,
                  )
                : Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 18),
                    child: TextField(
                      controller: body,
                      maxLines: null,
                      expands: true,
                      textAlignVertical: TextAlignVertical.top,
                      decoration: const InputDecoration(
                        hintText: '使用 Markdown 記錄…',
                        border: InputBorder.none,
                      ),
                    ),
                  ),
          ),
          if (noteId != null)
            ExpansionTile(
              title: const Text('標籤、附件與連結'),
              children: [
                ref
                    .watch(noteTagsProvider(noteId!))
                    .when(
                      loading: () => const LinearProgressIndicator(),
                      error: (e, _) => Text('$e'),
                      data: (tags) => Wrap(
                        spacing: 8,
                        children: tags
                            .map(
                              (e) => FilterChip(
                                label: Text(e.name),
                                selected: e.selected,
                                onSelected: (v) => ref
                                    .read(lifeRepositoryProvider)
                                    .toggleTag('note', noteId!, e.id, v),
                              ),
                            )
                            .toList(),
                      ),
                    ),
                ref
                    .watch(noteAttachmentsProvider(noteId!))
                    .when(
                      loading: () => const LinearProgressIndicator(),
                      error: (e, _) => Text('$e'),
                      data: (files) => Column(
                        children: [
                          ...files.map(
                            (e) => ListTile(
                              leading: const Icon(Icons.attach_file),
                              title: Text(e.displayName),
                            ),
                          ),
                          ListTile(
                            leading: const Icon(Icons.add),
                            title: const Text('加入附件'),
                            onTap: () async {
                              final file = await ref
                                  .read(attachmentServiceProvider)
                                  .pickFile();
                              if (file != null)
                                await ref
                                    .read(lifeRepositoryProvider)
                                    .addAttachment(
                                      'note',
                                      noteId!,
                                      file.path
                                          .replaceAll('\\', '/')
                                          .split('/')
                                          .last,
                                      file.path,
                                    );
                            },
                          ),
                        ],
                      ),
                    ),
                ref
                    .watch(linkedNotesProvider(noteId!))
                    .when(
                      loading: () => const LinearProgressIndicator(),
                      error: (e, _) => Text('$e'),
                      data: (items) => Column(
                        children: items
                            .map(
                              (e) => ListTile(
                                leading: const Icon(Icons.link),
                                title: Text(
                                  e.title.isEmpty ? '未命名筆記' : e.title,
                                ),
                                onTap: () => editNote(context, ref, e),
                              ),
                            )
                            .toList(),
                      ),
                    ),
              ],
            ),
          if (!preview)
            SafeArea(
              top: false,
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (final item in const [
                      ('H1', '# ', ''),
                      ('B', '**', '**'),
                      ('I', '_', '_'),
                      ('•', '- ', ''),
                      ('1.', '1. ', ''),
                      ('☑', '- [ ] ', ''),
                      ('❝', '> ', ''),
                      ('<>', '`', '`'),
                      ('—', '\n---\n', ''),
                    ])
                      TextButton(
                        onPressed: () => insert(item.$2, item.$3),
                        child: Text(item.$1),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class HabitsPage extends ConsumerWidget {
  const HabitsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => _withAdd(
    context,
    ref
        .watch(habitsProvider)
        .when(
          loading: () => const Busy(),
          error: (e, _) => Message('$e'),
          data: (items) => items.isEmpty
              ? const Message('還沒有習慣')
              : ListView(
                  children: items
                      .map(
                        (e) => ListTile(
                          title: Text(e.title),
                          subtitle: Text(e.recurrenceRule),
                          onTap: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => HabitDetailPage(habit: e),
                            ),
                          ),
                          trailing: IconButton(
                            icon: const Icon(Icons.check),
                            onPressed: () => ref
                                .read(lifeRepositoryProvider)
                                .completeHabit(e.id),
                          ),
                        ),
                      )
                      .toList(),
                ),
        ),
    () => _newHabit(context, ref),
  );
}

Future<void> _newHabit(BuildContext context, WidgetRef ref) async {
  final name = TextEditingController();
  var recurrence = 'daily';
  TimeOfDay? reminder;
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('新增習慣'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: '名稱'),
            ),
            DropdownButtonFormField(
              initialValue: recurrence,
              decoration: const InputDecoration(labelText: '重複'),
              items: const [
                DropdownMenuItem(value: 'daily', child: Text('每天')),
                DropdownMenuItem(value: 'weekly', child: Text('每週')),
                DropdownMenuItem(
                  value: 'weekdays:1,2,3,4,5',
                  child: Text('週一至週五'),
                ),
                DropdownMenuItem(value: 'weekdays:6,7', child: Text('週末')),
              ],
              onChanged: (v) => setState(() => recurrence = v!),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(
                reminder == null ? '提醒時間（選填）' : reminder!.format(context),
              ),
              trailing: const Icon(Icons.alarm),
              onTap: () async {
                final value = await showTimePicker(
                  context: context,
                  initialTime: reminder ?? const TimeOfDay(hour: 8, minute: 0),
                );
                if (value != null) setState(() => reminder = value);
              },
            ),
          ],
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
    ),
  );
  if (ok == true && name.text.trim().isNotEmpty) {
    final value = reminder == null
        ? null
        : '${reminder!.hour.toString().padLeft(2, '0')}:${reminder!.minute.toString().padLeft(2, '0')}';
    await ref
        .read(lifeRepositoryProvider)
        .saveHabit(
          title: name.text,
          recurrenceRule: recurrence,
          reminderTime: value,
        );
    if (reminder != null) {
      final service = ref.read(notificationProvider);
      await service.initialize();
      await service.scheduleDaily(
        id: name.text.hashCode & 0x7fffffff,
        title: name.text.trim(),
        body: '例行事項提醒',
        hour: reminder!.hour,
        minute: reminder!.minute,
      );
    }
  }
}

class HabitDetailPage extends ConsumerWidget {
  const HabitDetailPage({super.key, required this.habit});
  final LifeHabit habit;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    appBar: AppBar(title: Text(habit.title)),
    body: ref
        .watch(habitHistoryProvider(habit.id))
        .when(
          loading: () => const Busy(),
          error: (e, _) => Message('$e'),
          data: (items) => ListView(
            children: [
              ListTile(
                title: const Text('重複規則'),
                subtitle: Text(habit.recurrenceRule),
              ),
              ...items.map(
                (e) => ListTile(
                  leading: const Icon(Icons.check_circle_outline),
                  title: Text(
                    DateFormat('yyyy/M/d HH:mm').format(e.completedAt),
                  ),
                ),
              ),
            ],
          ),
        ),
  );
}

class ShoppingPage extends ConsumerWidget {
  const ShoppingPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => _withAdd(
    context,
    ref
        .watch(shoppingProvider)
        .when(
          loading: () => const Busy(),
          error: (e, _) => Message('$e'),
          data: (lists) => lists.isEmpty
              ? const Message('還沒有採買清單')
              : ListView(
                  children: lists
                      .map(
                        (list) => ExpansionTile(
                          title: Text(list.name),
                          subtitle: list.projectId == null
                              ? null
                              : const Text('已掛到生活專案'),
                          children: [
                            ...list.items.map(
                              (item) => CheckboxListTile(
                                title: Text(item.name),
                                subtitle: item.category == null
                                    ? null
                                    : Text(item.category!),
                                value: item.isDone,
                                onChanged: (v) => ref
                                    .read(lifeRepositoryProvider)
                                    .toggleShoppingItem(item.id, v == true),
                              ),
                            ),
                            ListTile(
                              leading: const Icon(Icons.add),
                              title: const Text('新增品項'),
                              onTap: () =>
                                  _addShoppingItem(context, ref, list.id),
                            ),
                          ],
                        ),
                      )
                      .toList(),
                ),
        ),
    () => _addShoppingList(context, ref),
  );
}

Future<void> _addShoppingList(BuildContext context, WidgetRef ref) async {
  final name = TextEditingController();
  String? projectId;
  final projects = ref.read(projectsProvider).value ?? const <LifeProject>[];
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('新增採買清單'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: '名稱'),
            ),
            DropdownButtonFormField<String?>(
              initialValue: projectId,
              decoration: const InputDecoration(labelText: '所屬專案'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('無')),
                ...projects.map(
                  (e) => DropdownMenuItem<String?>(
                    value: e.id,
                    child: Text(e.name),
                  ),
                ),
              ],
              onChanged: (v) => setState(() => projectId = v),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('建立'),
          ),
        ],
      ),
    ),
  );
  if (ok == true && name.text.trim().isNotEmpty)
    await ref
        .read(lifeRepositoryProvider)
        .addShoppingList(name.text, projectId: projectId);
}

Future<void> _addShoppingItem(
  BuildContext context,
  WidgetRef ref,
  String listId,
) async {
  final name = TextEditingController(), category = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('新增品項'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: name,
            decoration: const InputDecoration(labelText: '名稱'),
          ),
          TextField(
            controller: category,
            decoration: const InputDecoration(labelText: '分類（選填）'),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('取消'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, true),
          child: const Text('加入'),
        ),
      ],
    ),
  );
  if (ok == true && name.text.trim().isNotEmpty)
    await ref
        .read(lifeRepositoryProvider)
        .addShoppingItem(
          listId,
          name.text,
          category: category.text.trim().isEmpty ? null : category.text.trim(),
        );
}

class ActivityPage extends ConsumerWidget {
  const ActivityPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => ref
      .watch(activityProvider)
      .when(
        loading: () => const Busy(),
        error: (e, _) => Message('$e'),
        data: (items) => items.isEmpty
            ? const Message('尚無活動紀錄')
            : ListView(
                children: items
                    .map(
                      (e) => ListTile(
                        leading: const Icon(Icons.history),
                        title: Text(e.summary),
                        subtitle: Text(
                          DateFormat('yyyy/M/d HH:mm').format(e.createdAt),
                        ),
                      ),
                    )
                    .toList(),
              ),
      );
}

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      DropdownButtonFormField(
        initialValue: ref.watch(themeModeProvider),
        decoration: const InputDecoration(labelText: '主題'),
        items: const [
          DropdownMenuItem(value: AppThemeChoice.system, child: Text('跟隨系統')),
          DropdownMenuItem(value: AppThemeChoice.warm, child: Text('溫暖手帳')),
          DropdownMenuItem(value: AppThemeChoice.clean, child: Text('極簡清爽')),
          DropdownMenuItem(value: AppThemeChoice.dark, child: Text('深色夜間')),
        ],
        onChanged: (v) async {
          if (v == null) return;
          ref.read(themeModeProvider.notifier).state = v;
          await ref.read(appPreferencesProvider).setString('theme', v.name);
        },
      ),
      _setting(
        context,
        Icons.dashboard_customize_outlined,
        '首頁區塊與快捷',
        const DashboardSettingsPage(),
      ),
      _setting(
        context,
        Icons.account_circle_outlined,
        'Google 連線',
        const GoogleConnectionPage(),
      ),
      _setting(
        context,
        Icons.hub_outlined,
        'ChatGPT Drive Bridge',
        const BridgePage(),
      ),
      _setting(
        context,
        Icons.sync,
        'Markdown Folder Sync',
        const FolderSyncPage(),
      ),
      _setting(
        context,
        Icons.notifications_outlined,
        '通知',
        const NotificationPage(),
      ),
      _setting(context, Icons.lock_outline, 'App Lock', const SecurityPage()),
      _setting(context, Icons.backup_outlined, '備份與匯出', const BackupPage()),
      const ListTile(
        title: Text('隱私'),
        subtitle: Text('資料以本機 SQLite 為主；Google 僅在使用整合功能時授權。'),
      ),
      const ListTile(title: Text('版本'), subtitle: Text('0.1.0+1')),
    ],
  );
  Widget _setting(
    BuildContext context,
    IconData icon,
    String title,
    Widget page,
  ) => ListTile(
    leading: Icon(icon),
    title: Text(title),
    trailing: const Icon(Icons.chevron_right),
    onTap: () => Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(title)),
          body: page,
        ),
      ),
    ),
  );
}

Widget _withAdd(BuildContext context, Widget child, VoidCallback add) => Stack(
  children: [
    child,
    Positioned(
      right: 16,
      bottom: 16,
      child: FloatingActionButton(onPressed: add, child: const Icon(Icons.add)),
    ),
  ],
);

class Busy extends StatelessWidget {
  const Busy({super.key});
  @override
  Widget build(BuildContext context) =>
      const Center(child: CircularProgressIndicator());
}

class Message extends StatelessWidget {
  const Message(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Text(text, textAlign: TextAlign.center),
    ),
  );
}

Future<String?> prompt(BuildContext context, String title, String label) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: c,
        autofocus: true,
        decoration: InputDecoration(labelText: label),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('取消'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, true),
          child: const Text('確認'),
        ),
      ],
    ),
  );
  final value = c.text.trim();
  return ok == true && value.isNotEmpty ? value : null;
}
