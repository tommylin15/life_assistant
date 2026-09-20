import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:share_plus/share_plus.dart';

import '../data/folder_sync_engine.dart';
import '../domain/models.dart';
import 'providers.dart';

class SearchPage extends ConsumerStatefulWidget {
  const SearchPage({super.key});
  @override
  ConsumerState<SearchPage> createState() => _SearchState();
}

class _SearchState extends ConsumerState<SearchPage> {
  final query = TextEditingController();
  Future<List<SearchHit>>? results;
  @override
  Widget build(BuildContext context) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: TextField(
          controller: query,
          autofocus: true,
          decoration: InputDecoration(
            labelText: '搜尋待辦、專案、筆記、行程',
            suffixIcon: IconButton(
              icon: const Icon(Icons.search),
              onPressed: () => setState(
                () => results = ref
                    .read(lifeRepositoryProvider)
                    .search(query.text),
              ),
            ),
          ),
        ),
      ),
      Expanded(
        child: FutureBuilder<List<SearchHit>>(
          future: results,
          builder: (_, snap) => ListView(
            children: (snap.data ?? [])
                .map(
                  (e) => ListTile(
                    leading: Icon(
                      e.type == 'task'
                          ? Icons.check_circle_outline
                          : e.type == 'project'
                          ? Icons.folder_outlined
                          : e.type == 'calendar'
                          ? Icons.event
                          : Icons.note_outlined,
                    ),
                    title: Text(e.title),
                    subtitle: Text(e.snippet ?? '', maxLines: 2),
                  ),
                )
                .toList(),
          ),
        ),
      ),
    ],
  );
}

class DailyReviewPage extends ConsumerWidget {
  const DailyReviewPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => ref
      .watch(tasksProvider)
      .when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (items) {
          final today = DateUtils.dateOnly(DateTime.now()),
              completed = items.where(
                (e) =>
                    e.completedAt != null &&
                    DateUtils.isSameDay(e.completedAt, today),
              ),
              open = items.where(
                (e) =>
                    e.status != ItemStatus.completed &&
                    (e.dueAt == null ||
                        !e.dueAt!.isAfter(today.add(const Duration(days: 1)))),
              );
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('今天完成', style: Theme.of(context).textTheme.headlineSmall),
              if (completed.isEmpty)
                const ListTile(title: Text('今天還沒有完成紀錄'))
              else
                ...completed.map(
                  (e) => ListTile(
                    leading: const Icon(Icons.check),
                    title: Text(e.title),
                  ),
                ),
              const SizedBox(height: 16),
              Text('未完成', style: Theme.of(context).textTheme.headlineSmall),
              ...open.map(
                (e) => ListTile(
                  title: Text(e.title),
                  trailing: TextButton(
                    onPressed: () async {
                      final tomorrow = today.add(const Duration(days: 1));
                      await ref
                          .read(lifeRepositoryProvider)
                          .saveTask(
                            id: e.id,
                            title: e.title,
                            note: e.note,
                            priority: e.priority,
                            dueAt: DateTime(
                              tomorrow.year,
                              tomorrow.month,
                              tomorrow.day,
                              18,
                            ),
                            projectId: e.projectId,
                          );
                    },
                    child: const Text('延到明天'),
                  ),
                ),
              ),
            ],
          );
        },
      );
}

class LongTermPage extends ConsumerWidget {
  const LongTermPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cutoff = DateTime.now().add(const Duration(days: 30)),
        tasks = (ref.watch(tasksProvider).value ?? const <TaskItem>[])
            .where(
              (e) =>
                  e.status != ItemStatus.completed &&
                  (e.dueAt == null || e.dueAt!.isAfter(cutoff)),
            )
            .toList(),
        projects = ref.watch(projectsProvider).value ?? const <LifeProject>[];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('進行中專案', style: Theme.of(context).textTheme.headlineSmall),
        ...projects
            .where((e) => e.status == 'active')
            .map(
              (e) => ListTile(
                leading: const Icon(Icons.folder_outlined),
                title: Text(e.name),
                subtitle: Text(e.summary ?? ''),
              ),
            ),
        const SizedBox(height: 16),
        Text('30 天後與未排期', style: Theme.of(context).textTheme.headlineSmall),
        if (tasks.isEmpty)
          const ListTile(title: Text('沒有長期待辦'))
        else
          ...tasks.map(
            (e) => ListTile(
              leading: const Icon(Icons.schedule),
              title: Text(e.title),
              subtitle: Text(
                e.dueAt == null ? '未排期' : e.dueAt!.toLocal().toString(),
              ),
            ),
          ),
      ],
    );
  }
}

