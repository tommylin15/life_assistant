import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/theme/app_colors.dart';
import 'package:life_assistant/app/theme/app_theme.dart';

void main() {
  test('Warm Knowledge is the only formal light design track', () async {
    final source = await File('lib/app/theme/app_theme.dart').readAsString();

    expect(source, isNot(contains('static ThemeData get clean')));
    expect(AppTheme.light.scaffoldBackgroundColor, AppColors.lightCanvas);
  });

  test('shared navigation and primary actions use Warm Knowledge tokens', () {
    final theme = AppTheme.light;

    expect(theme.navigationRailTheme.backgroundColor, AppColors.lightPaper);
    expect(theme.navigationRailTheme.indicatorColor, AppColors.accentSageSoft);
    expect(
      theme.floatingActionButtonTheme.backgroundColor,
      AppColors.accentSage,
    );
  });

  test('responsive and content layout values have one token source', () async {
    final source = await File('lib/app/theme/app_tokens.dart').readAsString();

    expect(source, contains('abstract class AppBreakpoints'));
    expect(source, contains('static const pageActions = 720.0'));
    expect(source, contains('static const navigationRail = 840.0'));
    expect(source, contains('static const roomyDesktop = 1200.0'));
    expect(source, contains('static const contentMaxWidth = 1040.0'));
  });
}
