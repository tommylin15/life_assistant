import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'migrations/migrations.dart';
import 'dao/items_dao.dart';
import 'dao/projects_dao.dart';
import 'dao/notes_dao.dart';
import 'dao/habits_dao.dart';
import 'dao/shopping_dao.dart';
import 'dao/activity_log_dao.dart';
import 'dao/calendar_dao.dart';
import 'dao/gmail_dao.dart';
import 'dao/preferences_dao.dart';

part 'app_database.g.dart';

// ─── Tables ───────────────────────────────────────────────────────────────────

class Items extends Table {
  TextColumn get id => text()();
  TextColumn get title => text()();
  TextColumn get note => text().nullable()();
  TextColumn get status => text().withDefault(const Constant('pending'))();
  TextColumn get priority => text().withDefault(const Constant('normal'))();
  DateTimeColumn get dueAt => dateTime().nullable()();
  DateTimeColumn get reminderAt => dateTime().nullable()();
  TextColumn get projectId => text().nullable()();
  TextColumn get sourceType => text().nullable()();
  TextColumn get sourceRef => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  DateTimeColumn get completedAt => dateTime().nullable()();
  DateTimeColumn get deletedAt => dateTime().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

class ChecklistItems extends Table {
  TextColumn get id => text()();
  TextColumn get itemId => text().references(Items, #id)();
  TextColumn get title => text()();
  BoolColumn get isDone => boolean().withDefault(const Constant(false))();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class Projects extends Table {
  TextColumn get id => text()();
  TextColumn get name => text()();
  TextColumn get summary => text().nullable()();
  TextColumn get status => text().withDefault(const Constant('active'))();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class Notes extends Table {
  TextColumn get id => text()();
  TextColumn get title => text().nullable()();
  TextColumn get body => text().nullable()();
  TextColumn get projectId => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class NoteLinks extends Table {
  @ReferenceName('sourceNoteLinks')
  TextColumn get sourceNoteId => text().references(Notes, #id)();
  @ReferenceName('targetNoteLinks')
  TextColumn get targetNoteId => text().references(Notes, #id)();

  @override
  Set<Column> get primaryKey => {sourceNoteId, targetNoteId};
}

class Habits extends Table {
  TextColumn get id => text()();
  TextColumn get title => text()();
  TextColumn get recurrenceRule => text()();
  TextColumn get reminderTime => text().nullable()();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class HabitLogs extends Table {
  TextColumn get id => text()();
  TextColumn get habitId => text().references(Habits, #id)();
  DateTimeColumn get completedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class ShoppingLists extends Table {
  TextColumn get id => text()();
  TextColumn get name => text()();
  TextColumn get projectId => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class ShoppingItems extends Table {
  TextColumn get id => text()();
  TextColumn get listId => text().references(ShoppingLists, #id)();
  TextColumn get name => text()();
  TextColumn get category => text().nullable()();
  BoolColumn get isDone => boolean().withDefault(const Constant(false))();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  @override
  Set<Column> get primaryKey => {id};
}

class Tags extends Table {
  TextColumn get id => text()();
  TextColumn get name => text().unique()();

  @override
  Set<Column> get primaryKey => {id};
}

class EntityTags extends Table {
  TextColumn get entityType => text()();
  TextColumn get entityId => text()();
  TextColumn get tagId => text().references(Tags, #id)();

  @override
  Set<Column> get primaryKey => {entityType, entityId, tagId};
}

class Attachments extends Table {
  TextColumn get id => text()();
  TextColumn get entityType => text()();
  TextColumn get entityId => text()();
  TextColumn get displayName => text()();
  TextColumn get localPath => text()();
  TextColumn get mimeType => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class CalendarEventsCache extends Table {
  TextColumn get id => text()();
  TextColumn get googleEventId => text().unique()();
  TextColumn get calendarId => text()();
  TextColumn get title => text()();
  DateTimeColumn get startsAt => dateTime()();
  DateTimeColumn get endsAt => dateTime()();
  TextColumn get location => text().nullable()();
  TextColumn get description => text().nullable()();
  TextColumn get projectId => text().nullable()();
  DateTimeColumn get lastSyncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class GmailRefs extends Table {
  TextColumn get id => text()();
  TextColumn get gmailMessageId => text().unique()();
  TextColumn get threadId => text()();
  TextColumn get subject => text()();
  TextColumn get sender => text()();
  DateTimeColumn get receivedAt => dateTime()();
  TextColumn get snippet => text().nullable()();
  TextColumn get linkedEntityType => text().nullable()();
  TextColumn get linkedEntityId => text().nullable()();
  DateTimeColumn get lastSyncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class Reminders extends Table {
  TextColumn get id => text()();
  TextColumn get entityType => text()();
  TextColumn get entityId => text()();
  DateTimeColumn get scheduledAt => dateTime()();
  TextColumn get type => text().withDefault(const Constant('notification'))();
  BoolColumn get isEnabled => boolean().withDefault(const Constant(true))();

  @override
  Set<Column> get primaryKey => {id};
}

class Templates extends Table {
  TextColumn get id => text()();
  TextColumn get name => text()();
  TextColumn get templateType => text()();
  TextColumn get payloadJson => text()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class ActivityLogs extends Table {
  TextColumn get id => text()();
  TextColumn get actionType => text()();
  TextColumn get entityType => text().nullable()();
  TextColumn get entityId => text().nullable()();
  TextColumn get summary => text()();
  TextColumn get result => text().withDefault(const Constant('success'))();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class Preferences extends Table {
  TextColumn get key => text()();
  TextColumn get valueJson => text()();

  @override
  Set<Column> get primaryKey => {key};
}

class BridgeState extends Table {
  TextColumn get key => text()();
  TextColumn get valueJson => text()();

  @override
  Set<Column> get primaryKey => {key};
}

class SyncPairs extends Table {
  TextColumn get id => text()();
  TextColumn get localRootUri => text()();
  TextColumn get driveFolderId => text()();
  BoolColumn get includeSubfolders =>
      boolean().withDefault(const Constant(true))();
  TextColumn get allowedTypesJson => text()();
  BoolColumn get initialSyncCompleted =>
      boolean().withDefault(const Constant(false))();
  DateTimeColumn get lastSuccessfulSyncAt => dateTime().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  @override
  Set<Column> get primaryKey => {id};
}

class SyncFiles extends Table {
  TextColumn get id => text()();
  TextColumn get syncPairId => text().references(SyncPairs, #id)();
  TextColumn get relativePath => text()();
  TextColumn get driveFileId => text().nullable()();
  TextColumn get mimeType => text().nullable()();
  TextColumn get lastSyncedHash => text().nullable()();
  TextColumn get localHash => text().nullable()();
  TextColumn get driveHash => text().nullable()();
  DateTimeColumn get localModifiedAt => dateTime().nullable()();
  DateTimeColumn get driveModifiedAt => dateTime().nullable()();
  DateTimeColumn get lastSuccessfulSyncAt => dateTime().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  @override
  Set<Column> get primaryKey => {id};
  @override
  List<Set<Column>> get uniqueKeys => [
    {syncPairId, relativePath},
  ];
}

class SyncOperations extends Table {
  TextColumn get id => text()();
  TextColumn get syncPairId => text().references(SyncPairs, #id)();
  TextColumn get relativePath => text()();
  TextColumn get operationType => text()();
  TextColumn get status => text()();
  TextColumn get errorCode => text().nullable()();
  DateTimeColumn get startedAt => dateTime()();
  DateTimeColumn get finishedAt => dateTime().nullable()();
  @override
  Set<Column> get primaryKey => {id};
}

class BridgeExecutions extends Table {
  TextColumn get requestId => text()();
  TextColumn get actionId => text()();
  TextColumn get status => text()();
  TextColumn get entityId => text().nullable()();
  DateTimeColumn get executedAt => dateTime()();
  @override
  Set<Column> get primaryKey => {requestId, actionId};
}

// ─── Database ─────────────────────────────────────────────────────────────────

@DriftDatabase(
  tables: [
    Items,
    ChecklistItems,
    Projects,
    Notes,
    NoteLinks,
    Habits,
    HabitLogs,
    ShoppingLists,
    ShoppingItems,
    Tags,
    EntityTags,
    Attachments,
    CalendarEventsCache,
    GmailRefs,
    Reminders,
    Templates,
    ActivityLogs,
    Preferences,
    BridgeState,
    SyncPairs,
    SyncFiles,
    SyncOperations,
    BridgeExecutions,
  ],
  daos: [
    ItemsDao,
    ProjectsDao,
    NotesDao,
    HabitsDao,
    ShoppingDao,
    ActivityLogDao,
    CalendarDao,
    GmailDao,
    PreferencesDao,
  ],
)
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 3;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) async {
      await m.createAll();
      await _createNotesFts();
    },
    onUpgrade: (m, from, to) async {
      await runMigrations(from, to, (version) async {
        if (version == 2) {
          await m.createTable(syncPairs);
          await m.createTable(syncFiles);
          await m.createTable(syncOperations);
          await m.createTable(bridgeExecutions);
          await _createNotesFts();
        }
        if (version == 3)
          await m.addColumn(calendarEventsCache, calendarEventsCache.projectId);
      });
    },
    beforeOpen: (details) async {
      await customStatement('PRAGMA foreign_keys = ON');
      await customStatement('PRAGMA journal_mode = WAL');
      if (details.wasCreated) await _seed();
    },
  );

  Future<void> _seed() async {
    const names = ['家庭', '帳單', '居家', '健康', '採買', '行政'];
    await batch((batch) {
      for (var i = 0; i < names.length; i++) {
        batch.insert(
          tags,
          TagsCompanion.insert(id: 'tag_$i', name: names[i]),
          mode: InsertMode.insertOrIgnore,
        );
      }
      batch.insert(
        templates,
        TemplatesCompanion.insert(
          id: 'template_weekly',
          name: '每週整理',
          templateType: 'task',
          payloadJson: '{"title":"每週整理","checklist":["清空收件匣","安排下週","回顧等待中"]}',
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        ),
        mode: InsertMode.insertOrIgnore,
      );
      batch.insert(
        templates,
        TemplatesCompanion.insert(
          id: 'template_trip',
          name: '旅行規劃',
          templateType: 'project',
          payloadJson: '{"name":"旅行規劃","tags":["行政"]}',
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        ),
        mode: InsertMode.insertOrIgnore,
      );
    });
  }

  Future<void> _createNotesFts() async {
    await customStatement(
      "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, body, content='notes', content_rowid='rowid')",
    );
    await customStatement(
      "CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN INSERT INTO notes_fts(rowid,title,body) VALUES(new.rowid,new.title,new.body); END",
    );
    await customStatement(
      "CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN INSERT INTO notes_fts(notes_fts,rowid,title,body) VALUES('delete',old.rowid,old.title,old.body); END",
    );
    await customStatement(
      "CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN INSERT INTO notes_fts(notes_fts,rowid,title,body) VALUES('delete',old.rowid,old.title,old.body); INSERT INTO notes_fts(rowid,title,body) VALUES(new.rowid,new.title,new.body); END",
    );
    await customStatement("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')");
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File(p.join(dir.path, 'life_assistant.db'));
    final pending = File(p.join(dir.path, 'restore_pending.db'));
    if (await pending.exists()) {
      final previous = File(p.join(dir.path, 'life_assistant.pre_restore.db'));
      if (await file.exists()) await file.copy(previous.path);
      await pending.copy(file.path);
      await pending.delete();
    }
    return NativeDatabase.createInBackground(file);
  });
}