class DashboardSettingsPage extends ConsumerWidget {
  const DashboardSettingsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected =
            ref.watch(dashboardSectionsProvider).value ??
            defaultDashboardSections,
        actions = ref.watch(quickActionsProvider).value ?? defaultQuickActions;
    const labels = {
          'tasks': '待辦',
          'calendar': '行程',
          'reminders': '提醒',
          'waiting': '等待中',
          'shopping': '採買',
          'habits': '習慣',
          'projects': '近期專案',
        },
        actionLabels = {
          'task': '新增待辦',
          'event': '新增行程',
          'shopping': '新增採買',
          'voice': '語音輸入',
          'note': '新增筆記',
          'project': '新增專案',
        };
    Future<void> save(String key, List<String> values, dynamic provider) async {
      await ref.read(appPreferencesProvider).setList(key, values);
      ref.invalidate(provider);
    }

    Widget row(
      String key,
      String label,
      List<String> values,
      String pref,
      dynamic provider,
    ) {
      final enabled = values.contains(key), index = values.indexOf(key);
      return SwitchListTile(
        title: Text(label),
        subtitle: enabled ? Text('順序 ${index + 1}') : null,
        secondary: enabled && index > 0
            ? IconButton(
                icon: const Icon(Icons.arrow_upward),
                onPressed: () {
                  final next = [...values], item = next.removeAt(index);
                  next.insert(index - 1, item);
                  save(pref, next, provider);
                },
              )
            : null,
        value: enabled,
        onChanged: (value) {
          final next = [...values];
          value ? next.add(key) : next.remove(key);
          save(pref, next, provider);
        },
      );
    }

    return ListView(
      children: [
        const ListTile(title: Text('首頁區塊（箭頭可調整順序）')),
        ...[
          ...selected,
          ...labels.keys.where((e) => !selected.contains(e)),
        ].map(
          (key) => row(
            key,
            labels[key]!,
            selected,
            'dashboard_sections',
            dashboardSectionsProvider,
          ),
        ),
        const Divider(),
        const ListTile(title: Text('快捷列（箭頭可調整順序）')),
        ...[
          ...actions,
          ...actionLabels.keys.where((e) => !actions.contains(e)),
        ].map(
          (key) => row(
            key,
            actionLabels[key]!,
            actions,
            'quick_actions',
            quickActionsProvider,
          ),
        ),
      ],
    );
  }
}

class CalendarIntegrationPage extends ConsumerStatefulWidget {
  const CalendarIntegrationPage({super.key});
  @override
  ConsumerState<CalendarIntegrationPage> createState() => _CalendarState();
}

