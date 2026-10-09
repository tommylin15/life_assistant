import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../app/design_system/app_components.dart';
import '../app/theme/app_tokens.dart';
import 'browser_navigation.dart';
import 'free_events_api.dart';

final _verifiedFreeEvents = FutureProvider<List<_FreeEventCard>>((ref) async {
  final api = ref.read(freeEventsApiProvider);
  return (await api.listVerified())
      .map((json) => _FreeEventCard.fromJson(json))
      .toList();
});

class FreeEventsPage extends ConsumerWidget {
  const FreeEventsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(_verifiedFreeEvents);

    void reload() => ref.invalidate(_verifiedFreeEvents);

    return Scaffold(
      appBar: AppBar(
        title: const Text('免費活動探索'),
        actions: [
          IconButton(
            tooltip: '重新整理活動',
            onPressed: reload,
            icon: const Icon(Icons.refresh_outlined),
          ),
        ],
      ),
      body: state.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppStatePanel(
          title: '無法載入活動',
          message: '目前無法取得已驗證活動。請檢查網路或稍後重試。',
          icon: Icons.cloud_off_outlined,
          action: OutlinedButton.icon(
            onPressed: reload,
            icon: const Icon(Icons.refresh),
            label: const Text('重試'),
          ),
        ),
        data: (events) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(_verifiedFreeEvents);
            await ref.read(_verifiedFreeEvents.future);
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              AppPageFrame(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('台灣免費活動', style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: AppSpacing.sm),
                    const Text('僅顯示來源與免費條件已核實的活動。報名狀態可能改變，請再到主辦方確認。'),
                    const SizedBox(height: AppSpacing.lg),
                    if (events.isEmpty)
                      const AppStatePanel(
                        title: '目前沒有已核實的免費活動',
                        message: '來源尚在查證或目前沒有符合條件的活動。未核實候選不會顯示。',
                        icon: Icons.event_busy_outlined,
                      )
                    else
                      for (final item in events) ...[
                        _EventCard(item: item),
                        const SizedBox(height: AppSpacing.md),
                      ],
                    const SizedBox(height: 56),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EventCard extends ConsumerWidget {
  const _EventCard({required this.item});
  final _FreeEventCard item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final navigator = ref.read(browserNavigationProvider);
    final starts = item.startsOn ?? item.startsAt;
    final when = starts == null
        ? '日期待主辦公告'
        : item.startsOn != null
            ? DateFormat('yyyy/M/d').format(item.startsOn!)
            : DateFormat('yyyy/M/d HH:mm').format(item.startsAt!.toLocal());
    final where = [item.city, item.venue]
        .whereType<String>()
        .where((s) => s.isNotEmpty)
        .join(' · ');
    final feeText = item.feeKind == 'conditional_free'
        ? '有條件免費（請看資格）'
        : '已核實免費';
    final canClaimWindow = item.windowConfirmedOpen;
    final registerText = canClaimWindow
        ? '已核實報名時段 · 原站仍需確認名額'
        : item.registrationOpensAt == null
            ? '報名開始時間未確認'
            : '報名是否開放仍待確認';
    return AppSectionCard(
      title: item.title,
      subtitle: when,
      action: IconButton(
        key: ValueKey('free-event-source-${item.opportunityId}'),
        tooltip: '檢視官方來源：${item.title}',
        icon: const Icon(Icons.open_in_new),
        onPressed: () => navigator.openExternal(item.officialUrl),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (item.summary?.isNotEmpty == true) ...[
            Text(item.summary!),
            const SizedBox(height: AppSpacing.sm),
          ],
          if (where.isNotEmpty) Text(where),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              AppStatusChip(label: feeText, icon: Icons.sell_outlined),
              AppStatusChip(
                label: registerText,
                icon: canClaimWindow
                    ? Icons.event_available_outlined
                    : Icons.schedule_outlined,
              ),
            ],
          ),
          if (item.eligibilityNote?.isNotEmpty == true) ...[
            const SizedBox(height: AppSpacing.sm),
            Text('免費資格：${item.eligibilityNote}'),
          ],
          const SizedBox(height: AppSpacing.sm),
          TextButton.icon(
            key: ValueKey('free-event-register-${item.opportunityId}'),
            onPressed: () => navigator.openExternal(item.registrationUrl),
            icon: const Icon(Icons.open_in_new),
            label: const Text('前往主辦／報名原站'),
          ),
          const Text('前往原站不代表已報名；請自行確認是否額滿與費用。'),
        ],
      ),
    );
  }
}

class _FreeEventCard {
  const _FreeEventCard({
    required this.opportunityId,
    required this.title,
    required this.summary,
    required this.city,
    required this.venue,
    required this.startsAt,
    required this.startsOn,
    required this.feeKind,
    required this.eligibilityNote,
    required this.windowConfirmedOpen,
    required this.registrationOpensAt,
    required this.officialUrl,
    required this.registrationUrl,
  });

  factory _FreeEventCard.fromJson(Map<String, dynamic> raw) =>
      _FreeEventCard(
        opportunityId: raw['opportunity_id'] as String,
        title: raw['title'] as String,
        summary: raw['summary'] as String?,
        city: raw['city'] as String?,
        venue: raw['venue'] as String?,
        startsAt: DateTime.tryParse((raw['starts_at'] as String?) ?? ''),
        startsOn: DateTime.tryParse((raw['starts_on'] as String?) ?? ''),
        feeKind: raw['fee_kind'] as String,
        eligibilityNote: raw['eligibility_note'] as String?,
        windowConfirmedOpen: raw['window_confirmed_open'] == true,
        registrationOpensAt:
            DateTime.tryParse((raw['registration_opens_at'] as String?) ?? ''),
        officialUrl: raw['official_url'] as String,
        registrationUrl: raw['registration_url'] as String,
      );

  final String opportunityId;
  final String title;
  final String? summary;
  final String? city;
  final String? venue;
  final DateTime? startsAt;
  final DateTime? startsOn;
  final String feeKind;
  final String? eligibilityNote;
  final bool windowConfirmedOpen;
  final DateTime? registrationOpensAt;
  final String officialUrl;
  final String registrationUrl;
}
