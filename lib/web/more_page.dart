import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class MorePage extends StatelessWidget {
  const MorePage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('更多')),
        body: ListView(
          padding: const EdgeInsets.symmetric(vertical: 8),
          children: [
            ListTile(
              leading: const Icon(Icons.description_outlined),
              title: const Text('筆記'),
              subtitle: const Text('Markdown、搜尋、標籤與雙向連結'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/more/notes'),
            ),
            ListTile(
              leading: const Icon(Icons.repeat_rounded),
              title: const Text('習慣'),
              subtitle: const Text('週期、提醒與完成紀錄'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/more/habits'),
            ),
            ListTile(
              leading: const Icon(Icons.event_available_outlined),
              title: const Text('免費活動探索'),
              subtitle: const Text('只顯示已核實免費活動與原站報名資訊'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/more/events'),
            ),
            ListTile(
              leading: const Icon(Icons.shopping_cart_outlined),
              title: const Text('購物清單'),
              subtitle: const Text('清單、分類與採買完成狀態'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/more/shopping'),
            ),
            ListTile(
              leading: const Icon(Icons.cloud_outlined),
              title: const Text('Google Drive'),
              subtitle: const Text('檢視智能整理結果、相關筆記建議與 AI 同意設定'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/more/drive'),
            ),
            ListTile(
              leading: const Icon(Icons.hub_outlined),
              title: const Text('Google 整合'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push('/integrations'),
            ),
            ListTile(
              leading: const Icon(Icons.fact_check_outlined),
              title: const Text('驗收中心'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push('/acceptance'),
            ),
          ],
        ),
      );
}