class _CalendarState extends ConsumerState<CalendarIntegrationPage> {
  String? error;
  int days = 7;
  Future<void> load() async {
    final now = DateTime.now();
    try {
      await ref
          .read(googleIntegrationProvider)
          .syncCalendar(
            now.subtract(const Duration(days: 30)),
            now.add(const Duration(days: 90)),
          );
      error = null;
    } catch (e) {
      error = '$e';
    }
    if (mounted) setState(() {});
  }

  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now(),
        start = DateUtils.dateOnly(now),
        end = start.add(Duration(days: days));
    return Scaffold(
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 7, label: Text('週')),
                ButtonSegment(value: 42, label: Text('月')),
              ],
              selected: {days},
              onSelectionChanged: (v) => setState(() => days = v.first),
            ),
          ),
          if (error != null)
            MaterialBanner(
              content: Text('Calendar 同步失敗，本機快照仍可用：$error'),
              actions: [TextButton(onPressed: load, child: const Text('重試'))],
            ),
          Expanded(
            child: StreamBuilder<List<CalendarSlot>>(
              stream: ref
                  .read(googleIntegrationProvider)
                  .watchCalendar(start, end),
              builder: (_, snap) {
                final items = snap.data ?? [];
                return RefreshIndicator(
                  onRefresh: load,
                  child: items.isEmpty
                      ? ListView(
                          children: const [
                            SizedBox(height: 240),
                            Center(child: Text('這段期間沒有行程')),
                          ],
                        )
                      : ListView(
                          children: items.map((e) {
                            final conflict = items.any(
                              (other) =>
                                  other.id != e.id &&
                                  e.startsAt.isBefore(other.endsAt) &&
                                  e.endsAt.isAfter(other.startsAt),
                            );
                            return ListTile(
                              leading: Icon(
                                conflict ? Icons.warning_amber : Icons.event,
                                color: conflict
                                    ? Theme.of(context).colorScheme.error
                                    : null,
                              ),
                              title: Text(e.title),
                              subtitle: Text(
                                '${e.startsAt.month}/${e.startsAt.day} ${TimeOfDay.fromDateTime(e.startsAt).format(context)}–${TimeOfDay.fromDateTime(e.endsAt).format(context)}${conflict ? ' · 時間重疊' : ''}',
                              ),
                              onTap: () async {
                                final title = await _prompt(context, '修改行程名稱');
                                if (title != null)
                                  await ref
                                      .read(googleIntegrationProvider)
                                      .updateEvent(
                                        e,
                                        title,
                                        e.startsAt,
                                        e.endsAt,
                                      );
                              },
                              trailing: IconButton(
                                icon: const Icon(Icons.delete_outline),
                                onPressed: () => ref
                                    .read(googleIntegrationProvider)
                                    .deleteEvent(e.googleEventId),
                              ),
                            );
                          }).toList(),
                        ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final title = await _prompt(context, '新增行程');
          if (title == null) return;
          final start = DateTime.now().add(const Duration(hours: 1));
          await ref
              .read(googleIntegrationProvider)
              .createEvent(title, start, start.add(const Duration(hours: 1)));
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

class GmailPage extends ConsumerStatefulWidget {
  const GmailPage({super.key});
  @override
  ConsumerState<GmailPage> createState() => _GmailState();
}

class _GmailState extends ConsumerState<GmailPage> {
  String? error;
  Future<void> load() async {
    try {
      await ref.read(googleIntegrationProvider).syncGmail();
      error = null;
    } catch (e) {
      error = '$e';
    }
    if (mounted) setState(() {});
  }

  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      if (error != null)
        MaterialBanner(
          content: Text('Gmail 同步失敗，本機資料仍安全：$error'),
          actions: [TextButton(onPressed: load, child: const Text('重試'))],
        ),
      Expanded(
        child: StreamBuilder<List<GmailSummary>>(
          stream: ref.read(googleIntegrationProvider).watchGmail(),
          builder: (_, snap) => RefreshIndicator(
            onRefresh: load,
            child: ListView(
              children: (snap.data ?? [])
                  .map(
                    (m) => ListTile(
                      title: Text(m.subject.isEmpty ? '(無主旨)' : m.subject),
                      subtitle: Text(
                        '${m.sender}\n${m.snippet ?? ''}${m.linkedEntityId == null ? '' : '\n已掛到專案'}',
                        maxLines: 4,
                      ),
                      trailing: PopupMenuButton<String>(
                        onSelected: (value) async {
                          if (value == 'task')
                            await ref
                                .read(googleIntegrationProvider)
                                .gmailToTask(m);
                          if (value == 'calendar')
                            await ref
                                .read(googleIntegrationProvider)
                                .gmailToCalendar(
                                  m,
                                  DateTime.now().add(const Duration(days: 1)),
                                );
                          if (value == 'project') {
                            final projects =
                                ref.read(projectsProvider).value ??
                                const <LifeProject>[];
                            if (!mounted || projects.isEmpty) return;
                            final project = await showDialog<LifeProject>(
                              context: context,
                              builder: (_) => SimpleDialog(
                                title: const Text('掛到生活專案'),
                                children: projects
                                    .map(
                                      (p) => SimpleDialogOption(
                                        onPressed: () =>
                                            Navigator.pop(context, p),
                                        child: Text(p.name),
                                      ),
                                    )
                                    .toList(),
                              ),
                            );
                            if (project != null)
                              await ref
                                  .read(googleIntegrationProvider)
                                  .linkGmailToProject(m.id, project.id);
                          }
                        },
                        itemBuilder: (_) => const [
                          PopupMenuItem(value: 'task', child: Text('轉成待辦')),
                          PopupMenuItem(value: 'calendar', child: Text('轉成行程')),
                          PopupMenuItem(value: 'project', child: Text('掛到專案')),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        ),
      ),
    ],
  );
}

class QuickCapturePage extends ConsumerStatefulWidget {
  const QuickCapturePage({super.key});
  @override
  ConsumerState<QuickCapturePage> createState() => _QuickCaptureState();
}

class _QuickCaptureState extends ConsumerState<QuickCapturePage> {
  final controller = TextEditingController();
  bool listening = false;
  Future<void> save() async {
    final parsed = ref.read(quickInputProvider).parse(controller.text);
    if (parsed.title.isEmpty) return;
    await ref
        .read(lifeRepositoryProvider)
        .saveTask(
          title: parsed.title,
          dueAt: parsed.dueAt,
          priority: parsed.priority,
        );
    if (mounted) {
      controller.clear();
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('待辦已建立')));
    }
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      children: [
        TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: '例如：明天下午 3 點重要 繳電費'),
          maxLines: 4,
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: save,
                icon: const Icon(Icons.add_task),
                label: const Text('建立待辦'),
              ),
            ),
            IconButton(
              icon: Icon(listening ? Icons.stop : Icons.mic),
              onPressed: () async {
                final speech = ref.read(speechProvider);
                if (listening) {
                  await speech.stop();
                  setState(() => listening = false);
                } else if (await speech.initialize()) {
                  setState(() => listening = true);
                  await speech.listen((words, done) {
                    setState(() {
                      controller.text = words;
                      listening = !done;
                    });
                  });
                }
              },
            ),
          ],
        ),
      ],
    ),
  );
}

class TemplatesPage extends ConsumerWidget {
  const TemplatesPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    body: ref
        .watch(templatesProvider)
        .when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('$e')),
          data: (items) => ListView(
            children: items
                .map(
                  (t) => ListTile(
                    title: Text(t.name),
                    subtitle: Text(t.type),
                    trailing: const Icon(Icons.play_arrow),
                    onTap: () async {
                      final data =
                          jsonDecode(t.payloadJson) as Map<String, dynamic>;
                      if (t.type == 'task') {
                        final id = await ref
                            .read(lifeRepositoryProvider)
                            .saveTask(title: data['title'] as String);
                        for (final item
                            in (data['checklist'] as List? ?? const [])) {
                          await ref
                              .read(lifeRepositoryProvider)
                              .addChecklist(id, '$item');
                        }
                      } else {
                        await ref
                            .read(lifeRepositoryProvider)
                            .saveProject(name: data['name'] as String);
                      }
                      if (context.mounted)
                        ScaffoldMessenger.of(
                          context,
                        ).showSnackBar(const SnackBar(content: Text('已套用範本')));
                    },
                  ),
                )
                .toList(),
          ),
        ),
    floatingActionButton: FloatingActionButton(
      onPressed: () async {
        final name = await _prompt(context, '自訂範本名稱');
        if (name == null || !context.mounted) return;
        final title = await _prompt(context, '預設待辦標題');
        if (title != null)
          await ref
              .read(lifeRepositoryProvider)
              .saveTemplate(
                name: name,
                type: 'task',
                payloadJson: jsonEncode({'title': title}),
              );
      },
      child: const Icon(Icons.add),
    ),
  );
}

