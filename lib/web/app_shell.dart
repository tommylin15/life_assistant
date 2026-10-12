import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../app/theme/app_tokens.dart';
import 'platform_api.dart';

class AppShellDestination {
  const AppShellDestination({
    required this.path, required this.label,
    required this.icon, required this.selectedIcon,
  });
  final String path;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  bool matches(String location) =>
      location == path || location.startsWith('$path/');
}

class AppShell extends ConsumerWidget {
  const AppShell({
    super.key, required this.location,
    required this.onNavigate, required this.child,
  });

  static const destinations = <AppShellDestination>[
    AppShellDestination(path: '/today', label: '首頁', icon: Icons.home_outlined, selectedIcon: Icons.home),
    AppShellDestination(path: '/tasks', label: '待辦', icon: Icons.check_circle_outline, selectedIcon: Icons.check_circle),
    AppShellDestination(path: '/calendar', label: '日曆', icon: Icons.calendar_month_outlined, selectedIcon: Icons.calendar_month),
    AppShellDestination(path: '/projects', label: '專案', icon: Icons.folder_outlined, selectedIcon: Icons.folder),
    AppShellDestination(path: '/more', label: '更多', icon: Icons.more_horiz, selectedIcon: Icons.more_horiz),
  ];
  static const _extra = <String, AppShellDestination>{
    'notes': AppShellDestination(path: '/more/notes', label: '筆記', icon: Icons.description_outlined, selectedIcon: Icons.description),
    'habits': AppShellDestination(path: '/more/habits', label: '習慣', icon: Icons.repeat, selectedIcon: Icons.repeat),
    'opportunities': AppShellDestination(path: '/more/opportunities', label: '限時機會', icon: Icons.timer_outlined, selectedIcon: Icons.timer),
    'explore': AppShellDestination(path: '/more/explore', label: '活動探索', icon: Icons.explore_outlined, selectedIcon: Icons.explore),
    'shopping': AppShellDestination(path: '/more/shopping', label: '購物', icon: Icons.shopping_cart_outlined, selectedIcon: Icons.shopping_cart),
    'drive': AppShellDestination(path: '/more/drive', label: 'Drive', icon: Icons.cloud_outlined, selectedIcon: Icons.cloud),
    'integrations': AppShellDestination(path: '/integrations', label: 'Google', icon: Icons.hub_outlined, selectedIcon: Icons.hub),
  };

  final String location;
  final ValueChanged<String> onNavigate;
  final Widget child;


  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final width = MediaQuery.sizeOf(context).width;
    final prefs = ref.watch(uiPreferencesProvider).asData?.value;
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    final all = <String, AppShellDestination>{
      'today': destinations.first,
      'tasks': destinations[1], 'calendar': destinations[2],
      'projects': destinations[3], ..._extra,
    };
    bool enabled(String key) => flags?[key] ?? true;
    String normalize(String key) => key == 'events' ? 'explore' : key;
    final requestedPins = ((prefs?['pinned'] as List?)?.cast<String>() ??
        ['tasks', 'calendar', 'projects']).map(normalize).toList();
    // Home plus exactly three distinct, enabled shortcuts; fill legacy short lists.
    final pinKeys = <String>[...requestedPins, 'tasks', 'calendar',
      'projects', ...all.keys].toSet()
        .where((key) => key != 'today' && all.containsKey(key) && enabled(key))
        .take(3).toList();
    final bottom = <AppShellDestination>[
      destinations.first, for (final key in pinKeys) all[key]!,
    ];
    final savedOrder = ((prefs?['more_order'] as List?)?.cast<String>() ??
        ['notes', 'habits', 'opportunities', 'explore', 'shopping',
         'drive', 'integrations']).map(normalize);
    final railKeys = <String>[...savedOrder, ...requestedPins,
      ...all.keys.where((key) => key != 'today')]
        .toSet().where((key) => key != 'today' && all.containsKey(key) && enabled(key));
    final rail = <AppShellDestination>[
      destinations.first,
      for (final key in railKeys) all[key]!,
      destinations.last,
    ];
    final mode = prefs?['nav_mode'] as String? ?? 'auto';
    final showRail = width >= AppBreakpoints.navigationRail && mode != 'bottom';
    final extended = width >= AppBreakpoints.roomyDesktop;

    int active(List<AppShellDestination> items) {
      for (var i = 0; i < items.length; i++) {
        if (items[i].path != '/more' && items[i].matches(location)) return i;
      }
      final more = items.indexWhere((item) => item.path == '/more');
      return more < 0 ? 0 : more;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('life_assistant')),
      // Drawer and bottom bar are independent, even when a desktop rail is shown.
      drawer: Drawer(
        child: SafeArea(
          child: ListView(children: [
            const ListTile(title: Text('全部功能')),
            for (final item in rail)
              ListTile(
                key: ValueKey('nav-drawer-' + item.path),
                leading: Icon(item.icon),
                title: Text(item.label),
                selected: item.matches(location),
                onTap: () {
                  Navigator.of(context).pop();
                  onNavigate(item.path);
                },
              ),
          ]),
        ),
      ),
      body: showRail
          ? Row(children: [
              SafeArea(child: NavigationRail(
                selectedIndex: active(rail),
                onDestinationSelected: (index) => onNavigate(rail[index].path),
                extended: extended,
                scrollable: true,
                labelType: extended ? null : NavigationRailLabelType.all,
                minWidth: AppLayout.navigationRailWidth,
                minExtendedWidth: AppLayout.extendedNavigationRailWidth,
                destinations: [
                  for (final item in rail)
                    NavigationRailDestination(
                      icon: Icon(item.icon), selectedIcon: Icon(item.selectedIcon),
                      label: Text(item.label),
                    ),
                ],
              )),
              const VerticalDivider(width: 1),
              Expanded(child: child),
            ])
          : child,
      bottomNavigationBar: SafeArea(
        top: false,
        child: NavigationBar(
          selectedIndex: active(bottom),
          onDestinationSelected: (index) => onNavigate(bottom[index].path),
          destinations: [
            for (final item in bottom)
              NavigationDestination(
                icon: Icon(item.icon), selectedIcon: Icon(item.selectedIcon),
                label: item.label,
              ),
          ],
        ),
      ),
    );
  }
}
