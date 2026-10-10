import 'package:flutter_riverpod/flutter_riverpod.dart';

// Non-web/native test targets have no browser OAuth session.
// Fail closed instead of importing http/browser_client (dart:js_interop).
final sessionIdentityProvider = Provider<String?>((ref) => null);
