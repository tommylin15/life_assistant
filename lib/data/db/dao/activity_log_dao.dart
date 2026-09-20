import 'package:drift/drift.dart';

import '../app_database.dart';

part 'activity_log_dao.g.dart';

@DriftAccessor(tables: [ActivityLogs])
class ActivityLogDao extends DatabaseAccessor<AppDatabase>
    with _$ActivityLogDaoMixin {
  ActivityLogDao(super.db);

  Stream<List<ActivityLog>> watchRecent({int limit = 50}) =>
      (select(activityLogs)
            ..orderBy([(t) => OrderingTerm.desc(t.createdAt)])
            ..limit(limit))
          .watch();

  Future<void> insert(ActivityLogsCompanion entry) =>
      into(activityLogs).insert(entry);
}
