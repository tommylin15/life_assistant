import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'platform_api.dart';
import 'session_identity.dart';
import 'curated_activity_card.dart';
import 'visual_system.dart';

final curatedListProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, query) {
  ref.watch(curatedMutationEpochProvider);
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  return ref.read(platformApiProvider).get('/free-events/curated?$query');
});

final curatedOptionsProvider = FutureProvider<Map<String, dynamic>>((ref) {
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  return ref.read(platformApiProvider).get('/free-events/curated/filters');
});

class CuratedEventsPage extends ConsumerStatefulWidget {
  const CuratedEventsPage({super.key, this.entry = 'explore'});
  final String entry;
  @override
  ConsumerState<CuratedEventsPage> createState() => _CuratedEventsPageState();
}

class _CuratedEventsPageState extends ConsumerState<CuratedEventsPage> {
  final search = TextEditingController();
  String keyword = '';
  String quick = '';
  String region = '';
  String city = '';
  String category = '';
  String district = '';
  String fee = '';
  DateTime? from;
  bool savedOnly = false;
  List<int> offsets = [0];

  bool get opportunity => widget.entry == 'opportunities';

  static const opportunityChips = {
    'opening_soon': '即將開報', 'opening_today': '今天開報',
    'closing_soon': '3 天內截止', 'limited': '限額優惠',
    'unknown_time': '時間待公布', 'latest': '最新收錄',
  };
  static const explorationChips = {
    'ongoing': '正在進行', 'weekend': '本週末',
    'next_7': '7 天內開始', 'next_30': '30 天內開始',
    'free': '免費活動', 'latest': '最新收錄',
  };
  static const regions = {
    '': '全台', 'north': '北部', 'central': '中部',
    'south': '南部', 'east': '東部', 'islands': '離島',
  };

  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  void filter(VoidCallback change) => setState(() {
    change();
    offsets = [0];
  });

