import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'browser_navigation_contract.dart';
import 'browser_navigation_stub.dart'
    if (dart.library.html) 'browser_navigation_html.dart' as implementation;

export 'browser_navigation_contract.dart';

void navigateBrowser(String url) => implementation.navigateBrowser(url);

class _DefaultBrowserNavigation implements BrowserNavigation {
  @override
  Future<void> openExternal(String url) async {
    navigateBrowser(url);
  }
}

final browserNavigationProvider = Provider<BrowserNavigation>(
  (_) => _DefaultBrowserNavigation(),
);
