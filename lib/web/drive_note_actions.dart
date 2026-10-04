import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/design_system/design_system.dart';
import 'drive_api.dart';
import 'note_api.dart';

class DriveNoteActions extends ConsumerStatefulWidget {
  const DriveNoteActions({
    super.key,
    required this.document,
  });

  final Map<String, dynamic> document;

  @override
  ConsumerState<DriveNoteActions> createState() => _DriveNoteActionsState();
}

class _DriveNoteActionsState extends ConsumerState<DriveNoteActions> {
  bool _busy = false;
  List<Map<String, dynamic>> _relations = const [];

  String get _documentId => widget.document['id']?.toString() ?? '';

  @override
  void initState() {
    super.initState();
    _loadRelations();
  }

  Future<void> _loadRelations() async {
    if (_documentId.isEmpty) return;
    try {
      final relations =
          await ref.read(driveNoteApiProvider).getDocumentNotes(_documentId);
      if (!mounted) return;
      setState(() => _relations = relations);
    } catch (_) {
      // Relationship metadata is supplemental and must not hide the Drive file.
    }
  }

  Future<void> _importToNote() async {
    if (_busy || _documentId.isEmpty) return;
    List<Map<String, dynamic>> projects = const [];
    try {
      projects = await ref.read(noteApiProvider).getProjects();
    } catch (_) {
      // Import is still allowed without assigning a Project.
    }
    if (!mounted) return;

    final result = await showDialog<_ImportResult>(
      context: context,
      builder: (_) => _ImportDialog(
        defaultTitle: widget.document['name']?.toString() ?? '',
        projects: projects,
      ),
    );
    if (result == null || !mounted) return;

    setState(() => _busy = true);
    try {
      await ref.read(driveNoteApiProvider).importDocumentToNote(
        _documentId,
        {
          'title': result.title,
          'project_id': result.projectId,
          'tags': result.tags,
        },
      );
      await _loadRelations();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已轉成筆記。Drive 原始文件不會被修改。')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('轉成筆記失敗：$error')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _linkExistingNote() async {
    if (_busy || _documentId.isEmpty) return;
    List<Map<String, dynamic>> notes;
    try {
      notes = await ref.read(noteApiProvider).getNotes();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('載入筆記失敗：$error')),
      );
      return;
    }
    if (!mounted) return;

    final noteId = await showDialog<String>(
      context: context,
      builder: (_) => _LinkDialog(notes: notes),
    );
    if (noteId == null || !mounted) return;

    setState(() => _busy = true);
    try {
      await ref.read(driveNoteApiProvider).linkDocumentNote(
            _documentId,
            noteId,
          );
      await _loadRelations();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已建立 Drive 與筆記的手動關聯。')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('建立筆記關聯失敗：$error')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_documentId.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            FilledButton.tonalIcon(
              key: ValueKey('drive-note-import-$_documentId'),
              onPressed: _busy ? null : _importToNote,
              icon: const Icon(Icons.note_add_outlined),
              label: const Text('轉成筆記'),
            ),
            OutlinedButton.icon(
              key: ValueKey('drive-note-link-$_documentId'),
              onPressed: _busy ? null : _linkExistingNote,
              icon: const Icon(Icons.link),
              label: const Text('關聯既有筆記'),
            ),
          ],
        ),
        if (_relations.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          ..._relations.map((relation) {
            final note = (relation['note'] as Map?)?.cast<String, dynamic>() ??
                const <String, dynamic>{};
            final title = note['title']?.toString().trim();
            final displayTitle =
                title == null || title.isEmpty ? '未命名筆記' : title;
            final source = relation['relation_type'] == 'source_import';
            return Padding(
              padding: const EdgeInsets.only(top: AppSpacing.xs),
              child: Text(
                source ? '來源筆記：$displayTitle' : '相關筆記：$displayTitle',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            );
          }),
        ],
      ],
    );
  }
}

class _ImportResult {
  const _ImportResult({
    required this.title,
    required this.projectId,
    required this.tags,
  });

  final String? title;
  final String? projectId;
  final List<String> tags;
}

class _ImportDialog extends StatefulWidget {
  const _ImportDialog({
    required this.defaultTitle,
    required this.projects,
  });

  final String defaultTitle;
  final List<Map<String, dynamic>> projects;

  @override
  State<_ImportDialog> createState() => _ImportDialogState();
}

class _ImportDialogState extends State<_ImportDialog> {
  late final TextEditingController _title;
  final _tags = TextEditingController();
  String? _projectId;

  @override
  void initState() {
    super.initState();
    _title = TextEditingController(text: widget.defaultTitle);
  }

  @override
  void dispose() {
    _title.dispose();
    _tags.dispose();
    super.dispose();
  }

  List<String> _normalizedTags() {
    final seen = <String>{};
    final values = <String>[];
    for (final raw in _tags.text.split(',')) {
      final value = raw.trim();
      if (value.isEmpty || !seen.add(value)) continue;
      values.add(value);
    }
    return values;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('轉成筆記'),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              key: const ValueKey('drive-note-title-field'),
              controller: _title,
              decoration: const InputDecoration(labelText: '筆記標題'),
            ),
            const SizedBox(height: AppSpacing.md),
            DropdownButtonFormField<String?>(
              key: const ValueKey('drive-note-project-field'),
              initialValue: _projectId,
              decoration: const InputDecoration(labelText: '專案（選填）'),
              items: [
                const DropdownMenuItem<String?>(
                  value: null,
                  child: Text('不指定專案'),
                ),
                ...widget.projects.map(
                  (project) => DropdownMenuItem<String?>(
                    value: project['id']?.toString(),
                    child: Text(project['name']?.toString() ?? '未命名專案'),
                  ),
                ),
              ],
              onChanged: (value) => setState(() => _projectId = value),
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              key: const ValueKey('drive-note-tags-field'),
              controller: _tags,
              decoration: const InputDecoration(
                labelText: '標籤（逗號分隔）',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消'),
        ),
        FilledButton(
          key: const ValueKey('drive-note-import-save'),
          onPressed: () {
            final title = _title.text.trim();
            Navigator.pop(
              context,
              _ImportResult(
                title: title.isEmpty ? null : title,
                projectId: _projectId,
                tags: _normalizedTags(),
              ),
            );
          },
          child: const Text('建立筆記'),
        ),
      ],
    );
  }
}

class _LinkDialog extends StatefulWidget {
  const _LinkDialog({required this.notes});

  final List<Map<String, dynamic>> notes;

  @override
  State<_LinkDialog> createState() => _LinkDialogState();
}

class _LinkDialogState extends State<_LinkDialog> {
  String? _noteId;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('關聯既有筆記'),
      content: SizedBox(
        width: 480,
        child: DropdownButtonFormField<String>(
          key: const ValueKey('drive-note-link-target'),
          initialValue: _noteId,
          decoration: const InputDecoration(labelText: '筆記'),
          items: widget.notes
              .where((note) => (note['id']?.toString() ?? '').isNotEmpty)
              .map(
                (note) => DropdownMenuItem<String>(
                  value: note['id'].toString(),
                  child: Text(
                    (note['title']?.toString().trim().isNotEmpty ?? false)
                        ? note['title'].toString().trim()
                        : '未命名筆記',
                  ),
                ),
              )
              .toList(),
          onChanged: (value) => setState(() => _noteId = value),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消'),
        ),
        FilledButton(
          key: const ValueKey('drive-note-link-save'),
          onPressed:
              _noteId == null ? null : () => Navigator.pop(context, _noteId),
          child: const Text('建立關聯'),
        ),
      ],
    );
  }
}
