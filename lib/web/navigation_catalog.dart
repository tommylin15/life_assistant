import 'package:flutter/material.dart';

/// Business destinations are defined once for the sidebar and personalization.
/// Old /more/... deep links stay valid, but "More" is not a destination.
class LifeNavItem {
  const LifeNavItem(this.key, this.label, this.path, this.icon, this.selectedIcon);
  final String key;
  final String label;
  final String path;
  final IconData icon;
  final IconData selectedIcon;

  bool matches(String location) =>
      location == path || location.startsWith(path + '/');
}

class LifeNavGroup {
  const LifeNavGroup(this.id, this.title, this.icon, this.keys);
  final String id;
  final String title;
  final IconData icon;
  final List<String> keys;
}

const lifeNavigationItems = <String, LifeNavItem>{
  'today': LifeNavItem('today', '首頁', '/today', Icons.home_outlined, Icons.home),
  'tasks': LifeNavItem('tasks', '待辦', '/tasks', Icons.check_circle_outline, Icons.check_circle),
  'calendar': LifeNavItem('calendar', '日曆', '/calendar', Icons.calendar_month_outlined, Icons.calendar_month),
  'habits': LifeNavItem('habits', '習慣', '/more/habits', Icons.repeat, Icons.repeat_rounded),
  'shopping': LifeNavItem('shopping', '購物清單', '/more/shopping', Icons.shopping_cart_outlined, Icons.shopping_cart),
  'notes': LifeNavItem('notes', '筆記', '/more/notes', Icons.description_outlined, Icons.description),
  'projects': LifeNavItem('projects', '專案', '/projects', Icons.folder_outlined, Icons.folder),
  'drive': LifeNavItem('drive', 'Google Drive 智能整理', '/more/drive', Icons.cloud_outlined, Icons.cloud),
  'gmail_radar': LifeNavItem('gmail_radar', 'Gmail 智慧事項', '/more/gmail-radar', Icons.mark_email_unread_outlined, Icons.mark_email_read),
  'explore': LifeNavItem('explore', '活動探索', '/more/explore', Icons.explore_outlined, Icons.explore),
};

const lifeNavigationGroups = <LifeNavGroup>[
  LifeNavGroup('daily', '日常生活', Icons.event_available_outlined,
      <String>['tasks', 'calendar', 'habits', 'shopping', 'gmail_radar']),
  LifeNavGroup('knowledge', '知識與計畫', Icons.folder_copy_outlined,
      <String>['notes', 'projects', 'drive']),
  LifeNavGroup('activities', '活動與機會', Icons.explore_outlined,
      <String>['explore']),
];

const lifeDefaultPins = <String>['tasks', 'calendar', 'projects'];

String canonicalNavKey(String key) =>
    (key == 'events' || key == 'opportunities') ? 'explore' : key;

LifeNavGroup? lifeGroupFor(String key) {
  for (final group in lifeNavigationGroups) {
    if (group.keys.contains(key)) return group;
  }
  return null;
}

/// Convert legacy flat more_order to group-contiguous ordering without
/// discarding the owner's within-group preferences. A contiguous stored order
/// also persists reordered groups using the existing API, without a migration.
List<String> normalizeNavigationOrder(Iterable<String> saved) {
  final stored = <String>[];
  for (final raw in saved) {
    final key = canonicalNavKey(raw);
    if (lifeGroupFor(key) != null && !stored.contains(key)) stored.add(key);
  }
  final appeared = <String>{};
  var last = '';
  var contiguous = true;
  for (final key in stored) {
    final group = lifeGroupFor(key)!.id;
    if (group != last && appeared.contains(group)) contiguous = false;
    appeared.add(group);
    last = group;
  }
  final groups = <LifeNavGroup>[];
  if (contiguous && stored.isNotEmpty) {
    for (final key in stored) {
      final group = lifeGroupFor(key)!;
      if (!groups.contains(group)) groups.add(group);
    }
  }
  for (final group in lifeNavigationGroups) {
    if (!groups.contains(group)) groups.add(group);
  }
  return [
    for (final group in groups)
      ...[...stored.where(group.keys.contains),
          ...group.keys.where((key) => !stored.contains(key))],
  ];
}

List<LifeNavGroup> orderedNavigationGroups(Iterable<String> saved) {
  final order = normalizeNavigationOrder(saved);
  final result = <LifeNavGroup>[];
  for (final key in order) {
    final group = lifeGroupFor(key)!;
    if (!result.contains(group)) result.add(group);
  }
  return result;
}

List<String> availablePinKeys(Iterable<String> selected, bool Function(String) enabled) {
  final keys = <String>[];
  for (final raw in [...selected, ...lifeDefaultPins, ...lifeNavigationItems.keys]) {
    final key = canonicalNavKey(raw);
    if (key == 'today' || !lifeNavigationItems.containsKey(key) ||
        !enabled(key) || keys.contains(key)) continue;
    keys.add(key);
    if (keys.length == 3) break;
  }
  return keys;
}
