import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'api_client.dart';
import 'platform_api.dart';
import 'habit_api.dart';
import 'curated_activity_card.dart';
import 'session_identity.dart';
import 'visual_system.dart';

List<String> _visibleHomeCards(List<String> cards) => cards
    .map((k) => (k == 'events' || k == 'opportunities') ? 'explore' : k)
    .toSet().toList();

final _todayDataProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  final api = ref.read(apiClientProvider);
  // Read permissions before network awaits so the home dashboard cannot
  // request another account's legacy, not-yet-tenant-scoped resources.
  final prefs = ref.watch(uiPreferencesProvider).asData?.value;
  final chosen = _visibleHomeCards((prefs?['home_cards'] as List?)?.cast<String>() ??
      const ['tasks', 'calendar', 'attention', 'habits', 'explore', 'projects']);
  final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
  final now = DateTime.now();
  final tomorrow = DateTime(now.year, now.month, now.day).add(const Duration(days: 1));
  final tasks = await api.getTasks();
  List<Map<String, dynamic>>? projects;
  if (chosen.contains('projects') && flags?['projects'] == true) {
    try {
      projects = await api.getProjects();
    } catch (_) {
      projects = null; // Unavailable, not an empty project collection.
    }
  }
  Map<String, dynamic>? calendar;
  try {
    calendar = await api.getCalendarEvents(timeMin: now, timeMax: tomorrow, limit: 3);
  } catch (_) {
    calendar = null; // Disconnected is not an empty calendar.
  }
  final showExplore = chosen.contains('explore') && flags?['explore'] == true;
  Map<String, dynamic>? explore;
  if (showExplore) {
    try {
      explore = await ref.read(platformApiProvider)
          .get('/free-events/curated?entry=explore&limit=3&offset=0');
    } catch (_) {
      explore = null;
    }
  }
  List<Map<String, dynamic>>? habits;
  if (chosen.contains('habits') && flags?['habits'] == true) {
    try { habits = await ref.read(habitApiProvider).getHabits(); }
    catch (_) { habits = null; }
  }
  return {'tasks': tasks, 'projects': projects, 'calendar': calendar,
          'events': explore, 'habits': habits};
});

class TodayPage extends ConsumerWidget {
  const TodayPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefs = ref.watch(uiPreferencesProvider).asData?.value;
    final cards = _visibleHomeCards((prefs?['home_cards'] as List?)?.cast<String>() ??
        ['tasks', 'calendar', 'attention', 'habits', 'explore', 'projects']);
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    final data = ref.watch(_todayDataProvider);
    return Scaffold(
      body: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(child: TextButton.icon(
          onPressed: () => ref.invalidate(_todayDataProvider),
          icon: const Icon(Icons.refresh),
          label: const Text('首頁資料暫時無法讀取，點此重試'))),
        data: (snapshot) => Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1060),
            child: RefreshIndicator(
              onRefresh: () async {
                ref.invalidate(_todayDataProvider);
                await ref.read(_todayDataProvider.future);
              },
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16), children: [
              const LifeFeatureHeader(feature: LifeVisualFeature.today),
              const SizedBox(height: 12),
              for (final key in cards)
                if (flags?[key] ?? true) _card(context, ref, key, snapshot),
            ])),
          ),
        ),
      ),
    );
  }

  Widget _card(BuildContext context, WidgetRef ref, String key, Map<String, dynamic> data) {
    final tasks = (data['tasks'] as List).cast<Map<String, dynamic>>();
    final projects = (data['projects'] as List?)?.cast<Map<String, dynamic>>();
    final filtered = tasks.where((t) {
      if (t['status'] == 'completed' || t['status'] == 'cancelled') return false;
      final due = DateTime.tryParse(t['due_at']?.toString() ?? '')?.toLocal();
      if (due == null) return false;
      final end = DateTime.now();
      return due.isBefore(DateTime(end.year, end.month, end.day + 1));
    }).take(5).toList();
    final eventItems = (data['events']?['items'] as List? ?? const [])
        .whereType<Map<String, dynamic>>().toList();
    final events = groupActivities(eventItems)
        .take(3).map((group) => group.first).toList();
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
      case 'explore':
        return _tile(context, '活動探索', data['events'] == null
            ? '活動資料目前無法取得'
            : events == null || events.isEmpty
              ? '目前沒有符合的活動'
              : events.map((e) => e['title']?.toString() ?? '未命名活動').join(' · '),
          '/more/explore');
      case 'projects':
        return _tile(context, '進行中專案', projects == null
            ? '專案資料目前無法取得'
            : projects.where((p) => p['status'] == 'active')
                .take(3).map((p) => p['name']).join(' · '), '/projects');
      case 'attention':
        final now = DateTime.now();
        final overdue = tasks.where((task) {
          if (task['status'] == 'completed' || task['status'] == 'cancelled') return false;
          final due = DateTime.tryParse(task['due_at']?.toString() ?? '')?.toLocal();
          return due != null && due.isBefore(DateTime(now.year, now.month, now.day));
        }).length;
        return _tile(context, '需要關注', overdue == 0
            ? '目前沒有逾期待辦'
            : '有 $overdue 筆實際逾期的待辦', '/tasks');
      case 'habits':
        final habits = data['habits'] as List<Map<String, dynamic>>?;
        if (habits == null) {
          return _tile(context, '今日習慣', '習慣資料目前無法取得', '/more/habits');
        }
        if (habits.isEmpty) {
          return _tile(context, '今日習慣', '尚未建立習慣', '/more/habits');
        }
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
        return _tile(context, 'Google Drive', '查看個人已授權的雲端文件', '/more/drive');
      default: return const SizedBox.shrink();
    }
  }

  Widget _tile(BuildContext context, String title, String summary, String route) {
    final feature = switch (route) {
      '/tasks' => LifeVisualFeature.tasks,
      '/calendar' => LifeVisualFeature.calendar,
      '/projects' => LifeVisualFeature.projects,
      '/more/notes' => LifeVisualFeature.notes,
      '/more/habits' => LifeVisualFeature.habits,
      '/more/shopping' => LifeVisualFeature.shopping,
      '/more/drive' => LifeVisualFeature.drive,
      '/more/curated' || '/more/explore' => LifeVisualFeature.explore,
      _ => null,
    };
    final tint = feature?.color ?? Theme.of(context).colorScheme.primary;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(clipBehavior: Clip.antiAlias,
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          leading: Container(
            width: 44, height: 44,
            decoration: BoxDecoration(color: tint.withValues(alpha: .13),
              borderRadius: BorderRadius.circular(13)),
            child: Icon(feature?.icon ?? Icons.dashboard_customize_outlined, color: tint),
          ),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(summary.isEmpty ? '目前沒有資料' : summary,
            maxLines: 3, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => context.go(route),
        )),
    );
  }
}
