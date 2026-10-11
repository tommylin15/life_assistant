import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/activity_link.dart';

void main() {
  test('only HTTPS public-looking host is linked', () {
    expect(validActivityUrl('https://events.example.com/a')?.host,
        'events.example.com');
    for (final url in [
      'javascript:alert(1)', 'http://events.example.com',
      'https://localhost/', 'https://host.local/a',
      'https://user:pass@events.example.com',
      'https://events.example.com:8080/a',
      'https://events.example.com/a b',
      'https://127.0.0.1/inside', 'https://192.168.1.2/status',
      'https://8.8.8.8/', 'https://999.999.999.999/',
      'https://.invalid.example/a',
    ]) {
      expect(validActivityUrl(url), isNull, reason: url);
    }
  });

  test('marked event note opens correct activity URL', () {
    expect(activityUrlInText(
      '活動網址：https://events.example.com/registration\n說明：參考活動來源',
    )?.path, '/registration');
    expect(activityUrlInText('一般筆記裡有 https://events.example.com'),
      isNull);
    expect(activityUrlInText('https://events.example.com/legacy',
      allowBare: true)?.path, '/legacy');
  });
}
