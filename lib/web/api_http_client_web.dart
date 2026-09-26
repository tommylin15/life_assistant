import 'package:http/browser_client.dart';

BrowserClient createApiHttpClient() => BrowserClient()..withCredentials = true;
