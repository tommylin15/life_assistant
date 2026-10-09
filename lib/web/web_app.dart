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

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', redirect: (_, __) => '/tasks'),
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
          builder: (_, __) => const _SectionPlaceholderPage(
            title: '首頁',
            message: '首頁內容準備中',
            icon: Icons.home_outlined,
          ),
        ),
        GoRoute(path: '/tasks', builder: (_, __) => const TasksPage()),
        GoRoute(path: '/calendar', builder: (_, __) => const CalendarPage()),
        GoRoute(path: '/projects', builder: (_, __) => const ProjectsPage()),
        GoRoute(
          path: '/more/habits',
          builder: (_, __) => const HabitsPage(),
        ),
        GoRoute(
          path: '/more/shopping',
          builder: (_, __) => const ShoppingPage(),
        ),
        GoRoute(
          path: '/more/notes',
          builder: (_, __) => const NotesPage(),
        ),
        GoRoute(
          path: '/more/drive/settings',
          builder: (_, __) => const DriveSettingsPage(),
        ),
        GoRoute(
          path: '/more/drive',
          builder: (_, __) => const DrivePage(),
        ),
        GoRoute(path: '/more/events', builder: (_, __) => const FreeEventsPage()),
        GoRoute(path: '/more', builder: (_, __) => const MorePage()),
      ],
    ),
    GoRoute(
      path: '/integrations',
      builder: (_, __) => const AuthGuard(child: IntegrationsPage()),
    ),
    GoRoute(
      path: '/acceptance',
      builder: (_, __) => const AuthGuard(child: AcceptanceCenterPage()),
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

class _SectionPlaceholderPage extends StatelessWidget {
  const _SectionPlaceholderPage({
    required this.title,
    required this.message,
    required this.icon,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 48),
                const SizedBox(height: 16),
                Text(
                  message,
                  style: Theme.of(context).textTheme.headlineSmall,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
}