  String _query(int offset) {
    final params = <String, String>{
      'entry': opportunity ? 'opportunities' : 'explore',
      'limit': offset == 0 ? '5' : '10',
      'offset': '$offset',
    };
    if (keyword.isNotEmpty) params['keyword'] = keyword;
    if (quick.isNotEmpty) params['quick'] = quick;
    if (region.isNotEmpty) params['region'] = region;
    if (city.isNotEmpty) params['city'] = city;
    if (category.isNotEmpty) params['category'] = category;
    if (district.isNotEmpty) params['district'] = district;
    if (fee.isNotEmpty) params['fee_kind'] = fee;
    if (savedOnly) params['saved_only'] = 'true';
    if (from != null) {
      final d = from!;
      params['starts_from'] = '${d.year}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')}';
    }
    return Uri(queryParameters: params).query;
  }

  void _refreshPages() {
    for (final offset in offsets) {
      ref.invalidate(curatedListProvider(_query(offset)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final chips = opportunity ? opportunityChips : explorationChips;
    final optionState = ref.watch(curatedOptionsProvider);
    final options = optionState.asData?.value ?? const {};
    final pages = <Widget>[];
    var hasMore = false;
    int? nextOffset;
    var loadingLast = false;
    for (final offset in offsets) {
      final key = _query(offset);
      final result = ref.watch(curatedListProvider(key));
      final last = offset == offsets.last;
      pages.add(result.when(
        loading: () {
          if (last) loadingLast = true;
          return const Padding(padding: EdgeInsets.all(24),
            child: Center(child: CircularProgressIndicator()));
        },
        error: (_, __) => Padding(padding: const EdgeInsets.all(12),
          child: Row(children: [
            const Expanded(child: Text('活動載入失敗，請檢查連線後重試。')),
            TextButton(onPressed: () => ref.invalidate(curatedListProvider(key)),
              child: const Text('重試')),
          ])),
        data: (data) {
          if (last) {
            hasMore = data['has_more'] == true;
            nextOffset = int.tryParse(data['next_cursor']?.toString() ?? '');
          }
          final items = (data['items'] as List? ?? const [])
              .whereType<Map<String, dynamic>>().toList();
          final groups = groupActivities(items);
          final visibleIds = items.map((x) => x['identity_key']?.toString() ?? '').toList();
          // The actions API has an explicit 100-ID/6500-char upper bound.
          // Fall back to per-group queries for unusually large parent groups.
          final batchedActionIds = visibleIds.length <= 100 &&
              visibleIds.every((id) => RegExp(r'^[0-9a-f]{64}$').hasMatch(id))
              ? visibleIds.join(',') : null;
          if (groups.isEmpty && offset == 0) {
            return Padding(padding: const EdgeInsets.symmetric(vertical: 24),
              child: Column(children: [
                const Icon(Icons.search_off_outlined, size: 44),
                const SizedBox(height: 8),
                const Text('目前沒有符合條件的活動'),
                TextButton(onPressed: () => filter(() {
                  keyword = ''; search.clear(); quick = ''; region = '';
                  city = ''; district = ''; category = ''; fee = ''; from = null; savedOnly = false;
                }), child: const Text('清除篩選')),
              ]));
          }
          Widget activityCard(List<Map<String, dynamic>> group) =>
              CuratedActivityCard(
                key: ValueKey('group-${group.first['parent_event_key'] ?? group.first['handoff_event_key'] ?? group.first['identity_key']}'),
                items: group, entry: widget.entry,
                actionIds: batchedActionIds, onChanged: _refreshPages);
          // One comfortable mobile column; two independently-sized desktop
          // columns (no fixed-height GridView that clips expanded offers).
          return LayoutBuilder(builder: (context, constraints) {
            if (constraints.maxWidth < 840) {
              return Column(children: [
                for (final group in groups) activityCard(group),
              ]);
            }
            return Column(children: [
              for (var i = 0; i < groups.length; i += 2)
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(child: activityCard(groups[i])),
                  const SizedBox(width: 12),
                  Expanded(child: i + 1 < groups.length
                      ? activityCard(groups[i + 1]) : const SizedBox.shrink()),
                ]),
            ]);
          });
        },
      ));
    }

    return Scaffold(
      appBar: AppBar(title: Text(opportunity ? '限時機會' : '活動探索'),
        actions: [IconButton(tooltip: '重新整理', onPressed: _refreshPages,
          icon: const Icon(Icons.refresh))]),
      body: Center(child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1160),
        child: ListView(padding: const EdgeInsets.all(16), children: [
          LifeFeatureHeader(feature: opportunity
            ? LifeVisualFeature.opportunities : LifeVisualFeature.explore),
          const SizedBox(height: 12),
          const Text('活動與報名資訊以原站為準；收藏不代表已報名。'),
          const SizedBox(height: 12),
          TextField(
            controller: search,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search),
              hintText: '搜尋標題、主辦、地點、活動內容',
              suffixIcon: IconButton(
                tooltip: '搜尋',
                onPressed: () => filter(() => keyword = search.text.trim()),
                icon: const Icon(Icons.arrow_forward)),
              border: const OutlineInputBorder()),
            onSubmitted: (v) => filter(() => keyword = v.trim())),
          const SizedBox(height: 12),
          Wrap(spacing: 7, runSpacing: 8, children: [
            ChoiceChip(label: const Text('全部'),
              selected: !savedOnly,
              onSelected: (_) => filter(() => savedOnly = false)),
            ChoiceChip(label: const Text('已收藏'),
              avatar: const Icon(Icons.bookmark_outline, size: 17),
              selected: savedOnly,
              onSelected: (_) => filter(() => savedOnly = true)),
          ]),
          const SizedBox(height: 8),
          SingleChildScrollView(scrollDirection: Axis.horizontal, child: Row(children: [
            for (final entry in chips.entries)
              Padding(padding: const EdgeInsets.only(right: 7),
                child: ChoiceChip(label: Text(entry.value),
                  selected: quick == entry.key,
                  onSelected: (on) => filter(() => quick = on ? entry.key : ''))),
          ])),
          const SizedBox(height: 12),
          ExpansionTile(
            title: const Text('更多篩選'),
            leading: const Icon(Icons.tune),
            children: [
              Wrap(spacing: 10, runSpacing: 10, children: [
                DropdownButton<String>(
                  value: region, items: [
                    for (final e in regions.entries)
                      DropdownMenuItem(value: e.key, child: Text(e.value))],
                  onChanged: (v) => filter(() => region = v ?? ''),
                ),
                DropdownButton<String>(
                  value: city,
                  items: [
                    const DropdownMenuItem(value: '', child: Text('全部縣市')),
                    for (final c in (options['cities'] as List? ?? const []))
                      if (c is String && c.isNotEmpty)
                        DropdownMenuItem(value: c, child: Text(c)),
                  ],
                  onChanged: (v) => filter(() => city = v ?? ''),
                ),
                DropdownButton<String>(
                  value: category,
                  items: [
                    const DropdownMenuItem(value: '', child: Text('全部類別')),
                    for (final c in (options['categories'] as List? ?? const []))
                      if (c is String && c.isNotEmpty)
                        DropdownMenuItem(value: c, child: Text(c)),
                  ],
                  onChanged: (v) => filter(() => category = v ?? ''),
                ),
                SizedBox(width: 150, child: TextFormField(
                  key: ValueKey('activity-district-$district'),
                  initialValue: district,
                  decoration: const InputDecoration(labelText: '行政區', hintText: '例如：中正區'),
                  textInputAction: TextInputAction.search,
                  onFieldSubmitted: (v) => filter(() => district = v.trim()),
                )),
                DropdownButton<String>(
                  value: fee,
                  items: const [
                    DropdownMenuItem(value: '', child: Text('不限費用')),
                    DropdownMenuItem(value: 'free', child: Text('免費')),
                    DropdownMenuItem(value: 'paid', child: Text('付費')),
                    DropdownMenuItem(value: 'conditional_free', child: Text('條件免費')),
                    DropdownMenuItem(value: 'unknown', child: Text('費用未知')),
                  ],
                  onChanged: (v) => filter(() => fee = v ?? ''),
                ),
                OutlinedButton.icon(icon: const Icon(Icons.event),
                  label: Text(from == null ? '活動開始日期' :
                    '${from!.year}/${from!.month}/${from!.day}'),
                  onPressed: () async {
                    final picked = await showDatePicker(context: context,
                      initialDate: from ?? DateTime.now(),
                      firstDate: DateTime(2000), lastDate: DateTime(2100));
                    if (picked != null) filter(() => from = picked);
                  }),
              ]),
            ],
          ),
          const SizedBox(height: 16),
          ...pages,
          if (loadingLast) const SizedBox(height: 12),
          if (hasMore && nextOffset != null)
            Center(child: OutlinedButton.icon(
              key: const ValueKey('curated-load-more'),
              onPressed: () => setState(() => offsets.add(nextOffset!)),
              icon: const Icon(Icons.expand_more),
              label: const Text('再看 10 筆'))),
        ]),
      )),
    );
  }
}
