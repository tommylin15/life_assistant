import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'platform_api.dart';

class MorePage extends ConsumerWidget {
  const MorePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    final prefs = ref.watch(uiPreferencesProvider).asData?.value;
    bool enabled(String key) => flags?[key] ?? true;
    const keys = ['notes', 'habits', 'events', 'shopping', 'drive', 'integrations'];
    final preferred = (prefs?['more_order'] as List?)?.cast<String>() ?? keys;
    final ordered = [...preferred.where(keys.contains), ...keys.where((k) => !preferred.contains(k))];
    final entries = <String, Widget>{
      'notes': ListTile(
        leading: const Icon(Icons.description_outlined),
        title: const Text('筆記'),
        subtitle: const Text('Markdown、搜尋、標籤與雙向連結'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/more/notes'),
      ),
      'habits': ListTile(
        leading: const Icon(Icons.repeat_rounded),
        title: const Text('習慣'),
        subtitle: const Text('週期、提醒與完成紀錄'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/more/habits'),
      ),
      'events': ListTile(
        leading: const Icon(Icons.event_available_outlined),
        title: const Text('活動精選池'),
        subtitle: const Text('ChatGPT 精選重要活動與原站資訊'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/more/curated'),
      ),
      'shopping': ListTile(
        leading: const Icon(Icons.shopping_cart_outlined),
        title: const Text('購物清單'),
        subtitle: const Text('清單、分類與採買完成狀態'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/more/shopping'),
      ),
      'drive': ListTile(
        leading: const Icon(Icons.cloud_outlined),
        title: const Text('Google Drive'),
        subtitle: const Text('檢視智能整理結果、相關筆記建議與 AI 同意設定'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/more/drive'),
      ),
      'integrations': ListTile(
        leading: const Icon(Icons.hub_outlined),
        title: const Text('Google 整合'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push('/integrations'),
      ),
    };
    return Scaffold(
      appBar: AppBar(title: const Text('更多')),
      body: ListView(padding: const EdgeInsets.symmetric(vertical: 8), children: [
        for (final key in ordered)
          if (enabled(key)) entries[key]!,
        ListTile(
          leading: const Icon(Icons.tune_outlined),
          title: const Text('個人化介面'),
          subtitle: const Text('自訂導覽列與首頁卡片'),
          onTap: () => context.go('/more/personalize'),
        ),
        if (ref.watch(ownerAuthorizedProvider).asData?.value == true)
          ListTile(
            leading: const Icon(Icons.admin_panel_settings_outlined),
            title: const Text('管理中心'),
            onTap: () => context.go('/more/admin'),
          ),
        ListTile(
          leading: const Icon(Icons.fact_check_outlined),
          title: const Text('驗收中心'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => context.push('/acceptance'),
        ),
      ]),
    );
  }
}
