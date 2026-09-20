import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/db/app_database.dart';
import '../data/drift_life_repository.dart';
import '../data/attachment_service.dart';
import '../data/backup_service.dart';
import '../data/bridge_service.dart';
import '../data/app_preferences.dart';
import '../data/folder_sync_engine.dart';
import '../domain/life_repository.dart';
import '../domain/models.dart';
import '../application/app_lock.dart';
import '../application/quick_input.dart';
import '../application/google_integration_service.dart';
import '../integrations/google/google_services_adapter.dart';
import '../integrations/notifications/notification_adapter.dart';
import '../integrations/speech/speech_adapter.dart';

final databaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});
final lifeRepositoryProvider = Provider<LifeRepository>(
  (ref) => DriftLifeRepository(ref.watch(databaseProvider)),
);
final tasksProvider = StreamProvider<List<TaskItem>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchTasks(),
);
final projectsProvider = StreamProvider<List<LifeProject>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchProjects(),
);
final notesProvider = StreamProvider<List<LifeNote>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchNotes(),
);
final habitsProvider = StreamProvider<List<LifeHabit>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchHabits(),
);
final shoppingProvider = StreamProvider<List<LifeShoppingList>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchShopping(),
);
final activityProvider = StreamProvider<List<LifeActivity>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchActivity(),
);
final templatesProvider = StreamProvider<List<LifeTemplate>>(
  (ref) => ref.watch(lifeRepositoryProvider).watchTemplates(),
);

enum AppThemeChoice { system, warm, clean, dark }

final themeModeProvider = StateProvider<AppThemeChoice>(
  (ref) => AppThemeChoice.system,
);
final googleProvider = Provider((ref) => GoogleServicesAdapter());
final driveGatewayProvider = Provider<DriveFileGateway>(
  (ref) => GoogleDriveFileGateway(ref.watch(googleProvider)),
);
final folderSyncProvider = Provider(
  (ref) => FolderSyncEngine(
    ref.watch(databaseProvider),
    ref.watch(driveGatewayProvider),
  ),
);
final backupProvider = Provider(
  (ref) => BackupService(ref.watch(databaseProvider)),
);
final attachmentServiceProvider = Provider((ref) => AttachmentService());
final appLockProvider = Provider((ref) => AppLockService());
final notificationProvider = Provider((ref) => NotificationAdapter());
final speechProvider = Provider((ref) => SpeechAdapter());
final quickInputProvider = Provider((ref) => const QuickInputParser());
final bridgeServiceProvider = Provider(
  (ref) => BridgeService(
    ref.watch(databaseProvider),
    ref.watch(lifeRepositoryProvider),
    ref.watch(googleProvider),
  ),
);
final appPreferencesProvider = Provider(
  (ref) => AppPreferences(ref.watch(databaseProvider)),
);
final googleIntegrationProvider = Provider(
  (ref) => GoogleIntegrationService(
    ref.watch(databaseProvider),
    ref.watch(googleProvider),
    ref.watch(lifeRepositoryProvider),
  ),
);
final checklistProvider = StreamProvider.family<List<ChecklistEntry>, String>(
  (ref, id) => ref.watch(lifeRepositoryProvider).watchChecklist(id),
);
final taskTagsProvider = StreamProvider.family<List<LifeTag>, String>(
  (ref, id) => ref.watch(lifeRepositoryProvider).watchTags('task', id),
);
final taskAttachmentsProvider =
    StreamProvider.family<List<LifeAttachment>, String>(
      (ref, id) =>
          ref.watch(lifeRepositoryProvider).watchAttachments('task', id),
    );
final noteTagsProvider = StreamProvider.family<List<LifeTag>, String>(
  (ref, id) => ref.watch(lifeRepositoryProvider).watchTags('note', id),
);
final noteAttachmentsProvider =
    StreamProvider.family<List<LifeAttachment>, String>(
      (ref, id) =>
          ref.watch(lifeRepositoryProvider).watchAttachments('note', id),
    );
final linkedNotesProvider = StreamProvider.family<List<LifeNote>, String>(
  (ref, id) => ref.watch(lifeRepositoryProvider).watchLinkedNotes(id),
);
final habitHistoryProvider =
    StreamProvider.family<List<HabitCompletion>, String>(
      (ref, id) => ref.watch(lifeRepositoryProvider).watchHabitHistory(id),
    );
const defaultDashboardSections = [
  'tasks',
  'calendar',
  'reminders',
  'waiting',
  'shopping',
  'habits',
  'projects',
];
const defaultQuickActions = [
  'task',
  'event',
  'shopping',
  'voice',
  'note',
  'project',
];
final dashboardSectionsProvider = FutureProvider(
  (ref) => ref
      .watch(appPreferencesProvider)
      .getList('dashboard_sections', defaultDashboardSections),
);
final quickActionsProvider = FutureProvider(
  (ref) => ref
      .watch(appPreferencesProvider)
      .getList('quick_actions', defaultQuickActions),
);
