import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../app/design_system/design_system.dart';
import 'drive_api.dart';
import 'google_drive_picker.dart';
import 'note_api.dart';

class DrivePage extends ConsumerStatefulWidget {
  const DrivePage({super.key});

  @override
  ConsumerState<DrivePage> createState() => _DrivePageState();
}

class _DrivePageState extends ConsumerState<DrivePage> {
  bool _loading = true;
  bool _addingDocuments = false;
  Object? _loadError;
  List<Map<String, dynamic>> _documents = const [];
  Map<String, dynamic> _settings = const {};
  Map<String, String> _noteTitles = const {};
  Map<String, Map<String, dynamic>?> _enrichments = const {};
  Set<String> _enrichmentErrors = const {};
  final Set<String> _busyDocuments = <String>{};
  final Set<String> _busySuggestions = <String>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });

    final driveApi = ref.read(driveApiProvider);
    final noteApi = ref.read(noteApiProvider);

    List<Map<String, dynamic>> documents;
    try {
      documents = await driveApi.getDocuments();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _loadError = error;
      });
      return;
    }

    Map<String, dynamic> settings = const {};
    try {
      settings = await driveApi.getEnrichmentSettings();
    } catch (_) {
      // Settings availability must not hide registered Drive documents.
    }

    var noteTitles = <String, String>{};
    try {
      final notes = await noteApi.getNotes();
      noteTitles = {
        for (final note in notes)
          if ((note['id']?.toString() ?? '').isNotEmpty)
            note['id'].toString():
                (note['title']?.toString().trim().isNotEmpty ?? false)
                    ? note['title'].toString().trim()
                    : '未命名筆記',
      };
    } catch (_) {
      // Note identity is display-only. The suggestion remains actionable by ID.
    }

    final enrichments = <String, Map<String, dynamic>?>{};
    final enrichmentErrors = <String>{};
    await Future.wait(
      documents.map((document) async {
        final id = document['id']?.toString() ?? '';
        if (id.isEmpty) return;
        try {
          enrichments[id] = await driveApi.getEnrichment(id);
        } catch (_) {
          enrichmentErrors.add(id);
        }
      }),
    );

    if (!mounted) return;
    setState(() {
      _documents = documents;
      _settings = settings;
      _noteTitles = noteTitles;
      _enrichments = enrichments;
      _enrichmentErrors = enrichmentErrors;
      _loading = false;
    });
  }

  Future<void> _addDriveFiles() async {
    if (_addingDocuments) return;
    setState(() => _addingDocuments = true);
    try {
      final pickerApi = ref.read(drivePickerApiProvider);
      final config = PickerConfig.fromJson(await pickerApi.getPickerConfig());
      final googleFileIds = await ref.read(googleDrivePickerProvider).pick(
            config,
            folders: false,
            multiSelect: true,
          );
      if (googleFileIds.isEmpty) return;

      await pickerApi.registerDocuments(googleFileIds);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已加入 ${googleFileIds.length} 個 Drive 檔案。')),
      );
      await _load();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('無法加入 Drive 檔案；既有文件與智能整理結果不受影響。'),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _addingDocuments = false);
      }
    }
  }

  Future<void> _reanalyze(String documentId) async {
    if (_busyDocuments.contains(documentId)) return;
    setState(() => _busyDocuments.add(documentId));
    try {
      final run = await ref.read(driveApiProvider).runEnrichment(
            documentId,
            force: true,
          );
      if (!mounted) return;
      setState(() {
        _enrichments = {..._enrichments, documentId: run};
        _enrichmentErrors = {..._enrichmentErrors}..remove(documentId);
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _enrichmentErrors = {..._enrichmentErrors, documentId};
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('重新分析失敗；文件本身仍可正常使用。')),
      );
    } finally {
      if (mounted) {
        setState(() => _busyDocuments.remove(documentId));
      }
    }
  }

  Future<void> _decide(
    String documentId,
    String suggestionId,
    String decision,
  ) async {
    if (_busySuggestions.contains(suggestionId)) return;
    setState(() => _busySuggestions.add(suggestionId));
    try {
      final updated = await ref
          .read(driveApiProvider)
          .decideNoteSuggestion(suggestionId, decision);
      if (!mounted) return;
      final currentRun = _enrichments[documentId];
      if (currentRun != null) {
        final nextRun = Map<String, dynamic>.from(currentRun);
        final suggestions = (currentRun['note_suggestions'] as List? ?? const [])
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        final index = suggestions.indexWhere(
          (item) => item['id']?.toString() == suggestionId,
        );
        if (index >= 0) suggestions[index] = updated;
        nextRun['note_suggestions'] = suggestions;
        setState(() {
          _enrichments = {..._enrichments, documentId: nextRun};
        });
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('建議決策更新失敗，尚未變更接受／拒絕狀態。')),
      );
    } finally {
      if (mounted) {
        setState(() => _busySuggestions.remove(suggestionId));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Google Drive 智能整理'),
        actions: [
          IconButton(
            key: const ValueKey('add-drive-files'),
            tooltip: '加入 Drive 檔案',
            onPressed: _addingDocuments ? null : _addDriveFiles,
            icon: _addingDocuments
                ? const SizedBox.square(
                    dimension: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.add_to_drive),
          ),
          IconButton(
            tooltip: '智能整理設定',
            onPressed: () => context.go('/more/drive/settings'),
            icon: const Icon(Icons.tune),
          ),
        ],
      ),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_loadError != null) {
      return AppStatePanel(
        title: '無法載入 Google Drive 文件',
        message: '已註冊的文件暫時無法取得，請稍後重試。',
        icon: const Icon(Icons.cloud_off_outlined),
        action: FilledButton.icon(
          onPressed: _load,
          icon: const Icon(Icons.refresh),
          label: const Text('重試'),
        ),
      );
    }

    return SingleChildScrollView(
      child: AppPageFrame(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AppSectionCard(
              title: '智能整理',
              subtitle: '檢視標籤與相關筆記建議；AI 失敗不會回滾 Drive 或專案關聯。',
              action: TextButton.icon(
                onPressed: () => context.go('/more/drive/settings'),
                icon: const Icon(Icons.settings_outlined),
                label: const Text('智能整理設定'),
              ),
              child: const Text(
                '所有建議都沿用 provider-agnostic contract；相關筆記只有在你接受後才建立正式關聯。',
              ),
            ),
            if (_settings['allow_document_content'] == false) ...[
              const SizedBox(height: AppSpacing.lg),
              AppSectionCard(
                title: 'AI 內容分析未啟用',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '目前未允許將文件內容送交 AI 分析。Drive 文件與既有專案關聯仍可正常使用。',
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: [
                        FilledButton.tonalIcon(
                          onPressed: () => context.go('/more/drive/settings'),
                          icon: const Icon(Icons.privacy_tip_outlined),
                          label: const Text('檢查同意設定'),
                        ),
                        TextButton.icon(
                          onPressed: () => context.go('/more/notes'),
                          icon: const Icon(Icons.description_outlined),
                          label: const Text('前往筆記'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            if (_documents.isEmpty)
              AppStatePanel(
                title: '目前沒有已註冊的 Drive 文件',
                message: '只會處理你透過 Google Picker 明確選取並授權的文件，不會遞迴掃描整個雲端硬碟。',
                icon: const Icon(Icons.cloud_queue_outlined),
                action: FilledButton.icon(
                  key: const ValueKey('add-drive-files-empty'),
                  onPressed: _addingDocuments ? null : _addDriveFiles,
                  icon: const Icon(Icons.add_to_drive),
                  label: const Text('選取 Drive 檔案'),
                ),
              )
            else
              ..._documents.map((document) => Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.lg),
                    child: _buildDocumentCard(document),
                  )),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentCard(Map<String, dynamic> document) {
    final id = document['id']?.toString() ?? '';
    final run = _enrichments[id];
    final hasEnrichmentError = _enrichmentErrors.contains(id);
    final busy = _busyDocuments.contains(id);

    return AppSectionCard(
      title: document['name']?.toString() ?? '未命名 Drive 文件',
      subtitle: document['mime_type']?.toString(),
      action: IconButton(
        key: ValueKey('reanalyze-$id'),
        tooltip: '重新分析',
        onPressed: busy ? null : () => _reanalyze(id),
        icon: busy
            ? const SizedBox.square(
                dimension: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.auto_awesome_outlined),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              _statusChip(run, hasEnrichmentError: hasEnrichmentError),
              if (run?['cache_hit'] == true)
                const AppStatusChip(
                  label: '使用快取',
                  tone: AppStatusTone.info,
                  icon: Icons.cached,
                ),
            ],
          ),
          if (hasEnrichmentError) ...[
            const SizedBox(height: AppSpacing.md),
            const Text('智能整理狀態暫時無法取得；Drive 文件本身仍可正常使用。'),
          ],
          if (run != null) ...[
            ..._buildTags(run),
            ..._buildSuggestions(id, run),
            if (run['status'] == 'partial' ||
                run['status'] == 'failed' ||
                run['status'] == 'skipped') ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _fallbackMessage(run['status']?.toString()),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ],
      ),
    );
  }

  List<Widget> _buildTags(Map<String, dynamic> run) {
    final tags = (run['suggested_tags'] as List? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.isNotEmpty)
        .toList();
    if (tags.isEmpty) return const [];
    return [
      const SizedBox(height: AppSpacing.lg),
      Text('建議標籤', style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: AppSpacing.sm),
      Wrap(
        spacing: AppSpacing.sm,
        runSpacing: AppSpacing.sm,
        children: [for (final tag in tags) Chip(label: Text(tag))],
      ),
    ];
  }

  List<Widget> _buildSuggestions(
    String documentId,
    Map<String, dynamic> run,
  ) {
    final suggestions = (run['note_suggestions'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
    if (suggestions.isEmpty) return const [];
    return [
      const SizedBox(height: AppSpacing.lg),
      Text('相關筆記建議', style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: AppSpacing.sm),
      ...suggestions.map(
        (suggestion) => Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: _buildSuggestionCard(documentId, suggestion),
        ),
      ),
    ];
  }

  Widget _buildSuggestionCard(
    String documentId,
    Map<String, dynamic> suggestion,
  ) {
    final id = suggestion['id']?.toString() ?? '';
    final noteId = suggestion['note_id']?.toString() ?? '';
    final decision = suggestion['decision']?.toString() ?? 'pending';
    final title = _noteTitles[noteId] ?? '筆記 $noteId';
    final reason = suggestion['reason']?.toString() ?? '';
    final confidence = (suggestion['confidence'] as num?)?.toDouble();
    final busy = _busySuggestions.contains(id);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            if (reason.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(reason),
            ],
            if (confidence != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                '信心 ${(confidence * 100).round()}%',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: AppSpacing.sm),
            if (decision == 'pending')
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  FilledButton.tonal(
                    key: ValueKey('accept-$id'),
                    onPressed: busy
                        ? null
                        : () => _decide(documentId, id, 'accepted'),
                    child: const Text('接受'),
                  ),
                  OutlinedButton(
                    key: ValueKey('reject-$id'),
                    onPressed: busy
                        ? null
                        : () => _decide(documentId, id, 'rejected'),
                    child: const Text('拒絕'),
                  ),
                ],
              )
            else if (decision == 'accepted')
              const AppStatusChip(
                label: '已接受',
                tone: AppStatusTone.success,
                icon: Icons.check,
              )
            else
              const AppStatusChip(
                label: '已拒絕',
                tone: AppStatusTone.neutral,
                icon: Icons.close,
              ),
          ],
        ),
      ),
    );
  }

  AppStatusChip _statusChip(
    Map<String, dynamic>? run, {
    required bool hasEnrichmentError,
  }) {
    if (hasEnrichmentError) {
      return const AppStatusChip(
        label: '狀態無法取得',
        tone: AppStatusTone.warning,
        icon: Icons.warning_amber_outlined,
      );
    }
    final status = run?['status']?.toString();
    switch (status) {
      case 'succeeded':
        return const AppStatusChip(
          label: '分析完成',
          tone: AppStatusTone.success,
          icon: Icons.check_circle_outline,
        );
      case 'partial':
        return const AppStatusChip(
          label: '部分完成',
          tone: AppStatusTone.warning,
          icon: Icons.info_outline,
        );
      case 'failed':
        return const AppStatusChip(
          label: '分析失敗',
          tone: AppStatusTone.danger,
          icon: Icons.error_outline,
        );
      case 'skipped':
        return const AppStatusChip(
          label: '已略過',
          tone: AppStatusTone.neutral,
          icon: Icons.skip_next_outlined,
        );
      default:
        return const AppStatusChip(
          label: '尚未分析',
          tone: AppStatusTone.neutral,
          icon: Icons.hourglass_empty,
        );
    }
  }

  String _fallbackMessage(String? status) {
    switch (status) {
      case 'partial':
        return '部分智能整理未完成；已成功的結果仍保留，核心 Drive／專案功能不受影響。';
      case 'failed':
        return '智能整理目前失敗；可稍後重試，核心 Drive／專案功能不受影響。';
      case 'skipped':
        return '本次智能整理未執行；可檢查同意設定，或繼續使用既有手動整理方式。';
      default:
        return '';
    }
  }
}
