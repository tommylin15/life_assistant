@JS()
library;

import 'dart:js_interop';

import 'drive_api.dart';
import 'google_drive_picker_base.dart';

@JS('lifeAssistantPickDriveFiles')
external JSPromise<JSArray<JSString>> _pickDriveFiles(
  JSString clientId,
  JSString developerKey,
  JSString appId,
  JSString scope,
  JSString folderId,
  JSBoolean allowMultiple,
);

@JS('lifeAssistantPickDriveFolder')
external JSPromise<JSString> _pickDriveFolder(
  JSString clientId,
  JSString developerKey,
  JSString appId,
  JSString scope,
);

@JS('lifeAssistantOpenExternalUrl')
external void _openExternalUrl(JSString url);

GoogleDrivePicker createGoogleDrivePicker(
  Future<PickerConfig> Function() configLoader,
) =>
    _WebGoogleDrivePicker(configLoader);

class _WebGoogleDrivePicker implements GoogleDrivePicker {
  _WebGoogleDrivePicker(this._configLoader);

  final Future<PickerConfig> Function() _configLoader;

  @override
  Future<List<String>> pickFiles({
    String? folderId,
    bool allowMultiple = true,
  }) async {
    final config = await _configLoader();
    final result = await _pickDriveFiles(
      config.clientId.toJS,
      config.developerKey.toJS,
      config.appId.toJS,
      config.scope.toJS,
      (folderId ?? '').toJS,
      allowMultiple.toJS,
    ).toDart;
    return result.toDart.map((item) => item.toDart).toList(growable: false);
  }

  @override
  Future<String?> pickFolder() async {
    final config = await _configLoader();
    final result = await _pickDriveFolder(
      config.clientId.toJS,
      config.developerKey.toJS,
      config.appId.toJS,
      config.scope.toJS,
    ).toDart;
    final value = result.toDart.trim();
    return value.isEmpty ? null : value;
  }

  @override
  Future<void> openUrl(String url) async {
    _openExternalUrl(url.toJS);
  }
}
