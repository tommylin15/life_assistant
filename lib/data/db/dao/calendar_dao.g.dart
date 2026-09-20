// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'calendar_dao.dart';

// ignore_for_file: type=lint
mixin _$CalendarDaoMixin on DatabaseAccessor<AppDatabase> {
  $CalendarEventsCacheTable get calendarEventsCache =>
      attachedDatabase.calendarEventsCache;
  CalendarDaoManager get managers => CalendarDaoManager(this);
}

class CalendarDaoManager {
  final _$CalendarDaoMixin _db;
  CalendarDaoManager(this._db);
  $$CalendarEventsCacheTableTableManager get calendarEventsCache =>
      $$CalendarEventsCacheTableTableManager(
        _db.attachedDatabase,
        _db.calendarEventsCache,
      );
}
