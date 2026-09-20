import 'package:permission_handler/permission_handler.dart';

enum PermissionKey { notification, camera, microphone, storage }

class PermissionStatus {
  const PermissionStatus({required this.key, required this.granted, required this.label});
  final PermissionKey key;
  final bool granted;
  final String label;
}

class PermissionsStatusService {
  static const _labels = {
    PermissionKey.notification: '通知',
    PermissionKey.camera: '相機',
    PermissionKey.microphone: '麥克風',
    PermissionKey.storage: '儲存空間',
  };

  static const _permissions = {
    PermissionKey.notification: Permission.notification,
    PermissionKey.camera: Permission.camera,
    PermissionKey.microphone: Permission.microphone,
    PermissionKey.storage: Permission.storage,
  };

  Future<List<PermissionStatus>> checkAll() async {
    final result = <PermissionStatus>[];
    for (final entry in _permissions.entries) {
      final status = await entry.value.status;
      result.add(PermissionStatus(
        key: entry.key,
        granted: status.isGranted,
        label: _labels[entry.key]!,
      ));
    }
    return result;
  }

  Future<bool> request(PermissionKey key) async {
    final status = await _permissions[key]!.request();
    return status.isGranted;
  }

  Future<void> openSettings() => openAppSettings();
}