class TagManagerPage extends ConsumerWidget {
  const TagManagerPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    body: StreamBuilder<List<LifeTag>>(
      stream: ref.read(lifeRepositoryProvider).watchTags('none', 'none'),
      builder: (_, snap) => ListView(
        children: (snap.data ?? [])
            .map(
              (e) => ListTile(
                leading: const Icon(Icons.label_outline),
                title: Text(e.name),
              ),
            )
            .toList(),
      ),
    ),
    floatingActionButton: FloatingActionButton(
      onPressed: () async {
        final name = await _prompt(context, '新增標籤');
        if (name != null) await ref.read(lifeRepositoryProvider).addTag(name);
      },
      child: const Icon(Icons.add),
    ),
  );
}

class BridgePage extends ConsumerStatefulWidget {
  const BridgePage({super.key});
  @override
  ConsumerState<BridgePage> createState() => _BridgeState();
}

class _BridgeState extends ConsumerState<BridgePage> {
  String status = '尚未設定';
  bool busy = false;
  Future<void> run(Future<void> Function() action) async {
    setState(() => busy = true);
    try {
      await action();
    } catch (e) {
      status = '$e';
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      const ListTile(
        leading: Icon(Icons.looks_one_outlined),
        title: Text('授權 Google Drive 並建立 Bridge'),
      ),
      const ListTile(
        leading: Icon(Icons.looks_two_outlined),
        title: Text('在 ChatGPT 連接同一個 Google Drive'),
      ),
      const ListTile(
        leading: Icon(Icons.looks_3_outlined),
        title: Text(
          '請 ChatGPT 讀取 bridge_manifest.json，確認 Bridge ID 與 schema 1.0',
        ),
      ),
      Text(status),
      if (busy) const LinearProgressIndicator(),
      FilledButton(
        onPressed: busy
            ? null
            : () => run(() async {
                final folder = await ref
                    .read(bridgeServiceProvider)
                    .setupDrive();
                final id = await ref.read(bridgeServiceProvider).bridgeId();
                status = 'Bridge Ready：$id（Drive folder $folder）';
              }),
        child: const Text('建立 Drive Bridge'),
      ),
      OutlinedButton(
        onPressed: busy
            ? null
            : () => run(() async {
                final instruction = await ref
                    .read(bridgeServiceProvider)
                    .testInstruction();
                await Clipboard.setData(ClipboardData(text: instruction));
                status = 'ChatGPT 測試指令已複製';
              }),
        child: const Text('複製 ChatGPT 測試指令'),
      ),
      OutlinedButton(
        onPressed: busy
            ? null
            : () => run(() async {
                final valid = await ref
                    .read(bridgeServiceProvider)
                    .verifyDriveManifest();
                status = valid
                    ? 'Bridge ID 與 schema 1.0 驗證成功'
                    : 'Bridge 驗證失敗，請重新建立';
              }),
        child: const Text('驗證 Bridge ID / Schema'),
      ),
      OutlinedButton(
        onPressed: busy
            ? null
            : () => run(() async {
                await ref.read(bridgeServiceProvider).exportState();
                status = '狀態、收件匣與專案已匯出';
              }),
        child: const Text('匯出目前狀態'),
      ),
      OutlinedButton(
        onPressed: busy
            ? null
            : () => run(() async {
                final review = await ref
                    .read(bridgeServiceProvider)
                    .readPending();
                if (review == null) {
                  status = '沒有 pending_actions.json';
                  return;
                }
                if (!mounted) return;
                final accepted = await showDialog<bool>(
                  context: context,
                  builder: (_) => AlertDialog(
                    title: Text(
                      '確認 ${review.actions.where((e) => e.valid).length} 個建議動作',
                    ),
                    content: Text(
                      review.actions
                          .map((e) => '${e.type}: ${e.valid ? '可執行' : e.error}')
                          .join('\n'),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('拒絕'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('全部接受'),
                      ),
                    ],
                  ),
                );
                final ids = accepted == true
                    ? review.actions
                          .where((e) => e.valid)
                          .map((e) => e.actionId)
                          .toSet()
                    : <String>{};
                await ref.read(bridgeServiceProvider).executePending(ids);
                status = 'action_results.json 已更新';
              }),
        child: const Text('讀取並審查建議'),
      ),
      OutlinedButton(
        onPressed: () => run(() async {
          final text = await ref.read(bridgeServiceProvider).shareJson();
          await Clipboard.setData(ClipboardData(text: text));
          await SharePlus.instance.share(
            ShareParams(text: text, subject: '生活助理 Share Bridge'),
          );
          status = 'Share Bridge JSON 已複製並開啟分享';
        }),
        child: const Text('分享 Bridge JSON'),
      ),
    ],
  );
}

