import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../app/theme/app_tokens.dart';
import 'navigation_catalog.dart';
import 'platform_api.dart';
import 'life_ui_environment.dart';
import 'auth_state.dart';
import 'release_info.dart';
import 'release_update_checker.dart';
import 'browser_navigation.dart';

/// One navigation model; desktop uses a collapsible sidebar, mobile a drawer.
/// Home is present only in the four-slot bottom bar.
class AppShell extends ConsumerStatefulWidget {
  const AppShell({
    super.key, required this.location, required this.onNavigate, required this.child,
  });
  final String location;
  final ValueChanged<String> onNavigate;
  final Widget child;

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> with WidgetsBindingObserver {
  Timer? _releaseCheckTimer;
  bool _hasNewFrontend = false;
  bool _releaseChecking = false;

  @override
  void initState() {
    super.initState();
    if (lifeReleaseSha.length == 40) {
      WidgetsBinding.instance.addObserver(this);
      WidgetsBinding.instance.addPostFrameCallback((_) => _checkRelease());
      _releaseCheckTimer = Timer.periodic(
          const Duration(minutes: 15), (_) => _checkRelease());
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _checkRelease();
  }

  Future<void> _checkRelease() async {
    if (!mounted || _hasNewFrontend || _releaseChecking) return;
    _releaseChecking = true;
    try {
      final newer = await checkFrontendRelease();
      if (mounted && newer) setState(() => _hasNewFrontend = true);
    } finally {
      _releaseChecking = false;
    }
  }

  @override
  void dispose() {
    _releaseCheckTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  bool _wideSidebar = true;
  final Set<String> _expandedGroups = {'daily', 'knowledge', 'activities'};

  void _navigate(BuildContext context, String path, {bool closeDrawer = false}) {
    if (closeDrawer) Navigator.of(context).pop();
    widget.onNavigate(path);
  }

  Widget _groupMenu(BuildContext context, Map<String, bool>? flags,
      List<String> order, {required bool compact, required bool drawer}) {
    bool enabled(String key) => flags?[key] ?? true;
    final groups = orderedNavigationGroups(order);
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      children: [
        for (final group in groups)
          if (group.keys.any(enabled)) ...[
            if (compact)
              Tooltip(
                message: group.title,
                child: IconButton(
                  icon: Icon(group.icon),
                  onPressed: () => setState(() => _wideSidebar = true),
                ),
              )
            else
              ListTile(
                dense: true,
                key: ValueKey('nav-group-' + group.id),
                leading: Icon(group.icon),
                title: Text(group.title,
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                trailing: Icon(_expandedGroups.contains(group.id)
                    ? Icons.expand_less : Icons.expand_more),
                onTap: () => setState(() {
                  if (!_expandedGroups.add(group.id)) {
                    _expandedGroups.remove(group.id);
                  }
                }),
              ),
            if (!compact && _expandedGroups.contains(group.id))
              for (final key in order)
                if (group.keys.contains(key) && enabled(key))
                  ListTile(
                    dense: true,
                    key: ValueKey('nav-item-' + key),
                    leading: Icon(lifeNavigationItems[key]!.icon),
                    contentPadding: const EdgeInsets.only(left: 34, right: 12),
                    title: Text(lifeNavigationItems[key]!.label),
                    selected: lifeNavigationItems[key]!.matches(widget.location),
                    onTap: () => _navigate(context, lifeNavigationItems[key]!.path,
                        closeDrawer: drawer),
                  ),
          ],
      ],
    );
  }

  Widget _navigationPanel(BuildContext context, Map<String, bool>? flags,
      List<String> order, {required bool compact, required bool drawer}) {
    final isOwner = ref.watch(ownerAuthorizedProvider).asData?.value == true;
    ref.watch(releaseNotesReadRevisionProvider);
    final features = ref.watch(effectiveFeaturesProvider).asData?.value;
    final backend = ref.watch(backendReleaseNotesProvider).asData?.value ?? const <LifeReleaseNote>[];
    final visible = releaseNotesFor(lifeAppVersion,
        features: features, backendNotes: backend);
    Widget utility(IconData icon, String title, String path, String key,
        {bool unread = false}) {
      final displayIcon = Badge(
        isLabelVisible: unread, smallSize: 7, child: Icon(icon));
      return compact
          ? Tooltip(
              message: title,
              child: IconButton(
                key: ValueKey(key),
                onPressed: () => _navigate(context, path, closeDrawer: drawer),
                icon: displayIcon,
              ),
            )
          : ListTile(
              key: ValueKey(key),
              leading: displayIcon,
              title: Text(title),
              selected: widget.location == path,
              onTap: () => _navigate(context, path, closeDrawer: drawer),
            );
    }

    return SafeArea(
      child: Column(children: [
        Expanded(child: _groupMenu(context, flags, order,
            compact: compact, drawer: drawer)),
        const Divider(height: 1),
        utility(Icons.campaign_outlined, '最新消息', '/more/updates', 'nav-updates',
            unread: hasUnreadReleaseNotes(
                ref.watch(authProvider).asData?.value?['email'], visible)),
        utility(Icons.tune_outlined, '個人化', '/more/personalize', 'nav-personalize'),
        if (isOwner) ...[
          utility(Icons.admin_panel_settings_outlined, '管理中心', '/more/admin', 'nav-admin'),
          if (LifeUiEnvironment.isCandidate)
            utility(Icons.fact_check_outlined, '驗收中心', '/acceptance', 'nav-acceptance'),
        ],
        const SizedBox(height: 8),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final prefs = ref.watch(uiPreferencesProvider).asData?.value;
    final flags = ref.watch(effectiveFeaturesProvider).asData?.value;
    bool enabled(String key) => flags?[key] ?? true;
    final stored = ((prefs?['more_order'] as List?)?.cast<String>() ??
        const <String>[]).map(canonicalNavKey);
    final order = normalizeNavigationOrder(stored);
    final pinKeys = availablePinKeys(
      ((prefs?['pinned'] as List?)?.cast<String>() ?? lifeDefaultPins), enabled);
    final bottom = <LifeNavItem>[
      lifeNavigationItems['today']!,
      for (final key in pinKeys) lifeNavigationItems[key]!,
    ];
    final desktop = width >= AppBreakpoints.navigationRail;
    final sidebarWidth = _wideSidebar
        ? AppLayout.extendedNavigationRailWidth
        : AppLayout.navigationRailWidth;

    int selectedBottomIndex() {
      for (var i = 0; i < bottom.length; i++) {
        if (bottom[i].matches(widget.location)) return i;
      }
      return 0;
    }

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 48,
        actions: [
          if (flags?['life_inbox'] == true)
            IconButton(
              key: const ValueKey('global-life-capture'),
              tooltip: '快速新增',
              onPressed: () => widget.onNavigate('/capture'),
              icon: const Icon(Icons.add_circle_outline),
            ),
        ],
        title: const Text('Life Assistant'),
        leading: desktop
            ? IconButton(
                tooltip: _wideSidebar ? '收合左側選單' : '展開左側選單',
                icon: Icon(_wideSidebar ? Icons.menu_open : Icons.menu),
                onPressed: () => setState(() => _wideSidebar = !_wideSidebar),
              )
            : null,
      ),
      drawer: desktop ? null : Drawer(
        child: _navigationPanel(context, flags, order,
            compact: false, drawer: true),
      ),
      body: Column(children: [
        if (_hasNewFrontend)
          MaterialBanner(
            content: const Text('有新版可使用，重新整理後即可更新。'),
            leading: const Icon(Icons.system_update_alt),
            actions: [
              TextButton(
                onPressed: () => setState(() => _hasNewFrontend = false),
                child: const Text('稍後'),
              ),
              TextButton(
                onPressed: () => navigateBrowser(Uri.base.toString()),
                child: const Text('重新整理'),
              ),
            ],
          ),
        Expanded(child: desktop
          ? Row(children: [
              SizedBox(
                width: sidebarWidth,
                child: _navigationPanel(context, flags, order,
                    compact: !_wideSidebar, drawer: false),
              ),
              const VerticalDivider(width: 1),
              Expanded(child: widget.child),
            ])
          : widget.child),
      ]),
      bottomNavigationBar: SafeArea(
        top: false,
        child: NavigationBar(
          selectedIndex: selectedBottomIndex(),
          onDestinationSelected: (index) => widget.onNavigate(bottom[index].path),
          destinations: [
            for (final item in bottom)
              NavigationDestination(
                icon: Icon(item.icon),
                selectedIcon: Icon(item.selectedIcon),
                label: item.label,
              ),
          ],
        ),
      ),
    );
  }
}
