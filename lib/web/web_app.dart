import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'visual_system.dart';
import 'acceptance_center_page.dart';
import 'calendar_page.dart';
import 'app_shell.dart';
import 'auth_state.dart';
import 'browser_navigation.dart';
import 'drive_page.dart';
import 'drive_explorer_page.dart';
import 'gmail_radar_page.dart';
import 'habits_page.dart';
import 'login_page.dart';
import 'notes_page.dart';
import 'projects_page.dart';
import 'shopping_page.dart';
import 'tasks_page.dart';
import 'curated_events_page.dart';
import 'platform_api.dart';
import 'today_page.dart';
import 'personalize_page.dart';
import 'admin_center_page.dart';
import 'life_capture_page.dart';

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', redirect: (_, __) => '/today'),
    ShellRoute(
      builder: (context, state, child) => AuthGuard(
        child: AppShell(
          location: state.uri.path,
          onNavigate: (location) => context.go(location),
          child: child,
        ),
      ),
      routes: [
        GoRoute(
          path: '/today',
          builder: (_, __) => const FeatureAccess(feature: 'today', child: TodayPage()),
        ),
        GoRoute(path: '/capture', builder: (_, __) => const FeatureAccess(feature: 'life_inbox', child: LifeCapturePage())),
        GoRoute(path: '/tasks', builder: (_, __) => const FeatureAccess(feature: 'tasks', child: TasksPage())),
        GoRoute(path: '/calendar', builder: (_, __) => const FeatureAccess(feature: 'calendar', child: CalendarPage())),
        GoRoute(path: '/projects', builder: (_, __) => const FeatureAccess(feature: 'projects', child: ProjectsPage())),
        GoRoute(
          path: '/more/habits',
          builder: (_, __) => const FeatureAccess(feature: 'habits', child: HabitsPage()),
        ),
        GoRoute(
          path: '/more/shopping',
          builder: (_, __) => const FeatureAccess(feature: 'shopping', child: ShoppingPage()),
        ),
        GoRoute(
          path: '/more/notes',
          builder: (_, __) => const FeatureAccess(feature: 'notes', child: NotesPage()),
        ),
        GoRoute(
          path: '/more/drive/settings',
          redirect: (_, __) => '/more/drive',
        ),
        GoRoute(path: '/more/drive/files',
          builder: (_, __) => const FeatureAccess(feature: 'drive', child: DriveExplorerPage())),
        GoRoute(
          path: '/more/drive',
          builder: (_, __) => const FeatureAccess(feature: 'drive', child: DrivePage()),
        ),
        GoRoute(path: '/more/gmail-radar',
          builder: (_, __) => const FeatureAccess(feature: 'gmail_radar', child: GmailRadarPage())),
        GoRoute(path: '/more/events', redirect: (_, __) => '/more/explore'),
        GoRoute(path: '/more/curated', redirect: (_, __) => '/more/explore'),
        GoRoute(path: '/more/opportunities', builder: (_, __) => const FeatureAccess(feature: 'opportunities', child: CuratedEventsPage(entry: 'opportunities'))),
        GoRoute(path: '/more/explore', builder: (_, __) => const FeatureAccess(feature: 'explore', child: CuratedEventsPage(entry: 'explore'))),
        GoRoute(path: '/more/personalize', builder: (_, state) =>
            PersonalizePage(initialTab: state.uri.queryParameters['tab'] ?? 'home')),
        GoRoute(path: '/integrations', redirect: (_, __) => '/more/personalize?tab=google'),
        GoRoute(path: '/acceptance', builder: (_, __) => const AdminAccess(child: AcceptanceCenterPage())),
        GoRoute(path: '/more/admin', builder: (_, __) => const AdminAccess(child: AdminCenterPage())),
        GoRoute(path: '/more', redirect: (_, __) => '/more/personalize'),
      ],
    ),
    GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
  ],
);

class AuthGuard extends ConsumerWidget {
  const AuthGuard({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    return auth.when(
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (_, __) => Scaffold(
        body: Center(child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.error_outline, size: 36),
              const SizedBox(height: 12),
              const Text('無法確認登入狀態'),
              const SizedBox(height: 8),
              const Text('登入後無法取得帳號資料，可能是帳號權限或登入狀態驗證失敗。',
                  textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => ref.read(authProvider.notifier).refresh(),
                icon: const Icon(Icons.refresh),
                label: const Text('重新驗證'),
              ),
              TextButton(
                onPressed: () => navigateBrowser('/login'),
                child: const Text('返回登入／切換帳號'),
              ),
            ]),
          ),
        )),
      ),
      data: (user) => user == null ? const LoginPage() : child,
    );
  }
}

class WebApp extends ConsumerWidget {
  const WebApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appearance = ref.watch(lifeAppearanceProvider);
    return MaterialApp.router(
        title: '生活助理',
        debugShowCheckedModeBanner: false,
        theme: LifeVisualTheme.build(appearance.style, Brightness.light),
        darkTheme: LifeVisualTheme.build(appearance.style, Brightness.dark),
        themeMode: appearance.mode,
        routerConfig: _router,
      );
  }
}

