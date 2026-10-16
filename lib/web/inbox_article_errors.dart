/// User-facing explanation for the server's stable Life Inbox error codes.
/// Raw URLs, server exception strings and model output are never shown here.
String inboxArticleErrorMessage(Object error) {
  final description = error.toString();
  if (description.contains('article_short_link_unresolved')) {
    return 'Google 分享短網址未能解析出原文。請開啟連結後複製文章的實際網址，再試一次；也可以先只存連結。';
  }
  if (description.contains('article_site_restricted') ||
      description.contains('article_not_html')) {
    return '網站不允許直接讀取，或連結並非文章。請貼上原始公開文章網址；也可以先只存連結。';
  }
  if (description.contains('article_no_body') ||
      description.contains('article_too_large')) {
    return '無法抽取足夠的文章正文，請改用原始文章網址；仍可只存連結。';
  }
  if (description.contains('article_unsafe_url') ||
      description.contains('article_invalid_url') ||
      description.contains('article_invalid_redirect')) {
    return '為保護資料安全，無法讀取這個網址；你仍可把它存成筆記連結。';
  }
  if (description.contains('article_ai_gemini_text_disabled') ||
      description.contains('article_ai_gateway_configuration_unavailable') ||
      description.contains('article_ai_service_identity_unavailable')) {
    return '文章已讀取，但 Gemini 服務尚未正確啟用或授權。請通知管理員檢查服務設定；可以先只存網址。';
  }
  final aiCode = RegExp(r'article_ai_[a-z0-9_]+').firstMatch(description)?.group(0);
  if (aiCode != null) {
    if (aiCode == 'article_ai_invalid_response') {
      return '文章已讀取，但 Gemini 回覆格式無法解析（$aiCode）。原網址保留，可稍後再試。';
    }
    if (aiCode == 'article_ai_gateway_busy' ||
        aiCode == 'article_ai_gateway_upstream_unavailable') {
      return '文章已讀取，但 Gemini 服務忙碌或暫時無法回應（$aiCode）。請稍後再試。';
    }
    if (aiCode == 'article_ai_gateway_timeout') {
      return '文章已讀取，但 Gemini 等待逾時（$aiCode）。原網址仍保留。';
    }
    return '文章已讀取，但 Gemini 摘要未成功（$aiCode）。可先只存網址，請把此錯誤碼提供管理員。';
  }
  if (description.contains('article_dns_unavailable') ||
      description.contains('article_fetch_unavailable') ||
      description.contains('article_site_unavailable')) {
    return '文章網站暫時無法連線，建議使用原始文章網址或稍後再試；也可以先只存網址。';
  }
  if (description.contains('API 401') || description.contains('API 403')) {
    return '目前登入或功能權限無法使用文章摘要。請重新登入或請管理員檢查開放設定。';
  }
  return '文章摘要目前無法完成，原網址仍保留，可先儲存為筆記。';
}
