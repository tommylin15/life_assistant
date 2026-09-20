import 'dart:convert';

import 'package:drift/drift.dart';

import 'package:uuid/uuid.dart';

import '../application/bridge_coordinator.dart';
import '../application/bridge_validator.dart';
import '../domain/life_repository.dart';
import '../integrations/google/google_services_adapter.dart';
import 'db/app_database.dart';

class BridgeService {
  BridgeService(this.db, this.repository, this.google);
  final AppDatabase db;
  final LifeRepository repository;
  final GoogleServicesAdapter google;

  Future<String> bridgeId() async {
    final existing = await db.preferencesDao.getBridgeState('bridge_id');
    if (existing != null) return existing;
    final value = 'PA-${const Uuid().v4().substring(0, 4).toUpperCase()}';
    await db.preferencesDao.setBridgeState('bridge_id', value);
    return value;
  }

  Future<String> setupDrive() async {
    final root = await google.ensureFolder('生活助理');
    final folder = await google.ensureFolder('ChatGPT_Bridge', parentId: root);
    final id = await bridgeId();
    await db.preferencesDao.setBridgeState('drive_folder_id', folder);
    await google.writeJson(folder, 'bridge_manifest.json', {
      'schema_version': '1.0',
      'bridge_id': id,
      'generated_at': DateTime.now().toIso8601String(),
      'source': 'app',
      'app': {
        'name': 'Life Assistant',
        'app_version': '0.1.0',
        'platform': 'mobile',
      },
      'capabilities': supportedBridgeActions.toList(),
      'files': {
        'current_state': 'current_state.json',
        'inbox': 'inbox.json',
        'projects': 'projects.json',
        'pending_actions': 'pending_actions.json',
        'action_results': 'action_results.json',
      },
    });
    await google.writeText(
      folder,
      'README.md',
      '# Life Assistant Bridge\n\n先讀取 bridge_manifest.json，僅將建議動作寫入 pending_actions.json；所有動作需等待 action_results.json 才算完成。',
    );
    return folder;
  }

  Future<void> exportState() async {
    final folder = await _folder(), id = await bridgeId();
    final tasks = await db.select(db.items).get(),
        projects = await db.select(db.projects).get(),
        events = await db.select(db.calendarEventsCache).get(),
        habits = await db.select(db.habits).get(),
        shoppingLists = await db.select(db.shoppingLists).get(),
        shoppingItems = await db.select(db.shoppingItems).get(),
        activity =
            await (db.select(db.activityLogs)
                  ..orderBy([(t) => OrderingTerm.desc(t.createdAt)])
                  ..limit(20))
                .get(),
        gmail = await db.select(db.gmailRefs).get();
    final now = DateTime.now();
    final open = tasks
            .where(
              (e) =>
                  e.deletedAt == null &&
                  e.status != 'completed' &&
                  e.status != 'cancelled',
            )
            .toList(),
        today = DateTime(now.year, now.month, now.day),
        tomorrow = today.add(const Duration(days: 1));
    Map<String, Object?> envelope() => {
      'schema_version': '1.0',
      'bridge_id': id,
      'generated_at': now.toIso8601String(),
      'source': 'app',
    };
    await google.writeJson(folder, 'current_state.json', {
      ...envelope(),
      'context': {
        'timezone': now.timeZoneName,
        'local_date': now.toIso8601String().substring(0, 10),
      },
      'summary': {
        'open_tasks': open.length,
        'due_today': open
            .where(
              (e) =>
                  e.dueAt != null &&
                  !e.dueAt!.isBefore(today) &&
                  e.dueAt!.isBefore(tomorrow),
            )
            .length,
        'overdue': open.where((e) => e.dueAt?.isBefore(today) ?? false).length,
        'waiting': open.where((e) => e.status == 'waiting').length,
        'today_events': events
            .where(
              (e) =>
                  !e.startsAt.isBefore(today) && e.startsAt.isBefore(tomorrow),
            )
            .length,
      },
      'tasks': open.map((e) => e.toJson()).toList(),
      'calendar': events.map((e) => e.toJson()).toList(),
      'habits': habits.map((e) => e.toJson()).toList(),
      'shopping': shoppingLists
          .map(
            (list) => {
              ...list.toJson(),
              'items': shoppingItems
                  .where((item) => item.listId == list.id)
                  .map((e) => e.toJson())
                  .toList(),
            },
          )
          .toList(),
      'recent_activity': activity
          .map(
            (e) => {
              'summary': e.summary,
              'result': e.result,
              'created_at': e.createdAt.toIso8601String(),
            },
          )
          .toList(),
    });
    await google.writeJson(folder, 'inbox.json', {
      ...envelope(),
      'items': gmail
          .map(
            (e) => {
              'id': e.id,
              'type': 'gmail',
              'subject': e.subject,
              'sender': e.sender,
              'received_at': e.receivedAt.toIso8601String(),
              'snippet': e.snippet,
              'suggested_project_id': e.linkedEntityId,
              'available_actions': [
                'create_task',
                'create_calendar_event',
                'ignore',
              ],
            },
          )
          .toList(),
    });
    await google.writeJson(folder, 'projects.json', {
      ...envelope(),
      'projects': projects
          .map(
            (project) => {
              'id': project.id,
              'name': project.name,
              'status': project.status,
              'summary': project.summary,
              'open_task_ids': open
                  .where((e) => e.projectId == project.id)
                  .map((e) => e.id)
                  .toList(),
              'note_ids': <String>[],
              'attachment_count': 0,
            },
          )
          .toList(),
    });
  }

  Future<bool> verifyDriveManifest() async {
    final text = await google.readText(await _folder(), 'bridge_manifest.json');
    if (text == null) return false;
    final value = jsonDecode(text);
    return value is Map &&
        value['schema_version'] == '1.0' &&
        value['bridge_id'] == await bridgeId();
  }

  Future<String> testInstruction() async =>
      '請讀取 Google Drive「生活助理/ChatGPT_Bridge/bridge_manifest.json」，回覆 bridge_id ${await bridgeId()} 與 schema_version 1.0；不要直接修改其他檔案。';

  Future<BridgeReview?> readPending() async {
    final json = await google.readText(await _folder(), 'pending_actions.json');
    return json == null
        ? null
        : BridgeValidator(bridgeId: await bridgeId()).validate(json);
  }

  Future<Map<String, Object?>> executePending(Set<String> accepted) async {
    final folder = await _folder(),
        source = await google.readText(folder, 'pending_actions.json');
    if (source == null) throw StateError('NO_PENDING_ACTIONS');
    final result = await BridgeCoordinator(
      db: db,
      repository: repository,
      google: google,
      bridgeId: await bridgeId(),
    ).execute(source, accepted);
    await google.writeJson(folder, 'action_results.json', result);
    return result;
  }

  Future<String> shareJson() async {
    final tasks = await db.select(db.items).get(),
        projects = await db.select(db.projects).get();
    return const JsonEncoder.withIndent('  ').convert({
      'schema_version': '1.0',
      'generated_at': DateTime.now().toIso8601String(),
      'tasks': tasks
          .where((e) => e.deletedAt == null)
          .map((e) => e.toJson())
          .toList(),
      'projects': projects.map((e) => e.toJson()).toList(),
    });
  }

  Future<String> _folder() async =>
      await db.preferencesDao.getBridgeState('drive_folder_id') ??
      await setupDrive();
}
