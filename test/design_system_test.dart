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

  test('interaction and motion values are semantic tokens', () async {
    final source = await File('lib/app/theme/app_tokens.dart').readAsString();

    expect(source, contains('abstract class AppMotion'));
    expect(source, contains('Duration(milliseconds: 150)'));
    expect(source, contains('Duration(milliseconds: 200)'));
    expect(source, contains('Duration(milliseconds: 250)'));
    expect(source, contains('abstract class AppTouchTarget'));
    expect(source, contains('static const minimum = 44.0'));
    expect(source, contains('static const contextPanelWidth = 320.0'));
  });

  test('shared visual components have one reusable baseline', () async {
    final file = File('lib/app/design_system/app_components.dart');

    expect(file.existsSync(), isTrue);
    if (!file.existsSync()) {
      return;
    }

    final source = await file.readAsString();
    expect(source, contains('class AppPageFrame'));
    expect(source, contains('class AppSectionCard'));
    expect(source, contains('class AppStatusChip'));
    expect(source, contains('class AppStatePanel'));
    expect(source, isNot(contains('Color(0x')));
  });
}
