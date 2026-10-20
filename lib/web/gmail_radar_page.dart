import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'browser_navigation.dart';
import 'platform_api.dart';
import 'life_ui_environment.dart';

/// One-user, manual-only Gmail radar. No background scheduling.
class GmailRadarPage extends ConsumerStatefulWidget {
  const GmailRadarPage({super.key});
  @override
  ConsumerState<GmailRadarPage> createState() => _GmailRadarPageState();
}

class _GmailRadarPageState extends ConsumerState<GmailRadarPage> {
  bool _loading = true;
  bool _scanning = false;
  bool _backfilling = false;
  bool _rechecking = false;
  bool _sevenDay = false;
  bool _scanDetails = false;
  bool _loadingMore = false;
  bool _hasMore = false;
  int _loadRevision = 0;
  static const int _pageSize = 8;
  String? _error;
  String _filter = 'pending';
  Map<String, dynamic> _status = const {};
  List<Map<String, dynamic>> _items = const [];
  final Set<String> _updating = {};

  @override
  void initState() { super.initState(); _load(); }


  Future<void> _load() async {
    if (!mounted) return;
    final requestedFilter = _filter;
    final revision = ++_loadRevision;
    setState(() { _loading = true; _loadingMore = false; _error = null; });
    try {
      final api = ref.read(platformApiProvider);
      final status = await api.get('/integrations/google/gmail/radar/status');
      final response = await api.get(
        '/integrations/google/gmail/radar/items?status=$requestedFilter&limit=${_pageSize + 1}&offset=0');
      if (!mounted || revision != _loadRevision || requestedFilter != _filter) return;
      final fetched = (response['items'] as List? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map)).toList();
      setState(() {
        _status = status;
        _items = fetched.take(_pageSize).toList();
        _hasMore = fetched.length > _pageSize;
      });
    } catch (_) {
      if (mounted && revision == _loadRevision) {
        setState(() => _error = '無法取得 Gmail 事項，請重新整理。');
      }
    } finally {
      if (mounted && revision == _loadRevision) setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_loading || _loadingMore || !_hasMore) return;
    final requestedFilter = _filter;
    final revision = _loadRevision;
    final offset = _items.length;
    setState(() => _loadingMore = true);
    try {
      final response = await ref.read(platformApiProvider).get(
        '/integrations/google/gmail/radar/items?status=$requestedFilter&limit=${_pageSize + 1}&offset=$offset');
      if (!mounted || revision != _loadRevision || requestedFilter != _filter) return;
      final fetched = (response['items'] as List? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map)).toList();
      setState(() {
        final existing = _items.map((item) => item['id']).toSet();
        _items.addAll(fetched.take(_pageSize).where((item) => existing.add(item['id'])));
        _hasMore = fetched.length > _pageSize;
      });
    } catch (_) {
      if (mounted && revision == _loadRevision) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('載入更多事項失敗，請重試。')));
      }
    } finally {
      if (mounted && revision == _loadRevision) setState(() => _loadingMore = false);
    }
  }

  Future<void> _scan({bool backfill = false, bool recheck = false,
      bool sevenDay = false}) async {
    if (_scanning || _status['gmail_authorized'] != true) return;
    setState(() {
      _scanning = true;
      _backfilling = backfill;
      _rechecking = recheck;
      _sevenDay = sevenDay;
      _error = null;
    });
    try {
      final r = await ref.read(platformApiProvider).post(
        sevenDay
            ? '/integrations/google/gmail/radar/backfill-seven-days'
            : recheck
            ? '/integrations/google/gmail/radar/recheck-three-days'
            : backfill
                ? '/integrations/google/gmail/radar/backfill-three-days'
                : '/integrations/google/gmail/radar/quick-scan', const {});
      if (!mounted) return;
      final count = (sevenDay ? r['seven_day_count'] : r['three_day_count']) ?? '未知';
      final remaining = (sevenDay ? r['seven_day_remaining'] : r['three_day_remaining']) ?? '未知';
      final countText = (sevenDay ? r['seven_day_count_capped'] : r['three_day_count_capped']) == true
          ? '至少$count' : '$count';
      final message = (sevenDay ? '七天補檢' : recheck ? '重新判讀' : backfill ? '三天補檢' : '快掃') +
        '：近${sevenDay ? '七' : '三'}天 $countText 封，本次檢查 ' + (r['checked'] ?? 0).toString() +
        ' 封，新增事項 ' + (r['added'] ?? 0).toString() +
        ' 筆，未檢查 ' + remaining.toString() +
        ' 封，失敗 ' + (r['failed'] ?? 0).toString() + ' 封';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Gmail 掃描未完成。請稍後重試；若持續失敗，請提供發生時間以查詢紀錄。');
      }
    } finally {
      if (mounted) setState(() {
        _scanning = false;
        _backfilling = false;
        _rechecking = false;
        _sevenDay = false;
      });
    }
  }

  Future<void> _updateItem(String id, String status) async {
    if (!_updating.add(id)) return;
    setState(() {});
    try {
      await ref.read(platformApiProvider).patch(
        '/integrations/google/gmail/radar/items/' + Uri.encodeComponent(id),
        {'status': status});
      if (mounted) await _load();
    } catch (_) {
      if (mounted) setState(() => _error = '更新失敗，請稍後重試。');
    } finally {
      if (mounted) setState(() => _updating.remove(id));
    }
  }

  bool _safeGmailUrl(String url) {
    final uri = Uri.tryParse(url);
    return uri != null && uri.scheme == 'https' &&
        uri.host == 'mail.google.com' &&
        uri.userInfo.isEmpty && uri.port == 443;
  }

  String _date(dynamic value) {
    final date = DateTime.tryParse(value?.toString() ?? '');
    if (date == null) return '未提供';
    final local = date.toLocal();
    String two(int v) => v.toString().padLeft(2, '0');
    return local.year.toString() + '/' + two(local.month) + '/' +
        two(local.day) + ' ' + two(local.hour) + ':' + two(local.minute);
  }


  @override
  Widget build(BuildContext context) {
    final granted = _status['gmail_authorized'] == true;
    final threeDayCount = _status['three_day_count'] as int?;
    final remaining = _status['three_day_remaining'] as int?;
    final needBackfill = granted && (remaining ?? 0) > 0;
    final complete = _status['three_day_complete'] == true;
    final sevenDayCount = _status['seven_day_count'] as int?;
    final colors = Theme.of(context).colorScheme;
    const statusLabels = {
      'pending': '待處理', 'completed': '已完成', 'ignored': '已忽略',
    };
    final threeDayText = threeDayCount == null
        ? '近三天：未統計'
        : '近三天：${complete ? '' : (threeDayCount >= 2000 ? '至少 ' : '')}$threeDayCount 封';
    final summary = !complete && remaining != null
        ? '$threeDayText · 待補 $remaining 封'
        : threeDayText;

    return Scaffold(body: RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.symmetric(
          horizontal: 14, vertical: 12), children: [
        Text('Gmail 智慧事項雷達',
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 2),
        Text('僅手動掃描；提醒僅文字初篩，並非確認真偽，請至官方管道查證。',
            style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 12),
        Row(children: [
          FilledButton.icon(
            key: const ValueKey('gmail-radar-quick-scan'),
            onPressed: _loading || _scanning || !granted ? null : () => _scan(),
            icon: _scanning
                ? const SizedBox.square(dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.radar, size: 18),
            label: Text(_scanning && !_backfilling && !_rechecking && !_sevenDay
                ? '掃描中' : '立即快掃'),
          ),
          const SizedBox(width: 6),
          if (granted && !_loading)
            PopupMenuButton<String>(
              key: const ValueKey('gmail-radar-scan-more'),
              enabled: !_scanning,
              tooltip: '更多掃描選項',
              icon: const Icon(Icons.more_horiz),
              onSelected: (value) {
                if (value == 'seven_day') _scan(sevenDay: true);
                if (value == 'backfill') _scan(backfill: true);
                if (value == 'recheck') _scan(recheck: true);
              },
              itemBuilder: (_) => [
                const PopupMenuItem(
                  value: 'seven_day',
                  child: Text('七天補檢（每次最多 40 封）'),
                ),
                if (needBackfill)
                  const PopupMenuItem(
                    value: 'backfill',
                    child: Text('三天補檢（尚未檢查）'),
                  ),
                const PopupMenuItem(
                  key: ValueKey('gmail-radar-three-day-recheck'),
                  value: 'recheck',
                  child: Text('重新檢查近三天'),
                ),
              ],
            ),
        ]),
        if (!granted && !_loading)
          Card(child: ListTile(
            title: const Text('尚未授權 Gmail'),
            subtitle: const Text('前往個人化 → Google 服務連結。'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.go('/more/personalize?tab=google'),
          )),
        if (_status['last_finished_at'] != null) ...[
          const SizedBox(height: 4),
          Card(
            child: ExpansionTile(
              key: const ValueKey('gmail-radar-scan-summary'),
              initiallyExpanded: _scanDetails,
              onExpansionChanged: (value) => _scanDetails = value,
              tilePadding: const EdgeInsets.symmetric(horizontal: 12),
              title: Text(summary, style: Theme.of(context).textTheme.bodyMedium),
              subtitle: Text('上次掃描：${_date(_status['last_finished_at'])}',
                  style: Theme.of(context).textTheme.bodySmall),
              childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              children: [
                if (LifeUiEnvironment.isCandidate)
                  Text('本次檢查 ${_status['checked'] ?? 0} 封 · 新增 ${_status['added'] ?? 0} 筆 · 失敗 ${_status['failed'] ?? 0} 封'),
                Text(complete ? '近三天已檢查完成（截至上次掃描）'
                    : '近三天仍有 ${remaining ?? '未知'} 封待補檢；超過 2000 封只統計已列出部分。'),
                if (sevenDayCount != null)
                  Text('七天已列出 $sevenDayCount 封 · 尚待補檢 ${_status['seven_day_remaining'] ?? '未知'} 封'),
              ],
            ),
          ),
        ],
        if (_error != null)
          Padding(padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(_error!, style: TextStyle(color: colors.error))),
        const SizedBox(height: 8),
        Row(children: [
          Text('事項', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(width: 12),
          PopupMenuButton<String>(
            key: const ValueKey('gmail-radar-filter'),
            initialValue: _filter,
            tooltip: '切換事項狀態',
            onSelected: (status) {
              if (status == _filter) return;
              setState(() => _filter = status);
              _load();
            },
            itemBuilder: (_) => [
              for (final entry in statusLabels.entries)
                PopupMenuItem(value: entry.key, child: Text(entry.value)),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(statusLabels[_filter]!, style: TextStyle(color: colors.primary)),
                const Icon(Icons.arrow_drop_down),
              ]),
            ),
          ),
          const Spacer(),
          if (_filter != 'pending')
            Text('每次顯示 $_pageSize 筆', style: Theme.of(context).textTheme.bodySmall),
        ]),
        const SizedBox(height: 4),
        if (_loading)
          const Center(child: Padding(
            padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
        else if (_items.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 12),
            child: Text(_status['last_finished_at'] == null
                ? '尚未掃描 Gmail，請按「立即快掃」。'
                : _filter != 'pending'
                    ? '沒有${statusLabels[_filter]}紀錄。'
                    : '目前沒有待處理事項。需要補檢或重判舊信，請開啟快掃旁的「⋯」。',
                textAlign: TextAlign.center),
          )
        else for (final item in _items) _itemCard(item),
        if (_hasMore && !_loading)
          Center(child: TextButton.icon(
            key: const ValueKey('gmail-radar-load-more'),
            onPressed: _loadingMore ? null : _loadMore,
            icon: _loadingMore
                ? const SizedBox.square(dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.expand_more),
            label: const Text('載入更多'),
          )),
        if (LifeUiEnvironment.isCandidate)
          Padding(padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text('快掃最多 20 封、補檢每輪最多 40 封；僅手動執行、不傳送 Gmail 內容給外部 AI。',
              style: Theme.of(context).textTheme.bodySmall)),
      ]),
    ));
  }

  Widget _itemCard(Map<String, dynamic> item) {
    final id = item['id']?.toString() ?? '';
    final url = item['gmail_url']?.toString() ?? '';
    final fallback = item['gmail_fallback_url']?.toString() ?? '';
    final pending = item['status'] == 'pending';
    final linkedTarget = item['linked_target']?.toString();
    final linkedRoute = item['linked_route']?.toString();
    final dateText = _date(item['received_at']);
    final due = item['due_date'] ?? item['due_text'];
    const targetLabels = {
      'task': '待辦', 'note': '筆記', 'shopping': '購物清單', 'calendar': '日曆',
    };
    const categoryLabels = {
      'billing': '帳單與繳費',
      'pickup': '包裹取貨',
      'booking': '預約與訂位',
      'travel': '交通與航班',
      'deadline': '期限與待辦',
      'security': '帳號／交易安全警告',
      'account': '帳號／訂閱費用警告',
      'refund': '退款／訂單異常',
      'administrative': '行政／學校／工作待辦',
      'authorization': '第三方應用程式授權／權限變更',
    };
    final category = categoryLabels[item['category']] ??
        (item['category']?.toString() ?? '未知');
    final actions = Wrap(
      spacing: 4,
      runSpacing: 0,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        if (pending && linkedTarget == null)
          TextButton.icon(
            key: ValueKey('gmail-radar-send-inbox-' + id),
            onPressed: () => context.go(
                '/capture?gmail_item=' + Uri.encodeComponent(id)),
            icon: const Icon(Icons.move_to_inbox_outlined, size: 18),
            label: const Text('送收件匣'),
          ),
        if (linkedTarget != null && linkedRoute != null)
          TextButton.icon(
            key: ValueKey('gmail-radar-linked-' + id),
            onPressed: () => context.go(linkedRoute),
            icon: const Icon(Icons.open_in_new, size: 18),
            label: Text('開啟' + (targetLabels[linkedTarget] ?? '已儲存功能')),
          ),
        if (_safeGmailUrl(url))
          IconButton(
            key: ValueKey('gmail-radar-open-source-' + id),
            tooltip: '開啟 Gmail 原信',
            onPressed: () => openExternalBrowser(url),
            icon: const Icon(Icons.open_in_new),
          ),
        PopupMenuButton<String>(
          key: ValueKey('gmail-radar-more-' + id),
          tooltip: '更多 Gmail 操作',
          icon: const Icon(Icons.more_horiz),
          onSelected: (action) {
            if (action == 'mailbox' && _safeGmailUrl(fallback)) {
              openExternalBrowser(fallback);
            } else if (action == 'complete' || action == 'restore') {
              _updateItem(id, action == 'complete' ? 'completed' : 'pending');
            } else if (action == 'ignore') {
              _updateItem(id, 'ignored');
            }
          },
          itemBuilder: (_) => [
            if (_safeGmailUrl(fallback))
              const PopupMenuItem(value: 'mailbox', child: Text('Gmail 信箱備援')),
            if (linkedTarget == null && !_updating.contains(id)) ...[
              PopupMenuItem(
                value: pending ? 'complete' : 'restore',
                child: Text(pending ? '手動標示完成' : '恢復待處理'),
              ),
              if (pending)
                const PopupMenuItem(value: 'ignore', child: Text('忽略')),
            ],
          ],
        ),
      ],
    );

    return Card(
      key: ValueKey('gmail-radar-item-' + id),
      margin: const EdgeInsets.only(bottom: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        ExpansionTile(
          key: ValueKey('gmail-radar-expand-' + id),
          tilePadding: const EdgeInsets.symmetric(horizontal: 12),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 6),
          title: Text(item['title']?.toString() ?? '', maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleSmall),
          subtitle: Text(
            '分類：$category · $dateText${due != null ? ' · 期限 $due' : ''}',
            maxLines: 2, overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall),
          children: [
            if ((item['sender']?.toString() ?? '').isNotEmpty)
              Align(alignment: Alignment.centerLeft,
                child: Text(item['sender'].toString(),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall)),
            if ((item['summary']?.toString() ?? '').isNotEmpty)
              Align(alignment: Alignment.centerLeft, child:
                Text(item['summary'].toString(), maxLines: 3,
                  overflow: TextOverflow.ellipsis)),
            if (item['classification_source'] == 'local_semantic')
              Align(alignment: Alignment.centerLeft, child:
                Text('本地語意模型建議，請自行確認',
                  style: Theme.of(context).textTheme.bodySmall)),
            if (linkedTarget != null)
              Align(alignment: Alignment.centerLeft, child:
                Text('已完成 · 已存入' + (targetLabels[linkedTarget] ?? 'Life'),
                  style: Theme.of(context).textTheme.bodySmall)),
            if (!pending) actions,
          ],
        ),
        if (pending)
          Padding(
            padding: const EdgeInsets.only(left: 8, right: 8, bottom: 4),
            child: Align(alignment: Alignment.centerLeft, child: actions),
          ),
      ]),
    );
  }
}
