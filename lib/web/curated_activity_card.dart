import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'browser_navigation.dart';
import 'platform_api.dart';
import 'session_identity.dart';

final curatedActionsProvider = FutureProvider<Map<String, dynamic>>((ref) {
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  return ref.read(platformApiProvider).get('/free-events/curated/actions');
});

List<List<Map<String, dynamic>>> groupActivities(List<Map<String, dynamic>> items) {
  final groups = <String, List<Map<String, dynamic>>>{};
  for (final item in items) {
    final handoffKey = item['parent_event_key'] ?? item['handoff_event_key'];
    final key = handoffKey == null ? 'legacy:${item['identity_key']}' : 'handoff:$handoffKey';
    groups.putIfAbsent(key, () => []).add(item);
  }
  return groups.values.map((group) {
    group.sort((a, b) => ((a['handoff_details'] as Map?)?['record_type'] == 'main' ? 0 : 1)
        .compareTo((b['handoff_details'] as Map?)?['record_type'] == 'main' ? 0 : 1));
    return group;
  }).toList();
}

class CuratedActivityCard extends ConsumerStatefulWidget {
  const CuratedActivityCard({super.key, required this.items});
  final List<Map<String, dynamic>> items;
  @override
  ConsumerState<CuratedActivityCard> createState() => _CuratedActivityCardState();
}

class _CuratedActivityCardState extends ConsumerState<CuratedActivityCard> {
  bool saving = false;
  String? message;
  static const kinds = {
    'save': '收藏', 'follow': '追蹤', 'task': '加入待辦',
    'calendar_info': '標記活動日期（不占用時間）',
    'calendar_registration': '標記報名時間', 'calendar_confirmed': '確定參與行程',
    'reminder': '報名提前提醒（Google Calendar）',
  };
  static const trackingStatuses = {'interested': '想報名', 'waiting': '等開放',
    'submitted': '已送出／待確認', 'confirmed': '成功', 'waitlisted': '候補',
    'failed': '失敗', 'cancelled': '取消'};

