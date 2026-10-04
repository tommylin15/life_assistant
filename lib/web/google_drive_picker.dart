import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'google_drive_picker_contract.dart';
import 'google_drive_picker_stub.dart'
    if (dart.library.js_interop) 'google_drive_picker_web.dart' as implementation;

export 'google_drive_picker_contract.dart';

final googleDrivePickerProvider = Provider<GoogleDrivePicker>(
  (_) => implementation.createGoogleDrivePicker(),
);
