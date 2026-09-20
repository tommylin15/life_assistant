import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/data/db/app_database.dart';
import 'package:life_assistant/data/folder_sync_engine.dart';
import 'package:path/path.dart' as p;

void main() {
  test(
    'initial sync, conflict and keep-local resolution preserve snapshots',
    () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      final root = await Directory.systemTemp.createTemp(
        'life_assistant_sync_',
      );
      final drive = _FakeDrive()..put('notes/a.md', '# Drive');
      final engine = FolderSyncEngine(db, drive);
      addTearDown(() async {
        await db.close();
        await root.delete(recursive: true);
      });

      final pairId = await engine.createPair(root, 'folder');
      final initial = await engine.sync(pairId);
      expect(initial.downloaded, 1);
      expect(
        await File(p.join(root.path, 'notes/a.md')).readAsString(),
        '# Drive',
      );

      await File(p.join(root.path, 'notes/a.md')).writeAsString('# Local');
      drive.put('notes/a.md', '# Remote');
      final result = await engine.sync(pairId);
      expect(result.conflicts, 1);
      expect(await engine.conflicts(pairId), hasLength(1));

      await engine.resolveConflict(
        pairId,
        'notes/a.md',
        SyncConflictChoice.keepLocal,
      );
      expect(String.fromCharCodes(drive.bytes('notes/a.md')), '# Local');
      expect(await engine.conflicts(pairId), isEmpty);
    },
  );
}

class _FakeDrive implements DriveFileGateway {
  final _files = <String, List<int>>{};
  final _ids = <String, String>{};
  int _next = 0;

  void put(String path, String value) {
    _files[path] = value.codeUnits;
    _ids.putIfAbsent(path, () => 'id_${_next++}');
  }

  List<int> bytes(String path) => _files[path]!;

  @override Future<List<DriveFolderChoice>> listFolders() async => const [DriveFolderChoice(id: 'folder', name: '測試')];

  @override
  Future<List<DriveFileEntry>> listFiles(String folderId) async =>
      _files.entries.map((e) => _entry(e.key)).toList();
  @override
  Future<List<int>> download(String fileId) async =>
      List.of(_files[_path(fileId)]!);
  @override
  Future<void> delete(String fileId) async {
    final path = _path(fileId);
    _files.remove(path);
    _ids.remove(path);
  }

  @override
  Future<DriveFileEntry> upload(
    String folderId,
    String relativePath,
    List<int> bytes, {
    String? existingId,
  }) async {
    if (existingId != null) {
      final old = _path(existingId);
      _files.remove(old);
      _ids.remove(old);
      _ids[relativePath] = existingId;
    } else {
      _ids.putIfAbsent(relativePath, () => 'id_${_next++}');
    }
    _files[relativePath] = List.of(bytes);
    return _entry(relativePath);
  }

  @override
  Future<DriveFileEntry> move(
    String folderId,
    String fileId,
    String relativePath,
  ) async {
    final old = _path(fileId), data = _files.remove(old)!;
    _ids.remove(old);
    _files[relativePath] = data;
    _ids[relativePath] = fileId;
    return _entry(relativePath);
  }

  String _path(String id) => _ids.entries.singleWhere((e) => e.value == id).key;
  DriveFileEntry _entry(String path) => DriveFileEntry(
    id: _ids[path]!,
    path: path,
    hash: sha256.convert(_files[path]!).toString(),
    modifiedAt: DateTime.now(),
  );
}
