import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'appearance_storage.dart';
import 'life_ui_environment.dart';

/// Human-facing version is injected from pubspec.yaml by both V3 web builds.
/// The Git SHA remains the immutable technical release identity.
const lifeAppVersion =
    String.fromEnvironment('LIFE_APP_VERSION', defaultValue: '開發版');
const lifeReleaseSha = String.fromEnvironment('LIFE_RELEASE_SHA');

class LifeReleaseNote {
  const LifeReleaseNote({
    required this.version,
    required this.title,
    required this.changes,
  });

  final String version;
  final String title;
  final List<String> changes;
}

/// Only publish verified, user-facing changes here. Never summarize CI/SQL or
/// unverified fixes as if they were live. Keep newest first.
const lifeReleaseNotes = <LifeReleaseNote>[
  LifeReleaseNote(
    version: '0.2.0',
    title: '最新消息上線',
    changes: <String>[
      '新增「最新消息」，可以查看 Life Assistant 最近的功能與體驗更新。',
      '增加清楚的版本資訊，方便辨識目前使用的版本。',
    ],
  ),
];

List<int>? _parseVersion(String version) {
  final parts = version.split('.');
  if (parts.length != 3) return null;
  final numbers = parts.map(int.tryParse).toList();
  if (numbers.any((number) => number == null || number < 0)) return null;
  return numbers.cast<int>();
}

bool isReleaseAtLeast(String current, String release) {
  final a = _parseVersion(current);
  final b = _parseVersion(release);
  if (a == null || b == null) return false;
  for (var i = 0; i < 3; i++) {
    if (a[i] != b[i]) return a[i] > b[i];
  }
  return true;
}

List<LifeReleaseNote> releaseNotesFor(String version) =>
    lifeReleaseNotes.where((note) => isReleaseAtLeast(version, note.version)).toList();

String get lifeVersionLabel =>
    lifeAppVersion == '開發版' ? '開發版' : 'v$lifeAppVersion';

String? get latestVisibleReleaseNote =>
    releaseNotesFor(lifeAppVersion).firstOrNull?.version;

// The badge is a convenience, not an important notification guarantee.
// It is isolated per signed-in account, browser origin and environment.
String releaseReadStorageKey(String email, {required bool candidate}) {
  final normalized = email.trim().toLowerCase();
  final accountHash = sha256.convert(utf8.encode(normalized)).toString();
  return 'life:release_notes_seen:${candidate ? 'candidate' : 'production'}:$accountHash';
}

bool hasUnreadReleaseNotes(String? email) {
  final latest = latestVisibleReleaseNote;
  if (latest == null || email == null || email.trim().isEmpty) return false;
  try {
    return getStoredAppearance(releaseReadStorageKey(
          email, candidate: LifeUiEnvironment.isCandidate)) != latest;
  } catch (_) {
    // Private-browsing storage restrictions should not block the app.
    return false;
  }
}

void markReleaseNotesRead(String? email) {
  final latest = latestVisibleReleaseNote;
  if (latest == null || email == null || email.trim().isEmpty) return;
  try {
    setStoredAppearance(
      releaseReadStorageKey(email, candidate: LifeUiEnvironment.isCandidate),
      latest,
    );
  } catch (_) {
    // Reading the changelog is always permitted even if storage is blocked.
  }
}
