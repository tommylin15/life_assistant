import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/navigation_catalog.dart';
import 'package:life_assistant/web/curated_activity_card.dart';

void main() {
  test('legacy opportunity and events pins map to one discovery destination', () {
    expect(canonicalNavKey('opportunities'), 'explore');
    expect(canonicalNavKey('events'), 'explore');
    expect(normalizeNavigationOrder(
      const ['opportunities', 'explore', 'events']),
      contains('explore'));
    expect(normalizeNavigationOrder(
      const ['opportunities', 'explore', 'events'])
        .where((key) => key == 'explore').length, 1);
    expect(lifeNavigationGroups.last.keys, const ['explore']);
    expect(lifeNavigationItems.containsKey('opportunities'), false);
    expect(availablePinKeys(const ['opportunities', 'events', 'explore'],
      (_) => true).where((key) => key == 'explore').length, 1);
  });

  test('unified activity screen has no urgent tab and keeps complete explore feed', () async {
    final source = await File('lib/web/curated_events_page.dart').readAsString();
    expect(source, contains("key: const ValueKey('activity-mode-all')"));
    expect(source, contains("key: const ValueKey('activity-mode-saved')"));
    expect(source, isNot(contains("activity-mode-urgent")));
    expect(source, contains("'entry': 'explore'"));
    expect(source, contains("'opening_soon': '即將開報'"));
    expect(source, contains("'limited': '限額優惠'"));
  });

  test('one parent activity has one visual group across distinct offers', () {
    final groups = groupActivities([
      {'identity_key': 'one', 'parent_event_key': 'activity-1',
        'handoff_details': {'record_type': 'offer'}},
      {'identity_key': 'two', 'parent_event_key': 'activity-1',
        'handoff_details': {'record_type': 'main'}},
      {'identity_key': 'three', 'parent_event_key': 'activity-2',
        'handoff_details': {'record_type': 'main'}},
    ]);
    expect(groups.length, 2);
    expect(groups.first.length, 2);
    expect(groups.first.first['identity_key'], 'two');
  });
}
