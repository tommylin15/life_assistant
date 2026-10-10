import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'auth_state.dart';

// Invalidates account-owned caches on sign-out, sign-in and account change.
final sessionIdentityProvider = Provider<String?>((ref) {
  final user = ref.watch(authProvider).asData?.value;
  return user == null ? null : (user['email'] ?? '');
});
