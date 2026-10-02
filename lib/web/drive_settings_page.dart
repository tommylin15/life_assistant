import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/design_system/design_system.dart';
import 'drive_api.dart';

class DriveSettingsPage extends ConsumerStatefulWidget {
  const DriveSettingsPage({super.key});

  @override
  ConsumerState<DriveSettingsPage> createState() => _DriveSettingsPageState();
}

class _DriveSettingsPageState extends ConsumerState<DriveSettingsPage> {
  bool _loading = true;
  bool _saving = false;
  Object? _loadError;
  String? _saveError;
  bool _saved = false;
  bool _autoTags = true;
  bool _noteSuggestions = true;
  bool _allowDocumentContent = false;
  int _maxSuggestions = 5;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
      _saveError = null;
      _saved = false;
    });
    try {
      final settings = await ref.read(driveApiProvider).getEnrichmentSettings();
      if (!mounted) return;
      setState(() {
        _autoTags = settings['auto_tags_enabled'] as bool? ?? true;
        _noteSuggestions = settings['note_suggestions_enabled'] as bool? ?? true;
        _allowDocumentContent =
            settings['allow_document_content'] as bool? ?? false;
        _maxSuggestions =
            (settings['max_related_note_suggestions'] as num?)?.toInt() ?? 5;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _loadError = error;
      });
    }
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() {
      _saving = true;
      _saveError = null;
      _saved = false;
    });
    final body = <String, dynamic>{
      'auto_tags_enabled': _autoTags,
      'note_suggestions_enabled': _noteSuggestions,
      'allow_document_content': _allowDocumentContent,
      'max_related_note_suggestions': _maxSuggestions,
    };
    try {
      final saved = await ref
          .read(driveApiProvider)
          .updateEnrichmentSettings(body);
      if (!mounted) return;
      setState(() {
        _autoTags = saved['auto_tags_enabled'] as bool? ?? _autoTags;
        _noteSuggestions =
            saved['note_suggestions_enabled'] as bool? ?? _noteSuggestions;
        _allowDocumentContent =
            saved['allow_document_content'] as bool? ?? _allowDocumentContent;
        _maxSuggestions =
            (saved['max_related_note_suggestions'] as num?)?.toInt() ??
                _maxSuggestions;
        _saved = true;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _saveError = '設定儲存失敗：$error');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('智能整理設定')),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_loadError != null) {
      return AppStatePanel(
        title: '無法載入智能整理設定',
        message: '設定尚未變更，請重試。',
        icon: const Icon(Icons.settings_backup_restore_outlined),
        action: FilledButton.icon(
          onPressed: _load,
          icon: const Icon(Icons.refresh),
          label: const Text('重試'),
        ),
      );
    }

    return SingleChildScrollView(
      child: AppPageFrame(
        child: AppSectionCard(
          title: '智能整理設定',
          subtitle: '控制自動標籤、相關筆記建議，以及文件內容是否可送交 AI 分析。',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('自動套用建議標籤'),
                subtitle: const Text('允許智能整理把分析後的標籤套用到 Drive 文件。'),
                value: _autoTags,
                onChanged: (value) => setState(() {
                  _autoTags = value;
                  _saved = false;
                }),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('建議相關筆記'),
                subtitle: const Text('只產生候選；必須由你接受後才建立正式關聯。'),
                value: _noteSuggestions,
                onChanged: (value) => setState(() {
                  _noteSuggestions = value;
                  _saved = false;
                }),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('允許將文件內容送交 AI 分析'),
                subtitle: const Text(
                  '文件內容可能會送交目前設定的 AI 分析服務。關閉時不會傳送內容，也不會重用先前的成功分析快取。',
                ),
                value: _allowDocumentContent,
                onChanged: (value) => setState(() {
                  _allowDocumentContent = value;
                  _saved = false;
                }),
              ),
              const SizedBox(height: AppSpacing.md),
              DropdownButtonFormField<int>(
                key: const ValueKey('max-related-note-suggestions'),
                value: _maxSuggestions,
                decoration: const InputDecoration(
                  labelText: '最多顯示的相關筆記建議',
                  helperText: '後端合約限制為 1–20。',
                ),
                items: [
                  for (var value = 1; value <= 20; value++)
                    DropdownMenuItem(value: value, child: Text('$value')),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setState(() {
                    _maxSuggestions = value;
                    _saved = false;
                  });
                },
              ),
              if (_saveError != null) ...[
                const SizedBox(height: AppSpacing.md),
                Text(
                  _saveError!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              if (_saved) ...[
                const SizedBox(height: AppSpacing.md),
                const AppStatusChip(
                  label: '設定已儲存',
                  tone: AppStatusTone.success,
                  icon: Icons.check,
                ),
              ],
              const SizedBox(height: AppSpacing.lg),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  key: const ValueKey('save-drive-ai-settings'),
                  onPressed: _saving ? null : _save,
                  icon: _saving
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_outlined),
                  label: const Text('儲存設定'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
