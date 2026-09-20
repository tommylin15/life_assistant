import 'models.dart';

abstract interface class LifeRepository {
  Stream<List<TaskItem>> watchTasks();
  Future<TaskItem?> getTask(String id);
  Future<String> saveTask({
    String? id,
    required String title,
    String? note,
    ItemPriority priority = ItemPriority.normal,
    DateTime? dueAt,
    DateTime? reminderAt,
    String? projectId,
  });
  Future<void> setTaskStatus(String id, ItemStatus status);
  Future<void> deleteTask(String id);
  Stream<List<ChecklistEntry>> watchChecklist(String taskId);
  Future<void> addChecklist(String taskId, String title);
  Future<void> toggleChecklist(String id, bool isDone);
  Stream<List<LifeTag>> watchTags(String entityType, String entityId);
  Future<void> toggleTag(
    String entityType,
    String entityId,
    String tagId,
    bool selected,
  );
  Future<void> addTag(String name);
  Stream<List<LifeAttachment>> watchAttachments(
    String entityType,
    String entityId,
  );
  Future<void> addAttachment(
    String entityType,
    String entityId,
    String displayName,
    String localPath, {
    String? mimeType,
  });
  Future<void> removeAttachment(String id);
  Future<List<SearchHit>> search(String query);

  Stream<List<LifeProject>> watchProjects();
  Future<String> saveProject({
    String? id,
    required String name,
    String? summary,
  });
  Future<void> deleteProject(String id);

  Stream<List<LifeNote>> watchNotes();
  Future<LifeNote?> getNote(String id);
  Future<String> saveNote({
    String? id,
    required String title,
    required String body,
    String? projectId,
  });
  Future<void> deleteNote(String id);
  Stream<List<LifeNote>> watchLinkedNotes(String noteId);
  Future<void> linkNotes(String sourceId, String targetId);

  Stream<List<LifeHabit>> watchHabits();
  Future<void> saveHabit({
    String? id,
    required String title,
    required String recurrenceRule,
    String? reminderTime,
  });
  Future<void> completeHabit(String id);
  Stream<List<HabitCompletion>> watchHabitHistory(String id);

  Stream<List<LifeShoppingList>> watchShopping();
  Future<void> addShoppingList(String name, {String? projectId});
  Future<void> addShoppingItem(String listId, String name, {String? category});
  Future<void> toggleShoppingItem(String id, bool isDone);

  Stream<List<LifeActivity>> watchActivity();
  Stream<List<LifeTemplate>> watchTemplates();
  Future<void> saveTemplate({
    String? id,
    required String name,
    required String type,
    required String payloadJson,
  });
}
