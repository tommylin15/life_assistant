import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'api_client.dart';
import 'platform_api.dart';
import 'habit_api.dart';
import 'auth_state.dart';

final _todayDataProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  if (ref.watch(authProvider).asData?.value == null) {
    throw StateError('Authentication required');
  }
  final api = ref.read(apiClientProvider);
  final now = DateTime.now();
  final tomorrow = DateTime(now.year, now.month, now.day).add(const Duration(days: 1));
  final tasks = await api.getTasks();
  final projects = await api.getProjects();
  Map<String, dynamic>? calendar;
  try {
    calendar = await api.getCalendarEvents(timeMin: now, timeMax: tomorrow, limit: 3);
  } catch (_) {
    calendar = null; // Disconnected is not an empty calendar.
  }
  Map<String, dynamic>? curated;
  try { curated = await ref.read(platformApiProvider).get('/free-events/curated'); }
  catch (_) { curated = null; }
  List<Map<String, dynamic>>? habits;
  try { habits = await ref.read(habitApiProvider).getHabits(); }
  catch (_) { habits = null; }
  return {'tasks': tasks, 'projects': projects, 'calendar': calendar,
          'events': curated, 'habits': habits};
});

class TodayPage extends ConsumerWidget {
  const TodayPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefs = ref.watch(uiPreferencesProvider).asData?.value;
    final cards = (prefs?['home_cards'] as List?)?.cast<String>() ??
        ['tasks', 'calendar', 'attention', 'habits', 'events', 'projects'];
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    final data = ref.watch(_todayDataProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('今天'), actions: [
        IconButton(
          tooltip: '自訂首頁', icon: const Icon(Icons.tune),
          onPressed: () => context.go('/more/personalize'),
        ),
        IconButton(
          tooltip: '重新整理', icon: const Icon(Icons.refresh),
          onPressed: () => ref.invalidate(_todayDataProvider),
        ),
      ]),
      body: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('首頁資料暫時無法讀取')),
        data: (snapshot) => Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1060),
            child: ListView(padding: const EdgeInsets.all(16), children: [
              Text('今日重點', style: Theme.of(context).textTheme.headlineSmall),
              for (final key in cards)
                if (flags?[key] ?? true) _card(context, ref, key, snapshot),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _card(BuildContext context, WidgetRef ref, String key, Map<String, dynamic> data) {
    final tasks = (data['tasks'] as List).cast<Map<String, dynamic>>();
    final projects = (data['projects'] as List).cast<Map<String, dynamic>>();
    final filtered = tasks.where((t) {
      if (t['status'] == 'completed' || t['status'] == 'cancelled') return false;
      final due = DateTime.tryParse(t['due_at']?.toString() ?? '')?.toLocal();
      if (due == null) return false;
      final end = DateTime.now();
      return due.isBefore(DateTime(end.year, end.month, end.day + 1));
    }).take(5).toList();
    final events = (data['events']?['items'] as List?)?.take(3).toList();
    switch (key) {
      case 'tasks':
        return _tile(context, '待辦（今天及逾期）', filtered.isEmpty
            ? '沒有已確認的今日到期待辦'
            : filtered.map((t) => t['title'].toString()).join(' · '), '/tasks');
      case 'calendar':
        final cal = data['calendar'];
        final entries = (cal is Map<String, dynamic> ? cal['events'] as List? : null) ?? [];
        String summary = '今天沒有近期已取得的行程';
        if (entries.isNotEmpty && entries.first is Map) {
          final event = entries.first as Map;
          final timing = event['start'] is Map ? event['start'] as Map : const {};
          final start = timing['dateTime']?.toString() ?? timing['date']?.toString() ?? '日期未確認';
          final place = event['location']?.toString() ?? '';
          summary = '${event['summary'] ?? '未命名行程'} · $start${place.isEmpty ? '' : ' · $place'}';
        }
        return _tile(context, '下一個行程', cal == null
            ? '未取得行事曆；請檢查 Google 連線或授權' : summary, '/calendar');
      case 'events':
        if (data['events'] == null) return const SizedBox.shrink();
        return _tile(context, '精選活動', events == null || events.isEmpty
            ? '尚無精選活動' : events.map((e) => e['title']).join(' · '), '/more/curated');
      case 'projects':
        return _tile(context, '進行中專案', projects.where(
          (p) => p['status'] == 'active',
        ).take(3).map((p) => p['name']).join(' · '), '/projects');
      case 'attention':
        final now = DateTime.now();
        final overdue = tasks.where((task) {
          if (task['status'] == 'completed' || task['status'] == 'cancelled') return false;
          final due = DateTime.tryParse(task['due_at']?.toString() ?? '')?.toLocal();
          return due != null && due.isBefore(DateTime(now.year, now.month, now.day));
        }).length;
        if (overdue == 0) return const SizedBox.shrink();
        return _tile(context, '需要關注', '有 $overdue 筆實際逾期的待辦', '/tasks');
      case 'habits':
        final habits = data['habits'] as List<Map<String, dynamic>>?;
        if (habits == null || habits.isEmpty) return const SizedBox.shrink();
        return Card(child: Column(crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const ListTile(title: Text('今日習慣')),
            for (final habit in habits.take(4))
              ListTile(
                title: Text(habit['title']?.toString() ??
                    habit['name']?.toString() ?? '習慣'),
                trailing: OutlinedButton(
                  child: const Text('記錄完成'),
                  onPressed: () async {
                    try {
                      await ref.read(habitApiProvider).completeHabit(habit['id'].toString());
                      ref.invalidate(_todayDataProvider);
                    } catch (_) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('習慣完成紀錄未寫入')),
                        );
                      }
                    }
                  },
                ),
              ),
            TextButton(onPressed: () => context.go('/more/habits'),
                child: const Text('查看全部習慣')),
          ],
        ));
      case 'notes':
        return _tile(context, '筆記', '開啟個人筆記', '/more/notes');
      case 'shopping':
        return _tile(context, '購物', '查看購物清單', '/more/shopping');
      case 'drive':
        return _tile(context, 'Drive AI', '需個人 Google 授權及 AI 同意', '/more/drive');
      default: return const SizedBox.shrink();
    }
  }

  Widget _tile(BuildContext context, String title, String summary, String route) =>
      Card(child: ListTile(
        title: Text(title),
        subtitle: Text(summary.isEmpty ? '目前沒有資料' : summary),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go(route),
      ));
}
