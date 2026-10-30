import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'appearance_storage.dart';
import 'life_ui_environment.dart';
import 'platform_api.dart';

/// Friendly Flutter version and immutable SHA injected by both Web builds.
const lifeAppVersion =
    String.fromEnvironment('LIFE_APP_VERSION', defaultValue: '開發版');
const lifeReleaseSha = String.fromEnvironment('LIFE_RELEASE_SHA');

class LifeReleaseNote {
  const LifeReleaseNote({
    required this.id,
    required this.title,
    required this.changes,
    this.version,
    this.publishedOn,
    this.featureKey,
  });

  final String id;
  final String title;
  final List<String> changes;
  final String? version;
  final String? publishedOn;
  /// Feature-specific posts are hidden until effective, account-bound rollout
  /// data explicitly allows the feature. Null means globally available.
  final String? featureKey;
}

/// A bundled changelog is rolled out atomically with the Hosting build.
/// Never claim unrelated / unverified candidate fixes are production releases.
const lifeReleaseNotes = <LifeReleaseNote>[
  LifeReleaseNote(
    id: 'web-0.6.1-line-native-capture',
    version: '0.6.1',
    title: 'LINE 記錄操作更快速',
    featureKey: 'line',
    changes: <String>[
      '確認新增改為唯一醒目的橘色按鈕，必要欄位完整時才顯示。',
      '新增「重新開始」，清除尚未送出的 LINE 暫存操作，不影響 Life 正式資料。',
      '待辦、購物、筆記與行程可在 LINE 原生卡片操作，完整內容直接開啟 Life。',
    ],
  ),
  LifeReleaseNote(
    id: 'web-0.6.0-line-life',
    version: '0.6.0',
    title: 'LINE 生活助手',
    featureKey: 'line',
    changes: <String>[
      '連結帳號後，可從 LINE 留下文字草稿並確認新增生活事項。',
      '支援個人資料查詢，以及 LINE 內的待辦、購物與行程操作。',
    ],
  ),
  LifeReleaseNote(
    id: 'web-0.5.0-unified-activities',
    version: '0.5.0',
    title: '活動探索整合為全部活動',
    changes: <String>[
      '移除重複的「限時機會」分頁，活動集中在「全部活動」瀏覽。',
      '限額優惠、即將開報與截止提醒改由「更多」篩選快速查看。',
      '保留未驗證活動標示，方便辨識活動來源與確認狀態。',
    ],
  ),
  // 0.4.0 is a candidate until the matching production Hosting SHA passes.
  LifeReleaseNote(
    id: 'web-0.4.0-gmail-radar-compact',
    version: '0.4.0',
    title: 'Gmail 雷達操作更簡潔',
    featureKey: 'gmail_radar',
    changes: <String>[
      '整合掃描選項、收合郵件詳情，已完成與已忽略紀錄可分批查看。',
    ],
  ),
  LifeReleaseNote(
    id: 'web-0.4.0-life-inbox-multi-actions',
    version: '0.4.0',
    title: '快速新增可拆解多件事項',
    featureKey: 'life_inbox',
    changes: <String>[
      '一句話中的行程、購物和待辦可分開確認後新增。',
      '日期與時間依各筆事項辨識，不會套用到其他事項。',
    ],
  ),
  LifeReleaseNote(
    id: 'web-0.3.0-release-visibility',
    version: '0.3.0',
    title: '版本提醒更清楚',
    changes: <String>[
      '新增新版可用提示，可選擇何時重新整理。',
      '改善最新消息的未讀狀態與功能開放範圍。',
    ],
  ),
  LifeReleaseNote(
    id: 'web-0.2.0-release-center',
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

LifeReleaseNote? parseBackendReleaseNote(Object? value) {
  if (value is! Map) return null;
  final id = value['id'];
  final title = value['title'];
  final changes = value['changes'];
  final date = value['published_on'];
  final feature = value['feature_key'];
  if (id is! String ||
      !RegExp(r'^backend-[0-9]{8}-[a-z0-9-]+$').hasMatch(id) ||
      title is! String || title.trim().isEmpty || title.length > 80 ||
      date is! String || !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(date) ||
      changes is! List || changes.isEmpty || changes.length > 3 ||
      changes.any((item) =>
          item is! String || item.trim().isEmpty || item.length > 140) ||
      (feature != null && (feature is! String ||
          !RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(feature)))) {
    return null;
  }
  return LifeReleaseNote(
    id: id,
    title: title,
    changes: changes.cast<String>(),
    publishedOn: date,
    featureKey: feature as String?,
  );
}

/// An API-only fix can be announced when its backend revision goes live.
/// An unreachable API never blocks navigation or bundled release notes.
final backendReleaseNotesProvider = FutureProvider<List<LifeReleaseNote>>((ref) async {
  final payload = await ref.read(platformApiProvider).get('/release-notes');
  final list = payload['notes'];
  if (list is! List) return const <LifeReleaseNote>[];
  return list.map(parseBackendReleaseNote)
      .whereType<LifeReleaseNote>().take(30).toList();
});

List<LifeReleaseNote> releaseNotesFor(
  String version, {
  Map<String, bool>? features,
  List<LifeReleaseNote> backendNotes = const [],
}) {
  final notes = <LifeReleaseNote>[
    ...lifeReleaseNotes.where((note) =>
        note.version != null && isReleaseAtLeast(version, note.version!)),
    ...backendNotes,
  ];
  final seen = <String>{};
  return notes.where((note) =>
      seen.add(note.id) &&
      (note.featureKey == null || features?[note.featureKey] == true)).toList();
}

String get lifeVersionLabel =>
    lifeAppVersion == '開發版' ? '開發版' : 'v$lifeAppVersion';

/// Stable per-visible-content key: if a feature opens after an earlier read,
/// its newly visible entry can still light the unread dot.
String? releaseReadToken(List<LifeReleaseNote> visible) {
  if (visible.isEmpty) return null;
  final ids = visible.map((note) => note.id).toList()..sort();
  return sha256.convert(utf8.encode(ids.join('|'))).toString();
}

String releaseReadStorageKey(String email, {required bool candidate}) {
  final normalized = email.trim().toLowerCase();
  final accountHash = sha256.convert(utf8.encode(normalized)).toString();
  return 'life:release_notes_seen:${candidate ? 'candidate' : 'production'}:$accountHash';
}

bool hasUnreadReleaseNotes(String? email, List<LifeReleaseNote> visible) {
  final token = releaseReadToken(visible);
  if (token == null || email == null || email.trim().isEmpty) return false;
  try {
    return getStoredAppearance(releaseReadStorageKey(
          email, candidate: LifeUiEnvironment.isCandidate)) != token;
  } catch (_) {
    return false;
  }
}

void markReleaseNotesRead(String? email, List<LifeReleaseNote> visible) {
  final token = releaseReadToken(visible);
  if (token == null || email == null || email.trim().isEmpty) return;
  try {
    setStoredAppearance(
      releaseReadStorageKey(email, candidate: LifeUiEnvironment.isCandidate),
      token,
    );
  } catch (_) {
    // Storage restrictions must never block page access.
  }
}

/// Signals that the local unread indicator should rebuild immediately.
final releaseNotesReadRevisionProvider = StateProvider<int>((_) => 0);

