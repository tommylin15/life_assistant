/// Candidate-only developer affordances use exact Firebase staging hosts.
/// This is a presentation policy, NOT an authorization boundary.
class LifeUiEnvironment {
  static const stagingHost = 'life-assistant-v3-stage-tl15.web.app';

  static bool isCandidateHost(String host) {
    final normalized = host.toLowerCase();
    return normalized == stagingHost ||
        (normalized.startsWith('life-assistant-v3-stage-tl15--') &&
            normalized.endsWith('.web.app'));
  }

  static bool get isCandidate => isCandidateHost(Uri.base.host);
}

/// Production errors never reveal raw internal API details.
String lifeUserError(String label, Object error) {
  if (LifeUiEnvironment.isCandidate) {
    return label.isEmpty ? error.toString() : '$label：$error';
  }
  return label.isEmpty ? '請稍後重試。' : '$label，請稍後重試。';
}
