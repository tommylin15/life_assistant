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
    'events': AppShellDestination(path: '/more/curated', label: '精選', icon: Icons.event_outlined, selectedIcon: Icons.event),
    'opportunities': AppShellDestination(path: '/more/opportunities', label: '限時機會', icon: Icons.timer_outlined, selectedIcon: Icons.timer),
    'explore': AppShellDestination(path: '/more/explore', label: '活動探索', icon: Icons.explore_outlined, selectedIcon: Icons.explore),
    'shopping': AppShellDestination(path: '/more/shopping', label: '購物', icon: Icons.shopping_cart_outlined, selectedIcon: Icons.shopping_cart),
    'drive': AppShellDestination(path: '/more/drive', label: 'Drive', icon: Icons.cloud_outlined, selectedIcon: Icons.cloud),
    'integrations': AppShellDestination(path: '/integrations', label: 'Google', icon: Icons.hub_outlined, selectedIcon: Icons.hub),
  };

  final String location;
  final ValueChanged<String> onNavigate;
  final Widget child;

  int get selectedIndex {
    final index = destinations.indexWhere((destination) => destination.matches(location));
    return index < 0 ? 0 : index;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final width = MediaQuery.sizeOf(context).width;
    final prefs = ref.watch(uiPreferencesProvider).asData?.value;
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    final pins = (prefs?['pinned'] as List?)?.cast<String>() ??
        ['tasks', 'calendar', 'projects'];
    final mode = prefs?['nav_mode'] as String? ?? 'auto';
    final all = <String, AppShellDestination>{
      'today': destinations[0], 'tasks': destinations[1],
      'calendar': destinations[2], 'projects': destinations[3],
      ..._extra,
    };
    bool enabled(String key) => flags?[key] ?? true;
    final bottom = <AppShellDestination>[
      destinations.first,
      for (final key in pins.where(enabled).take(3))
        if (all.containsKey(key) && key != 'today') all[key]!,
      destinations.last,
    ];
    final rest = (prefs?['more_order'] as List?)?.cast<String>() ??
        ['notes', 'habits', 'events', 'opportunities', 'explore', 'shopping', 'drive', 'integrations'];
    final railKeys = <String>[
      ...pins,
      ...rest,
      ...all.keys.where((k) => k != 'today'),
    ];
    final ordered = railKeys.toSet().toList();
    final rail = <AppShellDestination>[
      destinations.first,
      for (final key in ordered)
        if (key != 'today' && all.containsKey(key) && enabled(key)) all[key]!,
      destinations.last,
    ];
    final isBottom = mode == 'bottom' ||
        (mode == 'auto' && width < AppBreakpoints.navigationRail);
    final isDrawer = mode == 'sidebar' && width < AppBreakpoints.navigationRail;

    int active(List<AppShellDestination> items) {
      // Match explicit feature paths before the /more prefix.
      for (var i = 0; i < items.length; i++) {
        if (items[i].path != '/more' && items[i].matches(location)) return i;
      }
      return items.indexWhere((d) => d.path == '/more');
    }
    void navigate(List<AppShellDestination> items, int index) {
      if (items[index].path != location) onNavigate(items[index].path);
    }

    if (isBottom || isDrawer) {
      return Scaffold(
        appBar: isDrawer ? AppBar(title: const Text('life_assistant')) : null,
        drawer: isDrawer ? Drawer(child: ListView(children: [
          const DrawerHeader(child: Text('功能列表')),
          for (final destination in rail)
            ListTile(
              title: Text(destination.label),
              leading: Icon(destination.icon),
              selected: destination.matches(location),
              onTap: () {
                Navigator.of(context).pop();
                onNavigate(destination.path);
              },
            ),
        ])) : null,
        body: child,
        bottomNavigationBar: isDrawer ? null : SafeArea(
          top: false,
          child: NavigationBar(
            selectedIndex: active(bottom),
            onDestinationSelected: (i) => navigate(bottom, i),
            destinations: [
              for (final destination in bottom)
                NavigationDestination(
                  icon: Icon(destination.icon), selectedIcon: Icon(destination.selectedIcon),
                  label: destination.label,
                ),
            ],
          ),
        ),
      );
    }

    final extended = width >= AppBreakpoints.roomyDesktop;
    return Scaffold(
      body: Row(children: [
        SafeArea(child: NavigationRail(
          selectedIndex: active(rail),
          onDestinationSelected: (i) => navigate(rail, i),
          extended: extended,
          scrollable: true,
          labelType: extended ? null : NavigationRailLabelType.all,
          minWidth: AppLayout.navigationRailWidth,
          minExtendedWidth: AppLayout.extendedNavigationRailWidth,
          groupAlignment: -0.75,
          leading: Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: extended ? const Text('life_assistant') : const Icon(Icons.auto_awesome_outlined),
          ),
          destinations: [
            for (final destination in rail)
              NavigationRailDestination(
                icon: Icon(destination.icon), selectedIcon: Icon(destination.selectedIcon),
                label: Text(destination.label),
              ),
          ],
        )),
        const VerticalDivider(width: 1),
        Expanded(child: child),
      ]),
    );
  }
}
