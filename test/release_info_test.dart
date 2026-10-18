import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/release_info.dart';

void main() {
  test('semantic version comparison never publishes a future announcement', () {
    expect(isReleaseAtLeast('0.2.0', '0.2.0'), isTrue);
    expect(isReleaseAtLeast('0.2.1', '0.2.0'), isTrue);
    expect(isReleaseAtLeast('0.1.9', '0.2.0'), isFalse);
    expect(isReleaseAtLeast('開發版', '0.2.0'), isFalse);
    expect(releaseNotesFor('0.1.0'), isEmpty);
    expect(releaseNotesFor('0.2.0').single.title, '最新消息上線');
  });

  test('per-account release read marker is isolated by environment', () {
    final a = releaseReadStorageKey('A@example.com', candidate: false);
    expect(a, releaseReadStorageKey('a@EXAMPLE.com', candidate: false));
    expect(a, isNot(releaseReadStorageKey('b@example.com', candidate: false)));
    expect(a, isNot(releaseReadStorageKey('a@example.com', candidate: true)));
    expect(a, isNot(contains('a@example.com')));
  });
}
