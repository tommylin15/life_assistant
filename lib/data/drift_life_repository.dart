import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../domain/life_repository.dart';
import '../domain/models.dart';
import 'db/app_database.dart';

class DriftLifeRepository implements LifeRepository {
  DriftLifeRepository(this.db);

  final AppDatabase db;
  final _uuid = const Uuid();

  Future<void> _log(
    String action,
    String summary, {
    String? type,
    String? id,
  }) => db.activityLogDao.insert(
    ActivityLogsCompanion.insert(
      id: _uuid.v4(),
      actionType: action,
      entityType: Value(type),
      entityId: Value(id),
      summary: summary,
      createdAt: DateTime.now(),
    ),
  );

  @override
  Stream<List<TaskItem>> watchTasks() => db.itemsDao.watchActive().map(
    (rows) => rows
        .map(
          (row) => TaskItem(
            id: row.id,
            title: row.title,
            note: row.note,
            status:
                ItemStatus.values
                    .where((v) => v.name == row.status)
                    .firstOrNull ??
                ItemStatus.pending,
            priority:
                ItemPriority.values
                    .where((v) => v.name == row.priority)
                    .firstOrNull ??
                ItemPriority.normal,
            dueAt: row.dueAt,
            reminderAt: row.reminderAt,
            projectId: row.projectId,
            createdAt: row.createdAt,
            updatedAt: row.updatedAt,
            completedAt: row.completedAt,
          ),
        )
        .toList(),
  );

  @override
  Future<TaskItem?> getTask(String id) async {
    final row = await db.itemsDao.getById(id);
    return row == null
        ? null
        : TaskItem(
            id: row.id,
            title: row.title,
            note: row.note,
            status:
                ItemStatus.values
                    .where((v) => v.name == row.status)
                    .firstOrNull ??
                ItemStatus.pending,
            priority:
                ItemPriority.values
                    .where((v) => v.name == row.priority)
                    .firstOrNull ??
                ItemPriority.normal,
            dueAt: row.dueAt,
            reminderAt: row.reminderAt,
            projectId: row.projectId,
            createdAt: row.createdAt,
            updatedAt: row.updatedAt,
            completedAt: row.completedAt,
          );
  }

  @override
  Future<String> saveTask({
    String? id,
    required String title,
    String? note,
    ItemPriority priority = ItemPriority.normal,
    DateTime? dueAt,
    DateTime? reminderAt,
    String? projectId,
  }) async {
    final clean = title.trim();
    if (clean.isEmpty) throw ArgumentError.value(title, 'title');
    final now = DateTime.now();
    final taskId = id ?? _uuid.v4();
    await db.transaction(() async {
      final existing = id == null ? null : await db.itemsDao.getById(id);
      await db.itemsDao.upsert(
        ItemsCompanion.insert(
          id: taskId,
          title: clean,
          note: Value(note?.trim()),
          priority: Value(priority.name),
          dueAt: Value(dueAt),
          reminderAt: Value(reminderAt),
          projectId: Value(projectId),
          createdAt: existing?.createdAt ?? now,
          updatedAt: now,
        ),
      );
      await _log(
        existing == null ? 'create_task' : 'update_task',
        clean,
        type: 'task',
        id: taskId,
      );
    });
    return taskId;
  }

  @override
  Stream<List<ChecklistEntry>> watchChecklist(String taskId) => db.itemsDao
      .watchChecklist(taskId)
      .map(
        (rows) => rows
            .map(
              (e) => ChecklistEntry(id: e.id, title: e.title, isDone: e.isDone),
            )
            .toList(),
      );
  @override
  Future<void> addChecklist(String taskId, String title) async {
    final id = _uuid.v4();
    await db.itemsDao.upsertChecklist(
      ChecklistItemsCompanion.insert(
        id: id,
        itemId: taskId,
        title: title.trim(),
        createdAt: DateTime.now(),
      ),
    );
    await _log('add_checklist', title.trim(), type: 'task', id: taskId);
  }

  @override
  Future<void> toggleChecklist(String id, bool isDone) =>
      (db.update(db.checklistItems)..where((t) => t.id.equals(id))).write(
        ChecklistItemsCompanion(isDone: Value(isDone)),
      );

