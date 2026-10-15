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
