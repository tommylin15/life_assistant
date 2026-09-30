import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'drive_api.dart';
import 'google_drive_picker.dart';

class DriveSettingsPage extends ConsumerStatefulWidget {
  const DriveSettingsPage({super.key});

  @override
  ConsumerState<DriveSettingsPage> createState() => _DriveSettingsPageState();
}

class _DriveSettingsPageState extends ConsumerState<DriveSettingsPage> {
  List<DriveWorkspace> _workspaces = const [];
  DriveAiSettings _settings = const DriveAiSettings();
  bool _loading = true;
  bool _busy = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_load);
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(driveApiProvider);
      final results = await Future.wait([
        api.getWorkspaces(),
        api.getAiSettings(),
      ]);
      if (!mounted) return;
      setState(() {
        _workspaces = results[0] as List<DriveWorkspace>;
        _settings = results[1] as DriveAiSettings;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        _loading = false;
      });
    }
  }

  Future<void> _addWorkspace() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final folderId = await ref.read(googleDrivePickerProvider).pickFolder();
      if (folderId == null || folderId.isEmpty) return;
      await ref.read(driveApiProvider).createWorkspace(folderId);
      await _load();
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _updateWorkspace(
    DriveWorkspace workspace,
    Map<String, dynamic> body,
  ) async {
    try {
      await ref.read(driveApiProvider).updateWorkspace(workspace.id, body);
      await _load();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _deleteWorkspace(DriveWorkspace workspace) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('移除 Drive 工作區？'),
        content: Text(
          '只會解除 life_assistant 的「${workspace.name}」工作區設定，不會刪除 Google Drive 資料夾或任何原始檔案。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('移除'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await ref.read(driveApiProvider).deleteWorkspace(workspace.id);
      await _load();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _updateAi(Map<String, dynamic> body) async {
    try {
      final updated = await ref.read(driveApiProvider).updateAiSettings(body);
      if (!mounted) return;
      setState(() => _settings = updated);
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Drive 設定失敗：$error')),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Google Drive 設定')),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _errorView()
                : Align(
                    alignment: Alignment.topCenter,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 900),
                      child: ListView(
                        padding: const EdgeInsets.fromLTRB(16, 16, 16, 80),
                        children: [
                          _workspaceSection(),
                          const SizedBox(height: 16),
                          _aiSection(),
                        ],
                      ),
                    ),
                  ),
      );

  Widget _errorView() => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('無法讀取 Drive 設定：$_error'),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('重試')),
            ],
          ),
        ),
      );

  Widget _workspaceSection() => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Drive 工作區',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: _busy ? null : _addWorkspace,
                    icon: const Icon(Icons.create_new_folder_outlined),
                    label: const Text('新增工作區'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                '工作區只是 life_assistant 的整理入口。選取資料夾不會自動取得資料夾內所有檔案，也不會遞迴掃描；文件仍需由你透過 Google Picker 明確選入。',
              ),
              const SizedBox(height: 12),
              if (_workspaces.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('尚未設定 Drive 工作區'),
                )
              else
                for (final workspace in _workspaces)
                  _workspaceTile(workspace),
            ],
          ),
        ),
      );

  Widget _workspaceTile(DriveWorkspace workspace) => Column(
        children: [
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              workspace.isDefault ? Icons.folder_special : Icons.folder_outlined,
            ),
            title: Text(workspace.name),
            subtitle: Text(
              workspace.isDefault ? '預設工作區' : 'Google Drive 資料夾',
            ),
            trailing: Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                IconButton(
                  key: ValueKey('drive-workspace-default-${workspace.id}'),
                  tooltip: workspace.isDefault ? '目前為預設' : '設為預設',
                  onPressed: workspace.isDefault
                      ? null
                      : () => _updateWorkspace(
                            workspace,
                            {'is_default': true},
                          ),
                  icon: Icon(
                    workspace.isDefault ? Icons.star : Icons.star_border,
                  ),
                ),
                IconButton(
                  tooltip: '移除工作區',
                  onPressed: () => _deleteWorkspace(workspace),
                  icon: const Icon(Icons.link_off_outlined),
                ),
              ],
            ),
          ),
          SwitchListTile(
            key: ValueKey('drive-workspace-enabled-${workspace.id}'),
            contentPadding: EdgeInsets.zero,
            title: const Text('啟用此工作區'),
            value: workspace.isEnabled,
            onChanged: (value) => _updateWorkspace(
              workspace,
              {'is_enabled': value},
            ),
          ),
          const Divider(),
        ],
      );

  Widget _aiSection() => Card(
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 8, 4),
                child: Text(
                  '智能整理',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              SwitchListTile(
                title: const Text('自動智能 Tag'),
                subtitle: const Text('文件加入專案時自動整理可修改的標籤'),
                value: _settings.autoTags,
                onChanged: (value) => _updateAi({'auto_tags': value}),
              ),
              SwitchListTile(
                title: const Text('建議相關 Notes'),
                subtitle: const Text('只提出建議；第一版不會自動建立雙鏈'),
                value: _settings.suggestRelatedNotes,
                onChanged: (value) =>
                    _updateAi({'suggest_related_notes': value}),
              ),
              SwitchListTile(
                title: const Text('允許將文件內容送交 AI 分析'),
                subtitle: const Text('預設關閉；關閉時仍可手動 Tag、關聯與開啟文件'),
                value: _settings.allowContentAnalysis,
                onChanged: (value) =>
                    _updateAi({'allow_content_analysis': value}),
              ),
              ListTile(
                title: const Text('相關 Notes 建議數量'),
                subtitle: Text('最多 ${_settings.maxRelatedNotes} 筆'),
                trailing: DropdownButton<int>(
                  value: _settings.maxRelatedNotes,
                  items: [1, 3, 5, 8, 10]
                      .map(
                        (value) => DropdownMenuItem(
                          value: value,
                          child: Text('$value'),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) {
                      _updateAi({'max_related_notes': value});
                    }
                  },
                ),
              ),
            ],
          ),
        ),
      );
}
