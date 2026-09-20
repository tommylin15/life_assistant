import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_tokens.dart';

abstract class AppTheme {
  static ThemeData get clean => _build(
    brightness: Brightness.light,
    canvas: const Color(0xFFF7F9FA),
    paper: Colors.white,
    card: Colors.white,
    elevated: Colors.white,
    muted: const Color(0xFFEAF0F2),
    textPrimary: const Color(0xFF1F2A30),
    textSecondary: const Color(0xFF66747B),
    border: const Color(0xFFDDE5E8),
    accent: const Color(0xFF397D7A),
    accentSoft: const Color(0xFFD9ECEA),
  );
  static ThemeData get light => _build(
    brightness: Brightness.light,
    canvas: AppColors.lightCanvas,
    paper: AppColors.lightPaper,
    card: AppColors.lightCard,
    elevated: AppColors.lightElevated,
    muted: AppColors.lightMuted,
    textPrimary: AppColors.lightTextPrimary,
    textSecondary: AppColors.lightTextSecondary,
    border: AppColors.lightBorderSoft,
    accent: AppColors.accentSage,
    accentSoft: AppColors.accentSageSoft,
  );

  static ThemeData get dark => _build(
    brightness: Brightness.dark,
    canvas: AppColors.darkCanvas,
    paper: AppColors.darkPaper,
    card: AppColors.darkCard,
    elevated: AppColors.darkElevated,
    muted: AppColors.darkMuted,
    textPrimary: AppColors.darkTextPrimary,
    textSecondary: AppColors.darkTextSecondary,
    border: AppColors.darkBorderSoft,
    accent: AppColors.accentSageDark,
    accentSoft: AppColors.darkMuted,
  );

  static ThemeData _build({
    required Brightness brightness,
    required Color canvas,
    required Color paper,
    required Color card,
    required Color elevated,
    required Color muted,
    required Color textPrimary,
    required Color textSecondary,
    required Color border,
    required Color accent,
    required Color accentSoft,
  }) {
    return ThemeData(
      brightness: brightness,
      scaffoldBackgroundColor: canvas,
      colorScheme: ColorScheme(
        brightness: brightness,
        primary: accent,
        onPrimary: brightness == Brightness.light
            ? Colors.white
            : AppColors.darkCanvas,
        secondary: AppColors.accentApricot,
        onSecondary: Colors.white,
        error: AppColors.danger,
        onError: Colors.white,
        surface: card,
        onSurface: textPrimary,
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: BorderSide(color: border, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: canvas,
        foregroundColor: textPrimary,
        elevation: 0,
        scrolledUnderElevation: 1,
        shadowColor: border,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: elevated,
        indicatorColor: accentSoft,
        labelTextStyle: WidgetStateProperty.all(
          TextStyle(fontSize: 12, color: textSecondary),
        ),
      ),
      dividerTheme: DividerThemeData(color: border, thickness: 1, space: 1),
      textTheme: TextTheme(
        displayLarge: TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        headlineLarge: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        headlineMedium: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        headlineSmall: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        bodyLarge: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w400,
          color: textPrimary,
          height: 1.6,
        ),
        bodyMedium: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w400,
          color: textPrimary,
          height: 1.45,
        ),
        bodySmall: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          color: textSecondary,
        ),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w500,
          color: textPrimary,
        ),
        labelSmall: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w400,
          color: textSecondary,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: paper,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: accent, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.md,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: brightness == Brightness.light
              ? Colors.white
              : AppColors.darkCanvas,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          minimumSize: const Size(0, 44),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: accent,
          side: BorderSide(color: accent),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          minimumSize: const Size(0, 44),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(minimumSize: const Size(44, 44)),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: accentSoft,
        labelStyle: TextStyle(fontSize: 13, color: textPrimary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.pill),
        ),
        side: BorderSide.none,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: 2,
        ),
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: FadeUpwardsPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
        },
      ),
    );
  }
}
