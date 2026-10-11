// ignore: deprecated_member_use
import 'dart:html' as html;

void navigateBrowser(String url) {
  html.window.location.assign(url);
}

void openExternalBrowser(String url) {
  // External activity pages must not destroy in-app filters/scroll state.
  html.window.open(url, '_blank', 'noopener,noreferrer');
}
