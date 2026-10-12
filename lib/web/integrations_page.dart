import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'browser_navigation.dart';

final googleStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(apiClientProvider).getGoogleIntegrationStatus();
});

/// Business users can authorize their own Google services from Personalize.
/// Developer Tool/Action diagnostics are not exposed on this user panel.
class GoogleConnectionsPanel extends ConsumerWidget {
  const GoogleConnectionsPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(googleStatusProvider);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Google 服務連結', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 6),
      Text('由目前登入的使用者授權自己的 Google 帳號；授權服務帳號須與 Life 登入帳號一致。',
        style: Theme.of(context).textTheme.bodySmall),
      const SizedBox(height: 14),
      status.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Card(child: ListTile(
          title: const Text('連線狀態暫時無法讀取'),
          trailing: IconButton(
            tooltip: '重新載入 Google 連線狀態',
            onPressed: () => ref.invalidate(googleStatusProvider),
            icon: const Icon(Icons.refresh),
          ),
        )),
        data: (data) {
          final services = (data['granted_services'] as List? ?? const []).cast<String>();
          final email = data['email']?.toString() ?? '';
          final serviceDetails = <(String, String, IconData)>[
            ('calendar', 'Google Calendar', Icons.calendar_month_outlined),
            ('gmail', 'Gmail', Icons.email_outlined),
            ('drive', 'Google Drive', Icons.cloud_outlined),
          ];
          return Card(child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(children: [
              if (email.isNotEmpty)
                ListTile(
                  leading: const Icon(Icons.account_circle_outlined),
                  title: Text(email),
                  subtitle: const Text('目前 Google 服務授權帳號'),
                ),
              for (final service in serviceDetails)
                ListTile(
                  key: ValueKey('google-service-' + service.$1),
                  leading: Icon(service.$3),
                  title: Text(service.$2),
                  subtitle: Text(services.contains(service.$1)
                      ? '已授權（不代表 API 即時可用）' : '尚未授權'),
                  trailing: OutlinedButton(
                    onPressed: () => navigateBrowser(
                      ref.read(apiClientProvider).googleAuthorizationUrl(service.$1),
                    ),
                    child: Text(services.contains(service.$1) ? '重新授權' : '授權'),
                  ),
                ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  icon: const Icon(Icons.refresh),
                  label: const Text('更新連線狀態'),
                  onPressed: () => ref.invalidate(googleStatusProvider),
                ),
              ),
            ]),
          ));
        },
      ),
      const SizedBox(height: 10),
      Text('Google Drive 的授權不等於同意將文件交給 AI 分析；Drive AI 個人同意設定目前暫不開放。',
        style: Theme.of(context).textTheme.bodySmall),
    ]);
  }
}

/// Old /integrations deep links remain a supported alias in the router.
class IntegrationsPage extends StatelessWidget {
  const IntegrationsPage({super.key});

  @override
  Widget build(BuildContext context) => const Scaffold(
    appBar: null,
    body: SafeArea(child: SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: GoogleConnectionsPanel(),
    )),
  );
}