class FolderSyncPage extends ConsumerStatefulWidget {
  const FolderSyncPage({super.key});
  @override
  ConsumerState<FolderSyncPage> createState() => _SyncState();
}

class _SyncState extends ConsumerState<FolderSyncPage> {
  final driveId = TextEditingController();
  String? driveName;
  String status = '尚未建立同步配對';
  bool busy = false;
  List<SyncConflict> conflicts = const [];
  Future<void> sync() async {
    setState(() => busy = true);
    try {
      final engine = ref.read(folderSyncProvider),
          id = await engine.activePairId();
      if (id == null) throw StateError('尚未建立配對');
      final result = await engine.sync(id);
      conflicts = await engine.conflicts(id);
      status =
          '上傳 ${result.uploaded}、下載 ${result.downloaded}、刪除 ${result.deleted}、衝突 ${result.conflicts}、失敗 ${result.failed}';
    } catch (e) {
      status = '$e';
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> resolve(SyncConflict item, SyncConflictChoice choice) async {
    final engine = ref.read(folderSyncProvider),
        id = await engine.activePairId();
    if (id == null) return;
    await engine.resolveConflict(id, item.path, choice);
    conflicts = await engine.conflicts(id);
    if (mounted) setState(() => status = '已解決 ${item.path}');
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text(status),
      ListTile(leading: const Icon(Icons.cloud_outlined), title: Text(driveName ?? '選擇 Google Drive 資料夾'), subtitle: driveId.text.isEmpty ? null : Text(driveId.text), trailing: const Icon(Icons.chevron_right), onTap: busy ? null : () async { setState(() => busy = true); try { final folders = await ref.read(folderSyncProvider).driveFolders(); if (!mounted) return; final picked = await showDialog<DriveFolderChoice>(context: context, builder: (_) => SimpleDialog(title: const Text('Google Drive 資料夾'), children: folders.map((e) => SimpleDialogOption(onPressed: () => Navigator.pop(context, e), child: Text(e.name))).toList())); if (picked != null) setState(() { driveId.text = picked.id; driveName = picked.name; }); } catch (e) { status = '$e'; } finally { if (mounted) setState(() => busy = false); } }),
      FilledButton(
        onPressed: busy
            ? null
            : () async {
                final path = await FilePicker.platform.getDirectoryPath();
                if (path == null || driveId.text.trim().isEmpty) return;
                setState(() => busy = true);
                try {
                  final id = await ref
                      .read(folderSyncProvider)
                      .createPair(Directory(path), driveId.text.trim());
                  status = '配對已建立：$id';
                } catch (e) {
                  status = '$e';
                } finally {
                  if (mounted) setState(() => busy = false);
                }
              },
        child: const Text('選擇空資料夾並建立配對'),
      ),
      OutlinedButton(onPressed: busy ? null : sync, child: const Text('立即同步')),
      OutlinedButton(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const WorkspacePage()),
        ),
        child: const Text('開啟 Markdown Workspace'),
      ),
      TextButton(onPressed: busy ? null : () async { final engine = ref.read(folderSyncProvider), id = await engine.activePairId(); if (id == null || !mounted) return; final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(title: const Text('移除同步配對？'), content: const Text('不會刪除手機或 Drive 檔案，只會移除同步設定與 snapshot。'), actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('取消')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('移除'))])); if (ok == true) { await engine.removePair(id); setState(() { status = '同步配對已移除，檔案保留'; conflicts = const []; }); } }, child: const Text('移除同步配對')),
      if (busy) const LinearProgressIndicator(),
      if (conflicts.isNotEmpty) ...[
        const Divider(),
        Text('待處理衝突', style: Theme.of(context).textTheme.titleLarge),
        ...conflicts.map(
          (item) => Card(
            child: ExpansionTile(
              title: Text(item.path),
              subtitle: Text(item.isText ? '文字檔，可比較內容' : '二進位檔'),
              children: [
                if (item.isText)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: SelectableText(
                      '本機\n${item.localText ?? '(已刪除)'}\n\nDrive\n${item.driveText ?? '(已刪除)'}',
                    ),
                  ),
                Wrap(
                  children: [
                    TextButton(
                      onPressed: () =>
                          resolve(item, SyncConflictChoice.keepLocal),
                      child: const Text('保留本機'),
                    ),
                    TextButton(
                      onPressed: () =>
                          resolve(item, SyncConflictChoice.keepDrive),
                      child: const Text('保留 Drive'),
                    ),
                    TextButton(
                      onPressed: () =>
                          resolve(item, SyncConflictChoice.keepBoth),
                      child: const Text('兩份都保留'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    ],
  );
}

class WorkspacePage extends ConsumerStatefulWidget {
  const WorkspacePage({super.key});
  @override
  ConsumerState<WorkspacePage> createState() => _WorkspaceState();
}

class _WorkspaceState extends ConsumerState<WorkspacePage> {
  List<String> files = const [];
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final engine = ref.read(folderSyncProvider),
          id = await engine.activePairId();
      if (id == null) throw StateError('尚未建立同步配對');
      files = await engine.workspaceFiles(id);
      error = null;
    } catch (e) {
      error = '$e';
    }
    if (mounted) setState(() {});
  }

  Future<void> create() async {
    var name = await _prompt(context, '新增 Markdown 檔案');
    if (name == null) return;
    if (!name.toLowerCase().endsWith('.md')) name += '.md';
    final engine = ref.read(folderSyncProvider),
        id = await engine.activePairId();
    if (id == null) return;
    await engine.saveWorkspaceFile(
      id,
      name,
      '# ${name.substring(0, name.length - 3)}\n',
    );
    await load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Markdown Workspace')),
    body: error != null
        ? _Error(error!, load)
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              children: files.isEmpty
                  ? const [ListTile(title: Text('尚無 Markdown 檔案'))]
                  : files
                        .map(
                          (path) => ListTile(
                            leading: const Icon(Icons.description_outlined),
                            title: Text(path),
                            onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => WorkspaceEditorPage(path: path),
                              ),
                            ).then((_) => load()),
                          ),
                        )
                        .toList(),
            ),
          ),
    floatingActionButton: FloatingActionButton(
      onPressed: create,
      child: const Icon(Icons.add),
    ),
  );
}

