import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:drift/drift.dart';
import 'package:path/path.dart' as p;
import 'package:uuid/uuid.dart';

import '../application/sync_planner.dart';
import 'db/app_database.dart';

class DriveFileEntry {
  const DriveFileEntry({
    required this.id,
    required this.path,
    required this.hash,
    required this.modifiedAt,
    this.mimeType,
  });
  final String id;
  final String path;
  final String hash;
  final DateTime modifiedAt;
  final String? mimeType;
}

class DriveFolderChoice {
  const DriveFolderChoice({required this.id, required this.name});
  final String id, name;
}

abstract interface class DriveFileGateway {
  Future<List<DriveFolderChoice>> listFolders();
  Future<List<DriveFileEntry>> listFiles(String folderId);
  Future<List<int>> download(String fileId);
  Future<DriveFileEntry> upload(
    String folderId,
    String relativePath,
    List<int> bytes, {
    String? existingId,
  });
  Future<DriveFileEntry> move(
    String folderId,
    String fileId,
    String relativePath,
  );
  Future<void> delete(String fileId);
}

enum SyncConflictChoice { keepLocal, keepDrive, keepBoth }

class SyncConflict {
  const SyncConflict({
    required this.path,
    this.localModifiedAt,
    this.driveModifiedAt,
    this.localText,
    this.driveText,
  });
  final String path;
  final DateTime? localModifiedAt, driveModifiedAt;
  final String? localText, driveText;
  bool get isText => localText != null || driveText != null;
}

class SyncSummary {
  const SyncSummary({
    required this.uploaded,
    required this.downloaded,
    required this.deleted,
    required this.conflicts,
    required this.failed,
  });
  final int uploaded, downloaded, deleted, conflicts, failed;
}

class FolderSyncEngine {
  FolderSyncEngine(this.db, this.drive);
  final AppDatabase db;
  final DriveFileGateway drive;
  final _planner = const SyncPlanner();
  final _uuid = const Uuid();

  Future<String?> activePairId() async =>
      (await db.select(db.syncPairs).getSingleOrNull())?.id;
  Future<List<DriveFolderChoice>> driveFolders() => drive.listFolders();
  Future<SyncPair?> activePair() => db.select(db.syncPairs).getSingleOrNull();

  Future<void> removePair(String pairId) async {
    await db.transaction(() async {
      await (db.delete(db.syncOperations)..where((t) => t.syncPairId.equals(pairId))).go();
      await (db.delete(db.syncFiles)..where((t) => t.syncPairId.equals(pairId))).go();
      await (db.delete(db.syncPairs)..where((t) => t.id.equals(pairId))).go();
    });
    await _log(pairId);
  }

  Future<List<String>> workspaceFiles(String pairId) async {
    final pair = await (db.select(
      db.syncPairs,
    )..where((t) => t.id.equals(pairId))).getSingle();
    final root = Directory(pair.localRootUri);
    if (!await root.exists()) return [];
    final files = <String>[];
    await for (final entity in root.list(recursive: true)) {
      if (entity is File) {
        final relative = p
            .relative(entity.path, from: root.path)
            .replaceAll('\\', '/');
        if (!isExcludedSyncPath(relative) &&
            p.extension(relative).toLowerCase() == '.md')
          files.add(relative);
      }
    }
    return files..sort();
  }

  Future<String> readWorkspaceFile(String pairId, String relativePath) async =>
      (await _workspaceFile(pairId, relativePath)).readAsString();

  Future<void> saveWorkspaceFile(
    String pairId,
    String relativePath,
    String content,
  ) async {
    final file = await _workspaceFile(
      pairId,
      relativePath,
      requireMarkdown: true,
    );
    await file.parent.create(recursive: true);
    await file.writeAsString(content, flush: true);
  }

  Future<void> renameWorkspaceFile(
    String pairId,
    String from,
    String to,
  ) async {
    final source = await _workspaceFile(pairId, from);
    final target = await _workspaceFile(pairId, to, requireMarkdown: true);
    if (await target.exists()) throw StateError('FILE_ALREADY_EXISTS');
    await target.parent.create(recursive: true);
    await source.rename(target.path);
  }

