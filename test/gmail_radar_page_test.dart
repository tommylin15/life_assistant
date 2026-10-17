import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/gmail_radar_page.dart';
import 'package:life_assistant/web/platform_api.dart';

class _FakeRadarApi extends PlatformApi {
  _FakeRadarApi({required this.authorized});
  final bool authorized;
  int scans = 0;
  int rechecks = 0;
  final List<Map<String, dynamic>> items = [];

  @override
  Future<Map<String, dynamic>> get(String path) async {
    if (path.endsWith('/status')) {
      return {
        'gmail_authorized': authorized,
        'status': scans == 0 ? 'never_scanned' : 'succeeded',
        'scan_kind': rechecks > 0 ? 'recheck' : 'quick',
        'last_finished_at': scans == 0 ? null : '2026-10-16T08:00:00Z',
        'checked': scans == 0 ? 0 : 1, 'added': scans == 0 ? 0 : 1,
      };
    }
    if (path.contains('/items?status=')) {
      final filter = Uri.parse(path).queryParameters['status'];
      return {'items': items.where((item) => item['status'] == filter).toList()};
    }
    throw StateError('Unexpected request: ' + path);
  }

  @override
  Future<Map<String, dynamic>> post(
      String path, Map<String, dynamic> body) async {
    if (path.endsWith('/recheck-three-days')) {
      rechecks++;
      scans++;
      return {'status': 'succeeded', 'scan_kind': 'recheck',
              'checked': 2, 'added': 0, 'skipped': 2, 'failed': 0,
              'three_day_count': 2, 'three_day_remaining': 0};
    }
    if (path.endsWith('/quick-scan')) {
      scans++;
      items.add({
        'id': 'item-1', 'title': '繳費通知', 'summary': '請查看帳單',
        'sender': 'bank@example.com', 'category': 'billing',
        'status': 'pending', 'received_at': '2026-10-16T08:00:00Z',
        'gmail_url': 'https://mail.google.com/mail/#all/thread-1',
        'gmail_fallback_url': 'https://mail.google.com/mail/#all',
      });
      return {'status': 'succeeded', 'checked': 1, 'added': 1,
              'skipped': 0, 'failed': 0};
    }
    throw StateError('Unexpected request');
  }

  @override
  Future<Map<String, dynamic>> patch(
      String path, Map<String, dynamic> body) async {
    items.first['status'] = body['status'];
    return {'item': items.first};
  }
}

void main() {
  testWidgets('manual Gmail scan requires owner Gmail authorization', (tester) async {
    final api = _FakeRadarApi(authorized: false);
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: GmailRadarPage()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('尚未授權 Gmail'), findsOneWidget);
    final button = tester.widget<FilledButton>(
        find.byKey(const ValueKey('gmail-radar-quick-scan')));
    expect(button.onPressed, isNull);
    expect(api.scans, 0);
  });

  testWidgets('quick scan updates only the personal action list', (tester) async {
    final api = _FakeRadarApi(authorized: true);
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: GmailRadarPage()),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('立即快掃'));
    await tester.pumpAndSettle();
    expect(api.scans, 1);
    expect(find.text('繳費通知'), findsOneWidget);
    expect(find.text('開啟 Gmail 原信'), findsOneWidget);
    expect(find.text('送到生活收件匣'), findsOneWidget);
    // Fallback is intentionally not a third primary button.
    expect(find.text('Gmail 信箱備援'), findsNothing);
    final more = find.byKey(const ValueKey('gmail-radar-more-item-1'));
    expect(more, findsOneWidget);
    await tester.ensureVisible(more);
    await tester.tap(more);
    await tester.pumpAndSettle();
    expect(find.text('Gmail 信箱備援'), findsOneWidget);
    expect(find.text('手動標示完成'), findsOneWidget);
    await tester.tap(find.text('手動標示完成'));
    await tester.pumpAndSettle();
    expect(api.items.first['status'], 'completed');
    expect(find.text('繳費通知'), findsNothing);
  });
  testWidgets('linked item replaces Life Inbox action with saved feature link',
      (tester) async {
    final api = _FakeRadarApi(authorized: true);
    api.items.add({
      'id': 'item-linked',
      'title': '訂房確認',
      'summary': '已記錄',
      'sender': 'hotel@example.com',
      'status': 'completed',
      'category': 'booking',
      'received_at': '2026-10-16T08:00:00Z',
      'linked_target': 'task',
      'linked_route': '/tasks',
      'linked_entity_id': 'task-1',
      'gmail_url': 'https://mail.google.com/mail/#all/thread-2',
      'gmail_fallback_url': 'https://mail.google.com/mail/#all',
    });
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: GmailRadarPage()),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('已完成'));
    await tester.pumpAndSettle();
    expect(find.text('已完成 · 已存入待辦'), findsOneWidget);
    expect(find.text('開啟待辦'), findsOneWidget);
    expect(find.text('送到生活收件匣'), findsNothing);
    expect(find.text('Gmail 信箱備援'), findsNothing);
    final more = find.byKey(const ValueKey('gmail-radar-more-item-linked'));
    await tester.ensureVisible(more);
    await tester.tap(more);
    await tester.pumpAndSettle();
    expect(find.text('Gmail 信箱備援'), findsOneWidget);
    expect(find.text('手動標示完成'), findsNothing);
  });

  testWidgets('risk and fee category labels stay readable and warn about phishing',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = _FakeRadarApi(authorized: true);
    for (final row in const [
      ['security', '帳號／交易安全警告'],
      ['account', '帳號／訂閱費用警告'],
      ['refund', '退款／訂單異常'],
      ['administrative', '行政／學校／工作待辦'],
    ]) {
      api.items.add({
        'id': 'test-' + row[0],
        'title': '需要確認的通知',
        'summary': '請前往官方網站確認',
        'sender': 'example@example.com',
        'category': row[0],
        'status': 'pending',
        'received_at': '2026-10-17T08:00:00Z',
        'gmail_url': 'https://mail.google.com/mail/#all/thread-1',
        'gmail_fallback_url': 'https://mail.google.com/mail/#all',
      });
    }
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: GmailRadarPage()),
    ));
    await tester.pumpAndSettle();
    expect(find.textContaining('並非確認真偽'), findsOneWidget);
    for (final label in const [
      '帳號／交易安全警告',
      '帳號／訂閱費用警告',
      '退款／訂單異常',
      '行政／學校／工作待辦',
    ]) {
      expect(find.textContaining('分類：' + label), findsOneWidget);
    }
  });

  testWidgets('manual recheck can revisit Gmail messages already checked by Life',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = _FakeRadarApi(authorized: true);
    await tester.pumpWidget(ProviderScope(
      overrides: [platformApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: GmailRadarPage()),
    ));
    await tester.pumpAndSettle();
    final button = find.byKey(const ValueKey('gmail-radar-three-day-recheck'));
    expect(button, findsOneWidget);
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pumpAndSettle();
    expect(api.rechecks, 1);
    expect(find.textContaining('本次重新判讀'), findsOneWidget);
    expect(find.textContaining('重新判讀最新 40 封'), findsOneWidget);
  });


}