class WorkspaceEditorPage extends ConsumerStatefulWidget {
  const WorkspaceEditorPage({super.key, required this.path});
  final String path;
  @override
  ConsumerState<WorkspaceEditorPage> createState() => _WorkspaceEditorState();
}

class _WorkspaceEditorState extends ConsumerState<WorkspaceEditorPage> {
  final body = TextEditingController();
  bool preview = false, ready = false;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    final engine = ref.read(folderSyncProvider),
        id = await engine.activePairId();
    if (id != null) body.text = await engine.readWorkspaceFile(id, widget.path);
    if (mounted) setState(() => ready = true);
  }

  Future<void> save() async {
    final engine = ref.read(folderSyncProvider),
        id = await engine.activePairId();
    if (id != null) await engine.saveWorkspaceFile(id, widget.path, body.text);
    if (mounted)
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('已儲存，本機有變更')));
  }

  Future<void> remove() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('刪除檔案？'),
        content: Text(widget.path),
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
    if (ok != true) return;
    final engine = ref.read(folderSyncProvider),
        id = await engine.activePairId();
    if (id != null) await engine.deleteWorkspaceFile(id, widget.path);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.path),
      actions: [
        IconButton(
          onPressed: () => setState(() => preview = !preview),
          icon: Icon(preview ? Icons.edit : Icons.visibility),
        ),
        IconButton(onPressed: save, icon: const Icon(Icons.save)),
        IconButton(onPressed: remove, icon: const Icon(Icons.delete_outline)),
      ],
    ),
    body: !ready
        ? const Center(child: CircularProgressIndicator())
        : preview
        ? Markdown(data: body.text, selectable: true)
        : Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: body,
              expands: true,
              maxLines: null,
              textAlignVertical: TextAlignVertical.top,
              decoration: const InputDecoration(border: InputBorder.none),
            ),
          ),
  );
}

