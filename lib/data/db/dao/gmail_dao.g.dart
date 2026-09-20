// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'gmail_dao.dart';

// ignore_for_file: type=lint
mixin _$GmailDaoMixin on DatabaseAccessor<AppDatabase> {
  $GmailRefsTable get gmailRefs => attachedDatabase.gmailRefs;
  GmailDaoManager get managers => GmailDaoManager(this);
}

class GmailDaoManager {
  final _$GmailDaoMixin _db;
  GmailDaoManager(this._db);
  $$GmailRefsTableTableManager get gmailRefs =>
      $$GmailRefsTableTableManager(_db.attachedDatabase, _db.gmailRefs);
}