  @override
  Stream<List<LifeTag>> watchTags(String entityType, String entityId) =>
      (db.select(db.tags)..orderBy([(t) => OrderingTerm.asc(t.name)]))
          .watch()
          .asyncMap((tags) async {
            final links =
                await (db.select(db.entityTags)..where(
                      (t) =>
                          t.entityType.equals(entityType) &
                          t.entityId.equals(entityId),
                    ))
                    .get();
            final selected = links.map((e) => e.tagId).toSet();
            return tags
                .map(
                  (e) => LifeTag(
                    id: e.id,
                    name: e.name,
                    selected: selected.contains(e.id),
                  ),
                )
                .toList();
          });
  @override
  Future<void> toggleTag(
    String entityType,
    String entityId,
    String tagId,
    bool selected,
  ) async {
    final query = db.delete(db.entityTags)
      ..where(
        (t) =>
            t.entityType.equals(entityType) &
            t.entityId.equals(entityId) &
            t.tagId.equals(tagId),
      );
    if (selected)
      await db
          .into(db.entityTags)
          .insert(
            EntityTagsCompanion.insert(
              entityType: entityType,
              entityId: entityId,
              tagId: tagId,
            ),
            mode: InsertMode.insertOrIgnore,
          );
    else
      await query.go();
  }

  @override
  Future<void> addTag(String name) async {
    final clean = name.trim();
    if (clean.isEmpty) return;
    await db
        .into(db.tags)
        .insert(
          TagsCompanion.insert(id: _uuid.v4(), name: clean),
          mode: InsertMode.insertOrIgnore,
        );
  }

  @override
  Stream<List<LifeAttachment>> watchAttachments(
    String entityType,
    String entityId,
  ) =>
      (db.select(db.attachments)..where(
            (t) =>
                t.entityType.equals(entityType) & t.entityId.equals(entityId),
          ))
          .watch()
          .map(
            (rows) => rows
                .map(
                  (e) => LifeAttachment(
                    id: e.id,
                    displayName: e.displayName,
                    localPath: e.localPath,
                    mimeType: e.mimeType,
                  ),
                )
                .toList(),
          );
  @override
  Future<void> addAttachment(
    String entityType,
    String entityId,
    String displayName,
    String localPath, {
    String? mimeType,
  }) async {
    final id = _uuid.v4();
    await db
        .into(db.attachments)
        .insert(
          AttachmentsCompanion.insert(
            id: id,
            entityType: entityType,
            entityId: entityId,
            displayName: displayName,
            localPath: localPath,
            mimeType: Value(mimeType),
            createdAt: DateTime.now(),
          ),
        );
    await _log('add_attachment', displayName, type: entityType, id: entityId);
  }

  @override
  Future<void> removeAttachment(String id) =>
      (db.delete(db.attachments)..where((t) => t.id.equals(id))).go();