  Future<void> deleteWorkspaceFile(String pairId, String relativePath) async {
    final file = await _workspaceFile(pairId, relativePath);
    if (await file.exists()) await file.delete();
  }

  Future<String> createPair(
    Directory local,
    String driveFolderId, {
    bool includeSubfolders = true,
  }) async {
    if (await activePairId() != null) throw StateError('SYNC_PAIR_ALREADY_EXISTS');
    if (!await local.exists()) await local.create(recursive: true);
    final contents = await local
        .list(recursive: true)
        .where(
          (e) =>
              e is File &&
              !isExcludedSyncPath(p.relative(e.path, from: local.path)),
        )
        .toList();
    if (contents.isNotEmpty) throw StateError('LOCAL_FOLDER_NOT_EMPTY');
    final id = _uuid.v4(), now = DateTime.now();
    await db
        .into(db.syncPairs)
        .insert(
          SyncPairsCompanion.insert(
            id: id,
            localRootUri: local.path,
            driveFolderId: driveFolderId,
            includeSubfolders: Value(includeSubfolders),
            allowedTypesJson: jsonEncode(_extensions.toList()),
            createdAt: now,
            updatedAt: now,
          ),
        );
    return id;
  }

  Future<SyncSummary> sync(String pairId) async {
    final pair = await (db.select(
      db.syncPairs,
    )..where((t) => t.id.equals(pairId))).getSingle();
    final local = Directory(pair.localRootUri);
    if (!await local.exists()) throw StateError('LOCAL_FOLDER_PERMISSION_LOST');
    return pair.initialSyncCompleted
        ? _normal(pairId, local, pair.driveFolderId)
        : _initial(pairId, local, pair.driveFolderId);
  }

  Future<SyncSummary> _initial(
    String pairId,
    Directory local,
    String folderId,
  ) async {
    final nonEmpty = await local
        .list(recursive: true)
        .where(
          (e) =>
              e is File &&
              !isExcludedSyncPath(p.relative(e.path, from: local.path)),
        )
        .any((_) => true);
    if (nonEmpty) throw StateError('LOCAL_FOLDER_NOT_EMPTY');
    final remote = await drive.listFiles(folderId);
    var downloaded = 0, failed = 0;
    for (final file in remote.where((e) => !isExcludedSyncPath(e.path))) {
      final operationId = await _startOperation(
        pairId,
        file.path,
        'initial_download',
      );
      try {
        final bytes = await drive.download(file.id);
        await _atomicWrite(File(p.join(local.path, file.path)), bytes);
        await _snapshot(pairId, file.path, file.id, file.hash, file.modifiedAt);
        await _finishOperation(operationId, 'success');
        downloaded++;
      } catch (error) {
        failed++;
        await _finishOperation(
          operationId,
          'failed',
          error.runtimeType.toString(),
        );
      }
    }
    if (failed == 0)
      await (db.update(db.syncPairs)..where((t) => t.id.equals(pairId))).write(
        SyncPairsCompanion(
          initialSyncCompleted: const Value(true),
          lastSuccessfulSyncAt: Value(DateTime.now()),
          updatedAt: Value(DateTime.now()),
        ),
      );
    await _log(pairId, downloaded: downloaded, failed: failed);
    return SyncSummary(
      uploaded: 0,
      downloaded: downloaded,
      deleted: 0,
      conflicts: 0,
      failed: failed,
    );
  }

