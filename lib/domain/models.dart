enum ItemStatus { pending, waiting, scheduled, completed, cancelled }

enum ItemPriority { low, normal, high }

class TaskItem {
  const TaskItem({
    required this.id,
    required this.title,
    required this.status,
    required this.priority,
    required this.createdAt,
    required this.updatedAt,
    this.note,
    this.dueAt,
    this.reminderAt,
    this.projectId,
    this.completedAt,
  });

  final String id;
  final String title;
  final String? note;
  final ItemStatus status;
  final ItemPriority priority;
  final DateTime? dueAt;
  final DateTime? reminderAt;
  final String? projectId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? completedAt;
}

class LifeProject {
  const LifeProject({
    required this.id,
    required this.name,
    required this.status,
    this.summary,
  });
  final String id;
  final String name;
  final String status;
  final String? summary;
}

class LifeNote {
  const LifeNote({
    required this.id,
    required this.title,
    required this.body,
    required this.updatedAt,
    this.projectId,
  });
  final String id;
  final String title;
  final String body;
  final DateTime updatedAt;
  final String? projectId;
}

class LifeHabit {
  const LifeHabit({
    required this.id,
    required this.title,
    required this.recurrenceRule,
    required this.isActive,
    this.reminderTime,
  });
  final String id;
  final String title;
  final String recurrenceRule;
  final bool isActive;
  final String? reminderTime;
}

class HabitCompletion {
  const HabitCompletion(this.completedAt);
  final DateTime completedAt;
}

class LifeShoppingList {
  const LifeShoppingList({
    required this.id,
    required this.name,
    required this.items,
    this.projectId,
  });
  final String id;
  final String name;
  final List<LifeShoppingItem> items;
  final String? projectId;
}

class LifeShoppingItem {
  const LifeShoppingItem({
    required this.id,
    required this.listId,
    required this.name,
    required this.isDone,
    this.category,
  });
  final String id;
  final String listId;
  final String name;
  final bool isDone;
  final String? category;
}

class LifeActivity {
  const LifeActivity({
    required this.summary,
    required this.result,
    required this.createdAt,
    this.entityType,
    this.entityId,
  });
  final String summary;
  final String result;
  final DateTime createdAt;
  final String? entityType, entityId;
}

class LifeTemplate {
  const LifeTemplate({
    required this.id,
    required this.name,
    required this.type,
    required this.payloadJson,
  });
  final String id, name, type, payloadJson;
}

class ChecklistEntry {
  const ChecklistEntry({
    required this.id,
    required this.title,
    required this.isDone,
  });
  final String id, title;
  final bool isDone;
}

class LifeTag {
  const LifeTag({required this.id, required this.name, required this.selected});
  final String id, name;
  final bool selected;
}

class LifeAttachment {
  const LifeAttachment({
    required this.id,
    required this.displayName,
    required this.localPath,
    this.mimeType,
  });
  final String id, displayName, localPath;
  final String? mimeType;
}

class SearchHit {
  const SearchHit({
    required this.id,
    required this.type,
    required this.title,
    this.snippet,
  });
  final String id, type, title;
  final String? snippet;
}

class CalendarSlot {
  const CalendarSlot({
    required this.id,
    required this.googleEventId,
    required this.title,
    required this.startsAt,
    required this.endsAt,
    this.location,
    this.projectId,
  });
  final String id, googleEventId, title;
  final DateTime startsAt, endsAt;
  final String? location, projectId;
}

class GmailSummary {
  const GmailSummary({
    required this.id,
    required this.messageId,
    required this.subject,
    required this.sender,
    required this.receivedAt,
    this.snippet,
    this.linkedEntityType,
    this.linkedEntityId,
  });
  final String id, messageId, subject, sender;
  final DateTime receivedAt;
  final String? snippet, linkedEntityType, linkedEntityId;
}
