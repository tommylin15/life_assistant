import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/navigation_catalog.dart';

void main() {
  test('legacy flat order becomes grouped and retains each group item order', () {
    const legacy = ['notes', 'habits', 'opportunities', 'explore',
        'shopping', 'drive', 'integrations'];
    final result = normalizeNavigationOrder(legacy);
    expect(result, containsAll(['notes', 'habits', 'explore',
        'shopping', 'drive', 'tasks', 'calendar', 'projects']));
    expect(orderedNavigationGroups(result).map((e) => e.id).toList(),
        ['daily', 'knowledge', 'activities']);
    expect(result, isNot(contains('integrations')));
    expect(result, isNot(contains('today')));
  });

  test('a contiguous saved order preserves group reordering', () {
    const reordered = ['opportunities', 'explore', 'notes', 'projects', 'drive',
        'shopping', 'habits', 'tasks', 'calendar'];
    final normalized = normalizeNavigationOrder(reordered);
    expect(normalized, containsAll(reordered.where((k) => k != 'opportunities')));
    expect(normalized, contains('gmail_radar'));
    expect(normalizeNavigationOrder(reordered).where((k) => k == 'explore').length, 1);
    expect(orderedNavigationGroups(reordered).map((e) => e.id).toList(),
        ['activities', 'knowledge', 'daily']);
  });

  test('bottom pins are distinct and exclude Home, More, and integrations', () {
    final keys = availablePinKeys(
        ['integrations', 'today', 'notes', 'notes', 'shopping'],
        (key) => key != 'calendar');
    expect(keys.length, 3);
    expect(keys.toSet().length, 3);
    expect(keys.take(2), ['notes', 'shopping']);
    expect(keys, isNot(contains('integrations')));
    expect(keys, isNot(contains('today')));
  });
}
