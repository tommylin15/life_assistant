import 'package:http/http.dart' as http;

import 'release_info.dart';

final _sha40 = RegExp(r'^[a-f0-9]{40}$');

bool isNewFrontendRelease(String localSha, String? remoteSha) {
  final remote = remoteSha?.trim() ?? '';
  return _sha40.hasMatch(localSha) && _sha40.hasMatch(remote) &&
      remote != localSha;
}

/// Compare only frontend Hosting's public release.txt, not Cloud Run's SHA.
/// Never use a failed/HTML/rewrite response to claim an update is available.
Future<bool> checkFrontendRelease({
  String currentSha = lifeReleaseSha,
  Uri? baseUri,
  http.Client? client,
}) async {
  if (!_sha40.hasMatch(currentSha)) return false;
  final owned = client == null;
  final httpClient = client ?? http.Client();
  try {
    final url = (baseUri ?? Uri.base).resolve('/release.txt').replace(
      queryParameters: {'check': DateTime.now().millisecondsSinceEpoch.toString()},
    );
    final response = await httpClient.get(
      url, headers: {'Cache-Control': 'no-cache'},
    ).timeout(const Duration(seconds: 8));
    return response.statusCode == 200 &&
        isNewFrontendRelease(currentSha, response.body);
  } catch (_) {
    return false;
  } finally {
    if (owned) httpClient.close();
  }
}
