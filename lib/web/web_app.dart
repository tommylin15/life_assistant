import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'auth_callback_page.dart';
import 'auth_state.dart';
import 'login_page.dart';
import 'tasks_page.dart';

final _router = GoRouter(
  redirect: (context, state) {
    // auth guard handled in each page via authProvider
    return null;
  },
  routes: [
    GoRoute(path: '/', builder: (_, __) => const AuthGuard(child: TasksPage())),
    GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
    GoRoute(path: '/auth/callback', builder: (_, __) => const AuthCallbackPage()),
  ],
);

class AuthGuard extends ConsumerWidget {
  const AuthGuard({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    return auth.when(
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
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
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4A90D9)),
          useMaterial3: true,
        ),
        routerConfig: _router,
      );
}