  @override
  Future<List<SearchHit>> search(String query) async {
    final clean = query.trim();
    if (clean.isEmpty) return const [];
    final pattern = '%$clean%', hits = <SearchHit>[];
    final tasks =
        await (db.select(db.items)..where(
              (t) =>
                  (t.title.like(pattern) | t.note.like(pattern)) &
                  t.deletedAt.isNull(),
            ))
            .get();
    hits.addAll(
      tasks.map(
        (e) =>
            SearchHit(id: e.id, type: 'task', title: e.title, snippet: e.note),
      ),
    );
    final projects = await (db.select(
      db.projects,
    )..where((t) => t.name.like(pattern) | t.summary.like(pattern))).get();
    hits.addAll(
      projects.map(
        (e) => SearchHit(
          id: e.id,
          type: 'project',
          title: e.name,
          snippet: e.summary,
        ),
      ),
    );
    final events = await (db.select(
      db.calendarEventsCache,
    )..where((t) => t.title.like(pattern))).get();
    hits.addAll(
      events.map(
        (e) => SearchHit(
          id: e.id,
          type: 'calendar',
          title: e.title,
          snippet: e.startsAt.toIso8601String(),
        ),
      ),
    );
    final notes = await db
        .customSelect(
          'SELECT n.id,n.title,n.body FROM notes n JOIN notes_fts f ON n.rowid=f.rowid WHERE notes_fts MATCH ? LIMIT 50',
          variables: [Variable.withString('"${clean.replaceAll('"', '""')}"*')],
          readsFrom: {db.notes},
        )
        .get();
    hits.addAll(
      notes.map(
        (e) => SearchHit(
          id: e.read<String>('id'),
          type: 'note',
          title: e.readNullable<String>('title') ?? '未命名筆記',
          snippet: e.readNullable<String>('body'),
        ),
      ),
    );
    return hits;
  }

  @override
  Future<void> setTaskStatus(String id, ItemStatus status) =>
      db.transaction(() async {
        await (db.update(db.items)..where((t) => t.id.equals(id))).write(
          ItemsCompanion(
            status: Value(status.name),
            completedAt: Value(
              status == ItemStatus.completed ? DateTime.now() : null,
            ),
            updatedAt: Value(DateTime.now()),
          ),
        );
        await _log('set_task_status', status.name, type: 'task', id: id);
      });

  @override
  Future<void> deleteTask(String id) => db.transaction(() async {
    await db.itemsDao.softDelete(id);
    await _log('delete_task', '待辦已移至刪除狀態', type: 'task', id: id);
  });

  @override
  Stream<List<LifeProject>> watchProjects() => db.projectsDao.watchAll().map(
    (rows) => rows
        .map(
          (row) => LifeProject(
            id: row.id,
            name: row.name,
            status: row.status,
            summary: row.summary,
          ),
        )
        .toList(),
  );

  @override
  Future<String> saveProject({
    String? id,
    required String name,
    String? summary,
  }) async {
    final clean = name.trim();
    if (clean.isEmpty) throw ArgumentError.value(name, 'name');
    final now = DateTime.now();
    final projectId = id ?? _uuid.v4();
    await db.transaction(() async {
      final existing = id == null ? null : await db.projectsDao.getById(id);
      await db.projectsDao.upsert(
        ProjectsCompanion.insert(
          id: projectId,
          name: clean,
          summary: Value(summary?.trim()),
          createdAt: existing?.createdAt ?? now,
          updatedAt: now,
        ),
      );
      await _log(
        existing == null ? 'create_project' : 'update_project',
        clean,
        type: 'project',
        id: projectId,
      );
    });
    return projectId;
  }

  @override
  Future<void> deleteProject(String id) => db.transaction(() async {
    await db.projectsDao.deleteById(id);
    await _log('delete_project', '專案已刪除', type: 'project', id: id);
  });

  @override
  Stream<List<LifeNote>> watchNotes() => db.notesDao.watchAll().map(
    (rows) => rows
        .map(
          (row) => LifeNote(
            id: row.id,
            title: row.title ?? '',
            body: row.body ?? '',
            updatedAt: row.updatedAt,
            projectId: row.projectId,
          ),
        )
        .toList(),
  );

  @override
  Future<LifeNote?> getNote(String id) async {
    final row = await db.notesDao.getById(id);
    return row == null
        ? null
        : LifeNote(
            id: row.id,
            title: row.title ?? '',
            body: row.body ?? '',
            updatedAt: row.updatedAt,
            projectId: row.projectId,
          );
  }

  @override
  Future<String> saveNote({
    String? id,
    required String title,
    required String body,
    String? projectId,
  }) async {
    final now = DateTime.now();
    final noteId = id ?? _uuid.v4();
    await db.transaction(() async {
      final existing = id == null ? null : await db.notesDao.getById(id);
      await db.notesDao.upsert(
        NotesCompanion.insert(
          id: noteId,
          title: Value(title.trim()),
          body: Value(body),
          projectId: Value(projectId),
          createdAt: existing?.createdAt ?? now,
          updatedAt: now,
        ),
      );
      await _log(
        existing == null ? 'create_note' : 'update_note',
        title.trim().isEmpty ? '未命名筆記' : title.trim(),
        type: 'note',
        id: noteId,
      );
    });
    return noteId;
  }

  @override
  Future<void> deleteNote(String id) => db.transaction(() async {
    await db.notesDao.deleteById(id);
    await _log('delete_note', '筆記已刪除', type: 'note', id: id);
  });

  @override
  Stream<List<LifeNote>> watchLinkedNotes(String noteId) =>
      (db.select(db.noteLinks)..where(
            (t) =>
                t.sourceNoteId.equals(noteId) | t.targetNoteId.equals(noteId),
          ))
          .watch()
          .asyncMap((links) async {
            final ids = links
                .expand((e) => [e.sourceNoteId, e.targetNoteId])
                .where((e) => e != noteId)
                .toSet();
            if (ids.isEmpty) return <LifeNote>[];
            final rows = await (db.select(
              db.notes,
            )..where((t) => t.id.isIn(ids))).get();
            return rows
                .map(
                  (e) => LifeNote(
                    id: e.id,
                    title: e.title ?? '',
                    body: e.body ?? '',
                    updatedAt: e.updatedAt,
                    projectId: e.projectId,
                  ),
                )
                .toList();
          });
  @override
  Future<void> linkNotes(String sourceId, String targetId) => db
      .into(db.noteLinks)
      .insert(
        NoteLinksCompanion.insert(
          sourceNoteId: sourceId,
          targetNoteId: targetId,
        ),
        mode: InsertMode.insertOrIgnore,
      );

  @override
  Stream<List<LifeHabit>> watchHabits() => db.habitsDao.watchActive().map(
    (rows) => rows
        .map(
          (row) => LifeHabit(
            id: row.id,
            title: row.title,
            recurrenceRule: row.recurrenceRule,
            isActive: row.isActive,
            reminderTime: row.reminderTime,
          ),
        )
        .toList(),
  );

  @override
  Future<void> saveHabit({
    String? id,
    required String title,
    required String recurrenceRule,
    String? reminderTime,
  }) async {
    final habitId = id ?? _uuid.v4();
    await db.transaction(() async {
      await db.habitsDao.upsert(
        HabitsCompanion.insert(
          id: habitId,
          title: title.trim(),
          recurrenceRule: recurrenceRule,
          reminderTime: Value(reminderTime),
          createdAt: DateTime.now(),
        ),
      );
      await _log('save_habit', title.trim(), type: 'habit', id: habitId);
    });
  }

  @override
  Future<void> completeHabit(String id) => db.transaction(() async {
    await db.habitsDao.logCompletion(
      HabitLogsCompanion.insert(
        id: _uuid.v4(),
        habitId: id,
        completedAt: DateTime.now(),
      ),
    );
    await _log('complete_habit', '習慣已完成', type: 'habit', id: id);
  });

  @override
  Stream<List<HabitCompletion>> watchHabitHistory(String id) =>
      (db.select(db.habitLogs)
            ..where((t) => t.habitId.equals(id))
            ..orderBy([(t) => OrderingTerm.desc(t.completedAt)]))
          .watch()
          .map(
            (rows) => rows.map((e) => HabitCompletion(e.completedAt)).toList(),
          );

  @override
  Stream<List<LifeShoppingList>> watchShopping() =>
      db.shoppingDao.watchLists().asyncMap((lists) async {
        final result = <LifeShoppingList>[];
        for (final list in lists) {
          final rows =
              await (db.select(db.shoppingItems)
                    ..where((t) => t.listId.equals(list.id))
                    ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
                  .get();
          result.add(
            LifeShoppingList(
              id: list.id,
              name: list.name,
              projectId: list.projectId,
              items: rows
                  .map(
                    (row) => LifeShoppingItem(
                      id: row.id,
                      listId: row.listId,
                      name: row.name,
                      isDone: row.isDone,
                      category: row.category,
                    ),
                  )
                  .toList(),
            ),
          );
        }
        return result;
      });

  @override
  Future<void> addShoppingList(String name, {String? projectId}) async {
    final id = _uuid.v4();
    await db.transaction(() async {
      await db.shoppingDao.upsertList(
        ShoppingListsCompanion.insert(
          id: id,
          name: name.trim(),
          projectId: Value(projectId),
          createdAt: DateTime.now(),
        ),
      );
      await _log(
        'create_shopping_list',
        name.trim(),
        type: 'shopping_list',
        id: id,
      );
    });
  }

  @override
  Future<void> addShoppingItem(
    String listId,
    String name, {
    String? category,
  }) async {
    final id = _uuid.v4();
    await db.transaction(() async {
      await db.shoppingDao.upsertItem(
        ShoppingItemsCompanion.insert(
          id: id,
          listId: listId,
          name: name.trim(),
          category: Value(category),
        ),
      );
      await _log(
        'add_shopping_item',
        name.trim(),
        type: 'shopping_item',
        id: id,
      );
    });
  }

  @override
  Future<void> toggleShoppingItem(String id, bool isDone) =>
      db.transaction(() async {
        await (db.update(db.shoppingItems)..where((t) => t.id.equals(id)))
            .write(ShoppingItemsCompanion(isDone: Value(isDone)));
        await _log(
          'toggle_shopping_item',
          isDone ? '採買完成' : '恢復採買',
          type: 'shopping_item',
          id: id,
        );
      });

  @override
  Stream<List<LifeActivity>> watchActivity() =>
      db.activityLogDao.watchRecent().map(
        (rows) => rows
            .map(
              (row) => LifeActivity(
                summary: row.summary,
                result: row.result,
                createdAt: row.createdAt,
                entityType: row.entityType,
                entityId: row.entityId,
              ),
            )
            .toList(),
      );

  @override
  Stream<List<LifeTemplate>> watchTemplates() =>
      (db.select(
        db.templates,
      )..orderBy([(t) => OrderingTerm.asc(t.name)])).watch().map(
        (rows) => rows
            .map(
              (row) => LifeTemplate(
                id: row.id,
                name: row.name,
                type: row.templateType,
                payloadJson: row.payloadJson,
              ),
            )
            .toList(),
      );

  @override
  Future<void> saveTemplate({
    String? id,
    required String name,
    required String type,
    required String payloadJson,
  }) async {
    final now = DateTime.now(), templateId = id ?? _uuid.v4();
    await db.transaction(() async {
      await db
          .into(db.templates)
          .insertOnConflictUpdate(
            TemplatesCompanion.insert(
              id: templateId,
              name: name.trim(),
              templateType: type,
              payloadJson: payloadJson,
              createdAt: now,
              updatedAt: now,
            ),
          );
      await _log(
        'save_template',
        name.trim(),
        type: 'template',
        id: templateId,
      );
    });
  }
}
