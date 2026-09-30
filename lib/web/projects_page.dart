import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'drive_api.dart';
import 'google_drive_picker.dart';
import 'project_api.dart';

final _projectWorkspaceProvider = FutureProvider<_ProjectWorkspace>((ref) async {
  final projectApi = ref.read(projectApiProvider);
  final driveApi = ref.read(driveApiProvider);
  final projects = await projectApi.getProjects();
  final tasks = await projectApi.getTasks();
  final driveDocuments = await driveApi.getProjectDocuments();
  return _ProjectWorkspace(
    projects: projects.map(_ProjectView.fromJson).toList(),
    tasks: tasks.map(_LinkedTaskView.fromJson).toList(),
    driveDocuments:
        driveDocuments.map(_DriveProjectDocumentView.fromJson).toList(),
  );
});

class ProjectsPage extends ConsumerStatefulWidget {
  const ProjectsPage({super.key});

  @override
  ConsumerState<ProjectsPage> createState() => _ProjectsPageState();
}

class _ProjectsPageState extends ConsumerState<ProjectsPage> {
  String _query = '';
  String _statusFilter = 'active';

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(_projectWorkspaceProvider);
    final data = workspace.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= 720;

    return Scaffold(
      appBar: AppBar(
        title: const Text('專案'),
        actions: [
          if (wide)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: FilledButton.icon(
                onPressed: data == null ? null : () => _openEditor(),
                icon: const Icon(Icons.create_new_folder_outlined),
                label: const Text('新增專案'),
              ),
            ),
        ],
      ),
      body: workspace.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ProjectErrorState(
          error: error,
          onRetry: () => ref.invalidate(_projectWorkspaceProvider),
        ),
        data: _buildContent,
      ),
      floatingActionButton: !wide && data != null
          ? FloatingActionButton(
              tooltip: '新增專案',
              onPressed: _openEditor,
              child: const Icon(Icons.create_new_folder_outlined),
            )
          : null,
    );
  }

  Widget _buildContent(_ProjectWorkspace workspace) {
    final projects = _visibleProjects(workspace);
    final activeCount = workspace.projects.where((p) => p.status == 'active').length;
    final withOpenTasks = workspace.projects
        .where((project) => workspace.openTasks(project.id).isNotEmpty)
        .length;
    final openTaskCount = workspace.tasks.where((task) => task.isOpen).length;

    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1040),
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              sliver: SliverToBoxAdapter(
                child: _ProjectOverview(
                  activeCount: activeCount,
                  withOpenTasksCount: withOpenTasks,
                  openTaskCount: openTaskCount,
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              sliver: SliverToBoxAdapter(
                child: TextField(
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search),
                    hintText: '搜尋專案、摘要或待辦',
                  ),
                  onChanged: (value) => setState(() => _query = value.trim()),
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
              sliver: SliverToBoxAdapter(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: _statusFilters(workspace)
                        .map(
                          (status) => Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: FilterChip(
                              label: Text(
                                status == '__all__'
                                    ? '全部'
                                    : _statusLabel(status),
                              ),
                              selected: _statusFilter == status,
                              onSelected: (_) =>
                                  setState(() => _statusFilter = status),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
              ),
            ),
            if (projects.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _ProjectEmptyState(
                  hasAnyProjects: workspace.projects.isNotEmpty,
                  onCreate: _openEditor,
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                sliver: SliverList.builder(
                  itemCount: projects.length,
                  itemBuilder: (context, index) {
                    final project = projects[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _ProjectCard(
                        project: project,
                        openTasks: workspace.openTasks(project.id),
                        driveDocuments: workspace.driveDocumentsFor(project.id),
                        onEdit: () => _openEditor(project: project),
                        onDelete: () => _deleteProject(project),
                        onOpenDrive: _openDriveDocument,
                        onDetachDrive: _detachDriveDocument,
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  List<String> _statusFilters(_ProjectWorkspace workspace) {
    final statuses = workspace.projects
        .map((project) => project.status)
        .where((status) => status != 'active')
        .toSet()
        .toList()
      ..sort();
    return ['active', ...statuses, '__all__'];
  }

  List<_ProjectView> _visibleProjects(_ProjectWorkspace workspace) {
    final query = _query.toLowerCase();
    final result = workspace.projects.where((project) {
      if (_statusFilter != '__all__' && project.status != _statusFilter) {
        return false;
      }
      if (query.isEmpty) return true;
      if (project.name.toLowerCase().contains(query) ||
          (project.summary ?? '').toLowerCase().contains(query)) {
        return true;
      }
      if (workspace
          .openTasks(project.id)
          .any((task) => task.title.toLowerCase().contains(query))) {
        return true;
      }
      return workspace
          .driveDocumentsFor(project.id)
          .any((document) => document.name.toLowerCase().contains(query));
    }).toList();

    result.sort((a, b) {
      if (a.status == 'active' && b.status != 'active') return -1;
      if (a.status != 'active' && b.status == 'active') return 1;
      final aUpdated = a.updatedAt;
      final bUpdated = b.updatedAt;
      if (aUpdated != null && bUpdated != null) {
        return bUpdated.compareTo(aUpdated);
      }
      if (aUpdated != null) return -1;
      if (bUpdated != null) return 1;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });
    return result;
  }

  Future<void> _openEditor({_ProjectView? project}) async {
    final result = await showDialog<_ProjectEditorResult>(
      context: context,
      builder: (_) => _ProjectEditorDialog(project: project),
    );
    if (result == null || !mounted) return;

    try {
      final api = ref.read(projectApiProvider);
      if (project == null) {
        await api.createProject(result.body);
      } else {
        await api.updateProject(project.id, result.body);
      }
      ref.invalidate(_projectWorkspaceProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(project == null ? '專案已新增' : '專案已更新')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _openDriveDocument(_DriveProjectDocumentView document) async {
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

  Future<void> _detachDriveDocument(_DriveProjectDocumentView document) async {
    try {
      await ref.read(driveApiProvider).detachDocumentFromProject(
            document.driveDocumentId,
            document.projectId,
          );
      ref.invalidate(_projectWorkspaceProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已解除「${document.name}」的專案關聯')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _deleteProject(_ProjectView project) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('刪除專案？'),
        content: Text(
          '確定要刪除「${project.name}」？若專案仍有關聯待辦、筆記、購物清單或 Drive 文件，系統會阻擋刪除。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
              foregroundColor: Theme.of(context).colorScheme.onError,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('刪除'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    try {
      await ref.read(projectApiProvider).deleteProject(project.id);
      ref.invalidate(_projectWorkspaceProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('專案已刪除')),
      );
    } on ProjectDeleteBlockedException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.userMessage)),
      );
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('操作失敗：$error')),
    );
  }
}

class _ProjectOverview extends StatelessWidget {
  const _ProjectOverview({
    required this.activeCount,
    required this.withOpenTasksCount,
    required this.openTaskCount,
  });

  final int activeCount;
  final int withOpenTasksCount;
  final int openTaskCount;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Wrap(
            spacing: 20,
            runSpacing: 12,
            children: [
              _ProjectMetric(label: '進行中專案', value: activeCount),
              _ProjectMetric(label: '有未完成待辦', value: withOpenTasksCount),
              _ProjectMetric(label: '未完成待辦', value: openTaskCount),
            ],
          ),
        ),
      );
}

class _ProjectMetric extends StatelessWidget {
  const _ProjectMetric({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 130,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$value', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 2),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
}

class _ProjectCard extends StatelessWidget {
  const _ProjectCard({
    required this.project,
    required this.openTasks,
    required this.driveDocuments,
    required this.onEdit,
    required this.onDelete,
    required this.onOpenDrive,
    required this.onDetachDrive,
  });

  final _ProjectView project;
  final List<_LinkedTaskView> openTasks;
  final List<_DriveProjectDocumentView> driveDocuments;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final ValueChanged<_DriveProjectDocumentView> onOpenDrive;
  final ValueChanged<_DriveProjectDocumentView> onDetachDrive;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final updated = project.updatedAt?.toLocal();

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  InkWell(
                    onTap: onEdit,
                    child: Text(
                      project.name,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  if ((project.summary ?? '').trim().isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      project.summary!.trim(),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _ProjectMetaChip(
                        icon: Icons.circle_outlined,
                        label: _statusLabel(project.status),
                      ),
                      _ProjectMetaChip(
                        icon: Icons.task_alt_outlined,
                        label: '未完成待辦 ${openTasks.length}',
                      ),
                      if (driveDocuments.isNotEmpty)
                        _ProjectMetaChip(
                          icon: Icons.add_to_drive_outlined,
                          label: '關聯文件 ${driveDocuments.length}',
                        ),
                      if (updated != null)
                        _ProjectMetaChip(
                          icon: Icons.update,
                          label: '更新 ${DateFormat('M/d HH:mm').format(updated)}',
                        ),
                    ],
                  ),
                  if (openTasks.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text('近期未完成待辦', style: theme.textTheme.labelMedium),
                    const SizedBox(height: 4),
                    for (final task in openTasks.take(3))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 2),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Padding(
                              padding: EdgeInsets.only(top: 7),
                              child: Icon(Icons.circle, size: 5),
                            ),
                            const SizedBox(width: 7),
                            Expanded(
                              child: Text(
                                task.title,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: theme.textTheme.bodySmall,
                              ),
                            ),
                          ],
                        ),
                      ),
                    if (openTasks.length > 3)
                      Text(
                        '另有 ${openTasks.length - 3} 項',
                        style: theme.textTheme.labelSmall,
                      ),
                  ],
                  if (driveDocuments.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    Text('關聯文件', style: theme.textTheme.labelMedium),
                    const SizedBox(height: 4),
                    for (final document in driveDocuments)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            border: Border.all(color: theme.dividerColor),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(10, 8, 8, 6),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.description_outlined, size: 18),
                                    const SizedBox(width: 7),
                                    Expanded(
                                      child: Text(
                                        document.name,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ],
                                ),
                                Wrap(
                                  spacing: 2,
                                  children: [
                                    TextButton(
                                      onPressed: document.webViewLink == null
                                          ? null
                                          : () => onOpenDrive(document),
                                      child: const Text('在 Drive 開啟'),
                                    ),
                                    const TextButton(
                                      onPressed: null,
                                      child: Text('相關筆記'),
                                    ),
                                    TextButton(
                                      onPressed: () => onDetachDrive(document),
                                      child: const Text('解除關聯'),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                  ],
                ],
              ),
            ),
            PopupMenuButton<String>(
              tooltip: '專案選項',
              onSelected: (value) {
                switch (value) {
                  case 'edit':
                    onEdit();
                    break;
                  case 'delete':
                    onDelete();
                    break;
                }
              },
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'edit', child: Text('編輯')),
                PopupMenuItem(value: 'delete', child: Text('刪除')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ProjectMetaChip extends StatelessWidget {
  const _ProjectMetaChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15),
          const SizedBox(width: 4),
          Text(label, style: theme.textTheme.labelSmall),
        ],
      ),
    );
  }
}

class _ProjectEditorDialog extends StatefulWidget {
  const _ProjectEditorDialog({required this.project});

  final _ProjectView? project;

  @override
  State<_ProjectEditorDialog> createState() => _ProjectEditorDialogState();
}

class _ProjectEditorDialogState extends State<_ProjectEditorDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _summary;
  late final TextEditingController _status;

  @override
  void initState() {
    super.initState();
    final project = widget.project;
    _name = TextEditingController(text: project?.name ?? '');
    _summary = TextEditingController(text: project?.summary ?? '');
    _status = TextEditingController(text: project?.status ?? 'active');
  }

  @override
  void dispose() {
    _name.dispose();
    _summary.dispose();
    _status.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.project != null;
    return AlertDialog(
      title: Text(editing ? '編輯專案' : '新增專案'),
      content: SizedBox(
        width: 520,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  key: const Key('project-name-field'),
                  controller: _name,
                  autofocus: true,
                  maxLength: 500,
                  decoration: const InputDecoration(labelText: '名稱'),
                  validator: (value) {
                    if ((value ?? '').trim().isEmpty) return '請輸入專案名稱';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  key: const Key('project-summary-field'),
                  controller: _summary,
                  maxLength: 10000,
                  minLines: 3,
                  maxLines: 6,
                  decoration: const InputDecoration(
                    labelText: '摘要',
                    alignLabelWithHint: true,
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  key: const Key('project-status-field'),
                  controller: _status,
                  maxLength: 32,
                  decoration: const InputDecoration(
                    labelText: '狀態',
                    helperText: '新專案預設為 active；既有自訂狀態會原樣保留。',
                  ),
                  validator: (value) {
                    if ((value ?? '').trim().isEmpty) return '請輸入狀態';
                    return null;
                  },
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消'),
        ),
        FilledButton(
          key: const Key('project-save-button'),
          onPressed: _submit,
          child: const Text('儲存'),
        ),
      ],
    );
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final summary = _summary.text.trim();
    Navigator.pop(
      context,
      _ProjectEditorResult(
        body: {
          'name': _name.text.trim(),
          'summary': summary.isEmpty ? null : summary,
          'status': _status.text.trim(),
        },
      ),
    );
  }
}

class _ProjectEditorResult {
  const _ProjectEditorResult({required this.body});

  final Map<String, dynamic> body;
}

class _ProjectWorkspace {
  const _ProjectWorkspace({
    required this.projects,
    required this.tasks,
    required this.driveDocuments,
  });

  final List<_ProjectView> projects;
  final List<_LinkedTaskView> tasks;
  final List<_DriveProjectDocumentView> driveDocuments;

  List<_LinkedTaskView> openTasks(String projectId) {
    final result = tasks
        .where((task) => task.projectId == projectId && task.isOpen)
        .toList();
    result.sort((a, b) {
      final aDue = a.dueAt?.toLocal();
      final bDue = b.dueAt?.toLocal();
      if (aDue != null && bDue != null) return aDue.compareTo(bDue);
      if (aDue != null) return -1;
      if (bDue != null) return 1;
      return a.title.toLowerCase().compareTo(b.title.toLowerCase());
    });
    return result;
  }

  List<_DriveProjectDocumentView> driveDocumentsFor(String projectId) =>
      driveDocuments.where((document) => document.projectId == projectId).toList();
}

class _ProjectView {
  const _ProjectView({
    required this.id,
    required this.name,
    required this.summary,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  factory _ProjectView.fromJson(Map<String, dynamic> json) => _ProjectView(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        summary: json['summary'] as String?,
        status: json['status'] as String? ?? 'active',
        createdAt: _parseDate(json['created_at']),
        updatedAt: _parseDate(json['updated_at']),
      );

  final String id;
  final String name;
  final String? summary;
  final String status;
  final DateTime? createdAt;
  final DateTime? updatedAt;
}

class _LinkedTaskView {
  const _LinkedTaskView({
    required this.id,
    required this.title,
    required this.status,
    required this.projectId,
    required this.dueAt,
  });

  factory _LinkedTaskView.fromJson(Map<String, dynamic> json) => _LinkedTaskView(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        status: json['status'] as String? ?? 'pending',
        projectId: json['project_id'] as String?,
        dueAt: _parseDate(json['due_at']),
      );

  final String id;
  final String title;
  final String status;
  final String? projectId;
  final DateTime? dueAt;

  bool get isOpen => status != 'completed' && status != 'cancelled';
}

class _DriveProjectDocumentView {
  const _DriveProjectDocumentView({
    required this.projectId,
    required this.driveDocumentId,
    required this.name,
    required this.mimeType,
    required this.webViewLink,
  });

  factory _DriveProjectDocumentView.fromJson(Map<String, dynamic> json) =>
      _DriveProjectDocumentView(
        projectId: json['project_id'] as String? ?? '',
        driveDocumentId: json['drive_document_id'] as String? ?? '',
        name: json['name'] as String? ?? 'Google Drive 文件',
        mimeType: json['mime_type'] as String? ?? 'application/octet-stream',
        webViewLink: json['web_view_link'] as String?,
      );

  final String projectId;
  final String driveDocumentId;
  final String name;
  final String mimeType;
  final String? webViewLink;
}

class _ProjectEmptyState extends StatelessWidget {
  const _ProjectEmptyState({
    required this.hasAnyProjects,
    required this.onCreate,
  });

  final bool hasAnyProjects;
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.folder_open_outlined,
                size: 48,
                color: Theme.of(context).colorScheme.secondary,
              ),
              const SizedBox(height: 12),
              Text(
                hasAnyProjects ? '沒有符合條件的專案' : '還沒有專案',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(
                hasAnyProjects ? '調整搜尋或狀態篩選。' : '建立一個專案，把相關待辦集中起來。',
                textAlign: TextAlign.center,
              ),
              if (!hasAnyProjects) ...[
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: onCreate,
                  icon: const Icon(Icons.add),
                  label: const Text('新增專案'),
                ),
              ],
            ],
          ),
        ),
      );
}

class _ProjectErrorState extends StatelessWidget {
  const _ProjectErrorState({required this.error, required this.onRetry});

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.cloud_off_outlined,
                size: 48,
                color: Theme.of(context).colorScheme.error,
              ),
              const SizedBox(height: 12),
              Text('無法載入專案', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 6),
              Text('$error', textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('重試'),
              ),
            ],
          ),
        ),
      );
}

DateTime? _parseDate(dynamic value) {
  if (value is! String || value.isEmpty) return null;
  return DateTime.tryParse(value);
}

String _statusLabel(String status) {
  switch (status) {
    case 'active':
      return '進行中';
    case 'completed':
      return '已完成';
    case 'archived':
      return '已封存';
    case 'paused':
      return '暫停';
    default:
      return status;
  }
}
