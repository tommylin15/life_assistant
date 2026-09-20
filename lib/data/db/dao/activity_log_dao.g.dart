// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'activity_log_dao.dart';

// ignore_for_file: type=lint
mixin _$ActivityLogDaoMixin on DatabaseAccessor<AppDatabase> {
  $ActivityLogsTable get activityLogs => attachedDatabase.activityLogs;
  ActivityLogDaoManager get managers => ActivityLogDaoManager(this);
}

class ActivityLogDaoManager {
  final _$ActivityLogDaoMixin _db;
  ActivityLogDaoManager(this._db);
  $$ActivityLogsTableTableManager get activityLogs =>
      $$ActivityLogsTableTableManager(_db.attachedDatabase, _db.activityLogs);
}
