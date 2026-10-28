import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_state.dart';
import 'browser_navigation.dart';
import 'integrations_page.dart';
import 'navigation_catalog.dart';
import 'platform_api.dart';
import 'visual_system.dart';

const _homeLabels = <String, String>{
  'tasks': '今日待辦',
  'calendar': '下一個行程',
  'habits': '今日習慣',
  'explore': '活動探索',
  'projects': '進行中專案',
  'notes': '筆記',
  'shopping': '購物清單',
  'drive': 'Google Drive',
};
List<String> _unifiedHomeCards(Iterable<String> saved) => saved
    .map((key) => (key == 'events' || key == 'opportunities') ? 'explore'
        : key == 'attention' ? 'tasks' : key)
    .where(_homeLabels.containsKey).toSet().toList();

const _defaultHome = <String>[
  'tasks', 'calendar', 'habits', 'explore', 'projects',
];

class PersonalizePage extends ConsumerStatefulWidget {
  const PersonalizePage({super.key, this.initialTab = 'home'});
  final String initialTab;

  @override
  ConsumerState<PersonalizePage> createState() => _PersonalizePageState();
}

class _PersonalizePageState extends ConsumerState<PersonalizePage> {
  Map<String, dynamic>? _draft;
  bool _saving = false;
  bool _loggingOut = false;
  String? _message;
  late String _tab;
  final Set<String> _openGroups = {'daily', 'knowledge', 'activities'};

  @override
  void initState() {
    super.initState();
    _tab = const ['home', 'navigation', 'appearance', 'google']
            .contains(widget.initialTab) ? widget.initialTab : 'home';
  }

