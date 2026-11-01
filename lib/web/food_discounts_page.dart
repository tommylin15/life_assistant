import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'activity_link.dart';
import 'browser_navigation.dart';
import 'platform_api.dart';
import 'session_identity.dart';
import 'task_api.dart';
import 'visual_system.dart';

final foodDiscountsListProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, query) {
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  return ref.read(platformApiProvider).get('/food-discounts?$query');
});

final foodDiscountsFiltersProvider =
    FutureProvider<Map<String, dynamic>>((ref) {
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  return ref.read(platformApiProvider).get('/food-discounts/filters');
});

class FoodDiscountsPage extends ConsumerStatefulWidget {
  const FoodDiscountsPage({super.key});

  @override
  ConsumerState<FoodDiscountsPage> createState() => _FoodDiscountsPageState();
}

class _FoodDiscountsPageState extends ConsumerState<FoodDiscountsPage> {
  final TextEditingController _search = TextEditingController();
  String _keyword = '';
  String _city = '';
  String _district = '';
  String _category = '';
  String _offerType = '';
  int _offset = 0;

  static const _categories = <String, String>{
    '': '全部品類',
    '手搖飲': '手搖飲',
    '國民美食': '國民美食',
    '咖啡甜點': '咖啡甜點',
    '餐飲聚餐': '餐飲聚餐',
  };

  static const _offerTypes = <String, String>{
    '': '全部優惠',
    'bogo': '買一送一／買N送N',
    'second_cup': '第二件優惠',
    'percent': '8折以下／票券',
  };

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _updateFilter(VoidCallback fn) {
    setState(() {
      fn();
      _offset = 0;
    });
  }

  String _buildQuery() {
    final params = <String, String>{
      'limit': '20',
      'offset': '$_offset',
    };
    if (_keyword.isNotEmpty) params['keyword'] = _keyword;
    if (_city.isNotEmpty) params['city'] = _city;
    if (_district.isNotEmpty) params['district'] = _district;
    if (_category.isNotEmpty) params['category'] = _category;
    if (_offerType.isNotEmpty) params['offer_type'] = _offerType;
    return Uri(queryParameters: params).query;
  }

