import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'browser_navigation.dart';
import 'platform_api.dart';
import 'session_identity.dart';
import 'activity_link.dart';
import 'visual_system.dart';


String? activityDisplayDate(Object? value) {
  final raw = value?.toString().trim();
  if (raw == null || raw.length < 10 ||
      raw[4] != '-' || raw[7] != '-') return null;
  final parsed = DateTime.tryParse(raw);
  if (parsed == null) return null;
  final withTime = raw.contains('T') || raw.contains(' ');
  final offset = withTime &&
      (raw.endsWith('Z') || raw.substring(10).contains('+') ||
       raw.substring(10).contains('-'));
  final local = offset
      ? parsed.toUtc().add(const Duration(hours: 8)) : parsed;
  final date = '${local.year}/${local.month}/${local.day}';
  if (!withTime) return date;
  final hh = local.hour.toString().padLeft(2, '0');
  final mm = local.minute.toString().padLeft(2, '0');
  return '$date $hh:$mm';
}

/// Source and registration are independent. The official/organizer URL
/// automatically wins once it is available; source_url remains provenance.
Uri? activityInfoUrl(Map<String, dynamic> item) {
  final d = item['handoff_details'] as Map? ?? const {};
  return validActivityUrl(d['official_url']?.toString()) ??
      validActivityUrl(d['source_url']?.toString()) ??
      validActivityUrl(item['original_url']?.toString());
}

Uri? activityRegistrationUrl(Map<String, dynamic> item) {
  final d = item['handoff_details'] as Map? ?? const {};
  return validActivityUrl(d['registration_url']?.toString());
}

String activitySourceName(Uri url) {
  final host = url.host.toLowerCase();
  if (host == 'beclass.com' || host.endsWith('.beclass.com')) return 'BeClass';
  if (host == 'eventgo.tw' || host.endsWith('.eventgo.tw')) return 'EventGo';
  if (host == 'accupass.com' || host.endsWith('.accupass.com')) return 'ACCUPASS';
  if (host == 'kktix.com' || host.endsWith('.kktix.com') ||
      host == 'kktix.cc' || host.endsWith('.kktix.cc')) return 'KKTIX';
  if (host == 'yii.tw' || host.endsWith('.yii.tw')) return '小藝';
  return host.startsWith('www.') ? host.substring(4) : host;
}

String? activityPublicEligibility(Object? value) {
  final raw = value?.toString().trim();
  if (raw == null || raw.isEmpty) return null;
  const noise = ['NOT VERIFIED', '精選池', '稽核', '批次', '來源：',
    '索引', '快取', '回執', '核實來源', '資料可信度', '官方核實'];
  final segments = raw.split(RegExp(r'[；;\n]'))
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty && !noise.any((n) => s.contains(n)))
      .take(4).toList();
  return segments.isEmpty ? null : segments.join('；');
}

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


// A successful personal action invalidates cached results in both entry pages.
final curatedMutationEpochProvider = StateProvider<int>((ref) => 0);

final curatedPageActionsProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, ids) {
  ref.watch(curatedMutationEpochProvider);
  if (ref.watch(sessionIdentityProvider) == null) {
    throw StateError('Authentication required');
  }
  return ref.read(platformApiProvider).get('/free-events/curated/actions?activity_ids=$ids');
});

class CuratedActivityCard extends ConsumerStatefulWidget {
  const CuratedActivityCard({super.key, required this.items,
    this.entry = 'explore', this.onChanged, this.actionIds});
  final List<Map<String, dynamic>> items;
  final String entry;
  final VoidCallback? onChanged;
  /// Optional list of all visible activity IDs on the current server page.
  /// One scoped request is shared by sibling cards instead of an N+1 fetch.
  final String? actionIds;
  @override
  ConsumerState<CuratedActivityCard> createState() => _CuratedActivityCardState();
}

