import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'api_client.dart';
import 'platform_api.dart';

final _todayDataProvider = FutureProvider<Map<String, dynamic>>((ref) async {
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
  return {'tasks': tasks, 'projects': projects, 'calendar': calendar, 'events': curated};
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
                if (flags?[key] ?? true) _card(context, key, snapshot),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _card(BuildContext context, String key, Map<String, dynamic> data) {
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
        return _tile(context, '行事曆', cal == null
            ? '未取得行事曆；請檢查 Google 連線或授權'
            : '查看今日行程', '/calendar');
      case 'events':
        if (data['events'] == null) return const SizedBox.shrink();
        return _tile(context, '精選活動', events == null || events.isEmpty
            ? '尚無精選活動' : events.map((e) => e['title']).join(' · '), '/more/curated');
      case 'projects':
        return _tile(context, '進行中專案', projects.where(
          (p) => p['status'] == 'active',
        ).take(3).map((p) => p['name']).join(' · '), '/projects');
      case 'attention':
        return const SizedBox.shrink(); // No invented universal alert source.
      case 'habits':
        return _tile(context, '習慣', '查看今天的習慣紀錄', '/more/habits');
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
