import 'package:http/http.dart' as http;

import 'api_http_client_stub.dart'
    if (dart.library.html) 'api_http_client_web.dart' as platform;

http.Client createApiHttpClient() => platform.createApiHttpClient();
