import 'google_drive_picker_contract.dart';

GoogleDrivePicker createGoogleDrivePicker() => _UnsupportedGoogleDrivePicker();

class _UnsupportedGoogleDrivePicker implements GoogleDrivePicker {
  @override
  Future<List<String>> pick(
    PickerConfig config, {
    required bool folders,
    bool multiSelect = true,
  }) {
    throw UnsupportedError('Google Drive Picker is only available on web.');
  }
}
