import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/data/app_preferences.dart';
import 'package:life_assistant/data/db/app_database.dart';
import 'package:life_assistant/data/drift_life_repository.dart';
import 'package:life_assistant/domain/models.dart';

void main() {
  late AppDatabase db;
  late DriftLifeRepository repository;
  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    repository = DriftLifeRepository(db);
  });
  tearDown(() => db.close());

  test('repository persists core entities, search and activity', () async {
    final projectId = await repository.saveProject(name: '居家整理');
    final taskId = await repository.saveTask(
      title: '整理書桌',
      projectId: projectId,
      priority: ItemPriority.high,
    );
    await repository.addChecklist(taskId, '清空抽屜');
    await repository.saveNote(
      title: '整理方法',
      body: '先分類再收納',
      projectId: projectId,
    );
    expect((await repository.watchTasks().first).single.projectId, projectId);
    expect(
      (await repository.watchChecklist(taskId).first).single.title,
      '清空抽屜',
    );
    expect((await repository.search('整理')).length, greaterThanOrEqualTo(3));
    expect(await repository.watchActivity().first, isNotEmpty);
  });

  test('preferences round-trip and current schema exists', () async {
    final preferences = AppPreferences(db);
    await preferences.setString('theme', 'warm');
    expect(await preferences.getString('theme'), 'warm');
    final version = await db.customSelect('PRAGMA user_version').getSingle();
    expect(version.data.values.single, 3);
    final columns = await db
        .customSelect('PRAGMA table_info(calendar_events_cache)')
        .get();
    expect(
      columns.any((row) => row.read<String>('name') == 'project_id'),
      isTrue,
    );
  });
}
