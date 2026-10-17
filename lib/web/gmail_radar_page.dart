import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'browser_navigation.dart';
import 'platform_api.dart';

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
  String? _error;
  String _filter = 'pending';
  Map<String, dynamic> _status = const {};
  List<Map<String, dynamic>> _items = const [];
  final Set<String> _updating = {};

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() { _loading = true; _error = null; });
    try {
      final api = ref.read(platformApiProvider);
      final status = await api.get('/integrations/google/gmail/radar/status');
      final items = await api.get('/integrations/google/gmail/radar/items?status=' + _filter);
      if (!mounted) return;
      setState(() {
        _status = status;
        _items = (items['items'] as List? ?? const [])
            .map((e) => Map<String, dynamic>.from(e as Map)).toList();
      });
    } catch (_) {
      if (mounted) setState(() => _error = '無法取得 Gmail 事項，請重新整理。');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _scan({bool backfill = false, bool recheck = false}) async {
    if (_scanning || _status['gmail_authorized'] != true) return;
    setState(() {
      _scanning = true;
      _backfilling = backfill;
      _rechecking = recheck;
      _error = null;
    });
    try {
      final r = await ref.read(platformApiProvider).post(
        recheck
            ? '/integrations/google/gmail/radar/recheck-three-days'
            : backfill
                ? '/integrations/google/gmail/radar/backfill-three-days'
                : '/integrations/google/gmail/radar/quick-scan', const {});
      if (!mounted) return;
      final count = r['three_day_count'] ?? '未知';
      final remaining = r['three_day_remaining'] ?? '未知';
      final countText = r['three_day_count_capped'] == true
          ? '至少$count' : '$count';
      final message = (recheck ? '重新判讀' : backfill ? '三天補檢' : '快掃') +
        '：近三天 $countText 封，本次檢查 ' + (r['checked'] ?? 0).toString() +
        ' 封，新增事項 ' + (r['added'] ?? 0).toString() +
        ' 筆，未檢查 ' + remaining.toString() +
        ' 封，失敗 ' + (r['failed'] ?? 0).toString() + ' 封';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (_) {
      if (mounted) setState(() =>
          _error = 'Gmail 掃描未完成。請稍後重試；若持續失敗，請提供發生時間以查詢紀錄。';
    } finally {
      if (mounted) setState(() {
        _scanning = false;
        _backfilling = false;
        _rechecking = false;
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
    final threeDayRemaining = _status['three_day_remaining'] as int?;
    final needBackfill = granted && (threeDayRemaining ?? 0) > 0;
    final threeDayComplete = _status['three_day_complete'] == true;
    return Scaffold(body: RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 12, runSpacing: 12, children: [
          const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Gmail 智慧事項雷達',
                style: TextStyle(fontSize: 23, fontWeight: FontWeight.w700)),
            Text('只有按下快掃才會檢查自己的 Gmail。'),
            Text('安全或費用類警告僅依文字初篩，並非確認真偽；請從官方網站或 App 查證。',
                style: TextStyle(fontSize: 12)),
          ]),
          FilledButton.icon(
            key: const ValueKey('gmail-radar-quick-scan'),
            onPressed: _loading || _scanning || !granted ? null : () => _scan(),
            icon: _scanning
                ? const SizedBox.square(dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.radar),
            label: Text(_scanning && !_backfilling ? '掃描中' : '立即快掃'),
          ),
          if (needBackfill)
            OutlinedButton.icon(
              key: const ValueKey('gmail-radar-three-day-backfill'),
              onPressed: _loading || _scanning ? null : () => _scan(backfill: true),
              icon: const Icon(Icons.manage_search),
              label: Text(_scanning && _backfilling ? '補檢中' : '三天補檢'),
            ),
          if (granted && !_loading)
            OutlinedButton.icon(
              key: const ValueKey('gmail-radar-three-day-recheck'),
              onPressed: _scanning ? null : () => _scan(recheck: true),
              icon: const Icon(Icons.refresh),
              label: Text(_scanning && _rechecking
                  ? '重新判讀中' : '重新檢查近三天'),
            ),
        ]),
        const SizedBox(height: 12),
        if (!granted && !_loading) Card(child: ListTile(
          title: const Text('尚未授權 Gmail'),
          subtitle: const Text('前往個人化 → Google 服務連結，授權自己的 Gmail。'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => context.go('/more/personalize?tab=google'),
        )),
        if (_status['last_finished_at'] != null)
          Card(
            key: const ValueKey('gmail-radar-three-day-summary'),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('最近三天：' +
                      (threeDayCount == null ? '尚未統計' :
                          (threeDayComplete || threeDayCount < 2000
                              ? '${threeDayCount} 封' : '至少 ${threeDayCount} 封')),
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text('本次' + (_status['scan_kind'] == 'recheck'
                      ? '重新判讀' : _status['scan_kind'] == 'backfill'
                          ? '補檢' : '快掃') +
                      '檢查 ${_status['checked'] ?? 0} 封，新增事項 ' +
                      '${_status['added'] ?? 0} 筆，失敗 ${_status['failed'] ?? 0} 封'),
                  Text(threeDayComplete
                      ? '近三天郵件已全部檢查（截至上次掃描）'
                      : '尚待補檢 ${threeDayRemaining ?? '未知'} 封；'
                        '若郵件量超過 2000 封，統計可能尚未涵蓋全部郵件。'),
                  Text('上次掃描：' + _date(_status['last_finished_at']),
                    style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ),
        if (_error != null) Card(child: Padding(
          padding: const EdgeInsets.all(12),
          child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        )),
        Wrap(spacing: 8, children: [
          for (final group in const [
            ('pending', '待處理'), ('completed', '已完成'), ('ignored', '已忽略')
          ]) ChoiceChip(
            label: Text(group.$2),
            selected: _filter == group.$1,
            onSelected: (selected) {
              if (!selected) return;
              setState(() => _filter = group.$1);
              _load();
            },
          ),
        ]),
        const SizedBox(height: 10),
        if (_loading) const Center(child: Padding(
          padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
        else if (_items.isEmpty) const Card(child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('目前沒有符合條件的 Gmail 事項。第一次使用請按「立即快掃」。',
              textAlign: TextAlign.center)))
        else for (final item in _items) _itemCard(item),
        const SizedBox(height: 12),
        Text('快掃檢查最近 7 天最新最多 20 封；三天補檢每次補查 40 封未檢查郵件。'
          '結果保留已處理 ID 去重；「重新檢查近三天」每次最多重新判讀最新 40 封，'
          '包括 Life 過去略過的郵件，不會刪除已完成事項；'
          '未使用 Gemini，不執行背景排程或推播。原信若無法定位，可改由 Gmail 開啟。',
          style: Theme.of(context).textTheme.bodySmall),
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

    return Card(key: ValueKey('gmail-radar-item-' + id),
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(item['title']?.toString() ?? '', maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(item['sender']?.toString() ?? '', maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(item['summary']?.toString() ?? '', maxLines: 3,
              overflow: TextOverflow.ellipsis),
          const SizedBox(height: 6),
          Text('分類：' + (categoryLabels[item['category']] ??
                  (item['category']?.toString() ?? '未知')) +
              '　郵件時間：' + _date(item['received_at']),
              style: Theme.of(context).textTheme.bodySmall),
          if (linkedTarget != null)
            Text('已完成 · 已存入' + (targetLabels[linkedTarget] ?? 'Life'),
                style: Theme.of(context).textTheme.bodySmall),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              if (linkedTarget == null && pending)
                TextButton.icon(
                  key: ValueKey('gmail-radar-send-inbox-' + id),
                  onPressed: () => context.go(
                      '/capture?gmail_item=' + Uri.encodeComponent(id)),
                  icon: const Icon(Icons.move_to_inbox_outlined),
                  label: const Text('送到生活收件匣'),
                ),
              if (linkedTarget != null && linkedRoute != null)
                TextButton.icon(
                  key: ValueKey('gmail-radar-linked-' + id),
                  onPressed: () => context.go(linkedRoute),
                  icon: const Icon(Icons.open_in_new),
                  label: Text('開啟' + (targetLabels[linkedTarget] ?? '已儲存功能')),
                ),
              if (_safeGmailUrl(url))
                TextButton.icon(
                  key: ValueKey('gmail-radar-open-source-' + id),
                  onPressed: () => openExternalBrowser(url),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('開啟 Gmail 原信'),
                ),
              PopupMenuButton<String>(
                key: ValueKey('gmail-radar-more-' + id),
                tooltip: '更多 Gmail 操作',
                icon: const Icon(Icons.more_horiz),
                onSelected: (action) {
                  if (action == 'mailbox' &&
                      _safeGmailUrl(fallback)) {
                    openExternalBrowser(fallback);
                  } else if (action == 'complete' || action == 'restore') {
                    _updateItem(id, action == 'complete' ? 'completed' : 'pending');
                  } else if (action == 'ignore') {
                    _updateItem(id, 'ignored');
                  }
                },
                itemBuilder: (_) => [
                  if (_safeGmailUrl(fallback))
                    const PopupMenuItem(
                      value: 'mailbox',
                      child: Text('Gmail 信箱備援'),
                    ),
                  if (linkedTarget == null && !_updating.contains(id)) ...[
                    PopupMenuItem(
                      value: pending ? 'complete' : 'restore',
                      child: Text(pending ? '手動標示完成' : '恢復待處理'),
                    ),
                    if (pending)
                      const PopupMenuItem(
                        value: 'ignore',
                        child: Text('忽略'),
                      ),
                  ],
                ],
              ),
            ],
          ),
        ]),
      ),
    );
  }
}
