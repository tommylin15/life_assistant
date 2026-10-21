import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/release_info.dart';

void main() {
  test('versions never expose an unshipped bundled announcement', () {
    expect(isReleaseAtLeast('0.2.0', '0.3.0'), isFalse);
    expect(isReleaseAtLeast('0.3.0', '0.3.0'), isTrue);
    expect(isReleaseAtLeast('開發版', '0.3.0'), isFalse);
    expect(releaseNotesFor('0.1.0'), isEmpty);
    expect(releaseNotesFor('0.2.0').single.title, '最新消息上線');
    expect(releaseNotesFor('0.3.0').first.title, '版本提醒更清楚');
  });

  test('0.4.0 candidates include feature-scoped product improvements', () {
    expect(isReleaseAtLeast('0.3.0', '0.4.0'), isFalse);
    expect(isReleaseAtLeast('0.4.0', '0.4.0'), isTrue);
    final oldNotes = releaseNotesFor('0.3.0', features: {
      'gmail_radar': true, 'life_inbox': true,
    });
    expect(oldNotes.any((note) => note.version == '0.4.0'), isFalse);
    final all = releaseNotesFor('0.4.0', features: {
      'gmail_radar': true, 'life_inbox': true,
    });
    expect(all.where((note) => note.version == '0.4.0').length, 2);
    expect(all.first.title, 'Gmail 雷達操作更簡潔');
    final hiddenInbox = releaseNotesFor('0.4.0', features: {
      'gmail_radar': true, 'life_inbox': false,
    });
    expect(hiddenInbox.any((note) =>
        note.id == 'web-0.4.0-life-inbox-multi-actions'), isFalse);
    expect(hiddenInbox.any((note) =>
        note.id == 'web-0.4.0-gmail-radar-compact'), isTrue);
    expect(releaseReadToken(oldNotes), isNot(releaseReadToken(all)));
  });

  test('feature-specific notices are gated and newly visible notes change read token', () {
    const note = LifeReleaseNote(
      id: 'backend-20261019-calendar', title: '日曆調整',
      changes: ['改善操作體驗'], featureKey: 'calendar',
    );
    final hidden = releaseNotesFor('0.3.0', backendNotes: [note],
      features: {'calendar': false});
    final public = releaseNotesFor('0.3.0', backendNotes: [note],
      features: {'calendar': true});
    expect(hidden.any((x) => x.id == note.id), isFalse);
    expect(public.any((x) => x.id == note.id), isTrue);
    expect(releaseReadToken(hidden), isNot(releaseReadToken(public)));
    expect(releaseReadToken(const []), isNull);
  });

  test('bad backend notes are discarded', () {
    expect(parseBackendReleaseNote({'id': 'bad', 'title': 'a'}), isNull);
    expect(parseBackendReleaseNote({
      'id': 'backend-20261019-calendar',
      'title': '日曆調整',
      'changes': ['操作更方便'],
      'published_on': '2026-10-19',
      'feature_key': 'calendar',
    })?.featureKey, 'calendar');
  });

  test('local read marker is isolated by account and environment', () {
    final a = releaseReadStorageKey('A@example.com', candidate: false);
    expect(a, releaseReadStorageKey('a@EXAMPLE.com', candidate: false));
    expect(a, isNot(releaseReadStorageKey('b@example.com', candidate: false)));
    expect(a, isNot(releaseReadStorageKey('a@example.com', candidate: true)));
    expect(a, isNot(contains('a@example.com')));
  });
}