class SecurityPage extends ConsumerStatefulWidget {
  const SecurityPage({super.key});
  @override
  ConsumerState<SecurityPage> createState() => _SecurityState();
}

class _SecurityState extends ConsumerState<SecurityPage> {
  String status = '';
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text(status),
      FilledButton(
        onPressed: () async {
          final pin = await _prompt(context, '設定 4–8 位 PIN');
          if (pin == null) return;
          try {
            await ref.read(appLockProvider).setPin(pin);
            setState(() => status = 'PIN 已安全儲存');
          } catch (e) {
            setState(() => status = '$e');
          }
        },
        child: const Text('設定 PIN'),
      ),
      OutlinedButton(
        onPressed: () async {
          final ok = await ref.read(appLockProvider).authenticateBiometric();
          setState(() => status = ok ? '生物辨識成功' : '生物辨識未通過');
        },
        child: const Text('測試生物辨識'),
      ),
      TextButton(
        onPressed: () async {
          await ref.read(appLockProvider).disable();
          setState(() => status = 'App Lock 已關閉');
        },
        child: const Text('關閉 App Lock'),
      ),
    ],
  );
}

class GoogleConnectionPage extends ConsumerStatefulWidget {
  const GoogleConnectionPage({super.key});
  @override
  ConsumerState<GoogleConnectionPage> createState() => _GoogleConnectionState();
}

class _GoogleConnectionState extends ConsumerState<GoogleConnectionPage> {
  bool? connected;
  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    connected = await ref.read(googleProvider).isSignedIn();
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      ListTile(
        leading: Icon(connected == true ? Icons.cloud_done : Icons.cloud_off),
        title: Text(connected == true ? 'Google 已連線' : '尚未連線'),
        subtitle: const Text('Calendar、Gmail、Drive 會在首次使用時分別要求最小權限。'),
      ),
      if (connected == true)
        OutlinedButton(
          onPressed: () async {
            await ref.read(googleProvider).disconnect();
            await refresh();
          },
          child: const Text('撤銷連線'),
        ),
      FilledButton(onPressed: refresh, child: const Text('重新檢查狀態')),
    ],
  );
}

class BackupPage extends ConsumerStatefulWidget {
  const BackupPage({super.key});
  @override
  ConsumerState<BackupPage> createState() => _BackupState();
}

