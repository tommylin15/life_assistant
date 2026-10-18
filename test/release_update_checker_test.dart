import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:life_assistant/web/release_update_checker.dart';

void main() {
  final oldSha = 'a' * 40;
  final newSha = 'b' * 40;

  test('recognizes only distinct, valid pinned frontend SHA values', () {
    expect(isNewFrontendRelease(oldSha, newSha), isTrue);
    expect(isNewFrontendRelease(oldSha, oldSha), isFalse);
    expect(isNewFrontendRelease(oldSha, '<html>fallback</html>'), isFalse);
    expect(isNewFrontendRelease('', newSha), isFalse);
  });

  test('checks public Hosting release with no-cache query', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/release.txt');
      expect(request.url.queryParameters['check'], isNotEmpty);
      expect(request.headers['Cache-Control'], 'no-cache');
      return http.Response('$newSha\n', 200);
    });
    expect(await checkFrontendRelease(
      currentSha: oldSha, baseUri: Uri.parse('https://example.test/tasks'),
      client: client,
    ), isTrue);
  });

  test('never claims an update on a missing release file', () async {
    final client = MockClient((_) async => http.Response('<html>no</html>', 200));
    expect(await checkFrontendRelease(
      currentSha: oldSha, baseUri: Uri.parse('https://example.test'),
      client: client,
    ), isFalse);
  });
}