  Future<SyncSummary> _normal(
    String pairId,
    Directory local,
    String folderId,
  ) async {
    final localFiles = <String, File>{};
    await for (final entity in local.list(recursive: true)) {
      if (entity is File) {
        final relative = p
            .relative(entity.path, from: local.path)
            .replaceAll('\\', '/');
        if (!isExcludedSyncPath(relative) &&
            _extensions.contains(p.extension(relative).toLowerCase()))
          localFiles[relative] = entity;
      }
    }
    final remote = {
      for (final e
          in await drive
              .listFiles(folderId)
              .then((items) => items.where((e) => !isExcludedSyncPath(e.path))))
        e.path: e,
    };
    final snapshots = await (db.select(
      db.syncFiles,
    )..where((t) => t.syncPairId.equals(pairId))).get();
    await _applySafeRenames(
      pairId,
      local,
      folderId,
      localFiles,
      remote,
      snapshots,
    );
    final snapshotByPath = {for (final e in snapshots) e.relativePath: e};
    final paths = {...localFiles.keys, ...remote.keys, ...snapshotByPath.keys};
    final states = <SyncFileState>[];
    for (final path in paths) {
      final localHash = localFiles[path] == null
          ? null
          : await _hash(localFiles[path]!);
      states.add(
        SyncFileState(
          path: path,
          localHash: localHash,
          driveHash: remote[path]?.hash,
          lastHash: snapshotByPath[path]?.lastSyncedHash,
          driveFileId: remote[path]?.id ?? snapshotByPath[path]?.driveFileId,
        ),
      );
    }
    var uploaded = 0, downloaded = 0, deleted = 0, conflicts = 0, failed = 0;
    for (final item in _planner.build(states)) {
      final operationId = await _startOperation(
        pairId,
        item.file.path,
        item.action.name,
      );
      try {
        final file = item.file;
        switch (item.action) {
          case SyncActionType.none:
            break;
          case SyncActionType.conflict:
            await _markConflict(
              pairId,
              item.file,
              localFiles[item.file.path],
              remote[item.file.path],
            );
            conflicts++;
          case SyncActionType.upload:
            final bytes = await localFiles[file.path]!.readAsBytes();
            final result = await drive.upload(
              folderId,
              file.path,
              bytes,
              existingId: file.driveFileId,
            );
            await _snapshot(
              pairId,
              file.path,
              result.id,
              file.localHash!,
              result.modifiedAt,
            );
            uploaded++;
          case SyncActionType.download:
            final entry = remote[file.path]!;
            await _atomicWrite(
              File(p.join(local.path, file.path)),
              await drive.download(entry.id),
            );
            await _snapshot(
              pairId,
              file.path,
              entry.id,
              entry.hash,
              entry.modifiedAt,
            );
            downloaded++;
          case SyncActionType.deleteDrive:
            await drive.delete(file.driveFileId!);
            await _removeSnapshot(pairId, file.path);
            deleted++;
          case SyncActionType.deleteLocal:
            final target = File(p.join(local.path, file.path));
            if (await target.exists()) await target.delete();
            await _removeSnapshot(pairId, file.path);
            deleted++;
        }
        await _finishOperation(operationId, 'success');
      } catch (error) {
        failed++;
        await _finishOperation(
          operationId,
          'failed',
          error.runtimeType.toString(),
        );
      }
    }
    if (failed == 0)
      await (db.update(db.syncPairs)..where((t) => t.id.equals(pairId))).write(
        SyncPairsCompanion(
          lastSuccessfulSyncAt: Value(DateTime.now()),
          updatedAt: Value(DateTime.now()),
        ),
      );
    await _log(
      pairId,
      uploaded: uploaded,
      downloaded: downloaded,
      deleted: deleted,
      conflicts: conflicts,
      failed: failed,
    );
    return SyncSummary(
      uploaded: uploaded,
      downloaded: downloaded,
      deleted: deleted,
      conflicts: conflicts,
      failed: failed,
    );
  }

