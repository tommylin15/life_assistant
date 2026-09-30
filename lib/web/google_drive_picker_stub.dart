import 'drive_api.dart';
import 'google_drive_picker_base.dart';

GoogleDrivePicker createGoogleDrivePicker(
  Future<PickerConfig> Function() configLoader,
) => _UnsupportedGoogleDrivePicker();

class _UnsupportedGoogleDrivePicker implements GoogleDrivePicker {
  @override
  Future<List<String>> pickFiles({
    String? folderId,
    bool allowMultiple = true,
  }) =>
      Future.error(
        UnsupportedError('Google Drive Picker is available on Web only'),
      );

  @override
  Future<String?> pickFolder() => Future.error(
        UnsupportedError('Google Drive Picker is available on Web only'),
      );

  @override
  Future<void> openUrl(String url) => Future.error(
        UnsupportedError('External Drive links are available on Web only'),
      );
}
