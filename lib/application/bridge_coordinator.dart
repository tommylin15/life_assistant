import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:googleapis/calendar/v3.dart' as calendar;

import '../data/db/app_database.dart';
import '../domain/life_repository.dart';
import '../domain/models.dart';
import '../integrations/google/google_services_adapter.dart';
import 'bridge_validator.dart';

class BridgeCoordinator {
  const BridgeCoordinator({
    required this.db,
    required this.repository,
    required this.google,
    required this.bridgeId,
  });
  final AppDatabase db;
  final LifeRepository repository;
  final GoogleServicesAdapter google;
  final String bridgeId;

  BridgeReview review(String json) =>
      BridgeValidator(bridgeId: bridgeId).validate(json);

  Future<Map<String, Object?>> execute(
    String json,
    Set<String> acceptedActionIds,
  ) async {
    final review = this.review(json), results = <Map<String, Object?>>[];
    for (final action in review.actions) {
      if (!action.valid) {
        results.add(_result(action, 'invalid', false, action.error));
        continue;
      }
      if (!acceptedActionIds.contains(action.actionId)) {
        results.add(_result(action, 'rejected', false, '使用者取消'));
        continue;
      }
      final duplicate =
          await (db.select(db.bridgeExecutions)..where(
                (t) =>
                    t.requestId.equals(review.requestId) &
                    t.actionId.equals(action.actionId),
              ))
              .getSingleOrNull();
      if (duplicate != null) {
        results.add(_result(action, 'invalid', false, 'duplicate_action'));
        continue;
      }
      try {
        final entityId = await _execute(action);
        await db
            .into(db.bridgeExecutions)
            .insert(
              BridgeExecutionsCompanion.insert(
                requestId: review.requestId,
                actionId: action.actionId,
                status: 'accepted',
                entityId: Value(entityId),
                executedAt: DateTime.now(),
              ),
            );
        results.add({
          ..._result(action, 'accepted', true, '已執行'),
          if (entityId != null) 'entity_id': entityId,
        });
      } catch (e) {
        results.add(_result(action, 'failed', false, e.toString()));
      }
    }
    return {
      'schema_version': '1.0',
      'bridge_id': bridgeId,
      'generated_at': DateTime.now().toIso8601String(),
      'source': 'app',
      'request_id': review.requestId,
      'results': results,
    };
  }

  Future<String?> _execute(BridgeActionReview action) async {
    final p = action.payload;
    switch (action.type) {
      case 'create_task':
        return repository.saveTask(
          title: p['title'] as String,
          note: p['note'] as String?,
          priority: _priority(p['priority']),
          dueAt: _date(p['due_at']),
          projectId: p['project_id'] as String?,
        );
      case 'update_task':
        final task = await repository.getTask(p['task_id'] as String);
        if (task == null) throw StateError('MISSING_ENTITY');
        final changes = (p['changes'] as Map).cast<String, Object?>();
        await repository.saveTask(
          id: task.id,
          title: changes['title'] as String? ?? task.title,
          note: changes['note'] as String? ?? task.note,
          priority: changes.containsKey('priority')
              ? _priority(changes['priority'])
              : task.priority,
          dueAt: changes.containsKey('due_at')
              ? _date(changes['due_at'])
              : task.dueAt,
          projectId: changes['project_id'] as String? ?? task.projectId,
        );
        return task.id;
      case 'complete_task':
        await repository.setTaskStatus(
          p['task_id'] as String,
          ItemStatus.completed,
        );
        return p['task_id'] as String;
      case 'create_project':
        return repository.saveProject(
          name: p['name'] as String,
          summary: p['summary'] as String?,
        );
      case 'create_note':
        return repository.saveNote(
          title: p['title'] as String? ?? '',
          body: p['body_markdown'] as String,
          projectId: p['project_id'] as String?,
        );
      case 'update_note':
        final note = await repository.getNote(p['note_id'] as String);
        if (note == null) throw StateError('MISSING_ENTITY');
        final changes = (p['changes'] as Map).cast<String, Object?>();
        await repository.saveNote(
          id: note.id,
          title: changes['title'] as String? ?? note.title,
          body: changes['body_markdown'] as String? ?? note.body,
          projectId: changes['project_id'] as String? ?? note.projectId,
        );
        return note.id;
      case 'add_shopping_item':
        await repository.addShoppingItem(
          p['list_id'] as String,
          p['name'] as String,
          category: p['category'] as String?,
        );
        return null;
      case 'create_calendar_event':
        final event = await google.saveCalendarEvent(_event(p));
        return event.id;
      case 'update_calendar_event':
        final changes = (p['changes'] as Map).cast<String, Object?>();
        final event = await google.saveCalendarEvent(
          _event(changes),
          eventId: p['google_event_id'] as String,
        );
        return event.id;
      case 'delete_calendar_event':
        await google.deleteCalendarEvent(p['google_event_id'] as String);
        return p['google_event_id'] as String;
      default:
        throw StateError('UNKNOWN_ACTION');
    }
  }

  calendar.Event _event(Map<String, Object?> p) => calendar.Event(
    summary: p['title'] as String?,
    location: p['location'] as String?,
    description: p['description'] as String?,
    start: calendar.EventDateTime(dateTime: _date(p['starts_at'])),
    end: calendar.EventDateTime(dateTime: _date(p['ends_at'])),
  );
  DateTime? _date(Object? value) =>
      value is String ? DateTime.tryParse(value) : null;
  ItemPriority _priority(Object? value) =>
      ItemPriority.values.where((e) => e.name == value).firstOrNull ??
      ItemPriority.normal;
  Map<String, Object?> _result(
    BridgeActionReview action,
    String status,
    bool executed,
    Object? message,
  ) => {
    'action_id': action.actionId,
    'status': status,
    'executed': executed,
    'message': '$message',
  };

  String encodeResult(Map<String, Object?> result) =>
      const JsonEncoder.withIndent('  ').convert(result);
}
