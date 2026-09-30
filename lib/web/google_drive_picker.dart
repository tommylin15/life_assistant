import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'drive_api.dart';
import 'google_drive_picker_stub.dart'
    if (dart.library.js_interop) 'google_drive_picker_web.dart' as platform;

export 'google_drive_picker_base.dart';

final googleDrivePickerProvider = Provider<GoogleDrivePicker>(
  (ref) => platform.createGoogleDrivePicker(
    () => ref.read(driveApiProvider).getPickerConfig(),
  ),
);
