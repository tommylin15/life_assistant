import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_tokens.dart';

/// Constrains page content to the approved Warm Knowledge reading width while
/// applying responsive horizontal gutters from the shared token layer.
class AppPageFrame extends StatelessWidget {
  const AppPageFrame({
    super.key,
    required this.child,
    this.maxWidth = AppLayout.contentMaxWidth,
    this.verticalPadding = AppSpacing.lg,
    this.alignment = Alignment.topCenter,
  });

  final Widget child;
  final double maxWidth;
  final double verticalPadding;
  final AlignmentGeometry alignment;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final horizontal = AppLayout.pageHorizontalFor(width);

    return Align(
      alignment: alignment,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            horizontal,
            verticalPadding,
            horizontal,
            verticalPadding,
          ),
          child: child,
        ),
      ),
    );
  }
}

/// Standard card container used by dashboard, task, project, note and Drive
/// surfaces. The card itself inherits color, border and radius from AppTheme.
class AppSectionCard extends StatelessWidget {
  const AppSectionCard({
    super.key,
    required this.child,
    this.title,
    this.subtitle,
    this.action,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
  });

  final Widget child;
  final String? title;
  final String? subtitle;
  final Widget? action;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasHeader = title != null || subtitle != null || action != null;

    return Card(
      child: Padding(
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (hasHeader) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (title != null || subtitle != null)
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (title != null)
                            Text(
                              title!,
                              style: theme.textTheme.headlineSmall,
                            ),
                          if (subtitle != null) ...[
                            const SizedBox(height: AppSpacing.xs),
                            Text(
                              subtitle!,
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ],
                      ),
                    ),
                  if (action != null) ...[
                    if (title != null || subtitle != null)
                      const SizedBox(width: AppSpacing.md),
                    action!,
                  ],
                ],
              ),
              const SizedBox(height: AppSpacing.lg),
            ],
            child,
          ],
        ),
      ),
    );
  }
}

enum AppStatusTone { neutral, success, warning, danger, info }

/// Low-saturation status label. Text/icon semantics stay present so status is
/// never communicated by color alone.
class AppStatusChip extends StatelessWidget {
  const AppStatusChip({
    super.key,
    required this.label,
    this.tone = AppStatusTone.neutral,
    this.icon,
  });

  final String label;
  final AppStatusTone tone;
  final IconData? icon;

  Color _toneColor(ThemeData theme) {
    switch (tone) {
      case AppStatusTone.success:
        return AppColors.success;
      case AppStatusTone.warning:
        return AppColors.warning;
      case AppStatusTone.danger:
        return AppColors.danger;
      case AppStatusTone.info:
        return AppColors.info;
      case AppStatusTone.neutral:
        return theme.colorScheme.onSurface;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final foreground = _toneColor(theme);
    final background = tone == AppStatusTone.neutral
        ? theme.colorScheme.surface
        : foreground.withValues(alpha: 0.12);

    return Semantics(
      label: label,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(
            color: foreground.withValues(alpha: 0.24),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.sm,
            vertical: AppSpacing.xs,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 16, color: foreground),
                const SizedBox(width: AppSpacing.xs),
              ],
              Text(
                label,
                style: theme.textTheme.labelLarge?.copyWith(color: foreground),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Reusable non-fixed-height state surface for empty, error and informational
/// states. Loading indicators can be supplied as [icon] or [action].
class AppStatePanel extends StatelessWidget {
  const AppStatePanel({
    super.key,
    required this.title,
    this.message,
    this.icon,
    this.action,
  });

  final String title;
  final String? message;
  final Widget? icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                IconTheme(
                  data: IconThemeData(
                    color: theme.colorScheme.primary,
                    size: 32,
                  ),
                  child: icon!,
                ),
                const SizedBox(height: AppSpacing.md),
              ],
              Text(
                title,
                textAlign: TextAlign.center,
                style: theme.textTheme.headlineSmall,
              ),
              if (message != null) ...[
                const SizedBox(height: AppSpacing.sm),
                Text(
                  message!,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.textTheme.bodySmall?.color,
                  ),
                ),
              ],
              if (action != null) ...[
                const SizedBox(height: AppSpacing.lg),
                action!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}
