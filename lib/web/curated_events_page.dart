import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'platform_api.dart';
import 'session_identity.dart';
import 'curated_activity_card.dart';

const _pageSize = 50;
final curatedListProvider = FutureProvider.family<Map<String, dynamic>, String>(
  (ref, query) {
    if (ref.watch(sessionIdentityProvider) == null) throw StateError('Authentication required');
    return ref.read(platformApiProvider).get('/free-events/curated?$query');
  },
);

class CuratedEventsPage extends ConsumerStatefulWidget {
  const CuratedEventsPage({super.key, this.entry = 'all'});
  final String entry;
  @override
  ConsumerState<CuratedEventsPage> createState() => _CuratedEventsPageState();
}

class _CuratedEventsPageState extends ConsumerState<CuratedEventsPage> {
  String city = '';
  String category = '';
  DateTime? startsFrom;
  int stars = 1;
  int offset = 0;

  String get _query {
    final params = <String, String>{
      'limit': '$_pageSize', 'offset': '$offset', 'min_importance': '$stars', 'entry': widget.entry,
    };
    if (city.isNotEmpty) params['city'] = city;
    if (category.isNotEmpty) params['category'] = category;
    if (startsFrom != null) {
      final d = startsFrom!;
      params['starts_from'] =
          '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    }
    return Uri(queryParameters: params).query;
  }

  void _filter(VoidCallback change) {
    setState(() {
      change();
      offset = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    final query = _query;
    final result = ref.watch(curatedListProvider(query));
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.entry == 'opportunities' ? '限時機會' : widget.entry == 'explore' ? '活動探索' : '活動精選池'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '重新整理',
            onPressed: () => ref.invalidate(curatedListProvider(query)),
          ),
        ],
      ),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('由 ChatGPT 精選。重要性、價值及報名資訊仍以活動原站為準。'),
        const SizedBox(height: 12),
        TextField(
          decoration: const InputDecoration(
            labelText: '地區（完整名稱，按搜尋送出）',
            prefixIcon: Icon(Icons.location_on_outlined),
          ),
          textInputAction: TextInputAction.search,
          onSubmitted: (value) => _filter(() => city = value.trim()),
        ),
        TextField(
          decoration: const InputDecoration(
            labelText: '類別（完整名稱，按搜尋送出）',
            prefixIcon: Icon(Icons.category_outlined),
          ),
          textInputAction: TextInputAction.search,
          onSubmitted: (value) => _filter(() => category = value.trim()),
        ),
        DropdownButtonFormField<int>(
          value: stars,
          decoration: const InputDecoration(labelText: '最低重要性'),
          items: [1, 2, 3, 4, 5].map((s) =>
              DropdownMenuItem(value: s, child: Text('$s 星以上'))).toList(),
          onChanged: (value) => _filter(() => stars = value ?? 1),
        ),
        const SizedBox(height: 8),
        Row(children: [
          TextButton.icon(
            icon: const Icon(Icons.date_range),
            label: Text(startsFrom == null
                ? '選擇開始日期' : '開始日期：${startsFrom!.year}/${startsFrom!.month}/${startsFrom!.day}'),
            onPressed: () async {
              final now = DateTime.now();
              final selected = await showDatePicker(
                context: context,
                initialDate: startsFrom ?? now,
                firstDate: DateTime(2000),
                lastDate: DateTime(2100),
              );
              if (selected != null && mounted) {
                _filter(() => startsFrom = selected);
              }
            },
          ),
          if (startsFrom != null)
            IconButton(
              icon: const Icon(Icons.clear),
              tooltip: '清除日期',
              onPressed: () => _filter(() => startsFrom = null),
            ),
        ]),
        const SizedBox(height: 12),
        result.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const ListTile(
            title: Text('活動資料暫時無法讀取'),
            subtitle: Text('可能尚未開放此功能，或連線已中斷。請重新整理。'),
          ),
          data: (json) {
            final items = (json['items'] as List?)?.cast<Map<String, dynamic>>() ??
                <Map<String, dynamic>>[];
            return Column(children: [
              if (items.isEmpty) const ListTile(
                title: Text('目前沒有符合條件的精選活動'),
                subtitle: Text('尚未匯入或篩選條件沒有符合結果。未知資料不會偽裝成已驗證。'),
              ),
              for (final group in groupActivities(items))
                CuratedActivityCard(items: group),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                TextButton(
                  onPressed: offset == 0 ? null :
                      () => setState(() => offset -= _pageSize),
                  child: const Text('上一頁'),
                ),
                Text('第 ${offset ~/ _pageSize + 1} 頁'),
                TextButton(
                  onPressed: (json['returned'] as num? ?? 0) < _pageSize ? null :
                      () => setState(() => offset += _pageSize),
                  child: const Text('下一頁'),
                ),
              ]),
            ]);
          },
        ),
      ]),
    );
  }

}
