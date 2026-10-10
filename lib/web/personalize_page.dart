import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'platform_api.dart';

const _titles = <String, String>{
  'today':'首頁', 'tasks':'待辦', 'calendar':'日曆', 'projects':'專案',
  'notes':'筆記', 'habits':'習慣', 'shopping':'購物', 'events':'精選活動', 'opportunities':'限時機會', 'explore':'活動探索',
  'drive':'Drive', 'integrations':'Google 整合', 'attention':'待關注',
};

class PersonalizePage extends ConsumerStatefulWidget {
  const PersonalizePage({super.key});
  @override
  ConsumerState<PersonalizePage> createState() => _PersonalizePageState();
}

class _PersonalizePageState extends ConsumerState<PersonalizePage> {
  Map<String, dynamic>? draft;
  bool saving = false;
  String? message;

  @override
  Widget build(BuildContext context) {
    final data = ref.watch(uiPreferencesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('個人化介面')),
      body: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('無法取得介面偏好')),
        data: (value) {
          draft ??= Map<String, dynamic>.from(value);
          final mode = draft!['nav_mode'] as String;
          final pins = (draft!['pinned'] as List).cast<String>().toList();
          final home = (draft!['home_cards'] as List).cast<String>().toList();
          final more = (draft!['more_order'] as List).cast<String>().toList();
          return ListView(padding: const EdgeInsets.all(16), children: [
            Text('選單位置', style: Theme.of(context).textTheme.titleLarge),
            DropdownButton<String>(
              value: mode,
              items: const [
                DropdownMenuItem(value: 'auto', child: Text('自動（依螢幕寬度）')),
                DropdownMenuItem(value: 'bottom', child: Text('底部')),
                DropdownMenuItem(value: 'sidebar', child: Text('左側 / 手機抽屜')),
              ],
              onChanged: (s) => setState(() => draft!['nav_mode'] = s ?? 'auto'),
            ),
            const SizedBox(height: 20),
            Text('底部捷徑（首頁、更多固定，最多選 3 項）',
                style: Theme.of(context).textTheme.titleMedium),
            Wrap(spacing: 6, children: [
              for (final key in ['tasks','calendar','projects','notes','habits',
                'shopping','events','opportunities','explore','drive','integrations'])
                FilterChip(
                  label: Text(_titles[key] ?? key),
                  selected: pins.contains(key),
                  onSelected: (on) => setState(() {
                    if (on && pins.length < 3) { pins.add(key); }
                    if (!on) { pins.remove(key); }
                    draft!['pinned'] = pins;
                  }),
                ),
            ]),
            for (var i = 0; i < pins.length; i++)
              ListTile(
                title: Text(_titles[pins[i]] ?? pins[i]),
                leading: const Icon(Icons.drag_handle),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                    tooltip: '往上移', icon: const Icon(Icons.arrow_upward),
                    onPressed: i == 0 ? null : () => setState(() {
                      final value = pins.removeAt(i); pins.insert(i - 1, value);
                      draft!['pinned'] = pins;
                    }),
                  ),
                  IconButton(
                    tooltip: '往下移', icon: const Icon(Icons.arrow_downward),
                    onPressed: i == pins.length - 1 ? null : () => setState(() {
                      final value = pins.removeAt(i); pins.insert(i + 1, value);
                      draft!['pinned'] = pins;
                    }),
                  ),
                ]),
              ),
            const SizedBox(height: 20),
            Text('更多功能排序', style: Theme.of(context).textTheme.titleMedium),
            for (var i = 0; i < more.length; i++)
              ListTile(
                title: Text(_titles[more[i]] ?? more[i]),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                    tooltip: '更多功能往上', icon: const Icon(Icons.arrow_upward),
                    onPressed: i == 0 ? null : () => setState(() {
                      final item = more.removeAt(i); more.insert(i - 1, item);
                      draft!['more_order'] = more;
                    }),
                  ),
                  IconButton(
                    tooltip: '更多功能往下', icon: const Icon(Icons.arrow_downward),
                    onPressed: i == more.length - 1 ? null : () => setState(() {
                      final item = more.removeAt(i); more.insert(i + 1, item);
                      draft!['more_order'] = more;
                    }),
                  ),
                ]),
              ),
            const SizedBox(height: 20),
            Text('首頁卡片（上下按鈕可供鍵盤操作）',
                style: Theme.of(context).textTheme.titleMedium),
            for (final key in ['tasks','calendar','attention','habits','events',
              'projects','notes','shopping','drive'])
              CheckboxListTile(
                title: Text(_titles[key] ?? key),
                value: home.contains(key),
                onChanged: (on) => setState(() {
                  if (on == true && !home.contains(key)) home.add(key);
                  if (on == false) home.remove(key);
                  draft!['home_cards'] = home;
                }),
              ),
            for (var i = 0; i < home.length; i++)
              ListTile(
                title: Text(_titles[home[i]] ?? home[i]),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                    tooltip: '卡片往上', icon: const Icon(Icons.keyboard_arrow_up),
                    onPressed: i == 0 ? null : () => setState(() {
                      final item = home.removeAt(i); home.insert(i - 1, item);
                      draft!['home_cards'] = home;
                    }),
                  ),
                  IconButton(
                    tooltip: '卡片往下', icon: const Icon(Icons.keyboard_arrow_down),
                    onPressed: i == home.length - 1 ? null : () => setState(() {
                      final item = home.removeAt(i); home.insert(i + 1, item);
                      draft!['home_cards'] = home;
                    }),
                  ),
                ]),
              ),
            if (message != null) Text(message!),
            const SizedBox(height: 12),
            Wrap(spacing: 12, children: [
              OutlinedButton(
                onPressed: saving ? null : () => setState(() {
                  draft!['nav_mode'] = 'auto';
                  draft!['pinned'] = ['tasks', 'calendar', 'projects'];
                  draft!['more_order'] = ['notes', 'habits', 'events', 'shopping', 'drive', 'integrations'];
                  draft!['home_cards'] = ['tasks', 'calendar', 'attention', 'habits', 'events', 'projects'];
                }),
                child: const Text('還原預設'),
              ),
              FilledButton(
                onPressed: saving ? null : _save, child: const Text('儲存偏好'),
              ),
            ]),
          ]);
        },
      ),
    );
  }

  Future<void> _save() async {
    setState(() { saving = true; message = null; });
    try {
      final saved = await ref.read(platformApiProvider).put(
        '/me/ui-preferences', {
          'expected_revision': draft!['revision'],
          'nav_mode': draft!['nav_mode'],
          'pinned': draft!['pinned'],
          'more_order': draft!['more_order'],
          'home_cards': draft!['home_cards'],
        },
      );
      setState(() { draft = saved; message = '偏好已更新'; });
      ref.invalidate(uiPreferencesProvider);
    } catch (_) {
      setState(() => message = '儲存失敗或版本已變更，請重新載入。');
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }
}
