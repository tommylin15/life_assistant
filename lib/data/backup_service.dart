import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqlite3/sqlite3.dart';

import 'db/app_database.dart';

class BackupService {
  const BackupService(this.db);
  final AppDatabase db;

  Future<File> backup(Directory destination) async {
    await db.customStatement('PRAGMA wal_checkpoint(FULL)');
    final appDir = await getApplicationDocumentsDirectory();
    final source = File(p.join(appDir.path, 'life_assistant.db'));
    final target = File(
      p.join(
        destination.path,
        'life_assistant_${DateTime.now().toIso8601String().replaceAll(':', '-')}.db',
      ),
    );
    await target.parent.create(recursive: true);
    return source.copy(target.path);
  }

  Future<void> stageRestore(File backup) async {
    final handle = sqlite3.open(backup.path, mode: OpenMode.readOnly);
    try {
      final version =
          handle.select('PRAGMA user_version').first.values.first as int;
      if (version < 1 || version > db.schemaVersion)
        throw const FormatException('不支援的備份 schema');
      if (handle
          .select(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='items'",
          )
          .isEmpty)
        throw const FormatException('不是生活助理備份');
    } finally {
      handle.close();
    }
    final dir = await getApplicationDocumentsDirectory();
    await backup.copy(p.join(dir.path, 'restore_pending.db'));
  }

  Future<File> exportJson(Directory destination) async {
    final tasks = await db.select(db.items).get();
    final projects = await db.select(db.projects).get();
    final notes = await db.select(db.notes).get();
    final data = {
      'schema_version': db.schemaVersion,
      'exported_at': DateTime.now().toIso8601String(),
      'tasks': tasks.map((e) => e.toJson()).toList(),
      'projects': projects.map((e) => e.toJson()).toList(),
      'notes': notes.map((e) => e.toJson()).toList(),
    };
    final file = File(p.join(destination.path, 'life_assistant_export.json'));
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(data),
      flush: true,
    );
    return file;
  }

  Future<File> exportTasksCsv(Directory destination) async {
    final tasks = await db.select(db.items).get();
    String cell(Object? value) =>
        '"${(value ?? '').toString().replaceAll('"', '""')}"';
    final rows = <String>[
      'id,title,status,priority,due_at,project_id',
      ...tasks.map(
        (e) => [
          e.id,
          e.title,
          e.status,
          e.priority,
          e.dueAt?.toIso8601String(),
          e.projectId,
        ].map(cell).join(','),
      ),
    ];
    final file = File(p.join(destination.path, 'life_assistant_tasks.csv'));
    await file.writeAsString('\uFEFF${rows.join('\r\n')}', flush: true);
    return file;
  }
}
