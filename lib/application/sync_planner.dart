enum SyncSideState { missing, unchanged, changed, newFile }

enum SyncActionType {
  none,
  upload,
  download,
  deleteLocal,
  deleteDrive,
  conflict,
}

class SyncFileState {
  const SyncFileState({
    required this.path,
    this.localHash,
    this.driveHash,
    this.lastHash,
    this.driveFileId,
  });
  final String path;
  final String? localHash;
  final String? driveHash;
  final String? lastHash;
  final String? driveFileId;
}

class SyncPlanItem {
  const SyncPlanItem(this.file, this.action);
  final SyncFileState file;
  final SyncActionType action;
}

class SyncPlanner {
  const SyncPlanner();

  List<SyncPlanItem> build(Iterable<SyncFileState> files) =>
      files.map((file) => SyncPlanItem(file, actionFor(file))).toList();

  SyncActionType actionFor(SyncFileState file) {
    final local = file.localHash, drive = file.driveHash, last = file.lastHash;
    if (last == null) {
      if (local != null && drive == null) return SyncActionType.upload;
      if (local == null && drive != null) return SyncActionType.download;
      if (local == drive) return SyncActionType.none;
      return SyncActionType.conflict;
    }
    final localChanged = local != last;
    final driveChanged = drive != last;
    if (!localChanged && !driveChanged) return SyncActionType.none;
    if (local == null && !driveChanged) return SyncActionType.deleteDrive;
    if (drive == null && !localChanged) return SyncActionType.deleteLocal;
    if (localChanged && !driveChanged) return SyncActionType.upload;
    if (!localChanged && driveChanged) return SyncActionType.download;
    if (local == drive) return SyncActionType.none;
    return SyncActionType.conflict;
  }
}

bool isExcludedSyncPath(String path) {
  final normalized = path.replaceAll('\\', '/').toLowerCase();
  final name = normalized.split('/').last;
  return normalized.startsWith('chatgpt_bridge/') ||
      normalized.contains('/chatgpt_bridge/') ||
      name.endsWith('.db') ||
      name.endsWith('.sqlite') ||
      name.endsWith('.sqlite3') ||
      name.endsWith('-wal') ||
      name.endsWith('-shm') ||
      name.endsWith('.sync-tmp');
}