  Future<void> change(Map<String, dynamic> item, String kind, bool active) async {
    final body = <String, dynamic>{'active': active};
    if (active && kind == 'follow') {
      final status = await showDialog<String>(context: context, builder: (ctx) => SimpleDialog(
        title: const Text('個人追蹤狀態（不代表官方報名結果）'), children: [
          for (final entry in trackingStatuses.entries)
            SimpleDialogOption(onPressed: () => Navigator.pop(ctx, entry.key), child: Text(entry.value)),
        ],
      ));
      if (status == null || !mounted) return;
      body['tracking_status'] = status;
    }
    if (active && (kind == 'calendar_registration' || kind == 'reminder')) {
      final phase = await showDialog<String>(context: context, builder: (ctx) => SimpleDialog(
        title: const Text('選擇提醒時點'), children: [
          SimpleDialogOption(onPressed: () => Navigator.pop(ctx, 'open'), child: const Text('報名開放')),
          SimpleDialogOption(onPressed: () => Navigator.pop(ctx, 'deadline'), child: const Text('報名截止')),
        ],
      ));
      if (phase == null || !mounted) return;
      body['phase'] = phase;
      if (kind == 'reminder') {
        final lead = await showDialog<int>(context: context, builder: (ctx) => SimpleDialog(
          title: const Text('提前多久提醒'), children: [
            for (final minutes in [60, 1440]) SimpleDialogOption(
              onPressed: () => Navigator.pop(ctx, minutes),
              child: Text(minutes == 60 ? '一小時' : '一天'),
            ),
          ],
        ));
        if (lead == null || !mounted) return;
        body['lead_minutes'] = lead;
      }
    }
    if (active && kind == 'calendar_confirmed') {
      final day = await showDatePicker(context: context, initialDate: DateTime.now(),
          firstDate: DateTime(2000), lastDate: DateTime(2100));
      if (day == null || !mounted) return;
      final start = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 9, minute: 0), helpText: '實際參與開始');
      if (start == null || !mounted) return;
      final end = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 10, minute: 0), helpText: '實際參與結束');
      if (end == null || !mounted) return;
      final begins = DateTime(day.year, day.month, day.day, start.hour, start.minute);
      final ends = DateTime(day.year, day.month, day.day, end.hour, end.minute);
      if (!ends.isAfter(begins)) {
        setState(() => message = '結束時間必須晚於開始時間');
        return;
      }
      body['start'] = begins.toUtc().toIso8601String();
      body['end'] = ends.toUtc().toIso8601String();
    }
    setState(() { saving = true; message = null; });
    try {
      await ref.read(platformApiProvider).put('/free-events/curated/${item['identity_key']}/actions/$kind', body);
      ref.invalidate(curatedActionsProvider);
      if (mounted) setState(() => message = active ? '已加入' : '已取消；原待辦會標為取消');
    } catch (_) {
      if (mounted) setState(() => message = '未完成操作。請確認日期／報名時間、Google Calendar 授權或連線，再重試。');
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final actions = ref.watch(curatedActionsProvider);
    final values = (actions.asData?.value['items'] as List?) ?? const [];
    final main = widget.items.first;
    return Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(
      crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(main['title']?.toString() ?? '', style: Theme.of(context).textTheme.titleMedium),
        if (widget.items.length > 1) Text('${widget.items.length} 個活動／優惠／場次，合併顯示'),
        for (final item in widget.items) ExpansionTile(
          initiallyExpanded: widget.items.length == 1,
          title: Text(item['title']?.toString() ?? ''),
          subtitle: Text('${'★' * ((item['importance'] as num?)?.toInt() ?? 1)} · ${item['city'] ?? '地區未知'}'),
          children: [Padding(padding: const EdgeInsets.all(8), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('活動日期：${item['starts_on'] ?? '未知'} ～ ${item['ends_on'] ?? '未知'}'),
              Text('不可退費用：${item['fee_amount'] ?? '未知'} · 福利面額：${item['benefit_value'] ?? '未知'}'),
              ..._details(item),
              const Text('星等代表價值；不代表已開放報名或仍有名額。'),
              Wrap(children: [
                TextButton.icon(icon: const Icon(Icons.open_in_new), label: const Text('活動原頁'),
                  onPressed: () => ref.read(browserNavigationProvider).openExternal(item['original_url'].toString())),
                if ((item['handoff_details'] as Map?)?['registration_url'] != null)
                  TextButton(onPressed: () => ref.read(browserNavigationProvider).openExternal(
                      (item['handoff_details'] as Map)['registration_url'].toString()), child: const Text('報名／優惠原頁')),
              ]),
              if (actions.isLoading) const LinearProgressIndicator(),
              if (actions.hasError) const Text('無法讀取個人操作狀態，請重新整理。'),
              Wrap(spacing: 6, children: [for (final kind in kinds.keys)
                FilterChip(label: Text(kinds[kind]!),
                  selected: values.any((a) => a['activity_id'] == item['identity_key'] && a['kind'] == kind && a['active'] == true),
                  onSelected: saving || actions.isLoading || actions.hasError ? null : (active) => change(item, kind, active)),
              ]),
              for (final action in values.where((a) => a['activity_id'] == item['identity_key'] && a['kind'] == 'follow' && a['active'] == true))
                Text('個人追蹤：${trackingStatuses[(action['payload'] as Map?)?['tracking_status']] ?? '未知'}（不代表官方報名結果）'),
              if (values.any((a) => a['activity_id'] == item['identity_key'] && a['kind'] == 'follow' && a['active'] == true))
                TextButton(onPressed: saving ? null : () => change(item, 'follow', true), child: const Text('更新個人追蹤狀態')),
            ],
          ))],
        ),
        if (message != null) Text(message!),
      ],
    )));
  }

  List<Widget> _details(Map<String, dynamic> item) {
    final details = item['handoff_details'] as Map? ?? const {};
    return [
      Text('主辦：${details['organizer'] ?? '未知'} · 分類：${item['category'] ?? '未知'}'),
      Text('活動類型：${details['opportunity_type'] ?? '未知'} · 區域：${details['district'] ?? '未知'}'),
      Text('活動時段：${details['start_at_tpe'] ?? item['starts_on'] ?? '未知'} ～ ${details['end_at_tpe'] ?? item['ends_on'] ?? '未知'}'),
      Text('報名開放：${details['registration_open_at_tpe'] ?? '未知'}'),
      Text('報名截止：${details['registration_deadline_at_tpe'] ?? item['registration_deadline'] ?? '未知'}'),
      Text('可退押金：${details['refundable_deposit_ntd'] ?? '未知'}；退款／資格條件：${details['eligibility_limit'] ?? '請查主辦原頁'}'),
      Text('地點：${details['venue'] ?? '未知'}'),
      Text('來源證據：${details['evidence_summary'] ?? item['summary'] ?? '待核'}'),
      Text('查核時間：${details['verified_at_tpe'] ?? '未知'}'),
    ];
  }
}
