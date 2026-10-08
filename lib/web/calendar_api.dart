import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

/// Keep Google credentials and requests behind the existing FastAPI boundary.
/// The facade also allows UI tests to use an in-memory calendar.
abstract class CalendarApi {
  Future<Map<String, dynamic>> status();
  Future<List<Map<String, dynamic>>> events(DateTime from, DateTime until);
  Future<Map<String, dynamic>> create(Map<String, dynamic> body);
  Future<Map<String, dynamic>> update(String id, Map<String, dynamic> body);
  Future<void> deleteConfirmed(String id);
  String authorizationUrl();
}

class HttpCalendarApi implements CalendarApi {
  HttpCalendarApi(this.client);
  final ApiClient client;

  @override
  Future<Map<String, dynamic>> status() =>
      client.getGoogleIntegrationStatus();

  @override
  Future<List<Map<String, dynamic>>> events(DateTime from, DateTime until) async {
    final result = await client.getCalendarEvents(
      timeMin: from,
      timeMax: until,
      limit: 250,
    );
    return (result['events'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>();
  }

  @override
  Future<Map<String, dynamic>> create(Map<String, dynamic> body) =>
      client.createCalendarEvent(body);

  @override
  Future<Map<String, dynamic>> update(String id, Map<String, dynamic> body) =>
      client.updateCalendarEvent(id, body);

  @override
  Future<void> deleteConfirmed(String id) =>
      client.deleteCalendarEventConfirmed(id);

  @override
  String authorizationUrl() => client.googleAuthorizationUrl('calendar');
}

final calendarApiProvider = Provider<CalendarApi>(
  (ref) => HttpCalendarApi(ref.read(apiClientProvider)),
);
