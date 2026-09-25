import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'acceptance_runner.dart';
import 'api_client.dart';

typedef RunAcceptance = Future<AcceptanceRunResult> Function();
typedef RetryAcceptanceCleanup = Future<AcceptanceArtifacts> Function(
  AcceptanceArtifacts artifacts,
);

extension AcceptanceRunnerCleanup on AcceptanceRunner {
  Future<AcceptanceArtifacts> retryCleanup(
    AcceptanceArtifacts artifacts,
  ) async {
    final remaining = artifacts.copy();

    for (final id in remaining.taskIds.toList()) {
      try {
        await api.deleteTask(id);
        remaining.taskIds.remove(id);
      } catch (_) {
        // Keep the id so the UI can report that cleanup is still incomplete.
      }
    }
    for (final id in remaining.projectIds.toList()) {
      try {
        await api.deleteProject(id);
        remaining.projectIds.remove(id);
      } catch (_) {
        // Keep the id so the UI can report that cleanup is still incomplete.
      }
    }
    for (final id in remaining.calendarEventIds.toList()) {
      try {
        await api.deleteCalendarEvent(id);
        remaining.calendarEventIds.remove(id);
      } catch (_) {
        // Keep the id so the UI can report that cleanup is still incomplete.
      }
    }

    return remaining;
  }
}

class AcceptanceCenterPage extends ConsumerStatefulWidget {
  const AcceptanceCenterPage({
    super.key,
    this.runAcceptance,
    this.retryCleanup,
  });

  final RunAcceptance? runAcceptance;
  final RetryAcceptanceCleanup? retryCleanup;

  @override
  ConsumerState<AcceptanceCenterPage> createState() =>
      _AcceptanceCenterPageState();
}

class _AcceptanceCenterPageState extends ConsumerState<AcceptanceCenterPage> {
  bool _running = false;
  bool _cleaning = false;
  AcceptanceRunResult? _result;
  String? _error;

  AcceptanceRunner get _runner =>
      AcceptanceRunner(ref.read(apiClientProvider));

  Future<void> _run() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('確認執行驗收？'),
        content: const Text(
          '這會在你的真實帳號建立、修改並刪除 [ACCEPTANCE TEST] Project 與 Calendar event，'
          '並讀取一封 Gmail metadata 後建立測試 Task / Project / Calendar。'
          '流程結束會自動清理測試資料；Activity Log 會保留作為驗收證據。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('確認執行'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() {
      _running = true;
      _error = null;
      _result = null;
    });

    try {
      final result = await (widget.runAcceptance?.call() ?? _runner.runAll());
      if (!mounted) return;
      setState(() => _result = result);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = '驗收流程無法完成：$error');
    } finally {
      if (mounted) {
        setState(() => _running = false);
      }
    }
  }

  Future<void> _retryCleanup() async {
    final current = _result;
    if (current == null || current.remainingArtifacts.isEmpty) return;

    setState(() {
      _cleaning = true;
      _error = null;
    });

    try {
      final remaining = await (widget.retryCleanup?.call(
            current.remainingArtifacts,
          ) ??
          _runner.retryCleanup(current.remainingArtifacts));
      if (!mounted) return;
      setState(() {
        _result = AcceptanceRunResult(
          label: current.label,
          checks: current.checks,
          remainingArtifacts: remaining,
        );
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = '重試清理失敗：$error');
    } finally {
      if (mounted) {
        setState(() => _cleaning = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('驗收中心'),
        leading: IconButton(
          tooltip: '返回 Google 整合',
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/integrations'),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Phase 1 真實驗收',
                    style: theme.textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '一鍵驗證 Project CRUD、Calendar CRUD、Gmail → Task / Project / Calendar，'
                    '最後用 Activity Log 核對 execution evidence。測試資料統一使用 '
                    '[ACCEPTANCE TEST] 前綴並在流程結束自動清除。',
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: _running || _cleaning ? null : _run,
                      icon: _running
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.play_arrow),
                      label: Text(_running ? '驗收執行中…' : '執行完整驗收'),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  _error!,
                  style: TextStyle(color: theme.colorScheme.error),
                ),
              ),
            ),
          ],
          if (result != null) ...[
            const SizedBox(height: 16),
            _SummaryCard(result: result),
            const SizedBox(height: 12),
            for (final check in result.checks) ...[
              _CheckCard(check: check),
              const SizedBox(height: 8),
            ],
            if (!result.remainingArtifacts.isEmpty) ...[
              const SizedBox(height: 4),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '仍有測試資料未清除',
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(_remainingText(result.remainingArtifacts)),
                      const SizedBox(height: 12),
                      FilledButton.tonalIcon(
                        onPressed: _cleaning ? null : _retryCleanup,
                        icon: _cleaning
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.cleaning_services_outlined),
                        label: Text(_cleaning ? '清理中…' : '重試清理'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  String _remainingText(AcceptanceArtifacts artifacts) {
    final parts = <String>[];
    if (artifacts.taskIds.isNotEmpty) {
      parts.add('Task ${artifacts.taskIds.length}');
    }
    if (artifacts.projectIds.isNotEmpty) {
      parts.add('Project ${artifacts.projectIds.length}');
    }
    if (artifacts.calendarEventIds.isNotEmpty) {
      parts.add('Calendar ${artifacts.calendarEventIds.length}');
    }
    return parts.join(' · ');
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.result});

  final AcceptanceRunResult result;

  @override
  Widget build(BuildContext context) {
    final passed = result.checks
        .where((item) => item.status == AcceptanceStatus.pass)
        .length;
    final failed = result.checks
        .where((item) => item.status == AcceptanceStatus.fail)
        .length;
    final notVerified = result.checks
        .where((item) => item.status == AcceptanceStatus.notVerified)
        .length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '本次結果',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text('通過 $passed · 失敗 $failed · 未驗證 $notVerified'),
            const SizedBox(height: 4),
            Text(
              result.label,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _CheckCard extends StatelessWidget {
  const _CheckCard({required this.check});

  final AcceptanceCheck check;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final (statusText, background, foreground, icon) = switch (check.status) {
      AcceptanceStatus.pass => (
          'PASS',
          scheme.primaryContainer,
          scheme.onPrimaryContainer,
          Icons.check_circle_outline,
        ),
      AcceptanceStatus.fail => (
          'FAIL',
          scheme.errorContainer,
          scheme.onErrorContainer,
          Icons.error_outline,
        ),
      AcceptanceStatus.notVerified => (
          'NOT VERIFIED',
          scheme.surfaceContainerHighest,
          scheme.onSurfaceVariant,
          Icons.help_outline,
        ),
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: foreground),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(check.label, style: theme.textTheme.titleSmall),
                      Chip(
                        label: Text(statusText),
                        backgroundColor: background,
                        labelStyle: TextStyle(color: foreground),
                        side: BorderSide.none,
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(check.detail),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
