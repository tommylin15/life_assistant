import 'package:flutter/material.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

const _configuredAuthBase =
    String.fromEnvironment('AUTH_BASE_URL', defaultValue: '');

String get _loginUrl => _configuredAuthBase.isEmpty
    ? '/auth/login'
    : '$_configuredAuthBase/auth/login';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              '生活助理',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 48),
            FilledButton.icon(
              icon: const Icon(Icons.login),
              label: const Text('用 Google 帳號登入'),
              onPressed: () => html.window.location.href = _loginUrl,
            ),
          ],
        ),
      ),
    );
  }
}
