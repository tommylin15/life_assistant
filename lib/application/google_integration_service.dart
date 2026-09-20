import 'package:drift/drift.dart';
import 'package:googleapis/calendar/v3.dart' as calendar;
import 'package:googleapis/gmail/v1.dart' as gmail;
import 'package:uuid/uuid.dart';

import '../data/db/app_database.dart';
import '../domain/life_repository.dart';
import '../domain/models.dart';
import '../integrations/google/google_services_adapter.dart';

class GoogleIntegrationService {
  GoogleIntegrationService(this.db, this.google, this.repository);
  final AppDatabase db;
  final GoogleServicesAdapter google;
  final LifeRepository repository;
  final _uuid = const Uuid();

  Stream<List<CalendarSlot>> watchCalendar(DateTime from, DateTime to) => db
      .calendarDao
      .watchRange(from, to)
      .map(
        (rows) => rows
            .map(
              (e) => CalendarSlot(
                id: e.id,
                googleEventId: e.googleEventId,
                title: e.title,
                startsAt: e.startsAt,
                endsAt: e.endsAt,
                location: e.location,
                projectId: e.projectId,
              ),
            )
            .toList(),
      );
  Future<void> syncCalendar(DateTime from, DateTime to) async {
    final events = await google.readCalendar(from, to);
    for (final e in events) {
      if (e.id == null || e.start?.dateTime == null || e.end?.dateTime == null)
        continue;
      await db.calendarDao.upsert(
        CalendarEventsCacheCompanion.insert(
          id: e.id!,
          googleEventId: e.id!,
          calendarId: 'primary',
          title: e.summary ?? '未命名行程',
          startsAt: e.start!.dateTime!.toLocal(),
          endsAt: e.end!.dateTime!.toLocal(),
          location: Value(e.location),
          description: Value(e.description),
          lastSyncedAt: DateTime.now(),
        ),
      );
    }
  }

  Future<void> createEvent(String title, DateTime start, DateTime end) async {
    await google.saveCalendarEvent(
      calendar.Event(
        summary: title,
        start: calendar.EventDateTime(dateTime: start),
        end: calendar.EventDateTime(dateTime: end),
      ),
    );
    await syncCalendar(
      start.subtract(const Duration(days: 1)),
      end.add(const Duration(days: 30)),
    );
  }

  Future<void> deleteEvent(String eventId) async {
    await google.deleteCalendarEvent(eventId);
    await db.calendarDao.deleteByGoogleId(eventId);
  }

  Stream<List<GmailSummary>> watchGmail() => db.gmailDao.watchAll().map(
    (rows) => rows
        .map(
          (e) => GmailSummary(
            id: e.id,
            messageId: e.gmailMessageId,
            subject: e.subject,
            sender: e.sender,
            receivedAt: e.receivedAt,
            snippet: e.snippet,
            linkedEntityType: e.linkedEntityType,
            linkedEntityId: e.linkedEntityId,
          ),
        )
        .toList(),
  );
  Future<void> syncGmail() async {
    final messages = await google.readGmailMetadata();
    for (final m in messages) {
      if (m.id == null) continue;
      await db.gmailDao.upsert(
        GmailRefsCompanion.insert(
          id: m.id!,
          gmailMessageId: m.id!,
          threadId: m.threadId ?? '',
          subject: _header(m, 'Subject'),
          sender: _header(m, 'From'),
          receivedAt: DateTime.fromMillisecondsSinceEpoch(
            int.tryParse(m.internalDate ?? '') ?? 0,
          ),
          snippet: Value(m.snippet),
          lastSyncedAt: DateTime.now(),
        ),
      );
    }
  }

  String _header(gmail.Message message, String name) =>
      message.payload?.headers
          ?.where((e) => e.name?.toLowerCase() == name.toLowerCase())
          .firstOrNull
          ?.value ??
      '';
  Future<void> gmailToTask(GmailSummary item) => repository
      .saveTask(
        title: item.subject.isEmpty ? '處理郵件' : item.subject,
        note: item.snippet,
      )
      .then((_) {});
  Future<void> gmailToCalendar(GmailSummary item, DateTime start) =>
      createEvent(
        item.subject.isEmpty ? '郵件行程' : item.subject,
        start,
        start.add(const Duration(hours: 1)),
      );
  Future<void> linkGmailToProject(String gmailId, String projectId) =>
      (db.update(db.gmailRefs)..where((t) => t.id.equals(gmailId))).write(
        GmailRefsCompanion(
          linkedEntityType: const Value('project'),
          linkedEntityId: Value(projectId),
        ),
      );
  Future<void> updateEvent(
    CalendarSlot item,
    String title,
    DateTime start,
    DateTime end,
  ) async {
    await google.saveCalendarEvent(
      calendar.Event(
        summary: title,
        start: calendar.EventDateTime(dateTime: start),
        end: calendar.EventDateTime(dateTime: end),
      ),
      eventId: item.googleEventId,
    );
    await syncCalendar(
      start.subtract(const Duration(days: 1)),
      end.add(const Duration(days: 30)),
    );
  }

  Future<void> linkEventToProject(String eventId, String projectId) =>
      (db.update(db.calendarEventsCache)..where((t) => t.id.equals(eventId)))
          .write(CalendarEventsCacheCompanion(projectId: Value(projectId)));
}
