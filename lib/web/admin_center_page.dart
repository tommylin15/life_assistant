import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'platform_api.dart';

final _adminRollouts = FutureProvider<Map<String, dynamic>>(
  (ref) => ref.read(platformApiProvider).get('/admin/feature-rollouts'));
final _adminAi = FutureProvider<Map<String, dynamic>>(
  (ref) => ref.read(platformApiProvider).get('/admin/ai/providers'));
final _adminUsage = FutureProvider<Map<String, dynamic>>(
  (ref) => ref.read(platformApiProvider).get('/admin/ai/usage'));
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
                onSelected: (status) async {
                  try {
                    await ref.read(platformApiProvider).put('/admin/feature-rollouts', {
                      'key': feature['key'],
                      'status': status,
                      'audience': status == 'beta' ? 'owner' : feature['audience'],
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
                itemBuilder: (_) => ['enabled', 'beta', 'hidden', 'maintenance']
                    .map((s) => PopupMenuItem(value: s, child: Text(s))).toList(),
              ),
            ),
          const Divider(),
          Text('平台 Drive AI（與 ChatGPT 活動精選分離）',
              style: Theme.of(context).textTheme.headlineSmall),
          _AiSettings(),
          const Divider(),
          Text('活動精選池：統計', style: Theme.of(context).textTheme.titleMedium),
          const _ActivityAdmin(),
        ]),
      ),
    );
  }
}

class _AiSettings extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(_adminAi).when(
      loading: () => const LinearProgressIndicator(),
      error: (_, __) => const Text('AI Provider 狀態尚未驗證'),
      data: (data) {
        final policy = data['policy'] as Map<String, dynamic>;
        final allowed = (policy['allowed_providers'] as List).cast<String>();
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SwitchListTile(
            title: const Text('允許平台 Drive AI'),
            subtitle: const Text('不覆蓋各使用者的 Google 授權及 AI 同意'),
            value: policy['enabled'] as bool,
            onChanged: (enabled) => _save(context, ref, policy, enabled, allowed),
          ),
          for (final dynamic p in data['providers'] as List)
            CheckboxListTile(
              title: Text(p['key'].toString()),
              subtitle: Text('憑證：${p['credential']} · 直連健康：${p['direct_health']}'),
              value: allowed.contains(p['key']),
              onChanged: (enable) {
                final next = [...allowed];
                if (enable == true && !next.contains(p['key'])) next.add(p['key']);
                if (enable == false) next.remove(p['key']);
                _save(context, ref, policy, policy['enabled'] as bool, next);
              },
              secondary: IconButton(
                tooltip: '直連健康測試（每 15 分鐘最多一次）',
                icon: const Icon(Icons.monitor_heart_outlined),
                onPressed: p['key'] == 'codex' ? null : () async {
                  try {
                    final outcome = await ref.read(platformApiProvider).post(
                        '/admin/ai/probe/${p['key']}', const {});
                    ref.invalidate(_adminAi);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text('直連健康：${outcome['direct_health']}'),
                      ));
                    }
                  } catch (_) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                        content: Text('無法完成直連測試；請檢查權限、配額或服務。'),
                      ));
                    }
                  }
                },
              ),
            ),
          const Text('Token / 成本：未計量，不推估金額。'),
          ref.watch(_adminUsage).when(
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => const Text('無法讀取用量統計'),
            data: (usage) => Text('已儲存執行結果筆數：${(usage['counts'] as List).fold<int>(
              0, (n, row) => n + ((row['count'] as num).toInt()))}'),
          ),
        ]);
      },
    );
  }

  Future<void> _save(BuildContext context, WidgetRef ref,
      Map<String, dynamic> policy, bool enabled, List<String> allowed) async {
    try {
      await ref.read(platformApiProvider).put('/admin/ai/policy', {
        'expected_revision': policy['revision'],
        'enabled': enabled,
        'allowed_providers': allowed,
      });
      ref.invalidate(_adminAi);
    } catch (_) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('AI 設定未儲存：版本衝突或權限不足')),
      );
    }
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
