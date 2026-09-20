import 'package:drift/drift.dart';

import '../app_database.dart';

part 'habits_dao.g.dart';

@DriftAccessor(tables: [Habits, HabitLogs])
class HabitsDao extends DatabaseAccessor<AppDatabase> with _$HabitsDaoMixin {
  HabitsDao(super.db);

  Stream<List<Habit>> watchActive() =>
      (select(habits)..where((t) => t.isActive.equals(true))).watch();

  Future<void> upsert(HabitsCompanion entry) =>
      into(habits).insertOnConflictUpdate(entry);

  Future<void> logCompletion(HabitLogsCompanion entry) =>
      into(habitLogs).insertOnConflictUpdate(entry);

  Future<List<HabitLog>> getLogsForDate(DateTime date) {
    final start = DateTime(date.year, date.month, date.day);
    final end = start.add(const Duration(days: 1));
    return (select(habitLogs)..where(
          (t) =>
              t.completedAt.isBiggerOrEqualValue(start) &
              t.completedAt.isSmallerThanValue(end),
        ))
        .get();
  }
}
