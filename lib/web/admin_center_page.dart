import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'platform_api.dart';

final _adminRollouts = FutureProvider<Map<String, dynamic>>(
  (ref) => ref.read(platformApiProvider).get('/admin/feature-rollouts'));
final _activityStatus = FutureProvider<Map<String, dynamic>>(
  (ref) => ref.read(platformApiProvider).get('/free-events/curated/status'));

class AdminCenterPage extends ConsumerWidget {
  const AdminCenterPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rollouts = ref.watch(_adminRollouts);
    return Scaffold(
      appBar: AppBar(title: const Text('管理中心')),
      body: rollouts.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('管理員授權不足或設定讀取失敗')),
        data: (data) => ListView(padding: const EdgeInsets.all(16), children: [
          Text('功能開放', style: Theme.of(context).textTheme.headlineSmall),
          const Text('設定由後端管控；無法透過隱藏按鈕繞過權限。'),
          for (final dynamic feature in (data['features'] as List))
            ListTile(
              title: Text(feature['title'].toString()),
              subtitle: Text('目前：${feature['status']} / ${feature['audience']}'),
              trailing: PopupMenuButton<String>(
                tooltip: '調整開放狀態',
                onSelected: (selection) async {
                  final parts = selection.split('/');
                  final status = parts.first;
                  final audience = parts.length == 2 ? parts.last : feature['audience'];
                  try {
                    await ref.read(platformApiProvider).put('/admin/feature-rollouts', {
                      'key': feature['key'],
                      'status': status,
                      'audience': audience,
                      'expected_revision': feature['revision'],
                    });
                    ref.invalidate(_adminRollouts);
                    ref.invalidate(effectiveFeaturesProvider);
                  } catch (_) {
                    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('修改失敗：權限、發版門檻或版本衝突')),
                    );
                  }
                },
                itemBuilder: (_) => const {
                  'enabled/all': '開放給所有使用者',
                  'enabled/owner': '開放給管理員',
                  'beta/owner': '測試（管理員）',
                  'hidden': '隱藏',
                  'maintenance': '維護中',
                }.entries.map((entry) => PopupMenuItem(value: entry.key, child: Text(entry.value))).toList(),
              ),
            ),
          const Divider(),
          Text('活動精選池：統計', style: Theme.of(context).textTheme.titleMedium),
          const _ActivityAdmin(),
        ]),
      ),
    );
  }
}

class _ActivityAdmin extends ConsumerWidget {
  const _ActivityAdmin();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(_activityStatus).when(
      loading: () => const LinearProgressIndicator(),
      error: (_, __) => const Text('活動狀態無法讀取'),
      data: (state) => Text('已收錄活動：${state['items']} · 最新更新：${state['last_updated_at'] ?? '未知'}'),
    );
  }
}