  Future<List<SyncConflict>> conflicts(String pairId) async {
    final pair = await (db.select(
      db.syncPairs,
    )..where((t) => t.id.equals(pairId))).getSingle();
    final rows =
        await (db.select(db.syncFiles)..where(
              (t) =>
                  t.syncPairId.equals(pairId) & t.syncStatus.equals('conflict'),
            ))
            .get();
    final remote = {
      for (final e in await drive.listFiles(pair.driveFolderId)) e.path: e,
    };
    final result = <SyncConflict>[];
    for (final row in rows) {
      final localFile = File(p.join(pair.localRootUri, row.relativePath));
      final driveFile = remote[row.relativePath];
      String? localText, driveText;
      if (_isText(row.relativePath)) {
        if (await localFile.exists())
          localText = await localFile.readAsString();
        if (driveFile != null)
          driveText = utf8.decode(
            await drive.download(driveFile.id),
            allowMalformed: true,
          );
      }
      result.add(
        SyncConflict(
          path: row.relativePath,
          localModifiedAt: await localFile.exists()
              ? (await localFile.stat()).modified
              : null,
          driveModifiedAt: driveFile?.modifiedAt,
          localText: localText,
          driveText: driveText,
        ),
      );
    }
    return result;
  }

  Future<void> _applySafeRenames(
    String pairId,
    Directory root,
    String folderId,
    Map<String, File> localFiles,
    Map<String, DriveFileEntry> remote,
    List<SyncFile> snapshots,
  ) async {
    for (final snapshot in snapshots.where(
      (e) => e.lastSyncedHash != null && e.driveFileId != null,
    )) {
      final movedRemote = remote.values
          .where(
            (e) =>
                e.id == snapshot.driveFileId && e.path != snapshot.relativePath,
          )
          .firstOrNull;
      final oldLocal = localFiles[snapshot.relativePath];
      if (movedRemote != null &&
          oldLocal != null &&
          await _hash(oldLocal) == snapshot.lastSyncedHash &&
          !localFiles.containsKey(movedRemote.path)) {
        final target = File(p.join(root.path, movedRemote.path));
        await target.parent.create(recursive: true);
        await oldLocal.rename(target.path);
        localFiles.remove(snapshot.relativePath);
        localFiles[movedRemote.path] = target;
        await _removeSnapshot(pairId, snapshot.relativePath);
        await _snapshot(
          pairId,
          movedRemote.path,
          movedRemote.id,
          movedRemote.hash,
          movedRemote.modifiedAt,
        );
        continue;
      }
      if (oldLocal == null &&
          remote[snapshot.relativePath]?.hash == snapshot.lastSyncedHash) {
        for (final candidate in localFiles.entries.where(
          (e) =>
              !remote.containsKey(e.key) &&
              snapshots.every((s) => s.relativePath != e.key),
        )) {
          if (await _hash(candidate.value) != snapshot.lastSyncedHash) continue;
          final moved = await drive.move(
            folderId,
            snapshot.driveFileId!,
            candidate.key,
          );
          remote.remove(snapshot.relativePath);
          remote[candidate.key] = moved;
          await _removeSnapshot(pairId, snapshot.relativePath);
          await _snapshot(
            pairId,
            candidate.key,
            moved.id,
            moved.hash,
            moved.modifiedAt,
          );
          break;
        }
      }
    }
  }

