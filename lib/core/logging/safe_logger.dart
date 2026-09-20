import 'dart:developer' as developer;

class SafeLogger {
  const SafeLogger();
  static final _secret = RegExp(
    r'(access[_-]?token|refresh[_-]?token|authorization|password|pin)\s*[:=]\s*[^\s,}]+',
    caseSensitive: false,
  );
  void info(String message, {String name = 'life_assistant'}) =>
      developer.log(_scrub(message), name: name);
  void error(
    String message,
    Object error,
    StackTrace stack, {
    String name = 'life_assistant',
  }) => developer.log(
    _scrub(message),
    name: name,
    error: _scrub('$error'),
    stackTrace: stack,
  );
  String _scrub(String value) =>
      value.replaceAllMapped(_secret, (m) => '${m.group(1)}=[REDACTED]');
}
