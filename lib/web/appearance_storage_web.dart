// Browser-local, per-account appearance only; no secrets or content stored.
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

String? getStoredAppearance(String key) => html.window.localStorage[key];
void setStoredAppearance(String key, String value) {
  html.window.localStorage[key] = value;
}
