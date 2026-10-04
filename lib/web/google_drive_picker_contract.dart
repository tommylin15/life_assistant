const driveFileScope = 'https://www.googleapis.com/auth/drive.file';

class PickerConfig {
  const PickerConfig({
    required this.clientId,
    required this.developerKey,
    required this.appId,
    required this.scope,
  });

  final String clientId;
  final String developerKey;
  final String appId;
  final String scope;

  factory PickerConfig.fromJson(Map<String, dynamic> json) {
    final config = PickerConfig(
      clientId: json['client_id']?.toString().trim() ?? '',
      developerKey: json['developer_key']?.toString().trim() ?? '',
      appId: json['app_id']?.toString().trim() ?? '',
      scope: json['scope']?.toString().trim() ?? '',
    );
    if (config.clientId.isEmpty ||
        config.developerKey.isEmpty ||
        config.appId.isEmpty) {
      throw StateError('Google Drive Picker configuration is incomplete.');
    }
    if (config.scope != driveFileScope) {
      throw StateError('Google Drive Picker must use the drive.file scope.');
    }
    return config;
  }
}

abstract class GoogleDrivePicker {
  Future<List<String>> pick(
    PickerConfig config, {
    required bool folders,
    bool multiSelect = true,
  });
}