  Future<void> resolveConflict(
    String pairId,
    String relativePath,
    SyncConflictChoice choice,
  ) async {
    final pair = await (db.select(
      db.syncPairs,
    )..where((t) => t.id.equals(pairId))).getSingle();
    final snapshot =
        await (db.select(db.syncFiles)..where(
              (t) =>
                  t.syncPairId.equals(pairId) &
                  t.relativePath.equals(relativePath),
            ))
            .getSingle();
    final local = File(p.join(pair.localRootUri, relativePath));
    final remote = (await drive.listFiles(pair.driveFolderId))
        .where((e) => e.path == relativePath)
        .firstOrNull;
    final operationId = await _startOperation(
      pairId,
      relativePath,
      'resolve_${choice.name}',
    );
    try {
      if (choice == SyncConflictChoice.keepDrive) {
        if (remote == null) {
          if (await local.exists()) await local.delete();
          await _removeSnapshot(pairId, relativePath);
        } else {
          await _atomicWrite(local, await drive.download(remote.id));
          await _snapshot(
            pairId,
            relativePath,
            remote.id,
            remote.hash,
            remote.modifiedAt,
          );
        }
      } else if (choice == SyncConflictChoice.keepLocal) {
        if (!await local.exists()) {
          if (remote != null) await drive.delete(remote.id);
          await _removeSnapshot(pairId, relativePath);
        } else {
          final bytes = await local.readAsBytes();
          final saved = await drive.upload(
            pair.driveFolderId,
            relativePath,
            bytes,
            existingId: remote?.id ?? snapshot.driveFileId,
          );
          await _snapshot(
            pairId,
            relativePath,
            saved.id,
            await _hash(local),
            saved.modifiedAt,
          );
        }
      } else {
        if (await local.exists() && remote != null) {
          final copyPath = await _conflictCopyPath(
            Directory(pair.localRootUri),
            relativePath,
          );
          final copy = File(p.join(pair.localRootUri, copyPath));
          final remoteBytes = await drive.download(remote.id);
          await _atomicWrite(copy, remoteBytes);
          final copied = await drive.upload(
            pair.driveFolderId,
            copyPath,
            remoteBytes,
          );
          await _snapshot(
            pairId,
            copyPath,
            copied.id,
            copied.hash,
            copied.modifiedAt,
          );
          final saved = await drive.upload(
            pair.driveFolderId,
            relativePath,
            await local.readAsBytes(),
            existingId: remote.id,
          );
          await _snapshot(
            pairId,
            relativePath,
            saved.id,
            await _hash(local),
            saved.modifiedAt,
          );
        } else {
          await resolveConflict(
            pairId,
            relativePath,
            await local.exists()
                ? SyncConflictChoice.keepLocal
                : SyncConflictChoice.keepDrive,
          );
        }
      }
      await _finishOperation(operationId, 'success');
    } catch (error) {
      await _finishOperation(
        operationId,
        'failed',
        error.runtimeType.toString(),
      );
      rethrow;
    }
  }

  Future<String> _hash(File file) async =>
      sha256.convert(await file.readAsBytes()).toString();
  Future<File> _workspaceFile(
    String pairId,
    String relativePath, {
    bool requireMarkdown = false,
  }) async {
    final normalized = p.normalize(relativePath.replaceAll('\\', '/'));
    if (p.isAbsolute(normalized) ||
        normalized == '..' ||
        normalized.startsWith('../') ||
        isExcludedSyncPath(normalized))
      throw const FormatException('INVALID_WORKSPACE_PATH');
    if (requireMarkdown && p.extension(normalized).toLowerCase() != '.md')
      throw const FormatException('MARKDOWN_REQUIRED');
    final pair = await (db.select(
      db.syncPairs,
    )..where((t) => t.id.equals(pairId))).getSingle();
    return File(p.join(pair.localRootUri, normalized));
  }

  Future<void> _atomicWrite(File target, List<int> bytes) async {
    await target.parent.create(recursive: true);
    final temp = File('${target.path}.sync-tmp');
    await temp.writeAsBytes(bytes, flush: true);
    if (await target.exists()) await target.delete();
    await temp.rename(target.path);
  }

  Future<void> _snapshot(
    String pairId,
    String path,
    String driveId,
    String hash,
    DateTime modified,
  ) async {
    final existing =
        await (db.select(db.syncFiles)..where(
              (t) => t.syncPairId.equals(pairId) & t.relativePath.equals(path),
            ))
            .getSingleOrNull();
    final values = SyncFilesCompanion(
      driveFileId: Value(driveId),
      lastSyncedHash: Value(hash),
      localHash: Value(hash),
      driveHash: Value(hash),
      driveModifiedAt: Value(modified),
      localModifiedAt: Value(DateTime.now()),
      lastSuccessfulSyncAt: Value(DateTime.now()),
      syncStatus: const Value('synced'),
    );
    if (existing == null) {
      await db
          .into(db.syncFiles)
          .insert(
            SyncFilesCompanion.insert(
              id: _uuid.v4(),
              syncPairId: pairId,
              relativePath: path,
              driveFileId: Value(driveId),
              lastSyncedHash: Value(hash),
              localHash: Value(hash),
              driveHash: Value(hash),
              driveModifiedAt: Value(modified),
              localModifiedAt: Value(DateTime.now()),
              lastSuccessfulSyncAt: Value(DateTime.now()),
            ),
          );
    } else {
      await (db.update(
        db.syncFiles,
      )..where((t) => t.id.equals(existing.id))).write(values);
    }
  }

