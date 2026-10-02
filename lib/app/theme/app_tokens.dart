abstract class AppSpacing {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 24.0;
  static const x2l = 32.0;
  static const x3l = 48.0;
  static const pageHorizontal = 16.0;
}

abstract class AppRadius {
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 20.0;
  static const pill = 999.0;
}

abstract class AppBreakpoints {
  static const compact = 600.0;
  static const pageActions = 720.0;
  static const navigationRail = 840.0;
  static const roomyDesktop = 1200.0;
}

abstract class AppLayout {
  static const contentMaxWidth = 1040.0;
  static const navigationRailWidth = 80.0;
  static const extendedNavigationRailWidth = 184.0;

  static double pageHorizontalFor(double width) {
    if (width >= AppBreakpoints.roomyDesktop) {
      return AppSpacing.x2l;
    }
    if (width >= AppBreakpoints.pageActions) {
      return AppSpacing.xl;
    }
    return AppSpacing.lg;
  }
}
