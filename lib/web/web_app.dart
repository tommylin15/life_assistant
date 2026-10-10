import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../app/theme/app_theme.dart';
import 'acceptance_center_page.dart';
import 'calendar_page.dart';
import 'app_shell.dart';
import 'auth_state.dart';
import 'drive_page.dart';
import 'drive_settings_page.dart';
import 'integrations_page.dart';
import 'habits_page.dart';
import 'login_page.dart';
import 'more_page.dart';
import 'notes_page.dart';
import 'projects_page.dart';
import 'shopping_page.dart';
import 'free_events_page.dart';
import 'tasks_page.dart';
import 'curated_events_page.dart';
import 'platform_api.dart';
import 'today_page.dart';
import 'personalize_page.dart';
import 'admin_center_page.dart';

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
          builder: (_, __) => const FeatureAccess(feature: 'drive', child: DriveSettingsPage()),
        ),
        GoRoute(
          path: '/more/drive',
          builder: (_, __) => const FeatureAccess(feature: 'drive', child: DrivePage()),
        ),
        GoRoute(path: '/more/events', builder: (_, __) => const FeatureAccess(feature: 'events', child: FreeEventsPage())),
        GoRoute(path: '/more/curated', builder: (_, __) =>
            const FeatureAccess(feature: 'events', child: CuratedEventsPage())),
        GoRoute(path: '/more/opportunities', builder: (_, __) => const FeatureAccess(feature: 'opportunities', child: CuratedEventsPage(entry: 'opportunities'))),
        GoRoute(path: '/more/explore', builder: (_, __) => const FeatureAccess(feature: 'explore', child: CuratedEventsPage(entry: 'explore'))),
        GoRoute(path: '/more/personalize', builder: (_, __) => const PersonalizePage()),
        GoRoute(path: '/more/admin', builder: (_, __) => const AdminAccess(child: AdminCenterPage())),
        GoRoute(path: '/more', builder: (_, __) => const MorePage()),
      ],
    ),
    GoRoute(
      path: '/integrations',
      builder: (_, __) => const AuthGuard(child: FeatureAccess(feature: 'integrations', child: IntegrationsPage())),
    ),
    GoRoute(
      path: '/acceptance',
      builder: (_, __) => const AuthGuard(child: AdminAccess(child: AcceptanceCenterPage())),
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
      error: (_, __) => const LoginPage(),
      data: (user) => user == null ? const LoginPage() : child,
    );
  }
}

class WebApp extends ConsumerWidget {
  const WebApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialApp.router(
        title: '生活助理',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        themeMode: ThemeMode.system,
        routerConfig: _router,
      );
}

