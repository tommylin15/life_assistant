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

enum AppWindowClass { compact, medium, expanded, roomy }

abstract class AppResponsive {
  static AppWindowClass windowClassFor(double width) {
    if (width >= AppBreakpoints.roomyDesktop) {
      return AppWindowClass.roomy;
    }
    if (width >= AppBreakpoints.navigationRail) {
      return AppWindowClass.expanded;
    }
    if (width >= AppBreakpoints.compact) {
      return AppWindowClass.medium;
    }
    return AppWindowClass.compact;
  }
}

abstract class AppLayout {
  static const contentMaxWidth = 1040.0;
  static const navigationRailWidth = 80.0;
  static const extendedNavigationRailWidth = 184.0;
  static const contextPanelWidth = 320.0;

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

abstract class AppMotion {
  static const fast = Duration(milliseconds: 150);
  static const standard = Duration(milliseconds: 200);
  static const slow = Duration(milliseconds: 250);
}

abstract class AppTouchTarget {
  static const minimum = 44.0;
}
