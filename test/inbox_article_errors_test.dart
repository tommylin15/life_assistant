import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/web/inbox_article_errors.dart';

void main() {
  test('Gemini gateway failure shows stable diagnostic code', () {
    final message = inboxArticleErrorMessage(
      StateError('API 503: article_ai_gateway_upstream_unavailable'));
    expect(message, contains('article_ai_gateway_upstream_unavailable'));
    expect(message, contains('Gemini'));
  });

  test('Gemini output error is not confused with unavailable website', () {
    final message = inboxArticleErrorMessage(
      StateError('API 502: article_ai_invalid_response'));
    expect(message, contains('回覆格式'));
    expect(message, contains('article_ai_invalid_response'));
  });

  test('unsafe or inaccessible URLs do not leak unknown errors', () {
    final message = inboxArticleErrorMessage(
      StateError('API 422: article_unsafe_url'));
    expect(message, contains('保護資料安全'));
  });
}
