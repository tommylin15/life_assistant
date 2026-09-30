import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import 'drive_api.dart';
import 'google_drive_picker.dart';

class DrivePage extends ConsumerStatefulWidget {
  const DrivePage({super.key});

  @override
  ConsumerState<DrivePage> createState() => _DrivePageState();
}

class _DrivePageState extends ConsumerState<DrivePage> {
  final _searchController = TextEditingController();
  List<DriveWorkspace> _workspaces = const [];
  List<DriveDocument> _documents = const [];
  String? _selectedWorkspaceId;
  bool _loading = true;
  bool _mutating = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadInitial);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  DriveWorkspace? get _selectedWorkspace {
    final id = _selectedWorkspaceId;
    if (id == null) return null;
    for (final workspace in _workspaces) {
      if (workspace.id == id) return workspace;
    }
    return null;
  }

  Future<void> _loadInitial() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(driveApiProvider);
      final workspaces = await api.getWorkspaces();
      String? selected = _selectedWorkspaceId;
      if (selected == null && workspaces.isNotEmpty) {
        final defaults = workspaces.where((item) => item.isDefault && item.isEnabled);
        selected = defaults.isNotEmpty
            ? defaults.first.id
            : workspaces.where((item) => item.isEnabled).firstOrNull?.id;
      }
      final documents = await api.getDocuments(workspaceId: selected);
      if (!mounted) return;
      setState(() {
        _workspaces = workspaces;
        _selectedWorkspaceId = selected;
        _documents = documents;
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

  Future<void> _loadDocuments() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final documents = await ref.read(driveApiProvider).getDocuments(
            q: _searchController.text,
            workspaceId: _selectedWorkspaceId,
          );
      if (!mounted) return;
      setState(() {
        _documents = documents;
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

  Future<void> _addDriveFiles() async {
    if (_mutating) return;
    setState(() => _mutating = true);
    try {
      final workspace = _selectedWorkspace;
      final ids = await ref.read(googleDrivePickerProvider).pickFiles(
            folderId: workspace?.googleFolderId,
            allowMultiple: true,
          );
      if (ids.isEmpty) return;
      await ref.read(driveApiProvider).registerDocuments(
            ids,
            workspaceId: workspace?.id,
          );
      await _loadDocuments();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已加入 ${ids.length} 份 Drive 文件')),
      );
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) setState(() => _mutating = false);
    }
  }

  Future<void> _openDocument(DriveDocument document) async {
    final link = document.webViewLink;
    if (link == null || link.isEmpty) {
      _showError('Google Drive 未提供可開啟連結');
      return;
    }
    try {
      await ref.read(googleDrivePickerProvider).openUrl(link);
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _refreshDocument(DriveDocument document) async {
    try {
      await ref.read(driveApiProvider).refreshDocument(document.id);
      await _loadDocuments();
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Drive 操作失敗：$error')),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Google Drive'),
          actions: [
            IconButton(
              tooltip: 'Drive 設定',
              onPressed: () => context.push('/more/drive/settings'),
              icon: const Icon(Icons.settings_outlined),
            ),
          ],
        ),
        body: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1040),
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: _toolbar(),
                ),
                Expanded(child: _body()),
              ],
            ),
          ),
        ),
      );

  Widget _toolbar() {
    final enabledWorkspaces = _workspaces.where((item) => item.isEnabled).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 280,
              child: TextField(
                key: const ValueKey('drive-search-field'),
                controller: _searchController,
                textInputAction: TextInputAction.search,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: '搜尋已加入的 Drive 文件',
                ),
                onSubmitted: (_) => _loadDocuments(),
              ),
            ),
            if (enabledWorkspaces.isNotEmpty)
              DropdownButton<String?>(
                value: _selectedWorkspaceId,
                hint: const Text('全部工作區'),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('全部工作區'),
                  ),
                  ...enabledWorkspaces.map(
                    (workspace) => DropdownMenuItem<String?>(
                      value: workspace.id,
                      child: Text(workspace.name),
                    ),
                  ),
                ],
                onChanged: (value) {
                  setState(() => _selectedWorkspaceId = value);
                  _loadDocuments();
                },
              ),
            FilledButton.icon(
              onPressed: _mutating ? null : _addDriveFiles,
              icon: const Icon(Icons.add_to_drive_outlined),
              label: const Text('新增 Drive 文件'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          '這裡只搜尋與管理你已透過 Google Picker 明確選入 life_assistant 的文件。',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _body() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined, size: 44),
              const SizedBox(height: 12),
              Text('無法讀取 Drive 文件：$_error', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _loadInitial, child: const Text('重試')),
            ],
          ),
        ),
      );
    }
    if (_documents.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.folder_open_outlined, size: 48),
              const SizedBox(height: 12),
              const Text(
                '目前沒有已加入的 Drive 文件',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              const Text(
                '只會顯示你透過 Google Picker 明確選取並授權的檔案；不會掃描整個 Google Drive。',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _addDriveFiles,
                icon: const Icon(Icons.add),
                label: const Text('新增 Drive 文件'),
              ),
            ],
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _loadDocuments,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
        itemCount: _documents.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, index) => _documentCard(_documents[index]),
      ),
    );
  }

  Widget _documentCard(DriveDocument document) {
    final modified = document.providerModifiedAt?.toLocal();
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 8, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(_fileIcon(document.mimeType)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        document.name,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      Text(
                        modified == null
                            ? document.mimeType
                            : '${document.mimeType} · 更新 ${DateFormat('M/d HH:mm').format(modified)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                PopupMenuButton<String>(
                  tooltip: '更多',
                  onSelected: (value) {
                    if (value == 'refresh') _refreshDocument(document);
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'refresh', child: Text('重新整理資訊')),
                  ],
                ),
              ],
            ),
            if (document.tags.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                children: [
                  for (final tag in document.tags) Chip(label: Text(tag)),
                ],
              ),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: [
                TextButton(
                  onPressed: document.webViewLink == null
                      ? null
                      : () => _openDocument(document),
                  child: const Text('開啟'),
                ),
                const TextButton(onPressed: null, child: Text('加入專案')),
                const TextButton(onPressed: null, child: Text('轉入 Notes')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

IconData _fileIcon(String mimeType) {
  if (mimeType.contains('spreadsheet')) return Icons.table_chart_outlined;
  if (mimeType.contains('presentation')) return Icons.slideshow_outlined;
  if (mimeType.contains('pdf')) return Icons.picture_as_pdf_outlined;
  return Icons.description_outlined;
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
