import 'package:drift/drift.dart';

import '../app_database.dart';

part 'projects_dao.g.dart';

@DriftAccessor(tables: [Projects])
class ProjectsDao extends DatabaseAccessor<AppDatabase>
    with _$ProjectsDaoMixin {
  ProjectsDao(super.db);

  Stream<List<Project>> watchAll() =>
      (select(projects)..orderBy([(t) => OrderingTerm.asc(t.name)])).watch();

  Future<Project?> getById(String id) =>
      (select(projects)..where((t) => t.id.equals(id))).getSingleOrNull();

  Future<void> upsert(ProjectsCompanion entry) =>
      into(projects).insertOnConflictUpdate(entry);

  Future<void> deleteById(String id) =>
      (delete(projects)..where((t) => t.id.equals(id))).go();
}
