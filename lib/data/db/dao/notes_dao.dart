import 'package:drift/drift.dart';

import '../app_database.dart';

part 'notes_dao.g.dart';

@DriftAccessor(tables: [Notes, NoteLinks])
class NotesDao extends DatabaseAccessor<AppDatabase> with _$NotesDaoMixin {
  NotesDao(super.db);

  Stream<List<Note>> watchAll() =>
      (select(notes)..orderBy([(t) => OrderingTerm.desc(t.updatedAt)])).watch();

  Future<Note?> getById(String id) =>
      (select(notes)..where((t) => t.id.equals(id))).getSingleOrNull();

  Future<void> upsert(NotesCompanion entry) =>
      into(notes).insertOnConflictUpdate(entry);

  Future<void> deleteById(String id) =>
      (delete(notes)..where((t) => t.id.equals(id))).go();
}
