// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'notes_dao.dart';

// ignore_for_file: type=lint
mixin _$NotesDaoMixin on DatabaseAccessor<AppDatabase> {
  $NotesTable get notes => attachedDatabase.notes;
  $NoteLinksTable get noteLinks => attachedDatabase.noteLinks;
  NotesDaoManager get managers => NotesDaoManager(this);
}

class NotesDaoManager {
  final _$NotesDaoMixin _db;
  NotesDaoManager(this._db);
  $$NotesTableTableManager get notes =>
      $$NotesTableTableManager(_db.attachedDatabase, _db.notes);
  $$NoteLinksTableTableManager get noteLinks =>
      $$NoteLinksTableTableManager(_db.attachedDatabase, _db.noteLinks);
}
