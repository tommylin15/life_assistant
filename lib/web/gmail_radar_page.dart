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

  Future<void> _scan() async {
    if (_scanning || _status['gmail_authorized'] != true) return;
    setState(() { _scanning = true; _error = null; });
    try {
      final r = await ref.read(platformApiProvider).post(
        '/integrations/google/gmail/radar/quick-scan', const {});
      if (!mounted) return;
      final message = '快掃' + (r['status'] == 'partial' ? '部分完成' : '完成') +
        '：檢查 ' + (r['checked'] ?? 0).toString() +
        ' 封，新增 ' + (r['added'] ?? 0).toString() +
        ' 筆，略過 ' + (r['skipped'] ?? 0).toString() +
        ' 筆，失敗 ' + (r['failed'] ?? 0).toString() + ' 筆';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
      await _load();
    } catch (_) {
      if (mounted) setState(() =>
          _error = '快掃未完成。請確認 Gmail 授權、網路連線，以及是否有其他快掃正在進行。');
    } finally {
      if (mounted) setState(() => _scanning = false);
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
          ]),
          FilledButton.icon(
            key: const ValueKey('gmail-radar-quick-scan'),
            onPressed: _loading || _scanning || !granted ? null : _scan,
            icon: _scanning
                ? const SizedBox.square(dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.radar),
            label: Text(_scanning ? '掃描中' : '立即快掃'),
          ),
        ]),
        const SizedBox(height: 12),
        if (!granted && !_loading) Card(child: ListTile(
          title: const Text('尚未授權 Gmail'),
          subtitle: const Text('前往個人化 → Google 服務連結，授權自己的 Gmail。'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => context.go('/more/personalize?tab=google'),
        )),
        if (_status['last_finished_at'] != null) Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text('上次快掃：' + _date(_status['last_finished_at']) +
            '　已檢查 ' + (_status['checked'] ?? 0).toString() +
            ' 封，新增 ' + (_status['added'] ?? 0).toString() + ' 筆',
            style: Theme.of(context).textTheme.bodySmall),
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
        Text('本版使用規則篩選最近 7 天最多 20 封郵件；不傳送郵件正文給 AI，'
          '不執行每小時排程或自動推播。原信如未能定位，可改用 Gmail 信箱入口。',
          style: Theme.of(context).textTheme.bodySmall),
      ]),
    ));
  }

  Widget _itemCard(Map<String, dynamic> item) {
    final id = item['id']?.toString() ?? '';
    final url = item['gmail_url']?.toString() ?? '';
    final fallback = item['gmail_fallback_url']?.toString() ?? '';
    final pending = item['status'] == 'pending';
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
          Text('分類：' + (item['category']?.toString() ?? '') +
              '　郵件時間：' + _date(item['received_at']),
              style: Theme.of(context).textTheme.bodySmall),
          Wrap(spacing: 8, children: [
            if (url.startsWith('https://mail.google.com/'))
              TextButton.icon(
                onPressed: () => openExternalBrowser(url),
                icon: const Icon(Icons.open_in_new),
                label: const Text('開啟 Gmail 原信'),
              ),
            if (fallback.startsWith('https://mail.google.com/'))
              TextButton(
                onPressed: () => openExternalBrowser(fallback),
                child: const Text('Gmail 信箱備援'),
              ),
            TextButton(
              onPressed: _updating.contains(id) ? null :
                  () => _updateItem(id, pending ? 'completed' : 'pending'),
              child: Text(pending ? '標示完成' : '恢復待處理'),
            ),
            if (pending) TextButton(
              onPressed: _updating.contains(id) ? null :
                  () => _updateItem(id, 'ignored'),
              child: const Text('忽略'),
            ),
          ]),
        ]),
      ),
    );
  }
}
