import 'package:drift/drift.dart';

import '../app_database.dart';

part 'calendar_dao.g.dart';

@DriftAccessor(tables: [CalendarEventsCache])
class CalendarDao extends DatabaseAccessor<AppDatabase>
    with _$CalendarDaoMixin {
  CalendarDao(super.db);

  Stream<List<CalendarEventsCacheData>> watchRange(
    DateTime from,
    DateTime to,
  ) =>
      (select(calendarEventsCache)
            ..where(
              (t) =>
                  t.startsAt.isBiggerOrEqualValue(from) &
                  t.startsAt.isSmallerThanValue(to),
            )
            ..orderBy([(t) => OrderingTerm.asc(t.startsAt)]))
          .watch();

  Future<void> upsert(CalendarEventsCacheCompanion entry) =>
      into(calendarEventsCache).insertOnConflictUpdate(entry);

  Future<void> deleteByGoogleId(String googleEventId) => (delete(
    calendarEventsCache,
  )..where((t) => t.googleEventId.equals(googleEventId))).go();
}
