/// Only trusted HTTPS links are exposed as actionable event URLs.
/// Legacy notes may be one bare HTTPS URL; ordinary text stays unlinked.
Uri? validActivityUrl(String? raw) {
  if (raw == null) return null;
  final candidate = raw.trim();
  final parsed = Uri.tryParse(candidate);
  if (parsed == null || parsed.scheme != 'https' || parsed.userInfo.isNotEmpty ||
      parsed.host.isEmpty || !parsed.host.contains('.') ||
      parsed.host.endsWith('.local') || parsed.host.endsWith('.internal') ||
      parsed.host == 'localhost' || (parsed.hasPort && parsed.port != 443) ||
      candidate.contains(RegExp(r'\s'))) {
    return null;
  }
  return parsed;
}

Uri? activityUrlInText(String? text, {bool allowBare = false}) {
  if (text == null) return null;
  final lines = text.split('\n');
  for (final line in lines) {
    if (line.trimLeft().startsWith('活動網址：')) {
      return validActivityUrl(line.trimLeft().substring('活動網址：'.length));
    }
  }
  if (allowBare && lines.length == 1) return validActivityUrl(lines.single);
  return null;
}
