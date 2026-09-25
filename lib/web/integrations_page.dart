import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'api_client.dart';
import 'browser_navigation.dart';

final _googleStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(apiClientProvider).getGoogleIntegrationStatus();
});

final _googleCapabilitiesProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  return ref.read(apiClientProvider).getGoogleCapabilities();
});

class IntegrationsPage extends ConsumerWidget {
  const IntegrationsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(_googleStatusProvider);
    final capabilities = ref.watch(_googleCapabilitiesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Google 整合'),
        leading: IconButton(
          tooltip: '返回待辦',
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
        actions: [
          IconButton(
            tooltip: '重新整理',
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(_googleStatusProvider);
              ref.invalidate(_googleCapabilitiesProvider);
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          status.when(
            loading: () => const Card(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: CircularProgressIndicator()),
              ),
            ),
            error: (error, _) => Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text('Google 整合狀態讀取失敗：$error'),
              ),
            ),
            data: (data) => _GoogleConnectionCard(
              data: data,
              onAuthorize: (service) => navigateBrowser(
                ref.read(apiClientProvider).googleAuthorizationUrl(service),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('目前 Tool / Action', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          capabilities.when(
            loading: () => const LinearProgressIndicator(),
            error: (error, _) => Text('能力清單讀取失敗：$error'),
            data: (items) => Card(
              child: Column(
                children: items
                    .map(
                      (item) => ListTile(
                        leading: Icon(
                          item['risk'] == 'read' ? Icons.visibility : Icons.edit,
                        ),
                        title: Text(item['name'] as String),
                        subtitle: Text(
                          'risk: ${item['risk']} · confirmation: ${item['confirmation']}',
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GoogleConnectionCard extends StatelessWidget {
  const _GoogleConnectionCard({required this.data, required this.onAuthorize});

  final Map<String, dynamic> data;
  final ValueChanged<String> onAuthorize;

  @override
  Widget build(BuildContext context) {
    final granted = (data['granted_services'] as List? ?? const []).cast<String>();
    final connected = data['connected'] == true;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(connected ? Icons.cloud_done : Icons.cloud_off),
                const SizedBox(width: 8),
                Text(
                  connected ? 'Google 已連線' : 'Google 尚未授權服務',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            if (data['email'] != null) ...[
              const SizedBox(height: 8),
              Text(data['email'] as String),
            ],
            const SizedBox(height: 12),
            Text(
              granted.isEmpty
                  ? '目前沒有 Gmail / Calendar / Drive scope'
                  : '已授權：${granted.join('、')}',
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _AuthorizeButton(
                  service: 'gmail',
                  label: granted.contains('gmail') ? '重新授權 Gmail' : '授權 Gmail',
                  onPressed: onAuthorize,
                ),
                _AuthorizeButton(
                  service: 'calendar',
                  label: granted.contains('calendar')
                      ? '重新授權 Calendar'
                      : '授權 Calendar',
                  onPressed: onAuthorize,
                ),
                _AuthorizeButton(
                  service: 'drive',
                  label: granted.contains('drive') ? '重新授權 Drive' : '授權 Drive',
                  onPressed: onAuthorize,
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              '第一批只開 Gmail 唯讀、Calendar event 與 Drive app-file 權限；不包含寄信、全 Drive 或刪除工具。',
            ),
          ],
        ),
      ),
    );
  }
}

class _AuthorizeButton extends StatelessWidget {
  const _AuthorizeButton({
    required this.service,
    required this.label,
    required this.onPressed,
  });

  final String service;
  final String label;
  final ValueChanged<String> onPressed;

  @override
  Widget build(BuildContext context) => FilledButton.tonal(
        onPressed: () => onPressed(service),
        child: Text(label),
      );
}
