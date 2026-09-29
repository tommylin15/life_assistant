import 'package:flutter/material.dart';

class AppShellDestination {
  const AppShellDestination({
    required this.path,
    required this.label,
    required this.icon,
    required this.selectedIcon,
  });

  final String path;
  final String label;
  final IconData icon;
  final IconData selectedIcon;

  bool matches(String location) =>
      location == path || location.startsWith('$path/');
}

class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.location,
    required this.onNavigate,
    required this.child,
  });

  static const compactBreakpoint = 840.0;

  static const destinations = <AppShellDestination>[
    AppShellDestination(
      path: '/today',
      label: '首頁',
      icon: Icons.home_outlined,
      selectedIcon: Icons.home,
    ),
    AppShellDestination(
      path: '/tasks',
      label: '待辦',
      icon: Icons.check_circle_outline,
      selectedIcon: Icons.check_circle,
    ),
    AppShellDestination(
      path: '/calendar',
      label: '日曆',
      icon: Icons.calendar_month_outlined,
      selectedIcon: Icons.calendar_month,
    ),
    AppShellDestination(
      path: '/projects',
      label: '專案',
      icon: Icons.folder_outlined,
      selectedIcon: Icons.folder,
    ),
    AppShellDestination(
      path: '/more',
      label: '更多',
      icon: Icons.more_horiz,
      selectedIcon: Icons.more_horiz,
    ),
  ];

  final String location;
  final ValueChanged<String> onNavigate;
  final Widget child;

  int get selectedIndex {
    final index = destinations.indexWhere(
      (destination) => destination.matches(location),
    );
    return index < 0 ? 0 : index;
  }

  void _navigate(int index) {
    final path = destinations[index].path;
    if (path != location) {
      onNavigate(path);
    }
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final index = selectedIndex;

    if (width < compactBreakpoint) {
      return Scaffold(
        body: child,
        bottomNavigationBar: SafeArea(
          top: false,
          child: NavigationBar(
            selectedIndex: index,
            onDestinationSelected: _navigate,
            destinations: [
              for (final destination in destinations)
                NavigationDestination(
                  icon: Icon(destination.icon),
                  selectedIcon: Icon(destination.selectedIcon),
                  label: destination.label,
                ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      body: Row(
        children: [
          SafeArea(
            child: NavigationRail(
              selectedIndex: index,
              onDestinationSelected: _navigate,
              labelType: NavigationRailLabelType.all,
              groupAlignment: -0.75,
              leading: const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: Icon(Icons.auto_awesome_outlined),
              ),
              destinations: [
                for (final destination in destinations)
                  NavigationRailDestination(
                    icon: Icon(destination.icon),
                    selectedIcon: Icon(destination.selectedIcon),
                    label: Text(destination.label),
                  ),
              ],
            ),
          ),
          const VerticalDivider(width: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}