class _BackupState extends ConsumerState<BackupPage> {
  String status = '';
  Future<void> output(String type) async {
    final path = await FilePicker.platform.getDirectoryPath();
    if (path == null) return;
    final service = ref.read(backupProvider);
    final file = switch (type) {
      'db' => await service.backup(Directory(path)),
      'json' => await service.exportJson(Directory(path)),
      _ => await service.exportTasksCsv(Directory(path)),
    };
    setState(() => status = file.path);
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text(status),
      FilledButton(
        onPressed: () => output('db'),
        child: const Text('建立 SQLite 備份'),
      ),
      OutlinedButton(
        onPressed: () => output('json'),
        child: const Text('匯出 JSON'),
      ),
      OutlinedButton(
        onPressed: () => output('csv'),
        child: const Text('匯出 CSV'),
      ),
      OutlinedButton(
        onPressed: () async {
          final picked = await FilePicker.platform.pickFiles(
            type: FileType.custom,
            allowedExtensions: ['db'],
          );
          final path = picked?.files.single.path;
          if (path == null || !context.mounted) return;
          final ok = await showDialog<bool>(
            context: context,
            builder: (_) => AlertDialog(
              title: const Text('確認還原備份？'),
              content: const Text('下次啟動會以此備份取代目前資料庫；目前資料庫會保留為 pre_restore 備份。'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('取消'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('確認還原'),
                ),
              ],
            ),
          );
          if (ok == true) {
            await ref.read(backupProvider).stageRestore(File(path));
            setState(() => status = '還原已排程，重新啟動後套用');
          }
        },
        child: const Text('選擇備份並還原'),
      ),
    ],
  );
}

class NotificationPage extends ConsumerStatefulWidget {
  const NotificationPage({super.key});
  @override
  ConsumerState<NotificationPage> createState() => _NotificationState();
}

class _NotificationState extends ConsumerState<NotificationPage> {
  String status = '';
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text(status),
      FilledButton(
        onPressed: () async {
          final service = ref.read(notificationProvider);
          await service.initialize();
          final allowed = await service.requestPermission();
          if (allowed) {
            await service.scheduleDaily(
              id: 9001,
              title: '今日摘要',
              body: '打開生活助理查看今天的待辦與行程',
              hour: 8,
              minute: 0,
            );
            await service.scheduleDaily(
              id: 9002,
              title: '每日收尾',
              body: '回顧今天並安排明天',
              hour: 21,
              minute: 0,
            );
          }
          setState(
            () => status = allowed ? '每日摘要 08:00、收尾 21:00 已設定' : '通知權限未開啟',
          );
        },
        child: const Text('開啟每日摘要與收尾'),
      ),
    ],
  );
}

class AttachmentPage extends ConsumerStatefulWidget {
  const AttachmentPage({super.key});
  @override
  ConsumerState<AttachmentPage> createState() => _AttachmentState();
}

class _AttachmentState extends ConsumerState<AttachmentPage> {
  final files = <File>[];
  Future<void> add(Future<File?> future) async {
    final file = await future;
    if (file != null) setState(() => files.add(file));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: ListView(
      children: files
          .map(
            (e) => ListTile(
              leading: const Icon(Icons.attach_file),
              title: Text(e.path.split(Platform.pathSeparator).last),
              subtitle: Text(e.path),
            ),
          )
          .toList(),
    ),
    bottomNavigationBar: SafeArea(
      child: Row(
        children: [
          Expanded(
            child: TextButton.icon(
              onPressed: () =>
                  add(ref.read(attachmentServiceProvider).pickFile()),
              icon: const Icon(Icons.file_open),
              label: const Text('檔案'),
            ),
          ),
          Expanded(
            child: TextButton.icon(
              onPressed: () =>
                  add(ref.read(attachmentServiceProvider).pickImage()),
              icon: const Icon(Icons.photo),
              label: const Text('圖片'),
            ),
          ),
          Expanded(
            child: TextButton.icon(
              onPressed: () => add(
                ref.read(attachmentServiceProvider).pickImage(camera: true),
              ),
              icon: const Icon(Icons.camera_alt),
              label: const Text('掃描'),
            ),
          ),
        ],
      ),
    ),
  );
}

class _Error extends StatelessWidget {
  const _Error(this.message, this.retry);
  final String message;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(message, textAlign: TextAlign.center),
        TextButton(onPressed: retry, child: const Text('重試')),
      ],
    ),
  );
}

Future<String?> _prompt(BuildContext context, String title) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: Text(title),
      content: TextField(controller: c, autofocus: true),
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
  return ok == true && c.text.trim().isNotEmpty ? c.text.trim() : null;
}
