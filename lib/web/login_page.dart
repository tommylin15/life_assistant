import 'package:flutter/material.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

const _configuredAuthBase =
    String.fromEnvironment('AUTH_BASE_URL', defaultValue: '');

const _canvasColor = Color(0xFFF7F3EA);
const _paperColor = Color(0xFFFFFCF6);
const _textPrimary = Color(0xFF322F2A);
const _textSecondary = Color(0xFF6F695F);
const _sage = Color(0xFF7F9278);
const _sageSoft = Color(0xFFDDE6D8);
const _apricotSoft = Color(0xFFF4DFCE);

String get _loginUrl => _configuredAuthBase.isEmpty
    ? '/auth/login'
    : '$_configuredAuthBase/auth/login';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _canvasColor,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_paperColor, _canvasColor],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 480),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final imageSize = constraints.maxWidth < 360
                            ? constraints.maxWidth * 0.74
                            : 280.0;
                        return Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(40),
                            boxShadow: const [
                              BoxShadow(
                                color: Color(0x1FD99A67),
                                blurRadius: 32,
                                offset: Offset(0, 18),
                              ),
                            ],
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(40),
                            child: Image.asset(
                              'assets/branding/life_assistant_hero_v2.jpg',
                              width: imageSize,
                              height: imageSize,
                              fit: BoxFit.cover,
                              filterQuality: FilterQuality.high,
                              semanticLabel: '生活助理主視覺',
                            ),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 32),
                    const Text(
                      '生活助理',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: _textPrimary,
                        fontSize: 32,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      '把待辦、行程與日常安排，整理成更從容的生活。',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: _textSecondary,
                        fontSize: 17,
                        height: 1.55,
                      ),
                    ),
                    const SizedBox(height: 32),
                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: _sage,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        icon: const Icon(Icons.account_circle_outlined),
                        label: const Text(
                          '用 Google 帳號登入',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        onPressed: () => html.window.location.href = _loginUrl,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: _sageSoft.withValues(alpha: 0.55),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: const Text(
                        '日常・行程・待辦，一個地方整理',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: _textSecondary,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      width: 64,
                      height: 3,
                      decoration: BoxDecoration(
                        color: _apricotSoft,
                        borderRadius: BorderRadius.circular(999),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
