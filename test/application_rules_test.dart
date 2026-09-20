import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/application/bridge_validator.dart';
import 'package:life_assistant/application/quick_input.dart';
import 'package:life_assistant/application/sync_planner.dart';
import 'package:life_assistant/domain/models.dart';

void main() {
  test('quick input parses Chinese dates, time and priority', () {
    const parser = QuickInputParser();
    final base = DateTime(2026, 9, 20, 10);
    final tomorrow = parser.parse('明天下午 3 點重要 繳電費', now: base);
    expect(tomorrow.title, '繳電費');
    expect(tomorrow.dueAt, DateTime(2026, 9, 21, 15));
    expect(tomorrow.priority, ItemPriority.high);
    expect(
      parser.parse('9/25 前繳信用卡', now: base).dueAt,
      DateTime(2026, 9, 25, 18),
    );
    expect(parser.parse('週六買濾芯', now: base).dueAt, DateTime(2026, 9, 26, 18));
  });

  test('bridge rejects mismatches and unsupported actions', () {
    const validator = BridgeValidator(bridgeId: 'PA-TEST');
    final source = jsonEncode({
      'schema_version': '1.0',
      'bridge_id': 'PA-TEST',
      'source': 'chatgpt',
      'request_id': 'req_1',
      'actions': [
        {
          'action_id': 'a1',
          'type': 'create_task',
          'requires_confirmation': true,
          'payload': {'title': '測試'},
        },
        {
          'action_id': 'a2',
          'type': 'erase_everything',
          'requires_confirmation': true,
          'payload': {},
        },
      ],
    });
    final review = validator.validate(source);
    expect(review.actions.first.valid, isTrue);
    expect(review.actions.last.error, 'UNKNOWN_ACTION');
    expect(
      () => validator.validate(source.replaceFirst('PA-TEST', 'PA-WRONG')),
      throwsFormatException,
    );
  });

  test('sync planner detects changes, deletes and conflicts', () {
    const planner = SyncPlanner();
    expect(
      planner.actionFor(
        const SyncFileState(
          path: 'a.md',
          localHash: 'b',
          driveHash: 'a',
          lastHash: 'a',
        ),
      ),
      SyncActionType.upload,
    );
    expect(
      planner.actionFor(
        const SyncFileState(
          path: 'a.md',
          localHash: null,
          driveHash: 'a',
          lastHash: 'a',
        ),
      ),
      SyncActionType.deleteDrive,
    );
    expect(
      planner.actionFor(
        const SyncFileState(
          path: 'a.md',
          localHash: 'b',
          driveHash: 'c',
          lastHash: 'a',
        ),
      ),
      SyncActionType.conflict,
    );
    expect(isExcludedSyncPath('ChatGPT_Bridge/current_state.json'), isTrue);
    expect(isExcludedSyncPath('life_assistant.db-wal'), isTrue);
  });
}