class _CuratedActivityCardState extends ConsumerState<CuratedActivityCard> {
  @override
  void didUpdateWidget(covariant CuratedActivityCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.items, widget.items)) savedOverride = null;
  }

  bool saving = false;
  String? message;
  bool? savedOverride;

  Map<String, dynamic> get main {
    for (final item in widget.items) {
      if ((item['handoff_details'] as Map?)?['record_type'] == 'main') return item;
    }
    return widget.items.first;
  }

  Uri? _url(Map<String, dynamic> item) {
    final d = item['handoff_details'] as Map? ?? const {};
    return validActivityUrl(d['registration_url']?.toString()) ??
      validActivityUrl(d['official_url']?.toString()) ??
      validActivityUrl(item['original_url']?.toString());
  }

  Future<void> _act(Map<String, dynamic> item, String kind, bool active,
      {Map<String, dynamic> data = const {}}) async {
    setState(() { saving = true; message = null; });
    try {
      await ref.read(platformApiProvider).put(
        '/free-events/curated/${item['identity_key']}/actions/$kind',
        {'active': active, ...data},
      );
      if (kind == 'save') savedOverride = active;
      ref.read(curatedMutationEpochProvider.notifier).state++;
      widget.onChanged?.call();
      if (mounted) setState(() => message = active ? '個人操作已建立' : '個人操作已更新');
    } catch (_) {
      if (mounted) setState(() => message = '操作未完成；請檢查資料、授權或連線。');
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _taskDialog(Map<String, dynamic> item) async {
    var title = '處理活動：${item['title'] ?? ''}';
    final d = item['handoff_details'] as Map? ?? const {};
    final open = d['registration_open_at_tpe']?.toString();
    final end = d['registration_deadline_at_tpe']?.toString() ??
        item['registration_deadline']?.toString();
    var selection = 'none';
    final choice = await showDialog<Map<String, String>>(
      context: context,
      builder: (dialog) => StatefulBuilder(builder: (dialog, redraw) =>
        AlertDialog(
          title: const Text('建立待辦'),
          content: SizedBox(width: 390, child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextFormField(
                initialValue: title,
                maxLength: 400,
                decoration: const InputDecoration(labelText: '待辦名稱'),
                onChanged: (value) => redraw(() => title = value),
              ),
              const Align(alignment: Alignment.centerLeft, child: Text('到期日選擇')),
              RadioGroup<String>(
                groupValue: selection,
                onChanged: (v) => redraw(() => selection = v ?? 'none'),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const RadioListTile<String>(value: 'none', title: Text('不設日期')),
                  if (open != null && open.contains('T'))
                    RadioListTile<String>(value: 'open',
                      title: Text('報名開放：${activityDisplayDate(open) ?? '待確認'}')),
                  if (end != null && end.contains('T'))
                    RadioListTile<String>(value: 'deadline',
                      title: Text('報名截止：${activityDisplayDate(end) ?? '待確認'}')),
                ]),
              ),
              const Text('會建立在原本待辦功能，並附上活動網址。'),
            ]),
          )),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialog),
              child: const Text('取消')),
            FilledButton(
              onPressed: title.trim().isEmpty ? null : () => Navigator.pop(dialog, {
                'task_title': title.trim(), 'task_due_choice': selection,
              }),
              child: const Text('建立'),
            ),
          ],
        ),
      ),
    );
    if (choice != null && mounted) await _act(item, 'task', true, data: choice);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();
    final item = main;
    final theme = Theme.of(context);
    final urgent = widget.entry == 'opportunities';
    final visualStyle = ref.watch(lifeAppearanceProvider).style;
    final accent = switch (visualStyle) {
      LifeVisualStyle.warm => urgent ? const Color(0xFFC77775) : const Color(0xFFB68B52),
      LifeVisualStyle.fresh => urgent ? const Color(0xFFF07665) : const Color(0xFF159E9A),
      LifeVisualStyle.focus => urgent ? const Color(0xFF777C9A) : const Color(0xFF527D8D),
      LifeVisualStyle.animated => urgent ? const Color(0xFFE57435) : const Color(0xFF357DC9),
      LifeVisualStyle.pinkBubble => urgent ? const Color(0xFFC74D8A) : const Color(0xFFAF609C),
    };
    final d = item['handoff_details'] as Map? ?? const {};
    final saved = savedOverride ?? widget.items.any((e) => e['saved'] == true);
    final ids = widget.actionIds ??
        widget.items.map((e) => e['identity_key']).join(',');
    final actions = ref.watch(curatedPageActionsProvider(ids));
    final values = (actions.asData?.value['items'] as List?) ?? const [];
    final nowTaipei = DateTime.now().toUtc().add(const Duration(hours: 8));
    final today = '${nowTaipei.year}-${nowTaipei.month.toString().padLeft(2, '0')}-${nowTaipei.day.toString().padLeft(2, '0')}';
    final endDate = item['ends_on']?.toString();
    final ended = endDate != null && DateTime.tryParse(endDate) != null &&
        endDate.substring(0, 10).compareTo(today) < 0;
    final full = urgent && item['registration_status'] == 'full';
    final closed = urgent && item['registration_status'] == 'closed';
    final cancelled = item['registration_status'] == 'cancelled' ||
        item['registration_status'] == 'canceled';
    final registrationOpen = d['registration_open_at_tpe']?.toString();
    final registrationDeadline = (d['registration_deadline_at_tpe'] ??
        item['registration_deadline'])?.toString();
    // Dates are displayed with their explicit meaning; activity start is not
    // substituted for an unverified registration opening/deadline.
    final pastDeadline = urgent && registrationDeadline != null &&
        registrationDeadline.length >= 10 &&
        DateTime.tryParse(registrationDeadline.substring(0, 10)) != null &&
        registrationDeadline.substring(0, 10).compareTo(today) < 0;
    final rawTags = item['tags'] as List? ?? (d['tags'] as List? ?? []);
    final tags = rawTags.map((e) => e?.toString() ?? '').where((s) => s.isNotEmpty).toList();

    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(gradient: LinearGradient(
            colors: [accent.withValues(alpha: .14), theme.colorScheme.surface])),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(width: 52, height: 52,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: .15),
                borderRadius: BorderRadius.circular(17)),
              child: Icon(urgent ? Icons.confirmation_number_outlined :
                Icons.explore_outlined, color: accent, size: 28)),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(item['title']?.toString() ?? '未命名活動',
                style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 5),
              // Raw summary/evidence_summary are internal provenance notes.
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: [
                if (urgent && activityDisplayDate(registrationOpen) != null)
                  _EventChip(Icons.event_outlined, '開報：${activityDisplayDate(registrationOpen)}'),
                if (urgent && activityDisplayDate(registrationDeadline) != null)
                  _EventChip(Icons.event_busy_outlined, '截止：${activityDisplayDate(registrationDeadline)}'),
                if (!urgent && activityDisplayDate(item['starts_on']) != null)
                  _EventChip(Icons.event_outlined, '活動：${activityDisplayDate(item['starts_on'])}${activityDisplayDate(item['ends_on']) != null && activityDisplayDate(item['ends_on']) != activityDisplayDate(item['starts_on']) ? ' ～ ${activityDisplayDate(item['ends_on'])}' : ''}'),
                _EventChip(Icons.place_outlined, item['city']?.toString() ?? '地區待確認'),
                for (final tag in tags)
                  _TagChip(tag),
                if (d['verification_status'] == 'pending_review')
                  const _EventChip(Icons.fact_check_outlined, '資訊待確認'),
                if (d['verification_status'] == 'verified')
                  const _EventChip(Icons.verified_outlined, '已核實'),
                if (item['fee_kind'] == 'free')
                  const _EventChip(Icons.sell_outlined, '免費'),
                if (item['fee_kind'] == 'paid')
                  const _EventChip(Icons.sell_outlined, '付費'),
                if (item['fee_kind'] == 'conditional_free')
                  const _EventChip(Icons.sell_outlined, '條件免費'),
                if (cancelled)
                  const _EventChip(Icons.event_busy_outlined, '已取消'),
                if (!cancelled && (ended || closed || pastDeadline))
                  const _EventChip(Icons.event_busy_outlined, '已結束／截止'),
                if (full)
                  const _EventChip(Icons.info_outline, '已額滿'),
                if (widget.items.length > 1)
                  _EventChip(Icons.layers_outlined, '${widget.items.length} 個場次'),
              ]),
            ])),
            IconButton(
              key: ValueKey('activity-bookmark-${item['identity_key']}'),
              tooltip: saved ? '取消收藏' : '收藏',
              icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border,
                color: saved ? accent : null),
              onPressed: saving ? null : () => _act(item, 'save', !saved)),
          ]),
        ),
        for (final child in widget.items)
          ExpansionTile(
            key: ValueKey('activity-detail-${child['identity_key']}'),
            initiallyExpanded: false,
            title: Text(widget.items.length == 1 ? '查看詳情與操作' :
              (child['title'] == item['title']
                  ? '第 ${widget.items.indexOf(child) + 1} 場｜詳情'
                  : (child['title']?.toString() ?? '相關場次'))),
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              Align(alignment: Alignment.centerLeft, child: Column(
                crossAxisAlignment: CrossAxisAlignment.start, children: [
                  for (final line in _details(child))
                    Padding(padding: const EdgeInsets.only(bottom: 5),
                      child: Text(line, maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall)),
                  if (activityInfoUrl(child) case final source?)
                    Align(alignment: Alignment.centerLeft,
                      child: TextButton.icon(
                        key: ValueKey('activity-source-${child['identity_key']}'),
                        onPressed: () => ref.read(browserNavigationProvider)
                            .openExternal(source.toString()),
                        icon: const Icon(Icons.link, size: 17),
                        label: Text('來源：${activitySourceName(source)}'),
                      )),
                  const Text('報名與名額請以活動網站為準。'),
                  const SizedBox(height: 8),
                  Wrap(spacing: 8, runSpacing: 7, children: [
                    if (_url(child) case final url?)
                      FilledButton.icon(
                        key: ValueKey('activity-url-${child['identity_key']}'),
                        onPressed: () => ref.read(browserNavigationProvider)
                          .openExternal(url.toString()),
                        icon: const Icon(Icons.open_in_new, size: 18),
                        label: Text(activityRegistrationUrl(child) == null
                          ? '查看活動' : '前往報名')),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.add_task),
                      label: Text(values.any((a) => a['activity_id'] == child['identity_key'] &&
                          a['kind'] == 'task' && a['active'] == true) ? '取消活動待辦' : '建立待辦'),
                      onPressed: saving || actions.isLoading || actions.hasError
                        ? null : () async {
                          final active = values.any((a) => a['activity_id'] == child['identity_key'] &&
                            a['kind'] == 'task' && a['active'] == true);
                          if (active) {
                            await _act(child, 'task', false);
                          } else {
                            await _taskDialog(child);
                          }
                        }),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.event_available_outlined),
                      label: Text(values.any((a) => a['activity_id'] == child['identity_key'] &&
                          a['kind'] == 'calendar_info' && a['active'] == true)
                          ? '移除日期標記' : '日曆日期標記'),
                      onPressed: saving || actions.isLoading || actions.hasError ||
                          child['starts_on'] == null
                        ? null : () async {
                          final active = values.any((a) => a['activity_id'] == child['identity_key'] &&
                            a['kind'] == 'calendar_info' && a['active'] == true);
                          await _act(child, 'calendar_info', !active);
                        }),
                  ]),
                ],
              )),
            ],
          ),
        if (actions.isLoading) const LinearProgressIndicator(minHeight: 2),
        if (actions.hasError)
          const Padding(padding: EdgeInsets.all(12),
            child: Text('個人操作狀態暫時無法取得')),
        if (message != null) Padding(padding: const EdgeInsets.all(12),
          child: Text(message!, style: theme.textTheme.bodySmall)),
      ]),
    );
  }

  List<String> _details(Map<String, dynamic> item) {
    final d = item['handoff_details'] as Map? ?? const {};
    final rows = <String>[];
    final start = activityDisplayDate(item['starts_on'] ?? d['start_at_tpe']);
    final end = activityDisplayDate(item['ends_on'] ?? d['end_at_tpe']);
    if (start != null) {
      rows.add('活動：$start${end != null && end != start ? ' ～ $end' : ''}');
    }
    if (d['organizer']?.toString().trim().isNotEmpty == true) {
      rows.add('主辦：${d['organizer']}');
    }
    final venue = d['venue'] ?? item['city'];
    if (venue?.toString().trim().isNotEmpty == true) rows.add('地點：$venue');
    final opening = activityDisplayDate(d['registration_open_at_tpe']);
    if (opening != null) rows.add('開放報名：$opening');
    final deadline = activityDisplayDate(
        d['registration_deadline_at_tpe'] ?? item['registration_deadline']);
    if (deadline != null) rows.add('報名截止：$deadline');
    final fee = switch (item['fee_kind']) {
      'free' => '免費',
      'paid' => '付費',
      'conditional_free' => '條件免費',
      _ => '待確認',
    };
    rows.add('費用：$fee');
    final eligibility = activityPublicEligibility(d['eligibility_limit']);
    if (eligibility != null) rows.add('報名條件：$eligibility');
    final rawTags = item['tags'] as List? ?? (d['tags'] as List? ?? []);
    final tags = rawTags.map((e) => e?.toString() ?? '').where((s) => s.isNotEmpty).toList();
    if (tags.isNotEmpty) rows.add('分類標籤：${tags.join("、")}');
    return rows;
  }
}

class _TagChip extends StatelessWidget {
  const _TagChip(this.label);
  final String label;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: theme.colorScheme.primaryContainer.withValues(alpha: .5),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.label_outline, size: 13, color: theme.colorScheme.onPrimaryContainer),
        const SizedBox(width: 4),
        Text(label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.onPrimaryContainer,
            fontWeight: FontWeight.w600,
          )),
      ]),
    );
  }
}

class _EventChip extends StatelessWidget {
  const _EventChip(this.icon, this.label);
  final IconData icon;
  final String label;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(20)),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 15, color: Theme.of(context).colorScheme.primary),
      const SizedBox(width: 5),
      Text(label, style: Theme.of(context).textTheme.labelSmall),
    ]),
  );
}