  @override
  Widget build(BuildContext context) {
    final query = _buildQuery();
    final listing = ref.watch(foodDiscountsListProvider(query));
    final filters =
        ref.watch(foodDiscountsFiltersProvider).asData?.value ?? const {};
    final cities = (filters['cities'] as List? ?? const ['台北市', '新北市', '雙北通用'])
        .map((e) => e.toString())
        .toList();
    final districts = (filters['districts'] as List? ?? const [])
        .map((e) => e.toString())
        .where((e) => e.isNotEmpty)
        .toList();

    return Scaffold(
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1060),
          child: RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(foodDiscountsListProvider(query));
              ref.invalidate(foodDiscountsFiltersProvider);
              await ref.read(foodDiscountsListProvider(query).future);
            },
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                LifeFeatureHeader(
                  feature: LifeVisualFeature.foodDiscounts,
                  trailing: IconButton(
                    tooltip: '重新整理',
                    icon: const Icon(Icons.refresh),
                    onPressed: () {
                      ref.invalidate(foodDiscountsListProvider(query));
                      ref.invalidate(foodDiscountsFiltersProvider);
                    },
                  ),
                ),
                const SizedBox(height: 10),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.info_outline, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '雙北 41 區日常手搖飲與國民美食優惠情報（公開來源宣稱買一送一或折幅 ≥ 20%，未逐店核實，實際兌換以店家現場與原始公告為準）',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                key: const ValueKey('food-discounts-search'),
                                controller: _search,
                                decoration: InputDecoration(
                                  hintText: '搜尋店家、手搖飲、早餐、雞排、行政區或路段...',
                                  prefixIcon: const Icon(Icons.search),
                                  isDense: true,
                                  suffixIcon: _keyword.isEmpty
                                      ? null
                                      : IconButton(
                                          icon: const Icon(Icons.clear),
                                          onPressed: () => _updateFilter(() {
                                            _search.clear();
                                            _keyword = '';
                                          }),
                                        ),
                                ),
                                onSubmitted: (value) =>
                                    _updateFilter(() => _keyword = value.trim()),
                              ),
                            ),
                            const SizedBox(width: 8),
                            FilledButton.tonal(
                              onPressed: () => _updateFilter(
                                  () => _keyword = _search.text.trim()),
                              child: const Text('搜尋'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            for (final entry in _categories.entries)
                              ChoiceChip(
                                key: ValueKey('food-cat-${entry.key.isEmpty ? "all" : entry.key}'),
                                label: Text(entry.value),
                                selected: _category == entry.key,
                                onSelected: (_) =>
                                    _updateFilter(() => _category = entry.key),
                              ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            for (final entry in _offerTypes.entries)
                              FilterChip(
                                key: ValueKey('food-type-${entry.key.isEmpty ? "all" : entry.key}'),
                                label: Text(entry.value),
                                selected: _offerType == entry.key,
                                onSelected: (_) =>
                                    _updateFilter(() => _offerType = entry.key),
                              ),
                            DropdownButton<String>(
                              value: cities.contains(_city) ? _city : '',
                              hint: const Text('全部地區'),
                              items: [
                                const DropdownMenuItem(
                                    value: '', child: Text('全部地區')),
                                for (final c in cities)
                                  DropdownMenuItem(value: c, child: Text(c)),
                              ],
                              onChanged: (value) => _updateFilter(() {
                                _city = value ?? '';
                                _district = '';
                              }),
                            ),
                            if (districts.isNotEmpty)
                              DropdownButton<String>(
                                value: districts.contains(_district)
                                    ? _district
                                    : '',
                                hint: const Text('全部行政區／範圍'),
                                items: [
                                  const DropdownMenuItem(
                                      value: '', child: Text('全部行政區／範圍')),
                                  for (final d in districts)
                                    DropdownMenuItem(
                                      value: d,
                                      child: Text(d.length > 16
                                          ? '${d.substring(0, 16)}…'
                                          : d),
                                    ),
                                ],
                                onChanged: (value) => _updateFilter(
                                    () => _district = value ?? ''),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                listing.when(
                  loading: () => const Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (err, _) => Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(err.toString().contains('API 403')
                                ? '此帳號尚未開放美食優惠功能，請檢查管理員的功能設定。'
                                : '美食優惠資料讀取失敗，請稍後重試。'),
                          ),
                          TextButton(
                            onPressed: () =>
                                ref.invalidate(foodDiscountsListProvider(query)),
                            child: const Text('重試'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  data: (data) {
                    final items = (data['items'] as List? ?? const [])
                        .whereType<Map<String, dynamic>>()
                        .toList();
                    final total = data['total'] as int? ?? items.length;
                    final hasMore = data['has_more'] == true;
                    if (items.isEmpty) {
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              vertical: 32, horizontal: 16),
                          child: Column(
                            children: [
                              const Icon(Icons.local_dining_outlined, size: 44),
                              const SizedBox(height: 8),
                              const Text('目前沒有符合篩選條件的當期美食優惠'),
                              const SizedBox(height: 8),
                              TextButton(
                                onPressed: () => _updateFilter(() {
                                  _search.clear();
                                  _keyword = '';
                                  _city = '';
                                  _district = '';
                                  _category = '';
                                  _offerType = '';
                                }),
                                child: const Text('清除篩選條件'),
                              ),
                            ],
                          ),
                        ),
                      );
                    }
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8, left: 4),
                          child: Text(
                            '共 $total 筆當期公開來源優惠情報',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                        for (final item in items)
                          _FoodDiscountCard(item: item),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            if (_offset > 0)
                              OutlinedButton.icon(
                                onPressed: () => setState(() =>
                                    _offset = (_offset - 20).clamp(0, 10000)),
                                icon: const Icon(Icons.chevron_left),
                                label: const Text('上一頁'),
                              ),
                            if (_offset > 0 && hasMore)
                              const SizedBox(width: 12),
                            if (hasMore)
                              FilledButton.tonalIcon(
                                onPressed: () =>
                                    setState(() => _offset += items.length),
                                icon: const Icon(Icons.chevron_right),
                                label: const Text('下一頁'),
                              ),
                          ],
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _FoodDiscountCard extends ConsumerWidget {
  const _FoodDiscountCard({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final merchant = item['merchant']?.toString() ?? '未命名店家';
    final category = item['category']?.toString() ?? '餐飲優惠';
    final summary = item['offer_summary']?.toString() ?? '';
    final offerType = item['offer_type']?.toString() ?? '';
    final discount = item['nominal_discount']?.toString() ?? '';
    final district = item['district']?.toString() ?? '雙北門市未指定';
    final address = item['address']?.toString() ?? '';
    final period = item['period_text']?.toString() ?? '';
    final endsOn = item['offer_ends_on']?.toString() ?? '';
    final claimDeadline = item['claim_deadline_on']?.toString() ?? '';
    final notes = item['notes']?.toString() ?? '';
    final disclosure =
        item['disclosure']?.toString() ?? '公開來源宣稱，未逐項核實，不保證到店可使用';
    final sourceUrl = validActivityUrl(item['source_url']?.toString());

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(
                    merchant,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  Chip(
                    label: Text(category),
                    visualDensity: VisualDensity.compact,
                  ),
                  if (offerType.isNotEmpty)
                    Chip(
                      label: Text(offerType),
                      visualDensity: VisualDensity.compact,
                    ),
                  if (discount.isNotEmpty)
                    Chip(
                      label: Text('折幅：$discount'),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                summary,
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 6),
              Text('地區／門市：$district${address.isEmpty ? "" : " · $address"}'),
              if (period.isNotEmpty || endsOn.isNotEmpty || claimDeadline.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  [
                    if (period.isNotEmpty) '期間：$period',
                    if (endsOn.isNotEmpty) '截止日：$endsOn',
                    if (claimDeadline.isNotEmpty) '領券截止：$claimDeadline',
                  ].join(' ｜ '),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              if (notes.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  '限制與說明：$notes',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 4),
              Text(
                disclosure,
                style: Theme.of(context).textTheme.labelSmall,
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (sourceUrl != null)
                    OutlinedButton.icon(
                      icon: const Icon(Icons.open_in_new, size: 18),
                      label: const Text('查看來源公告'),
                      onPressed: () => ref
                          .read(browserNavigationProvider)
                          .openExternal(sourceUrl.toString()),
                    ),
                  TextButton.icon(
                    icon: const Icon(Icons.add_task, size: 18),
                    label: const Text('加入待辦提醒'),
                    onPressed: () async {
                      try {
                        final noteLines = <String>[
                          summary,
                          '地區：$district',
                          if (period.isNotEmpty) '期間：$period',
                          if (sourceUrl != null) '活動網址：$sourceUrl',
                        ];
                        await ref.read(taskApiProvider).createTask({
                          'title': '[美食優惠] $merchant - $summary',
                          'notes': noteLines.join('\n'),
                          if (endsOn.length >= 10) 'due_at': '${endsOn.substring(0, 10)}T23:59:00+08:00',
                        });
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('已加入待辦清單')),
                          );
                        }
                      } catch (_) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('加入待辦失敗，請稍後再試')),
                          );
                        }
                      }
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
