import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

import 'auth_state.dart';

class AuthCallbackPage extends ConsumerStatefulWidget {
  const AuthCallbackPage({super.key});

  @override
  ConsumerState<AuthCallbackPage> createState() => _AuthCallbackPageState();
}

class _AuthCallbackPageState extends ConsumerState<AuthCallbackPage> {
  @override
  void initState() {
    super.initState();
    _handleCallback();
  }

  Future<void> _handleCallback() async {
    final params = Uri.parse(html.window.location.href).queryParameters;
    final token = params['access_token'];
    final email = params['email'] ?? '';
    final name = params['name'] ?? '';

    if (token == null) {
      context.go('/login');
      return;
    }

    await ref.read(authProvider.notifier).saveSession(
          token: token,
          email: email,
          name: name,
        );
    context.go('/');
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
