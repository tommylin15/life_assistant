import 'dart:js_interop';

import 'google_drive_picker_contract.dart';

@JS('lifeAssistantDrivePickerPick')
external JSPromise<JSArray<JSString>> _lifeAssistantDrivePickerPick(
  JSString clientId,
  JSString developerKey,
  JSString appId,
  JSString scope,
  JSBoolean folders,
  JSBoolean multiSelect,
);

GoogleDrivePicker createGoogleDrivePicker() => _WebGoogleDrivePicker();

class _WebGoogleDrivePicker implements GoogleDrivePicker {
  @override
  Future<List<String>> pick(
    PickerConfig config, {
    required bool folders,
    bool multiSelect = true,
  }) async {
    final values = await _lifeAssistantDrivePickerPick(
      config.clientId.toJS,
      config.developerKey.toJS,
      config.appId.toJS,
      config.scope.toJS,
      folders.toJS,
      multiSelect.toJS,
    ).toDart;
    return values.toDart
        .map((value) => value.toDart.trim())
        .where((value) => value.isNotEmpty)
        .toSet()
        .toList(growable: false);
  }
}
