import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'browser_navigation.dart';
import 'platform_api.dart';

final curatedListProvider = FutureProvider<Map<String, dynamic>>((ref) async =>
    ref.read(platformApiProvider).get('/free-events/curated'));

class CuratedEventsPage extends ConsumerStatefulWidget {
  const CuratedEventsPage({super.key});
  @override
  ConsumerState<CuratedEventsPage> createState() => _CuratedEventsPageState();
}

class _CuratedEventsPageState extends ConsumerState<CuratedEventsPage> {
  String city = '';
  int stars = 1;

  @override
  Widget build(BuildContext context) {
    final result = ref.watch(curatedListProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('活動精選池'), actions: [
        IconButton(
          icon: const Icon(Icons.refresh),
          tooltip: '重新整理',
          onPressed: () => ref.invalidate(curatedListProvider),
        )
      ]),
      body: result.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('活動資料暫時無法讀取')),
        data: (json) {
          final items = (json['items'] as List).cast<Map<String, dynamic>>();
          final filtered = items.where((event) {
            final rating = (event['importance'] as num?)?.toInt() ?? 1;
            return rating >= stars && (city.isEmpty ||
                (event['city']?.toString() ?? '').contains(city));
          }).toList();
          return ListView(padding: const EdgeInsets.all(16), children: [
            const Text('由 ChatGPT 精選，活動內容與報名狀況請以原站為準。'),
            const SizedBox(height: 12),
            TextField(
              decoration: const InputDecoration(labelText: '篩選地區', prefixIcon: Icon(Icons.search)),
              onChanged: (text) => setState(() => city = text.trim()),
            ),
            DropdownButtonFormField<int>(
              value: stars,
              decoration: const InputDecoration(labelText: '最低重要性'),
              items: [1, 2, 3, 4, 5].map((s) => DropdownMenuItem(
                value: s, child: Text('$s 星以上'),
              )).toList(),
              onChanged: (n) => setState(() => stars = n ?? 1),
            ),
            const SizedBox(height: 16),
            if (filtered.isEmpty) const ListTile(
              title: Text('目前沒有符合條件的精選活動'),
              subtitle: Text('尚未匯入或篩選條件沒有符合結果。'),
            ),
            for (final item in filtered)
              Card(child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(item['title']?.toString() ?? '',
                      style: Theme.of(context).textTheme.titleMedium),
                  Text('★' * ((item['importance'] as num?)?.toInt() ?? 1)),
                  if (item['summary'] != null) Text(item['summary'].toString()),
                  Text('地區：${item['city'] ?? '未知'} · 日期：${item['starts_on'] ?? '未知'}'),
                  Text('入場：${_feeText(item)} · 現場消費：${item['on_site_spending'] == true ? '可能需要' : '未標示'}'),
                  if (item['benefit_value'] != null)
                    Text('福利價值：${item['benefit_value']}（由來源提供，未獨立查核）'),
                  Text('報名：${item['registration_status'] ?? '未知'} · ${item['registration_required'] == true ? '需報名' : '請查原站'}'),
                  if (item['limited_offer'] == true) const Text('限量或限時資訊，請即時至原站確認'),
                  TextButton.icon(
                    onPressed: () => ref.read(browserNavigationProvider)
                        .openExternal(item['original_url'].toString()),
                    icon: const Icon(Icons.open_in_new), label: const Text('前往活動原站'),
                  ),
                ]),
              )),
          ]);
        },
      ),
    );
  }

  String _feeText(Map<String, dynamic> item) {
    switch (item['fee_kind']) {
      case 'free': return '免費';
      case 'paid': return '付費 ${item['fee_amount'] ?? '金額未知'}';
      case 'conditional_free': return '有條件免費';
      default: return '未知';
    }
  }
}