  @override
  void didUpdateWidget(covariant PersonalizePage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialTab != widget.initialTab) {
      _tab = widget.initialTab;
    }
  }

  void _initialize(Map<String, dynamic> value) {
    _draft ??= {
      ...value,
      'nav_mode': 'auto',
      'pinned': availablePinKeys(
          (value['pinned'] as List).cast<String>(), (_) => true),
      'more_order': normalizeNavigationOrder(
          (value['more_order'] as List).cast<String>()),
      'home_cards': _unifiedHomeCards((value['home_cards'] as List).cast<String>()),
    };
  }

  void _moveGroup(String id, int offset) {
    final current = normalizeNavigationOrder(
        (_draft!['more_order'] as List).cast<String>());
    final groups = orderedNavigationGroups(current);
    final at = groups.indexWhere((g) => g.id == id);
    final to = at + offset;
    if (at < 0 || to < 0 || to >= groups.length) return;
    setState(() {
      final group = groups.removeAt(at);
      groups.insert(to, group);
      _draft!['more_order'] = [
        for (final g in groups) ...current.where(g.keys.contains),
      ];
    });
  }

  void _moveItem(String key, int offset) {
    final current = normalizeNavigationOrder(
        (_draft!['more_order'] as List).cast<String>());
    final group = lifeGroupFor(key);
    if (group == null) return;
    final subset = current.where(group.keys.contains).toList();
    final at = subset.indexOf(key);
    final to = at + offset;
    if (at < 0 || to < 0 || to >= subset.length) return;
    setState(() {
      final moved = subset.removeAt(at);
      subset.insert(to, moved);
      final groups = orderedNavigationGroups(current);
      _draft!['more_order'] = [
        for (final g in groups)
          ...(g.id == group.id ? subset : current.where(g.keys.contains)),
      ];
    });
  }

  Widget _heading(String title, String explanation) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 4),
      Text(explanation, style: Theme.of(context).textTheme.bodySmall),
    ]),
  );

  Widget _homeTab(Map<String, bool>? flags) {
    final chosen = (_draft!['home_cards'] as List).cast<String>().toList();
    final listed = [...chosen, ..._homeLabels.keys.where((k) => !chosen.contains(k))];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _heading('首頁卡片', '列出所有首頁支援的功能；勾選顯示，並調整排序。未開放的功能不可勾選。'),
      Card(child: Column(children: [
        for (final key in listed)
          CheckboxListTile(
            key: ValueKey('home-card-' + key),
            title: Text((_homeLabels[key] ?? key) +
                ((flags?[key] == false) ? '（未開放）' : '')),
            value: chosen.contains(key),
            controlAffinity: ListTileControlAffinity.leading,
            secondary: chosen.contains(key)
              ? Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                    tooltip: '上移' + (_homeLabels[key] ?? key),
                    onPressed: chosen.indexOf(key) == 0 ? null : () => setState(() {
                      final at = chosen.indexOf(key);
                      final value = chosen.removeAt(at);
                      chosen.insert(at - 1, value);
                      _draft!['home_cards'] = chosen;
                    }),
                    icon: const Icon(Icons.keyboard_arrow_up),
                  ),
                  IconButton(
                    tooltip: '下移' + (_homeLabels[key] ?? key),
                    onPressed: chosen.indexOf(key) == chosen.length - 1
                        ? null : () => setState(() {
                      final at = chosen.indexOf(key);
                      final value = chosen.removeAt(at);
                      chosen.insert(at + 1, value);
                      _draft!['home_cards'] = chosen;
                    }),
                    icon: const Icon(Icons.keyboard_arrow_down),
                  ),
                ]) : null,
            onChanged: flags?[key] == false ? null : (enabled) => setState(() {
              if (enabled == true && !chosen.contains(key)) chosen.add(key);
              if (enabled == false) chosen.remove(key);
              _draft!['home_cards'] = chosen;
            }),
          ),
      ])),
      const SizedBox(height: 12),
      Text('首頁預覽順序：' + (chosen.isEmpty
          ? '未選擇卡片'
          : chosen.map((k) => _homeLabels[k] ?? k).join(' → '))),
    ]);
  }

  Widget _navigationTab(Map<String, bool>? flags) {
    bool enabled(String key) => flags?[key] ?? true;
    final pins = availablePinKeys(
        (_draft!['pinned'] as List).cast<String>(), enabled);
    final candidates = lifeNavigationItems.keys
        .where((k) => k != 'today' && enabled(k)).toList();
    final ordered = normalizeNavigationOrder(
        (_draft!['more_order'] as List).cast<String>());
    final groups = orderedNavigationGroups(ordered);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _heading('底部四個快捷', '首頁固定，另外三格直接選擇，不必另外排序。'),
      Row(children: [
        for (final key in ['today', ...pins])
          Expanded(child: Card(child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
            child: Column(children: [
              Icon(lifeNavigationItems[key]!.selectedIcon),
              const SizedBox(height: 5),
              Text(lifeNavigationItems[key]!.label,
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall),
            ]),
          ))),
      ]),
      for (var i = 0; i < pins.length; i++)
        Padding(
          padding: const EdgeInsets.only(top: 9),
          child: Row(children: [
            SizedBox(width: 72, child: Text('第 ' + (i + 2).toString() + ' 格')),
            Expanded(child: DropdownButtonFormField<String>(
              key: ValueKey('bottom-pin-' + i.toString()),
              value: pins[i],
              isExpanded: true,
              decoration: const InputDecoration(isDense: true),
              items: [
                for (final key in candidates)
                  if (key == pins[i] || !pins.contains(key))
                    DropdownMenuItem(value: key, child: Text(
                      lifeNavigationItems[key]!.label,
                      overflow: TextOverflow.ellipsis)),
              ],
              onChanged: (key) {
                if (key == null) return;
                setState(() {
                  pins[i] = key;
                  _draft!['pinned'] = pins;
                });
              },
            )),
          ]),
        ),
      const SizedBox(height: 26),
      _heading('左側完整選單', '功能按用途分組。可調整群組及各群組的功能順序；首頁與更多不會出現在左側。'),
      Card(child: Column(children: [
        for (var gi = 0; gi < groups.length; gi++) ...[
          ListTile(
            key: ValueKey('settings-nav-group-' + groups[gi].id),
            leading: Icon(groups[gi].icon),
            title: Text(groups[gi].title),
            onTap: () => setState(() {
              if (!_openGroups.add(groups[gi].id)) {
                _openGroups.remove(groups[gi].id);
              }
            }),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              IconButton(
                tooltip: '群組上移',
                onPressed: gi == 0 ? null
                    : () => _moveGroup(groups[gi].id, -1),
                icon: const Icon(Icons.arrow_upward, size: 18),
              ),
              IconButton(
                tooltip: '群組下移',
                onPressed: gi == groups.length - 1 ? null
                    : () => _moveGroup(groups[gi].id, 1),
                icon: const Icon(Icons.arrow_downward, size: 18),
              ),
              Icon(_openGroups.contains(groups[gi].id)
                  ? Icons.expand_less : Icons.expand_more),
            ]),
          ),
          if (_openGroups.contains(groups[gi].id))
            for (final key in ordered.where(groups[gi].keys.contains))
              if (enabled(key))
                ListTile(
                  key: ValueKey('settings-nav-item-' + key),
                  contentPadding: const EdgeInsets.only(left: 38, right: 12),
                  title: Text(lifeNavigationItems[key]!.label),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    IconButton(
                      tooltip: '項目上移',
                      onPressed: ordered.where(groups[gi].keys.contains)
                                  .first == key ? null
                          : () => _moveItem(key, -1),
                      icon: const Icon(Icons.keyboard_arrow_up),
                    ),
                    IconButton(
                      tooltip: '項目下移',
                      onPressed: ordered.where(groups[gi].keys.contains)
                                  .last == key ? null
                          : () => _moveItem(key, 1),
                      icon: const Icon(Icons.keyboard_arrow_down),
                    ),
                  ]),
                ),
        ],
      ])),
      const SizedBox(height: 10),
      const Text('電腦左側／手機抽屜會自動切換，不需要另行選擇導覽模式。'),
    ]);
  }

  Widget _appearanceTab() {
    final appearance = ref.watch(lifeAppearanceProvider);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _heading('主題風格', '選擇即時生效。動畫風格不使用人物插畫，粉紅泡泡使用純 Flutter 色彩與圖形。'),
      for (final style in LifeVisualStyle.values)
        Card(
          child: RadioListTile<LifeVisualStyle>(
            key: ValueKey('visual-style-' + style.name),
            title: Text(style.label),
            subtitle: Text(style.description),
            secondary: CircleAvatar(
              backgroundColor: LifeVisualTheme.build(style, Brightness.light)
                  .colorScheme.primary,
              child: Icon(style == LifeVisualStyle.animated
                  ? Icons.auto_awesome : style == LifeVisualStyle.pinkBubble
                      ? Icons.bubble_chart : Icons.palette_outlined,
                  color: Colors.white),
            ),
            value: style,
            groupValue: appearance.style,
            onChanged: (value) {
              if (value != null) ref.read(lifeAppearanceProvider.notifier).setStyle(value);
            },
          ),
        ),
      const SizedBox(height: 20),
      _heading('亮暗模式', '跟隨系統、淺色或深色。'),
      SegmentedButton<ThemeMode>(
        segments: const [
          ButtonSegment(value: ThemeMode.system, label: Text('系統')),
          ButtonSegment(value: ThemeMode.light, label: Text('淺色')),
          ButtonSegment(value: ThemeMode.dark, label: Text('深色')),
        ],
        selected: {appearance.mode},
        onSelectionChanged: (selected) =>
            ref.read(lifeAppearanceProvider.notifier).setMode(selected.first),
      ),
      const SizedBox(height: 12),
      Text('外觀即時保存於目前瀏覽器、目前帳號；尚未提供跨裝置同步。',
          style: Theme.of(context).textTheme.bodySmall),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final prefs = ref.watch(uiPreferencesProvider);
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    final signedIn = ref.watch(authProvider).asData?.value;
    return Scaffold(
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: Center(child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Card(child: ListTile(
              key: const ValueKey('personalize-account'),
              leading: const Icon(Icons.account_circle_outlined),
              title: const Text('目前登入帳號'),
              subtitle: Text(signedIn?['email'] ?? '無法取得帳號資料',
                maxLines: 1, overflow: TextOverflow.ellipsis),
              trailing: OutlinedButton.icon(
                key: const ValueKey('personalize-logout'),
                onPressed: _loggingOut ? null : _logout,
                icon: const Icon(Icons.logout),
                label: Text(_loggingOut ? '登出中…' : '登出／切換帳號'),
              ),
            )),
          )),
        ),
        Expanded(child: prefs.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('無法取得介面偏好')),
        data: (value) {
          _initialize(value);
          return Align(alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 900),
              child: ListView(padding: const EdgeInsets.all(16), children: [
                const LifeFeatureHeader(feature: LifeVisualFeature.personalize),
                const SizedBox(height: 12),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'home', label: Text('首頁'), icon: Icon(Icons.dashboard_outlined)),
                      ButtonSegment(value: 'navigation', label: Text('導覽'), icon: Icon(Icons.menu)),
                      ButtonSegment(value: 'appearance', label: Text('外觀'), icon: Icon(Icons.palette_outlined)),
                      ButtonSegment(value: 'google', label: Text('服務連結'), icon: Icon(Icons.link)),
                    ],
                    selected: {_tab},
                    onSelectionChanged: (selected) => setState(() => _tab = selected.first),
                  ),
                ),
                const SizedBox(height: 22),
                if (_tab == 'home') _homeTab(flags),
                if (_tab == 'navigation') _navigationTab(flags),
                if (_tab == 'appearance') _appearanceTab(),
                if (_tab == 'google' && flags?['line'] == true)
                  Card(child: ListTile(
                    leading: const Icon(Icons.chat_bubble_outline),
                    title: const Text('LINE 生活助手'),
                    subtitle: const Text('連結或解除 LINE 帳號；原有 Life 資料保留'),
                    trailing: const Icon(Icons.open_in_new),
                    onTap: () => navigateBrowser('/line/link.html'),
                  )),
                if (_tab == 'google') const FeatureAccess(
                    feature: 'integrations', child: GoogleConnectionsPanel()),
                if (_tab == 'home' || _tab == 'navigation') ...[
                  const SizedBox(height: 22),
                  if (_message != null) Text(_message!),
                  Wrap(spacing: 12, runSpacing: 8, children: [
                    OutlinedButton(
                      onPressed: _saving ? null : () => setState(() {
                        _draft!['nav_mode'] = 'auto';
                        _draft!['pinned'] = [...lifeDefaultPins];
                        _draft!['more_order'] = normalizeNavigationOrder(const []);
                        _draft!['home_cards'] = [..._defaultHome];
                        _message = '已還原預設值預覽，按儲存才會生效。';
                      }),
                      child: const Text('還原預設'),
                    ),
                    FilledButton(
                      onPressed: _saving ? null : _save,
                      child: Text(_saving ? '儲存中…' : '儲存偏好'),
                    ),
                  ]),
                ],
              ]),
            ),
          );
        },
      )),
      ]),
    );
  }

  Future<void> _logout() async {
    if (_loggingOut) return;
    setState(() => _loggingOut = true);
    try {
      await ref.read(authProvider.notifier).logout();
      ref.invalidate(uiPreferencesProvider);
      ref.invalidate(effectiveFeaturesProvider);
      ref.invalidate(googleStatusProvider);
      // A full reload clears all remaining previous-user Riverpod caches.
      navigateBrowser('/login');
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('登出失敗，請稍後再試；帳號保持登入。')));
    } finally {
      if (mounted) setState(() => _loggingOut = false);
    }
  }

  Future<void> _save() async {
    setState(() { _saving = true; _message = null; });
    try {
      final saved = await ref.read(platformApiProvider).put(
        '/me/ui-preferences', {
          'expected_revision': _draft!['revision'],
          'nav_mode': 'auto',
          'pinned': _draft!['pinned'],
          'more_order': _draft!['more_order'],
          'home_cards': _draft!['home_cards'],
        },
      );
      if (!mounted) return;
      setState(() { _draft = null; _message = '已儲存個人偏好'; });
      ref.invalidate(uiPreferencesProvider);
      _initialize(saved);
    } catch (_) {
      if (mounted) setState(() => _message = '儲存失敗或設定版本已改變，請重新載入。');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}