  Future<void> _markConflict(
    String pairId,
    SyncFileState state,
    File? local,
    DriveFileEntry? remote,
  ) async {
    final existing =
        await (db.select(db.syncFiles)..where(
              (t) =>
                  t.syncPairId.equals(pairId) &
                  t.relativePath.equals(state.path),
            ))
            .getSingleOrNull();
    final values = SyncFilesCompanion(
      localHash: Value(state.localHash),
      driveHash: Value(state.driveHash),
      driveFileId: Value(state.driveFileId),
      localModifiedAt: Value(
        local == null ? null : (await local.stat()).modified,
      ),
      driveModifiedAt: Value(remote?.modifiedAt),
      syncStatus: const Value('conflict'),
    );
    if (existing == null)
      await db
          .into(db.syncFiles)
          .insert(
            SyncFilesCompanion.insert(
              id: _uuid.v4(),
              syncPairId: pairId,
              relativePath: state.path,
              driveFileId: Value(state.driveFileId),
              localHash: Value(state.localHash),
              driveHash: Value(state.driveHash),
              syncStatus: const Value('conflict'),
            ),
          );
    else
      await (db.update(
        db.syncFiles,
      )..where((t) => t.id.equals(existing.id))).write(values);
  }

  Future<String> _conflictCopyPath(Directory root, String path) async {
    final stem = p.basenameWithoutExtension(path),
        extension = p.extension(path),
        directory = p.dirname(path) == '.' ? '' : '${p.dirname(path)}/';
    final stamp = DateTime.now()
        .toIso8601String()
        .substring(0, 16)
        .replaceAll(RegExp(r'[-:T]'), '');
    var candidate = '$directory$stem (Drive Conflict $stamp)$extension',
        index = 2;
    while (await File(p.join(root.path, candidate)).exists())
      candidate = '$directory$stem (Drive Conflict $stamp $index)$extension';
    return candidate;
  }

  bool _isText(String path) =>
      const {'.md', '.txt', '.json'}.contains(p.extension(path).toLowerCase());
  Future<String> _startOperation(
    String pairId,
    String path,
    String type,
  ) async {
    final id = _uuid.v4();
    await db
        .into(db.syncOperations)
        .insert(
          SyncOperationsCompanion.insert(
            id: id,
            syncPairId: pairId,
            relativePath: path,
            operationType: type,
            status: 'running',
            startedAt: DateTime.now(),
          ),
        );
    return id;
  }

  Future<void> _finishOperation(String id, String status, [String? error]) =>
      (db.update(db.syncOperations)..where((t) => t.id.equals(id))).write(
        SyncOperationsCompanion(
          status: Value(status),
          errorCode: Value(error),
          finishedAt: Value(DateTime.now()),
        ),
      );
  Future<void> _removeSnapshot(String pairId, String path) =>
      (db.delete(db.syncFiles)..where(
            (t) => t.syncPairId.equals(pairId) & t.relativePath.equals(path),
          ))
          .go();
  Future<void> _log(
    String pairId, {
    int uploaded = 0,
    int downloaded = 0,
    int deleted = 0,
    int conflicts = 0,
    int failed = 0,
  }) => db.activityLogDao.insert(
    ActivityLogsCompanion.insert(
      id: _uuid.v4(),
      actionType: 'folder_sync',
      entityType: const Value('sync_pair'),
      entityId: Value(pairId),
      summary:
          '上傳 $uploaded、下載 $downloaded、刪除 $deleted、衝突 $conflicts、失敗 $failed',
      result: Value(failed == 0 ? 'success' : 'partial'),
      createdAt: DateTime.now(),
    ),
  );
}

const _extensions = {
  '.md',
  '.txt',
  '.json',
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
};
